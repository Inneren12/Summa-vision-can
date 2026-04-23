"""Tests for the admin publications router (Editor + Gallery extension).

Covers:
* POST   /api/v1/admin/publications           — create DRAFT
* GET    /api/v1/admin/publications           — list with status filter
* GET    /api/v1/admin/publications/{id}      — fetch single
* PATCH  /api/v1/admin/publications/{id}      — partial update
* POST   /api/v1/admin/publications/{id}/publish    — publish
* POST   /api/v1/admin/publications/{id}/unpublish  — unpublish
* AuthMiddleware rejects requests without ``X-API-KEY``.

The router-level tests stand up a tiny FastAPI app with dependency
overrides and a real (in-memory SQLite) session factory so the
PublicationRepository runs against a fresh schema for each test.
"""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator
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

from sqlalchemy import select

from src.api.routers.admin_publications import (
    _get_audit,
    _get_repo,
    router,
)
from src.api.routers.public_graphics import (
    _get_repo as _get_public_repo,
    _get_storage as _get_public_storage,
    get_gallery_limiter,
    router as public_graphics_router,
)
from src.core.database import Base
from src.core.security.auth import AuthMiddleware
from src.core.security.ip_rate_limiter import InMemoryRateLimiter
from src.core.storage import StorageInterface, StorageObjectMetadata
from src.models.audit_event import AuditEvent
from src.repositories.publication_repository import PublicationRepository
from src.services.audit import AuditWriter


# ---------------------------------------------------------------------------
# Test infrastructure: in-memory engine + session factory per test
# ---------------------------------------------------------------------------


@pytest.fixture()
async def engine() -> AsyncGenerator[AsyncEngine, None]:
    """Create a fresh in-memory SQLite engine with the full schema."""
    eng = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest.fixture()
async def session_factory(engine: AsyncEngine):
    """async_sessionmaker bound to the per-test engine."""
    return async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )


def _make_app(session_factory) -> FastAPI:
    """Build a FastAPI app with the publications router + auth middleware.

    The DI helpers (_get_repo, _get_audit) are overridden so each request
    gets a fresh session backed by the per-test engine.
    """
    app = FastAPI()
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

    app.dependency_overrides[_get_repo] = _override_repo
    app.dependency_overrides[_get_audit] = _override_audit

    app.add_middleware(AuthMiddleware, admin_api_key="test-admin-key")
    return app


def _auth_headers() -> dict[str, str]:
    return {"X-API-KEY": "test-admin-key"}


# ---------------------------------------------------------------------------
# AuthMiddleware
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_without_api_key_returns_401(session_factory) -> None:
    """POST without ``X-API-KEY`` must be rejected by AuthMiddleware."""
    app = _make_app(session_factory)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/admin/publications",
            json={"headline": "x", "chart_type": "bar"},
        )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# POST /api/v1/admin/publications
# ---------------------------------------------------------------------------


_VALID_BODY: dict[str, Any] = {
    "headline": "Housing starts hit a record",
    "chart_type": "bar",
    "eyebrow": "STATCAN · TABLE 18-10-0004",
    "description": "March hit the highest level in five years.",
    "source_text": "Source: Statistics Canada",
    "footnote": "Seasonally adjusted.",
    "visual_config": {
        "layout": "single_stat",
        "palette": "housing",
        "background": "gradient_warm",
        "size": "instagram",
    },
    "virality_score": 0.91,
}


@pytest.mark.asyncio
async def test_create_publication_returns_201_with_id_and_draft(
    session_factory,
) -> None:
    """A valid POST should return HTTP 201 with id and DRAFT status."""
    app = _make_app(session_factory)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/admin/publications",
            json=_VALID_BODY,
            headers=_auth_headers(),
        )

    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["id"]
    assert data["headline"] == "Housing starts hit a record"
    assert data["status"] == "DRAFT"
    assert data["eyebrow"] == "STATCAN · TABLE 18-10-0004"
    assert data["visual_config"]["layout"] == "single_stat"
    assert "cdn_url" in data  # may be null


