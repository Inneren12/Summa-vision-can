"""Tests for the opaque ``document_state`` column on publications.

Covers DEBT-026 closure:

* ``document_state`` round-trips verbatim (no backend parsing).
* Omitting the field from PATCH leaves it unchanged; explicit ``null``
  clears it.
* PATCHing ``document_state`` does NOT trigger workflow-sync logic —
  only the top-level ``review`` field drives status transitions. This
  guard ensures the backend stays opaque to the editor schema.
* Legacy rows (created before the column existed) report
  ``document_state: null`` and remain valid.
* PATCH can update ``document_state`` alongside editorial fields.
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
# Test infrastructure — mirrors test_admin_publications.py conventions.
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


def _make_app(session_factory) -> FastAPI:
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


_BASE_BODY: dict[str, Any] = {
    "headline": "Housing starts hit a record",
    "chart_type": "bar",
    "visual_config": {
        "layout": "single_stat",
        "palette": "housing",
        "background": "gradient_warm",
        "size": "instagram",
    },
}


async def _create_publication(
    client: AsyncClient, **overrides: Any
) -> str:
    body = {**_BASE_BODY, **overrides}
    resp = await client.post(
        "/api/v1/admin/publications",
        json=body,
        headers=_auth_headers(),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


# ---------------------------------------------------------------------------
# 1. Opaque storage round-trip
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_patch_document_state_stores_opaque_string(session_factory) -> None:
    """A PATCH with a JSON string document_state returns the same string."""
    app = _make_app(session_factory)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        pub_id = await _create_publication(client)

        opaque = json.dumps(
            {
                "doc": "arbitrary",
                "blocks": {"b1": {"type": "foo", "props": {"x": 1}}},
                "nested": {"deep": [1, 2, 3]},
            }
        )
        resp = await client.patch(
            f"/api/v1/admin/publications/{pub_id}",
            json={"document_state": opaque},
            headers=_auth_headers(),
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["document_state"] == opaque

        # GET round-trip
        resp = await client.get(
            f"/api/v1/admin/publications/{pub_id}",
            headers=_auth_headers(),
        )
        assert resp.status_code == 200
        assert resp.json()["document_state"] == opaque


# ---------------------------------------------------------------------------
# 2. PATCH semantics — omitted vs explicit null
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_patch_document_state_is_optional(session_factory) -> None:
    """Omitted -> unchanged; explicit null -> cleared."""
    app = _make_app(session_factory)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        pub_id = await _create_publication(client)
        opaque = '{"seed":true}'

        # Seed the column.
        await client.patch(
            f"/api/v1/admin/publications/{pub_id}",
            json={"document_state": opaque},
            headers=_auth_headers(),
        )

        # Omit document_state — must remain.
        resp = await client.patch(
            f"/api/v1/admin/publications/{pub_id}",
            json={"headline": "Updated headline"},
            headers=_auth_headers(),
        )
        assert resp.status_code == 200
        assert resp.json()["document_state"] == opaque
        assert resp.json()["headline"] == "Updated headline"

        # Explicit null clears.
        resp = await client.patch(
            f"/api/v1/admin/publications/{pub_id}",
            json={"document_state": None},
            headers=_auth_headers(),
        )
        assert resp.status_code == 200
        assert resp.json()["document_state"] is None


# ---------------------------------------------------------------------------
# 3. Backend does NOT parse document_state — no workflow sync side-effect
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_patch_document_state_does_not_trigger_workflow_sync(
    session_factory,
) -> None:
    """If document_state embeds a published workflow but the top-level
    review field is absent, status must NOT flip to PUBLISHED. This
    guards against the backend accidentally parsing document_state.
    """
    app = _make_app(session_factory)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        pub_id = await _create_publication(client)

        # Document state references a "published" workflow deep inside,
        # but the PATCH does NOT include a top-level review field.
        trojan = json.dumps(
            {
                "review": {
                    "workflow": "published",
                    "history": [],
                    "comments": [],
                }
            }
        )
        resp = await client.patch(
            f"/api/v1/admin/publications/{pub_id}",
            json={"document_state": trojan},
            headers=_auth_headers(),
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["document_state"] == trojan
        # Status must still be DRAFT — workflow-sync is driven ONLY by
        # the top-level ``review`` field, never by document_state.
        assert data["status"] == "DRAFT"
        assert data["published_at"] is None


# ---------------------------------------------------------------------------
# 4. Legacy rows — created without document_state remain valid
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_legacy_row_document_state_is_null(session_factory) -> None:
    """A publication created without document_state exposes null."""
    app = _make_app(session_factory)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        pub_id = await _create_publication(client)

        resp = await client.get(
            f"/api/v1/admin/publications/{pub_id}",
            headers=_auth_headers(),
        )
        assert resp.status_code == 200
        assert resp.json()["document_state"] is None


# ---------------------------------------------------------------------------
# 5. Combined update — document_state + editorial field
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_patch_document_state_alongside_editorial_fields(
    session_factory,
) -> None:
    """Editorial fields and document_state can be updated in one PATCH."""
    app = _make_app(session_factory)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        pub_id = await _create_publication(client)

        opaque = '{"both":"yes"}'
        resp = await client.patch(
            f"/api/v1/admin/publications/{pub_id}",
            json={
                "headline": "New headline",
                "document_state": opaque,
            },
            headers=_auth_headers(),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["headline"] == "New headline"
        assert data["document_state"] == opaque
