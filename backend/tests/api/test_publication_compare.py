"""Phase 3.1d integration tests — compare endpoint + publish capture extension.

Per ``docs/recon/phase-3-1d-recon.md`` §6.3.

Tests use a real per-test SQLite engine for ``publication_block_snapshot``
+ ``publications`` rows, and a fake ResolveService stand-in for the
cached-only resolve path. The fake is wired through the same DI
contract (PublicationStalenessService(snapshot_repo, publication_repo,
resolve_service)) so the comparator algorithm runs against real DB rows
under test.
"""
from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from typing import Any

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.api.routers.admin_publications import (
    _get_audit,
    _get_repo,
    _get_snapshot_repo,
    _get_staleness_service,
    router,
)
from src.core.database import Base
from src.core.error_handler import register_exception_handlers
from src.core.security.auth import AuthMiddleware
from src.models.publication import Publication, PublicationStatus
from src.models.publication_block_snapshot import PublicationBlockSnapshot
from src.repositories.publication_block_snapshot_repository import (
    PublicationBlockSnapshotRepository,
)
from src.repositories.publication_repository import PublicationRepository
from src.schemas.resolve import ResolvedValueResponse
from src.services.audit import AuditWriter
from src.services.publications.lineage import generate_lineage_key
from src.services.publications.staleness import PublicationStalenessService
from src.services.resolve.exceptions import ResolveCacheMissError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
async def engine() -> AsyncGenerator[AsyncEngine, None]:
    eng = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest.fixture()
async def session_factory(engine: AsyncEngine):
    return async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )


# ---------------------------------------------------------------------------
# Fake ResolveService — implements the cached-only contract used by
# PublicationStalenessService._compare_one_snapshot. Programmable with a
# dict keyed on (cube_id, semantic_key, period); value is either a
# ResolvedValueResponse OR an Exception instance to raise.
# ---------------------------------------------------------------------------


class _FakeResolveService:
    def __init__(self) -> None:
        self.responses: dict[tuple[str, str, str | None], Any] = {}
        self.calls: list[dict[str, Any]] = []

    def set_response(
        self,
        *,
        cube_id: str,
        semantic_key: str,
        period: str | None,
        response: Any,
    ) -> None:
        self.responses[(cube_id, semantic_key, period)] = response

    async def resolve_value(
        self,
        *,
        cube_id: str,
        semantic_key: str,
        dims: list[int],
        members: list[int],
        period: str | None,
        allow_auto_prime: bool = True,
    ) -> ResolvedValueResponse:
        self.calls.append(
            {
                "cube_id": cube_id,
                "semantic_key": semantic_key,
                "dims": list(dims),
                "members": list(members),
                "period": period,
                "allow_auto_prime": allow_auto_prime,
            }
        )
        key = (cube_id, semantic_key, period)
        outcome = self.responses.get(key)
        if outcome is None:
            raise ResolveCacheMissError(
                cube_id=cube_id,
                semantic_key=semantic_key,
                coord="",
                period=period,
                prime_attempted=False,
                prime_error_code=None,
            )
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


def _resolved(
    *,
    cube_id: str = "1810000401",
    semantic_key: str = "housing.starts.total",
    coord: str = "1.1.1.1",
    period: str = "2025-12",
    value: str | None = "12345",
    missing: bool = False,
    is_stale: bool = False,
    source_hash: str = "src-hash-A",
    mapping_version: int | None = 1,
) -> ResolvedValueResponse:
    return ResolvedValueResponse(
        cube_id=cube_id,
        semantic_key=semantic_key,
        coord=coord,
        period=period,
        value=value,
        missing=missing,
        resolved_at=datetime.now(timezone.utc),
        source_hash=source_hash,
        is_stale=is_stale,
        units=None,
        cache_status="hit",
        mapping_version=mapping_version,
    )


# ---------------------------------------------------------------------------
# App builder
# ---------------------------------------------------------------------------


