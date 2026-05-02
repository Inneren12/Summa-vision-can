"""Phase 3.1a: SemanticMapping repository.

Commit semantics (matches CubeCatalogRepository convention):
    Repository performs ``session.flush()`` but does NOT call
    ``session.commit()``. Commits are handled by the FastAPI ``get_db``
    dependency or by CLI scripts/background tasks running outside a
    request context.
"""
from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import func, select, update
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
            product_id=payload.product_id,
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
            or existing.product_id != payload.product_id
            or existing.description != payload.description
            or existing.config != new_config
            or existing.is_active != payload.is_active
        )
        if not changed:
            return existing, False

        existing.label = payload.label
        existing.product_id = payload.product_id
        existing.description = payload.description
        existing.config = new_config
        existing.is_active = payload.is_active
        existing.updated_by = updated_by
        await self._session.flush()
        return existing, False

    async def list(
        self,
        *,
        cube_id: str | None = None,
        semantic_key: str | None = None,
        is_active: bool | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[SemanticMapping], int]:
        """Paginated list with filters. Returns ``(rows, total_count)``.

        Phase 3.1b admin list endpoint. ``total_count`` is the unpaginated
        match count so the operator UI can render pagination controls.
        """
        filters = []
        if cube_id is not None:
            filters.append(SemanticMapping.cube_id == cube_id)
        if semantic_key is not None:
            filters.append(SemanticMapping.semantic_key == semantic_key)
        if is_active is not None:
            filters.append(SemanticMapping.is_active.is_(is_active))

        rows_stmt = select(SemanticMapping)
        count_stmt = select(func.count()).select_from(SemanticMapping)
        for clause in filters:
            rows_stmt = rows_stmt.where(clause)
            count_stmt = count_stmt.where(clause)

        rows_stmt = (
            rows_stmt.order_by(
                SemanticMapping.cube_id.asc(), SemanticMapping.label.asc()
            )
            .limit(limit)
            .offset(offset)
        )

        rows_result = await self._session.execute(rows_stmt)
        rows = list(rows_result.scalars().all())
        total = (await self._session.execute(count_stmt)).scalar_one()
        return rows, int(total)

    async def update_with_version_check(
        self,
        *,
        id: int,
        expected_version: int,
        product_id: int,
        label: str,
        description: str | None,
        config: dict,
        is_active: bool,
        updated_by: str | None,
    ) -> SemanticMapping | None:
        """Atomic UPDATE with version check (Phase 3.1b R2 fix).

        Returns the updated row when ``rowcount == 1`` (version matched).
        Returns ``None`` when ``rowcount == 0`` (version did NOT match —
        caller decides whether the row exists at a different version or
        does not exist at all).

        The ``version`` column is bumped as part of the same UPDATE
        statement. The ORM ``before_update`` event listener does NOT fire
        for Core-level :func:`update` statements, so the bump is encoded
        explicitly here (``version = version + 1``) plus an explicit
        ``updated_at = now()`` to mirror the listener-driven path.

        This is the ONLY safe path for optimistic concurrency on this
        table. Callers MUST NOT do SELECT-then-UPDATE on the version
        column; that introduces a TOCTOU race where two writers reading
        the same version both pass the check and the second silently
        clobbers the first.
        """
        stmt = (
            update(SemanticMapping)
            .where(SemanticMapping.id == id)
            .where(SemanticMapping.version == expected_version)
            .values(
                product_id=product_id,
                label=label,
                description=description,
                config=config,
                is_active=is_active,
                updated_by=updated_by,
                version=SemanticMapping.version + 1,
                updated_at=func.now(),
            )
            .execution_options(synchronize_session=False)
        )
        result = await self._session.execute(stmt)
        if result.rowcount == 0:
            return None
        await self._session.flush()
        # Re-read the row to materialize the new version + updated_at on
        # an ORM instance the caller can serialize. ``populate_existing``
        # bypasses the identity-map cache that still holds the pre-UPDATE
        # row state (synchronize_session=False above means the Core update
        # did not refresh ORM-attached instances).
        return await self._session.get(
            SemanticMapping, id, populate_existing=True
        )

    async def soft_delete(self, id: int) -> SemanticMapping | None:
        """Sets ``is_active=False``. Returns updated row, or ``None`` if id
        not found.

        Idempotent: if the row is already ``is_active=False``, the row is
        returned unchanged (no version bump, no ``updated_at`` touch).
        Mirrors the change-detection pattern used by
        :meth:`upsert_by_key` and the 3.1aa cube_metadata_cache upsert.
        """
        mapping = await self._session.get(SemanticMapping, id)
        if mapping is None:
            return None
        if mapping.is_active is False:
            return mapping
        mapping.is_active = False
        await self._session.flush()
        return mapping

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
