"""Phase 3.1aaa: end-to-end migration + GENERATED column round-trip.

Requires ``TEST_DATABASE_URL`` pointed at a real PostgreSQL instance;
skips otherwise. Mirrors :mod:`test_metadata_cache_integration` for
the ``pg_session`` flow (Alembic upgrade head; teardown via downgrade
base).
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.models.semantic_mapping import SemanticMapping
from src.models.semantic_value_cache import SemanticValueCache
from src.repositories.semantic_value_cache_repository import (
    SemanticValueCacheRepository,
)
from src.services.statcan.value_cache_hash import compute_source_hash


_FIXED = datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc)


async def _seed_mapping(
    session_factory,
    *,
    cube_id: str = "18-10-0004-01",
    semantic_key: str = "cpi.canada.all_items",
) -> None:
    async with session_factory() as session:
        m = SemanticMapping(
            cube_id=cube_id,
            product_id=18100004,
            semantic_key=semantic_key,
            label="lbl",
            description=None,
            config={"dimension_filters": {}},
            is_active=True,
            version=1,
        )
        session.add(m)
        await session.commit()


@pytest.mark.asyncio
async def test_semantic_value_cache_table_created(pg_session):
    """Alembic upgrade head materialises the table + parser function."""
    result = await pg_session.execute(
        text(
            "SELECT to_regclass('public.semantic_value_cache') IS NOT NULL"
        )
    )
    assert result.scalar() is True
    fn = await pg_session.execute(
        text(
            "SELECT EXISTS (SELECT 1 FROM pg_proc "
            "WHERE proname = 'parse_ref_period_to_date')"
        )
    )
    assert fn.scalar() is True


@pytest.mark.asyncio
async def test_period_start_generated_monthly(pg_session):
    """ref_period='2026-04' → period_start = 2026-04-01 (PG GENERATED)."""
    factory = async_sessionmaker(
        bind=pg_session.bind, class_=AsyncSession, expire_on_commit=False
    )
    await _seed_mapping(factory)
    async with factory() as session:
        repo = SemanticValueCacheRepository(session)
        kw = dict(
            cube_id="18-10-0004-01",
            product_id=18100004,
            semantic_key="cpi.canada.all_items",
            coord="1.10.0.0.0.0.0.0.0.0",
            ref_period="2026-04",
            value=Decimal("1.0"),
            missing=False,
            decimals=1,
            scalar_factor_code=0,
            symbol_code=0,
            security_level_code=0,
            status_code=0,
            frequency_code=6,
            vector_id=42,
            response_status_code=0,
            fetched_at=_FIXED,
            release_time=None,
        )
        sh = compute_source_hash(
            product_id=kw["product_id"],
            cube_id=kw["cube_id"],
            semantic_key=kw["semantic_key"],
            coord=kw["coord"],
            ref_period=kw["ref_period"],
            value=kw["value"],
            missing=kw["missing"],
            decimals=kw["decimals"],
            scalar_factor_code=kw["scalar_factor_code"],
            symbol_code=kw["symbol_code"],
            security_level_code=kw["security_level_code"],
            status_code=kw["status_code"],
            frequency_code=kw["frequency_code"],
            vector_id=kw["vector_id"],
            response_status_code=kw["response_status_code"],
        )
        entity, _ = await repo.upsert_period(source_hash=sh, **kw)
        await session.commit()
        await session.refresh(entity)
        assert entity.period_start == date(2026, 4, 1)


@pytest.mark.asyncio
async def test_period_start_generated_quarterly(pg_session):
    result = await pg_session.execute(
        text("SELECT parse_ref_period_to_date('2026-Q3')")
    )
    assert result.scalar() == date(2026, 7, 1)


@pytest.mark.asyncio
async def test_period_start_generated_annual(pg_session):
    result = await pg_session.execute(
        text("SELECT parse_ref_period_to_date('2026')")
    )
    assert result.scalar() == date(2026, 1, 1)


@pytest.mark.asyncio
async def test_unsupported_ref_period_format_raises(pg_session):
    with pytest.raises(Exception, match="Unsupported ref_period"):
        await pg_session.execute(
            text("SELECT parse_ref_period_to_date('garbage')")
        )


@pytest.mark.asyncio
async def test_fk_cascade_on_mapping_delete(pg_session):
    """Deleting the mapping cascades to value-cache rows."""
    factory = async_sessionmaker(
        bind=pg_session.bind, class_=AsyncSession, expire_on_commit=False
    )
    await _seed_mapping(factory)
    async with factory() as session:
        repo = SemanticValueCacheRepository(session)
        kw = dict(
            cube_id="18-10-0004-01",
            product_id=18100004,
            semantic_key="cpi.canada.all_items",
            coord="1.10.0.0.0.0.0.0.0.0",
            ref_period="2026-04",
            value=Decimal("1.0"),
            missing=False,
            decimals=1,
            scalar_factor_code=0,
            symbol_code=0,
            security_level_code=0,
            status_code=0,
            frequency_code=6,
            vector_id=42,
            response_status_code=0,
            fetched_at=_FIXED,
            release_time=None,
        )
        await repo.upsert_period(source_hash="x" * 64, **kw)
        await session.commit()

        # Delete mapping → rows should cascade.
        await session.execute(
            text("DELETE FROM semantic_mappings WHERE cube_id = :c"),
            {"c": "18-10-0004-01"},
        )
        await session.commit()

        rows = await session.execute(
            text("SELECT COUNT(*) FROM semantic_value_cache")
        )
        assert rows.scalar() == 0
