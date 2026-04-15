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

from src.api.routers.admin_publications import (
    _get_audit,
    _get_repo,
    router,
)
from src.core.database import Base
from src.core.security.auth import AuthMiddleware
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
