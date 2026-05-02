"""Phase 3.1ab: pure-function tests for SemanticMapping validator.

ARCH-PURA-001: validator is a pure function — these tests use no async
fixtures, no mocks, no I/O. Each test constructs an in-memory
:class:`CubeMetadataCacheEntry` and asserts on the returned
:class:`ValidationResult`.
"""
from __future__ import annotations

from datetime import datetime, timezone

from src.services.semantic_mappings.validation import (
    ResolvedDimensionFilter,
    ValidationError,
    ValidationResult,
    validate_mapping_against_cache,
)
from src.services.statcan.metadata_cache import CubeMetadataCacheEntry


_FIXED_FETCHED_AT = datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc)


def _entry(
    *,
    product_id: int = 18100004,
    cube_id: str = "18-10-0004",
    dimensions: dict | None = None,
) -> CubeMetadataCacheEntry:
    """Construct a cache entry with the canonical Geography/Products shape."""
    if dimensions is None:
        dimensions = {
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
                        {
                            "member_id": 2,
                            "name_en": "Ontario",
                            "name_fr": "Ontario",
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
                        {
                            "member_id": 11,
                            "name_en": "Food",
                            "name_fr": "Aliments",
                        },
                    ],
                },
            ]
        }
    return CubeMetadataCacheEntry(
        cube_id=cube_id,
        product_id=product_id,
        dimensions=dimensions,
        frequency_code="6",
        cube_title_en="CPI",
        cube_title_fr="IPC",
        fetched_at=_FIXED_FETCHED_AT,
    )


def test_valid_mapping_returns_is_valid_true_with_resolved_filters() -> None:
    result = validate_mapping_against_cache(
        cube_id="18-10-0004",
        product_id=18100004,
        dimension_filters={"Geography": "Canada", "Products": "All-items"},
        cache_entry=_entry(),
    )

    assert isinstance(result, ValidationResult)
    assert result.is_valid is True
    assert result.errors == []
    assert result.resolved_filters == [
        ResolvedDimensionFilter(
            dimension_name="Geography",
            member_name="Canada",
            dimension_position_id=1,
            member_id=1,
        ),
        ResolvedDimensionFilter(
            dimension_name="Products",
            member_name="All-items",
            dimension_position_id=2,
            member_id=10,
        ),
    ]


def test_cube_product_mismatch_returns_error_with_correct_message() -> None:
    result = validate_mapping_against_cache(
        cube_id="18-10-0004",
        product_id=99999999,
        dimension_filters={"Geography": "Canada"},
        cache_entry=_entry(product_id=18100004),
    )

    assert result.is_valid is False
    mismatches = [
        e for e in result.errors if e.error_code == "CUBE_PRODUCT_MISMATCH"
    ]
    assert len(mismatches) == 1
    err: ValidationError = mismatches[0]
    assert err.dimension_name is None
    assert err.member_name is None
    assert "99999999" in err.message
    assert "18100004" in err.message


def test_dimension_not_found_returns_error_with_dimension_name_populated() -> None:
    result = validate_mapping_against_cache(
        cube_id="18-10-0004",
        product_id=18100004,
        dimension_filters={"Province": "Quebec"},
        cache_entry=_entry(),
    )

    assert result.is_valid is False
    assert result.resolved_filters == []
    assert len(result.errors) == 1
    err = result.errors[0]
    assert err.error_code == "DIMENSION_NOT_FOUND"
    assert err.dimension_name == "Province"
    assert err.member_name == "Quebec"
    assert err.resolved_dimension_position_id is None
    assert err.resolved_member_id is None


def test_member_not_found_returns_error_with_dimension_resolved_member_unresolved() -> None:
    result = validate_mapping_against_cache(
        cube_id="18-10-0004",
        product_id=18100004,
        dimension_filters={"Geography": "Atlantis"},
        cache_entry=_entry(),
    )

    assert result.is_valid is False
    assert result.resolved_filters == []
    assert len(result.errors) == 1
    err = result.errors[0]
    assert err.error_code == "MEMBER_NOT_FOUND"
    assert err.dimension_name == "Geography"
    assert err.member_name == "Atlantis"
    # Dimension was matched — its position_id is resolved.
    assert err.resolved_dimension_position_id == 1
    # Member was not matched — id stays None.
    assert err.resolved_member_id is None


def test_multiple_errors_collected_not_short_circuited() -> None:
    result = validate_mapping_against_cache(
        cube_id="18-10-0004",
        product_id=99999999,  # triggers CUBE_PRODUCT_MISMATCH
        dimension_filters={
            "Province": "Quebec",  # triggers DIMENSION_NOT_FOUND
            "Geography": "Atlantis",  # triggers MEMBER_NOT_FOUND
        },
        cache_entry=_entry(product_id=18100004),
    )

    assert result.is_valid is False
    codes = sorted(e.error_code for e in result.errors)
    assert codes == [
        "CUBE_PRODUCT_MISMATCH",
        "DIMENSION_NOT_FOUND",
        "MEMBER_NOT_FOUND",
    ]


def test_normalization_handles_case_and_whitespace() -> None:
    result = validate_mapping_against_cache(
        cube_id="18-10-0004",
        product_id=18100004,
        dimension_filters={"  GEOGRAPHY ": "  canada  "},
        cache_entry=_entry(),
    )

    assert result.is_valid is True
    assert len(result.resolved_filters) == 1
    # Original (un-normalized) names are preserved on the resolved filter
    # so the caller can echo the user's input back.
    assert result.resolved_filters[0].dimension_name == "  GEOGRAPHY "
    assert result.resolved_filters[0].member_name == "  canada  "
    assert result.resolved_filters[0].dimension_position_id == 1
    assert result.resolved_filters[0].member_id == 1


def test_fuzzy_suggestion_populated_for_close_member_typo() -> None:
    # "All-iems" is one char off "All-items" — get_close_matches should hit.
    result = validate_mapping_against_cache(
        cube_id="18-10-0004",
        product_id=18100004,
        dimension_filters={"Products": "All-iems"},
        cache_entry=_entry(),
    )

    assert result.is_valid is False
    assert len(result.errors) == 1
    err = result.errors[0]
    assert err.error_code == "MEMBER_NOT_FOUND"
    assert err.suggested_member_name_en == "All-items"
    assert "All-items" in err.message
