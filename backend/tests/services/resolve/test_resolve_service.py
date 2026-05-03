"""Phase 3.1c — :class:`ResolveService` orchestration tests.

Recon §6.2 (8 tests) + impl-addendum §"ADDITIONS — Phase 1 test
scaffolding" test 1.2 (``test_resolve_hit_returns_missing_observation_faithfully``
for F-fix-3) → 9 tests total.

Heavy use of :class:`AsyncMock` for collaborators (mapping repo,
value-cache service, metadata cache) keeps these tests pure-unit:
no DB, no HTTP. The 8-step state machine is exercised by varying
mock return values per test.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
import structlog

from src.models.semantic_mapping import SemanticMapping
from src.services.resolve.exceptions import (
    MappingNotFoundForResolveError,
    ResolveCacheMissError,
    ResolveInvalidFiltersError,
)
from src.services.resolve.service import ResolveService
from src.services.statcan.metadata_cache import StatCanMetadataCacheService
from src.services.statcan.value_cache import StatCanValueCacheService
from src.services.statcan.value_cache_schemas import (
    AutoPrimeResult,
    ValueCacheRow,
)


_FIXED_FETCHED_AT = datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc)


def _mapping(*, is_active: bool = True) -> SemanticMapping:
    m = SemanticMapping(
        cube_id="18-10-0004",
        product_id=18100004,
        semantic_key="cpi.canada.all_items.index",
        label="CPI",
        description=None,
        config={
            "dimension_filters": {
                "Geography": "Canada",
                "Products": "All-items",
            },
            "unit": "index",
            "frequency": "monthly",
        },
        is_active=is_active,
    )
    m.version = 1
    return m


def _row(*, value: Decimal | None = Decimal("100.0"), missing: bool = False) -> ValueCacheRow:
    return ValueCacheRow(
        id=1,
        cube_id="18-10-0004",
        product_id=18100004,
        semantic_key="cpi.canada.all_items.index",
        coord="1.10.0.0.0.0.0.0.0.0",
        ref_period="2025-12",
        period_start=None,
        value=value,
        missing=missing,
        decimals=2,
        scalar_factor_code=0,
        symbol_code=0,
        security_level_code=0,
        status_code=0,
        frequency_code=6,
        vector_id=None,
        response_status_code=None,
        source_hash="abc",
        fetched_at=_FIXED_FETCHED_AT,
        release_time=None,
        is_stale=False,
    )


def _build_service(
    *,
    mapping: SemanticMapping | None,
    get_cached_returns: list,  # list of returns per call
    auto_prime_result: AutoPrimeResult = AutoPrimeResult(0, 0, 0),
) -> tuple[ResolveService, MagicMock, MagicMock]:
    # Mapping repo: returns the supplied mapping (None for not-found path).
    mapping_repo = MagicMock()
    mapping_repo.get_active_by_key = AsyncMock(return_value=mapping)
    mapping_repo_factory = MagicMock(return_value=mapping_repo)

    # Async session factory: produces an async-context-manager that yields
    # a dummy session — the service only uses it as the arg to the repo
    # factory, not for any actual SQL.
    session_cm = AsyncMock()
    session_cm.__aenter__ = AsyncMock(return_value=AsyncMock())
    session_cm.__aexit__ = AsyncMock(return_value=None)
    factory = MagicMock(return_value=session_cm)

    value_cache_service = MagicMock(spec=StatCanValueCacheService)
    value_cache_service.get_cached = AsyncMock(side_effect=get_cached_returns)
    value_cache_service.auto_prime = AsyncMock(return_value=auto_prime_result)

    metadata_cache = MagicMock(spec=StatCanMetadataCacheService)
    metadata_cache.get_cached = AsyncMock(return_value=None)

    service = ResolveService(
        session_factory=factory,
        mapping_repository_factory=mapping_repo_factory,
        value_cache_service=value_cache_service,
        metadata_cache=metadata_cache,
        logger=structlog.get_logger(),
    )
    return service, value_cache_service, mapping_repo


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resolve_hit_no_prime() -> None:
    service, vc, _ = _build_service(
        mapping=_mapping(),
        get_cached_returns=[[_row()]],
    )
    dto = await service.resolve_value(
        cube_id="18-10-0004",
        semantic_key="cpi.canada.all_items.index",
        raw_filters=[(1, 1), (2, 10)],
        period=None,
    )
    assert dto.cache_status == "hit"
    assert dto.value == "100.0"
    vc.auto_prime.assert_not_called()


@pytest.mark.asyncio
async def test_resolve_hit_returns_missing_observation_faithfully() -> None:
    service, vc, _ = _build_service(
        mapping=_mapping(),
        get_cached_returns=[[_row(value=None, missing=True)]],
    )
    dto = await service.resolve_value(
        cube_id="18-10-0004",
        semantic_key="cpi.canada.all_items.index",
        raw_filters=[(1, 1), (2, 10)],
        period=None,
    )
    assert dto.value is None
    assert dto.missing is True
    assert dto.cache_status == "hit"
    vc.auto_prime.assert_not_called()


@pytest.mark.asyncio
async def test_resolve_mapping_missing() -> None:
    service, _, _ = _build_service(
        mapping=None, get_cached_returns=[[]]
    )
    with pytest.raises(MappingNotFoundForResolveError):
        await service.resolve_value(
            cube_id="18-10-0004",
            semantic_key="cpi.canada.all_items.index",
            raw_filters=[(1, 1), (2, 10)],
            period=None,
        )


@pytest.mark.asyncio
async def test_resolve_invalid_filters_missing_dim() -> None:
    service, _, _ = _build_service(
        mapping=_mapping(), get_cached_returns=[[]]
    )
    with pytest.raises(ResolveInvalidFiltersError):
        await service.resolve_value(
            cube_id="18-10-0004",
            semantic_key="cpi.canada.all_items.index",
            raw_filters=[(1, 1)],  # missing 2nd dim
            period=None,
        )


@pytest.mark.asyncio
async def test_resolve_invalid_filters_extra_dim() -> None:
    service, _, _ = _build_service(
        mapping=_mapping(), get_cached_returns=[[]]
    )
    with pytest.raises(ResolveInvalidFiltersError):
        await service.resolve_value(
            cube_id="18-10-0004",
            semantic_key="cpi.canada.all_items.index",
            raw_filters=[(1, 1), (2, 10), (3, 7)],  # extra
            period=None,
        )


@pytest.mark.asyncio
async def test_resolve_cold_cache_auto_prime_success_returns_primed() -> None:
    service, vc, _ = _build_service(
        mapping=_mapping(),
        get_cached_returns=[[], [_row()]],  # cold first, primed second
        auto_prime_result=AutoPrimeResult(1, 0, 0),
    )
    dto = await service.resolve_value(
        cube_id="18-10-0004",
        semantic_key="cpi.canada.all_items.index",
        raw_filters=[(1, 1), (2, 10)],
        period=None,
    )
    assert dto.cache_status == "primed"
    vc.auto_prime.assert_awaited_once()


@pytest.mark.asyncio
async def test_resolve_cache_miss_prime_error_but_row_written() -> None:
    service, vc, _ = _build_service(
        mapping=_mapping(),
        get_cached_returns=[[], [_row()]],  # row appeared anyway
        auto_prime_result=AutoPrimeResult(0, 0, 0, error="persist: kaboom"),
    )
    dto = await service.resolve_value(
        cube_id="18-10-0004",
        semantic_key="cpi.canada.all_items.index",
        raw_filters=[(1, 1), (2, 10)],
        period=None,
    )
    # Error should NOT surface in DTO (recon §5.2 invariant).
    assert dto.cache_status == "primed"
    assert "error" not in dto.model_dump()


@pytest.mark.asyncio
async def test_resolve_cache_miss_prime_error_no_row() -> None:
    service, _, _ = _build_service(
        mapping=_mapping(),
        get_cached_returns=[[], []],
        auto_prime_result=AutoPrimeResult(0, 0, 0, error="upstream timeout"),
    )
    with pytest.raises(ResolveCacheMissError) as info:
        await service.resolve_value(
            cube_id="18-10-0004",
            semantic_key="cpi.canada.all_items.index",
            raw_filters=[(1, 1), (2, 10)],
            period=None,
        )
    assert info.value.prime_error_code == "upstream"
    assert info.value.prime_attempted is True


@pytest.mark.asyncio
async def test_http_to_service_pipeline_wiring() -> None:
    """Smoke check that the service's coord ends up populating the DTO,
    end-to-end through the helpers (no HTTP layer)."""
    service, _, _ = _build_service(
        mapping=_mapping(),
        get_cached_returns=[[_row()]],
    )
    dto = await service.resolve_value(
        cube_id="18-10-0004",
        semantic_key="cpi.canada.all_items.index",
        raw_filters=[(1, 1), (2, 10)],
        period=None,
    )
    # Cache-row coord echoed (the seeded row uses the canonical encoding).
    assert dto.coord == "1.10.0.0.0.0.0.0.0.0"
