"""Phase 3.1aa: end-to-end integration test for the metadata cache.

Mirrors :mod:`tests.integration.test_cube_catalog_repository_integration`'s
real-Postgres pattern: relies on the ``pg_session`` fixture which boots
Alembic against ``TEST_DATABASE_URL``. Skips if no Postgres URL is set.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest
import structlog
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from src.services.statcan.client import StatCanClient
from src.services.statcan.metadata_cache import StatCanMetadataCacheService
from src.services.statcan.schemas import CubeMetadataResponse


def _payload(title: str = "CPI") -> CubeMetadataResponse:
    return CubeMetadataResponse.model_validate(
        {
            "productId": 18100004,
            "cubeTitleEn": title,
            "cubeTitleFr": title,
            "frequencyCode": 6,
            "scalarFactorCode": 0,
            "dimension": [
                {
                    "dimensionNameEn": "Geography",
                    "dimensionNameFr": "Géographie",
                    "dimensionPositionId": 1,
                    "hasUom": False,
                },
            ],
        }
    )


@pytest.mark.asyncio
async def test_metadata_cache_warm_then_idempotent_then_stale_refresh(pg_session):
    bind = pg_session.bind
    factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
        bind=bind, class_=AsyncSession, expire_on_commit=False
    )

    clock_value = {"now": datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc)}

    def clock() -> datetime:
        return clock_value["now"]

    client = AsyncMock(spec=StatCanClient)
    client.get_cube_metadata.return_value = _payload("CPI v1")

    service = StatCanMetadataCacheService(
        session_factory=factory,
        client=client,
        clock=clock,
        logger=structlog.get_logger(),
    )

    # Warm path: cache miss → fetch + persist.
    entry = await service.get_or_fetch("18-10-0004-01", 18100004)
    assert entry.cube_title_en == "CPI v1"
    assert client.get_cube_metadata.await_count == 1

    # Second call: cache hit, no client call.
    entry2 = await service.get_or_fetch("18-10-0004-01", 18100004)
    assert entry2.cube_title_en == "CPI v1"
    assert client.get_cube_metadata.await_count == 1

    # Advance the clock so the row is stale, then sweep.
    clock_value["now"] = clock_value["now"] + timedelta(days=2)
    client.get_cube_metadata.return_value = _payload("CPI v2")

    summary = await service.refresh_all_stale(stale_after=timedelta(hours=23))
    assert summary.refreshed == 1
    assert summary.failed == 0

    refreshed = await service.get_cached("18-10-0004-01")
    assert refreshed is not None
    assert refreshed.cube_title_en == "CPI v2"