@pytest.mark.asyncio
async def test_create_publication_invalid_visual_config_returns_422(
    session_factory,
) -> None:
    """Sending a non-object visual_config must be rejected."""
    app = _make_app(session_factory)
    body = dict(_VALID_BODY)
    body["visual_config"] = "not-an-object"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/admin/publications",
            json=body,
            headers=_auth_headers(),
        )

    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# PATCH /api/v1/admin/publications/{id}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_patch_publication_updates_only_provided_fields(
    session_factory,
) -> None:
    """A PATCH request should change only the supplied fields."""
    app = _make_app(session_factory)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create
        resp = await client.post(
            "/api/v1/admin/publications",
            json=_VALID_BODY,
            headers=_auth_headers(),
        )
        pub_id = resp.json()["id"]

        # Patch only the headline
        resp = await client.patch(
            f"/api/v1/admin/publications/{pub_id}",
            json={"headline": "Updated headline"},
            headers=_auth_headers(),
        )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["headline"] == "Updated headline"
    # eyebrow should still be the original
    assert data["eyebrow"] == "STATCAN · TABLE 18-10-0004"


# ---------------------------------------------------------------------------
# POST /api/v1/admin/publications/{id}/publish
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_publish_endpoint_flips_status(session_factory) -> None:
    """Publishing must set status=PUBLISHED and stamp ``published_at``."""
    app = _make_app(session_factory)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/admin/publications",
            json=_VALID_BODY,
            headers=_auth_headers(),
        )
        pub_id = resp.json()["id"]

        resp = await client.post(
            f"/api/v1/admin/publications/{pub_id}/publish",
            headers=_auth_headers(),
        )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "PUBLISHED"
    assert data["published_at"] is not None


# ---------------------------------------------------------------------------
# GET /api/v1/admin/publications?status=draft
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_filters_by_status_draft(session_factory) -> None:
    """``?status=draft`` should return only DRAFT publications."""
    app = _make_app(session_factory)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create two; publish one
        r1 = await client.post(
            "/api/v1/admin/publications",
            json={**_VALID_BODY, "headline": "Draft one"},
            headers=_auth_headers(),
        )
        r2 = await client.post(
            "/api/v1/admin/publications",
            json={**_VALID_BODY, "headline": "To publish"},
            headers=_auth_headers(),
        )
        pub2_id = r2.json()["id"]
        await client.post(
            f"/api/v1/admin/publications/{pub2_id}/publish",
            headers=_auth_headers(),
        )

        resp = await client.get(
            "/api/v1/admin/publications?status=draft",
            headers=_auth_headers(),
        )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert isinstance(data, list)
    assert all(p["status"] == "DRAFT" for p in data)
    # The published one should NOT be in the draft list
    headlines = {p["headline"] for p in data}
    assert "Draft one" in headlines
    assert "To publish" not in headlines


# ---------------------------------------------------------------------------
# GET /api/v1/admin/publications/{nonexistent}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_nonexistent_returns_404(session_factory) -> None:
    """A GET for a missing publication ID must return 404."""
    app = _make_app(session_factory)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/admin/publications/999999",
            headers=_auth_headers(),
        )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Round-trip — visual_config is preserved across create + read
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_visual_config_round_trip(session_factory) -> None:
    """visual_config submitted on create must round-trip on subsequent GET."""
    app = _make_app(session_factory)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/admin/publications",
            json=_VALID_BODY,
            headers=_auth_headers(),
        )
        pub_id = resp.json()["id"]

        resp = await client.get(
            f"/api/v1/admin/publications/{pub_id}",
            headers=_auth_headers(),
        )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["visual_config"]["palette"] == "housing"
    assert data["visual_config"]["background"] == "gradient_warm"


# ---------------------------------------------------------------------------
# Unpublish
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unpublish_reverts_to_draft(session_factory) -> None:
    """Unpublishing must flip status back to DRAFT."""
    app = _make_app(session_factory)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/admin/publications",
            json=_VALID_BODY,
            headers=_auth_headers(),
        )
        pub_id = resp.json()["id"]

        await client.post(
            f"/api/v1/admin/publications/{pub_id}/publish",
            headers=_auth_headers(),
        )
        resp = await client.post(
            f"/api/v1/admin/publications/{pub_id}/unpublish",
            headers=_auth_headers(),
        )

    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "DRAFT"


