"""Tests for admin cube catalog endpoints.

Tests use the ``client`` fixture (AsyncClient with ASGITransport).
CubeCatalog records are created via repository in test setup.
Auth is handled by providing X-API-KEY header.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.main import app
from src.models.cube_catalog import CubeCatalog
from src.repositories.cube_catalog_repository import CubeCatalogRepository
from src.schemas.cube_catalog import CubeCatalogCreate
from src.core.database import get_db

# ---- Helpers ----

API_KEY_HEADER = {"X-API-KEY": "test-secret-key"}

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
    monkeypatch.setenv("ADMIN_API_KEY", "test-secret-key")
    from src.main import settings_on_startup
    settings_on_startup.admin_api_key = "test-secret-key"

    for middleware in app.user_middleware:
        if hasattr(middleware, 'kwargs') and 'admin_api_key' in middleware.kwargs:
            middleware.kwargs['admin_api_key'] = "test-secret-key"


@pytest.fixture
async def client(client_no_auth: AsyncClient) -> AsyncClient:
    """Provide an AsyncClient with the correct test auth headers."""
    client_no_auth.headers.update(API_KEY_HEADER)
    yield client_no_auth


async def _seed_cubes(
    session: AsyncSession,
    count: int = 3,
) -> list[CubeCatalog]:
    """Insert test cubes into DB."""
    repo = CubeCatalogRepository(session)
    cubes = [
        CubeCatalogCreate(
            product_id=f"14-10-{i:04d}-01",
            cube_id_statcan=14100000 + i,
            title_en=f"Vacancy rates for rental apartments table {i}",
            subject_code="46",
            subject_en="Housing",
            frequency="Monthly",
        )
        for i in range(count)
    ]
    await repo.upsert_batch(cubes)
    await session.commit()

    result = []
    for c in cubes:
        record = await repo.get_by_product_id(c.product_id)
        if record:
            result.append(record)
    return result


# ---- Search ----

async def test_search_returns_results(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """GET /search?q=vacancy returns matching cubes."""
    await _seed_cubes(db_session)

    resp = await client.get(
        "/api/v1/admin/cubes/search",
        params={"q": "vacancy"},
        headers=API_KEY_HEADER,
    )

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert "product_id" in data[0]
    assert "title_en" in data[0]


async def test_search_empty_query_returns_422(
    client: AsyncClient,
) -> None:
    """GET /search without q param returns 422."""
    resp = await client.get(
        "/api/v1/admin/cubes/search",
        headers=API_KEY_HEADER,
    )
    assert resp.status_code == 422


async def test_search_whitespace_only_returns_422(
    client: AsyncClient,
) -> None:
    """GET /search?q=   (whitespace) returns 422."""
    resp = await client.get(
        "/api/v1/admin/cubes/search",
        params={"q": "   "},
        headers=API_KEY_HEADER,
    )
    assert resp.status_code == 422


async def test_search_respects_limit(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """GET /search?q=vacancy&limit=1 returns at most 1."""
    await _seed_cubes(db_session, count=10)

    resp = await client.get(
        "/api/v1/admin/cubes/search",
        params={"q": "vacancy", "limit": 1},
        headers=API_KEY_HEADER,
    )

    assert resp.status_code == 200
    assert len(resp.json()) <= 1


async def test_search_no_results(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """GET /search?q=nonexistent returns empty list."""
    await _seed_cubes(db_session)

    resp = await client.get(
        "/api/v1/admin/cubes/search",
        params={"q": "xyznonexistent"},
        headers=API_KEY_HEADER,
    )

    assert resp.status_code == 200
    assert resp.json() == []


async def test_search_requires_auth(
    client_no_auth: AsyncClient,
) -> None:
    """GET /search without API key returns 401."""
    resp = await client_no_auth.get(
        "/api/v1/admin/cubes/search",
        params={"q": "test"},
    )
    assert resp.status_code == 401


# ---- Sync ----

async def test_sync_returns_202_with_job_id(
    client: AsyncClient,
) -> None:
    """POST /sync creates a job and returns 202."""
    resp = await client.post(
        "/api/v1/admin/cubes/sync",
        headers=API_KEY_HEADER,
    )

    assert resp.status_code == 202
    data = resp.json()
    assert "job_id" in data
    assert data["status"] == "queued"
    assert data["dedupe"] == "new"


async def test_sync_twice_same_day_returns_existing(
    client: AsyncClient,
) -> None:
    """POST /sync twice on same day returns same job_id."""
    resp1 = await client.post(
        "/api/v1/admin/cubes/sync",
        headers=API_KEY_HEADER,
    )
    assert resp1.status_code == 202
    data1 = resp1.json()
    assert data1["dedupe"] == "new"

    resp2 = await client.post(
        "/api/v1/admin/cubes/sync",
        headers=API_KEY_HEADER,
    )

    assert resp2.status_code == 202
    data2 = resp2.json()
    assert data2["dedupe"] == "existing"
    assert data2["job_id"] == data1["job_id"]


async def test_sync_requires_auth(
    client_no_auth: AsyncClient,
) -> None:
    """POST /sync without API key returns 401."""
    resp = await client_no_auth.post("/api/v1/admin/cubes/sync")
    assert resp.status_code == 401


# ---- Get by product_id ----

async def test_get_cube_returns_metadata(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """GET /{product_id} returns full cube metadata."""
    cubes = await _seed_cubes(db_session, count=1)
    pid = cubes[0].product_id

    resp = await client.get(
        f"/api/v1/admin/cubes/{pid}",
        headers=API_KEY_HEADER,
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["product_id"] == pid
    assert "title_en" in data
    assert "subject_en" in data
    assert "frequency" in data


async def test_get_cube_not_found(
    client: AsyncClient,
) -> None:
    """GET /{product_id} with unknown ID returns 404."""
    resp = await client.get(
        "/api/v1/admin/cubes/99-99-9999-99",
        headers=API_KEY_HEADER,
    )
    assert resp.status_code == 404


async def test_get_cube_requires_auth(
    client_no_auth: AsyncClient,
) -> None:
    """GET /{product_id} without API key returns 401."""
    resp = await client_no_auth.get("/api/v1/admin/cubes/14-10-0127-01")
    assert resp.status_code == 401
