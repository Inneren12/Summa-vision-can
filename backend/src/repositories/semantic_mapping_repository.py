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

        Phase 3.1a contract: re-running the seed CLI on the same YAML must
        NOT bump version. Comparing normalized payload to existing row
        guarantees no-op on identical input. Without this guard the
        before_update event listener increments version on every flush,
        breaking staleness checks.

        Returns ``(mapping, was_created)``.
        """
        existing = await self.get_by_key(payload.cube_id, payload.semantic_key)
        if existing is None:
            created = await self.create(payload, updated_by=updated_by)
            return created, True

        new_config = payload.config.model_dump()
        changed = (
            existing.label != payload.label
            or existing.description != payload.description
            or existing.config != new_config
            or existing.is_active != payload.is_active
        )
        if not changed:
            return existing, False

        existing.label = payload.label
        existing.description = payload.description
        existing.config = new_config
        existing.is_active = payload.is_active
        existing.updated_by = updated_by
        await self._session.flush()
        return existing, False

    async def update(
        self,
        mapping: SemanticMapping,
        payload: SemanticMappingUpdate,
        *,
        updated_by: str | None = None,
    ) -> SemanticMapping:
        """PATCH-style update: only fields present in payload are modified.

        Pydantic ``model_dump(exclude_unset=True)`` distinguishes omitted
        from explicit null. Important for 3.1b admin UI: PATCH with
        ``description: null`` must clear the field; PATCH without
        ``description`` must leave it unchanged.

        ``config`` cannot be cleared (NOT NULL). Explicit ``config: null`` is
        treated as "omitted" — the field stays. Future schema-level rejection
        of explicit null on config is fine; for 3.1a we tolerate it.
        """
        updates = payload.model_dump(exclude_unset=True)

        if "label" in updates:
            mapping.label = updates["label"]
        if "description" in updates:
            mapping.description = updates["description"]  # may be None to clear
        if "config" in updates and updates["config"] is not None:
            mapping.config = payload.config.model_dump()
        if "is_active" in updates:
            mapping.is_active = updates["is_active"]

        mapping.updated_by = updated_by
        await self._session.flush()
        return mapping
