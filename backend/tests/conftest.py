"""Root-level shared test fixtures.

Provides an isolated, in-memory async SQLite engine and session so that
**every** test module in the project can run against a fresh database
without touching disk or a real PostgreSQL instance.

Fixtures defined here are automatically discovered by pytest for all
tests under ``tests/``.
"""

from __future__ import annotations

import os

# Ensure required secrets have test-safe defaults so that Settings
# validation (DEBT-008) does not reject module-level get_settings()
# calls during test collection.
os.environ.setdefault("ADMIN_API_KEY", "test-key")

import subprocess
from collections.abc import AsyncGenerator
from typing import Any
from uuid import uuid4

import pytest
from slugify import slugify as _slugify_lib
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.core.database import Base
from src.models.publication import Publication, PublicationStatus
from src.services.publications.lineage import generate_lineage_key

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


# ---------------------------------------------------------------------------
# Test factory helpers
# ---------------------------------------------------------------------------


def _make_test_slug(headline: str) -> str:
    """Deterministic-ish test slug with uuid suffix for fixture isolation.

    Mirrors prod slugify but appends ``-<uuid8>`` to avoid collisions
    across multiple ``make_publication()`` calls in the same test
    session (the slug column will gain a UNIQUE constraint in
    Chunk 4.5).
    """
    base = _slugify_lib(headline or "test-publication", max_length=180)
    if not base:
        base = "test-publication"
    return f"{base}-{uuid4().hex[:8]}"


def make_publication(**overrides: Any) -> Publication:
    """Build a Publication ORM instance with sensible defaults for tests.

    Defaults a fresh ``lineage_key`` via :func:`generate_lineage_key`
    (UUID v7) so tests don't fail on the post-Phase-2.2.0 NOT NULL
    constraint. Accepts overrides for any field; pass
    ``lineage_key="..."`` to pin a specific value (e.g. for clone-
    inheritance tests).

    A unique ``slug`` is auto-generated from the final headline (after
    overrides) unless the caller passes ``slug=`` explicitly.

    Non-persisting: caller is responsible for ``session.add(pub)`` +
    commit if persistence is needed.
    """
    defaults: dict[str, Any] = {
        "headline": "test publication",
        "chart_type": "bar",
        "status": PublicationStatus.DRAFT,
        "lineage_key": generate_lineage_key(),
    }
    defaults.update(overrides)
    if "slug" not in defaults:
        defaults["slug"] = _make_test_slug(defaults["headline"])
    return Publication(**defaults)


@pytest.fixture(name="make_publication")
def _make_publication_fixture() -> Any:
    """Pytest-fixture wrapper that exposes :func:`make_publication` as the
    ``make_publication`` fixture, so test methods can request it via DI
    (``def test_x(self, make_publication): ...``) instead of importing.

    Registered under a different symbol (``_make_publication_fixture``)
    via ``name=`` so the module-level ``make_publication`` function
    remains importable for legacy tests that do
    ``from tests.conftest import make_publication``.
    """
    return make_publication
