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
async def test_unsupported_ref_period_format_returns_null(pg_session):
    """FIX-R1 Blocker 3: parser tolerates unknown formats by returning NULL."""
    result = await pg_session.execute(
        text("SELECT parse_ref_period_to_date('garbage')")
    )
    assert result.scalar() is None


@pytest.mark.asyncio
async def test_unknown_ref_period_format_inserts_with_null_period_start(
    pg_session,
):
    """FIX-R1 Blocker 3: row insert succeeds for unknown ref_period."""
    factory = async_sessionmaker(
        bind=pg_session.bind, class_=AsyncSession, expire_on_commit=False
    )
    await _seed_mapping(factory)
    async with factory() as session:
        await session.execute(
            text(
                """
                INSERT INTO semantic_value_cache (
                    cube_id, product_id, semantic_key, coord, ref_period,
                    source_hash, fetched_at
                ) VALUES (
                    '18-10-0004-01', 18100004, 'cpi.canada.all_items',
                    '1.10.0.0.0.0.0.0.0.0', 'fortnight-2026-W17',
                    :hash, NOW()
                )
                """
            ),
            {"hash": "0" * 64},
        )
        await session.commit()
        result = await session.execute(
            text(
                "SELECT period_start FROM semantic_value_cache "
                "WHERE ref_period = 'fortnight-2026-W17'"
            )
        )
        row = result.first()
        assert row is not None
        assert row.period_start is None


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


