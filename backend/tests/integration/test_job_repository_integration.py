"""Integration tests for JobRepository — requires PostgreSQL.

Tests SKIP LOCKED semantics that cannot be verified on SQLite.
Run with: pytest -m integration

Requires TEST_DATABASE_URL env var pointing to a PostgreSQL database.
"""

from __future__ import annotations

import asyncio
import os
import subprocess

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# Skip entire file if no PostgreSQL available
pytestmark = pytest.mark.integration

PG_URL = os.environ.get("TEST_DATABASE_URL", "")


@pytest.fixture
async def pg_engine():
    """Create a PostgreSQL engine for integration tests."""
    if not PG_URL:
        pytest.skip("TEST_DATABASE_URL not set")

    env = {**os.environ, "DATABASE_URL": PG_URL}

    # Setup: apply migrations
    result = subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=os.path.join(os.path.dirname(__file__), "..", ".."),
        capture_output=True,
        text=True,
        env=env,
    )
    if result.returncode != 0:
        pytest.fail(
            f"alembic upgrade head failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )

    engine = create_async_engine(PG_URL, echo=False)

    yield engine

    # Teardown: dispose engine FIRST, then downgrade
    await engine.dispose()

    result = subprocess.run(
        ["alembic", "downgrade", "base"],
        cwd=os.path.join(os.path.dirname(__file__), "..", ".."),
        capture_output=True,
        text=True,
        env=env,
    )
    if result.returncode != 0:
        # Don't fail on teardown, just warn
        import warnings

        warnings.warn(f"alembic downgrade base failed:\n{result.stderr}")


@pytest.fixture
async def pg_session_factory(pg_engine):
    """Session factory for integration tests."""
    return async_sessionmaker(
        pg_engine, class_=AsyncSession, expire_on_commit=False
    )


async def test_skip_locked_prevents_double_claim(
    pg_session_factory,
) -> None:
    """Two concurrent claim_next() calls return DIFFERENT jobs.

    This proves FOR UPDATE SKIP LOCKED works — the second session
    skips the locked row and claims the next available job.
    """
    from src.repositories.job_repository import JobRepository
    from src.schemas.job_payloads import CatalogSyncPayload
    from src.models.job import JobStatus

    payload = CatalogSyncPayload().model_dump_json()

    # Enqueue 2 jobs
    async with pg_session_factory() as session:
        repo = JobRepository(session)
        result1 = await repo.enqueue("test_type", payload, dedupe_key="skip1")
        result2 = await repo.enqueue("test_type", payload, dedupe_key="skip2")
        await session.commit()
        job1_id = result1.job.id
        job2_id = result2.job.id

    # Claim from two concurrent sessions
    claimed_ids: list[int] = []

    async def claim_one():
        async with pg_session_factory() as session:
            repo = JobRepository(session)
            job = await repo.claim_next()
            if job:
                claimed_ids.append(job.id)
            await session.commit()

    await asyncio.gather(claim_one(), claim_one())

    # Both should have claimed, but DIFFERENT jobs
    assert len(claimed_ids) == 2
    assert claimed_ids[0] != claimed_ids[1]
    assert set(claimed_ids) == {job1_id, job2_id}


async def test_dedupe_race_condition_safe(
    pg_session_factory,
) -> None:
    """Concurrent enqueue with same dedupe_key returns same job.

    Partial unique index ix_jobs_dedupe_active prevents duplicates.
    """
    from src.repositories.job_repository import JobRepository
    from src.schemas.job_payloads import CatalogSyncPayload

    payload = CatalogSyncPayload().model_dump_json()
    results: list[tuple[int, bool]] = []

    async def enqueue_one():
        async with pg_session_factory() as session:
            repo = JobRepository(session)
            result = await repo.enqueue(
                "test_type", payload, dedupe_key="race_test"
            )
            results.append((result.job.id, result.created))
            await session.commit()

    await asyncio.gather(enqueue_one(), enqueue_one())

    # Both should return the same job_id (one created, one deduped)
    assert len(results) == 2
    assert results[0][0] == results[1][0]

    # Exactly one should have created=True
    created_flags = [r[1] for r in results]
    assert created_flags.count(True) == 1
    assert created_flags.count(False) == 1
