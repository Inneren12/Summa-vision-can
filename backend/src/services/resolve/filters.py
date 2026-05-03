"""Phase 3.1c — query-filter parsing and mapping-shape validation.

Pure adapter layer between the HTTP query string and the validator's
:class:`ResolvedDimensionFilter` DTO that downstream code (``derive_coord``,
``StatCanValueCacheService.auto_prime``) already consumes.

ARCH-PURA-001: :func:`parse_filters_from_query` is pure (no I/O, no clock,
no logger). :func:`validate_filters_against_mapping` is async and consults
the injected metadata cache (read-through) — it remains free of HTTP and
clock concerns and never raises ``HTTPException`` (R2: HTTP translation
happens at the router boundary only). It raises
:class:`ResolveInvalidFiltersError` on shape problems.

Encoding choice (recon §2.3 / Appendix B grep B-C): repeated query pairs
``?dim=<position_id>&member=<member_id>`` for FastAPI-native parsing and
parity with how mapping config addresses dimensions today.
"""
from __future__ import annotations

from src.models.semantic_mapping import SemanticMapping
from src.services.resolve.exceptions import ResolveInvalidFiltersError
from src.services.semantic_mappings.validation import (
    ResolvedDimensionFilter,
    validate_mapping_against_cache,
)
from src.services.statcan.metadata_cache import (
    CubeNotFoundError,
    MetadataCacheError,
    StatCanMetadataCacheService,
)


def parse_filters_from_query(
    *, dims: list[int], members: list[int]
) -> list[ResolvedDimensionFilter]:
    """Convert parallel ``dims`` / ``members`` query lists to validator DTOs.

    The router supplies the raw repeated query parameters as parallel
    lists. This helper:

    * rejects mismatched list lengths (``dim/member count mismatch``);
    * rejects duplicate ``dimension_position_id`` (each dimension may
      appear at most once);
    * rejects out-of-range positions (the canonical 10-slot encoding in
      :func:`src.services.semantic.coord.derive_coord`).

    The returned ``ResolvedDimensionFilter`` instances populate
    ``dimension_name`` / ``member_name`` with empty strings — the
    validator dataclass requires them but downstream consumers
    (``derive_coord``) only read the numeric IDs.
    """
    if len(dims) != len(members):
        raise ResolveInvalidFiltersError(
            reason=(
                f"dim/member count mismatch: got {len(dims)} dim(s) and "
                f"{len(members)} member(s)"
            ),
        )

    seen: set[int] = set()
    out: list[ResolvedDimensionFilter] = []
    for pos, member in zip(dims, members, strict=True):
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


async def validate_filters_against_mapping(
    *,
    filters: list[ResolvedDimensionFilter],
    mapping: SemanticMapping,
    metadata_cache: StatCanMetadataCacheService,
) -> None:
    """Validate the supplied filter set against the mapping's pinned cell.

    Strategy (founder-ratified F1, Option A — wrapper):

    1. Fetch the cube metadata cache entry for ``mapping.cube_id`` /
       ``mapping.product_id``.
    2. Re-run the pure 3.1ab :func:`validate_mapping_against_cache`
       against the mapping's ``config.dimension_filters`` (name-based)
       to obtain the canonical ``(position_id, member_id)`` set the
       mapping pins.
    3. Compare that canonical set element-wise to the filter set the
       caller supplied. Any mismatch (extra, missing, wrong position,
       or wrong member id) raises ``RESOLVE_INVALID_FILTERS``.

    This guarantees the resolve flow only proceeds when the request's
    ``(dim, member)`` pairs are *identical* to the cell the mapping
    canonically points at — preventing silent coord drift.

    Raises:
        ResolveInvalidFiltersError: on cache fetch failure, on broken
            mapping config, or on filter-set mismatch.
    """
    try:
        cache_entry = await metadata_cache.get_or_fetch(
            mapping.cube_id, mapping.product_id
        )
    except CubeNotFoundError as exc:
        raise ResolveInvalidFiltersError(
            reason=(
                f"cube metadata not found for cube_id={mapping.cube_id!r} "
                f"product_id={mapping.product_id}"
            ),
        ) from exc
    except MetadataCacheError as exc:
        raise ResolveInvalidFiltersError(
            reason=f"cube metadata fetch failed: {exc}",
        ) from exc

    config = mapping.config or {}
    raw = config.get("dimension_filters")
    dimension_filters_cfg: dict[str, str] = (
        raw if isinstance(raw, dict) else {}
    )

    result = validate_mapping_against_cache(
        cube_id=mapping.cube_id,
        product_id=mapping.product_id,
        dimension_filters=dimension_filters_cfg,
        cache_entry=cache_entry,
    )

    if not result.is_valid:
        error_messages = "; ".join(e.message for e in result.errors)
        raise ResolveInvalidFiltersError(
            reason=(
                "mapping config invalid against cube metadata: "
                f"{error_messages}"
            ),
        )

    expected_set = {
        (rf.dimension_position_id, rf.member_id)
        for rf in result.resolved_filters
    }
    provided_set = {
        (f.dimension_position_id, f.member_id) for f in filters
    }

    if expected_set != provided_set:
        expected_sorted = sorted(expected_set)
        provided_sorted = sorted(provided_set)
        expected_str = [
            f"({pos},{mid})" for pos, mid in expected_sorted
        ]
        provided_str = [
            f"({pos},{mid})" for pos, mid in provided_sorted
        ]
        raise ResolveInvalidFiltersError(
            reason="filter set does not match mapping pins",
            expected=expected_str,
            provided=provided_str,
        )


__all__ = [
    "parse_filters_from_query",
    "validate_filters_against_mapping",
]
