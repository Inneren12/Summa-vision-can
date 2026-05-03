"""Phase 3.1aaa: source_hash unit tests.

Critical invariants:
* Identical content → identical hash (pure function).
* Any data change → hash changes.
* Timestamps (fetched_at, release_time, created_at, updated_at) are
  NOT inputs — refreshing a row with new fetched_at must NOT change
  source_hash, otherwise the nightly refresh always reports "updated".
"""
from __future__ import annotations

from decimal import Decimal

from src.services.statcan.value_cache_hash import compute_source_hash


def _kwargs(**overrides):
    base = dict(
        product_id=18100004,
        cube_id="18-10-0004-01",
        semantic_key="cpi.canada.all_items",
        coord="1.10.0.0.0.0.0.0.0.0",
        ref_period="2026-04",
        value=Decimal("123.456"),
        missing=False,
        decimals=1,
        scalar_factor_code=0,
        symbol_code=0,
        security_level_code=0,
        status_code=0,
        frequency_code=6,
        vector_id=42,
        response_status_code=0,
    )
    base.update(overrides)
    return base


class TestSourceHash:
    def test_deterministic_identical_input(self) -> None:
        assert compute_source_hash(**_kwargs()) == compute_source_hash(**_kwargs())

    def test_value_change_changes_hash(self) -> None:
        a = compute_source_hash(**_kwargs(value=Decimal("1.0")))
        b = compute_source_hash(**_kwargs(value=Decimal("2.0")))
        assert a != b

    def test_none_value_handled(self) -> None:
        h = compute_source_hash(**_kwargs(value=None, missing=True))
        # Distinct from a populated value.
        assert h != compute_source_hash(**_kwargs())

    def test_missing_flag_changes_hash(self) -> None:
        assert compute_source_hash(**_kwargs(missing=True)) != compute_source_hash(
            **_kwargs(missing=False)
        )

    def test_decimal_precision_preserved(self) -> None:
        # str(Decimal) preserves trailing zeros — these MUST be distinct
        # so that 123.4 and 123.40 are not confused.
        a = compute_source_hash(**_kwargs(value=Decimal("123.4")))
        b = compute_source_hash(**_kwargs(value=Decimal("123.40")))
        assert a != b