def _build_app(session_factory, fake_resolve: _FakeResolveService) -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(router)

    async def _override_repo() -> AsyncGenerator[PublicationRepository, None]:
        async with session_factory() as session:
            try:
                yield PublicationRepository(session)
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def _override_audit() -> AsyncGenerator[AuditWriter, None]:
        async with session_factory() as session:
            try:
                yield AuditWriter(session)
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def _override_snapshot_repo() -> AsyncGenerator[
        PublicationBlockSnapshotRepository, None
    ]:
        async with session_factory() as session:
            try:
                yield PublicationBlockSnapshotRepository(session)
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    # Compose the real PublicationStalenessService with real repos
    # against in-memory SQLite + a programmable fake ResolveService.
    # The comparator algorithm runs against actual DB rows; only the
    # cache-resolution boundary is faked.
    #
    # Async generator dependency mirrors _override_repo / _override_audit:
    # explicit commit on success, rollback on exception, session closed
    # by `async with` on yield exit. This guarantees publish capture
    # commits to the engine before the test reads back via a separate
    # session.
    async def _override_staleness() -> AsyncGenerator[
        PublicationStalenessService, None
    ]:
        async with session_factory() as session:
            try:
                yield PublicationStalenessService(
                    snapshot_repository=PublicationBlockSnapshotRepository(session),
                    publication_repository=PublicationRepository(session),
                    resolve_service=fake_resolve,  # type: ignore[arg-type]
                )
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[_get_repo] = _override_repo
    app.dependency_overrides[_get_audit] = _override_audit
    app.dependency_overrides[_get_snapshot_repo] = _override_snapshot_repo
    app.dependency_overrides[_get_staleness_service] = _override_staleness

    app.add_middleware(AuthMiddleware, admin_api_key="test-admin-key")
    return app


def _auth_headers() -> dict[str, str]:
    return {"X-API-KEY": "test-admin-key"}


# ---------------------------------------------------------------------------
# Helpers — direct DB seeding (bypass admin endpoints for setup speed)
# ---------------------------------------------------------------------------


async def _seed_publication(
    session_factory,
    *,
    status: PublicationStatus = PublicationStatus.PUBLISHED,
    headline: str = "Test publication",
) -> int:
    async with session_factory() as session:
        lineage_key = generate_lineage_key()
        pub = Publication(
            headline=headline,
            chart_type="bar",
            status=status,
            lineage_key=lineage_key,
            slug=f"test-{lineage_key}",
            published_at=(
                datetime.now(timezone.utc)
                if status == PublicationStatus.PUBLISHED
                else None
            ),
        )
        session.add(pub)
        await session.commit()
        return pub.id


async def _seed_snapshot(
    session_factory,
    *,
    publication_id: int,
    block_id: str = "block-1",
    cube_id: str = "1810000401",
    semantic_key: str = "housing.starts.total",
    coord: str = "1.1.1.1",
    period: str | None = "2025-12",
    dims: list[int] | None = None,
    members: list[int] | None = None,
    mapping_version: int | None = 1,
    source_hash: str = "src-hash-A",
    value: str | None = "12345",
    missing: bool = False,
    is_stale: bool = False,
) -> None:
    async with session_factory() as session:
        snap = PublicationBlockSnapshot(
            publication_id=publication_id,
            block_id=block_id,
            cube_id=cube_id,
            semantic_key=semantic_key,
            coord=coord,
            period=period,
            dims_json=dims if dims is not None else [1],
            members_json=members if members is not None else [1],
            mapping_version_at_publish=mapping_version,
            source_hash_at_publish=source_hash,
            value_at_publish=value,
            missing_at_publish=missing,
            is_stale_at_publish=is_stale,
            captured_at=datetime.now(timezone.utc),
        )
        session.add(snap)
        await session.commit()


async def _count_snapshots(session_factory, publication_id: int) -> int:
    from sqlalchemy import select
    async with session_factory() as session:
        result = await session.execute(
            select(PublicationBlockSnapshot).where(
                PublicationBlockSnapshot.publication_id == publication_id
            )
        )
        return len(list(result.scalars().all()))


async def _get_snapshot(
    session_factory, publication_id: int, block_id: str = "block-1",
) -> PublicationBlockSnapshot:
    """Fetch a single snapshot row for content assertions.

    Raises if zero or multiple rows match — caller assumes a single
    captured row from the bound_block.
    """
    from sqlalchemy import select
    async with session_factory() as session:
        result = await session.execute(
            select(PublicationBlockSnapshot).where(
                PublicationBlockSnapshot.publication_id == publication_id,
                PublicationBlockSnapshot.block_id == block_id,
            )
        )
        rows = list(result.scalars().all())
        assert len(rows) == 1, (
            f"expected exactly 1 snapshot for pub={publication_id} "
            f"block={block_id}, found {len(rows)}"
        )
        return rows[0]


# ---------------------------------------------------------------------------
# Compare endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compare_returns_404_for_nonexistent_publication(
    session_factory,
) -> None:
    fake = _FakeResolveService()
    app = _build_app(session_factory, fake)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/admin/publications/99999/compare",
            headers=_auth_headers(),
        )
    assert resp.status_code == 404, resp.text


