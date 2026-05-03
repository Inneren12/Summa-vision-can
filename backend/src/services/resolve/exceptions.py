"""Phase 3.1c — Resolve service exceptions.

Three terminal exception types raised by :class:`ResolveService` and
caught by the admin resolve router (``backend/src/api/routers/admin_resolve.py``):

* :class:`MappingNotFoundForResolveError` — 404 ``MAPPING_NOT_FOUND``
  (C1: missing-or-inactive mapping).
* :class:`ResolveInvalidFiltersError` — 400 ``RESOLVE_INVALID_FILTERS``
  (filter parse / validation failure).
* :class:`ResolveCacheMissError` — 404 ``RESOLVE_CACHE_MISS`` (no row
  after auto-prime + re-query, C2 terminal step).

The service layer NEVER raises ``HTTPException``; the router translates
these typed exceptions into the flat handler-detail envelope (R2).
"""
from __future__ import annotations


class MappingNotFoundForResolveError(Exception):
    """Active SemanticMapping not found for the requested cube/key (C1).

    Inactive mappings are treated identically to "does not exist" per
    recon §1 lock C1 (``get_active_by_key`` filters on ``is_active``).
    """

    def __init__(self, *, cube_id: str, semantic_key: str) -> None:
        self.cube_id = cube_id
        self.semantic_key = semantic_key
        super().__init__(
            f"Semantic mapping not found for cube_id={cube_id!r} "
            f"and semantic_key={semantic_key!r}."
        )


class ResolveInvalidFiltersError(Exception):
    """Filter parse or mapping-shape validation failed.

    Carries the rendered reason string plus the expected/provided
    dimension sets so the router can build the
    ``RESOLVE_INVALID_FILTERS`` envelope verbatim per recon §3.
    """

    def __init__(
        self,
        *,
        reason: str,
        expected: list[str] | None = None,
        provided: list[str] | None = None,
    ) -> None:
        self.reason = reason
        self.expected = expected or []
        self.provided = provided or []
        super().__init__(reason)


class ResolveCacheMissError(Exception):
    """Cache miss after the auto-prime + re-query state machine (C2).

    The router renders the ``RESOLVE_CACHE_MISS`` 404 envelope including
    the service-derived ``coord`` for ops visibility (recon §2.5).
    """

    def __init__(
        self,
        *,
        cube_id: str,
        semantic_key: str,
        coord: str,
        period: str | None,
        prime_attempted: bool,
        prime_error_code: str | None,
    ) -> None:
        self.cube_id = cube_id
        self.semantic_key = semantic_key
        self.coord = coord
        self.period = period
        self.prime_attempted = prime_attempted
        self.prime_error_code = prime_error_code
        super().__init__(
            "No cached value available for requested lookup after prime attempt."
        )


__all__ = [
    "MappingNotFoundForResolveError",
    "ResolveInvalidFiltersError",
    "ResolveCacheMissError",
]
