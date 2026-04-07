"""CubeCatalog repository — data access layer for StatCan cube metadata.

Supports bilingual full-text search with typo tolerance on PostgreSQL
(via pg_trgm + tsvector) and LIKE-based fallback on SQLite (unit tests).

Commit semantics:
    Repositories perform ``session.flush()`` and ``session.refresh()``
    on create operations but do **not** call ``session.commit()``.
    Commits are handled by the FastAPI ``get_db`` dependency (auto-commit
    on successful request, rollback on exception).  Callers outside of
    a request context (e.g. background tasks, scripts) must commit
    explicitly.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.cube_catalog import CubeCatalog
from src.schemas.cube_catalog import CubeCatalogCreate


class CubeCatalogRepository:
    """Data access layer for the StatCan cube catalog."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_batch(
        self,
        cubes: list[CubeCatalogCreate],
        chunk_size: int = 500,
    ) -> int:
        """Bulk insert or update cubes. Returns total affected rows.

        On PostgreSQL: uses INSERT ... ON CONFLICT (product_id) DO UPDATE.
        On SQLite: uses merge-style logic (check exists, insert or update).

        Processes in chunks of ``chunk_size`` to avoid memory issues
        with large catalog syncs (~7000 cubes).
        """
        dialect = self._session.bind.dialect.name if self._session.bind else ""
        total = 0

        for i in range(0, len(cubes), chunk_size):
            chunk = cubes[i : i + chunk_size]

            if dialect == "postgresql":
                total += await self._upsert_chunk_pg(chunk)
            else:
                total += await self._upsert_chunk_sqlite(chunk)

        return total

    async def search(
        self,
        query: str,
        limit: int = 20,
    ) -> Sequence[CubeCatalog]:
        """Search cubes by text query with typo tolerance.

        PostgreSQL: Uses ``websearch_to_tsquery`` for full-text search
        combined with ``pg_trgm`` similarity for typo tolerance.
        Results ranked by combined relevance score.

        SQLite: Falls back to LIKE-based search, splitting query
        into words and AND-chaining them.

        Args:
            query: Search string (e.g. "rental vacancy Alberta").
            limit: Maximum results to return (default 20, max 100).

        Returns:
            List of matching CubeCatalog records, ranked by relevance.
        """
        limit = min(limit, 100)
        dialect = self._session.bind.dialect.name if self._session.bind else ""

        if dialect == "postgresql":
            return await self._search_pg(query, limit)
        else:
            return await self._search_sqlite(query, limit)

    async def get_by_product_id(
        self,
        product_id: str,
    ) -> CubeCatalog | None:
        """Fetch a single cube by its StatCan product ID."""
        result = await self._session.execute(
            select(CubeCatalog).where(
                CubeCatalog.product_id == product_id
            )
        )
        return result.scalar_one_or_none()

    async def get_by_subject(
        self,
        subject_code: str,
        limit: int = 50,
    ) -> Sequence[CubeCatalog]:
        """Fetch cubes by subject classification code."""
        result = await self._session.execute(
            select(CubeCatalog)
            .where(CubeCatalog.subject_code == subject_code)
            .order_by(CubeCatalog.title_en)
            .limit(limit)
        )
        return result.scalars().all()

    async def count(self) -> int:
        """Total number of cubes in the catalog."""
        result = await self._session.scalar(
            select(func.count(CubeCatalog.id))
        )
        return result or 0

    # ------------------------------------------------------------------
    # PostgreSQL implementations
    # ------------------------------------------------------------------

    async def _upsert_chunk_pg(
        self,
        chunk: list[CubeCatalogCreate],
    ) -> int:
        """PostgreSQL upsert via INSERT ... ON CONFLICT DO UPDATE."""
        now = datetime.now(timezone.utc)
        values = [
            {
                "product_id": c.product_id,
                "cube_id_statcan": c.cube_id_statcan,
                "title_en": c.title_en,
                "title_fr": c.title_fr,
                "subject_code": c.subject_code,
                "subject_en": c.subject_en,
                "survey_en": c.survey_en,
                "frequency": c.frequency,
                "start_date": c.start_date,
                "end_date": c.end_date,
                "archive_status": c.archive_status,
                "last_synced_at": now,
            }
            for c in chunk
        ]

        stmt = pg_insert(CubeCatalog).values(values)
        stmt = stmt.on_conflict_do_update(
            index_elements=["product_id"],
            set_={
                "cube_id_statcan": stmt.excluded.cube_id_statcan,
                "title_en": stmt.excluded.title_en,
                "title_fr": stmt.excluded.title_fr,
                "subject_code": stmt.excluded.subject_code,
                "subject_en": stmt.excluded.subject_en,
                "survey_en": stmt.excluded.survey_en,
                "frequency": stmt.excluded.frequency,
                "start_date": stmt.excluded.start_date,
                "end_date": stmt.excluded.end_date,
                "archive_status": stmt.excluded.archive_status,
                "last_synced_at": stmt.excluded.last_synced_at,
            },
        )

        result = await self._session.execute(stmt)
        return result.rowcount  # type: ignore[return-value]

    async def _search_pg(
        self,
        query: str,
        limit: int,
    ) -> Sequence[CubeCatalog]:
        """PostgreSQL FTS + trigram similarity search."""
        # Combine full-text rank and trigram similarity for best results
        stmt = text("""
            SELECT cc.*,
                   ts_rank(cc.search_vector, websearch_to_tsquery('english', :query)) AS fts_rank,
                   GREATEST(
                       similarity(cc.title_en, :query),
                       COALESCE(similarity(cc.title_fr, :query), 0)
                   ) AS trgm_score
            FROM cube_catalog cc
            WHERE cc.search_vector @@ websearch_to_tsquery('english', :query)
               OR similarity(cc.title_en, :query) > 0.1
               OR similarity(COALESCE(cc.title_fr, ''), :query) > 0.1
            ORDER BY (ts_rank(cc.search_vector, websearch_to_tsquery('english', :query)) * 2 +
                      GREATEST(similarity(cc.title_en, :query),
                               COALESCE(similarity(cc.title_fr, :query), 0)))
                     DESC
            LIMIT :limit
        """)

        result = await self._session.execute(
            stmt, {"query": query, "limit": limit}
        )
        rows = result.fetchall()

        # Convert raw rows back to CubeCatalog instances
        if not rows:
            return []

        product_ids = [row.product_id for row in rows]
        orm_result = await self._session.execute(
            select(CubeCatalog).where(
                CubeCatalog.product_id.in_(product_ids)
            )
        )
        cubes_by_pid = {c.product_id: c for c in orm_result.scalars().all()}

        # Preserve relevance order from the raw query
        return [cubes_by_pid[pid] for pid in product_ids if pid in cubes_by_pid]

    # ------------------------------------------------------------------
    # SQLite implementations (unit tests only)
    # ------------------------------------------------------------------

    async def _upsert_chunk_sqlite(
        self,
        chunk: list[CubeCatalogCreate],
    ) -> int:
        """SQLite upsert via check-and-insert/update."""
        now = datetime.now(timezone.utc)
        count = 0

        for cube in chunk:
            existing = await self.get_by_product_id(cube.product_id)

            if existing is not None:
                # Update
                existing.cube_id_statcan = cube.cube_id_statcan
                existing.title_en = cube.title_en
                existing.title_fr = cube.title_fr
                existing.subject_code = cube.subject_code
                existing.subject_en = cube.subject_en
                existing.survey_en = cube.survey_en
                existing.frequency = cube.frequency
                existing.start_date = cube.start_date
                existing.end_date = cube.end_date
                existing.archive_status = cube.archive_status
                existing.last_synced_at = now
            else:
                # Insert
                record = CubeCatalog(
                    product_id=cube.product_id,
                    cube_id_statcan=cube.cube_id_statcan,
                    title_en=cube.title_en,
                    title_fr=cube.title_fr,
                    subject_code=cube.subject_code,
                    subject_en=cube.subject_en,
                    survey_en=cube.survey_en,
                    frequency=cube.frequency,
                    start_date=cube.start_date,
                    end_date=cube.end_date,
                    archive_status=cube.archive_status,
                    last_synced_at=now,
                )
                self._session.add(record)

            count += 1

        await self._session.flush()
        return count

    async def _search_sqlite(
        self,
        query: str,
        limit: int,
    ) -> Sequence[CubeCatalog]:
        """SQLite fallback: AND-chained LIKE search on title_en."""
        words = query.strip().split()
        if not words:
            return []

        stmt = select(CubeCatalog)
        for word in words:
            pattern = f"%{word}%"
            stmt = stmt.where(
                CubeCatalog.title_en.ilike(pattern)
                | CubeCatalog.subject_en.ilike(pattern)
                | (
                    CubeCatalog.title_fr.isnot(None)
                    & CubeCatalog.title_fr.ilike(pattern)
                )
            )
        stmt = stmt.order_by(CubeCatalog.title_en).limit(limit)

        result = await self._session.execute(stmt)
        return result.scalars().all()
