"""Publication ORM model.

Represents a generated graphic / infographic that can be stored in
draft or published state.  The low-res and high-res S3 keys allow the
API to serve a preview thumbnail while the full-resolution asset is
used for downloads.
"""

from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Float, String, Text
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
    """

    __tablename__ = "publications"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    headline: Mapped[str] = mapped_column(String(500), nullable=False)
    chart_type: Mapped[str] = mapped_column(String(100), nullable=False)
    s3_key_lowres: Mapped[str | None] = mapped_column(Text, nullable=True)
    s3_key_highres: Mapped[str | None] = mapped_column(Text, nullable=True)
    virality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[PublicationStatus] = mapped_column(
        Enum(PublicationStatus, name="publication_status"),
        nullable=False,
        default=PublicationStatus.DRAFT,
        server_default="DRAFT",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<Publication(id={self.id}, headline={self.headline!r}, "
            f"status={self.status.value})>"
        )
