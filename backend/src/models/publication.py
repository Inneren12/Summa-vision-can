"""Publication ORM model.

Represents a generated graphic / infographic that can be stored in
draft or published state.  The low-res and high-res S3 keys allow the
API to serve a preview thumbnail while the full-resolution asset is
used for downloads.
"""

from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Float, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class PublicationStatus(enum.Enum):
    """Lifecycle status of a publication."""

    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"


class Publication(Base):
    """A generated graphic asset.

    Attributes:
        id: Auto-incrementing primary key.
        headline: Short title for the graphic (max 500 chars).
        chart_type: Identifier for the type of chart (e.g. ``"bar"``,
            ``"line"``, ``"infographic"``).
        s3_key_lowres: S3 object key for the low-resolution preview.
        s3_key_highres: S3 object key for the full-resolution asset.
        virality_score: AI-estimated virality score (0.0 – 1.0).
        status: Current lifecycle status (DRAFT or PUBLISHED).
        created_at: UTC timestamp of record creation.
        source_product_id: StatCan product ID for versioning.
        version: Publication version number.
        config_hash: Hash of the chart configuration.
        content_hash: Hash of the low-resolution image content.
        eyebrow: Optional eyebrow / kicker line shown above the
            headline on the public gallery card (e.g.
            ``"STATISTICS CANADA · TABLE 18-10-0004"``).
        description: Optional short description shown on the gallery
            card body.
        source_text: Optional source attribution
            (e.g. ``"Source: Statistics Canada, Table 18-10-0004-01"``).
        footnote: Optional methodology / footnote text rendered at the
            bottom of the publication detail view.
        visual_config: JSON-serialised editor layer configuration
            (palette, background, layout, branding, custom primary
            colour). Stored as Text to keep SQLite compatibility for
            unit tests; the application layer parses/dumps the JSON.
        review: JSON-serialised review subtree mirroring the frontend
            ``CanonicalDocument.review`` ( ``workflow``, ``history``,
            ``comments``). Stored as Text for SQLite compatibility.
            The backend stores the payload verbatim — deep validation
            (e.g. comment parent-id integrity) lives on the frontend.
        updated_at: UTC timestamp of the most recent change. Set
            automatically by SQLAlchemy on update.
        published_at: UTC timestamp recorded when the publication
            transitions to ``PUBLISHED``. ``None`` while DRAFT.
    """

    __tablename__ = "publications"
    __table_args__ = (
        UniqueConstraint(
            "source_product_id",
            "config_hash",
            "version",
            name="uq_publication_lineage_version",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    headline: Mapped[str] = mapped_column(String(500), nullable=False)
    chart_type: Mapped[str] = mapped_column(String(100), nullable=False)
    s3_key_lowres: Mapped[str | None] = mapped_column(Text, nullable=True)
    s3_key_highres: Mapped[str | None] = mapped_column(Text, nullable=True)
    virality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_product_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    version: Mapped[int] = mapped_column(nullable=False, default=1, server_default="1")
    config_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[PublicationStatus] = mapped_column(
        Enum(PublicationStatus, name="publication_status"),
        nullable=False,
        default=PublicationStatus.DRAFT,
        server_default="DRAFT",
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    # ------------------------------------------------------------------
    # Editorial fields (Editor + Gallery extension)
    # All nullable for backward compatibility with pre-existing rows.
    # ------------------------------------------------------------------
    eyebrow: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_text: Mapped[str | None] = mapped_column(String(500), nullable=True)
    footnote: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ------------------------------------------------------------------
    # Visual config — JSON-serialised editor layer configuration.
    # Stored as Text for SQLite compatibility.
    # ------------------------------------------------------------------
    visual_config: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ------------------------------------------------------------------
    # Review subtree — JSON-serialised editor workflow, history and
    # comments (mirrors the frontend CanonicalDocument.review subtree).
    # Stored as Text (not JSONB) for SQLite compatibility, matching the
    # ``visual_config`` pattern. The backend stores the payload verbatim
    # and does not deep-validate nested entries; the frontend's
    # ``assertCanonicalDocumentV2Shape`` owns shape validation.
    # ------------------------------------------------------------------
    review: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ------------------------------------------------------------------
    # Lifecycle metadata
    # ------------------------------------------------------------------
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        onupdate=func.now(),
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<Publication(id={self.id}, headline={self.headline!r}, "
            f"status={self.status.value})>"
        )
