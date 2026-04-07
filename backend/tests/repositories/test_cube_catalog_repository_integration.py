"""Integration tests for CubeCatalogRepository search on PostgreSQL.

Proves bilingual FTS and typo tolerance work through the repository
API, not just at the raw SQL/index level.

Requires PostgreSQL — skipped on SQLite.
Run with: pytest -m integration
"""

from __future__ import annotations

import os

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.integration


# ---- Helper ----

def _cube(pid: str, title_en: str, title_fr: str | None = None,
          subject: str = "Housing", subject_code: str = "46") -> dict:
    """Create a CubeCatalogCreate-compatible dict."""
    from src.schemas.cube_catalog import CubeCatalogCreate
    return CubeCatalogCreate(
        product_id=pid,
        cube_id_statcan=int(pid.replace("-", "")[:8]),
        title_en=title_en,
        title_fr=title_fr,
        subject_code=subject_code,
        subject_en=subject,
        frequency="Monthly",
    )


# ---- Tests ----

async def test_search_english_fts(pg_session: AsyncSession) -> None:
    """English full-text search finds cubes by title."""
    from src.repositories.cube_catalog_repository import CubeCatalogRepository

    repo = CubeCatalogRepository(pg_session)
    await repo.upsert_batch([
        _cube("14-10-0001-01",
              "Vacancy rates for rental apartments in Canada"),
        _cube("18-10-0001-01",
              "Consumer Price Index monthly"),
    ])
    await pg_session.commit()

    results = await repo.search("vacancy rental")
    assert len(results) >= 1
    assert results[0].product_id == "14-10-0001-01"


async def test_search_french_fts(pg_session: AsyncSession) -> None:
    """French full-text search finds cubes by title_fr."""
    from src.repositories.cube_catalog_repository import CubeCatalogRepository

    repo = CubeCatalogRepository(pg_session)
    await repo.upsert_batch([
        _cube("14-10-0002-01",
              "Vacancy rates for rental apartments",
              title_fr="Taux d'inoccupation des appartements locatifs"),
        _cube("18-10-0002-01",
              "Consumer Price Index",
              title_fr="Indice des prix à la consommation"),
    ])
    await pg_session.commit()

    results = await repo.search("appartements locatifs")
    assert len(results) >= 1
    assert results[0].product_id == "14-10-0002-01"


async def test_search_typo_tolerance(pg_session: AsyncSession) -> None:
    """Typo 'renal vacncy' still finds 'rental vacancy' via trigram.

    This is the key acceptance criterion for A-2.
    """
    from src.repositories.cube_catalog_repository import CubeCatalogRepository

    repo = CubeCatalogRepository(pg_session)
    await repo.upsert_batch([
        _cube("14-10-0003-01",
              "Vacancy rates for rental apartments in Canada"),
        _cube("18-10-0003-01",
              "Consumer Price Index monthly"),
        _cube("36-10-0003-01",
              "International trade statistics"),
    ])
    await pg_session.commit()

    results = await repo.search("renal vacncy")
    assert len(results) >= 1
    # The vacancy cube should be in results (trigram similarity)
    pids = [r.product_id for r in results]
    assert "14-10-0003-01" in pids, (
        f"Expected vacancy cube in typo search results, got: {pids}"
    )


async def test_search_returns_empty_for_nonsense(
    pg_session: AsyncSession,
) -> None:
    """Completely unrelated query returns empty list."""
    from src.repositories.cube_catalog_repository import CubeCatalogRepository

    repo = CubeCatalogRepository(pg_session)
    await repo.upsert_batch([
        _cube("14-10-0004-01", "Housing starts in Canada"),
    ])
    await pg_session.commit()

    results = await repo.search("xyznonexistent")
    assert len(results) == 0


async def test_upsert_batch_returns_deterministic_count(
    pg_session: AsyncSession,
) -> None:
    """upsert_batch returns number of input records, not driver rowcount."""
    from src.repositories.cube_catalog_repository import CubeCatalogRepository

    repo = CubeCatalogRepository(pg_session)
    cubes = [
        _cube(f"99-10-{i:04d}-01", f"Test cube {i}")
        for i in range(10)
    ]

    # First insert
    count1 = await repo.upsert_batch(cubes)
    await pg_session.commit()
    assert count1 == 10

    # Second upsert (same data — update path)
    count2 = await repo.upsert_batch(cubes)
    await pg_session.commit()
    assert count2 == 10  # Same count regardless of insert vs update
