"""CubeCatalog ORM model — StatCan cube metadata index.

Stores metadata for all ~7,000 Statistics Canada data cubes.
Populated by CatalogSyncService (A-3) via the ``getAllCubesList``
API endpoint. Queried by CubeCatalogRepository (A-2) with bilingual
full-text search and trigram similarity for typo tolerance.

Architecture decision R12:
    ``id`` is an autoincrement PK (not the StatCan cube_id).
    ``product_id`` is the StatCan business identifier (e.g. "14-10-0127-01"),
    stored as a unique indexed string.
    ``cube_id_statcan`` is the numeric StatCan internal ID, stored
    separately for API compatibility.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class CubeCatalog(Base):
    """A StatCan data cube in the searchable catalog.

    Attributes:
        id: Auto-incrementing primary key (R12).
        product_id: StatCan product identifier (e.g. ``"14-10-0127-01"``).
            Unique, indexed. Used as the business key for lookups.
        cube_id_statcan: StatCan numeric cube ID. Indexed for API calls.
        title_en: English title of the cube (up to 500 chars).
        title_fr: French title (nullable — some cubes lack FR translation).
        subject_code: StatCan subject classification code (e.g. ``"14"``,
            ``"18"``). Indexed for category-based browsing.
        subject_en: English subject name (e.g. ``"Labour"``).
        survey_en: English survey name (nullable).
        frequency: Data release frequency (``"Daily"``, ``"Monthly"``,
            ``"Quarterly"``, ``"Annual"``). Used by DataFetchService (A-5)
            to calculate dynamic periods (R13).
        start_date: Earliest data reference date (nullable).
        end_date: Latest data reference date (nullable).
        archive_status: Whether this cube has been archived by StatCan.
        last_synced_at: UTC timestamp of last successful catalog sync.
    """

    __tablename__ = "cube_catalog"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    product_id: Mapped[str] = mapped_column(
        String(30), nullable=False, unique=True, index=True
    )
    cube_id_statcan: Mapped[int] = mapped_column(
        Integer, nullable=False, index=True
    )

    title_en: Mapped[str] = mapped_column(String(500), nullable=False)
    title_fr: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )

    subject_code: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )
    subject_en: Mapped[str] = mapped_column(String(255), nullable=False)
    survey_en: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )

    frequency: Mapped[str] = mapped_column(String(20), nullable=False)

    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    archive_status: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<CubeCatalog(id={self.id}, product_id={self.product_id!r}, "
            f"title={self.title_en[:50]!r}...)>"
        )