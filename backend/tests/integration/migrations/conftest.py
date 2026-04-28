"""Migration test fixtures.

Pattern:
- Each test gets a fresh DB at a specific Alembic revision via
  ``db_at_revision``.
- Migrations applied via ``subprocess.run(['alembic', ...])``;
  programmatic Alembic API conflicts with pytest-asyncio event loop.
- Teardown via ``alembic downgrade base`` so PostgreSQL enum types
  drop cleanly (the SQLAlchemy metadata-level drop helpers leave
  enum types behind, breaking the next test's CREATE TYPE).

Required environment:
- ``TEST_DATABASE_URL`` set (e.g. ``postgresql+asyncpg://summa:devpassword@
  localhost:5432/summa_test``). Tests are skipped when missing or pointed
  at SQLite.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Callable

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

# This file lives at backend/tests/integration/migrations/conftest.py:
# parents[0]=migrations, [1]=integration, [2]=tests, [3]=backend
BACKEND_ROOT = Path(__file__).resolve().parents[3]
ALEMBIC_INI = BACKEND_ROOT / "alembic.ini"


def _alembic(*args: str, db_url: str) -> subprocess.CompletedProcess[str]:
    """Run alembic CLI as subprocess with the target DB URL."""
    env = {**os.environ, "DATABASE_URL": db_url}
    result = subprocess.run(
        ["alembic", "-c", str(ALEMBIC_INI), *args],
        cwd=BACKEND_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"alembic {' '.join(args)} failed:\n"
            f"STDOUT: {result.stdout}\n"
            f"STDERR: {result.stderr}"
        )
    return result


@pytest.fixture
def test_db_url() -> str:
    """Test database URL from env, skips test if missing/SQLite."""
    url = os.environ.get("TEST_DATABASE_URL")
    if not url or "sqlite" in url:
        pytest.skip(
            "TEST_DATABASE_URL not set to PostgreSQL — migration test skipped"
        )
    return url


@pytest_asyncio.fixture
async def db_at_revision(test_db_url: str):
    """Yield a callable that brings the DB to a specific Alembic revision.

    Usage::

        async def test_x(db_at_revision):
            engine = await db_at_revision("b4f9a21c8d77")
            ...

    On the first call: downgrades to ``base`` then upgrades to the
    requested revision (handles dirty state from a prior failed run).
    On subsequent calls within the same test: runs ``alembic upgrade``
    (or ``downgrade``) directly so data inserted at an intermediate
    revision survives forward migrations — alembic figures out which
    revisions to run between the current and target.

    Teardown disposes any engines and downgrades to ``base``.
    """
    engines: list[AsyncEngine] = []
    first_call = True

    async def _bring_to(revision: str) -> AsyncEngine:
        nonlocal first_call
        if first_call:
            try:
                _alembic("downgrade", "base", db_url=test_db_url)
            except RuntimeError:
                # Empty DB — nothing to downgrade; safe to ignore
                pass
            first_call = False
        _alembic("upgrade", revision, db_url=test_db_url)
        engine = create_async_engine(test_db_url, future=True)
        engines.append(engine)
        return engine

    try:
        yield _bring_to
    finally:
        for engine in engines:
            await engine.dispose()
        try:
            _alembic("downgrade", "base", db_url=test_db_url)
        except RuntimeError as exc:
            # Best-effort cleanup; surface but don't fail next test
            print(f"WARN: teardown downgrade failed: {exc}")
