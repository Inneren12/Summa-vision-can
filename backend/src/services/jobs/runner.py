"""In-process job executor with retry, dedupe, and shutdown awareness.

Architecture decisions:
    R7  — Jobs are persistent DB-backed records.
    R8  — claim_next uses SKIP LOCKED on PostgreSQL.
    R16 — Retry only for idempotent / retryable failures.
    R20 — Runner stops claiming on shutdown, does NOT requeue running job.

Usage in lifespan::

    runner = JobRunner(session_factory, app.state)
    asyncio.create_task(runner.run_loop(poll_interval=2.0))
"""

from __future__ import annotations

import asyncio
import json
import traceback
from datetime import datetime, timedelta, timezone
from typing import Any

import structlog

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.models.job import Job, JobStatus
from src.repositories.job_repository import JobRepository
from src.schemas.job_payloads import (
    IncompatiblePayloadError,
    UnknownJobTypeError,
    parse_payload,
)
from src.services.jobs.handlers import get_handler

logger = structlog.get_logger()


# Error codes that are NEVER retried
NON_RETRYABLE_CODES: set[str] = {
    "UNKNOWN_JOB_TYPE",
    "INCOMPATIBLE_PAYLOAD_VERSION",
    "DATA_CONTRACT_VIOLATION",
}


