"""Phase 3.1c — :class:`ResolveService`.

Orchestrates the 8-step state machine documented in recon §5.2:

    1. Load active mapping (C1).
    2. Parse + validate filters.
    3. Derive coord via shared :func:`derive_coord` helper (C3).
    4. Read cache (hit → return).
    5. Auto-prime via :class:`StatCanValueCacheService.auto_prime`.
    6. Re-query cache.
    7. Hit on re-query → return ``cache_status="primed"``.
    8. Still empty → raise :class:`ResolveCacheMissError` (C2 terminal).

Service NEVER raises :class:`HTTPException` — typed exceptions defined
in :mod:`src.services.resolve.exceptions` are translated by the router.
ARCH-DPEN-001: every collaborator is injected through ``__init__``.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Literal

import structlog

from src.models.semantic_mapping import SemanticMapping
from src.repositories.semantic_mapping_repository import (
    SemanticMappingRepository,
)
from src.schemas.resolve import ResolvedValueResponse
from src.services.resolve.exceptions import (
    MappingNotFoundForResolveError,
    ResolveCacheMissError,
    ResolveInvalidFiltersError,
)
from src.services.resolve.filters import (
    parse_filters_from_query,
    validate_filters_against_mapping,
)
from src.services.resolve.frequency import resolve_frequency_code
from src.services.resolve.period import pick_row
from src.services.semantic.coord import derive_coord
from src.services.statcan.metadata_cache import StatCanMetadataCacheService
from src.services.statcan.value_cache import StatCanValueCacheService
from src.services.statcan.value_cache_schemas import ValueCacheRow
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


def map_to_resolved(
    row: ValueCacheRow,
    mapping: SemanticMapping,
    *,
    cache_status: Literal["hit", "primed"],
) -> ResolvedValueResponse:
    """Build a :class:`ResolvedValueResponse` from a cache row + mapping.

    Verbatim from impl-addendum §"REPLACEMENT — Phase 5 ``map_to_resolved``
    semantics" — ``row.value is None`` MUST yield DTO ``value=None``,
    NEVER the literal string ``"None"`` (F-fix-3).

    ``canonical_str`` choice: ``f"{row.value}"`` matches the existing
    ``ResolvedValue`` DTO precedent in ``value_cache_schemas.py`` (the
    project already serialises Decimal via ``str(...)`` for the wire);
    Decimal's ``__str__`` is deterministic and preserves precision.
    """
    # Critical: never str(None) → "None"
    value_str: str | None
    if row.value is None:
        value_str = None
    else:
        # canonical_str: Decimal's __str__ — preserves precision, matches
        # the existing ResolvedValue DTO serialization pattern.
        value_str = f"{row.value}"

    unit_raw = (
        mapping.config.get("unit") if isinstance(mapping.config, dict) else None
    )
    units = unit_raw if isinstance(unit_raw, str) else None

    return ResolvedValueResponse(
        cube_id=row.cube_id,
        semantic_key=row.semantic_key,
        coord=row.coord,
        period=row.ref_period,
        value=value_str,
        missing=row.missing,
        resolved_at=row.fetched_at,
        source_hash=row.source_hash,
        is_stale=row.is_stale,
        units=units,
        cache_status=cache_status,
        mapping_version=getattr(mapping, "version", None),
    )


def sanitize_prime_error(error: str | None) -> str | None:
    """Squeeze :class:`AutoPrimeResult.error` into a short ops code.

    The auto-prime error string is one of ``"coord: ..."``,
    ``"parse: ..."``, ``"persist: ..."`` or a raw upstream message; we
    keep the leading category token (or ``"upstream"``) so the
    ``RESOLVE_CACHE_MISS`` envelope and structured log carry a stable
    label without leaking implementation detail.
    """
    if error is None:
        return None
    head = error.split(":", 1)[0].strip()
    if head in {"coord", "parse", "persist"}:
        return head
    return "upstream"


class ResolveService:
    """Read-side orchestrator for the singular admin resolve endpoint."""

    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession],
        mapping_repository_factory: Callable[
            [AsyncSession], SemanticMappingRepository
        ],
        value_cache_service: StatCanValueCacheService,
        metadata_cache: StatCanMetadataCacheService,
        logger: structlog.stdlib.BoundLogger,
    ) -> None:
        self._session_factory = session_factory
        self._mapping_repository_factory = mapping_repository_factory
        self._value_cache_service = value_cache_service
        self._metadata_cache = metadata_cache
        self._logger = logger

    async def resolve_value(
        self,
        *,
        cube_id: str,
        semantic_key: str,
        dims: list[int],
        members: list[int],
        period: str | None,
    ) -> ResolvedValueResponse:
        """Execute the 8-step resolve state machine.

        See module docstring for the full sequence. Pure orchestration
        — every leaf I/O lives in an injected collaborator.
        """
        # Step 1 — active mapping lookup (C1).
        async with self._session_factory() as session:
            mapping_repo = self._mapping_repository_factory(session)
            mapping = await mapping_repo.get_active_by_key(
                cube_id, semantic_key
            )
        if mapping is None:
            raise MappingNotFoundForResolveError(
                cube_id=cube_id, semantic_key=semantic_key
            )

        # Step 2 — parse + validate filters.
        filters = parse_filters_from_query(dims=dims, members=members)
        await validate_filters_against_mapping(
            filters=filters,
            mapping=mapping,
            metadata_cache=self._metadata_cache,
        )

        # Step 3 — service-derived coord (C3).
        try:
            coord = derive_coord(filters)
        except ValueError as exc:
            # derive_coord enforces position uniqueness/range; our
            # parser already rejects these but we re-raise as
            # RESOLVE_INVALID_FILTERS for defense in depth.
            raise ResolveInvalidFiltersError(reason=str(exc)) from exc

        # Step 4 — first cache read.
        rows = await self._value_cache_service.get_cached(
            cube_id=cube_id,
            semantic_key=semantic_key,
            coord=coord,
            ref_period=period,
        )
        if rows:
            row = pick_row(rows, period=period)
            return map_to_resolved(row, mapping, cache_status="hit")

        # Step 5 — auto-prime (best-effort; never raises into the caller).
        frequency_code = await resolve_frequency_code(
            mapping=mapping, metadata_cache=self._metadata_cache
        )
        prime_result = None
        prime_error_code: str | None = None
        try:
            prime_result = await self._value_cache_service.auto_prime(
                cube_id=cube_id,
                semantic_key=semantic_key,
                product_id=mapping.product_id,
                resolved_filters=filters,
                frequency_code=frequency_code,
            )
        except Exception:  # noqa: BLE001
            self._logger.exception(
                "resolve.auto_prime_unexpected_error",
                cube_id=cube_id,
                semantic_key=semantic_key,
                coord=coord,
            )
            prime_error_code = "unexpected"
        else:
            if prime_result.error:
                prime_error_code = sanitize_prime_error(prime_result.error)

        # Step 6 — re-query under identical lookup args (MUST run even if
        # auto_prime raised: the upstream operation may have partially
        # succeeded and persisted the row before the failure surfaced).
        rows_after = await self._value_cache_service.get_cached(
            cube_id=cube_id,
            semantic_key=semantic_key,
            coord=coord,
            ref_period=period,
        )

        # Step 7 — primed hit.
        if rows_after:
            if prime_error_code is not None:
                self._logger.warning(
                    "resolve.prime_succeeded_with_error",
                    cube_id=cube_id,
                    semantic_key=semantic_key,
                    coord=coord,
                    error_code=prime_error_code,
                )
            row = pick_row(rows_after, period=period)
            return map_to_resolved(row, mapping, cache_status="primed")

        # Step 8 — terminal miss (C2).
        raise ResolveCacheMissError(
            cube_id=cube_id,
            semantic_key=semantic_key,
            coord=coord,
            period=period,
            prime_attempted=True,
            prime_error_code=prime_error_code,
        )


__all__ = ["ResolveService", "map_to_resolved", "sanitize_prime_error"]
