"""Phase 3.1aaa: SemanticValueCache ORM model.

Persistent cache of StatCan vectorDataPoint rows. Populated by
:class:`StatCanValueCacheService` (auto-prime on mapping save, best-
effort) and refreshed nightly by the
``statcan_value_cache_refresh`` scheduler job. Read by the resolve
service (3.1c, deferred).

Storage shape — row per period
------------------------------
Each row represents one (cube_id, semantic_key, coord, ref_period)
data point. Multiple periods for the same (cube_id, semantic_key,
coord) coexist as separate rows. Founder-locked decision Q-1.

period_start
------------
On Postgres the ``period_start`` column is a STORED GENERATED column
populated by ``parse_ref_period_to_date(ref_period)`` (defined in
migration ``478d906c6410``). On SQLite (test fixtures) the column is
declared as a regular nullable Date; the GENERATED clause is enforced
at the DDL level only in the live database. This mirrors the
``cube_catalog.search_vector`` precedent — PG-specific machinery
lives in the migration, not the ORM.

Mirrors :class:`CubeMetadataCache` (3.1aa) for ORM conventions.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class SemanticValueCache(Base):
    """Cached StatCan data point keyed by (cube_id, semantic_key, coord, ref_period)."""

    __tablename__ = "semantic_value_cache"
    __table_args__ = (
        UniqueConstraint(
            "cube_id",
            "semantic_key",
            "coord",
            "ref_period",
            name="uq_semantic_value_cache_lookup",
        ),
        ForeignKeyConstraint(
            ["cube_id", "semantic_key"],
            ["semantic_mappings.cube_id", "semantic_mappings.semantic_key"],
            name="fk_semantic_value_cache_mapping",
            ondelete="CASCADE",
        ),
        Index("ix_semantic_value_cache_product_id", "product_id"),
        Index(
            "ix_semantic_value_cache_coord",
            "cube_id",
            "semantic_key",
            "coord",
        ),
        Index("ix_semantic_value_cache_fetched_at", "fetched_at"),
        Index("ix_semantic_value_cache_period_start", "period_start"),
        # Partial index — Postgres only; SQLAlchemy emits the
        # ``WHERE`` clause via ``postgresql_where``. SQLite ignores
        # the dialect kwarg and creates a plain index, which is a
        # tolerable superset for tests.
        Index(
            "ix_semantic_value_cache_is_stale",
            "is_stale",
            postgresql_where=sa.text("is_stale = true"),
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer(), "sqlite"),
        primary_key=True,
        autoincrement=True,
    )
    cube_id: Mapped[str] = mapped_column(String(length=50), nullable=False)
    product_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    semantic_key: Mapped[str] = mapped_column(String(length=100), nullable=False)
    coord: Mapped[str] = mapped_column(String(length=50), nullable=False)
    ref_period: Mapped[str] = mapped_column(String(length=20), nullable=False)
    # period_start: PG migration declares this column GENERATED ALWAYS
    # AS (parse_ref_period_to_date(ref_period)) STORED. ORM exposes a
    # plain nullable Date so SQLite tests can build the schema via
    # ``Base.metadata.create_all`` (the parser function is PG-only).
    period_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    value: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=18, scale=6), nullable=True
    )
    missing: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=sa.false()
    )
    decimals: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sa.text("0")
    )
    scalar_factor_code: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sa.text("0")
    )
    symbol_code: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sa.text("0")
    )
    security_level_code: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sa.text("0")
    )
    status_code: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sa.text("0")
    )
    frequency_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    vector_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    response_status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_hash: Mapped[str] = mapped_column(String(length=64), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    release_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_stale: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=sa.false()
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
