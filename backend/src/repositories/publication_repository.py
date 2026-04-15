"""Repository for Publication CRUD operations.

All database access for publications goes through this class.
Services must never import SQLAlchemy models directly — they use
this repository to decouple business logic from persistence.

Commit semantics:
    Repositories perform ``session.flush()`` and ``session.refresh()``
    on create operations but do **not** call ``session.commit()``.
    Commits are handled by the FastAPI ``get_db`` dependency (auto-commit
    on successful request, rollback on exception).  Callers outside of
    a request context (e.g. background tasks, scripts) must commit
    explicitly.
"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.publication import Publication, PublicationStatus


class PublicationRepository:
    """Encapsulates persistence logic for :class:`Publication`.

    Attributes:
        _session: The injected async database session.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialise with an injected ``AsyncSession``.

        Args:
            session: An active SQLAlchemy async session provided by DI.
        """
        self._session = session

    @staticmethod
    def _published_order_clause(sort: str) -> tuple:
        """Stable ordering for published publications.

        Tie-breakers are required because timestamps/scores can be equal,
        otherwise DB row order becomes non-deterministic and pagination/tests
        become flaky.
        """
        if sort == "oldest":
            return (Publication.created_at.asc(), Publication.id.asc())
        if sort == "score":
            return (
                Publication.virality_score.desc(),
                Publication.created_at.desc(),
                Publication.id.desc(),
            )
        # default: newest
        return (Publication.created_at.desc(), Publication.id.desc())

    async def get_latest_version(self, source_product_id: str, config_hash: str) -> int | None:
        """Get the latest version number for a given product and configuration hash.

        Args:
            source_product_id: The StatCan product ID.
            config_hash: Hash of the chart configuration.

        Returns:
            The highest version number, or None if no match is found.
        """
        stmt = (
            select(func.max(Publication.version))
            .where(Publication.source_product_id == source_product_id)
            .where(Publication.config_hash == config_hash)
        )
        result = await self._session.execute(stmt)
        return result.scalar()

    async def create_published(
        self,
        *,
        headline: str,
        chart_type: str,
        s3_key_lowres: str,
        s3_key_highres: str,
        source_product_id: str | None,
        version: int,
        config_hash: str,
        content_hash: str,
        virality_score: float | None = None,
        status: PublicationStatus = PublicationStatus.PUBLISHED,
    ) -> Publication:
        """Create a new publication record with versioning.

        Args:
            headline: Short title for the graphic.
            chart_type: Identifier for the chart type.
            s3_key_lowres: S3 key for low-res preview.
            s3_key_highres: S3 key for high-res asset.
            source_product_id: StatCan product ID.
            version: The publication version.
            config_hash: Hash of the configuration.
            content_hash: Hash of the image content.
            virality_score: Optional AI-estimated virality score.

        Returns:
            The newly created ``Publication`` instance.
        """
        for attempt in range(3):
            try:
                publication = Publication(
                    headline=headline,
                    chart_type=chart_type,
                    s3_key_lowres=s3_key_lowres,
                    s3_key_highres=s3_key_highres,
                    source_product_id=source_product_id,
                    version=version + attempt,
                    config_hash=config_hash,
                    content_hash=content_hash,
                    virality_score=virality_score,
                    status=status,
                )
                self._session.add(publication)
                await self._session.flush()
                await self._session.refresh(publication)
                return publication
            except IntegrityError:
                await self._session.rollback()
                if attempt == 2:
                    raise
        raise RuntimeError("Failed to create publication after 3 attempts")

    async def create(
        self,
        *,
        headline: str,
        chart_type: str,
        s3_key_lowres: str | None = None,
        s3_key_highres: str | None = None,
        virality_score: float | None = None,
        status: PublicationStatus = PublicationStatus.DRAFT,
    ) -> Publication:
        """Create a new publication record.

        Args:
            headline: Short title for the graphic.
            chart_type: Identifier for the chart type.
            s3_key_lowres: Optional S3 key for low-res preview.
            s3_key_highres: Optional S3 key for high-res asset.
            virality_score: Optional AI-estimated virality score.
            status: Initial lifecycle status (default: DRAFT).

        Returns:
            The newly created ``Publication`` instance with its ``id``
            populated after flush.
        """
        publication = Publication(
            headline=headline,
            chart_type=chart_type,
            s3_key_lowres=s3_key_lowres,
            s3_key_highres=s3_key_highres,
            virality_score=virality_score,
            status=status,
        )
        self._session.add(publication)
        await self._session.flush()
        await self._session.refresh(publication)
        return publication

    async def get_published(
        self,
        limit: int,
        offset: int,
    ) -> list[Publication]:
        """Return published publications ordered by newest first.

        Args:
            limit: Maximum number of records to return.
            offset: Number of records to skip (for pagination).

        Returns:
            A list of ``Publication`` instances with ``PUBLISHED`` status.
        """
        stmt = (
            select(Publication)
            .where(Publication.status == PublicationStatus.PUBLISHED)
            .order_by(Publication.created_at.desc(), Publication.id.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_published_sorted(
        self,
        limit: int,
        offset: int,
        sort: str = "newest",
    ) -> list[Publication]:
        """Return published publications with configurable sort order.

        Args:
            limit: Maximum number of records to return.
            offset: Number of records to skip (for pagination).
            sort: Sort order — one of ``"newest"``, ``"oldest"``, or
                ``"score"`` (descending virality score).

        Returns:
            A list of ``Publication`` instances with ``PUBLISHED`` status.
        """
        stmt = (
            select(Publication)
            .where(Publication.status == PublicationStatus.PUBLISHED)
            .order_by(*self._published_order_clause(sort))
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, publication_id: int) -> Publication | None:
        """Return a single publication by primary key, or ``None``.

        Args:
            publication_id: Primary key of the publication to fetch.

        Returns:
            The ``Publication`` instance, or ``None`` if not found.
        """
        stmt = select(Publication).where(Publication.id == publication_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_drafts(self, limit: int) -> list[Publication]:
        """Return draft publications sorted by virality score (highest first).

        Args:
            limit: Maximum number of records to return.

        Returns:
            A list of ``Publication`` instances with ``DRAFT`` status,
            ordered by ``virality_score`` descending.
        """
        stmt = (
            select(Publication)
            .where(Publication.status == PublicationStatus.DRAFT)
            .order_by(Publication.virality_score.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update_status(
        self,
        publication_id: int,
        status: PublicationStatus,
    ) -> None:
        """Update the status of a publication by ID.

        Args:
            publication_id: Primary key of the publication to update.
            status: New status to set.
        """
        stmt = (
            update(Publication)
            .where(Publication.id == publication_id)
            .values(status=status)
        )
        await self._session.execute(stmt)

    async def update_s3_keys(
        self,
        publication_id: int,
        s3_key_lowres: str,
        s3_key_highres: str,
    ) -> None:
        """Update the S3 object keys for a publication.

        Args:
            publication_id: Primary key of the publication to update.
            s3_key_lowres: S3 key for the low-resolution preview.
            s3_key_highres: S3 key for the high-resolution asset.
        """
        stmt = (
            update(Publication)
            .where(Publication.id == publication_id)
            .values(
                s3_key_lowres=s3_key_lowres,
                s3_key_highres=s3_key_highres,
            )
        )
        await self._session.execute(stmt)

    async def update_s3_keys_and_publish(
        self,
        publication_id: int,
        s3_key_lowres: str,
        s3_key_highres: str,
        status: PublicationStatus,
    ) -> None:
        """Update the S3 object keys and status for a publication.

        Args:
            publication_id: Primary key of the publication to update.
            s3_key_lowres: S3 key for the low-resolution preview.
            s3_key_highres: S3 key for the high-resolution asset.
            status: Status to update to.
        """
        stmt = (
            update(Publication)
            .where(Publication.id == publication_id)
            .values(
                s3_key_lowres=s3_key_lowres,
                s3_key_highres=s3_key_highres,
                status=status,
            )
        )
        await self._session.execute(stmt)

    # ------------------------------------------------------------------
    # Editor + Gallery extension
    # ------------------------------------------------------------------

    @staticmethod
    def _serialize_visual_config(value: Any) -> str | None:
        """Coerce a visual_config value to a JSON string for storage.

        Accepts ``None``, an existing JSON string, a dict, or a Pydantic
        model exposing ``model_dump``. Returns the JSON-serialised form.
        """
        if value is None:
            return None
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            return json.dumps(value)
        # Pydantic model with ``model_dump`` (e.g. VisualConfig)
        if hasattr(value, "model_dump"):
            return json.dumps(value.model_dump())
        raise TypeError(
            f"Unsupported visual_config type: {type(value).__name__}"
        )

    async def create_full(self, data: dict[str, Any]) -> Publication:
        """Create a publication with all editorial + visual fields.

        Args:
            data: Mapping produced by ``PublicationCreate.model_dump()``.
                If a ``visual_config`` entry is present and not already a
                JSON string, it is serialised before persistence.

        Returns:
            The newly created :class:`Publication` (in ``DRAFT`` status
            unless ``status`` is provided in ``data``).
        """
        payload = dict(data)
        if "visual_config" in payload:
            payload["visual_config"] = self._serialize_visual_config(
                payload["visual_config"]
            )

        payload.setdefault("status", PublicationStatus.DRAFT)

        publication = Publication(**payload)
        self._session.add(publication)
        await self._session.flush()
        await self._session.refresh(publication)
        return publication

    async def update_fields(
        self,
        pub_id: int,
        data: dict[str, Any],
    ) -> Publication | None:
        """Apply a partial update to a publication.

        Partial-update semantics (PATCH):

        * Keys NOT present in ``data`` are left unchanged.
        * Keys present in ``data`` are always applied — including
          explicit ``None`` which clears nullable editorial fields
          (``eyebrow``, ``description``, ``source_text``, ``footnote``,
          ``visual_config``).

        Callers should produce ``data`` via
        ``PublicationUpdate.model_dump(exclude_unset=True)`` so omitted
        fields do not accidentally overwrite existing values.

        Visual config dicts / Pydantic models are serialised to JSON
        before being persisted; ``None`` clears the column.

        Args:
            pub_id: Primary key of the publication to update.
            data: Field map. Every key in the dict is applied, including
                explicit ``None`` values (for clearing nullable fields).

        Returns:
            The updated :class:`Publication`, or ``None`` if not found.
        """
        publication = await self._session.get(Publication, pub_id)
        if publication is None:
            return None

        for key, value in data.items():
            if key == "visual_config":
                value = self._serialize_visual_config(value)
            setattr(publication, key, value)

        await self._session.flush()
        await self._session.refresh(publication)
        return publication

    async def publish(self, pub_id: int) -> Publication | None:
        """Transition the publication to ``PUBLISHED`` and stamp the time.

        Args:
            pub_id: Primary key of the publication to publish.

        Returns:
            The updated :class:`Publication`, or ``None`` if not found.
        """
        publication = await self._session.get(Publication, pub_id)
        if publication is None:
            return None

        publication.status = PublicationStatus.PUBLISHED
        publication.published_at = func.now()
        await self._session.flush()
        await self._session.refresh(publication)
        return publication

    async def unpublish(self, pub_id: int) -> Publication | None:
        """Revert the publication back to ``DRAFT`` status.

        Note:
            ``published_at`` is intentionally left in place so the
            timeline of past publications remains auditable.

        Args:
            pub_id: Primary key of the publication to revert.

        Returns:
            The updated :class:`Publication`, or ``None`` if not found.
        """
        publication = await self._session.get(Publication, pub_id)
        if publication is None:
            return None

        publication.status = PublicationStatus.DRAFT
        await self._session.flush()
        await self._session.refresh(publication)
        return publication

    async def list_by_status(
        self,
        status_filter: PublicationStatus | None,
        limit: int,
        offset: int,
    ) -> list[Publication]:
        """List publications, optionally filtered by status.

        Used by the admin listing endpoint
        (``GET /api/v1/admin/publications``). Ordering is newest-first
        with id tie-break for stable pagination.

        Args:
            status_filter: ``None`` returns all statuses;
                ``PublicationStatus.DRAFT`` or ``.PUBLISHED`` filter.
            limit: Maximum number of records.
            offset: Number of records to skip.

        Returns:
            A list of :class:`Publication` instances.
        """
        stmt = select(Publication)
        if status_filter is not None:
            stmt = stmt.where(Publication.status == status_filter)
        stmt = (
            stmt.order_by(
                Publication.created_at.desc(), Publication.id.desc()
            )
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
