"""Tests for AuditWriter and EventType taxonomy (R18)."""

from __future__ import annotations

import json

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.audit_event import AuditEvent
from src.schemas.events import EventType
from src.services.audit import AuditWriter


# ---- Write + read back ----

async def test_log_event_creates_record(db_session: AsyncSession) -> None:
    """AuditWriter creates a record with all fields populated."""
    writer = AuditWriter(db_session)

    event = await writer.log_event(
        event_type=EventType.JOB_CREATED,
        entity_type="job",
        entity_id="42",
        metadata={"job_type": "catalog_sync", "dedupe_key": "sync:2025-04-04"},
        actor="system",
    )
    await db_session.commit()

    assert event.id is not None
    assert event.event_type == "job.created"
    assert event.entity_type == "job"
    assert event.entity_id == "42"
    assert event.actor == "system"
    assert event.created_at is not None

    # Verify metadata round-trip
    meta = json.loads(event.metadata_json)
    assert meta["job_type"] == "catalog_sync"
    assert meta["dedupe_key"] == "sync:2025-04-04"


async def test_log_event_without_metadata(db_session: AsyncSession) -> None:
    """AuditWriter works when metadata and actor are None."""
    writer = AuditWriter(db_session)

    event = await writer.log_event(
        event_type=EventType.CATALOG_SYNCED,
        entity_type="catalog",
        entity_id="full",
    )
    await db_session.commit()

    assert event.metadata_json is None
    assert event.actor is None


async def test_log_event_accepts_string_value(
    db_session: AsyncSession,
) -> None:
    """AuditWriter accepts raw string if it matches an EventType value."""
    writer = AuditWriter(db_session)

    event = await writer.log_event(
        event_type="job.failed",  # string, not enum member
        entity_type="job",
        entity_id="99",
    )
    await db_session.commit()

    assert event.event_type == "job.failed"


# ---- Taxonomy enforcement ----

async def test_log_event_rejects_unknown_type(
    db_session: AsyncSession,
) -> None:
    """AuditWriter raises ValueError for strings not in EventType."""
    writer = AuditWriter(db_session)

    with pytest.raises(ValueError, match="Unknown event_type"):
        await writer.log_event(
            event_type="something.random",
            entity_type="test",
            entity_id="1",
        )


async def test_log_event_rejects_typo(db_session: AsyncSession) -> None:
    """Common typos like 'job_failed' (underscore) are rejected."""
    writer = AuditWriter(db_session)

    with pytest.raises(ValueError, match="Unknown event_type"):
        await writer.log_event(
            event_type="job_failed",  # wrong: underscore instead of dot
            entity_type="job",
            entity_id="1",
        )


# ---- All EventType values are valid ----

@pytest.mark.parametrize("event_type", list(EventType))
async def test_all_enum_values_accepted(
    db_session: AsyncSession,
    event_type: EventType,
) -> None:
    """Every EventType enum member is accepted by AuditWriter."""
    writer = AuditWriter(db_session)

    event = await writer.log_event(
        event_type=event_type,
        entity_type="test",
        entity_id="1",
    )
    await db_session.commit()

    assert event.event_type == event_type.value


# ---- Query by type ----

async def test_query_events_by_type(db_session: AsyncSession) -> None:
    """Events can be filtered by event_type efficiently."""
    writer = AuditWriter(db_session)

    await writer.log_event(EventType.JOB_CREATED, "job", "1")
    await writer.log_event(EventType.JOB_FAILED, "job", "2")
    await writer.log_event(EventType.JOB_CREATED, "job", "3")
    await db_session.commit()

    result = await db_session.execute(
        select(AuditEvent).where(
            AuditEvent.event_type == EventType.JOB_CREATED.value
        )
    )
    created_events = result.scalars().all()
    assert len(created_events) == 2


# ---- Index existence (SQLite-compatible check) ----

async def test_composite_index_exists(db_session: AsyncSession) -> None:
    """Verify ix_audit_type_created index is defined on the model."""
    indexes = {
        idx.name
        for idx in AuditEvent.__table__.indexes
    }
    assert "ix_audit_type_created" in indexes


# ---- EventType enum completeness ----

def test_event_type_enum_has_minimum_members() -> None:
    """EventType must have all required taxonomy members."""
    required = {
        "job.created", "job.started", "job.succeeded", "job.failed",
        "lead.captured", "lead.email_sent",
        "token.created", "token.activated",
        "publication.generated", "publication.published",
        "catalog.synced", "data.contract_violation",
    }
    actual = {e.value for e in EventType}
    missing = required - actual
    assert not missing, f"EventType missing: {missing}"
