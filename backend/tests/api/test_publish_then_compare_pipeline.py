"""Phase 3.1d pipeline test — full publish→compare HTTP roundtrip.

Per ``docs/recon/phase-3-1d-recon.md`` §6.4.

Unlike ``test_publication_compare.py`` (which fakes the ResolveService
boundary), this pipeline test seeds ``cube_metadata_cache`` +
``semantic_mappings`` + ``semantic_value_cache`` rows directly into an
in-memory SQLite engine and runs the **real** composed
``ResolveService`` against those rows. Cache hits short-circuit step 4
of the resolve state machine, so no StatCan client call is ever issued.

Loop exercised:

  1. POST /publish with bound_blocks → snapshot captured
  2. POST /compare → fresh
  3. Mutate cache value in DB → simulate upstream drift
  4. POST /compare → stale + value_changed
"""
from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import pytest
import structlog
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.api.routers.admin_publications import router
from src.api.routers.admin_resolve import _get_resolve_service
from src.core.database import Base, get_db
from src.core.error_handler import register_exception_handlers
from src.core.security.auth import AuthMiddleware
from src.models.cube_metadata_cache import CubeMetadataCache
from src.models.publication import Publication, PublicationStatus
from src.models.publication_block_snapshot import PublicationBlockSnapshot
from src.models.semantic_mapping import SemanticMapping
from src.models.semantic_value_cache import SemanticValueCache
from src.repositories.semantic_mapping_repository import (
    SemanticMappingRepository,
)
from src.repositories.semantic_value_cache_repository import (
    SemanticValueCacheRepository,
)
from src.services.publications.lineage import generate_lineage_key
from src.services.resolve.service import ResolveService
from src.services.statcan.metadata_cache import StatCanMetadataCacheService
from src.services.statcan.value_cache import StatCanValueCacheService


# ---------------------------------------------------------------------------
# Test data — single canonical (cube, semantic_key, dim, member, period) tuple
# ---------------------------------------------------------------------------

_CUBE_ID = "1810000401"
_PRODUCT_ID = 18100004
_SEMANTIC_KEY = "housing.starts.total"
_DIM_NAME = "Geography"
_MEMBER_NAME = "Canada"
_DIM_POSITION = 1
_MEMBER_ID = 1
# derive_coord places member_id at slot (position-1) of a 10-slot dotted string.
_COORD = "1.0.0.0.0.0.0.0.0.0"
_PERIOD = "2025-12"
_SOURCE_HASH = "src-hash-A"
_VALUE_INITIAL = Decimal("12345.000000")
_VALUE_DRIFTED = Decimal("99999.000000")


# ---------------------------------------------------------------------------
# Engine / session_factory fixtures
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
# DB seeding helpers
# ---------------------------------------------------------------------------


async def _seed_cube_metadata(session_factory) -> None:
    """Seed cube_metadata_cache so validate_filters_against_mapping resolves
    Geography→Canada to (position_id=1, member_id=1) without StatCan."""
    async with session_factory() as session:
        row = CubeMetadataCache(
            cube_id=_CUBE_ID,
            product_id=_PRODUCT_ID,
            dimensions={
                "dimensions": [
                    {
                        "position_id": _DIM_POSITION,
                        "name_en": _DIM_NAME,
                        "name_fr": _DIM_NAME,
                        "has_uom": False,
                        "members": [
                            {
                                "member_id": _MEMBER_ID,
                                "name_en": _MEMBER_NAME,
                                "name_fr": _MEMBER_NAME,
                            }
                        ],
                    }
                ]
            },
            frequency_code="6",
            cube_title_en="Housing starts",
            cube_title_fr=None,
            fetched_at=datetime.now(timezone.utc),
        )
        session.add(row)
        await session.commit()


