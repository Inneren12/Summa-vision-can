"""AuditEvent ORM model — generic operational event record (R18).

Stores every significant system action with typed classification.
Used for KPI dashboards, debugging, and operational alerting.

Retention: raw events kept for ``AUDIT_RETENTION_DAYS`` (default 90).
Aggregation tables are backlog — raw events are sufficient for MVP.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class AuditEvent(Base):
    """A single operational event in the audit trail.

    Attributes:
        id: Auto-incrementing primary key.
        event_type: Typed event classification from ``EventType`` enum.
            Validated at write time by ``AuditWriter``. Arbitrary
            strings are rejected.
        entity_type: Kind of entity this event relates to
            (e.g. ``"job"``, ``"lead"``, ``"publication"``).
        entity_id: Identifier of the specific entity instance
            (e.g. job ID, lead ID, publication ID). Stored as string
            for flexibility across entity types.
        metadata_json: Optional JSON with event-specific details
            (e.g. error_code, product_id, attempt_count).
        created_at: UTC timestamp when the event occurred.
        actor: Who/what caused the event. ``"system"`` for automated
            actions, ``"admin:name"`` for operator actions, ``None``
            if not applicable.
    """

    __tablename__ = "audit_events"
    __table_args__ = (
        Index("ix_audit_type_created", "event_type", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    event_type: Mapped[str] = mapped_column(
        String(80), nullable=False, index=True
    )
    entity_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )
    entity_id: Mapped[str] = mapped_column(
        String(100), nullable=False
    )

    metadata_json: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    actor: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<AuditEvent(id={self.id}, type={self.event_type!r}, "
            f"entity={self.entity_type}:{self.entity_id})>"
        )
