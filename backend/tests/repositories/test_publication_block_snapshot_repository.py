"""Phase 3.1d: PublicationBlockSnapshotRepository unit tests.

In-memory SQLite via the project ``db_session`` fixture. The repository
provides a SQLite-compatible upsert fallback (PG path is exercised in
the migration round-trip integration test, deferred to PR 2 pipeline).

SQLite's ``foreign_keys`` PRAGMA defaults to OFF in the project test
rig (see ``test_semantic_value_cache_repository``). The FK CASCADE
test enables the PRAGMA explicitly.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from src.models.publication_block_snapshot import PublicationBlockSnapshot
from src.repositories.publication_block_snapshot_repository import (
    PublicationBlockSnapshotRepository,
)
from tests.conftest import make_publication


_NOW = datetime(2026, 5, 4, 12, 0, 0, tzinfo=timezone.utc)


async def _seed_publication(db_session, **overrides):
    pub = make_publication(**overrides)
    db_session.add(pub)
    await db_session.commit()
    return pub


def _kwargs(publication_id: int, block_id: str = "block-A", **overrides):
    base = dict(
        publication_id=publication_id,
        block_id=block_id,
        cube_id="18-10-0004",
        semantic_key="cpi.canada.all_items",
        coord="1.10.0.0.0.0.0.0.0.0",
        period="2026-04",
        dims_json=[1, 2],
        members_json=[10, 20],
        mapping_version_at_publish=1,
        source_hash_at_publish="a" * 64,
        value_at_publish="123.4",
        missing_at_publish=False,
        is_stale_at_publish=False,
        captured_at=_NOW,
    )
    base.update(overrides)
    return base


class TestPublicationBlockSnapshotRepository:
    async def test_upsert_inserts_new_row(self, db_session):
        pub = await _seed_publication(db_session)
        repo = PublicationBlockSnapshotRepository(db_session)

        row = await repo.upsert_for_block(**_kwargs(pub.id))
        await db_session.commit()

        assert row.id is not None
        assert row.publication_id == pub.id
        assert row.block_id == "block-A"
        assert row.cube_id == "18-10-0004"
        assert row.semantic_key == "cpi.canada.all_items"
        assert row.coord == "1.10.0.0.0.0.0.0.0.0"
        assert row.period == "2026-04"
        assert row.dims_json == [1, 2]
        assert row.members_json == [10, 20]
        assert row.mapping_version_at_publish == 1
        assert row.source_hash_at_publish == "a" * 64
        assert row.value_at_publish == "123.4"
        assert row.missing_at_publish is False
        assert row.is_stale_at_publish is False
        assert row.captured_at is not None
        assert row.created_at is not None
        assert row.updated_at is not None

    async def test_upsert_overwrites_existing_row(self, db_session):
        pub = await _seed_publication(db_session)
        repo = PublicationBlockSnapshotRepository(db_session)

        first = await repo.upsert_for_block(**_kwargs(pub.id))
        await db_session.commit()
        first_id = first.id
        first_created_at = first.created_at
        first_updated_at = first.updated_at

        # Sleep so updated_at can advance against second-resolution clocks.
        await asyncio.sleep(0.05)

        second_captured = datetime(2026, 5, 5, 9, 0, 0, tzinfo=timezone.utc)
        second = await repo.upsert_for_block(
            **_kwargs(
                pub.id,
                cube_id="18-10-9999",
                semantic_key="cpi.canada.shelter",
                coord="2.20.0.0.0.0.0.0.0.0",
                period="2026-05",
                dims_json=[3],
                members_json=[30],
                mapping_version_at_publish=7,
                source_hash_at_publish="b" * 64,
                value_at_publish="999.9",
                missing_at_publish=True,
                is_stale_at_publish=True,
                captured_at=second_captured,
            )
        )
        await db_session.commit()

        assert second.id == first_id, "upsert must overwrite, not insert new row"
        assert second.cube_id == "18-10-9999"
        assert second.semantic_key == "cpi.canada.shelter"
        assert second.coord == "2.20.0.0.0.0.0.0.0.0"
        assert second.period == "2026-05"
        assert second.dims_json == [3]
        assert second.members_json == [30]
        assert second.mapping_version_at_publish == 7
        assert second.source_hash_at_publish == "b" * 64
        assert second.value_at_publish == "999.9"
        assert second.missing_at_publish is True
        assert second.is_stale_at_publish is True
        # SQLite strips tzinfo on roundtrip; compare naive components.
        assert second.captured_at.replace(tzinfo=None) == second_captured.replace(
            tzinfo=None
        )
        assert second.created_at == first_created_at
        assert second.updated_at >= first_updated_at

        # Single row exists.
        rows = await repo.get_for_publication(pub.id)
        assert len(rows) == 1

    async def test_get_for_publication_returns_all_rows(self, db_session):
        pub_a = await _seed_publication(db_session, headline="A")
        pub_b = await _seed_publication(db_session, headline="B")
        repo = PublicationBlockSnapshotRepository(db_session)

        await repo.upsert_for_block(**_kwargs(pub_a.id, block_id="block-c"))
        await repo.upsert_for_block(**_kwargs(pub_a.id, block_id="block-a"))
        await repo.upsert_for_block(**_kwargs(pub_a.id, block_id="block-b"))
        await repo.upsert_for_block(**_kwargs(pub_b.id, block_id="block-z"))
        await db_session.commit()

        rows_a = await repo.get_for_publication(pub_a.id)
        assert [r.block_id for r in rows_a] == ["block-a", "block-b", "block-c"]

        rows_b = await repo.get_for_publication(pub_b.id)
        assert [r.block_id for r in rows_b] == ["block-z"]

    async def test_get_for_publication_empty_returns_empty_list(self, db_session):
        pub = await _seed_publication(db_session)
        repo = PublicationBlockSnapshotRepository(db_session)

        rows = await repo.get_for_publication(pub.id)
        assert rows == []

    async def test_delete_for_publication_removes_all(self, db_session):
        pub = await _seed_publication(db_session)
        repo = PublicationBlockSnapshotRepository(db_session)

        for bid in ("block-a", "block-b", "block-c"):
            await repo.upsert_for_block(**_kwargs(pub.id, block_id=bid))
        await db_session.commit()

        deleted = await repo.delete_for_publication(pub.id)
        await db_session.commit()

        assert deleted == 3
        assert await repo.get_for_publication(pub.id) == []

    async def test_fk_cascade_on_publication_delete(self, db_session):
        # Enable foreign key enforcement on SQLite (OFF by default in
        # the project test rig). Postgres CI uses real FKs natively.
        if db_session.bind.dialect.name == "sqlite":
            await db_session.execute(text("PRAGMA foreign_keys = ON"))

        pub = await _seed_publication(db_session)
        repo = PublicationBlockSnapshotRepository(db_session)

        await repo.upsert_for_block(**_kwargs(pub.id))
        await db_session.commit()
        assert len(await repo.get_for_publication(pub.id)) == 1

        await db_session.execute(
            text("DELETE FROM publications WHERE id = :id"), {"id": pub.id}
        )
        await db_session.commit()

        assert await repo.get_for_publication(pub.id) == []

    async def test_column_lengths_match_locked_recon_contract(self):
        """Snapshot column lengths must match recon §2.1 lock + cache parity.

        coord parity rule: publication_block_snapshot.coord MUST NOT be
        narrower than semantic_value_cache.coord (snapshot stores identity
        for re-resolve through cache).
        """
        cols = PublicationBlockSnapshot.__table__.c
        assert cols.block_id.type.length == 128, "block_id locked at String(128)"
        assert cols.cube_id.type.length == 50, "cube_id matches semantic_value_cache.cube_id"
        assert cols.semantic_key.type.length == 200, "semantic_key=200 per DEBT-063"
        assert cols.coord.type.length == 50, (
            "coord must match semantic_value_cache.coord = String(50); "
            "narrower would truncate/fail on long StatCan coords"
        )
        assert cols.period.type.length == 20, "period locked at String(20)"
        assert cols.source_hash_at_publish.type.length == 64, "source_hash=64"

    async def test_unique_constraint_violation(self, db_session):
        pub = await _seed_publication(db_session)

        row1 = PublicationBlockSnapshot(**_kwargs(pub.id, block_id="dup"))
        db_session.add(row1)
        await db_session.commit()

        row2 = PublicationBlockSnapshot(**_kwargs(pub.id, block_id="dup"))
        db_session.add(row2)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()
