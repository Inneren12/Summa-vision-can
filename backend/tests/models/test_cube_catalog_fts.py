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
