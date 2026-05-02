"""Phase 3.1ab: ``SemanticMappingService`` unit tests.

Uses an in-memory SQLite engine (provided by the project's ``async_engine``
fixture) wrapped in an ``async_sessionmaker`` to back the service's session
factory, plus an ``AsyncMock(spec=StatCanMetadataCacheService)`` for the
cache layer. Async mocks only — never the synchronous variant for async
dependencies.
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.repositories.semantic_mapping_repository import (
    SemanticMappingRepository,
)
from src.services.semantic_mappings.exceptions import (
    CubeNotInCacheError,
    DimensionMismatchError,
    MemberMismatchError,
    MetadataValidationError,
)
from src.services.semantic_mappings.service import SemanticMappingService
from src.services.statcan.metadata_cache import (
    CubeMetadataCacheEntry,
    CubeMetadataProductMismatchError,
    CubeNotFoundError,
    StatCanMetadataCacheService,
    StatCanUnavailableError,
)


_FIXED_FETCHED_AT = datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc)


def _cache_entry(
    *,
    cube_id: str = "18-10-0004",
    product_id: int = 18100004,
) -> CubeMetadataCacheEntry:
    return CubeMetadataCacheEntry(
        cube_id=cube_id,
        product_id=product_id,
        dimensions={
            "dimensions": [
                {
                    "position_id": 1,
                    "name_en": "Geography",
                    "name_fr": "Géographie",
                    "has_uom": False,
                    "members": [
                        {
                            "member_id": 1,
                            "name_en": "Canada",
                            "name_fr": "Canada",
                        },
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


def _valid_config() -> dict:
    return {
        "dimension_filters": {"Geography": "Canada", "Products": "All-items"},
        "measure": "Value",
        "unit": "index",
        "frequency": "monthly",
        "supported_metrics": [
            "current_value",
            "year_over_year_change",
            "previous_period_change",
        ],
        "default_geo": "Canada",
    }


@pytest.fixture()
def session_factory(async_engine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=async_engine, class_=AsyncSession, expire_on_commit=False
    )


@pytest.fixture()
def mock_cache() -> AsyncMock:
    return AsyncMock(spec=StatCanMetadataCacheService)


@pytest.fixture()
def service(session_factory, mock_cache) -> SemanticMappingService:
    return SemanticMappingService(
        session_factory=session_factory,
        repository_factory=SemanticMappingRepository,
        metadata_cache=mock_cache,
        logger=structlog.get_logger(),
    )


@pytest.mark.asyncio
async def test_upsert_validated_happy_path_calls_cache_validator_and_repo(
    service, session_factory, mock_cache
):
    mock_cache.get_or_fetch.return_value = _cache_entry()

    mapping, _was_created = await service.upsert_validated(
        cube_id="18-10-0004",
        product_id=18100004,
        semantic_key="cpi.canada.all_items.index",
        label="CPI — Canada, all-items",
        description="headline",
        config=_valid_config(),
        is_active=True,
        updated_by="alice",
    )

    mock_cache.get_or_fetch.assert_awaited_once_with("18-10-0004", 18100004)
    assert mapping.cube_id == "18-10-0004"
    assert mapping.semantic_key == "cpi.canada.all_items.index"
    assert mapping.updated_by == "alice"
    # The row must actually be persisted (commit happened inside the service).
    async with session_factory() as session:
        repo = SemanticMappingRepository(session)
        fetched = await repo.get_by_key(
            "18-10-0004", "cpi.canada.all_items.index"
        )
    assert fetched is not None
    assert fetched.label == "CPI — Canada, all-items"


@pytest.mark.asyncio
async def test_cache_unavailable_re_raises_as_cube_not_in_cache_error(
    service, mock_cache
):
    mock_cache.get_or_fetch.side_effect = StatCanUnavailableError(
        cube_id="18-10-0004"
    )

    with pytest.raises(CubeNotInCacheError) as exc_info:
        await service.upsert_validated(
            cube_id="18-10-0004",
            product_id=18100004,
            semantic_key="cpi.k",
            label="L",
            description=None,
            config=_valid_config(),
            is_active=True,
            updated_by=None,
        )

    assert exc_info.value.error_code == "CUBE_NOT_IN_CACHE"
    assert exc_info.value.cube_id == "18-10-0004"
    assert isinstance(exc_info.value.__cause__, StatCanUnavailableError)


@pytest.mark.asyncio
async def test_cache_cube_not_found_re_raises_as_cube_not_in_cache_error(
    service, mock_cache
):
    mock_cache.get_or_fetch.side_effect = CubeNotFoundError(
        cube_id="18-10-0004", product_id=18100004
    )

    with pytest.raises(CubeNotInCacheError) as exc_info:
        await service.upsert_validated(
            cube_id="18-10-0004",
            product_id=18100004,
            semantic_key="cpi.k",
            label="L",
            description=None,
            config=_valid_config(),
            is_active=True,
            updated_by=None,
        )

    assert exc_info.value.error_code == "CUBE_NOT_IN_CACHE"
    assert isinstance(exc_info.value.__cause__, CubeNotFoundError)


@pytest.mark.asyncio
async def test_cache_product_mismatch_re_raises_as_metadata_validation_error_with_correct_code(
    service, mock_cache
):
    mock_cache.get_or_fetch.side_effect = CubeMetadataProductMismatchError(
        cube_id="18-10-0004",
        expected_product_id=18100004,
        actual_product_id=99999999,
    )

    with pytest.raises(MetadataValidationError) as exc_info:
        await service.upsert_validated(
            cube_id="18-10-0004",
            product_id=99999999,
            semantic_key="cpi.k",
            label="L",
            description=None,
            config=_valid_config(),
            is_active=True,
            updated_by=None,
        )

    assert exc_info.value.error_code == "CUBE_PRODUCT_MISMATCH"
    # Must NOT be the more-specific CubeNotInCacheError subclass.
    assert not isinstance(exc_info.value, CubeNotInCacheError)
    assert isinstance(
        exc_info.value.__cause__, CubeMetadataProductMismatchError
    )


@pytest.mark.asyncio
async def test_validation_dimension_not_found_raises_dimension_mismatch_error(
    service, mock_cache
):
    mock_cache.get_or_fetch.return_value = _cache_entry()
    bad_config = _valid_config()
    bad_config["dimension_filters"] = {"Province": "Ontario"}  # not in cube

    with pytest.raises(DimensionMismatchError) as exc_info:
        await service.upsert_validated(
            cube_id="18-10-0004",
            product_id=18100004,
            semantic_key="cpi.k",
            label="L",
            description=None,
            config=bad_config,
            is_active=True,
            updated_by=None,
        )

    assert exc_info.value.error_code == "DIMENSION_NOT_FOUND"
    codes = [e.error_code for e in exc_info.value.result.errors]
    assert "DIMENSION_NOT_FOUND" in codes


@pytest.mark.asyncio
async def test_validation_member_not_found_raises_member_mismatch_error(
    service, mock_cache
):
    mock_cache.get_or_fetch.return_value = _cache_entry()
    bad_config = _valid_config()
    bad_config["dimension_filters"] = {"Geography": "Atlantis"}  # bad member

    with pytest.raises(MemberMismatchError) as exc_info:
        await service.upsert_validated(
            cube_id="18-10-0004",
            product_id=18100004,
            semantic_key="cpi.k",
            label="L",
            description=None,
            config=bad_config,
            is_active=True,
            updated_by=None,
        )

    assert exc_info.value.error_code == "MEMBER_NOT_FOUND"
    codes = [e.error_code for e in exc_info.value.result.errors]
    assert "MEMBER_NOT_FOUND" in codes


@pytest.mark.asyncio
async def test_upsert_validated_bad_config_shape_raises_before_cache_fetch(
    service, mock_cache
):
    """Reviewer P1: config validation must fail BEFORE cache fetch.

    A malformed ``config`` (e.g. ``dimension_filters`` as a list) must raise
    ``pydantic.ValidationError`` immediately and NOT call ``get_or_fetch``.
    """
    from pydantic import ValidationError

    mock_cache.get_or_fetch.side_effect = AssertionError(
        "cache must NOT be called when config shape is invalid"
    )

    bad_config = {"dimension_filters": ["Geography", "Canada"]}  # list, not dict

    with pytest.raises(ValidationError):
        await service.upsert_validated(
            cube_id="18-10-0004",
            product_id=18100004,
            semantic_key="cpi.k",
            label="L",
            description=None,
            config=bad_config,
            is_active=True,
            updated_by=None,
        )

    mock_cache.get_or_fetch.assert_not_called()


@pytest.mark.asyncio
async def test_validation_cube_product_mismatch_takes_precedence_over_dim_or_member_errors(
    service, mock_cache
):
    # Cache returns a row whose product_id is 18100004; caller passes a
    # different product_id AND bad dim+member. The service must raise the
    # base MetadataValidationError with code CUBE_PRODUCT_MISMATCH, not
    # the DimensionMismatch / MemberMismatch subclasses.
    mock_cache.get_or_fetch.return_value = _cache_entry(product_id=18100004)
    bad_config = _valid_config()
    bad_config["dimension_filters"] = {
        "Province": "Ontario",  # DIMENSION_NOT_FOUND
        "Geography": "Atlantis",  # MEMBER_NOT_FOUND
    }

    with pytest.raises(MetadataValidationError) as exc_info:
        await service.upsert_validated(
            cube_id="18-10-0004",
            product_id=99999999,
            semantic_key="cpi.k",
            label="L",
            description=None,
            config=bad_config,
            is_active=True,
            updated_by=None,
        )

    assert exc_info.value.error_code == "CUBE_PRODUCT_MISMATCH"
    assert not isinstance(exc_info.value, DimensionMismatchError)
    assert not isinstance(exc_info.value, MemberMismatchError)


# ---------------------------------------------------------------------------
# Phase 3.1b — bulk validated upsert (validate-all-then-decide)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upsert_many_validated_rolls_back_on_first_invalid_item(
    service, session_factory, mock_cache
):
    """File atomicity regression: when ANY item fails validation, NO rows
    from the batch are persisted. Compares row count before/after.
    """
    from src.services.semantic_mappings.exceptions import (
        BulkUpsertItem,
        BulkValidationError,
    )

    mock_cache.get_or_fetch.return_value = _cache_entry()

    good = BulkUpsertItem(
        cube_id="18-10-0004",
        product_id=18100004,
        semantic_key="cpi.canada.all_items.index",
        label="good",
        description=None,
        config=_valid_config(),
        is_active=True,
    )
    bad_config = _valid_config()
    bad_config["dimension_filters"] = {"Geography": "Atlantis"}
    bad = BulkUpsertItem(
        cube_id="18-10-0004",
        product_id=18100004,
        semantic_key="cpi.canada.bad",
        label="bad",
        description=None,
        config=bad_config,
        is_active=True,
    )

    async with session_factory() as session:
        before = (
            await session.execute(
                __import__("sqlalchemy").text(
                    "SELECT COUNT(*) FROM semantic_mappings"
                )
            )
        ).scalar_one()
    assert before == 0

    with pytest.raises(BulkValidationError) as exc_info:
        await service.upsert_many_validated([good, bad])

    # Per-item results carry the failure detail.
    results = exc_info.value.results
    assert len(results) == 2
    assert results[0].is_valid is True
    assert results[1].is_valid is False
    assert results[1].error_code == "MEMBER_NOT_FOUND"

    async with session_factory() as session:
        after = (
            await session.execute(
                __import__("sqlalchemy").text(
                    "SELECT COUNT(*) FROM semantic_mappings"
                )
            )
        ).scalar_one()
    assert after == 0


@pytest.mark.asyncio
async def test_upsert_many_validated_rolls_back_on_cube_not_in_cache(
    service, session_factory, mock_cache
):
    """Whole-batch failure when ANY item raises CubeNotInCacheError —
    matches founder lock 9 (validate-all-then-decide)."""
    from src.services.semantic_mappings.exceptions import (
        BulkUpsertItem,
        CubeNotInCacheError,
    )

    # First item resolves; second item is a cache miss.
    async def fake_get_or_fetch(cube_id, product_id):
        if cube_id == "18-10-0004":
            return _cache_entry()
        raise StatCanUnavailableError(cube_id=cube_id)

    mock_cache.get_or_fetch.side_effect = fake_get_or_fetch

    items = [
        BulkUpsertItem(
            cube_id="18-10-0004",
            product_id=18100004,
            semantic_key="ok",
            label="ok",
            description=None,
            config=_valid_config(),
            is_active=True,
        ),
        BulkUpsertItem(
            cube_id="99-99-9999",
            product_id=99999999,
            semantic_key="bad",
            label="bad",
            description=None,
            config=_valid_config(),
            is_active=True,
        ),
    ]

    with pytest.raises(CubeNotInCacheError):
        await service.upsert_many_validated(items)

    async with session_factory() as session:
        count = (
            await session.execute(
                __import__("sqlalchemy").text(
                    "SELECT COUNT(*) FROM semantic_mappings"
                )
            )
        ).scalar_one()
    assert count == 0
