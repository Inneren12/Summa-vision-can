"""Migration backfill tests for the ``lineage_key`` column.

Scenarios per recon ``phase-2-2-0-recon.md`` §E2:

1. Linear clone chain inheritance (A → B → C share key).
2. Multiple independent roots (no parents → distinct keys).
3. Orphaned clone (parent SET NULL via cascade → fresh key).
4. Idempotency of upgrade → downgrade → upgrade.
5. NOT NULL enforcement after backfill.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import pytest
import sqlalchemy as sa

# UUID v7 (RFC 9562): version=7, variant=10xx (first variant nibble is 8/9/a/b)
UUID_V7_REGEX = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)

# Pre-Phase-2.2.0 head — last revision before lineage_key was added.
PRE_LINEAGE_REVISION = "b4f9a21c8d77"

pytestmark = pytest.mark.integration


async def test_linear_clone_chain_shares_lineage_key(db_at_revision) -> None:
    """A → B → C all inherit A's freshly-generated lineage_key."""
    engine = await db_at_revision(PRE_LINEAGE_REVISION)

    async with engine.begin() as conn:
        await conn.execute(
            sa.text(
                "INSERT INTO publications "
                "(id, headline, chart_type, status, version, created_at) VALUES "
                "(1, 'A', 'bar', 'DRAFT'::publication_status, 1, NOW()), "
                "(2, 'B', 'bar', 'DRAFT'::publication_status, 1, NOW()), "
                "(3, 'C', 'bar', 'DRAFT'::publication_status, 1, NOW())"
            )
        )
        await conn.execute(
            sa.text(
                "UPDATE publications SET cloned_from_publication_id = 1 WHERE id = 2"
            )
        )
        await conn.execute(
            sa.text(
                "UPDATE publications SET cloned_from_publication_id = 2 WHERE id = 3"
            )
        )

    engine = await db_at_revision("head")

    async with engine.begin() as conn:
        result = await conn.execute(
            sa.text("SELECT id, lineage_key FROM publications ORDER BY id")
        )
        rows = result.all()

    assert len(rows) == 3
    keys = [row.lineage_key for row in rows]
    assert keys[0] == keys[1] == keys[2]
    assert UUID_V7_REGEX.match(keys[0]), f"Expected UUID v7, got {keys[0]!r}"


async def test_multiple_independent_roots_get_distinct_keys(db_at_revision) -> None:
    """Three rows with no clone parents get three distinct lineage_keys."""
    engine = await db_at_revision(PRE_LINEAGE_REVISION)

    async with engine.begin() as conn:
        await conn.execute(
            sa.text(
                "INSERT INTO publications "
                "(id, headline, chart_type, status, version, created_at) VALUES "
                "(1, 'P1', 'bar', 'DRAFT'::publication_status, 1, NOW()), "
                "(2, 'P2', 'bar', 'DRAFT'::publication_status, 1, NOW()), "
                "(3, 'P3', 'bar', 'DRAFT'::publication_status, 1, NOW())"
            )
        )

    engine = await db_at_revision("head")

    async with engine.begin() as conn:
        result = await conn.execute(
            sa.text("SELECT lineage_key FROM publications ORDER BY id")
        )
        keys = [row.lineage_key for row in result.all()]

    assert len(keys) == 3
    assert len(set(keys)) == 3
    for key in keys:
        assert UUID_V7_REGEX.match(key), f"Expected UUID v7, got {key!r}"


async def test_orphaned_clone_gets_fresh_lineage_key(db_at_revision) -> None:
    """Clone with parent hard-deleted (FK SET NULL) is treated as a root."""
    engine = await db_at_revision(PRE_LINEAGE_REVISION)

    async with engine.begin() as conn:
        await conn.execute(
            sa.text(
                "INSERT INTO publications "
                "(id, headline, chart_type, status, version, created_at) VALUES "
                "(1, 'parent', 'bar', 'DRAFT'::publication_status, 1, NOW()), "
                "(2, 'orphan', 'bar', 'DRAFT'::publication_status, 1, NOW())"
            )
        )
        await conn.execute(
            sa.text(
                "UPDATE publications SET cloned_from_publication_id = 1 WHERE id = 2"
            )
        )
        # Hard-delete parent — FK ondelete=SET NULL nulls orphan.cloned_from_publication_id
        await conn.execute(sa.text("DELETE FROM publications WHERE id = 1"))

    engine = await db_at_revision("head")

    async with engine.begin() as conn:
        result = await conn.execute(
            sa.text("SELECT lineage_key FROM publications WHERE id = 2")
        )
        row = result.one()

    assert row.lineage_key is not None
    assert UUID_V7_REGEX.match(row.lineage_key), (
        f"Expected UUID v7, got {row.lineage_key!r}"
    )


async def test_upgrade_downgrade_upgrade_idempotency(db_at_revision) -> None:
    """``upgrade head`` → ``downgrade -1`` → ``upgrade head`` keeps schema valid."""
    engine = await db_at_revision("head")

    async with engine.begin() as conn:
        result = await conn.execute(
            sa.text(
                "SELECT column_name, is_nullable FROM information_schema.columns "
                "WHERE table_name = 'publications' AND column_name = 'lineage_key'"
            )
        )
        col = result.one_or_none()
        assert col is not None, "lineage_key column missing after upgrade"
        assert col.is_nullable == "NO", (
            f"lineage_key should be NOT NULL, got {col.is_nullable}"
        )

    # Round-trip via subprocess directly — fixture's helper is intentionally
    # private; we bypass it here to control timing precisely.
    backend_root = Path(__file__).resolve().parents[3]
    db_url = os.environ["TEST_DATABASE_URL"]
    env = {**os.environ, "DATABASE_URL": db_url}
    alembic_ini = backend_root / "alembic.ini"

    await engine.dispose()  # release connections before alembic runs

    subprocess.run(
        ["alembic", "-c", str(alembic_ini), "downgrade", "-1"],
        cwd=backend_root,
        env=env,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["alembic", "-c", str(alembic_ini), "upgrade", "head"],
        cwd=backend_root,
        env=env,
        check=True,
        capture_output=True,
    )

    engine = await db_at_revision("head")
    async with engine.begin() as conn:
        result = await conn.execute(
            sa.text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'publications' AND column_name = 'lineage_key'"
            )
        )
        assert result.one_or_none() is not None


async def test_not_null_enforced_after_backfill(db_at_revision) -> None:
    """Post-backfill, INSERT without lineage_key fails the NOT NULL check."""
    engine = await db_at_revision("head")

    with pytest.raises(Exception) as exc_info:
        async with engine.begin() as conn:
            await conn.execute(
                sa.text(
                    "INSERT INTO publications "
                    "(headline, chart_type, status, version, created_at) VALUES "
                    "('NoLineage', 'bar', 'DRAFT'::publication_status, 1, NOW())"
                )
            )

    err = str(exc_info.value).lower()
    assert "lineage_key" in err or "not null" in err or "not-null" in err, (
        f"Expected NOT NULL violation message, got: {err}"
    )