@pytest.mark.asyncio
async def test_compare_returns_synthetic_unknown_for_pre_3_1d_publication(
    session_factory,
) -> None:
    pub_id = await _seed_publication(session_factory)
    fake = _FakeResolveService()
    app = _build_app(session_factory, fake)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            f"/api/v1/admin/publications/{pub_id}/compare",
            headers=_auth_headers(),
        )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["overall_status"] == "unknown"
    assert data["overall_severity"] == "info"
    assert len(data["block_results"]) == 1
    block = data["block_results"][0]
    assert block["block_id"] == ""
    assert block["cube_id"] == ""
    assert block["semantic_key"] == ""
    assert block["stale_reasons"] == ["snapshot_missing"]
    assert block["compare_basis"]["compare_kind"] == "snapshot_missing"
    assert block["compare_basis"]["cause"] == "no_snapshot_row"


@pytest.mark.asyncio
async def test_compare_returns_fresh_when_snapshot_matches_current_cache(
    session_factory,
) -> None:
    pub_id = await _seed_publication(session_factory)
    await _seed_snapshot(
        session_factory,
        publication_id=pub_id,
        mapping_version=1,
        source_hash="src-hash-A",
        value="12345",
        missing=False,
        is_stale=False,
    )
    fake = _FakeResolveService()
    fake.set_response(
        cube_id="1810000401",
        semantic_key="housing.starts.total",
        period="2025-12",
        response=_resolved(
            mapping_version=1,
            source_hash="src-hash-A",
            value="12345",
            missing=False,
            is_stale=False,
        ),
    )
    app = _build_app(session_factory, fake)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            f"/api/v1/admin/publications/{pub_id}/compare",
            headers=_auth_headers(),
        )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["overall_status"] == "fresh"
    assert len(data["block_results"]) == 1
    assert data["block_results"][0]["stale_reasons"] == []
    # Cached-only mode must be enforced.
    assert fake.calls and fake.calls[0]["allow_auto_prime"] is False


@pytest.mark.asyncio
async def test_compare_returns_stale_when_value_drifts(session_factory) -> None:
    pub_id = await _seed_publication(session_factory)
    await _seed_snapshot(
        session_factory,
        publication_id=pub_id,
        value="12345",
    )
    fake = _FakeResolveService()
    fake.set_response(
        cube_id="1810000401",
        semantic_key="housing.starts.total",
        period="2025-12",
        response=_resolved(value="99999"),  # drifted
    )
    app = _build_app(session_factory, fake)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            f"/api/v1/admin/publications/{pub_id}/compare",
            headers=_auth_headers(),
        )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["overall_status"] == "stale"
    reasons = data["block_results"][0]["stale_reasons"]
    assert "value_changed" in reasons


@pytest.mark.asyncio
async def test_compare_aggregates_severity_warning_dominates_info(
    session_factory,
) -> None:
    pub_id = await _seed_publication(session_factory)
    # Block 1: mapping_version drift (info-only).
    await _seed_snapshot(
        session_factory,
        publication_id=pub_id,
        block_id="block-1",
        semantic_key="housing.starts.total",
        mapping_version=1,
        value="12345",
    )
    # Block 2: value drift (warning).
    await _seed_snapshot(
        session_factory,
        publication_id=pub_id,
        block_id="block-2",
        semantic_key="housing.completions.total",
        value="100",
    )
    fake = _FakeResolveService()
    fake.set_response(
        cube_id="1810000401",
        semantic_key="housing.starts.total",
        period="2025-12",
        response=_resolved(
            semantic_key="housing.starts.total",
            mapping_version=2,
            value="12345",
        ),
    )
    fake.set_response(
        cube_id="1810000401",
        semantic_key="housing.completions.total",
        period="2025-12",
        response=_resolved(
            semantic_key="housing.completions.total", value="200"
        ),
    )
    app = _build_app(session_factory, fake)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            f"/api/v1/admin/publications/{pub_id}/compare",
            headers=_auth_headers(),
        )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["overall_severity"] == "warning"
    assert data["overall_status"] == "stale"


@pytest.mark.asyncio
async def test_compare_returns_compare_failed_when_cache_row_missing(
    session_factory,
) -> None:
    pub_id = await _seed_publication(session_factory)
    await _seed_snapshot(session_factory, publication_id=pub_id)
    fake = _FakeResolveService()
    # No response set → fake raises ResolveCacheMissError by default.
    app = _build_app(session_factory, fake)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            f"/api/v1/admin/publications/{pub_id}/compare",
            headers=_auth_headers(),
        )
    assert resp.status_code == 200, resp.text
    block = resp.json()["block_results"][0]
    assert block["stale_reasons"] == ["compare_failed"]
    assert block["compare_basis"]["compare_kind"] == "compare_failed"
    assert block["compare_basis"]["resolve_error"] == "RESOLVE_CACHE_MISS"
    assert (
        block["compare_basis"]["details"]["message"]
        == "Current cache row is missing"
    )


