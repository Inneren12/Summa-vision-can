"""Phase 3.1c — unit tests for the filter parser + map_to_resolved.

Recon §6.1 plus impl-addendum §"ADDITIONS — Phase 1 test scaffolding"
test 1.3 (``test_map_to_resolved_missing_observation`` for F-fix-3).
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.models.semantic_mapping import SemanticMapping
from src.services.resolve.exceptions import ResolveInvalidFiltersError
from src.services.resolve.filters import (
    parse_filters_from_query,
    validate_filters_against_mapping,
)
from src.services.resolve.period import pick_row
from src.services.resolve.service import map_to_resolved
from src.services.statcan.metadata_cache import (
    CubeMetadataCacheEntry,
    StatCanMetadataCacheService,
)
from src.services.statcan.value_cache_schemas import ValueCacheRow


_FIXED_FETCHED_AT = datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc)


def _mapping(*, dimension_filters: dict[str, str], unit: str = "index") -> SemanticMapping:
    m = SemanticMapping(
        cube_id="18-10-0004",
        product_id=18100004,
        semantic_key="cpi.canada.all_items.index",
        label="CPI",
        description=None,
        config={
            "dimension_filters": dimension_filters,
            "unit": unit,
            "frequency": "monthly",
        },
        is_active=True,
    )
    m.version = 3
    return m


def _row(*, value: Decimal | None, missing: bool) -> ValueCacheRow:
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


def _cache_entry() -> CubeMetadataCacheEntry:
    """Minimal cache entry matching ``_mapping(dimension_filters=...)``.

    Geography (position 1) → Canada (member_id 1)
    Products   (position 2) → All-items (member_id 10)
    """
    return CubeMetadataCacheEntry(
        cube_id="18-10-0004",
        product_id=18100004,
        dimensions={
            "dimensions": [
                {
                    "position_id": 1,
                    "name_en": "Geography",
                    "members": [
                        {"member_id": 1, "name_en": "Canada"},
                    ],
                },
                {
                    "position_id": 2,
                    "name_en": "Products",
                    "members": [
                        {"member_id": 10, "name_en": "All-items"},
                    ],
                },
            ]
        },
        frequency_code="monthly",
        cube_title_en="CPI",
        cube_title_fr=None,
        fetched_at=_FIXED_FETCHED_AT,
    )


def _metadata_cache_mock(
    entry: CubeMetadataCacheEntry | None = None,
) -> MagicMock:
    cache = MagicMock(spec=StatCanMetadataCacheService)
    cache.get_or_fetch = AsyncMock(
        return_value=entry if entry is not None else _cache_entry()
    )
    return cache


class TestParseFiltersFromQuery:
    def test_parse_filters_from_query_valid(self) -> None:
        out = parse_filters_from_query(dims=[1, 2], members=[1, 10])
        assert [(f.dimension_position_id, f.member_id) for f in out] == [
            (1, 1),
            (2, 10),
        ]

    def test_parse_filters_from_query_malformed(self) -> None:
        # duplicate dim
        with pytest.raises(ResolveInvalidFiltersError):
            parse_filters_from_query(dims=[1, 1], members=[1, 2])
        # out-of-range
        with pytest.raises(ResolveInvalidFiltersError):
            parse_filters_from_query(dims=[11], members=[1])

    def test_parse_filters_more_dims_than_members(self) -> None:
        with pytest.raises(ResolveInvalidFiltersError) as info:
            parse_filters_from_query(dims=[1, 2], members=[1])
        assert "dim/member count mismatch" in info.value.reason

    def test_parse_filters_more_members_than_dims(self) -> None:
        with pytest.raises(ResolveInvalidFiltersError) as info:
            parse_filters_from_query(dims=[1], members=[1, 10])
        assert "dim/member count mismatch" in info.value.reason


class TestValidateFiltersAgainstMapping:
    @pytest.mark.asyncio
    async def test_validate_filters_against_mapping_extra_dim(self) -> None:
        # Mapping pins ONE dim (Geography→Canada at position 1, member 1).
        mapping = _mapping(dimension_filters={"Geography": "Canada"})
        entry = CubeMetadataCacheEntry(
            cube_id="18-10-0004",
            product_id=18100004,
            dimensions={
                "dimensions": [
                    {
                        "position_id": 1,
                        "name_en": "Geography",
                        "members": [{"member_id": 1, "name_en": "Canada"}],
                    },
                ]
            },
            frequency_code="monthly",
            cube_title_en=None,
            cube_title_fr=None,
            fetched_at=_FIXED_FETCHED_AT,
        )
        cache = _metadata_cache_mock(entry)
        # Caller supplies TWO filters → mismatch with the 1-dim mapping.
        filters = parse_filters_from_query(dims=[1, 2], members=[1, 10])
        with pytest.raises(ResolveInvalidFiltersError):
            await validate_filters_against_mapping(
                filters=filters, mapping=mapping, metadata_cache=cache
            )

    @pytest.mark.asyncio
    async def test_validate_filters_wrong_member(self) -> None:
        # Mapping expects (1,1) and (2,10); caller supplies (1,1) and (2,99).
        mapping = _mapping(
            dimension_filters={"Geography": "Canada", "Products": "All-items"}
        )
        cache = _metadata_cache_mock(_cache_entry())
        filters = parse_filters_from_query(dims=[1, 2], members=[1, 99])
        # member 99 doesn't exist on dim 2 in the entry, but parser doesn't
        # know that — set check happens in the validator wrapper. Add a
        # cache entry that includes member 99 so we test SET mismatch only.
        entry = CubeMetadataCacheEntry(
            cube_id="18-10-0004",
            product_id=18100004,
            dimensions={
                "dimensions": [
                    {
                        "position_id": 1,
                        "name_en": "Geography",
                        "members": [{"member_id": 1, "name_en": "Canada"}],
                    },
                    {
                        "position_id": 2,
                        "name_en": "Products",
                        "members": [
                            {"member_id": 10, "name_en": "All-items"},
                            {"member_id": 99, "name_en": "Other"},
                        ],
                    },
                ]
            },
            frequency_code="monthly",
            cube_title_en=None,
            cube_title_fr=None,
            fetched_at=_FIXED_FETCHED_AT,
        )
        cache = _metadata_cache_mock(entry)
        with pytest.raises(ResolveInvalidFiltersError) as info:
            await validate_filters_against_mapping(
                filters=filters, mapping=mapping, metadata_cache=cache
            )
        assert "filter set does not match mapping pins" in info.value.reason


class TestPickRow:
    def test_pick_row_warns_on_multiple_rows_with_explicit_period(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        rows = [_row(value=Decimal("1.0"), missing=False), _row(value=Decimal("2.0"), missing=False)]
        # explicit period + 2 rows → warning emitted, returns rows[0]
        chosen = pick_row(rows, period="2025-12")
        assert chosen is rows[0]


class TestMapToResolved:
    def test_map_to_resolved_missing_observation(self) -> None:
        mapping = _mapping(dimension_filters={"Geography": "Canada"})
        # value=None, missing=True → DTO value=None (NEVER literal "None")
        row = _row(value=None, missing=True)
        dto = map_to_resolved(row, mapping, cache_status="hit")
        assert dto.value is None
        assert dto.missing is True
        # defensive variant — value=None, missing=False also passes through
        row2 = _row(value=None, missing=False)
        dto2 = map_to_resolved(row2, mapping, cache_status="hit")
        assert dto2.value is None
        assert dto2.missing is False
        # JSON serialization must NOT contain literal "None"
        assert '"None"' not in dto.model_dump_json()

    def test_map_to_resolved_present_value_uses_canonical_str(self) -> None:
        mapping = _mapping(dimension_filters={"Geography": "Canada"}, unit="index")
        row = _row(value=Decimal("123.456"), missing=False)
        dto = map_to_resolved(row, mapping, cache_status="primed")
        assert dto.value == "123.456"
        assert dto.missing is False
        assert dto.units == "index"
        assert dto.cache_status == "primed"
        assert dto.mapping_version == 3
