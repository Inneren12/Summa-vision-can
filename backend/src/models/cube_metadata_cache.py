"""Phase 3.1aa: CubeMetadataCache ORM model.

Persistent cache of StatCan cube metadata. Populated by
:class:`StatCanMetadataCacheService` (auto-prime on first admin save) and
refreshed nightly by the ``statcan_metadata_cache_refresh`` scheduler
job. Read by the semantic mapping validator (3.1ab) in cache-required
mode — saves fail when no cache row exists; stale rows are tolerated.
"""
from __future__ import annotations

from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import (
    JSON,
    BigInteger,
    DateTime,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class CubeMetadataCache(Base):
    """Cached StatCan cube metadata keyed by ``cube_id``.

    Both ``cube_id`` (semantic mapping form, e.g. ``"18-10-0004-01"``)
    and the numeric ``product_id`` are stored side-by-side so that the
    cache can be invalidated/refreshed without re-deriving one from the
    other (founder-locked recon decision A4).
    """

    __tablename__ = "cube_metadata_cache"
    __table_args__ = (
        UniqueConstraint("cube_id", name="uq_cube_metadata_cache_cube_id"),
        Index("ix_cube_metadata_cache_fetched_at", "fetched_at"),
    )

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer(), "sqlite"),
        primary_key=True,
        autoincrement=True,
    )
    cube_id: Mapped[str] = mapped_column(String(length=50), nullable=False)
    product_id: Mapped[int] = mapped_column(Integer, nullable=False)
    dimensions: Mapped[dict] = mapped_column(
        JSONB(astext_type=sa.Text()).with_variant(JSON(), "sqlite"),
        nullable=False,
    )
    frequency_code: Mapped[str | None] = mapped_column(String(length=8), nullable=True)
    cube_title_en: Mapped[str | None] = mapped_column(String(length=255), nullable=True)
    cube_title_fr: Mapped[str | None] = mapped_column(String(length=255), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
