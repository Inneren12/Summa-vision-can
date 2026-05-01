"""Phase 3.1a: SemanticMapping ORM model."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Integer,
    String,
    Text,
    UniqueConstraint,
    event,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class SemanticMapping(Base):
    """DB-backed semantic mapping for a single cube cell.

    Phase 3.1a: source of truth for the semantic layer. Each row maps a
    semantic_key (operator-facing identifier) to a specific cell of a
    StatCan cube via fixed dimension_filters in `config`.

    config JSONB shape (validated by SemanticMappingConfig pydantic
    schema at app layer)::

        {
          "dimension_filters": {"Geography": "Canada", "Products": "All-items"},
          "measure": "Value",
          "unit": "index",
          "frequency": "monthly",
          "supported_metrics": [
              "current_value",
              "year_over_year_change",
              "previous_period_change"
          ],
          "default_geo": "Canada",
          "notes": "..."
        }

    `version` auto-increments on update via before_update event listener.
    Snapshots stored on publication blocks reference `version` for staleness
    checks (Phase 3.1d / 3.5).

    Phase 3.1a explicitly does NOT validate cube_id existence or dimension
    correctness at save time. Mappings created via the seed CLI script are
    taken on trust; validator service in 3.1ab will hook into save flow
    once admin CRUD endpoints (3.1b) exist.
    """

    __tablename__ = "semantic_mappings"
    __table_args__ = (
        UniqueConstraint(
            "cube_id", "semantic_key", name="uq_semantic_mappings_cube_key"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cube_id: Mapped[str] = mapped_column(
        String(length=50), nullable=False, index=True
    )
    semantic_key: Mapped[str] = mapped_column(String(length=200), nullable=False)
    label: Mapped[str] = mapped_column(String(length=200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    # JSONB on PG, JSON on SQLite (test fixtures use in-memory SQLite)
    config: Mapped[dict] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
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
    updated_by: Mapped[str | None] = mapped_column(String(length=100), nullable=True)


@event.listens_for(SemanticMapping, "before_update")
def _increment_version(mapper, connection, target: SemanticMapping) -> None:
    """Phase 3.1a: auto-increment version on any update.

    Used by snapshot staleness check in 3.1d:
    snapshot.mapping_version != current.version → stale.
    """
    target.version += 1
