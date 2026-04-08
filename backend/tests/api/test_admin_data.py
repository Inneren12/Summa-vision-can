"""Tests for admin data endpoints: fetch, transform, preview.

Uses AsyncClient with mocked storage on app.state.
"""

from __future__ import annotations

import io
import json
from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import patch

from src.main import app
from src.core.database import get_db

API_KEY = {"X-API-KEY": "test-ci-key"}

@pytest.fixture
async def client_no_auth(db_session: AsyncSession) -> AsyncClient:
    """Provide an AsyncClient without auth headers, for auth testing."""
    app.dependency_overrides[get_db] = lambda: db_session
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def _set_test_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set the API key in the environment and app settings before tests run."""
    monkeypatch.setenv("ADMIN_API_KEY", "test-ci-key")
    from src.main import settings_on_startup
    settings_on_startup.admin_api_key = "test-ci-key"

    # TODO: Replace middleware kwargs mutation with app factory / DI-based auth override.
    # Current approach depends on Starlette internals and is fragile.
    for middleware in app.user_middleware:
        if hasattr(middleware, 'kwargs') and 'admin_api_key' in middleware.kwargs:
            middleware.kwargs['admin_api_key'] = "test-ci-key"


@pytest.fixture
async def client(client_no_auth: AsyncClient) -> AsyncClient:
    """Provide an AsyncClient with the correct test auth headers."""
    client_no_auth.headers.update(API_KEY)
    yield client_no_auth


# ---- Helpers ----

def _sample_parquet_bytes() -> bytes:
    """Create Parquet bytes from a sample DataFrame."""
    df = pl.DataFrame({
        "REF_DATE": [f"2024-{m:02d}-01" for m in range(1, 13)],
        "GEO": ["Canada"] * 12,
        "VALUE": [100.0 + i * 2 for i in range(12)],
    })
    buf = io.BytesIO()
    df.write_parquet(buf)
    return buf.getvalue()


# ---- POST /cubes/{product_id}/fetch ----

@pytest.mark.asyncio
async def test_fetch_returns_202(client: AsyncClient) -> None:
    """POST /cubes/{product_id}/fetch creates job → 202."""
    resp = await client.post(
        "/api/v1/admin/cubes/test-product/fetch",
        headers=API_KEY,
    )
    assert resp.status_code == 202
    data = resp.json()
    assert "job_id" in data
    assert data["product_id"] == "test-product"


@pytest.mark.asyncio
async def test_fetch_dedupe_same_day(client: AsyncClient) -> None:
    """Two fetches for same product on same day → same job_id."""
    resp1 = await client.post(
        "/api/v1/admin/cubes/test-product/fetch",
        headers=API_KEY,
    )
    resp2 = await client.post(
        "/api/v1/admin/cubes/test-product/fetch",
        headers=API_KEY,
    )
    assert resp1.json()["job_id"] == resp2.json()["job_id"]


@pytest.mark.asyncio
async def test_fetch_requires_auth(client_no_auth: AsyncClient) -> None:
    """POST /fetch without API key → 401."""
    resp = await client_no_auth.post("/api/v1/admin/cubes/test/fetch")
    assert resp.status_code == 401


# ---- POST /data/transform ----

@pytest.mark.asyncio
async def test_transform_returns_output_key(
    client: AsyncClient,
) -> None:
    """Transform returns Parquet storage key, not full data."""
    # Mock storage to return sample parquet and accept uploads
    parquet = _sample_parquet_bytes()

    mock_storage = AsyncMock()
    mock_storage.download_bytes = AsyncMock(return_value=parquet)
    mock_storage.upload_bytes = AsyncMock()

    # Patch app.state.storage
    with patch.object(
        client._transport.app.state, "storage", mock_storage, create=True  # type: ignore
    ):
        resp = await client.post(
            "/api/v1/admin/data/transform",
            headers=API_KEY,
            json={
                "source_keys": ["statcan/processed/test/2024-01-01.parquet"],
                "operations": [
                    {"type": "filter_geo", "params": {"geography": "Canada"}},
                ],
            },
        )

    assert resp.status_code == 200
    data = resp.json()
    assert "output_key" in data
    assert data["output_key"].endswith(".parquet")
    assert "rows" in data
    assert "columns" in data


@pytest.mark.asyncio
async def test_transform_unknown_operation_returns_422(
    client: AsyncClient,
) -> None:
    """Unknown transform type → 422."""
    parquet = _sample_parquet_bytes()
    mock_storage = AsyncMock()
    mock_storage.download_bytes = AsyncMock(return_value=parquet)

    with patch.object(
        client._transport.app.state, "storage", mock_storage, create=True  # type: ignore
    ):
        resp = await client.post(
            "/api/v1/admin/data/transform",
            headers=API_KEY,
            json={
                "source_keys": ["test.parquet"],
                "operations": [
                    {"type": "nonexistent_function", "params": {}},
                ],
            },
        )

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_transform_requires_auth(client_no_auth: AsyncClient) -> None:
    """POST /data/transform without API key → 401."""
    resp = await client_no_auth.post(
        "/api/v1/admin/data/transform",
        json={"source_keys": ["x"], "operations": [{"type": "y", "params": {}}]},
    )
    assert resp.status_code == 401


# ---- GET /data/preview ----

@pytest.mark.asyncio
async def test_preview_returns_data(client: AsyncClient) -> None:
    """Preview returns rows as typed JSON."""
    parquet = _sample_parquet_bytes()
    mock_storage = AsyncMock()
    mock_storage.download_bytes = AsyncMock(return_value=parquet)

    with patch.object(
        client._transport.app.state, "storage", mock_storage, create=True  # type: ignore
    ):
        resp = await client.get(
            "/api/v1/admin/data/preview/statcan/processed/test.parquet",
            headers=API_KEY,
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["rows"] <= 100  # capped
    assert "column_names" in data
    assert "data" in data
    assert len(data["data"]) > 0
    assert "VALUE" in data["column_names"]


@pytest.mark.asyncio
async def test_preview_respects_limit(client: AsyncClient) -> None:
    """Preview with limit=3 returns at most 3 rows."""
    parquet = _sample_parquet_bytes()
    mock_storage = AsyncMock()
    mock_storage.download_bytes = AsyncMock(return_value=parquet)

    with patch.object(
        client._transport.app.state, "storage", mock_storage, create=True  # type: ignore
    ):
        resp = await client.get(
            "/api/v1/admin/data/preview/test.parquet?limit=3",
            headers=API_KEY,
        )

    assert resp.status_code == 200
    assert resp.json()["rows"] <= 3


@pytest.mark.asyncio
async def test_preview_not_found(client: AsyncClient) -> None:
    """Preview of nonexistent key → 404."""
    mock_storage = AsyncMock()
    mock_storage.download_bytes = AsyncMock(side_effect=FileNotFoundError)

    with patch.object(
        client._transport.app.state, "storage", mock_storage, create=True  # type: ignore
    ):
        resp = await client.get(
            "/api/v1/admin/data/preview/nonexistent.parquet",
            headers=API_KEY,
        )

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_preview_requires_auth(client_no_auth: AsyncClient) -> None:
    """GET /data/preview without API key → 401."""
    resp = await client_no_auth.get("/api/v1/admin/data/preview/test.parquet")
    assert resp.status_code == 401
