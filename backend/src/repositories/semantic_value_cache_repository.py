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

import sqlalchemy as sa
from sqlalchemy import and_, delete, func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.semantic_mapping import SemanticMapping
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

    def _dialect(self) -> str:
        """Best-effort dialect lookup for dialect-aware upsert path."""
        bind = getattr(self._session, "bind", None)
        if bind is None:
            return ""
        return bind.dialect.name

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

        Phase 3.1aaa FIX-R1 (P1 #4 + #5): on PostgreSQL the upsert is
        atomic via ``INSERT ... ON CONFLICT DO UPDATE``. The ``WHERE
        source_hash != excluded.source_hash`` guard turns hash-equal
        re-writes into no-ops without paying the UPDATE cost, and the
        UPDATE clause explicitly bumps ``updated_at`` (cannot rely on
        ORM ``onupdate`` for raw-SQL paths). On SQLite (test fixtures
        only) we fall back to SELECT-then-write: SQLite supports
        ``ON CONFLICT`` but lacks ``xmax``, and its FK semantics
        differ from PG anyway, so the simpler fallback is safer.
        """
        if self._dialect() == "postgresql":
            return await self._upsert_period_pg(
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
            )
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

    async def _upsert_period_pg(
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
        """PG ``INSERT ... ON CONFLICT DO UPDATE`` path.

        Outcome is derived from ``xmax``: PostgreSQL exposes the row
        version on RETURNING — ``xmax = 0`` for fresh INSERTs,
        non-zero for UPDATEs. The conditional ``WHERE`` clause keeps
        identical-hash writes as no-ops; the second SELECT pulls the
        existing row in that case to maintain the existing API
        contract.
        """
        stmt = pg_insert(SemanticValueCache).values(
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
        excluded = stmt.excluded
        stmt = stmt.on_conflict_do_update(
            constraint="uq_semantic_value_cache_lookup",
            set_={
                "product_id": excluded.product_id,
                "value": excluded.value,
                "missing": excluded.missing,
                "decimals": excluded.decimals,
                "scalar_factor_code": excluded.scalar_factor_code,
                "symbol_code": excluded.symbol_code,
                "security_level_code": excluded.security_level_code,
                "status_code": excluded.status_code,
                "frequency_code": excluded.frequency_code,
                "vector_id": excluded.vector_id,
                "response_status_code": excluded.response_status_code,
                "source_hash": excluded.source_hash,
                "fetched_at": excluded.fetched_at,
                "release_time": excluded.release_time,
                "is_stale": False,
                # P1 #5: explicit updated_at; ORM onupdate doesn't fire
                # on raw INSERT...ON CONFLICT DO UPDATE.
                "updated_at": func.now(),
            },
            # Avoid spurious UPDATEs when the source_hash is unchanged —
            # the ON CONFLICT path otherwise rewrites every column on
            # every refresh, defeating the unchanged outcome.
            where=(SemanticValueCache.source_hash != excluded.source_hash),
        ).returning(
            SemanticValueCache,
            sa.literal_column("(xmax = 0)").label("was_inserted"),
        )
        result = await self._session.execute(stmt)
        row = result.first()
        await self._session.flush()
        if row is None:
            # WHERE filtered the UPDATE → no row returned. Fetch the
            # existing row for the unchanged outcome. Refresh
            # fetched_at + clear is_stale so the row reads as live-
            # verified (matches SQLite behaviour above).
            existing = await self._get_by_lookup_key(
                cube_id=cube_id,
                semantic_key=semantic_key,
                coord=coord,
                ref_period=ref_period,
            )
            if existing is not None:
                existing.fetched_at = fetched_at
                existing.is_stale = False
                await self._session.flush()
                return existing, "unchanged"
            # Should be unreachable — conflict implies the row exists.
            raise RuntimeError(
                "ON CONFLICT path produced no row and no existing match"
            )
        entity = row[0]
        was_inserted = bool(row[1])
        return entity, "inserted" if was_inserted else "updated"

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
                vector_id=item.vector_id,
                response_status_code=item.response_status_code,
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
                vector_id=item.vector_id,
                response_status_code=item.response_status_code,
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
        # FIX-R2 (P2): order by parsed ``period_start`` ASC primarily,
        # with ``ref_period`` ASC as a tiebreaker. Avoids string sort
        # putting ``"2025-Q4"`` before ``"2025-12"``.
        stmt = stmt.order_by(
            SemanticValueCache.period_start.asc().nulls_last(),
            SemanticValueCache.ref_period.asc(),
        )
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

    async def list_active_lookup_keys(
        self,
    ) -> list[tuple[str, str, str | None, int]]:
        """List ``(cube_id, semantic_key, coord, product_id)`` for every
        ACTIVE :class:`SemanticMapping` row.

        Phase 3.1aaa FIX-R2 (Blocker 2): the source of truth for the
        nightly refresh fan-out is ``semantic_mappings.is_active=true``
        — NOT distinct rows in ``semantic_value_cache``. A mapping
        whose auto-prime never succeeded must still be revisited by
        the nightly job (best-effort retry contract); the prior
        cache-only query silently dropped exactly those mappings.

        ``coord`` is ``None`` for mappings that have no cached row
        yet. The caller (refresh service) is expected to skip those
        with a debug log; first-resolve / next-mapping-upsert paths
        will prime the cache. Tracked under DEBT-062 for an explicit
        prime-on-refresh path.

        Inactive mappings (soft-deleted via ``is_active=false``) are
        excluded.
        """
        stmt = (
            select(
                SemanticMapping.cube_id,
                SemanticMapping.semantic_key,
                SemanticValueCache.coord,
                SemanticMapping.product_id,
            )
            .select_from(SemanticMapping)
            .outerjoin(
                SemanticValueCache,
                and_(
                    SemanticValueCache.cube_id == SemanticMapping.cube_id,
                    SemanticValueCache.semantic_key
                    == SemanticMapping.semantic_key,
                ),
            )
            .where(SemanticMapping.is_active.is_(True))
            .distinct()
        )
        result = await self._session.execute(stmt)
        return [(row[0], row[1], row[2], row[3]) for row in result.all()]

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
        # FIX-R2 (P2): rank by ``period_start`` DATE, falling back to
        # ``ref_period`` only as a tiebreaker. Mixed token formats
        # (YYYY, YYYY-MM, YYYY-Qn, YYYY-MM-DD) sort incorrectly as
        # strings — e.g. ``"2025-Q4"`` > ``"2025-12"`` lexically but
        # represents an earlier date. ``nulls_last()`` keeps rows
        # with unparseable ``ref_period`` (null period_start, per
        # Blocker 3 tolerant parser) at the end of the ranking so
        # they are NOT in the keep window.
        stmt = (
            select(SemanticValueCache.ref_period)
            .where(
                SemanticValueCache.cube_id == cube_id,
                SemanticValueCache.semantic_key == semantic_key,
                SemanticValueCache.coord == coord,
            )
            .order_by(
                SemanticValueCache.period_start.desc().nulls_last(),
                SemanticValueCache.ref_period.desc(),
            )
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
