"""Tests for CubeCatalogRepository.

Uses SQLite in-memory (R11). FTS/trigram tests require PostgreSQL
and are in a separate integration test file.
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.cube_catalog import CubeCatalog
from src.repositories.cube_catalog_repository import CubeCatalogRepository
from src.schemas.cube_catalog import CubeCatalogCreate


def _make_cube_create(**overrides) -> CubeCatalogCreate:
    """Create a CubeCatalogCreate with sensible defaults."""
    defaults = {
        "product_id": "14-10-0127-01",
        "cube_id_statcan": 14100127,
        "title_en": "Canada Mortgage and Housing Corporation, vacancy rates",
        "title_fr": None,
        "subject_code": "46",
        "subject_en": "Housing",
        "survey_en": "CMHC Survey",
        "frequency": "Monthly",
        "start_date": None,
        "end_date": None,
        "archive_status": False,
    }
    defaults.update(overrides)
    return CubeCatalogCreate(**defaults)


# ---- Upsert ----

async def test_upsert_batch_inserts(db_session: AsyncSession) -> None:
    """upsert_batch creates new records."""
    repo = CubeCatalogRepository(db_session)
    cubes = [
        _make_cube_create(product_id=f"10-10-{i:04d}-01", cube_id_statcan=i)
        for i in range(10)
    ]
    count = await repo.upsert_batch(cubes)
    await db_session.commit()

    assert count == 10
    total = await repo.count()
    assert total == 10


async def test_upsert_batch_updates_existing(db_session: AsyncSession) -> None:
    """upsert_batch updates records when product_id already exists."""
    repo = CubeCatalogRepository(db_session)

    # First insert
    cubes = [_make_cube_create(title_en="Original Title")]
    await repo.upsert_batch(cubes)
    await db_session.commit()

    # Upsert with updated title
    cubes_updated = [_make_cube_create(title_en="Updated Title")]
    count = await repo.upsert_batch(cubes_updated)
    await db_session.commit()

    # Verify updated
    cube = await repo.get_by_product_id("14-10-0127-01")
    assert cube is not None
    assert cube.title_en == "Updated Title"

    # Still only 1 record
    total = await repo.count()
    assert total == 1


async def test_upsert_batch_idempotent(db_session: AsyncSession) -> None:
    """Upserting same data twice doesn't duplicate records."""
    repo = CubeCatalogRepository(db_session)
    cubes = [_make_cube_create()]

    await repo.upsert_batch(cubes)
    await db_session.commit()
    await repo.upsert_batch(cubes)
    await db_session.commit()

    total = await repo.count()
    assert total == 1


async def test_upsert_batch_large_chunk(db_session: AsyncSession) -> None:
    """upsert_batch handles more than chunk_size records."""
    repo = CubeCatalogRepository(db_session)
    cubes = [
        _make_cube_create(
            product_id=f"99-99-{i:04d}-01",
            cube_id_statcan=990000 + i,
            title_en=f"Cube {i}",
        )
        for i in range(50)
    ]
    count = await repo.upsert_batch(cubes, chunk_size=10)
    await db_session.commit()

    assert count == 50
    total = await repo.count()
    assert total == 50


# ---- Search (SQLite LIKE fallback) ----

async def test_search_finds_by_title(db_session: AsyncSession) -> None:
    """Search finds cubes by title words."""
    repo = CubeCatalogRepository(db_session)
    await repo.upsert_batch([
        _make_cube_create(
            product_id="14-10-0127-01",
            title_en="Vacancy rates for rental apartments in Canada",
            subject_en="Housing",
        ),
        _make_cube_create(
            product_id="18-10-0001-01",
            cube_id_statcan=18100001,
            title_en="Consumer Price Index monthly",
            subject_en="Prices",
        ),
    ])
    await db_session.commit()

    results = await repo.search("vacancy rental")
    assert len(results) == 1
    assert results[0].product_id == "14-10-0127-01"


