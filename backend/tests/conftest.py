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
