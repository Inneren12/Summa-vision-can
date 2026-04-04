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

from sqlalchemy import select, update
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
            .order_by(Publication.created_at.desc())
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
        order_clause = {
            "newest": Publication.created_at.desc(),
            "oldest": Publication.created_at.asc(),
            "score": Publication.virality_score.desc(),
        }.get(sort, Publication.created_at.desc())

        stmt = (
            select(Publication)
            .where(Publication.status == PublicationStatus.PUBLISHED)
            .order_by(order_clause)
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
