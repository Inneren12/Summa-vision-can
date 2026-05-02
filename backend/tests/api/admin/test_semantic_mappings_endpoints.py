"""Phase 3.1b: admin semantic-mappings endpoint integration tests.

Tests stand up a tiny FastAPI app with dependency overrides and a real
in-memory SQLite session factory; the StatCan metadata cache is replaced
with an :class:`AsyncMock` so no network I/O is triggered.

Coverage (9 cases):
    1. POST upsert success → 201 on new
    2. POST upsert success → 200 on update
    3. POST upsert → 400 envelope on member-not-found
    4. POST upsert → 412 on If-Match header mismatch
    5. POST upsert → 412 on if_match_version body mismatch
    6. POST upsert: header takes precedence over body when both supplied
    7. GET list with cube_id filter
    8. GET /{id} → 404 on miss
    9. DELETE /{id} → soft-deletes (idempotent)
"""
from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock

import pytest
import structlog
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.api.dependencies.statcan import get_statcan_metadata_cache_service
from src.api.routers.admin_semantic_mappings import (
    _get_service,
    _get_session_factory,
    router,
)
from src.core.database import Base
from src.repositories.semantic_mapping_repository import (
    SemanticMappingRepository,
)
from src.services.semantic_mappings.service import SemanticMappingService
from src.services.statcan.metadata_cache import (
    CubeMetadataCacheEntry,
    StatCanMetadataCacheService,
)


_FIXED_FETCHED_AT = datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc)


def _cache_entry(*, product_id: int = 18100004) -> CubeMetadataCacheEntry:
    return CubeMetadataCacheEntry(
        cube_id="18-10-0004",
        product_id=product_id,
        dimensions={
            "dimensions": [
                {
                    "position_id": 1,
                    "name_en": "Geography",
                    "name_fr": "Géographie",
                    "has_uom": False,
                    "members": [
                        {"member_id": 1, "name_en": "Canada", "name_fr": "Canada"},
                    ],
                },
                {
                    "position_id": 2,
                    "name_en": "Products",
                    "name_fr": "Produits",
                    "has_uom": False,
                    "members": [
                        {
                            "member_id": 10,
                            "name_en": "All-items",
                            "name_fr": "Ensemble",
                        },
                    ],
                },
            ]
        },
        frequency_code="6",
        cube_title_en="CPI",
        cube_title_fr="IPC",
        fetched_at=_FIXED_FETCHED_AT,
    )


def _valid_body(**overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "cube_id": "18-10-0004",
        "product_id": 18100004,
        "semantic_key": "cpi.canada.all_items.index",
        "label": "CPI — Canada, all-items",
        "description": "headline",
        "config": {
            "dimension_filters": {
                "Geography": "Canada",
                "Products": "All-items",
            },
            "measure": "Value",
            "unit": "index",
            "frequency": "monthly",
            "supported_metrics": ["current_value"],
            "default_geo": "Canada",
        },
        "is_active": True,
        "updated_by": "alice",
    }
    body.update(overrides)
    return body


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
async def session_factory(
    engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )


@pytest.fixture()
def mock_cache() -> AsyncMock:
    return AsyncMock(spec=StatCanMetadataCacheService)


@pytest.fixture()
def app(session_factory, mock_cache) -> FastAPI:
    app = FastAPI()
    app.include_router(router)

    def _override_factory():
        return session_factory

    def _override_cache():
        return mock_cache

    def _override_service():
        return SemanticMappingService(
            session_factory=session_factory,
            repository_factory=SemanticMappingRepository,
            metadata_cache=mock_cache,
            logger=structlog.get_logger(),
        )

    app.dependency_overrides[_get_session_factory] = _override_factory
    app.dependency_overrides[get_statcan_metadata_cache_service] = (
        _override_cache
    )
    app.dependency_overrides[_get_service] = _override_service
    return app


