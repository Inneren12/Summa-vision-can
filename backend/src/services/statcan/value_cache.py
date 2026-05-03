"""Phase 3.1aaa: ``StatCanValueCacheService``.

Sits between the value-cache repository and the StatCan WDS data
endpoint. Two write entrypoints:

* :meth:`auto_prime` — sync, BEST-EFFORT prime invoked from the
  semantic-mapping upsert flow. Founder lock Q-3 RE-LOCK: failures
  here MUST NOT propagate to the caller; the mapping save proceeds
  regardless.
* :meth:`refresh_all` — nightly scheduler entry. Iterates the active
  set of (cube_id, semantic_key, coord) lookup keys, fans out via
  :meth:`StatCanClient.get_data_batch`, and upserts results in
  conservative ``batch_size`` chunks.

Read entrypoint :meth:`get_cached` is consumed by 3.1c (deferred).

Architecture notes (mirrors :class:`StatCanMetadataCacheService`):
* short-lived sessions via ``async_sessionmaker`` factory;
* ARCH-DPEN-001 dependency injection for every collaborator;
* DTOs (frozen dataclasses) at the service boundary, never ORM rows.
"""
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Final

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.exceptions import DataSourceError
from src.repositories.semantic_mapping_repository import (
    SemanticMappingRepository,
)
from src.repositories.semantic_value_cache_repository import (
    SemanticValueCacheRepository,
)
from src.services.semantic.coord import derive_coord
from src.services.semantic_mappings.validation import ResolvedDimensionFilter
from src.services.statcan.client import StatCanClient
from src.services.statcan.metadata_cache import StatCanMetadataCacheService
from src.services.statcan.value_cache_hash import compute_source_hash
from src.services.statcan.value_cache_schemas import (
    AutoPrimeResult,
    RefreshSummary,
    StatCanDataResponse,
    ValueCacheRow,
)


# StatCan frequency_code → retention default (recon §C2). Codes per
# the WDS reference: 6=monthly, 9=quarterly, 12=annual.
_FREQ_RETENTION: Final[dict[int, int]] = {
    6: 12,   # monthly → 12 months
    9: 8,    # quarterly → 8 quarters (~2 years)
    12: 10,  # annual → 10 years
}


