import os
import subprocess

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.core.database import Base

@pytest.fixture
async def pg_session():
    """PostgreSQL session with schema applied via Alembic migrations.

    This ensures we test against the REAL production schema,
    including partial indexes, generated columns, and FTS indexes
    that are defined in migration SQL, not in SQLAlchemy metadata.
    """
    pg_url = os.environ.get("TEST_DATABASE_URL")
    if not pg_url or "sqlite" in pg_url:
        pytest.skip("TEST_DATABASE_URL not set to PostgreSQL — skipping PG integration test")

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

    # Cleanup: drop all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