@pytest.fixture()
async def client(app) -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upsert_returns_201_on_new(client, mock_cache):
    mock_cache.get_or_fetch.return_value = _cache_entry()
    resp = await client.post(
        "/api/v1/admin/semantic-mappings/upsert", json=_valid_body()
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["cube_id"] == "18-10-0004"
    assert body["semantic_key"] == "cpi.canada.all_items.index"
    assert body["version"] == 1


@pytest.mark.asyncio
async def test_upsert_returns_200_on_update(client, mock_cache):
    mock_cache.get_or_fetch.return_value = _cache_entry()
    first = await client.post(
        "/api/v1/admin/semantic-mappings/upsert", json=_valid_body()
    )
    assert first.status_code == 201
    second = await client.post(
        "/api/v1/admin/semantic-mappings/upsert",
        json=_valid_body(label="CPI — Canada, all-items (updated)"),
    )
    assert second.status_code == 200, second.text
    assert second.json()["label"].endswith("(updated)")
    assert second.json()["version"] == 2


@pytest.mark.asyncio
async def test_upsert_returns_400_envelope_on_member_not_found(client, mock_cache):
    mock_cache.get_or_fetch.return_value = _cache_entry()
    body = _valid_body()
    body["config"]["dimension_filters"] = {"Geography": "Atlantis"}
    resp = await client.post(
        "/api/v1/admin/semantic-mappings/upsert", json=body
    )
    assert resp.status_code == 400
    detail = resp.json()["detail"]
    assert detail["error_code"] == "MEMBER_NOT_FOUND"
    assert any(
        e["error_code"] == "MEMBER_NOT_FOUND" for e in detail["details"]["errors"]
    )


@pytest.mark.asyncio
async def test_upsert_returns_412_on_if_match_header_mismatch(client, mock_cache):
    mock_cache.get_or_fetch.return_value = _cache_entry()
    first = await client.post(
        "/api/v1/admin/semantic-mappings/upsert", json=_valid_body()
    )
    assert first.status_code == 201
    # Existing version is 1; client claims it is 99.
    resp = await client.post(
        "/api/v1/admin/semantic-mappings/upsert",
        json=_valid_body(label="x"),
        headers={"If-Match": "99"},
    )
    assert resp.status_code == 412, resp.text
    detail = resp.json()["detail"]
    assert detail["error_code"] == "VERSION_CONFLICT"
    assert detail["details"]["expected_version"] == 99
    assert detail["details"]["actual_version"] == 1


@pytest.mark.asyncio
async def test_upsert_returns_412_on_if_match_body_field_mismatch(
    client, mock_cache
):
    mock_cache.get_or_fetch.return_value = _cache_entry()
    first = await client.post(
        "/api/v1/admin/semantic-mappings/upsert", json=_valid_body()
    )
    assert first.status_code == 201
    resp = await client.post(
        "/api/v1/admin/semantic-mappings/upsert",
        json=_valid_body(label="x", if_match_version=99),
    )
    assert resp.status_code == 412, resp.text
    assert resp.json()["detail"]["error_code"] == "VERSION_CONFLICT"


@pytest.mark.asyncio
async def test_upsert_header_takes_precedence_over_body_field(client, mock_cache):
    """Header wins when both are supplied: header=1 (matches), body=99
    (would mismatch). A success here proves header took precedence."""
    mock_cache.get_or_fetch.return_value = _cache_entry()
    first = await client.post(
        "/api/v1/admin/semantic-mappings/upsert", json=_valid_body()
    )
    assert first.status_code == 201
    resp = await client.post(
        "/api/v1/admin/semantic-mappings/upsert",
        json=_valid_body(label="updated", if_match_version=99),
        headers={"If-Match": "1"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["label"] == "updated"


@pytest.mark.asyncio
async def test_list_with_cube_id_filter(client, mock_cache):
    mock_cache.get_or_fetch.return_value = _cache_entry()
    await client.post(
        "/api/v1/admin/semantic-mappings/upsert", json=_valid_body()
    )
    resp = await client.get(
        "/api/v1/admin/semantic-mappings", params={"cube_id": "18-10-0004"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1
    assert body["items"][0]["cube_id"] == "18-10-0004"

    # Filter on a non-existent cube → empty page.
    resp_empty = await client.get(
        "/api/v1/admin/semantic-mappings", params={"cube_id": "does-not-exist"}
    )
    assert resp_empty.status_code == 200
    assert resp_empty.json()["total"] == 0


@pytest.mark.asyncio
async def test_get_by_id_returns_404_on_miss(client):
    resp = await client.get("/api/v1/admin/semantic-mappings/9999")
    assert resp.status_code == 404
    assert resp.json()["detail"]["error_code"] == "MAPPING_NOT_FOUND"


@pytest.mark.asyncio
async def test_delete_soft_deletes_idempotently(client, mock_cache):
    mock_cache.get_or_fetch.return_value = _cache_entry()
    created = await client.post(
        "/api/v1/admin/semantic-mappings/upsert", json=_valid_body()
    )
    mapping_id = created.json()["id"]

    first_delete = await client.delete(
        f"/api/v1/admin/semantic-mappings/{mapping_id}"
    )
    assert first_delete.status_code == 200
    assert first_delete.json()["is_active"] is False
    version_after_first = first_delete.json()["version"]

    # Second delete is a no-op idempotent: still 200, same is_active=false,
    # version unchanged (no version bump).
    second_delete = await client.delete(
        f"/api/v1/admin/semantic-mappings/{mapping_id}"
    )
    assert second_delete.status_code == 200
    assert second_delete.json()["is_active"] is False
    assert second_delete.json()["version"] == version_after_first


# ---------------------------------------------------------------------------
# Phase 3.1b fix R1 — strict INVALID_IF_MATCH on malformed header
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_post_upsert_returns_400_invalid_if_match_when_header_malformed_and_no_body(
    client, mock_cache,
):
    """Reviewer R1 P1: malformed If-Match header is rejected, not silently ignored."""
    mock_cache.get_or_fetch.return_value = _cache_entry()
    resp = await client.post(
        "/api/v1/admin/semantic-mappings/upsert",
        json=_valid_body(),
        headers={"If-Match": "abc"},
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()["detail"]["error_code"] == "INVALID_IF_MATCH"


@pytest.mark.asyncio
async def test_post_upsert_returns_400_invalid_if_match_when_header_malformed_even_with_body(
    client, mock_cache,
):
    """Malformed header MUST NOT silently fall through to the body field.

    The header explicitly invokes the concurrency contract; if it cannot be
    parsed, the request is broken regardless of what the body says.
    """
    mock_cache.get_or_fetch.return_value = _cache_entry()
    resp = await client.post(
        "/api/v1/admin/semantic-mappings/upsert",
        json=_valid_body(if_match_version=1),
        headers={"If-Match": "abc"},
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()["detail"]["error_code"] == "INVALID_IF_MATCH"


@pytest.mark.asyncio
async def test_post_upsert_resolves_weak_etag_header_w_prefix(client, mock_cache):
    """``W/"1"`` must parse as version 1 — verifies the strip-W/-and-quotes path."""
    mock_cache.get_or_fetch.return_value = _cache_entry()
    first = await client.post(
        "/api/v1/admin/semantic-mappings/upsert", json=_valid_body()
    )
    assert first.status_code == 201
    # Existing version is 1; weak-ETag form ``W/"1"`` should match.
    resp = await client.post(
        "/api/v1/admin/semantic-mappings/upsert",
        json=_valid_body(label="updated-via-weak-etag"),
        headers={"If-Match": 'W/"1"'},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["label"] == "updated-via-weak-etag"
