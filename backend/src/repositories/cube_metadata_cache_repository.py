"""Phase 3.1aa: CubeMetadataCache repository.

Commit semantics (matches ``SemanticMappingRepository`` convention):
    Repository performs ``session.flush()`` but does NOT call
    ``session.commit()``. Commits are handled by the caller — typically
    the service layer in this case, since the cache is written outside
    of FastAPI request scope (admin save flow + scheduler).
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.cube_metadata_cache import CubeMetadataCache


class CubeMetadataCacheRepository:
    """Read/write access to the ``cube_metadata_cache`` table."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_cube_id(self, cube_id: str) -> CubeMetadataCache | None:
        result = await self._session.execute(
            select(CubeMetadataCache).where(CubeMetadataCache.cube_id == cube_id)
        )
        return result.scalar_one_or_none()

    async def list_stale(self, *, before: datetime) -> list[CubeMetadataCache]:
        result = await self._session.execute(
            select(CubeMetadataCache)
            .where(CubeMetadataCache.fetched_at < before)
            .order_by(CubeMetadataCache.fetched_at.asc())
        )
        return list(result.scalars().all())

    async def upsert(
        self,
        *,
        cube_id: str,
        product_id: int,
        dimensions: dict,
        frequency_code: str | None,
        cube_title_en: str | None,
        cube_title_fr: str | None,
        fetched_at: datetime,
    ) -> tuple[CubeMetadataCache, bool]:
        """Idempotent upsert keyed by ``cube_id``.

        Returns ``(entity, changed)``. ``changed=False`` means the existing
        row already matched the new payload exactly; the row is returned
        untouched and ``updated_at`` is NOT bumped. ``dimensions``
        equality is dict-level — callers MUST pass an already-normalized
        payload (``normalize_dimensions``) so both sides are comparable.
        """
        existing = await self.get_by_cube_id(cube_id)
        if existing is None:
            entity = CubeMetadataCache(
                cube_id=cube_id,
                product_id=product_id,
                dimensions=dimensions,
                frequency_code=frequency_code,
                cube_title_en=cube_title_en,
                cube_title_fr=cube_title_fr,
                fetched_at=fetched_at,
            )
            self._session.add(entity)
            await self._session.flush()
            return entity, True

        unchanged = (
            existing.product_id == product_id
            and existing.dimensions == dimensions
            and existing.frequency_code == frequency_code
            and existing.cube_title_en == cube_title_en
            and existing.cube_title_fr == cube_title_fr
        )
        if unchanged:
            return existing, False

        existing.product_id = product_id
        existing.dimensions = dimensions
        existing.frequency_code = frequency_code
        existing.cube_title_en = cube_title_en
        existing.cube_title_fr = cube_title_fr
        existing.fetched_at = fetched_at
        await self._session.flush()
        return existing, True
