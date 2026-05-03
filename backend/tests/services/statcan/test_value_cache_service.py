"""Phase 3.1aaa: StatCanValueCacheService unit tests.

In-memory SQLite + ``AsyncMock`` for the StatCan client. AsyncMock-only
for async paths (project pattern); never plain ``MagicMock``.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.exceptions import DataSourceError
from src.models.semantic_mapping import SemanticMapping
from src.repositories.semantic_mapping_repository import (
    SemanticMappingRepository,
)
from src.repositories.semantic_value_cache_repository import (
    SemanticValueCacheRepository,
)
from src.services.semantic_mappings.validation import ResolvedDimensionFilter
from src.services.statcan.client import StatCanClient
from src.services.statcan.metadata_cache import (
    CubeMetadataCacheEntry,
    StatCanMetadataCacheService,
)
from src.services.statcan.value_cache import StatCanValueCacheService
from src.services.statcan.value_cache_schemas import (
    StatCanDataPoint,
    StatCanDataResponse,
)


_FIXED = datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc)


def _clock() -> datetime:
    return _FIXED


@pytest.fixture()
def session_factory(async_engine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=async_engine, class_=AsyncSession, expire_on_commit=False
    )


@pytest.fixture()
def mock_client() -> AsyncMock:
    return AsyncMock(spec=StatCanClient)


@pytest.fixture()
def mock_metadata_cache() -> AsyncMock:
    return AsyncMock(spec=StatCanMetadataCacheService)


@pytest.fixture()
def service(
    session_factory, mock_client, mock_metadata_cache
) -> StatCanValueCacheService:
    return StatCanValueCacheService(
        session_factory=session_factory,
        repository_factory=lambda s: SemanticValueCacheRepository(s),
        mapping_repository_factory=lambda s: SemanticMappingRepository(s),
        cube_metadata_cache=mock_metadata_cache,
        statcan_client=mock_client,
        clock=_clock,
        logger=structlog.get_logger(),
    )


def _resp(periods: list[tuple[str, Decimal | None]]) -> StatCanDataResponse:
    return StatCanDataResponse.model_validate(
        {
            "responseStatusCode": 0,
            "productId": 18100004,
            "coordinate": "1.10.0.0.0.0.0.0.0.0",
            "vectorId": 41690914,
            "vectorDataPoint": [
                {
                    "refPer": rp,
                    "value": str(v) if v is not None else None,
                    "decimals": 1,
                    "scalarFactorCode": 0,
                    "symbolCode": 0,
                    "securityLevelCode": 0,
                    "statusCode": 0,
                    "frequencyCode": 6,
                    "missing": v is None,
                }
                for rp, v in periods
            ],
        }
    )


def _filter(pos: int, member: int) -> ResolvedDimensionFilter:
    return ResolvedDimensionFilter(
        dimension_name="d",
        member_name="m",
        dimension_position_id=pos,
        member_id=member,
    )


async def _seed_mapping(session_factory, **kwargs) -> SemanticMapping:
    defaults = dict(
        cube_id="18-10-0004-01",
        product_id=18100004,
        semantic_key="cpi.canada.all_items",
        label="lbl",
        description=None,
        config={"dimension_filters": {}},
        is_active=True,
        version=1,
    )
    defaults.update(kwargs)
    async with session_factory() as session:
        m = SemanticMapping(**defaults)
        session.add(m)
        await session.commit()
        await session.refresh(m)
        return m


class TestAutoPrime:
    @pytest.mark.asyncio
    async def test_happy_single_period(self, service, mock_client, session_factory):
        await _seed_mapping(session_factory)
        mock_client.get_data_from_cube_pid_coord_and_latest_n_periods.return_value = (
            _resp([("2026-04", Decimal("123.4"))])
        )
        result = await service.auto_prime(
            cube_id="18-10-0004-01",
            semantic_key="cpi.canada.all_items",
            product_id=18100004,
            resolved_filters=[_filter(1, 1), _filter(2, 10)],
            frequency_code=6,
        )
        assert result.error is None
        assert result.rows_inserted == 1

    @pytest.mark.asyncio
    async def test_statcan_unavailable_does_not_propagate(
        self, service, mock_client, session_factory
    ):
        """Q-3 RE-LOCK: best-effort failure must NOT raise."""
        await _seed_mapping(session_factory)
        mock_client.get_data_from_cube_pid_coord_and_latest_n_periods.side_effect = (
            DataSourceError(
                message="boom",
                error_code="DATASOURCE_NETWORK_ERROR",
                context={},
            )
        )
        result = await service.auto_prime(
            cube_id="18-10-0004-01",
            semantic_key="cpi.canada.all_items",
            product_id=18100004,
            resolved_filters=[_filter(1, 1)],
            frequency_code=6,
        )
        assert result.error is not None
        assert "boom" in result.error
        assert result.rows_inserted == 0

    @pytest.mark.asyncio
    async def test_invalid_coord_returns_error(self, service, mock_client):
        result = await service.auto_prime(
            cube_id="18-10-0004-01",
            semantic_key="x",
            product_id=18100004,
            resolved_filters=[_filter(11, 1)],  # out of range
            frequency_code=6,
        )
        assert result.error is not None
        assert "coord" in result.error
        mock_client.get_data_from_cube_pid_coord_and_latest_n_periods.assert_not_called()

    @pytest.mark.asyncio
    async def test_multi_period_response(self, service, mock_client, session_factory):
        await _seed_mapping(session_factory)
        mock_client.get_data_from_cube_pid_coord_and_latest_n_periods.return_value = (
            _resp(
                [
                    ("2026-02", Decimal("100.0")),
                    ("2026-03", Decimal("101.0")),
                    ("2026-04", Decimal("102.0")),
                ]
            )
        )
        result = await service.auto_prime(
            cube_id="18-10-0004-01",
            semantic_key="cpi.canada.all_items",
            product_id=18100004,
            resolved_filters=[_filter(1, 1)],
            frequency_code=6,
        )
        assert result.rows_inserted == 3
        assert result.error is None

    @pytest.mark.asyncio
    async def test_missing_value_handling(
        self, service, mock_client, session_factory
    ):
        await _seed_mapping(session_factory)
        mock_client.get_data_from_cube_pid_coord_and_latest_n_periods.return_value = (
            _resp([("2026-04", None)])
        )
        result = await service.auto_prime(
            cube_id="18-10-0004-01",
            semantic_key="cpi.canada.all_items",
            product_id=18100004,
            resolved_filters=[_filter(1, 1)],
            frequency_code=6,
        )
        assert result.rows_inserted == 1
        # And the persisted row marks missing=True.
        rows = await service.get_cached(
            cube_id="18-10-0004-01",
            semantic_key="cpi.canada.all_items",
            coord="1.0.0.0.0.0.0.0.0.0",
        )
        assert rows[0].missing is True

    @pytest.mark.asyncio
    async def test_idempotent_re_prime_same_data(
        self, service, mock_client, session_factory
    ):
        await _seed_mapping(session_factory)
        mock_client.get_data_from_cube_pid_coord_and_latest_n_periods.return_value = (
            _resp([("2026-04", Decimal("1.0"))])
        )
        r1 = await service.auto_prime(
            cube_id="18-10-0004-01",
            semantic_key="cpi.canada.all_items",
            product_id=18100004,
            resolved_filters=[_filter(1, 1)],
            frequency_code=6,
        )
        r2 = await service.auto_prime(
            cube_id="18-10-0004-01",
            semantic_key="cpi.canada.all_items",
            product_id=18100004,
            resolved_filters=[_filter(1, 1)],
            frequency_code=6,
        )
        assert r1.rows_inserted == 1
        assert r2.rows_unchanged == 1
        assert r2.rows_inserted == 0

    @pytest.mark.asyncio
    async def test_frequency_code_drives_latest_n(
        self, service, mock_client, session_factory
    ):
        await _seed_mapping(session_factory)
        mock_client.get_data_from_cube_pid_coord_and_latest_n_periods.return_value = (
            _resp([("2026-04", Decimal("1.0"))])
        )
        await service.auto_prime(
            cube_id="18-10-0004-01",
            semantic_key="cpi.canada.all_items",
            product_id=18100004,
            resolved_filters=[_filter(1, 1)],
            frequency_code=9,  # quarterly
        )
        kwargs = mock_client.get_data_from_cube_pid_coord_and_latest_n_periods.call_args.kwargs
        assert kwargs["latest_n"] == 8  # quarterly default

    @pytest.mark.asyncio
    async def test_unknown_frequency_uses_default(
        self, service, mock_client, session_factory
    ):
        await _seed_mapping(session_factory)
        mock_client.get_data_from_cube_pid_coord_and_latest_n_periods.return_value = (
            _resp([("2026-04", Decimal("1.0"))])
        )
        await service.auto_prime(
            cube_id="18-10-0004-01",
            semantic_key="cpi.canada.all_items",
            product_id=18100004,
            resolved_filters=[_filter(1, 1)],
            frequency_code=999,
        )
        kwargs = mock_client.get_data_from_cube_pid_coord_and_latest_n_periods.call_args.kwargs
        assert kwargs["latest_n"] == 12  # default

    @pytest.mark.asyncio
    async def test_empty_response_returns_zero_no_error(
        self, service, mock_client, session_factory
    ):
        await _seed_mapping(session_factory)
        mock_client.get_data_from_cube_pid_coord_and_latest_n_periods.return_value = None
        result = await service.auto_prime(
            cube_id="18-10-0004-01",
            semantic_key="cpi.canada.all_items",
            product_id=18100004,
            resolved_filters=[_filter(1, 1)],
            frequency_code=6,
        )
        assert result.error is None
        assert result.rows_inserted == 0

    @pytest.mark.asyncio
    async def test_unexpected_exception_caught(
        self, service, mock_client, session_factory
    ):
        await _seed_mapping(session_factory)
        mock_client.get_data_from_cube_pid_coord_and_latest_n_periods.side_effect = (
            RuntimeError("totally unexpected")
        )
        result = await service.auto_prime(
            cube_id="18-10-0004-01",
            semantic_key="cpi.canada.all_items",
            product_id=18100004,
            resolved_filters=[_filter(1, 1)],
            frequency_code=6,
        )
        assert result.error is not None
        assert "parse" in result.error or "totally unexpected" in result.error


class TestRefreshAll:
    @pytest.mark.asyncio
    async def test_no_active_mappings(self, service, mock_client):
        summary = await service.refresh_all()
        assert summary.mappings_processed == 0
        assert summary.rows_upserted == 0
        mock_client.get_data_from_cube_pid_coord_and_latest_n_periods.assert_not_called()

    @pytest.mark.asyncio
    async def test_single_mapping_with_existing_row(
        self, service, mock_client, mock_metadata_cache, session_factory
    ):
        await _seed_mapping(session_factory)
        # Pre-seed a value-cache row so refresh has a coord to revisit.
        mock_client.get_data_from_cube_pid_coord_and_latest_n_periods.return_value = (
            _resp([("2026-04", Decimal("100.0"))])
        )
        await service.auto_prime(
            cube_id="18-10-0004-01",
            semantic_key="cpi.canada.all_items",
            product_id=18100004,
            resolved_filters=[_filter(1, 1)],
            frequency_code=6,
        )
        mock_metadata_cache.get_cached.return_value = CubeMetadataCacheEntry(
            cube_id="18-10-0004-01",
            product_id=18100004,
            dimensions={"dimensions": []},
            frequency_code="6",
            cube_title_en="x",
            cube_title_fr="x",
            fetched_at=_FIXED,
        )
        # Refresh returns updated value.
        mock_client.get_data_from_cube_pid_coord_and_latest_n_periods.return_value = (
            _resp([("2026-04", Decimal("999.0"))])
        )
        summary = await service.refresh_all()
        assert summary.mappings_processed == 1
        assert summary.rows_upserted == 1
        assert summary.errors == []

    @pytest.mark.asyncio
    async def test_per_target_failure_continues(
        self, service, mock_client, mock_metadata_cache, session_factory
    ):
        await _seed_mapping(session_factory)
        # Seed two coords (two rows) so we have two targets.
        mock_client.get_data_from_cube_pid_coord_and_latest_n_periods.return_value = (
            _resp([("2026-04", Decimal("1.0"))])
        )
        await service.auto_prime(
            cube_id="18-10-0004-01",
            semantic_key="cpi.canada.all_items",
            product_id=18100004,
            resolved_filters=[_filter(1, 1)],
            frequency_code=6,
        )
        await service.auto_prime(
            cube_id="18-10-0004-01",
            semantic_key="cpi.canada.all_items",
            product_id=18100004,
            resolved_filters=[_filter(1, 2)],
            frequency_code=6,
        )
        mock_metadata_cache.get_cached.return_value = None

        # First call succeeds, second raises.
        mock_client.get_data_from_cube_pid_coord_and_latest_n_periods.reset_mock()
        mock_client.get_data_from_cube_pid_coord_and_latest_n_periods.side_effect = [
            _resp([("2026-04", Decimal("2.0"))]),
            DataSourceError(message="x", error_code="X", context={}),
        ]
        summary = await service.refresh_all()
        assert summary.mappings_processed == 1
        assert len(summary.errors) == 1


class TestEvictStale:
    @pytest.mark.asyncio
    async def test_evict_stale_deletes_old(self, service, session_factory, mock_client):
        from datetime import timedelta

        await _seed_mapping(session_factory)
        mock_client.get_data_from_cube_pid_coord_and_latest_n_periods.return_value = (
            _resp([("2026-04", Decimal("1.0"))])
        )
        await service.auto_prime(
            cube_id="18-10-0004-01",
            semantic_key="cpi.canada.all_items",
            product_id=18100004,
            resolved_filters=[_filter(1, 1)],
            frequency_code=6,
        )
        # Default fetched_at is _FIXED — eviction with 0-day retention drops it.
        n = await service.evict_stale(timedelta(days=-1))
        assert n == 1
