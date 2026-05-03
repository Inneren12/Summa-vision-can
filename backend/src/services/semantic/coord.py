"""Phase 3.1aaa: StatCan ``coord`` derivation from validator output.

Pure helper: takes ``ValidationResult.resolved_filters`` from the
3.1ab validator and produces the StatCan native ``coord`` string used
by the WDS data API (e.g.
``getDataFromCubePidCoordAndLatestNPeriods``).

Per founder lock Q-6 (recon §B): validator output reuse is mandatory.
This module deliberately performs no name-matching of its own — it
trusts the (position_id, member_id) pairs already resolved by 3.1ab.
"""
from __future__ import annotations

from src.services.semantic_mappings.validation import ResolvedDimensionFilter

_MAX_DIMENSIONS = 10


def derive_coord(resolved_filters: list[ResolvedDimensionFilter]) -> str:
    """Convert validator-resolved (position_id, member_id) pairs to a coord.

    StatCan's ``coordinate`` argument is a 10-position dot-separated
    string. Each position corresponds to a dimension (1-indexed); a
    value of ``0`` means "all members" / unset. Validator-resolved
    pairs populate the slots their ``dimension_position_id`` indexes.

    Args:
        resolved_filters: Successfully matched (dimension, member) pairs
            from a :class:`ValidationResult`. Order does not matter.

    Returns:
        A 10-position dot-separated string (e.g.
        ``"1.10.0.0.0.0.0.0.0.0"`` for two filtered dimensions).

    Raises:
        ValueError: If a ``dimension_position_id`` is outside ``[1, 10]``
            or if two filters target the same position.

    Pure function — no I/O, no clock, no logger.
    """
    slots = ["0"] * _MAX_DIMENSIONS
    seen_positions: set[int] = set()

    for item in resolved_filters:
        pos = item.dimension_position_id
        member = item.member_id

        if pos < 1 or pos > _MAX_DIMENSIONS:
            raise ValueError(
                f"dimension_position_id out of range: {pos} "
                f"(must be 1..{_MAX_DIMENSIONS})"
            )
        if pos in seen_positions:
            raise ValueError(
                f"duplicate dimension_position_id in resolved_filters: {pos}"
            )

        seen_positions.add(pos)
        slots[pos - 1] = str(member)

    return ".".join(slots)