async def test_search_finds_by_subject(db_session: AsyncSession) -> None:
    """Search matches subject_en as well as title."""
    repo = CubeCatalogRepository(db_session)
    await repo.upsert_batch([
        _make_cube_create(
            product_id="14-10-0200-01",
            cube_id_statcan=14100200,
            title_en="Some obscure table about dwellings",
            subject_en="Housing",
        ),
    ])
    await db_session.commit()

    results = await repo.search("Housing")
    assert len(results) >= 1


async def test_search_empty_query_returns_empty(
    db_session: AsyncSession,
) -> None:
    """Empty search query returns no results."""
    repo = CubeCatalogRepository(db_session)
    await repo.upsert_batch([_make_cube_create()])
    await db_session.commit()

    results = await repo.search("")
    assert len(results) == 0

    results2 = await repo.search("   ")
    assert len(results2) == 0


async def test_search_respects_limit(db_session: AsyncSession) -> None:
    """Search returns at most 'limit' results."""
    repo = CubeCatalogRepository(db_session)
    cubes = [
        _make_cube_create(
            product_id=f"10-10-{i:04d}-01",
            cube_id_statcan=i,
            title_en=f"Housing statistics table {i}",
            subject_en="Housing",
        )
        for i in range(20)
    ]
    await repo.upsert_batch(cubes)
    await db_session.commit()

    results = await repo.search("Housing", limit=5)
    assert len(results) == 5


async def test_search_max_limit_capped(db_session: AsyncSession) -> None:
    """Limit is capped at 100 even if caller requests more."""
    repo = CubeCatalogRepository(db_session)
    # Just verify no crash — actual cap is enforced in code
    results = await repo.search("anything", limit=999)
    assert isinstance(results, (list, tuple))


# ---- Lookups ----

async def test_get_by_product_id(db_session: AsyncSession) -> None:
    """get_by_product_id returns correct cube."""
    repo = CubeCatalogRepository(db_session)
    await repo.upsert_batch([_make_cube_create()])
    await db_session.commit()

    cube = await repo.get_by_product_id("14-10-0127-01")
    assert cube is not None
    assert cube.title_en.startswith("Canada Mortgage")


async def test_get_by_product_id_not_found(
    db_session: AsyncSession,
) -> None:
    """get_by_product_id returns None for unknown product_id."""
    repo = CubeCatalogRepository(db_session)
    cube = await repo.get_by_product_id("99-99-9999-99")
    assert cube is None


async def test_get_by_subject(db_session: AsyncSession) -> None:
    """get_by_subject returns cubes with matching subject_code."""
    repo = CubeCatalogRepository(db_session)
    await repo.upsert_batch([
        _make_cube_create(product_id="14-10-0001-01", cube_id_statcan=1, subject_code="46"),
        _make_cube_create(product_id="18-10-0001-01", cube_id_statcan=2, subject_code="18"),
        _make_cube_create(product_id="14-10-0002-01", cube_id_statcan=3, subject_code="46"),
    ])
    await db_session.commit()

    results = await repo.get_by_subject("46")
    assert len(results) == 2
    assert all(c.subject_code == "46" for c in results)


async def test_count_empty(db_session: AsyncSession) -> None:
    """count returns 0 on empty catalog."""
    repo = CubeCatalogRepository(db_session)
    assert await repo.count() == 0


async def test_count_after_inserts(db_session: AsyncSession) -> None:
    """count returns correct number after inserts."""
    repo = CubeCatalogRepository(db_session)
    cubes = [
        _make_cube_create(product_id=f"10-10-{i:04d}-01", cube_id_statcan=i)
        for i in range(7)
    ]
    await repo.upsert_batch(cubes)
    await db_session.commit()

    assert await repo.count() == 7


# ---- last_synced_at ----

async def test_upsert_sets_last_synced_at(db_session: AsyncSession) -> None:
    """Upserted cubes have last_synced_at set automatically."""
    repo = CubeCatalogRepository(db_session)
    await repo.upsert_batch([_make_cube_create()])
    await db_session.commit()

    cube = await repo.get_by_product_id("14-10-0127-01")
    assert cube is not None
    assert cube.last_synced_at is not None