async def _seed_semantic_mapping(session_factory) -> None:
    async with session_factory() as session:
        mapping = SemanticMapping(
            cube_id=_CUBE_ID,
            product_id=_PRODUCT_ID,
            semantic_key=_SEMANTIC_KEY,
            label="Housing starts (Canada, total)",
            description=None,
            config={
                "dimension_filters": {_DIM_NAME: _MEMBER_NAME},
                "measure": "Value",
                "unit": "units",
                "frequency": "monthly",
            },
            is_active=True,
            version=1,
        )
        session.add(mapping)
        await session.commit()


async def _seed_cache_row(session_factory, *, value: Decimal = _VALUE_INITIAL) -> None:
    async with session_factory() as session:
        row = SemanticValueCache(
            cube_id=_CUBE_ID,
            product_id=_PRODUCT_ID,
            semantic_key=_SEMANTIC_KEY,
            coord=_COORD,
            ref_period=_PERIOD,
            period_start=None,
            value=value,
            missing=False,
            decimals=0,
            scalar_factor_code=0,
            symbol_code=0,
            security_level_code=0,
            status_code=0,
            frequency_code=6,
            vector_id=None,
            response_status_code=None,
            source_hash=_SOURCE_HASH,
            fetched_at=datetime.now(timezone.utc),
            release_time=None,
            is_stale=False,
        )
        session.add(row)
        await session.commit()


async def _mutate_cache_value(session_factory, *, new_value: Decimal) -> None:
    async with session_factory() as session:
        await session.execute(
            update(SemanticValueCache)
            .where(SemanticValueCache.cube_id == _CUBE_ID)
            .where(SemanticValueCache.semantic_key == _SEMANTIC_KEY)
            .where(SemanticValueCache.coord == _COORD)
            .where(SemanticValueCache.ref_period == _PERIOD)
            .values(value=new_value)
        )
        await session.commit()


async def _seed_draft_publication(session_factory) -> int:
    async with session_factory() as session:
        lineage_key = generate_lineage_key()
        pub = Publication(
            headline="Pipeline test publication",
            chart_type="bar",
            status=PublicationStatus.DRAFT,
            lineage_key=lineage_key,
            slug=f"pipeline-{lineage_key}",
        )
        session.add(pub)
        await session.commit()
        return pub.id


# ---------------------------------------------------------------------------
# App builder — wires the REAL ResolveService composition graph against the
# per-test session_factory. StatCanClient is a stub that errors out if
# touched (cache hit must short-circuit before any network call).
# ---------------------------------------------------------------------------


class _AssertNoNetworkClient:
    """Stub StatCanClient: raises if any method is invoked.

    The pipeline test relies on cache-hit short-circuiting at step 4 of
    the resolve state machine. If ResolveService falls through to
    auto-prime, the test is structurally wrong — re-seed.
    """

    def __getattr__(self, name: str) -> Any:
        async def _raise(*_a: Any, **_kw: Any) -> Any:
            raise AssertionError(
                f"StatCanClient.{name} called — pipeline test requires cache hit"
            )
        return _raise


def _build_app(session_factory) -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(router)

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    def _override_resolve_service() -> ResolveService:
        client = _AssertNoNetworkClient()
        metadata_cache = StatCanMetadataCacheService(
            session_factory=session_factory,
            client=client,  # type: ignore[arg-type]
            clock=lambda: datetime.now(timezone.utc),
            logger=structlog.get_logger(module="test.metadata_cache"),
        )
        value_cache = StatCanValueCacheService(
            session_factory=session_factory,
            repository_factory=lambda s: SemanticValueCacheRepository(s),
            mapping_repository_factory=lambda s: SemanticMappingRepository(s),
            cube_metadata_cache=metadata_cache,
            statcan_client=client,  # type: ignore[arg-type]
            clock=lambda: datetime.now(timezone.utc),
            logger=structlog.get_logger(module="test.value_cache"),
        )
        return ResolveService(
            session_factory=session_factory,
            mapping_repository_factory=SemanticMappingRepository,
            value_cache_service=value_cache,
            metadata_cache=metadata_cache,
            logger=structlog.get_logger(module="test.resolve"),
        )

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[_get_resolve_service] = _override_resolve_service

    app.add_middleware(AuthMiddleware, admin_api_key="test-admin-key")
    return app


