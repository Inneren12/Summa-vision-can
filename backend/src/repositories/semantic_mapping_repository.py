"""Phase 3.1a: SemanticMapping repository.

Commit semantics (matches CubeCatalogRepository convention):
    Repository performs ``session.flush()`` but does NOT call
    ``session.commit()``. Commits are handled by the FastAPI ``get_db``
    dependency or by CLI scripts/background tasks running outside a
    request context.
"""
from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.semantic_mapping import SemanticMapping
from src.schemas.semantic_mapping import (
    SemanticMappingCreate,
    SemanticMappingUpdate,
)


class SemanticMappingRepository:
    """Read/write access to semantic_mappings table.

    Phase 3.1a provides foundation only. Admin CRUD endpoints in 3.1b
    will use this repository.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_active_for_cube(
        self, cube_id: str
    ) -> Sequence[SemanticMapping]:
        """Phase 3.1a: primary query for picker UI (3.1c)."""
        result = await self._session.execute(
            select(SemanticMapping)
            .where(SemanticMapping.cube_id == cube_id)
            .where(SemanticMapping.is_active.is_(True))
            .order_by(SemanticMapping.label.asc())
        )
        return result.scalars().all()

    async def get_by_id(self, id: int) -> SemanticMapping | None:
        return await self._session.get(SemanticMapping, id)

    async def get_by_key(
        self,
        cube_id: str,
        semantic_key: str,
    ) -> SemanticMapping | None:
        result = await self._session.execute(
            select(SemanticMapping)
            .where(SemanticMapping.cube_id == cube_id)
            .where(SemanticMapping.semantic_key == semantic_key)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        payload: SemanticMappingCreate,
        *,
        updated_by: str | None = None,
    ) -> SemanticMapping:
        mapping = SemanticMapping(
            cube_id=payload.cube_id,
            semantic_key=payload.semantic_key,
            label=payload.label,
            description=payload.description,
            config=payload.config.model_dump(),
            is_active=payload.is_active,
            updated_by=updated_by,
        )
        self._session.add(mapping)
        await self._session.flush()
        return mapping

    async def upsert_by_key(
        self,
        payload: SemanticMappingCreate,
        *,
        updated_by: str | None = None,
    ) -> tuple[SemanticMapping, bool]:
        """Idempotent upsert by (cube_id, semantic_key). Used by seed CLI.

        Returns ``(mapping, was_created)``.
        """
        existing = await self.get_by_key(payload.cube_id, payload.semantic_key)
        if existing is not None:
            existing.label = payload.label
            existing.description = payload.description
            existing.config = payload.config.model_dump()
            existing.is_active = payload.is_active
            existing.updated_by = updated_by
            await self._session.flush()
            return existing, False
        created = await self.create(payload, updated_by=updated_by)
        return created, True

    async def update(
        self,
        mapping: SemanticMapping,
        payload: SemanticMappingUpdate,
        *,
        updated_by: str | None = None,
    ) -> SemanticMapping:
        if payload.label is not None:
            mapping.label = payload.label
        if payload.description is not None:
            mapping.description = payload.description
        if payload.config is not None:
            mapping.config = payload.config.model_dump()
        if payload.is_active is not None:
            mapping.is_active = payload.is_active
        mapping.updated_by = updated_by
        await self._session.flush()
        return mapping
