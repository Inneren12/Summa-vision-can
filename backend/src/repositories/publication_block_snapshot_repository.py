"""Phase 3.1d: PublicationBlockSnapshotRepository.

Per recon ``docs/recon/phase-3-1d-recon.md`` §3.3.

Commit semantics: repository performs ``session.flush()`` but does NOT
``commit``. Caller (publish handler / service layer) owns the
transaction.

Dialect-aware upsert mirrors :class:`SemanticValueCacheRepository`:
PostgreSQL uses atomic ``INSERT ... ON CONFLICT DO UPDATE``; SQLite
test fixtures use SELECT-then-write fallback.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import and_, delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.publication_block_snapshot import PublicationBlockSnapshot


class PublicationBlockSnapshotRepository:
    """Repository for ``publication_block_snapshot`` rows."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _dialect(self) -> str:
        bind = getattr(self._session, "bind", None)
        if bind is None:
            return ""
        return bind.dialect.name

    async def upsert_for_block(
        self,
        *,
        publication_id: int,
        block_id: str,
        cube_id: str,
        semantic_key: str,
        coord: str,
        period: str | None,
        dims_json: list[int],
        members_json: list[int],
        mapping_version_at_publish: int | None,
        source_hash_at_publish: str,
        value_at_publish: str | None,
        missing_at_publish: bool,
        is_stale_at_publish: bool,
        captured_at: datetime,
    ) -> PublicationBlockSnapshot:
        """Upsert snapshot row by ``(publication_id, block_id)``.

        On conflict: refresh all ``*_at_publish`` fields + identity
        context + ``captured_at``, bump ``updated_at``, preserve
        ``created_at``.
        """
        if self._dialect() == "postgresql":
            return await self._upsert_pg(
                publication_id=publication_id,
                block_id=block_id,
                cube_id=cube_id,
                semantic_key=semantic_key,
                coord=coord,
                period=period,
                dims_json=dims_json,
                members_json=members_json,
                mapping_version_at_publish=mapping_version_at_publish,
                source_hash_at_publish=source_hash_at_publish,
                value_at_publish=value_at_publish,
                missing_at_publish=missing_at_publish,
                is_stale_at_publish=is_stale_at_publish,
                captured_at=captured_at,
            )
        return await self._upsert_fallback(
            publication_id=publication_id,
            block_id=block_id,
            cube_id=cube_id,
            semantic_key=semantic_key,
            coord=coord,
            period=period,
            dims_json=dims_json,
            members_json=members_json,
            mapping_version_at_publish=mapping_version_at_publish,
            source_hash_at_publish=source_hash_at_publish,
            value_at_publish=value_at_publish,
            missing_at_publish=missing_at_publish,
            is_stale_at_publish=is_stale_at_publish,
            captured_at=captured_at,
        )

    async def _upsert_pg(
        self,
        *,
        publication_id: int,
        block_id: str,
        cube_id: str,
        semantic_key: str,
        coord: str,
        period: str | None,
        dims_json: list[int],
        members_json: list[int],
        mapping_version_at_publish: int | None,
        source_hash_at_publish: str,
        value_at_publish: str | None,
        missing_at_publish: bool,
        is_stale_at_publish: bool,
        captured_at: datetime,
    ) -> PublicationBlockSnapshot:
        stmt = pg_insert(PublicationBlockSnapshot).values(
            publication_id=publication_id,
            block_id=block_id,
            cube_id=cube_id,
            semantic_key=semantic_key,
            coord=coord,
            period=period,
            dims_json=dims_json,
            members_json=members_json,
            mapping_version_at_publish=mapping_version_at_publish,
            source_hash_at_publish=source_hash_at_publish,
            value_at_publish=value_at_publish,
            missing_at_publish=missing_at_publish,
            is_stale_at_publish=is_stale_at_publish,
            captured_at=captured_at,
        )
        excluded = stmt.excluded
        stmt = stmt.on_conflict_do_update(
            constraint="uq_publication_block_snapshot_pub_block",
            set_={
                "cube_id": excluded.cube_id,
                "semantic_key": excluded.semantic_key,
                "coord": excluded.coord,
                "period": excluded.period,
                "dims_json": excluded.dims_json,
                "members_json": excluded.members_json,
                "mapping_version_at_publish": excluded.mapping_version_at_publish,
                "source_hash_at_publish": excluded.source_hash_at_publish,
                "value_at_publish": excluded.value_at_publish,
                "missing_at_publish": excluded.missing_at_publish,
                "is_stale_at_publish": excluded.is_stale_at_publish,
                "captured_at": excluded.captured_at,
                # ORM ``onupdate`` does not fire on raw INSERT...ON CONFLICT;
                # bump explicitly so updated_at moves on every overwrite.
                "updated_at": func.now(),
            },
        ).returning(PublicationBlockSnapshot)
        result = await self._session.execute(stmt)
        row = result.scalar_one()
        await self._session.flush()
        return row

    async def _upsert_fallback(
        self,
        *,
        publication_id: int,
        block_id: str,
        cube_id: str,
        semantic_key: str,
        coord: str,
        period: str | None,
        dims_json: list[int],
        members_json: list[int],
        mapping_version_at_publish: int | None,
        source_hash_at_publish: str,
        value_at_publish: str | None,
        missing_at_publish: bool,
        is_stale_at_publish: bool,
        captured_at: datetime,
    ) -> PublicationBlockSnapshot:
        existing = await self._get_by_pub_block(publication_id, block_id)
        if existing is None:
            entity = PublicationBlockSnapshot(
                publication_id=publication_id,
                block_id=block_id,
                cube_id=cube_id,
                semantic_key=semantic_key,
                coord=coord,
                period=period,
                dims_json=dims_json,
                members_json=members_json,
                mapping_version_at_publish=mapping_version_at_publish,
                source_hash_at_publish=source_hash_at_publish,
                value_at_publish=value_at_publish,
                missing_at_publish=missing_at_publish,
                is_stale_at_publish=is_stale_at_publish,
                captured_at=captured_at,
            )
            self._session.add(entity)
            await self._session.flush()
            return entity

        existing.cube_id = cube_id
        existing.semantic_key = semantic_key
        existing.coord = coord
        existing.period = period
        existing.dims_json = dims_json
        existing.members_json = members_json
        existing.mapping_version_at_publish = mapping_version_at_publish
        existing.source_hash_at_publish = source_hash_at_publish
        existing.value_at_publish = value_at_publish
        existing.missing_at_publish = missing_at_publish
        existing.is_stale_at_publish = is_stale_at_publish
        existing.captured_at = captured_at
        await self._session.flush()
        # Refresh so server-side ``onupdate=func.now()`` is materialised
        # on the returned entity (otherwise the attribute is expired and
        # would trigger a lazy load outside session scope).
        await self._session.refresh(existing)
        return existing

    async def get_for_publication(
        self, publication_id: int
    ) -> list[PublicationBlockSnapshot]:
        """Return all snapshot rows for a publication, ordered by ``block_id``."""
        stmt = (
            select(PublicationBlockSnapshot)
            .where(PublicationBlockSnapshot.publication_id == publication_id)
            .order_by(PublicationBlockSnapshot.block_id)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def delete_for_publication(self, publication_id: int) -> int:
        """Hard-delete all snapshot rows for a publication.

        Per recon §3.3: NEVER called in normal publish flow. FK CASCADE
        handles publication deletion automatically; this method exists
        for explicit test cleanup + future cleanup workflows
        (DEBT-NN6).
        """
        stmt = delete(PublicationBlockSnapshot).where(
            PublicationBlockSnapshot.publication_id == publication_id
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount or 0

    async def _get_by_pub_block(
        self, publication_id: int, block_id: str
    ) -> PublicationBlockSnapshot | None:
        stmt = select(PublicationBlockSnapshot).where(
            and_(
                PublicationBlockSnapshot.publication_id == publication_id,
                PublicationBlockSnapshot.block_id == block_id,
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
