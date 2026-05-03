"""Phase 3.1aaa: SemanticValueCache repository.

Commit semantics (matches :class:`CubeMetadataCacheRepository` and
:class:`SemanticMappingRepository`):

    Repository performs ``session.flush()`` but does NOT call
    ``session.commit()``. Commits are owned by the caller — typically
    the service layer, since the cache is written outside FastAPI
    request scope (mapping-save auto-prime + nightly scheduler).
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import and_, delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.semantic_value_cache import SemanticValueCache
from src.services.statcan.value_cache_hash import compute_source_hash
from src.services.statcan.value_cache_schemas import ValueCacheUpsertItem


# Sentinel surfaced by upsert_period to indicate the relative outcome
# of an upsert operation.
UpsertOutcome = str  # one of: "inserted" | "updated" | "unchanged"


class SemanticValueCacheRepository:
    """Read/write access to the ``semantic_value_cache`` table."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Writes
    # ------------------------------------------------------------------

    async def upsert_period(
        self,
        *,
        cube_id: str,
        product_id: int,
        semantic_key: str,
        coord: str,
        ref_period: str,
        value: Decimal | None,
        missing: bool,
        decimals: int,
        scalar_factor_code: int,
        symbol_code: int,
        security_level_code: int,
        status_code: int,
        frequency_code: int | None,
        vector_id: int | None,
        response_status_code: int | None,
        source_hash: str,
        fetched_at: datetime,
        release_time: datetime | None,
    ) -> tuple[SemanticValueCache, UpsertOutcome]:
        """Upsert a single value-cache row.

        Returns ``(entity, outcome)`` where ``outcome`` is one of
        ``"inserted"`` (no prior row), ``"updated"`` (source_hash
        changed), or ``"unchanged"`` (identical source_hash → no-op
        write; only ``fetched_at``/``is_stale`` reset for freshness).

        Lookup is by the ``(cube_id, semantic_key, coord, ref_period)``
        unique key, mirroring the DB constraint
        ``uq_semantic_value_cache_lookup``.
        """
        existing = await self._get_by_lookup_key(
            cube_id=cube_id,
            semantic_key=semantic_key,
            coord=coord,
            ref_period=ref_period,
        )
        if existing is None:
            entity = SemanticValueCache(
                cube_id=cube_id,
                product_id=product_id,
                semantic_key=semantic_key,
                coord=coord,
                ref_period=ref_period,
                value=value,
                missing=missing,
                decimals=decimals,
                scalar_factor_code=scalar_factor_code,
                symbol_code=symbol_code,
                security_level_code=security_level_code,
                status_code=status_code,
                frequency_code=frequency_code,
                vector_id=vector_id,
                response_status_code=response_status_code,
                source_hash=source_hash,
                fetched_at=fetched_at,
                release_time=release_time,
                is_stale=False,
            )
            self._session.add(entity)
            await self._session.flush()
            return entity, "inserted"

        if existing.source_hash == source_hash:
            # Idempotent no-op write. Refresh ``fetched_at`` and clear
            # the stale flag so the row is treated as live-verified.
            existing.fetched_at = fetched_at
            existing.is_stale = False
            await self._session.flush()
            return existing, "unchanged"

        existing.product_id = product_id
        existing.value = value
        existing.missing = missing
        existing.decimals = decimals
        existing.scalar_factor_code = scalar_factor_code
        existing.symbol_code = symbol_code
        existing.security_level_code = security_level_code
        existing.status_code = status_code
        existing.frequency_code = frequency_code
        existing.vector_id = vector_id
        existing.response_status_code = response_status_code
        existing.source_hash = source_hash
        existing.fetched_at = fetched_at
        existing.release_time = release_time
        existing.is_stale = False
        await self._session.flush()
        return existing, "updated"

    async def upsert_periods_batch(
        self, items: list[ValueCacheUpsertItem]
    ) -> dict[str, int]:
        """Bulk upsert. Returns counts of ``inserted``/``updated``/``unchanged``.

        Used by the nightly refresh job. Wraps :meth:`upsert_period`
        for each item; the caller owns the surrounding transaction.
        """
        counts = {"inserted": 0, "updated": 0, "unchanged": 0}
        for item in items:
            dp = item.data_point
            source_hash = compute_source_hash(
                product_id=item.product_id,
                cube_id=item.cube_id,
                semantic_key=item.semantic_key,
                coord=item.coord,
                ref_period=dp.ref_per,
                value=dp.value,
                missing=dp.missing,
                decimals=dp.decimals,
                scalar_factor_code=dp.scalar_factor_code,
                symbol_code=dp.symbol_code,
                security_level_code=dp.security_level_code,
                status_code=dp.status_code,
                frequency_code=dp.frequency_code,
                vector_id=None,
                response_status_code=None,
            )
            _, outcome = await self.upsert_period(
                cube_id=item.cube_id,
                product_id=item.product_id,
                semantic_key=item.semantic_key,
                coord=item.coord,
                ref_period=dp.ref_per,
                value=dp.value,
                missing=dp.missing,
                decimals=dp.decimals,
                scalar_factor_code=dp.scalar_factor_code,
                symbol_code=dp.symbol_code,
                security_level_code=dp.security_level_code,
                status_code=dp.status_code,
                frequency_code=dp.frequency_code,
                vector_id=None,
                response_status_code=None,
                source_hash=source_hash,
                fetched_at=item.fetched_at,
                release_time=dp.release_time,
            )
            counts[outcome] += 1
        return counts

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    async def get_by_lookup(
        self,
        *,
        cube_id: str,
        semantic_key: str,
        coord: str,
        ref_period: str | None = None,
    ) -> list[SemanticValueCache]:
        """Read cached rows for a (cube_id, semantic_key, coord) triple.

        When ``ref_period`` is given, narrows to that single period.
        Results are ordered by ``ref_period`` ascending (or
        ``period_start`` ascending where it is populated by Postgres).
        """
        stmt = select(SemanticValueCache).where(
            SemanticValueCache.cube_id == cube_id,
            SemanticValueCache.semantic_key == semantic_key,
            SemanticValueCache.coord == coord,
        )
        if ref_period is not None:
            stmt = stmt.where(SemanticValueCache.ref_period == ref_period)
        stmt = stmt.order_by(SemanticValueCache.ref_period.asc())
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_latest_by_lookup(
        self,
        *,
        cube_id: str,
        semantic_key: str,
        coord: str,
    ) -> SemanticValueCache | None:
        """Most recent period for the given lookup key.

        Orders by ``period_start`` first (populated by Postgres
        GENERATED column) and falls back to ``ref_period`` so SQLite
        tests still produce a deterministic ordering.
        """
        stmt = (
            select(SemanticValueCache)
            .where(
                SemanticValueCache.cube_id == cube_id,
                SemanticValueCache.semantic_key == semantic_key,
                SemanticValueCache.coord == coord,
            )
            .order_by(
                SemanticValueCache.period_start.desc().nulls_last(),
                SemanticValueCache.ref_period.desc(),
            )
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_active_lookup_keys(self) -> list[tuple[str, str, str, int]]:
        """Distinct (cube_id, semantic_key, coord, product_id) tuples.

        Source of fan-out for the nightly refresh job.
        """
        stmt = select(
            SemanticValueCache.cube_id,
            SemanticValueCache.semantic_key,
            SemanticValueCache.coord,
            SemanticValueCache.product_id,
        ).distinct()
        result = await self._session.execute(stmt)
        return [tuple(row) for row in result.all()]

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------

    async def mark_stale_outside_window(
        self,
        *,
        cube_id: str,
        semantic_key: str,
        coord: str,
        retention_count: int,
    ) -> int:
        """Mark ``is_stale=true`` on rows beyond the most recent N periods.

        Returns the number of rows newly marked stale (does NOT include
        rows that were already stale). The "most recent N" set is
        defined by ``ref_period`` ordering, descending, since
        ``period_start`` may be NULL on SQLite test fixtures.
        """
        stmt = (
            select(SemanticValueCache.ref_period)
            .where(
                SemanticValueCache.cube_id == cube_id,
                SemanticValueCache.semantic_key == semantic_key,
                SemanticValueCache.coord == coord,
            )
            .order_by(SemanticValueCache.ref_period.desc())
            .limit(retention_count)
        )
        result = await self._session.execute(stmt)
        keep_periods = {row[0] for row in result.all()}

        upd = (
            update(SemanticValueCache)
            .where(
                SemanticValueCache.cube_id == cube_id,
                SemanticValueCache.semantic_key == semantic_key,
                SemanticValueCache.coord == coord,
                SemanticValueCache.is_stale.is_(False),
                ~SemanticValueCache.ref_period.in_(keep_periods)
                if keep_periods
                else SemanticValueCache.ref_period.isnot(None),
            )
            .values(is_stale=True)
            .execution_options(synchronize_session=False)
        )
        upd_result = await self._session.execute(upd)
        await self._session.flush()
        return upd_result.rowcount or 0

    async def delete_older_than(self, cutoff: datetime) -> int:
        """Hard-delete rows whose ``fetched_at`` precedes ``cutoff``.

        Returns the number of rows deleted.
        """
        stmt = (
            delete(SemanticValueCache)
            .where(SemanticValueCache.fetched_at < cutoff)
            .execution_options(synchronize_session=False)
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount or 0

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    async def _get_by_lookup_key(
        self,
        *,
        cube_id: str,
        semantic_key: str,
        coord: str,
        ref_period: str,
    ) -> SemanticValueCache | None:
        stmt = select(SemanticValueCache).where(
            and_(
                SemanticValueCache.cube_id == cube_id,
                SemanticValueCache.semantic_key == semantic_key,
                SemanticValueCache.coord == coord,
                SemanticValueCache.ref_period == ref_period,
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
