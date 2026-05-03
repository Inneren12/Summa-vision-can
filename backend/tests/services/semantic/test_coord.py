"""Phase 3.1aaa: derive_coord pure helper unit tests."""
from __future__ import annotations

import pytest

from src.services.semantic.coord import derive_coord
from src.services.semantic_mappings.validation import ResolvedDimensionFilter


def _f(pos: int, member: int) -> ResolvedDimensionFilter:
    return ResolvedDimensionFilter(
        dimension_name=f"d{pos}",
        member_name=f"m{member}",
        dimension_position_id=pos,
        member_id=member,
    )


class TestDeriveCoord:
    def test_two_dimensions(self) -> None:
        coord = derive_coord([_f(1, 1), _f(2, 10)])
        assert coord == "1.10.0.0.0.0.0.0.0.0"

    def test_five_dimensions_out_of_order(self) -> None:
        coord = derive_coord(
            [_f(5, 99), _f(1, 1), _f(3, 7), _f(2, 4), _f(4, 12)]
        )
        assert coord == "1.4.7.12.99.0.0.0.0.0"

    def test_empty_filters_yields_all_zeros(self) -> None:
        assert derive_coord([]) == "0.0.0.0.0.0.0.0.0.0"

    def test_gap_in_positions_keeps_zero(self) -> None:
        # Position 1 set, position 3 set, position 2 left as 0.
        assert derive_coord([_f(1, 1), _f(3, 5)]) == "1.0.5.0.0.0.0.0.0.0"

    def test_invalid_position_low(self) -> None:
        with pytest.raises(ValueError, match="out of range"):
            derive_coord([_f(0, 1)])

    def test_invalid_position_high(self) -> None:
        with pytest.raises(ValueError, match="out of range"):
            derive_coord([_f(11, 1)])

    def test_duplicate_position_raises(self) -> None:
        with pytest.raises(ValueError, match="duplicate"):
            derive_coord([_f(1, 1), _f(1, 2)])
