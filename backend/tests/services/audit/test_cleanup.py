"""Tests for audit event retention cleanup."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.models.audit_event import AuditEvent
from src.services.audit.cleanup import cleanup_old_audit_events


def _make_event(created_at: datetime, event_type: str = "test.event") -> AuditEvent:
    """Helper: build an AuditEvent with a specific created_at timestamp."""
    return AuditEvent(
        event_type=event_type,
        entity_type="test",
        entity_id="1",
        created_at=created_at,
    )


@pytest.fixture()
async def session_factory(async_engine):
    """Provide an async_sessionmaker bound to the in-memory test engine."""
    factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    return factory


@pytest.mark.asyncio
async def test_cleanup_deletes_old_events(session_factory):
    """Events older than retention are deleted, recent ones kept."""
    now = datetime.now(timezone.utc)
    old_event = _make_event(created_at=now - timedelta(days=100))
    recent_event = _make_event(created_at=now - timedelta(days=5))

    async with session_factory() as session:
        session.add(old_event)
        session.add(recent_event)
        await session.commit()

    deleted = await cleanup_old_audit_events(session_factory, retention_days=90)
    assert deleted == 1

    # Verify only the recent event survives
    async with session_factory() as session:
        result = await session.execute(select(AuditEvent))
        remaining = result.scalars().all()
        assert len(remaining) == 1
        # SQLite returns naive datetimes; compare without tzinfo
        created = remaining[0].created_at.replace(tzinfo=None)
        cutoff = (now - timedelta(days=90)).replace(tzinfo=None)
        assert created > cutoff


@pytest.mark.asyncio
async def test_cleanup_empty_table(session_factory):
    """No crash when table is empty."""
    deleted = await cleanup_old_audit_events(session_factory, retention_days=90)
    assert deleted == 0


@pytest.mark.asyncio
async def test_cleanup_respects_retention_days(session_factory):
    """Custom retention_days is honored."""
    now = datetime.now(timezone.utc)
    event_10_days_ago = _make_event(created_at=now - timedelta(days=10))

    # Insert the event
    async with session_factory() as session:
        session.add(event_10_days_ago)
        await session.commit()

    # retention_days=7 → event is 10 days old → should be deleted
    deleted = await cleanup_old_audit_events(session_factory, retention_days=7)
    assert deleted == 1

    # Re-insert for the next check
    event_10_days_ago_2 = _make_event(created_at=now - timedelta(days=10))
    async with session_factory() as session:
        session.add(event_10_days_ago_2)
        await session.commit()

    # retention_days=30 → event is 10 days old → should NOT be deleted
    deleted = await cleanup_old_audit_events(session_factory, retention_days=30)
    assert deleted == 0

    # Verify event still in DB
    async with session_factory() as session:
        result = await session.execute(select(AuditEvent))
        remaining = result.scalars().all()
        assert len(remaining) == 1