class StatCanValueCacheService:
    """Façade around the value-cache repository + StatCan data API."""

    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession],
        repository_factory: Callable[
            [AsyncSession], SemanticValueCacheRepository
        ],
        mapping_repository_factory: Callable[
            [AsyncSession], SemanticMappingRepository
        ],
        cube_metadata_cache: StatCanMetadataCacheService,
        statcan_client: StatCanClient,
        clock: Callable[[], datetime],
        logger: structlog.stdlib.BoundLogger,
        retention_count_default: int = 12,
        batch_size: int = 100,
    ) -> None:
        self._session_factory = session_factory
        self._repository_factory = repository_factory
        self._mapping_repository_factory = mapping_repository_factory
        self._metadata_cache = cube_metadata_cache
        self._client = statcan_client
        self._clock = clock
        self._logger = logger
        self._retention_count_default = retention_count_default
        self._batch_size = batch_size

    # ------------------------------------------------------------------
    # Auto-prime (mapping-save path)
    # ------------------------------------------------------------------

    async def auto_prime(
        self,
        *,
        cube_id: str,
        semantic_key: str,
        product_id: int,
        resolved_filters: list[ResolvedDimensionFilter],
        frequency_code: int | None = None,
    ) -> AutoPrimeResult:
        """Sync, BEST-EFFORT prime of recent periods for a single mapping.

        Per founder lock Q-3 RE-LOCK: every failure path returns an
        :class:`AutoPrimeResult` with a populated ``error`` field, NEVER
        raises. Caller (mapping service) treats a non-``None`` ``error``
        as a warning and proceeds with the mapping save.
        """
        try:
            coord = derive_coord(resolved_filters)
        except ValueError as exc:
            self._logger.warning(
                "value_cache.auto_prime.coord_invalid",
                cube_id=cube_id,
                semantic_key=semantic_key,
                error=str(exc),
            )
            return AutoPrimeResult(0, 0, 0, error=f"coord: {exc}")

        latest_n = self._n_for_frequency(frequency_code)

        try:
            response = await self._client.get_data_from_cube_pid_coord_and_latest_n_periods(
                product_id=product_id,
                coord=coord,
                latest_n=latest_n,
            )
        except DataSourceError as exc:
            self._logger.warning(
                "value_cache.auto_prime.statcan_unavailable",
                cube_id=cube_id,
                semantic_key=semantic_key,
                product_id=product_id,
                error=str(exc),
            )
            return AutoPrimeResult(0, 0, 0, error=str(exc))
        except Exception as exc:  # noqa: BLE001
            # Defensive: parsing or validation failures must not surface.
            self._logger.warning(
                "value_cache.auto_prime.parse_failed",
                cube_id=cube_id,
                semantic_key=semantic_key,
                error=str(exc),
            )
            return AutoPrimeResult(0, 0, 0, error=f"parse: {exc}")

        if response is None or not response.vector_data_point:
            self._logger.info(
                "value_cache.auto_prime.empty_response",
                cube_id=cube_id,
                semantic_key=semantic_key,
                product_id=product_id,
            )
            return AutoPrimeResult(0, 0, 0)

        try:
            counts = await self._persist_response(
                cube_id=cube_id,
                product_id=product_id,
                semantic_key=semantic_key,
                coord=coord,
                response=response,
            )
        except Exception as exc:  # noqa: BLE001
            self._logger.warning(
                "value_cache.auto_prime.persist_failed",
                cube_id=cube_id,
                semantic_key=semantic_key,
                error=str(exc),
            )
            return AutoPrimeResult(0, 0, 0, error=f"persist: {exc}")

        return AutoPrimeResult(
            rows_inserted=counts.get("inserted", 0),
            rows_updated=counts.get("updated", 0),
            rows_unchanged=counts.get("unchanged", 0),
        )

    # ------------------------------------------------------------------
    # Nightly refresh
    # ------------------------------------------------------------------

    async def refresh_all(self) -> RefreshSummary:
        """Nightly scheduler entry. Iterates active mappings and refreshes.

        Per-mapping failures are caught + counted; a single bad cube
        does NOT abort the whole job.
        """
        # Snapshot the active set under a short read session.
        async with self._session_factory() as session:
            mapping_repo = self._mapping_repository_factory(session)
            active_mappings, _total = await mapping_repo.list(
                is_active=True, limit=10_000, offset=0
            )

        # Look up frequency_code per mapping from the metadata cache.
        # Nightly refresh re-uses whatever coord(s) we already have rows
        # for — we don't try to re-derive coord from the mapping config
        # here since a single mapping may have produced rows for several
        # coords over its lifetime as the operator edited filters.
        freq_map: dict[tuple[str, str], int | None] = {}
        for mapping in active_mappings:
            cache_entry = await self._metadata_cache.get_cached(mapping.cube_id)
            freq = cache_entry.frequency_code if cache_entry else None
            try:
                freq_int = int(freq) if freq is not None else None
            except (TypeError, ValueError):
                freq_int = None
            freq_map[(mapping.cube_id, mapping.semantic_key)] = freq_int

        # Pull the distinct (cube_id, semantic_key, coord, product_id)
        # tuples we already have rows for. We refresh those.
        async with self._session_factory() as session:
            repo = self._repository_factory(session)
            existing_keys = await repo.list_active_lookup_keys()

        refresh_jobs: list[
            tuple[str, str, str, int, int]  # cube_id, sk, coord, pid, n
        ] = []
        for cube_id, semantic_key, coord, product_id in existing_keys:
            freq = freq_map.get((cube_id, semantic_key))
            n = self._n_for_frequency(freq)
            refresh_jobs.append(
                (cube_id, semantic_key, coord, product_id, n)
            )

        self._logger.info(
            "value_cache.refresh_all.started",
            mappings_processed=len(active_mappings),
            refresh_targets=len(refresh_jobs),
        )

        rows_upserted = 0
        rows_marked_stale = 0
        errors: list[str] = []

        # Sequential per-job batches so a single bad item only dings
        # one mapping/coord pair (recon §A6 conservative path).
        for job in refresh_jobs:
            cube_id, semantic_key, coord, product_id, n = job
            try:
                response = await self._client.get_data_from_cube_pid_coord_and_latest_n_periods(
                    product_id=product_id, coord=coord, latest_n=n
                )
            except DataSourceError as exc:
                self._logger.warning(
                    "value_cache.refresh_all.fetch_failed",
                    cube_id=cube_id,
                    semantic_key=semantic_key,
                    coord=coord,
                    error=str(exc),
                )
                errors.append(
                    f"{cube_id}/{semantic_key}/{coord}: {exc}"
                )
                continue
            if response is None or not response.vector_data_point:
                continue
            try:
                counts = await self._persist_response(
                    cube_id=cube_id,
                    product_id=product_id,
                    semantic_key=semantic_key,
                    coord=coord,
                    response=response,
                )
                rows_upserted += counts.get("inserted", 0) + counts.get(
                    "updated", 0
                )
                # After upsert, mark anything beyond retention stale.
                async with self._session_factory() as session:
                    repo = self._repository_factory(session)
                    marked = await repo.mark_stale_outside_window(
                        cube_id=cube_id,
                        semantic_key=semantic_key,
                        coord=coord,
                        retention_count=n,
                    )
                    await session.commit()
                rows_marked_stale += marked
            except Exception as exc:  # noqa: BLE001
                self._logger.warning(
                    "value_cache.refresh_all.persist_failed",
                    cube_id=cube_id,
                    semantic_key=semantic_key,
                    coord=coord,
                    error=str(exc),
                )
                errors.append(
                    f"{cube_id}/{semantic_key}/{coord}: persist {exc}"
                )

        summary = RefreshSummary(
            mappings_processed=len(active_mappings),
            rows_upserted=rows_upserted,
            rows_marked_stale=rows_marked_stale,
            errors=errors,
        )
        self._logger.info(
            "value_cache.refresh_all.completed",
            mappings_processed=summary.mappings_processed,
            rows_upserted=summary.rows_upserted,
            rows_marked_stale=summary.rows_marked_stale,
            errors=len(summary.errors),
        )
        return summary

    # ------------------------------------------------------------------
    # Reads (consumed by 3.1c)
    # ------------------------------------------------------------------

    async def get_cached(
        self,
        *,
        cube_id: str,
        semantic_key: str,
        coord: str,
        ref_period: str | None = None,
    ) -> list[ValueCacheRow]:
        """Read-only cache lookup. Never calls StatCan."""
        async with self._session_factory() as session:
            repo = self._repository_factory(session)
            rows = await repo.get_by_lookup(
                cube_id=cube_id,
                semantic_key=semantic_key,
                coord=coord,
                ref_period=ref_period,
            )
        return [_row_to_dto(r) for r in rows]

    async def evict_stale(self, retention: timedelta) -> int:
        """Hard-delete rows whose ``fetched_at`` precedes ``now - retention``."""
        cutoff = self._clock() - retention
        async with self._session_factory() as session:
            repo = self._repository_factory(session)
            n = await repo.delete_older_than(cutoff)
            await session.commit()
        self._logger.info(
            "value_cache.evict_stale.completed",
            cutoff=cutoff.isoformat(),
            deleted=n,
        )
        return n

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _n_for_frequency(self, frequency_code: int | None) -> int:
        """N retention by StatCan ``frequency_code``.

        Defaults: monthly(6)→12, quarterly(9)→8, annual(12)→10.
        Unknown → ``retention_count_default`` (12).
        """
        if frequency_code is None:
            return self._retention_count_default
        return _FREQ_RETENTION.get(frequency_code, self._retention_count_default)

    async def _persist_response(
        self,
        *,
        cube_id: str,
        product_id: int,
        semantic_key: str,
        coord: str,
        response: StatCanDataResponse,
    ) -> dict[str, int]:
        """Upsert every data point in ``response`` under one transaction."""
        fetched_at = self._clock()
        counts = {"inserted": 0, "updated": 0, "unchanged": 0}
        async with self._session_factory() as session:
            repo = self._repository_factory(session)
            for dp in response.vector_data_point:
                source_hash = compute_source_hash(
                    product_id=product_id,
                    cube_id=cube_id,
                    semantic_key=semantic_key,
                    coord=coord,
                    ref_period=dp.ref_per,
                    value=dp.value,
                    missing=dp.missing,
                    decimals=dp.decimals,
                    scalar_factor_code=dp.scalar_factor_code,
                    symbol_code=dp.symbol_code,
                    security_level_code=dp.security_level_code,
                    status_code=dp.status_code,
                    frequency_code=dp.frequency_code,
                    vector_id=response.vector_id,
                    response_status_code=response.response_status_code,
                )
                _, outcome = await repo.upsert_period(
                    cube_id=cube_id,
                    product_id=product_id,
                    semantic_key=semantic_key,
                    coord=coord,
                    ref_period=dp.ref_per,
                    value=dp.value,
                    missing=dp.missing,
                    decimals=dp.decimals,
                    scalar_factor_code=dp.scalar_factor_code,
                    symbol_code=dp.symbol_code,
                    security_level_code=dp.security_level_code,
                    status_code=dp.status_code,
                    frequency_code=dp.frequency_code,
                    vector_id=response.vector_id,
                    response_status_code=response.response_status_code,
                    source_hash=source_hash,
                    fetched_at=fetched_at,
                    release_time=dp.release_time,
                )
                counts[outcome] += 1
            await session.commit()
        return counts


def _row_to_dto(row) -> ValueCacheRow:
    return ValueCacheRow(
        id=row.id,
        cube_id=row.cube_id,
        product_id=row.product_id,
        semantic_key=row.semantic_key,
        coord=row.coord,
        ref_period=row.ref_period,
        period_start=row.period_start,
        value=row.value,
        missing=row.missing,
        decimals=row.decimals,
        scalar_factor_code=row.scalar_factor_code,
        symbol_code=row.symbol_code,
        security_level_code=row.security_level_code,
        status_code=row.status_code,
        frequency_code=row.frequency_code,
        vector_id=row.vector_id,
        response_status_code=row.response_status_code,
        source_hash=row.source_hash,
        fetched_at=row.fetched_at,
        release_time=row.release_time,
        is_stale=row.is_stale,
    )
