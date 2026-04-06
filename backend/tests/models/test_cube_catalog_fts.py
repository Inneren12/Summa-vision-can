"""Integration tests for CubeCatalog full-text search features.

Requires PostgreSQL — skipped on SQLite.
Run with: pytest -m integration
"""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.cube_catalog import CubeCatalog


pytestmark = pytest.mark.integration


async def test_search_vector_populated(pg_session: AsyncSession) -> None:
    """search_vector column is auto-populated on PostgreSQL."""
    cube = CubeCatalog(
        product_id="14-10-0127-01",
        cube_id_statcan=14100127,
        title_en="Vacancy rates for rental apartments in Canada",
        subject_code="46",
        subject_en="Housing",
        frequency="Monthly",
    )
    pg_session.add(cube)
    await pg_session.flush()

    result = await pg_session.execute(
        text(
            "SELECT search_vector IS NOT NULL FROM cube_catalog "
            "WHERE product_id = '14-10-0127-01'"
        )
    )
    has_vector = result.scalar()
    assert has_vector is True


async def test_fts_query_finds_cube(pg_session: AsyncSession) -> None:
    """Full-text search query returns matching cubes."""
    cube = CubeCatalog(
        product_id="14-10-0127-01",
        cube_id_statcan=14100127,
        title_en="Vacancy rates for rental apartments in Canada",
        subject_code="46",
        subject_en="Housing",
        frequency="Monthly",
    )
    pg_session.add(cube)
    await pg_session.flush()

    result = await pg_session.execute(
        text(
            "SELECT product_id FROM cube_catalog "
            "WHERE search_vector @@ websearch_to_tsquery('english', 'rental vacancy') "
        )
    )
    rows = result.fetchall()
    assert len(rows) == 1
    assert rows[0][0] == "14-10-0127-01"


async def test_trigram_finds_typo(pg_session: AsyncSession) -> None:
    """Trigram similarity finds cubes despite typos."""
    cube = CubeCatalog(
        product_id="14-10-0127-01",
        cube_id_statcan=14100127,
        title_en="Vacancy rates for rental apartments in Canada",
        subject_code="46",
        subject_en="Housing",
        frequency="Monthly",
    )
    pg_session.add(cube)
    await pg_session.flush()

    # "vacncy rentel" — typo for "vacancy rental"
    result = await pg_session.execute(
        text(
            "SELECT product_id, similarity(title_en, 'vacncy rentel') as sim "
            "FROM cube_catalog "
            "WHERE similarity(title_en, 'vacncy rentel') > 0.1 "
            "ORDER BY sim DESC"
        )
    )
    rows = result.fetchall()
    assert len(rows) >= 1
    assert rows[0][0] == "14-10-0127-01"


async def test_fts_finds_french_title(pg_session: AsyncSession) -> None:
    """Full-text search finds cubes by French title."""
    cube = CubeCatalog(
        product_id="14-10-0200-01",
        cube_id_statcan=14100200,
        title_en="Vacancy rates for rental apartments",
        title_fr="Taux d'inoccupation des appartements locatifs",
        subject_code="46",
        subject_en="Housing",
        frequency="Monthly",
    )
    pg_session.add(cube)
    await pg_session.flush()

    # Search in French
    result = await pg_session.execute(
        text(
            "SELECT product_id FROM cube_catalog "
            "WHERE search_vector @@ to_tsquery('french', 'locatifs') "
        )
    )
    rows = result.fetchall()
    assert len(rows) >= 1, "French FTS should find cube by title_fr"
    assert rows[0][0] == "14-10-0200-01"


async def test_fts_finds_mixed_language_query(pg_session: AsyncSession) -> None:
    """FTS handles queries that match across EN and FR titles."""
    cube = CubeCatalog(
        product_id="14-10-0300-01",
        cube_id_statcan=14100300,
        title_en="Consumer Price Index",
        title_fr="Indice des prix à la consommation",
        subject_code="18",
        subject_en="Prices",
        frequency="Monthly",
    )
    pg_session.add(cube)
    await pg_session.flush()

    # Search by English term
    result_en = await pg_session.execute(
        text(
            "SELECT product_id FROM cube_catalog "
            "WHERE search_vector @@ websearch_to_tsquery('english', 'consumer price') "
        )
    )
    assert len(result_en.fetchall()) >= 1, "EN search should work"

    # Search by French term
    result_fr = await pg_session.execute(
        text(
            "SELECT product_id FROM cube_catalog "
            "WHERE search_vector @@ to_tsquery('french', 'consommation') "
        )
    )
    assert len(result_fr.fetchall()) >= 1, "FR search should work"


async def test_fts_indexes_exist_after_migration(pg_session: AsyncSession) -> None:
    """Verify FTS and trigram indexes exist on the real Alembic schema."""
    result = await pg_session.execute(
        text(
            "SELECT indexname FROM pg_indexes "
            "WHERE tablename = 'cube_catalog' "
            "ORDER BY indexname"
        )
    )
    index_names = [row[0] for row in result.fetchall()]

    assert "ix_cube_catalog_search_vector" in index_names, \
        f"GIN search_vector index missing. Found: {index_names}"
    assert "ix_cube_catalog_title_en_trgm" in index_names, \
        f"EN trigram index missing. Found: {index_names}"
    assert "ix_cube_catalog_title_fr_trgm" in index_names, \
        f"FR trigram index missing. Found: {index_names}"
