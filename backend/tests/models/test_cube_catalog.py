"""Tests for CubeCatalog model.

Uses SQLite in-memory (R11). FTS features (search_vector, trigram)
are PostgreSQL-only and tested in integration tests or manually.
These tests verify the base model, CRUD, and constraints.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.cube_catalog import CubeCatalog


# ---- Fixtures ----

def _make_cube(**overrides) -> CubeCatalog:
    """Create a CubeCatalog instance with sensible defaults."""
    defaults = {
        "product_id": "14-10-0127-01",
        "cube_id_statcan": 14100127,
        "title_en": "Canada Mortgage and Housing Corporation, vacancy rates, apartment structures of six units and over, privately initiated in census metropolitan areas",
        "title_fr": None,
        "subject_code": "46",
        "subject_en": "Housing",
        "survey_en": "Canada Mortgage and Housing Corporation Survey",
        "frequency": "Monthly",
        "start_date": date(1990, 1, 1),
        "end_date": date(2024, 12, 1),
        "archive_status": False,
        "last_synced_at": datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    return CubeCatalog(**defaults)


# ---- CRUD cycle ----

async def test_create_and_read_cube(db_session: AsyncSession) -> None:
    """Create a CubeCatalog record and read it back."""
    cube = _make_cube()
    db_session.add(cube)
    await db_session.flush()
    await db_session.refresh(cube)

    assert cube.id is not None
    assert cube.product_id == "14-10-0127-01"
    assert cube.cube_id_statcan == 14100127
    assert cube.title_en.startswith("Canada Mortgage")
    assert cube.frequency == "Monthly"
    assert cube.archive_status is False
    assert cube.last_synced_at is not None


async def test_read_back_by_product_id(db_session: AsyncSession) -> None:
    """Query cube by product_id."""
    cube = _make_cube()
    db_session.add(cube)
    await db_session.flush()

    result = await db_session.execute(
        select(CubeCatalog).where(
            CubeCatalog.product_id == "14-10-0127-01"
        )
    )
    found = result.scalar_one()
    assert found.id == cube.id
    assert found.subject_en == "Housing"


# ---- Uniqueness constraint ----

async def test_product_id_unique_constraint(
    db_session: AsyncSession,
) -> None:
    """Duplicate product_id raises IntegrityError."""
    cube1 = _make_cube(product_id="14-10-0001-01")
    cube2 = _make_cube(product_id="14-10-0001-01", cube_id_statcan=99999)

    db_session.add(cube1)
    await db_session.flush()

    db_session.add(cube2)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_different_product_ids_allowed(
    db_session: AsyncSession,
) -> None:
    """Different product_ids create separate records."""
    cube1 = _make_cube(product_id="14-10-0001-01", cube_id_statcan=1)
    cube2 = _make_cube(product_id="14-10-0002-01", cube_id_statcan=2)

    db_session.add_all([cube1, cube2])
    await db_session.flush()

    result = await db_session.execute(select(CubeCatalog))
    all_cubes = result.scalars().all()
    assert len(all_cubes) == 2


# ---- Nullable fields ----

async def test_nullable_fields(db_session: AsyncSession) -> None:
    """Optional fields accept None."""
    cube = _make_cube(
        title_fr=None,
        survey_en=None,
        start_date=None,
        end_date=None,
        last_synced_at=None,
    )
    db_session.add(cube)
    await db_session.flush()
    await db_session.refresh(cube)

    assert cube.title_fr is None
    assert cube.survey_en is None
    assert cube.start_date is None
    assert cube.end_date is None
    assert cube.last_synced_at is None


# ---- Frequency values ----

@pytest.mark.parametrize(
    "freq",
    ["Daily", "Monthly", "Quarterly", "Annual"],
)
async def test_all_frequency_values(
    db_session: AsyncSession,
    freq: str,
) -> None:
    """All expected frequency values are accepted."""
    cube = _make_cube(
        product_id=f"99-99-{freq[:4]}-01",
        cube_id_statcan=hash(freq) % 100000,
        frequency=freq,
    )
    db_session.add(cube)
    await db_session.flush()
    assert cube.frequency == freq


# ---- Indexes exist ----

def test_indexes_defined() -> None:
    """Verify expected column-level indexes are defined on the model."""
    from src.models.cube_catalog import CubeCatalog

    # Check column properties directly
    assert CubeCatalog.product_id.property.columns[0].unique is True
    assert CubeCatalog.product_id.property.columns[0].index is True
    assert CubeCatalog.cube_id_statcan.property.columns[0].index is True
    assert CubeCatalog.subject_code.property.columns[0].index is True


# ---- Repr ----

async def test_repr(db_session: AsyncSession) -> None:
    """__repr__ returns readable string."""
    cube = _make_cube()
    db_session.add(cube)
    await db_session.flush()
    r = repr(cube)
    assert "CubeCatalog" in r
    assert "14-10-0127-01" in r


# ---- Bulk insert ----

async def test_bulk_insert(db_session: AsyncSession) -> None:
    """Multiple cubes can be inserted in one flush."""
    cubes = [
        _make_cube(
            product_id=f"10-10-{i:04d}-01",
            cube_id_statcan=10100000 + i,
            title_en=f"Test Cube {i}",
        )
        for i in range(20)
    ]
    db_session.add_all(cubes)
    await db_session.flush()

    count_result = await db_session.execute(select(CubeCatalog))
    assert len(count_result.scalars().all()) == 20