class JobRunner:
    """Claims and executes persistent jobs in a polling loop.

    Args:
        session_factory: SQLAlchemy async session maker.
        app_state: FastAPI app.state — provides ``shutting_down`` flag
            and resource semaphores (``data_sem``, ``render_sem``, ``io_sem``).
        cool_down_threshold: Number of consecutive DATA_CONTRACT_VIOLATION
            failures for the same product_id within ``cool_down_window``
            before the cube is skipped.
        cool_down_window_hours: Time window for cool-down check.
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        app_state: Any,
        *,
        cool_down_threshold: int = 3,
        cool_down_window_hours: int = 24,
    ) -> None:
        self._session_factory = session_factory
        self._app_state = app_state
        self._cool_down_threshold = cool_down_threshold
        self._cool_down_window = timedelta(hours=cool_down_window_hours)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run_loop(self, poll_interval: float = 2.0) -> None:
        """Poll for queued jobs until shutdown signal.

        This method runs forever (until ``app_state.shutting_down`` is True).
        It should be launched as a background task in the FastAPI lifespan.
        """
        logger.info("job_runner_started", poll_interval=poll_interval)

        while not getattr(self._app_state, "shutting_down", False):
            job_claimed = await self._try_claim_and_execute()

            if not job_claimed:
                # No work available — sleep before next poll
                await asyncio.sleep(poll_interval)

        logger.info("job_runner_stopped", reason="shutdown_signal")

    async def execute_once(self) -> bool:
        """Claim and execute a single job. Used in tests.

        Returns True if a job was processed, False if queue was empty.
        """
        return await self._try_claim_and_execute()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _try_claim_and_execute(self) -> bool:
        """Try to claim one job, execute it, and record result.

        Returns True if a job was claimed and processed (success or failure).
        Returns False if no queued job was available.
        """
        async with self._session_factory() as session:
            repo = JobRepository(session)
            job = await repo.claim_next()
            if job is not None:
                # Record job.started audit event
                from src.services.audit import AuditWriter
                from src.schemas.events import EventType

                audit = AuditWriter(session)
                await audit.log_event(
                    event_type=EventType.JOB_STARTED,
                    entity_type="job",
                    entity_id=str(job.id),
                    metadata={
                        "job_type": job.job_type,
                        "attempt": job.attempt_count,
                    },
                    actor="system",
                )
            await session.commit()

        if job is None:
            return False

        log = logger.bind(job_id=job.id, job_type=job.job_type)
        log.info("job_claimed", attempt=job.attempt_count)

        # --- Validate payload ---
        try:
            payload = parse_payload(job.job_type, job.payload_json)
        except (UnknownJobTypeError, IncompatiblePayloadError) as exc:
            await self._fail_job(
                job.id,
                error_code=exc.error_code,
                error_message=str(exc),
                retryable=False,
                attempt_count=job.attempt_count,
                max_attempts=job.max_attempts,
            )
            return True

        # --- Check cool-down for DATA_CONTRACT_VIOLATION ---
        if await self._is_cooled_down(job):
            log.warning(
                "job_skipped_cooldown",
                reason="repeated DATA_CONTRACT_VIOLATION",
            )
            await self._fail_job(
                job.id,
                error_code="COOL_DOWN_ACTIVE",
                error_message=(
                    f"Skipped: {self._cool_down_threshold} consecutive "
                    f"DATA_CONTRACT_VIOLATION failures within "
                    f"{self._cool_down_window}"
                ),
                retryable=False,
                attempt_count=job.attempt_count,
                max_attempts=job.max_attempts,
            )
            return True

        # --- Look up handler ---
        handler = get_handler(job.job_type)
        if handler is None:
            await self._fail_job(
                job.id,
                error_code="NO_HANDLER_REGISTERED",
                error_message=f"No handler registered for '{job.job_type}'",
                retryable=False,
                attempt_count=job.attempt_count,
                max_attempts=job.max_attempts,
            )
            return True

        # --- Execute ---
        try:
            result = await handler(payload, app_state=self._app_state)
            result_json = json.dumps(result) if result else None
            await self._succeed_job(job.id, result_json)
            log.info("job_succeeded")
        except Exception as exc:
            error_code = getattr(exc, "error_code", "UNHANDLED_ERROR")

            # Determine retryability:
            # 1. If exception has explicit retryable attribute, honor it
            # 2. Otherwise, check error_code against known non-retryable set
            exc_retryable = getattr(exc, "retryable", None)
            if exc_retryable is not None:
                retryable = exc_retryable
            else:
                retryable = error_code not in NON_RETRYABLE_CODES

            tb = traceback.format_exc()

            log.error(
                "job_failed",
                error_code=error_code,
                retryable=retryable,
                error=str(exc),
            )

            await self._fail_job(
                job.id,
                error_code=error_code,
                error_message=f"{exc}\n\n{tb}",
                retryable=retryable,
                attempt_count=job.attempt_count,
                max_attempts=job.max_attempts,
            )

        return True

    async def _succeed_job(
        self,
        job_id: int,
        result_json: str | None,
    ) -> None:
        """Mark job as successful in a fresh session."""
        async with self._session_factory() as session:
            repo = JobRepository(session)
            await repo.mark_success(job_id, result_json)

            from src.services.audit import AuditWriter
            from src.schemas.events import EventType
            audit = AuditWriter(session)
            await audit.log_event(
                event_type=EventType.JOB_SUCCEEDED,
                entity_type="job",
                entity_id=str(job_id),
                metadata={"result_size": len(result_json) if result_json else 0},
                actor="system",
            )

            await session.commit()

    async def _fail_job(
        self,
        job_id: int,
        *,
        error_code: str,
        error_message: str,
        retryable: bool,
        attempt_count: int,
        max_attempts: int,
    ) -> None:
        """Mark job as failed. Re-enqueue same job if retryable and budget remains."""
        async with self._session_factory() as session:
            repo = JobRepository(session)

            if retryable and attempt_count < max_attempts:
                # Re-queue the SAME job (not a new row).
                # attempt_count was already incremented by claim_next().
                await session.execute(
                    update(Job)
                    .where(Job.id == job_id)
                    .values(
                        status=JobStatus.QUEUED,
                        error_code=None,       # Clear — job is queued, not failed
                        error_message=None,     # Clear
                        started_at=None,
                        finished_at=None,
                    )
                )
                logger.info(
                    "job_retry_requeued",
                    job_id=job_id,
                    attempt=attempt_count,
                    max_attempts=max_attempts,
                )
            else:
                # Terminal failure — no more retries
                await repo.mark_failed(job_id, error_code, error_message)
                if retryable:
                    logger.warning(
                        "job_retry_budget_exhausted",
                        job_id=job_id,
                        attempt=attempt_count,
                        max_attempts=max_attempts,
                    )

            from src.services.audit import AuditWriter
            from src.schemas.events import EventType
            audit = AuditWriter(session)
            await audit.log_event(
                event_type=EventType.JOB_FAILED,
                entity_type="job",
                entity_id=str(job_id),
                metadata={
                    "error_code": error_code,
                    "retryable": retryable,
                    "attempt": attempt_count,
                },
                actor="system",
            )

            await session.commit()

    async def _is_cooled_down(self, job: Job) -> bool:
        """Check if this cube has too many recent DATA_CONTRACT_VIOLATION failures.

        Only applies to cube_fetch jobs. Looks at the last N jobs
        for the same product_id that failed with DATA_CONTRACT_VIOLATION
        within the cool-down window.
        """
        if job.job_type != "cube_fetch":
            return False

        try:
            payload_data = json.loads(job.payload_json)
            product_id = payload_data.get("product_id")
        except (json.JSONDecodeError, AttributeError):
            return False

        if not product_id:
            return False

        cutoff = datetime.now(timezone.utc) - self._cool_down_window

        # Use exact JSON key match instead of raw substring
        # Pattern: "product_id":"14-10-0127-01" (with quotes)
        # TODO: This text-based JSON match is fragile — depends on exact
        # serialization without spaces. When payload is stored as JSONB
        # (future), replace with proper JSON path query. For now, the
        # exact pattern f'"product_id":"{product_id}"' is sufficient
        # because Pydantic's model_dump_json() produces compact JSON.
        exact_pattern = f'"product_id":"{product_id}"'

        async with self._session_factory() as session:
            from sqlalchemy import select, func, and_

            from src.models.job import Job as JobModel

            count = await session.scalar(
                select(func.count(JobModel.id)).where(
                    and_(
                        JobModel.job_type == "cube_fetch",
                        JobModel.status == JobStatus.FAILED,
                        JobModel.error_code == "DATA_CONTRACT_VIOLATION",
                        JobModel.payload_json.contains(exact_pattern),
                        JobModel.finished_at >= cutoff,
                    )
                )
            )

        return (count or 0) >= self._cool_down_threshold
