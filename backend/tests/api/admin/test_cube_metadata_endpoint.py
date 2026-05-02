"""Phase 3.1b: admin cube-metadata endpoint integration tests.

Coverage (3 cases):
    1. GET 200 on cached cube
    2. GET 404 on uncached cube without prime
    3. GET ?prime=true&product_id=N triggers fetch
"""
from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.api.routers.admin_cube_metadata import (
    _get_metadata_cache_service,
    router,
)
from src.services.statcan.metadata_cache import (
    CubeMetadataCacheEntry,
    StatCanMetadataCacheService,
)

_FIXED_FETCHED_AT = datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc)


def _entry() -> CubeMetadataCacheEntry:
    return CubeMetadataCacheEntry(
        cube_id="18-10-0004",
        product_id=18100004,
        dimensions={"dimensions": []},
        frequency_code="6",
        cube_title_en="CPI",
        cube_title_fr="IPC",
        fetched_at=_FIXED_FETCHED_AT,
    )


@pytest.fixture()
def mock_cache() -> AsyncMock:
    return AsyncMock(spec=StatCanMetadataCacheService)


@pytest.fixture()
def app(mock_cache) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[_get_metadata_cache_service] = lambda: mock_cache
    return app


@pytest.fixture()
async def client(app) -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_get_200_on_cached_cube(client, mock_cache):
    mock_cache.get_cached.return_value = _entry()
    resp = await client.get("/api/v1/admin/cube-metadata/18-10-0004")
    assert resp.status_code == 200
    body = resp.json()
    assert body["cube_id"] == "18-10-0004"
    assert body["product_id"] == 18100004
    mock_cache.get_or_fetch.assert_not_called()


@pytest.mark.asyncio
async def test_get_404_on_uncached_cube_without_prime(client, mock_cache):
    mock_cache.get_cached.return_value = None
    resp = await client.get("/api/v1/admin/cube-metadata/18-10-9999")
    assert resp.status_code == 404
    assert resp.json()["detail"]["error_code"] == "CUBE_NOT_IN_CACHE"
    mock_cache.get_or_fetch.assert_not_called()


@pytest.mark.asyncio
async def test_get_with_prime_triggers_fetch(client, mock_cache):
    mock_cache.get_or_fetch.return_value = _entry()
    resp = await client.get(
        "/api/v1/admin/cube-metadata/18-10-0004",
        params={"prime": "true", "product_id": 18100004},
    )
    assert resp.status_code == 200
    mock_cache.get_or_fetch.assert_awaited_once_with("18-10-0004", 18100004)