@pytest.mark.asyncio
async def test_compare_publication_without_snapshots_returns_synthetic(
    session_factory,
) -> None:
    """Compare on any published publication with zero snapshot rows
    returns the synthetic snapshot_missing result. This covers
    pre-3.1d publications, fresh clones, and any other case where the
    publication exists but capture never wrote rows.

    Note: real clone-via-endpoint snapshot semantics belong to the
    repository/migration test layer (PR 1). This test only locks the
    compare endpoint contract for the zero-snapshots input.
    """
    src_id = await _seed_publication(session_factory)
    await _seed_snapshot(session_factory, publication_id=src_id)
    target_id = await _seed_publication(
        session_factory, headline="Target with no snapshots"
    )
    fake = _FakeResolveService()
    app = _build_app(session_factory, fake)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            f"/api/v1/admin/publications/{target_id}/compare",
            headers=_auth_headers(),
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["overall_status"] == "unknown"
    assert data["block_results"][0]["compare_basis"]["compare_kind"] == (
        "snapshot_missing"
    )


@pytest.mark.asyncio
async def test_compare_requires_admin_auth(session_factory) -> None:
    pub_id = await _seed_publication(session_factory)
    fake = _FakeResolveService()
    app = _build_app(session_factory, fake)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            f"/api/v1/admin/publications/{pub_id}/compare",
        )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Publish handler extension tests
# ---------------------------------------------------------------------------


async def _seed_draft(session_factory) -> int:
    return await _seed_publication(
        session_factory, status=PublicationStatus.DRAFT
    )


@pytest.mark.asyncio
async def test_publish_with_no_body_works_unchanged(session_factory) -> None:
    pub_id = await _seed_draft(session_factory)
    fake = _FakeResolveService()
    app = _build_app(session_factory, fake)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            f"/api/v1/admin/publications/{pub_id}/publish",
            headers=_auth_headers(),
        )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "PUBLISHED"
    assert await _count_snapshots(session_factory, pub_id) == 0


@pytest.mark.asyncio
async def test_publish_with_null_body_works_unchanged(session_factory) -> None:
    pub_id = await _seed_draft(session_factory)
    fake = _FakeResolveService()
    app = _build_app(session_factory, fake)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            f"/api/v1/admin/publications/{pub_id}/publish",
            headers=_auth_headers(),
            json=None,
        )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "PUBLISHED"
    assert await _count_snapshots(session_factory, pub_id) == 0


@pytest.mark.asyncio
async def test_publish_with_empty_object_body_works_unchanged(
    session_factory,
) -> None:
    pub_id = await _seed_draft(session_factory)
    fake = _FakeResolveService()
    app = _build_app(session_factory, fake)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            f"/api/v1/admin/publications/{pub_id}/publish",
            headers=_auth_headers(),
            json={},
        )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "PUBLISHED"
    assert await _count_snapshots(session_factory, pub_id) == 0


