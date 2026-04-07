"""Tests for CatalogSyncService."""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.cube_catalog_repository import CubeCatalogRepository
from src.services.statcan.catalog_sync import CatalogSyncService, SyncReport


def _make_statcan_cube(
    product_id: str = "14-10-0127-01",
    cansim_id: int = 14100127,
    **overrides,
) -> dict:
    """Create a mock StatCan API response item (camelCase JSON)."""
    base = {
        "productId": product_id,
        "cansimId": cansim_id,
        "cubeTitleEn": f"Test cube {product_id}",
        "cubeTitleFr": None,
        "subjectCode": "46",
        "subjectEn": "Housing",
        "surveyEn": "Test Survey",
        "frequencyCode": 6,
        "startDate": "1990-01-01",
        "endDate": "2024-12-01",
        "archived": False,
    }
    base.update(overrides)
    return base


def _mock_http(cubes: list[dict]) -> AsyncMock:
    """Create mock HTTP client returning given cubes."""
    response = MagicMock()
    response.json.return_value = cubes
    response.raise_for_status = MagicMock()
    client = AsyncMock()
    client.get.return_value = response
    client.request.return_value = response
    return client


async def test_sync_saves_all_cubes(db_session: AsyncSession) -> None:
    """50 cubes from API → 50 records in DB."""
    cubes = [
        _make_statcan_cube(f"10-10-{i:04d}-01", 10100000 + i)
        for i in range(50)
    ]
    repo = CubeCatalogRepository(db_session)
    service = CatalogSyncService(_mock_http(cubes), repo)

    report = await service.sync_full_catalog()
    await db_session.commit()

    assert report.total == 50
    assert report.new == 50
    assert report.errors == 0
    assert await repo.count() == 50


async def test_sync_idempotent(db_session: AsyncSession) -> None:
    """Syncing same data twice doesn't duplicate records."""
    cubes = [_make_statcan_cube()]
    repo = CubeCatalogRepository(db_session)
    service = CatalogSyncService(_mock_http(cubes), repo)

    await service.sync_full_catalog()
    await db_session.commit()
    report = await service.sync_full_catalog()
    await db_session.commit()

    assert report.total == 1
    assert report.new == 0
    assert await repo.count() == 1


async def test_sync_handles_malformed(db_session: AsyncSession) -> None:
    """Malformed entries counted as errors, valid ones saved."""
    cubes = [
        _make_statcan_cube("14-10-0001-01", 1),
        {"bad": "data"},
        _make_statcan_cube("14-10-0002-01", 2),
    ]
    repo = CubeCatalogRepository(db_session)
    service = CatalogSyncService(_mock_http(cubes), repo)

    report = await service.sync_full_catalog()
    await db_session.commit()

    assert report.total == 3
    assert report.errors == 1
    assert report.new == 2


async def test_sync_maps_frequency(db_session: AsyncSession) -> None:
    """Numeric frequency codes mapped to strings."""
    cubes = [
        _make_statcan_cube("14-10-0001-01", 1, frequencyCode=6),
        _make_statcan_cube("14-10-0002-01", 2, frequencyCode=4),
        _make_statcan_cube("14-10-0003-01", 3, frequencyCode=1),
    ]
    repo = CubeCatalogRepository(db_session)
    service = CatalogSyncService(_mock_http(cubes), repo)

    await service.sync_full_catalog()
    await db_session.commit()

    m = await repo.get_by_product_id("14-10-0001-01")
    q = await repo.get_by_product_id("14-10-0002-01")
    a = await repo.get_by_product_id("14-10-0003-01")

    assert m is not None and m.frequency == "Monthly"
    assert q is not None and q.frequency == "Quarterly"
    assert a is not None and a.frequency == "Annual"


async def test_sync_empty_response(db_session: AsyncSession) -> None:
    """Empty API response → zero-count report."""
    repo = CubeCatalogRepository(db_session)
    service = CatalogSyncService(_mock_http([]), repo)

    report = await service.sync_full_catalog()
    assert report.total == 0
    assert report.errors == 0


async def test_sync_calls_correct_url(db_session: AsyncSession) -> None:
    """Service calls getAllCubesList endpoint."""
    import httpx
    import respx

    repo = CubeCatalogRepository(db_session)

    with respx.mock(assert_all_called=True) as respx_mock:
        route = respx_mock.get("https://www150.statcan.gc.ca/t1/tbl1/en/dtl!getAllCubesList").mock(
            return_value=httpx.Response(200, json=[])
        )
        async with httpx.AsyncClient() as client:
            service = CatalogSyncService(client, repo)
            await service.sync_full_catalog()

        assert route.call_count == 1


async def test_sync_wrapped_response(db_session: AsyncSession) -> None:
    """Service handles responses wrapped in a container object."""
    wrapped_response = {"data": [_make_statcan_cube()]}
    repo = CubeCatalogRepository(db_session)
    service = CatalogSyncService(_mock_http(wrapped_response), repo)

    report = await service.sync_full_catalog()
    assert report.total == 1
    assert report.errors == 0


async def test_sync_updates_existing(db_session: AsyncSession) -> None:
    """Second sync with changed title updates the record."""
    repo = CubeCatalogRepository(db_session)

    cubes_v1 = [_make_statcan_cube(cubeTitleEn="Original Title")]
    service1 = CatalogSyncService(_mock_http(cubes_v1), repo)
    await service1.sync_full_catalog()
    await db_session.commit()

    cubes_v2 = [_make_statcan_cube(cubeTitleEn="Updated Title")]
    service2 = CatalogSyncService(_mock_http(cubes_v2), repo)
    await service2.sync_full_catalog()
    await db_session.commit()

    cube = await repo.get_by_product_id("14-10-0127-01")
    assert cube is not None
    assert cube.title_en == "Updated Title"
    assert await repo.count() == 1


def test_dedupe_key_format() -> None:
    """Dedupe key has correct format."""
    from src.services.jobs.dedupe import catalog_sync_key

    key = catalog_sync_key(date(2025, 4, 5))
    assert key == "catalog_sync:2025-04-05"


def test_handler_registered() -> None:
    """catalog_sync handler is in HANDLER_REGISTRY."""
    from src.services.jobs.handlers import HANDLER_REGISTRY

    assert "catalog_sync" in HANDLER_REGISTRY
