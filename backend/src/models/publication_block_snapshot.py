"""Phase 3.1d: PublicationBlockSnapshot ORM model.

Per recon ``docs/recon/phase-3-1d-recon.md`` §2.1. Captures publish-time
fingerprint of each bound block for later staleness comparison.

JSONB-on-PG / JSON-on-SQLite parity follows the established pattern in
``semantic_mapping`` / ``cube_metadata_cache``.
"""
from __future__ import annotations

from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class PublicationBlockSnapshot(Base):
    """Publish-time snapshot of a bound block on a publication.

    Identity: ``UNIQUE(publication_id, block_id)``. Captured semantic
    context (``cube_id``, ``semantic_key``, ``coord``, ``period``) +
    raw resolve inputs (``dims_json``, ``members_json``) live alongside
    the fingerprint columns for mechanical re-resolve during compare.
    """

    __tablename__ = "publication_block_snapshot"
    __table_args__ = (
        UniqueConstraint(
            "publication_id",
            "block_id",
            name="uq_publication_block_snapshot_pub_block",
        ),
        Index(
            "ix_publication_block_snapshot_publication_id",
            "publication_id",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    publication_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("publications.id", ondelete="CASCADE"),
        nullable=False,
    )
    block_id: Mapped[str] = mapped_column(String(length=128), nullable=False)
    cube_id: Mapped[str] = mapped_column(String(length=50), nullable=False)
    semantic_key: Mapped[str] = mapped_column(String(length=200), nullable=False)
    coord: Mapped[str] = mapped_column(String(length=40), nullable=False)
    period: Mapped[str | None] = mapped_column(String(length=20), nullable=True)
    dims_json: Mapped[list[int]] = mapped_column(
        JSONB(astext_type=sa.Text()).with_variant(JSON(), "sqlite"),
        nullable=False,
    )
    members_json: Mapped[list[int]] = mapped_column(
        JSONB(astext_type=sa.Text()).with_variant(JSON(), "sqlite"),
        nullable=False,
    )
    mapping_version_at_publish: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    source_hash_at_publish: Mapped[str] = mapped_column(
        String(length=64), nullable=False
    )
    value_at_publish: Mapped[str | None] = mapped_column(Text, nullable=True)
    missing_at_publish: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_stale_at_publish: Mapped[bool] = mapped_column(Boolean, nullable=False)
    captured_at: Mapped[datetime] = mapped_column(
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