# ---------------------------------------------------------------------------
# Unpublish — audit symmetry with publish (FIX 2)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unpublish_writes_audit_event(session_factory) -> None:
    """Unpublish must emit an audit event mirroring the publish lifecycle.

    Admin lifecycle actions are symmetrically audited. There is no
    dedicated ``PUBLICATION_UNPUBLISHED`` enum member, so the router
    reuses ``PUBLICATION_PUBLISHED`` with ``metadata.action='unpublish'``
    as the distinguishing marker for dashboards.
    """
    app = _make_app(session_factory)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/admin/publications",
            json=_VALID_BODY,
            headers=_auth_headers(),
        )
        pub_id = resp.json()["id"]

        await client.post(
            f"/api/v1/admin/publications/{pub_id}/publish",
            headers=_auth_headers(),
        )
        resp = await client.post(
            f"/api/v1/admin/publications/{pub_id}/unpublish",
            headers=_auth_headers(),
        )
        assert resp.status_code == 200, resp.text

    # Inspect the audit trail directly via a fresh session.
    async with session_factory() as session:
        result = await session.execute(
            select(AuditEvent).where(AuditEvent.entity_id == str(pub_id))
        )
        events = list(result.scalars().all())

    assert len(events) == 2, f"expected publish+unpublish events, got {events}"
    # Both events share the same type; unpublish carries the 'action' marker.
    unpublish_events = [
        e for e in events if e.metadata_json and "unpublish" in e.metadata_json
    ]
    assert len(unpublish_events) == 1
    unpublish_event = unpublish_events[0]
    assert unpublish_event.event_type == "publication.published"
    assert unpublish_event.entity_type == "publication"
    assert unpublish_event.entity_id == str(pub_id)
    metadata = json.loads(unpublish_event.metadata_json)
    assert metadata["action"] == "unpublish"
    assert metadata["new_status"] == "DRAFT"


# ---------------------------------------------------------------------------
# PATCH — clearing nullable fields with explicit null (FIX 4)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_patch_clear_nullable_field_with_null(session_factory) -> None:
    """Explicit ``null`` in the PATCH body clears the column.

    Contract:
    * Field omitted from the JSON body → column unchanged.
    * Field sent as ``null`` → column cleared (set to NULL).
    * Field sent with a value → column updated.

    Drives the ``exclude_unset=True`` + repository apply-all-keys fix.
    """
    app = _make_app(session_factory)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create with footnote + description set.
        resp = await client.post(
            "/api/v1/admin/publications",
            json={
                **_VALID_BODY,
                "headline": "Clearable",
                "footnote": "Seasonally adjusted.",
                "description": "A description to preserve.",
            },
            headers=_auth_headers(),
        )
        assert resp.status_code == 201, resp.text
        pub_id = resp.json()["id"]
        assert resp.json()["footnote"] == "Seasonally adjusted."

        # PATCH: clear footnote via explicit null, leave everything else alone.
        resp = await client.patch(
            f"/api/v1/admin/publications/{pub_id}",
            json={"footnote": None},
            headers=_auth_headers(),
        )
        assert resp.status_code == 200, resp.text
        patched = resp.json()
        assert patched["footnote"] is None
        # Omitted fields must remain unchanged.
        assert patched["description"] == "A description to preserve."
        assert patched["eyebrow"] == _VALID_BODY["eyebrow"]

        # Re-fetch to confirm persistence.
        resp = await client.get(
            f"/api/v1/admin/publications/{pub_id}",
            headers=_auth_headers(),
        )
        assert resp.status_code == 200
        fetched = resp.json()
        assert fetched["footnote"] is None
        assert fetched["description"] == "A description to preserve."


@pytest.mark.asyncio
async def test_patch_unknown_field_rejected(session_factory) -> None:
    """``extra='forbid'`` on PublicationUpdate rejects typos with 422."""
    app = _make_app(session_factory)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/admin/publications",
            json=_VALID_BODY,
            headers=_auth_headers(),
        )
        pub_id = resp.json()["id"]

        # Deliberate typo — should be rejected rather than silently ignored.
        resp = await client.patch(
            f"/api/v1/admin/publications/{pub_id}",
            json={"eybrow": "TYPO"},
            headers=_auth_headers(),
        )

    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Public gallery contract test (FIX 1 + FIX 3)
# ---------------------------------------------------------------------------