@pytest.mark.asyncio
async def test_upsert_period_atomic_under_concurrency(pg_session):
    """FIX-R1 P1 #4: ON CONFLICT prevents duplicate inserts under race."""
    import asyncio

    factory = async_sessionmaker(
        bind=pg_session.bind, class_=AsyncSession, expire_on_commit=False
    )
    await _seed_mapping(factory)

    async def upsert_one():
        async with factory() as session:
            repo = SemanticValueCacheRepository(session)
            kw = dict(
                cube_id="18-10-0004-01",
                product_id=18100004,
                semantic_key="cpi.canada.all_items",
                coord="1.10.0.0.0.0.0.0.0.0",
                ref_period="2026-04",
                value=Decimal("123.4"),
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
            await repo.upsert_period(source_hash=sh, **kw)
            await session.commit()

    # Concurrent racers: ON CONFLICT must keep this to exactly one row.
    await asyncio.gather(upsert_one(), upsert_one(), upsert_one())

    async with factory() as session:
        result = await session.execute(
            text(
                "SELECT COUNT(*) FROM semantic_value_cache "
                "WHERE ref_period = '2026-04'"
            )
        )
        assert result.scalar() == 1


@pytest.mark.asyncio
async def test_upsert_period_bumps_updated_at_on_change(pg_session):
    """FIX-R1 P1 #5: ``updated_at = NOW()`` fires on the ON CONFLICT path."""
    import asyncio as _asyncio

    factory = async_sessionmaker(
        bind=pg_session.bind, class_=AsyncSession, expire_on_commit=False
    )
    await _seed_mapping(factory)
    base_kw = dict(
        cube_id="18-10-0004-01",
        product_id=18100004,
        semantic_key="cpi.canada.all_items",
        coord="1.10.0.0.0.0.0.0.0.0",
        ref_period="2026-04",
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

    def hash_for(value: Decimal) -> str:
        return compute_source_hash(value=value, **base_kw)

    async with factory() as session:
        repo = SemanticValueCacheRepository(session)
        await repo.upsert_period(
            source_hash=hash_for(Decimal("100.0")),
            value=Decimal("100.0"),
            **base_kw,
        )
        await session.commit()
        rows1 = await repo.get_by_lookup(
            cube_id="18-10-0004-01",
            semantic_key="cpi.canada.all_items",
            coord="1.10.0.0.0.0.0.0.0.0",
        )
        first_updated_at = rows1[0].updated_at

    await _asyncio.sleep(0.05)

    async with factory() as session:
        repo = SemanticValueCacheRepository(session)
        await repo.upsert_period(
            source_hash=hash_for(Decimal("200.0")),
            value=Decimal("200.0"),
            **base_kw,
        )
        await session.commit()
        rows2 = await repo.get_by_lookup(
            cube_id="18-10-0004-01",
            semantic_key="cpi.canada.all_items",
            coord="1.10.0.0.0.0.0.0.0.0",
        )
        assert rows2[0].updated_at > first_updated_at


@pytest.mark.asyncio
async def test_upsert_validated_primes_value_cache_for_new_mapping(pg_session):
    """FIX-R1 Blocker 1 regression: auto-prime POST-COMMIT actually
    succeeds for newly-saved mapping.

    Prior bug: auto-prime ran before mapping commit → FK to
    ``semantic_mappings`` violated → best-effort handler swallowed the
    error → no rows ever primed for new mappings. The fix moves auto-
    prime to AFTER ``session.commit()`` so the parent row is visible
    to the value-cache FK.
    """
    from datetime import timedelta
    from unittest.mock import AsyncMock
    import structlog
    from src.repositories.semantic_mapping_repository import (
        SemanticMappingRepository,
    )
    from src.services.semantic_mappings.service import SemanticMappingService
    from src.services.statcan.client import StatCanClient
    from src.services.statcan.metadata_cache import (
        CubeMetadataCacheEntry,
        StatCanMetadataCacheService,
    )
    from src.services.statcan.value_cache import StatCanValueCacheService
    from src.services.statcan.value_cache_schemas import StatCanDataResponse

    factory = async_sessionmaker(
        bind=pg_session.bind, class_=AsyncSession, expire_on_commit=False
    )

    # Seed metadata cache row so the mapping validator passes.
    async with factory() as session:
        await session.execute(
            text(
                """
                INSERT INTO cube_metadata_cache
                  (cube_id, product_id, dimensions, frequency_code,
                   cube_title_en, cube_title_fr, fetched_at)
                VALUES
                  ('18-10-0004-01', 18100004,
                   '{"dimensions":[{"position_id":1,"name_en":"Geography","name_fr":"x","has_uom":false,"members":[{"member_id":1,"name_en":"Canada","name_fr":"Canada"}]}]}'::jsonb,
                   '6', 'CPI', 'IPC', NOW())
                """
            )
        )
        await session.commit()

    metadata_cache = AsyncMock(spec=StatCanMetadataCacheService)
    metadata_cache.get_or_fetch.return_value = CubeMetadataCacheEntry(
        cube_id="18-10-0004-01",
        product_id=18100004,
        dimensions={
            "dimensions": [
                {
                    "position_id": 1,
                    "name_en": "Geography",
                    "name_fr": "x",
                    "has_uom": False,
                    "members": [
                        {"member_id": 1, "name_en": "Canada", "name_fr": "Canada"}
                    ],
                }
            ]
        },
        frequency_code="6",
        cube_title_en="CPI",
        cube_title_fr="IPC",
        fetched_at=_FIXED,
    )
    metadata_cache.get_cached.return_value = (
        metadata_cache.get_or_fetch.return_value
    )

    statcan_client = AsyncMock(spec=StatCanClient)
    statcan_client.get_data_from_cube_pid_coord_and_latest_n_periods.return_value = (
        StatCanDataResponse.model_validate(
            {
                "responseStatusCode": 0,
                "productId": 18100004,
                "coordinate": "1.0.0.0.0.0.0.0.0.0",
                "vectorId": 41690914,
                "vectorDataPoint": [
                    {
                        "refPer": "2026-04",
                        "value": "165.7",
                        "decimals": 1,
                        "scalarFactorCode": 0,
                        "symbolCode": 0,
                        "securityLevelCode": 0,
                        "statusCode": 0,
                        "frequencyCode": 6,
                        "missing": False,
                    }
                ],
            }
        )
    )

    value_cache_service = StatCanValueCacheService(
        session_factory=factory,
        repository_factory=lambda s: SemanticValueCacheRepository(s),
        mapping_repository_factory=lambda s: SemanticMappingRepository(s),
        cube_metadata_cache=metadata_cache,
        statcan_client=statcan_client,
        clock=lambda: _FIXED,
        logger=structlog.get_logger(),
    )
    mapping_service = SemanticMappingService(
        session_factory=factory,
        repository_factory=lambda s: SemanticMappingRepository(s),
        metadata_cache=metadata_cache,
        logger=structlog.get_logger(),
        value_cache_service=value_cache_service,
    )

    mapping, was_created = await mapping_service.upsert_validated(
        cube_id="18-10-0004-01",
        product_id=18100004,
        semantic_key="cpi.canada.all_items",
        label="CPI Canada all items",
        description=None,
        config={"dimension_filters": {"Geography": "Canada"}},
        is_active=True,
        updated_by="test",
    )
    assert was_created is True

    # Mapping must be committed (visible from a fresh session).
    async with factory() as session:
        repo = SemanticMappingRepository(session)
        persisted = await repo.get_by_key(
            "18-10-0004-01", "cpi.canada.all_items"
        )
        assert persisted is not None

    # Value cache must be primed (this is what the bug broke).
    async with factory() as session:
        vrepo = SemanticValueCacheRepository(session)
        rows = await vrepo.get_by_lookup(
            cube_id="18-10-0004-01",
            semantic_key="cpi.canada.all_items",
            coord="1.0.0.0.0.0.0.0.0.0",
        )
        assert len(rows) == 1, "auto-prime did not insert post-commit"
        assert rows[0].vector_id == 41690914
        assert rows[0].response_status_code == 0


@pytest.mark.asyncio
async def test_get_latest_by_lookup_orders_by_period_start_not_string(
    pg_session,
):
    """FIX-R2 (P2): rank by GENERATED ``period_start`` DATE, not string.

    Mixed ref_period formats: ``"2025-Q4"`` (period_start = 2025-10-01)
    vs ``"2025-12"`` (period_start = 2025-12-01). String sort would put
    ``"2025-Q4"`` after ``"2025-12"`` lexically — actual chronology has
    ``"2025-12"`` later. This test would fail with a pure string sort.
    """
    factory = async_sessionmaker(
        bind=pg_session.bind, class_=AsyncSession, expire_on_commit=False
    )
    await _seed_mapping(factory)
    async with factory() as session:
        repo = SemanticValueCacheRepository(session)
        for rp, value in [
            ("2025-01-15", Decimal("1.0")),
            ("2025-Q4", Decimal("2.0")),
            ("2025-12", Decimal("3.0")),
        ]:
            kw = dict(
                cube_id="18-10-0004-01",
                product_id=18100004,
                semantic_key="cpi.canada.all_items",
                coord="1.10.0.0.0.0.0.0.0.0",
                ref_period=rp,
                value=value,
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
            await repo.upsert_period(source_hash=sh, **kw)
        await session.commit()

        latest = await repo.get_latest_by_lookup(
            cube_id="18-10-0004-01",
            semantic_key="cpi.canada.all_items",
            coord="1.10.0.0.0.0.0.0.0.0",
        )
        assert latest is not None
        # period_start ordering: 2025-12 (Dec 1) > 2025-Q4 (Oct 1) > 2025-01-15
        assert latest.ref_period == "2025-12"
