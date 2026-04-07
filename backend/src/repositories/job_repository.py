"""Repository for persistent job orchestration.

Implements safe job claiming with dialect-aware locking:
- PostgreSQL: ``FOR UPDATE SKIP LOCKED`` prevents deadlocks (R8).
- SQLite: Simple ``SELECT ... LIMIT 1`` for unit tests only — no
  locking guarantees. Integration tests with PostgreSQL verify
  locking behavior separately.

Commit semantics: repositories flush/refresh but do NOT commit.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import select, update
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from src.models.job import Job, JobStatus


@dataclass(frozen=True, slots=True)
class EnqueueResult:
    """Result of an enqueue operation."""
    job: Job
    created: bool


class JobRepository:
    """Data access layer for persistent jobs."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def enqueue(
        self,
        job_type: str,
        payload_json: str,
        *,
        dedupe_key: str | None = None,
        created_by: str | None = None,
        max_attempts: int = 3,
    ) -> EnqueueResult:
        """Create a new job or return existing if dedupe_key matches.

        If ``dedupe_key`` is provided and a job with the same key already
        exists in ``queued`` or ``running`` status, the existing job is
        returned instead of creating a duplicate.

        Returns:
            EnqueueResult with the job and a created boolean flag.
        """
        if dedupe_key is not None:
            existing = await self._find_active_by_dedupe(dedupe_key)
            if existing is not None:
                return EnqueueResult(job=existing, created=False)

        job = Job(
            job_type=job_type,
            payload_json=payload_json,
            dedupe_key=dedupe_key,
            created_by=created_by,
            max_attempts=max_attempts,
        )
        self._session.add(job)

        try:
            await self._session.flush()
        except IntegrityError:
            # Race condition: another session inserted with same dedupe_key
            # between our SELECT and INSERT. Roll back and fetch the winner.
            await self._session.rollback()
            existing = await self._find_active_by_dedupe(dedupe_key)
            if existing is not None:
                return EnqueueResult(job=existing, created=False)
            raise  # Unknown integrity error — re-raise

        await self._session.refresh(job)

        # Emit job.created audit event
        from src.services.audit import AuditWriter
        from src.schemas.events import EventType

        audit = AuditWriter(self._session)
        await audit.log_event(
            event_type=EventType.JOB_CREATED,
            entity_type="job",
            entity_id=str(job.id),
            metadata={
                "job_type": job_type,
                "dedupe_key": dedupe_key,
            },
            actor=created_by or "system",
        )

        return EnqueueResult(job=job, created=True)

    async def claim_next(
        self,
        job_type: str | None = None,
    ) -> Job | None:
        """Atomically claim the next queued job.

        Uses ``FOR UPDATE SKIP LOCKED`` on PostgreSQL to prevent
        concurrent workers from claiming the same job.
        Falls back to simple SELECT on SQLite (unit tests only).
        """
        stmt = (
            select(Job)
            .where(Job.status == JobStatus.QUEUED)
            .order_by(Job.created_at.asc())
            .limit(1)
        )

        if job_type is not None:
            stmt = stmt.where(Job.job_type == job_type)

        # Dialect-aware locking (R8 + R11)
        dialect = self._session.bind.dialect.name if self._session.bind else ""
        if dialect == "postgresql":
            stmt = stmt.with_for_update(skip_locked=True)

        result = await self._session.execute(stmt)
        job = result.scalar_one_or_none()

        if job is not None:
            job.status = JobStatus.RUNNING
            job.started_at = datetime.now(timezone.utc)
            job.attempt_count += 1
            await self._session.flush()

        return job

    async def mark_success(
        self,
        job_id: int,
        result_json: str | None = None,
    ) -> None:
        """Mark a job as successfully completed."""
        await self._session.execute(
            update(Job)
            .where(Job.id == job_id)
            .values(
                status=JobStatus.SUCCESS,
                result_json=result_json,
                finished_at=datetime.now(timezone.utc),
            )
        )

    async def mark_failed(
        self,
        job_id: int,
        error_code: str,
        error_message: str,
    ) -> None:
        """Mark a job as failed."""
        await self._session.execute(
            update(Job)
            .where(Job.id == job_id)
            .values(
                status=JobStatus.FAILED,
                error_code=error_code,
                error_message=error_message,
                finished_at=datetime.now(timezone.utc),
            )
        )

    async def list_jobs(
        self,
        job_type: str | None = None,
        status: JobStatus | None = None,
        limit: int = 50,
    ) -> Sequence[Job]:
        """List jobs with optional filters."""
        stmt = select(Job).order_by(Job.created_at.desc()).limit(limit)
        if job_type is not None:
            stmt = stmt.where(Job.job_type == job_type)
        if status is not None:
            stmt = stmt.where(Job.status == status)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_job(self, job_id: int) -> Job | None:
        """Fetch a single job by ID."""
        return await self._session.get(Job, job_id)

    async def requeue_stale_running(
        self,
        stale_threshold_minutes: int = 10,
    ) -> int:
        """Zombie reaper (R8): requeue jobs stuck in 'running' state.

        Only affects jobs that have been running longer than the stale
        threshold AND have remaining retry attempts. This is called
        once on application startup.

        Returns:
            Number of jobs requeued.
        """
        from datetime import timedelta

        cutoff = datetime.now(timezone.utc) - timedelta(
            minutes=stale_threshold_minutes
        )

        result = await self._session.execute(
            update(Job)
            .where(
                Job.status == JobStatus.RUNNING,
                Job.started_at < cutoff,
                Job.attempt_count < Job.max_attempts,
            )
            .values(
                status=JobStatus.QUEUED,
                attempt_count=Job.attempt_count + 1,  # R8: increment
                started_at=None,  # Reset so it doesn't re-trigger reaper
            )
        )
        return result.rowcount  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _find_active_by_dedupe(
        self, dedupe_key: str
    ) -> Job | None:
        """Find an existing queued/running job with the given dedupe key."""
        stmt = (
            select(Job)
            .where(
                Job.dedupe_key == dedupe_key,
                Job.status.in_([JobStatus.QUEUED, JobStatus.RUNNING]),
            )
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()