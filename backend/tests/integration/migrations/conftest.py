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
    """Test database URL from env, skips test if not Postgres async.

    Migration tests use create_async_engine + Postgres-specific SQL
    (information_schema queries, FK ondelete=SET NULL semantics), so
    the URL must be ``postgresql+asyncpg://``.
    """
    url = os.environ.get("TEST_DATABASE_URL")
    if not url or not url.startswith("postgresql+asyncpg://"):
        pytest.skip(
            "TEST_DATABASE_URL must be set to a postgresql+asyncpg:// URL "
            "for migration integration tests"
        )
    return url


@pytest_asyncio.fixture
async def db_at_revision(test_db_url: str):
    """Yield a callable that brings the DB to a specific Alembic revision.

    Usage::

        async def test_x(db_at_revision):
            engine = await db_at_revision("b4f9a21c8d77")
            ...

    Contract — reset-then-upgrade on first call:
    On the first call within a test, the DB is downgraded to ``base``
    (tolerating empty/fresh state) and then upgraded forward to the
    requested revision. This handles dirty state from a prior failed
    run regardless of where the previous test left the DB.

    On subsequent calls within the same test, ``alembic upgrade``/
    ``downgrade`` runs directly without resetting — data inserted at
    an intermediate revision survives forward migrations, which is the
    whole point of multi-step migration tests.

    Teardown disposes any engines and downgrades to ``base`` so the
    next test starts clean.
    """
    engines: list[AsyncEngine] = []
    first_call = True

    async def _bring_to(revision: str) -> AsyncEngine:
        nonlocal first_call
        if first_call:
            try:
                _alembic("downgrade", "base", db_url=test_db_url)
            except RuntimeError as exc:
                msg = str(exc).lower()
                # Tolerate only legitimate fresh-DB / no-state cases
                if (
                    "can't locate revision" in msg
                    or "no such table" in msg
                    or ("alembic_version" in msg and "does not exist" in msg)
                ):
                    pass
                else:
                    raise
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
            msg = str(exc).lower()
            # Tolerate only legitimate fresh-DB / no-state cases
            if (
                "can't locate revision" in msg
                or "no such table" in msg
                or ("alembic_version" in msg and "does not exist" in msg)
            ):
                pass
            else:
                # Best-effort cleanup; surface but don't fail next test
                print(f"WARN: teardown downgrade failed: {exc}")
