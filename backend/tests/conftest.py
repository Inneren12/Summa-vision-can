"""Root-level shared test fixtures.

Provides an isolated, in-memory async SQLite engine and session so that
**every** test module in the project can run against a fresh database
without touching disk or a real PostgreSQL instance.

Fixtures defined here are automatically discovered by pytest for all
tests under ``tests/``.
"""

from __future__ import annotations

import os
import subprocess
from collections.abc import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.core.database import Base

# ---------------------------------------------------------------------------
# In-memory async engine for tests
# ---------------------------------------------------------------------------

TEST_DATABASE_URL: str = "sqlite+aiosqlite:///:memory:"


@pytest.fixture()
async def async_engine() -> AsyncGenerator[AsyncEngine, None]:
    """Create an in-memory SQLite async engine and bootstrap the schema.

    The full ORM schema is created before the test and torn down after,
    guaranteeing each test gets a completely clean slate.
    """
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture()
async def db_session(
    async_engine: AsyncEngine,
) -> AsyncGenerator[AsyncSession, None]:
    """Yield an ``AsyncSession`` bound to the in-memory test engine.

    The session uses ``expire_on_commit=False`` so that attributes
    remain accessible after a flush/commit without triggering lazy loads.
    """
    session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_factory() as session:
        yield session


@pytest.fixture
async def pg_session():
    """PostgreSQL session with schema applied via Alembic migrations.

    This ensures we test against the REAL production schema,
    including partial indexes, generated columns, and FTS indexes
    that are defined in migration SQL, not in SQLAlchemy metadata.
    """
    pg_url = os.environ.get("TEST_DATABASE_URL")
    if not pg_url or "sqlite" in pg_url:
        pytest.skip(
            "TEST_DATABASE_URL not set to PostgreSQL — skipping PG integration test"
        )

    # Run Alembic in a subprocess to avoid event loop conflict
    # IMPORTANT: migrations/env.py uses async_engine_from_config(...),
    # so Alembic must receive the async URL, not a sync psycopg2 URL.
    env = {**os.environ, "DATABASE_URL": pg_url}
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

    engine = create_async_engine(pg_url, echo=False)
    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        yield session

    await engine.dispose()

    # Cleanup via Alembic, not Base.metadata.drop_all().
    # Otherwise alembic_version remains in the DB, and the next
    # "alembic upgrade head" becomes a no-op against a partially dropped schema.
    result = subprocess.run(
        ["alembic", "downgrade", "base"],
        cwd=os.path.join(os.path.dirname(__file__), "..", ".."),
        capture_output=True,
        text=True,
        env=env,
    )
    if result.returncode != 0:
        pytest.fail(
            f"alembic downgrade base failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