@pytest.mark.asyncio
async def test_publish_with_bound_blocks_captures_snapshots(
    session_factory,
) -> None:
    """Capture path persists the full snapshot fingerprint.

    Asserts every captured field — not just row count — so a regression
    in capture wiring (wrong dims/coord/period/value/source_hash/mapping)
    fails this test.
    """
    pub_id = await _seed_draft(session_factory)
    fake = _FakeResolveService()
    fake.set_response(
        cube_id="1810000401",
        semantic_key="housing.starts.total",
        period="2025-12",
        response=_resolved(
            coord="1.1.1.1",
            value="42000",
            source_hash="src-hash-A",
            mapping_version=1,
            missing=False,
            is_stale=False,
        ),
    )
    app = _build_app(session_factory, fake)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            f"/api/v1/admin/publications/{pub_id}/publish",
            headers=_auth_headers(),
            json={
                "bound_blocks": [
                    {
                        "block_id": "block-1",
                        "cube_id": "1810000401",
                        "semantic_key": "housing.starts.total",
                        "dims": [1],
                        "members": [1],
                        "period": "2025-12",
                    }
                ]
            },
        )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "PUBLISHED"
    assert await _count_snapshots(session_factory, pub_id) == 1

    # Full content assertion — every captured field must reflect the
    # bound_block input + resolved fingerprint, not garbage from a
    # mis-wired capture path.
    snap = await _get_snapshot(session_factory, pub_id, block_id="block-1")
    assert snap.publication_id == pub_id
    assert snap.block_id == "block-1"
    assert snap.cube_id == "1810000401"
    assert snap.semantic_key == "housing.starts.total"
    assert snap.coord == "1.1.1.1"
    assert snap.period == "2025-12"
    assert snap.dims_json == [1]
    assert snap.members_json == [1]
    assert snap.value_at_publish == "42000"
    assert snap.source_hash_at_publish == "src-hash-A"
    assert snap.mapping_version_at_publish == 1
    assert snap.missing_at_publish is False
    assert snap.is_stale_at_publish is False
    assert snap.captured_at is not None

    # Capture path uses default auto-prime (recon §5.3 — capture SHOULD
    # prime the cache if missing). This is the contract opposite to the
    # compare path which sets allow_auto_prime=False.
    assert len(fake.calls) == 1
    call = fake.calls[0]
    assert call["allow_auto_prime"] is True
    assert call["dims"] == [1]
    assert call["members"] == [1]
    assert call["cube_id"] == "1810000401"
    assert call["semantic_key"] == "housing.starts.total"
    assert call["period"] == "2025-12"


@pytest.mark.asyncio
async def test_publish_capture_failure_does_not_fail_publish(
    session_factory,
) -> None:
    """Capture failure on resolve does NOT roll back publish (recon §5)."""
    pub_id = await _seed_draft(session_factory)
    fake = _FakeResolveService()
    # No response registered for this block — fake raises by default.
    app = _build_app(session_factory, fake)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            f"/api/v1/admin/publications/{pub_id}/publish",
            headers=_auth_headers(),
            json={
                "bound_blocks": [
                    {
                        "block_id": "missing-mapping-block",
                        "cube_id": "1810000401",
                        "semantic_key": "housing.starts.total",
                        "dims": [1],
                        "members": [1],
                        "period": "2025-12",
                    }
                ]
            },
        )
    assert resp.status_code == 200, resp.text
    # Publish succeeded but no snapshot row was written for the failing block.
    assert await _count_snapshots(session_factory, pub_id) == 0
    assert resp.json()["status"] == "PUBLISHED"


@pytest.mark.asyncio
async def test_publish_capture_db_upsert_failure_does_not_fail_publish(
    session_factory,
) -> None:
    """DB-level upsert failure during capture is swallowed by the
    service-level per-block try/except (recon §5).

    Mechanism: send a bound_block with ``members`` violating the shape
    invariant (negative member, which the service's
    ``validate_snapshot_dims_members`` rejects via ValueError before
    repo.upsert_for_block is called). This exercises the same
    per-block exception swallowing path as a real DB upsert error
    (IntegrityError, etc.) without needing to inject a broken
    repository — the contract being tested is "service-level
    swallow", which is identical regardless of which layer raises.
    """
    pub_id = await _seed_draft(session_factory)
    fake = _FakeResolveService()
    # Resolve registered so we get past resolve. The shape validator
    # then fires before upsert.
    fake.set_response(
        cube_id="1810000401",
        semantic_key="housing.starts.total",
        period="2025-12",
        response=_resolved(coord="1.1.1.1", value="42000"),
    )
    app = _build_app(session_factory, fake)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            f"/api/v1/admin/publications/{pub_id}/publish",
            headers=_auth_headers(),
            json={
                "bound_blocks": [
                    {
                        "block_id": "block-1",
                        "cube_id": "1810000401",
                        "semantic_key": "housing.starts.total",
                        # Negative member triggers
                        # validate_snapshot_dims_members ValueError
                        # before any DB write.
                        "dims": [1],
                        "members": [-1],
                        "period": "2025-12",
                    }
                ]
            },
        )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "PUBLISHED"
    assert await _count_snapshots(session_factory, pub_id) == 0


@pytest.mark.asyncio
async def test_publish_bare_array_body_rejected(session_factory) -> None:
    pub_id = await _seed_draft(session_factory)
    fake = _FakeResolveService()
    app = _build_app(session_factory, fake)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            f"/api/v1/admin/publications/{pub_id}/publish",
            headers=_auth_headers(),
            json=[
                {
                    "block_id": "block-1",
                    "cube_id": "1810000401",
                    "semantic_key": "housing.starts.total",
                    "dims": [1],
                    "members": [1],
                }
            ],
        )
    assert resp.status_code == 422, resp.text
