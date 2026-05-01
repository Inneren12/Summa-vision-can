"""Phase 3.1aa: CubeMetadataCacheRepository tests."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from src.repositories.cube_metadata_cache_repository import (
    CubeMetadataCacheRepository,
)


def _now() -> datetime:
    return datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc)


def _payload(**overrides):
    base = dict(
        cube_id="18-10-0004-01",
        product_id=18100004,
        dimensions={"dimensions": [{"position_id": 1, "name_en": "Geo"}]},
        frequency_code="6",
        cube_title_en="Consumer Price Index",
        cube_title_fr="Indice des prix à la consommation",
        fetched_at=_now(),
    )
    base.update(overrides)
    return base


class TestCubeMetadataCacheRepository:
    @pytest.mark.asyncio
    async def test_get_by_cube_id_returns_none_when_missing(self, db_session):
        repo = CubeMetadataCacheRepository(db_session)
        assert await repo.get_by_cube_id("missing") is None

    @pytest.mark.asyncio
    async def test_upsert_inserts_when_absent_returns_changed_true(
        self, db_session
    ):
        repo = CubeMetadataCacheRepository(db_session)
        entity, changed = await repo.upsert(**_payload())
        await db_session.commit()

        assert changed is True
        assert entity.id is not None
        assert entity.cube_id == "18-10-0004-01"
        assert entity.product_id == 18100004
        assert entity.frequency_code == "6"

    @pytest.mark.asyncio
    async def test_upsert_with_identical_payload_returns_changed_false_and_does_not_bump_updated_at(
        self, db_session
    ):
        repo = CubeMetadataCacheRepository(db_session)
        entity, _ = await repo.upsert(**_payload())
        await db_session.commit()
        first_updated_at = entity.updated_at

        # Yield to ensure any timestamp tick would register if onupdate fired.
        await asyncio.sleep(0.01)

        entity2, changed = await repo.upsert(**_payload())
        await db_session.commit()

        assert changed is False
        assert entity2.id == entity.id
        assert entity2.updated_at == first_updated_at

    @pytest.mark.asyncio
    async def test_upsert_with_modified_dimensions_returns_changed_true_and_bumps_updated_at(
        self, db_session
    ):
        repo = CubeMetadataCacheRepository(db_session)
        entity, _ = await repo.upsert(**_payload())
        await db_session.commit()
        original_id = entity.id

        new_dims = {"dimensions": [{"position_id": 1, "name_en": "Geography"}]}
        entity2, changed = await repo.upsert(
            **_payload(dimensions=new_dims, fetched_at=_now() + timedelta(hours=1))
        )
        await db_session.commit()

        assert changed is True
        assert entity2.id == original_id
        assert entity2.dimensions == new_dims
        assert entity2.fetched_at == _now() + timedelta(hours=1)

    @pytest.mark.asyncio
    async def test_list_stale_returns_only_rows_older_than_threshold(
        self, db_session
    ):
        repo = CubeMetadataCacheRepository(db_session)
        old = _now() - timedelta(days=2)
        recent = _now()

        await repo.upsert(**_payload(cube_id="old-1", fetched_at=old))
        await repo.upsert(**_payload(cube_id="recent-1", fetched_at=recent))
        await db_session.commit()

        threshold = _now() - timedelta(days=1)
        stale = await repo.list_stale(before=threshold)

        ids = {row.cube_id for row in stale}
        assert ids == {"old-1"}