def _auth_headers() -> dict[str, str]:
    return {"X-API-KEY": "test-admin-key"}


# ---------------------------------------------------------------------------
# Pipeline test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_publish_then_compare_full_pipeline(session_factory) -> None:
    """End-to-end: publish → capture → compare-fresh → drift → compare-stale."""
    await _seed_cube_metadata(session_factory)
    await _seed_semantic_mapping(session_factory)
    await _seed_cache_row(session_factory, value=_VALUE_INITIAL)
    pub_id = await _seed_draft_publication(session_factory)

    app = _build_app(session_factory)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Step 1 — publish with bound_blocks
        publish_resp = await client.post(
            f"/api/v1/admin/publications/{pub_id}/publish",
            headers=_auth_headers(),
            json={
                "bound_blocks": [
                    {
                        "block_id": "block-1",
                        "cube_id": _CUBE_ID,
                        "semantic_key": _SEMANTIC_KEY,
                        "dims": [_DIM_POSITION],
                        "members": [_MEMBER_ID],
                        "period": _PERIOD,
                    }
                ]
            },
        )
        assert publish_resp.status_code == 200, publish_resp.text
        assert publish_resp.json()["status"] == "PUBLISHED"

        # Step 2 — verify snapshot captured with the full fingerprint
        async with session_factory() as session:
            result = await session.execute(
                select(PublicationBlockSnapshot).where(
                    PublicationBlockSnapshot.publication_id == pub_id
                )
            )
            snapshots = list(result.scalars().all())
        assert len(snapshots) == 1
        snap = snapshots[0]
        assert snap.block_id == "block-1"
        assert snap.cube_id == _CUBE_ID
        assert snap.semantic_key == _SEMANTIC_KEY
        assert snap.coord == _COORD
        assert snap.period == _PERIOD
        assert snap.value_at_publish == str(_VALUE_INITIAL)
        assert snap.source_hash_at_publish == _SOURCE_HASH
        assert snap.mapping_version_at_publish == 1
        assert snap.missing_at_publish is False
        assert snap.is_stale_at_publish is False

        # Step 3 — compare returns fresh
        compare_fresh_resp = await client.post(
            f"/api/v1/admin/publications/{pub_id}/compare",
            headers=_auth_headers(),
        )
        assert compare_fresh_resp.status_code == 200, compare_fresh_resp.text
        fresh_data = compare_fresh_resp.json()
        assert fresh_data["overall_status"] == "fresh"
        assert fresh_data["overall_severity"] == "info"
        assert len(fresh_data["block_results"]) == 1
        fresh_block = fresh_data["block_results"][0]
        assert fresh_block["stale_status"] == "fresh"
        assert fresh_block["stale_reasons"] == []
        assert fresh_block["compare_basis"]["compare_kind"] == "drift_check"

        # Step 4 — simulate upstream drift in the cache row
        await _mutate_cache_value(session_factory, new_value=_VALUE_DRIFTED)

        # Step 5 — compare returns stale + value_changed
        compare_stale_resp = await client.post(
            f"/api/v1/admin/publications/{pub_id}/compare",
            headers=_auth_headers(),
        )
        assert compare_stale_resp.status_code == 200, compare_stale_resp.text
        stale_data = compare_stale_resp.json()
        assert stale_data["overall_status"] == "stale"
        stale_block = stale_data["block_results"][0]
        assert stale_block["stale_status"] == "stale"
        assert "value_changed" in stale_block["stale_reasons"]
        assert stale_block["compare_basis"]["compare_kind"] == "drift_check"
        assert "value" in stale_block["compare_basis"]["drift_fields"]
