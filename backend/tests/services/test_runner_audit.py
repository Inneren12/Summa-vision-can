"""Audit event integration tests for JobRunner."""

from __future__ import annotations

from types import SimpleNamespace

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.audit_event import AuditEvent
from src.repositories.job_repository import JobRepository
from src.services.jobs.runner import JobRunner
from src.services.jobs.handlers import register_handler


def _make_test_session_factory(db_session: AsyncSession):
    # Helper to mock session factory using an existing session
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def _factory():
        yield db_session
    return _factory


async def test_runner_writes_audit_events_on_success(
    db_session: AsyncSession,
) -> None:
    """Runner writes job.started and job.succeeded audit events."""
    app_state = SimpleNamespace()

    async def ok_handler(payload, *, app_state):
        return {"ok": True}

    from src.schemas.job_payloads import PAYLOAD_REGISTRY, CatalogSyncPayload
    PAYLOAD_REGISTRY["audit_success_test"] = CatalogSyncPayload

    register_handler("audit_success_test", ok_handler)

    repo = JobRepository(db_session)
    job, _ = await repo.enqueue(
        "audit_success_test",
        '{"schema_version": 1}',
    )
    await db_session.commit()

    runner = JobRunner(
        _make_test_session_factory(db_session),
        app_state,
    )
    await runner.execute_once()

    # Check audit events exist
    result = await db_session.execute(
        select(AuditEvent).where(
            AuditEvent.entity_type == "job"
        ).order_by(AuditEvent.created_at)
    )
    events = result.scalars().all()
    event_types = [e.event_type for e in events]

    assert "job.created" in event_types, f"Missing job.created, got: {event_types}"
    assert "job.started" in event_types, f"Missing job.started, got: {event_types}"
    assert "job.succeeded" in event_types, f"Missing job.succeeded, got: {event_types}"


async def test_runner_writes_audit_events_on_failure(
    db_session: AsyncSession,
) -> None:
    """Runner writes job.started and job.failed audit events."""
    app_state = SimpleNamespace()

    async def fail_handler(payload, *, app_state):
        raise RuntimeError("intentional failure")

    from src.schemas.job_payloads import PAYLOAD_REGISTRY, CatalogSyncPayload
    PAYLOAD_REGISTRY["audit_fail_test"] = CatalogSyncPayload

    register_handler("audit_fail_test", fail_handler)

    repo = JobRepository(db_session)
    job, _ = await repo.enqueue(
        "audit_fail_test",
        '{"schema_version": 1}',
        max_attempts=1,  # No retry — immediate failure
    )
    await db_session.commit()

    runner = JobRunner(
        _make_test_session_factory(db_session),
        app_state,
    )
    await runner.execute_once()

    result = await db_session.execute(
        select(AuditEvent).where(
            AuditEvent.entity_type == "job"
        ).order_by(AuditEvent.created_at)
    )
    events = result.scalars().all()
    event_types = [e.event_type for e in events]

    assert "job.created" in event_types, f"Missing job.created, got: {event_types}"
    assert "job.started" in event_types, f"Missing job.started, got: {event_types}"
    assert "job.failed" in event_types, f"Missing job.failed, got: {event_types}"


async def test_enqueue_writes_job_created_event(
    db_session: AsyncSession,
) -> None:
    """JobRepository.enqueue() writes job.created audit event."""
    repo = JobRepository(db_session)
    job, _ = await repo.enqueue(
        "catalog_sync",
        '{"schema_version": 1}',
        created_by="admin:test",
    )
    await db_session.commit()

    result = await db_session.execute(
        select(AuditEvent).where(
            AuditEvent.event_type == "job.created",
            AuditEvent.entity_id == str(job.id),
        )
    )
    event = result.scalar_one_or_none()

    assert event is not None, "job.created event not found"
    assert event.actor == "admin:test"
    assert event.entity_type == "job"


async def test_dedupe_enqueue_does_not_create_duplicate_event(
    db_session: AsyncSession,
) -> None:
    """Deduped enqueue returns existing job without new job.created event."""
    repo = JobRepository(db_session)
    job1, _ = await repo.enqueue(
        "catalog_sync",
        '{"schema_version": 1}',
        dedupe_key="test_dedupe",
    )
    await db_session.commit()

    count_before = await db_session.scalar(
        select(func.count(AuditEvent.id)).where(
            AuditEvent.event_type == "job.created"
        )
    )

    # Second enqueue with same dedupe_key — should return existing
    job2, _ = await repo.enqueue(
        "catalog_sync",
        '{"schema_version": 1}',
        dedupe_key="test_dedupe",
    )
    await db_session.commit()

    assert job2.id == job1.id  # same job

    count_after = await db_session.scalar(
        select(func.count(AuditEvent.id)).where(
            AuditEvent.event_type == "job.created"
        )
    )

    assert count_after == count_before, "Deduped enqueue should not create new audit event"
