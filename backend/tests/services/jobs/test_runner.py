"""Tests for JobRunner — execution, retry, dedupe, shutdown, cool-down."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.job import Job, JobStatus
from src.repositories.job_repository import JobRepository
from src.schemas.job_payloads import CatalogSyncPayload, CubeFetchPayload
from src.services.jobs.runner import JobRunner
from src.services.jobs.handlers import register_handler, HANDLER_REGISTRY
from src.services.jobs.dedupe import catalog_sync_key, cube_fetch_key


@pytest.fixture(autouse=True)
def _clean_handler_registry():
    """Clear handler registry between tests."""
    saved = dict(HANDLER_REGISTRY)
    HANDLER_REGISTRY.clear()
    yield
    HANDLER_REGISTRY.clear()
    HANDLER_REGISTRY.update(saved)


@pytest.fixture
def app_state():
    """Fake app.state with shutdown flag and semaphores."""
    state = SimpleNamespace()
    state.shutting_down = False
    state.data_sem = asyncio.Semaphore(2)
    state.render_sem = asyncio.Semaphore(2)
    state.io_sem = asyncio.Semaphore(10)
    return state


# ---- Successful execution ----

async def test_runner_executes_job_successfully(
    db_session: AsyncSession,
    app_state: SimpleNamespace,
) -> None:
    """Runner claims job, calls handler, marks success."""
    result_data = {"synced": 100}

    async def mock_handler(payload, *, app_state):
        return result_data

    register_handler("catalog_sync", mock_handler)

    repo = JobRepository(db_session)
    await repo.enqueue(
        "catalog_sync",
        CatalogSyncPayload().model_dump_json(),
    )
    await db_session.commit()

    # Need a session factory that returns our test session
    # For unit tests, we create a simple wrapper
    runner = JobRunner(
        _make_test_session_factory(db_session),
        app_state,
    )

    executed = await runner.execute_once()
    assert executed is True

    jobs = await repo.list_jobs(status=JobStatus.SUCCESS)
    assert len(jobs) == 1
    assert json.loads(jobs[0].result_json) == result_data


# ---- Retryable failure ----

async def test_runner_retries_on_retryable_error(
    db_session: AsyncSession,
    app_state: SimpleNamespace,
) -> None:
    """Retryable error marks job failed and creates retry job."""
    async def failing_handler(payload, *, app_state):
        raise RuntimeError("Transient network error")

    register_handler("catalog_sync", failing_handler)

    repo = JobRepository(db_session)
    await repo.enqueue(
        "catalog_sync",
        CatalogSyncPayload().model_dump_json(),
    )
    await db_session.commit()

    runner = JobRunner(
        _make_test_session_factory(db_session),
        app_state,
    )
    await runner.execute_once()

    # Original job failed
    failed = await repo.list_jobs(status=JobStatus.FAILED)
    assert len(failed) == 1

    # Retry job created
    queued = await repo.list_jobs(status=JobStatus.QUEUED)
    assert len(queued) == 1
    assert queued[0].created_by.startswith("retry:job:")


# ---- Non-retryable failure ----

async def test_runner_does_not_retry_non_retryable_error(
    db_session: AsyncSession,
    app_state: SimpleNamespace,
) -> None:
    """DATA_CONTRACT_VIOLATION does NOT create a retry job."""
    from src.core.exceptions import DataSourceError

    async def contract_handler(payload, *, app_state):
        exc = DataSourceError(
            message="Missing SCALAR_ID",
            error_code="DATA_CONTRACT_VIOLATION",
        )
        raise exc

    register_handler("cube_fetch", contract_handler)

    repo = JobRepository(db_session)
    await repo.enqueue(
        "cube_fetch",
        CubeFetchPayload(product_id="14-10-0127").model_dump_json(),
    )
    await db_session.commit()

    runner = JobRunner(
        _make_test_session_factory(db_session),
        app_state,
    )
    await runner.execute_once()

    failed = await repo.list_jobs(status=JobStatus.FAILED)
    assert len(failed) == 1

    # No retry job created
    queued = await repo.list_jobs(status=JobStatus.QUEUED)
    assert len(queued) == 0


# ---- Unknown job type ----

async def test_runner_fails_unknown_job_type(
    db_session: AsyncSession,
    app_state: SimpleNamespace,
) -> None:
    """Job with no registered handler fails permanently."""
    repo = JobRepository(db_session)
    job = Job(
        job_type="nonexistent",
        payload_json='{"schema_version": 1}',
    )
    db_session.add(job)
    await db_session.flush()
    await db_session.commit()

    runner = JobRunner(
        _make_test_session_factory(db_session),
        app_state,
    )
    await runner.execute_once()

    failed = await repo.list_jobs(status=JobStatus.FAILED)
    assert len(failed) == 1
    assert failed[0].error_code in ("UNKNOWN_JOB_TYPE", "NO_HANDLER_REGISTERED")


# ---- Shutdown awareness ----

async def test_runner_stops_on_shutdown_flag(
    db_session: AsyncSession,
    app_state: SimpleNamespace,
) -> None:
    """Runner loop exits when shutting_down is True."""
    app_state.shutting_down = True

    runner = JobRunner(
        _make_test_session_factory(db_session),
        app_state,
    )

    # run_loop should exit almost immediately
    task = asyncio.create_task(runner.run_loop(poll_interval=0.1))
    await asyncio.wait_for(task, timeout=2.0)
    # If we get here without timeout, shutdown worked


# ---- Cool-down ----

async def test_runner_skips_cooled_down_cube(
    db_session: AsyncSession,
    app_state: SimpleNamespace,
) -> None:
    """After 3 DATA_CONTRACT_VIOLATION failures, cube is skipped."""
    repo = JobRepository(db_session)
    product_id = "14-10-0127"
    payload = CubeFetchPayload(product_id=product_id)

    # Create 3 failed jobs with DATA_CONTRACT_VIOLATION
    for i in range(3):
        j = Job(
            job_type="cube_fetch",
            payload_json=payload.model_dump_json(),
            status=JobStatus.FAILED,
            error_code="DATA_CONTRACT_VIOLATION",
            finished_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        db_session.add(j)
    await db_session.flush()

    # Now enqueue a new fetch for the same cube
    await repo.enqueue(
        "cube_fetch",
        payload.model_dump_json(),
    )
    await db_session.commit()

    # Register a handler that should NOT be called
    handler_called = False

    async def should_not_run(payload, *, app_state):
        nonlocal handler_called
        handler_called = True
        return {}

    register_handler("cube_fetch", should_not_run)

    runner = JobRunner(
        _make_test_session_factory(db_session),
        app_state,
        cool_down_threshold=3,
        cool_down_window_hours=24,
    )
    await runner.execute_once()

    assert handler_called is False

    # Job should be marked as failed with COOL_DOWN_ACTIVE
    failed = await repo.list_jobs(
        job_type="cube_fetch", status=JobStatus.FAILED
    )
    cool_down_jobs = [j for j in failed if j.error_code == "COOL_DOWN_ACTIVE"]
    assert len(cool_down_jobs) >= 1


# ---- Dedupe key helpers ----

def test_catalog_sync_dedupe_key() -> None:
    """catalog_sync_key generates correct format."""
    from datetime import date

    key = catalog_sync_key(date(2025, 4, 4))
    assert key == "catalog_sync:2025-04-04"


def test_cube_fetch_dedupe_key() -> None:
    """cube_fetch_key generates correct format."""
    from datetime import date

    key = cube_fetch_key("14-10-0127", date(2025, 4, 4))
    assert key == "fetch:14-10-0127:2025-04-04"


# ---- Test utility ----

def _make_test_session_factory(session: AsyncSession):
    """Create a fake session factory that always returns the test session.

    This is needed because JobRunner opens its own sessions. In tests,
    we want all operations on the same in-memory SQLite session.

    NOTE: This is a simplification for unit tests. The real
    async_session_factory creates separate sessions per context.
    """
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def factory():
        yield session

    return factory
