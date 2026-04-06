"""AuditWriter — validated event recording service (R18).

Validates every event_type against the ``EventType`` enum before
writing. Arbitrary strings are rejected with ``ValueError``.

Usage::

    writer = AuditWriter(session)
    await writer.log_event(
        event_type=EventType.JOB_CREATED,
        entity_type="job",
        entity_id=str(job.id),
        metadata={"job_type": "catalog_sync"},
        actor="system",
    )

The writer does NOT call ``session.commit()``. Commits are handled
by the caller or the ``get_db`` dependency at request boundary.
"""

from __future__ import annotations

import json
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.audit_event import AuditEvent
from src.schemas.events import EventType

logger = structlog.get_logger()


class AuditWriter:
    """Writes validated audit events to the database."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def log_event(
        self,
        event_type: EventType | str,
        entity_type: str,
        entity_id: str,
        metadata: dict[str, Any] | None = None,
        actor: str | None = None,
    ) -> AuditEvent:
        """Record a single audit event.

        Args:
            event_type: Must be a valid ``EventType`` enum member or
                its string value. Arbitrary strings are rejected.
            entity_type: Kind of entity (``"job"``, ``"lead"``, etc.).
            entity_id: Specific entity identifier (as string).
            metadata: Optional dict with event-specific details.
                Serialized to JSON for storage.
            actor: Who triggered the event. ``"system"`` for automated.

        Returns:
            The created ``AuditEvent`` record.

        Raises:
            ValueError: If ``event_type`` is not in the ``EventType`` enum.
        """
        # Validate event_type against taxonomy
        validated_type = self._validate_event_type(event_type)

        metadata_json: str | None = None
        if metadata is not None:
            metadata_json = json.dumps(metadata, default=str)

        event = AuditEvent(
            event_type=validated_type,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata_json=metadata_json,
            actor=actor,
        )

        self._session.add(event)
        await self._session.flush()
        await self._session.refresh(event)

        logger.debug(
            "audit_event_recorded",
            event_type=validated_type,
            entity_type=entity_type,
            entity_id=entity_id,
        )

        return event

    # Module-level cache — EventType members don't change at runtime
    _VALID_EVENT_VALUES: frozenset[str] = frozenset(e.value for e in EventType)

    @staticmethod
    def _validate_event_type(event_type: EventType | str) -> str:
        """Ensure event_type is a member of the EventType enum.

        Accepts both ``EventType.JOB_CREATED`` and ``"job.created"``.

        Raises:
            ValueError: If the value is not in the enum.
        """
        if isinstance(event_type, EventType):
            return event_type.value

        if event_type not in AuditWriter._VALID_EVENT_VALUES:
            raise ValueError(
                f"Unknown event_type: {event_type!r}. "
                f"Must be one of: {sorted(AuditWriter._VALID_EVENT_VALUES)}"
            )
        return event_type
