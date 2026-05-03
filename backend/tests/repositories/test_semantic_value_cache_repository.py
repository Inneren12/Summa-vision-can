"""Phase 3.1aaa: SemanticValueCacheRepository unit tests.

In-memory SQLite via the project ``db_session`` fixture. The Postgres
GENERATED ``period_start`` column is ignored on SQLite (column exists,
defaults NULL) — repository methods do not depend on it.

FK CASCADE behaviour against ``semantic_mappings`` is asserted in the
PG migration round-trip integration test
(`test_semantic_value_cache_migration.py`); SQLite's foreign_keys
pragma defaults to OFF in the project test rig.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from src.models.semantic_mapping import SemanticMapping
from src.repositories.semantic_value_cache_repository import (
    SemanticValueCacheRepository,
)
from src.services.statcan.value_cache_hash import compute_source_hash
from src.services.statcan.value_cache_schemas import (
    StatCanDataPoint,
    ValueCacheUpsertItem,
)


_FIXED = datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc)


async def _seed_mapping(
    db_session,
    *,
    cube_id: str = "18-10-0004-01",
    semantic_key: str = "cpi.canada.all_items",
) -> SemanticMapping:
    mapping = SemanticMapping(
        cube_id=cube_id,
        product_id=18100004,
        semantic_key=semantic_key,
        label="lbl",
        description=None,
        config={"dimension_filters": {}},
        is_active=True,
        version=1,
    )
    db_session.add(mapping)
    await db_session.commit()
    return mapping


def _row_kwargs(**overrides):
    base = dict(
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
    base.update(overrides)
    return base


def _hash_of(kwargs: dict) -> str:
    return compute_source_hash(
        product_id=kwargs["product_id"],
        cube_id=kwargs["cube_id"],
        semantic_key=kwargs["semantic_key"],
        coord=kwargs["coord"],
        ref_period=kwargs["ref_period"],
        value=kwargs["value"],
        missing=kwargs["missing"],
        decimals=kwargs["decimals"],
        scalar_factor_code=kwargs["scalar_factor_code"],
        symbol_code=kwargs["symbol_code"],
        security_level_code=kwargs["security_level_code"],
        status_code=kwargs["status_code"],
        frequency_code=kwargs["frequency_code"],
        vector_id=kwargs["vector_id"],
        response_status_code=kwargs["response_status_code"],
    )


class TestUpsertPeriod:
    @pytest.mark.asyncio
    async def test_inserts_new_row(self, db_session):
        await _seed_mapping(db_session)
        repo = SemanticValueCacheRepository(db_session)
        kw = _row_kwargs()
        entity, outcome = await repo.upsert_period(source_hash=_hash_of(kw), **kw)
        await db_session.commit()
        assert outcome == "inserted"
        assert entity.id is not None
        assert entity.value == Decimal("123.4")

    @pytest.mark.asyncio
    async def test_idempotent_same_hash_returns_unchanged(self, db_session):
        await _seed_mapping(db_session)
        repo = SemanticValueCacheRepository(db_session)
        kw = _row_kwargs()
        await repo.upsert_period(source_hash=_hash_of(kw), **kw)
        await db_session.commit()
        _, outcome = await repo.upsert_period(source_hash=_hash_of(kw), **kw)
        await db_session.commit()
        assert outcome == "unchanged"

    @pytest.mark.asyncio
    async def test_changed_hash_updates_row(self, db_session):
        await _seed_mapping(db_session)
        repo = SemanticValueCacheRepository(db_session)
        kw1 = _row_kwargs(value=Decimal("1.0"))
        await repo.upsert_period(source_hash=_hash_of(kw1), **kw1)
        await db_session.commit()
        kw2 = _row_kwargs(value=Decimal("2.0"))
        entity, outcome = await repo.upsert_period(source_hash=_hash_of(kw2), **kw2)
        await db_session.commit()
        assert outcome == "updated"
        assert entity.value == Decimal("2.0")

    @pytest.mark.asyncio
    async def test_unchanged_clears_stale_flag(self, db_session):
        await _seed_mapping(db_session)
        repo = SemanticValueCacheRepository(db_session)
        kw = _row_kwargs()
        entity, _ = await repo.upsert_period(source_hash=_hash_of(kw), **kw)
        entity.is_stale = True
        await db_session.commit()
        e2, outcome = await repo.upsert_period(source_hash=_hash_of(kw), **kw)
        await db_session.commit()
        assert outcome == "unchanged"
        assert e2.is_stale is False


    @pytest.mark.asyncio
    async def test_persists_vector_id_and_response_status_code(self, db_session):
        """FIX-R1 Blocker 2: response-level metadata flows into the row."""
        await _seed_mapping(db_session)
        repo = SemanticValueCacheRepository(db_session)
        kw = _row_kwargs(vector_id=41690914, response_status_code=7)
        entity, _ = await repo.upsert_period(source_hash=_hash_of(kw), **kw)
        await db_session.commit()
        assert entity.vector_id == 41690914
        assert entity.response_status_code == 7


class TestUpsertPeriodsBatch:
    @pytest.mark.asyncio
    async def test_batch_inserts_multiple_periods(self, db_session):
        await _seed_mapping(db_session)
        repo = SemanticValueCacheRepository(db_session)
        items = [
            ValueCacheUpsertItem(
                cube_id="18-10-0004-01",
                product_id=18100004,
                semantic_key="cpi.canada.all_items",
                coord="1.10.0.0.0.0.0.0.0.0",
                data_point=StatCanDataPoint(
                    refPer=f"2026-{m:02d}",
                    value=Decimal(f"{100 + m}.0"),
                    decimals=1,
                ),
                fetched_at=_FIXED,
            )
            for m in (1, 2, 3)
        ]
        counts = await repo.upsert_periods_batch(items)
        await db_session.commit()
        assert counts == {"inserted": 3, "updated": 0, "unchanged": 0}

    @pytest.mark.asyncio
    async def test_batch_propagates_vector_id_and_response_status_code(
        self, db_session
    ):
        """FIX-R1 Blocker 2: ``ValueCacheUpsertItem`` carries response-
        level metadata into both ``compute_source_hash`` and the row."""
        await _seed_mapping(db_session)
        repo = SemanticValueCacheRepository(db_session)
        items = [
            ValueCacheUpsertItem(
                cube_id="18-10-0004-01",
                product_id=18100004,
                semantic_key="cpi.canada.all_items",
                coord="1.10.0.0.0.0.0.0.0.0",
                data_point=StatCanDataPoint(
                    refPer="2026-04",
                    value=Decimal("123.4"),
                    decimals=1,
                ),
                fetched_at=_FIXED,
                vector_id=41690914,
                response_status_code=0,
            )
        ]
        await repo.upsert_periods_batch(items)
        await db_session.commit()
        rows = await repo.get_by_lookup(
            cube_id="18-10-0004-01",
            semantic_key="cpi.canada.all_items",
            coord="1.10.0.0.0.0.0.0.0.0",
        )
        assert rows[0].vector_id == 41690914
        assert rows[0].response_status_code == 0


class TestGetByLookup:
    @pytest.mark.asyncio
    async def test_returns_all_for_triple(self, db_session):
        await _seed_mapping(db_session)
        repo = SemanticValueCacheRepository(db_session)
        for m in (1, 2, 3):
            kw = _row_kwargs(ref_period=f"2026-{m:02d}")
            await repo.upsert_period(source_hash=_hash_of(kw), **kw)
        await db_session.commit()
        rows = await repo.get_by_lookup(
            cube_id="18-10-0004-01",
            semantic_key="cpi.canada.all_items",
            coord="1.10.0.0.0.0.0.0.0.0",
        )
        assert len(rows) == 3

    @pytest.mark.asyncio
    async def test_filtered_by_ref_period(self, db_session):
        await _seed_mapping(db_session)
        repo = SemanticValueCacheRepository(db_session)
        for m in (1, 2, 3):
            kw = _row_kwargs(ref_period=f"2026-{m:02d}")
            await repo.upsert_period(source_hash=_hash_of(kw), **kw)
        await db_session.commit()
        rows = await repo.get_by_lookup(
            cube_id="18-10-0004-01",
            semantic_key="cpi.canada.all_items",
            coord="1.10.0.0.0.0.0.0.0.0",
            ref_period="2026-02",
        )
        assert len(rows) == 1
        assert rows[0].ref_period == "2026-02"


class TestGetLatestByLookup:
    @pytest.mark.asyncio
    async def test_orders_by_ref_period_desc(self, db_session):
        await _seed_mapping(db_session)
        repo = SemanticValueCacheRepository(db_session)
        for m in (1, 2, 3):
            kw = _row_kwargs(ref_period=f"2026-{m:02d}")
            await repo.upsert_period(source_hash=_hash_of(kw), **kw)
        await db_session.commit()
        latest = await repo.get_latest_by_lookup(
            cube_id="18-10-0004-01",
            semantic_key="cpi.canada.all_items",
            coord="1.10.0.0.0.0.0.0.0.0",
        )
        assert latest is not None
        assert latest.ref_period == "2026-03"


class TestMarkStaleOutsideWindow:
    @pytest.mark.asyncio
    async def test_marks_old_periods_stale(self, db_session):
        await _seed_mapping(db_session)
        repo = SemanticValueCacheRepository(db_session)
        for m in range(1, 6):
            kw = _row_kwargs(ref_period=f"2026-{m:02d}")
            await repo.upsert_period(source_hash=_hash_of(kw), **kw)
        await db_session.commit()
        marked = await repo.mark_stale_outside_window(
            cube_id="18-10-0004-01",
            semantic_key="cpi.canada.all_items",
            coord="1.10.0.0.0.0.0.0.0.0",
            retention_count=3,
        )
        await db_session.commit()
        # 5 rows total, retention=3 → 2 marked stale.
        assert marked == 2
        rows = await repo.get_by_lookup(
            cube_id="18-10-0004-01",
            semantic_key="cpi.canada.all_items",
            coord="1.10.0.0.0.0.0.0.0.0",
        )
        stale_periods = sorted(r.ref_period for r in rows if r.is_stale)
        assert stale_periods == ["2026-01", "2026-02"]


class TestDeleteOlderThan:
    @pytest.mark.asyncio
    async def test_hard_deletes_by_fetched_at(self, db_session):
        await _seed_mapping(db_session)
        repo = SemanticValueCacheRepository(db_session)
        old = _FIXED - timedelta(days=10)
        kw_old = _row_kwargs(ref_period="2025-12", fetched_at=old)
        await repo.upsert_period(source_hash=_hash_of(kw_old), **kw_old)
        kw_new = _row_kwargs(ref_period="2026-04")
        await repo.upsert_period(source_hash=_hash_of(kw_new), **kw_new)
        await db_session.commit()

        deleted = await repo.delete_older_than(_FIXED - timedelta(days=1))
        await db_session.commit()
        assert deleted == 1


class TestListActiveLookupKeys:
    """FIX-R2 (Blocker 2) regressions: source from semantic_mappings."""

    @pytest.mark.asyncio
    async def test_includes_active_mapping_with_no_cache_rows(self, db_session):
        """Active mapping must appear with ``coord=None`` even when no
        value-cache row exists for it (best-effort retry contract)."""
        await _seed_mapping(
            db_session,
            cube_id="11-10-0001-01",
            semantic_key="empty_cache_mapping",
        )
        repo = SemanticValueCacheRepository(db_session)
        keys = await repo.list_active_lookup_keys()
        match = [
            k for k in keys
            if k[0] == "11-10-0001-01" and k[1] == "empty_cache_mapping"
        ]
        assert len(match) == 1
        assert match[0][2] is None  # coord
        assert match[0][3] == 18100004  # product_id from _seed_mapping default

    @pytest.mark.asyncio
    async def test_excludes_inactive_mapping(self, db_session):
        """Soft-deleted mapping (``is_active=False``) must NOT appear."""
        mapping = SemanticMapping(
            cube_id="34-10-0001-01",
            product_id=34100001,
            semantic_key="inactive_test",
            label="lbl",
            description=None,
            config={"dimension_filters": {}},
            is_active=False,
            version=1,
        )
        db_session.add(mapping)
        await db_session.commit()
        repo = SemanticValueCacheRepository(db_session)
        keys = await repo.list_active_lookup_keys()
        assert not any(
            k[0] == "34-10-0001-01" and k[1] == "inactive_test" for k in keys
        )

    @pytest.mark.asyncio
    async def test_includes_active_mapping_with_cached_coord(self, db_session):
        """Mapping with cached row(s) appears once per (mapping, coord)."""
        await _seed_mapping(db_session)
        repo = SemanticValueCacheRepository(db_session)
        kw = _row_kwargs(coord="1.10.0.0.0.0.0.0.0.0")
        await repo.upsert_period(source_hash=_hash_of(kw), **kw)
        await db_session.commit()

        keys = await repo.list_active_lookup_keys()
        primed = [
            k for k in keys
            if k[0] == "18-10-0004-01"
            and k[1] == "cpi.canada.all_items"
            and k[2] == "1.10.0.0.0.0.0.0.0.0"
        ]
        assert len(primed) == 1


class TestSortByPeriodStart:
    """FIX-R2 (P2) regression: sort by period_start DATE, not string."""

    @pytest.mark.asyncio
    async def test_get_by_lookup_orders_by_period_start_asc(self, db_session):
        """Mixed-format ref_periods must order by period_start, not string.

        On SQLite (test fixture) ``period_start`` is always NULL — the
        ``nulls_last()`` clause in the query causes the ``ref_period``
        tiebreaker to drive the order. The test asserts the sort is
        stable and reasonable for the SQLite path; full PG semantic
        coverage lives in the integration tests.
        """
        await _seed_mapping(db_session)
        repo = SemanticValueCacheRepository(db_session)
        for rp in ("2025-12", "2025-01-15", "2025-Q4"):
            kw = _row_kwargs(ref_period=rp)
            await repo.upsert_period(source_hash=_hash_of(kw), **kw)
        await db_session.commit()

        rows = await repo.get_by_lookup(
            cube_id="18-10-0004-01",
            semantic_key="cpi.canada.all_items",
            coord="1.10.0.0.0.0.0.0.0.0",
        )
        # All NULL period_start on SQLite → ref_period asc tiebreaker.
        assert [r.ref_period for r in rows] == sorted(
            r.ref_period for r in rows
        )