class _ContractTestStorage(StorageInterface):
    """Tiny mock storage for the public gallery contract test."""

    async def upload_bytes(self, data: bytes, key: str) -> None:
        pass

    async def download_bytes(self, key: str) -> bytes:  # pragma: no cover
        return b""

    async def upload_dataframe_as_csv(self, df: Any, path: str) -> None:
        pass

    async def upload_raw(
        self, data: str | bytes, path: str, content_type: str = "text/html"
    ) -> None:
        pass

    async def download_csv(self, path: str) -> Any:  # pragma: no cover
        import pandas as pd

        return pd.DataFrame()

    async def list_objects(self, prefix: str) -> list[str]:
        return []

    async def list_objects_with_metadata(
        self, prefix: str
    ) -> list[StorageObjectMetadata]:
        return []

    async def generate_presigned_url(self, path: str, ttl: int = 3600) -> str:
        return f"https://cdn.example.test/{path}?ttl={ttl}"

    async def delete_object(self, key: str) -> None:
        pass


def _make_admin_and_public_app(session_factory):
    """Build an app with BOTH admin + public routers sharing one DB."""
    app = FastAPI()
    app.include_router(router)
    app.include_router(public_graphics_router)

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

    app.dependency_overrides[_get_repo] = _override_repo
    app.dependency_overrides[_get_audit] = _override_audit
    # Public router uses its own dependency symbols — override them too so
    # requests hit the same per-test DB / session factory.
    app.dependency_overrides[_get_public_repo] = _override_repo
    app.dependency_overrides[_get_public_storage] = lambda: _ContractTestStorage()
    # Use an isolated limiter so other tests don't consume quota.
    app.dependency_overrides[get_gallery_limiter] = lambda: InMemoryRateLimiter(
        max_requests=1000, window_seconds=60
    )

    app.add_middleware(AuthMiddleware, admin_api_key="test-admin-key")
    return app


@pytest.mark.asyncio
async def test_public_gallery_includes_editorial_excludes_visual_config(
    session_factory,
) -> None:
    """Public gallery must expose editorial fields but not visual_config.

    End-to-end contract:
    1. Admin creates a publication with the full editorial set + a
       ``visual_config`` block.
    2. Admin publishes it.
    3. Public endpoint lists it.
    4. Editorial fields are present; ``visual_config`` is omitted;
       ``s3_key_*`` are omitted.
    """
    app = _make_admin_and_public_app(session_factory)
    transport = ASGITransport(app=app)
    create_payload: dict[str, Any] = {
        "headline": "Test Editorial",
        "chart_type": "BAR",
        "eyebrow": "STATISTICS CANADA",
        "description": "Test description for gallery",
        "source_text": "Source: StatCan",
        "footnote": "Seasonally adjusted",
        "visual_config": {
            "layout": "bar_editorial",
            "palette": "housing",
            "background": "gradient_warm",
            "size": "instagram",
            "branding": {
                "show_top_accent": True,
                "show_corner_mark": True,
                "accent_color": "#FBBF24",
            },
        },
    }

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create via admin
        resp = await client.post(
            "/api/v1/admin/publications",
            json=create_payload,
            headers=_auth_headers(),
        )
        assert resp.status_code == 201, resp.text
        pub_id = resp.json()["id"]

        # 2. Publish via admin
        resp = await client.post(
            f"/api/v1/admin/publications/{pub_id}/publish",
            headers=_auth_headers(),
        )
        assert resp.status_code == 200, resp.text

        # 3. Fetch public gallery (no auth)
        resp = await client.get("/api/v1/public/graphics")
        assert resp.status_code == 200, resp.text

    body = resp.json()
    items = body["items"]
    assert len(items) == 1
    pub = items[0]

    # 4a. Editorial fields are present.
    assert pub["headline"] == "Test Editorial"
    assert pub["eyebrow"] == "STATISTICS CANADA"
    assert pub["description"] == "Test description for gallery"
    assert pub["source_text"] == "Source: StatCan"
    assert pub["footnote"] == "Seasonally adjusted"
    # Lifecycle timestamps are exposed.
    assert "updated_at" in pub
    assert "published_at" in pub
    assert pub["published_at"] is not None

    # 4b. Admin-only / internal fields must NOT be exposed.
    assert "visual_config" not in pub
    assert "s3_key_lowres" not in pub
    assert "s3_key_highres" not in pub
