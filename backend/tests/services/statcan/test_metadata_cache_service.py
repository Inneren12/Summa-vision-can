"""Phase 3.1aa: StatCanMetadataCacheService unit tests.

Uses the project's in-memory SQLite ``async_engine`` fixture wrapped in
an ``async_sessionmaker`` to back the service's session factory, and an
``AsyncMock(spec=StatCanClient)`` for the StatCan API.
Async mocks only — never the synchronous variant for async dependencies.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest
import structlog
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from src.core.exceptions import DataSourceError
from src.repositories.cube_metadata_cache_repository import (
    CubeMetadataCacheRepository,
)
from src.services.statcan.client import StatCanClient
from src.services.statcan.metadata_cache import (
    CubeNotFoundError,
    StatCanMetadataCacheService,
    StatCanUnavailableError,
    normalize_dimensions,
)
from src.services.statcan.schemas import CubeMetadataResponse


_FIXED_NOW = datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc)


def _fixed_clock() -> datetime:
    return _FIXED_NOW


def _make_payload(product_id: int = 18100004) -> CubeMetadataResponse:
    return CubeMetadataResponse.model_validate(
        {
            "productId": product_id,
            "cubeTitleEn": "CPI",
            "cubeTitleFr": "IPC",
            "frequencyCode": 6,
            "scalarFactorCode": 0,
            "dimension": [
                {
                    "dimensionNameEn": "Geography",
                    "dimensionNameFr": "Géographie",
                    "dimensionPositionId": 1,
                    "hasUom": False,
                    "member": [
                        {
                            "memberId": 1,
                            "memberNameEn": "Canada",
                            "memberNameFr": "Canada",
                        },
                    ],
                },
            ],
        }
    )


@pytest.fixture()
def session_factory(async_engine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=async_engine, class_=AsyncSession, expire_on_commit=False
    )


@pytest.fixture()
def mock_client() -> AsyncMock:
    return AsyncMock(spec=StatCanClient)


@pytest.fixture()
def service(session_factory, mock_client) -> StatCanMetadataCacheService:
    return StatCanMetadataCacheService(
        session_factory=session_factory,
        client=mock_client,
        clock=_fixed_clock,
        logger=structlog.get_logger(),
    )


async def _seed(session_factory, **kwargs) -> None:
    async with session_factory() as session:
        repo = CubeMetadataCacheRepository(session)
        await repo.upsert(**kwargs)
        await session.commit()


class TestGetCached:
    @pytest.mark.asyncio
    async def test_get_cached_returns_dto_on_hit(
        self, service, session_factory
    ):
        await _seed(
            session_factory,
            cube_id="18-10-0004-01",
            product_id=18100004,
            dimensions=normalize_dimensions(_make_payload()),
            frequency_code="6",
            cube_title_en="CPI",
            cube_title_fr="IPC",
            fetched_at=_FIXED_NOW,
        )
        entry = await service.get_cached("18-10-0004-01")
        assert entry is not None
        assert entry.cube_id == "18-10-0004-01"
        assert entry.product_id == 18100004
        assert entry.cube_title_en == "CPI"

    @pytest.mark.asyncio
    async def test_get_cached_returns_none_on_miss(self, service):
        assert await service.get_cached("nonexistent") is None


class TestGetOrFetch:
    @pytest.mark.asyncio
    async def test_returns_cached_without_calling_client_on_hit(
        self, service, session_factory, mock_client
    ):
        await _seed(
            session_factory,
            cube_id="18-10-0004-01",
            product_id=18100004,
            dimensions=normalize_dimensions(_make_payload()),
            frequency_code="6",
            cube_title_en="CPI",
            cube_title_fr="IPC",
            fetched_at=_FIXED_NOW,
        )
        entry = await service.get_or_fetch("18-10-0004-01", 18100004)
        assert entry.cube_id == "18-10-0004-01"
        mock_client.get_cube_metadata.assert_not_called()

    @pytest.mark.asyncio
    async def test_calls_client_and_persists_on_miss(
        self, service, session_factory, mock_client
    ):
        mock_client.get_cube_metadata.return_value = _make_payload()

        entry = await service.get_or_fetch("18-10-0004-01", 18100004)

        mock_client.get_cube_metadata.assert_awaited_once_with(18100004)
        assert entry.cube_id == "18-10-0004-01"
        assert entry.product_id == 18100004

        # Verify it was persisted.
        async with session_factory() as session:
            repo = CubeMetadataCacheRepository(session)
            row = await repo.get_by_cube_id("18-10-0004-01")
        assert row is not None
        assert row.frequency_code == "6"

    @pytest.mark.asyncio
    async def test_raises_statcan_unavailable_on_miss_when_client_raises_datasource_error(
        self, service, mock_client
    ):
        mock_client.get_cube_metadata.side_effect = DataSourceError(
            message="boom", error_code="DATASOURCE_NETWORK_ERROR"
        )
        with pytest.raises(StatCanUnavailableError):
            await service.get_or_fetch("18-10-0004-01", 18100004)

    @pytest.mark.asyncio
    async def test_raises_cube_not_found_when_client_returns_none(
        self, service, mock_client
    ):
        mock_client.get_cube_metadata.return_value = None
        with pytest.raises(CubeNotFoundError):
            await service.get_or_fetch("18-10-0004-01", 18100004)


class TestRefresh:
    @pytest.mark.asyncio
    async def test_refresh_always_calls_client_even_on_cache_hit(
        self, service, session_factory, mock_client
    ):
        await _seed(
            session_factory,
            cube_id="18-10-0004-01",
            product_id=18100004,
            dimensions=normalize_dimensions(_make_payload()),
            frequency_code="6",
            cube_title_en="CPI",
            cube_title_fr="IPC",
            fetched_at=_FIXED_NOW - timedelta(days=2),
        )
        # Return updated payload (new title).
        new_payload = CubeMetadataResponse.model_validate(
            {
                "productId": 18100004,
                "cubeTitleEn": "CPI v2",
                "cubeTitleFr": "IPC v2",
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
        mock_client.get_cube_metadata.return_value = new_payload

        entry = await service.refresh("18-10-0004-01", 18100004)

        mock_client.get_cube_metadata.assert_awaited_once_with(18100004)
        assert entry.cube_title_en == "CPI v2"


class TestRefreshAllStale:
    @pytest.mark.asyncio
    async def test_continues_on_per_cube_error_and_returns_summary(
        self, service, session_factory, mock_client
    ):
        # Two stale rows.
        old = _FIXED_NOW - timedelta(days=2)
        for cube_id, product_id in [("a-1", 1), ("b-2", 2)]:
            await _seed(
                session_factory,
                cube_id=cube_id,
                product_id=product_id,
                dimensions={"dimensions": []},
                frequency_code="6",
                cube_title_en=cube_id,
                cube_title_fr=cube_id,
                fetched_at=old,
            )

        async def fake_get(product_id: int):
            if product_id == 1:
                return _make_payload(product_id=1)
            raise DataSourceError(message="x", error_code="X")

        mock_client.get_cube_metadata.side_effect = fake_get

        summary = await service.refresh_all_stale(stale_after=timedelta(hours=23))

        assert summary.refreshed == 1
        assert summary.failed == 1
        assert summary.skipped == 0
