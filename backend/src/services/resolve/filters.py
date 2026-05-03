"""Phase 3.1c — query-filter parsing and mapping-shape validation.

Pure adapter layer between the HTTP query string and the validator's
:class:`ResolvedDimensionFilter` DTO that downstream code (``derive_coord``,
``StatCanValueCacheService.auto_prime``) already consumes.

ARCH-PURA-001: both functions here are pure — no I/O, no clock, no logger.
They raise :class:`ResolveInvalidFiltersError` (caught by the router) on
shape problems; they NEVER raise ``HTTPException`` (R2: HTTP translation
happens at the router boundary only).

Encoding choice (recon §2.3 / Appendix B grep B-C): repeated query pairs
``?dim=<position_id>&member=<member_id>`` for FastAPI-native parsing and
parity with how mapping config addresses dimensions today.
"""
from __future__ import annotations

from src.models.semantic_mapping import SemanticMapping
from src.services.resolve.exceptions import ResolveInvalidFiltersError
from src.services.semantic_mappings.validation import ResolvedDimensionFilter


def parse_filters_from_query(
    *, raw_filters: list[tuple[int, int]]
) -> list[ResolvedDimensionFilter]:
    """Convert ``[(dim_position_id, member_id), ...]`` to validator DTOs.

    The router supplies the raw pairs by zipping the repeated ``dim`` and
    ``member`` query params. This helper:

    * rejects mismatched pair lengths implicitly (the router uses
      ``zip(..., strict=False)`` so a length mismatch produces a short
      list — we DON'T need to re-detect it because the validation step
      catches resulting missing dimensions);
    * rejects duplicate ``dimension_position_id`` (each dimension may
      appear at most once);
    * rejects out-of-range positions (the canonical 10-slot encoding in
      :func:`src.services.semantic.coord.derive_coord`).

    The returned ``ResolvedDimensionFilter`` instances populate
    ``dimension_name`` / ``member_name`` with empty strings — the
    validator dataclass requires them but downstream consumers
    (``derive_coord``) only read the numeric IDs. This is a deliberate
    short-circuit: the resolve flow does NOT have access to the cached
    cube metadata at parse time and re-resolving names would require an
    extra cache fetch with no benefit (the names are already encoded
    server-side in ``mapping.config.dimension_filters``).
    """
    seen: set[int] = set()
    out: list[ResolvedDimensionFilter] = []
    for pos, member in raw_filters:
        if pos < 1 or pos > 10:
            raise ResolveInvalidFiltersError(
                reason=(
                    f"dimension_position_id={pos} out of range (1..10)"
                ),
            )
        if pos in seen:
            raise ResolveInvalidFiltersError(
                reason=(
                    f"duplicate dimension_position_id={pos} in filters"
                ),
            )
        seen.add(pos)
        out.append(
            ResolvedDimensionFilter(
                dimension_name="",
                member_name="",
                dimension_position_id=pos,
                member_id=member,
            )
        )
    return out


def validate_filters_against_mapping(
    *,
    filters: list[ResolvedDimensionFilter],
    mapping: SemanticMapping,
) -> None:
    """Ensure the supplied filter set matches the mapping's expected dims.

    The mapping ``config.dimension_filters`` is a ``dict[str, str]``
    keyed by dimension name (Appendix B grep B). For 3.1c we validate
    on COUNT only — the canonical names are not echoed in the query
    string and the position-id ↔ name mapping lives in the cube
    metadata cache (out-of-scope for resolve). A future enhancement
    can grow this into per-name validation when the resolve service
    starts hydrating metadata.

    Rules enforced:
    * required dimensions present (count match: every configured
      filter must be supplied);
    * no extras (the supplied count must not exceed configured count).

    Raises:
        ResolveInvalidFiltersError: with a deterministic reason string
            and the expected/provided dimension lists for the
            ``RESOLVE_INVALID_FILTERS`` envelope (recon §2.5).
    """
    config = mapping.config or {}
    expected_filters: dict[str, str] = {}
    raw = config.get("dimension_filters") if isinstance(config, dict) else None
    if isinstance(raw, dict):
        expected_filters = raw

    expected_names: list[str] = sorted(expected_filters.keys())
    provided_positions: list[str] = sorted(
        str(f.dimension_position_id) for f in filters
    )

    if len(filters) < len(expected_filters):
        raise ResolveInvalidFiltersError(
            reason=(
                f"missing required dimension(s): mapping requires "
                f"{len(expected_filters)} dim(s), got {len(filters)}"
            ),
            expected=expected_names,
            provided=provided_positions,
        )
    if len(filters) > len(expected_filters):
        raise ResolveInvalidFiltersError(
            reason=(
                f"unexpected extra dimension(s): mapping requires "
                f"{len(expected_filters)} dim(s), got {len(filters)}"
            ),
            expected=expected_names,
            provided=provided_positions,
        )


__all__ = [
    "parse_filters_from_query",
    "validate_filters_against_mapping",
]
