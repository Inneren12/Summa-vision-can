"""add product_id to semantic_mappings

Revision ID: a1b2c3d4e5f6
Revises: 2e15e3f4d1f2
Create Date: 2026-05-02 00:00:00.000000

Phase 3.1b R3 — reviewer P1 fix.

Persists ``product_id`` on ``semantic_mappings`` so the admin edit flow can
hydrate the form from the row alone (no separate cache lookup).

Expand-contract upgrade (safe regardless of pre-existing row count):

    1. Add ``product_id`` nullable.
    2. Best-effort backfill: copy ``product_id`` from
       ``cube_metadata_cache`` for any existing semantic mapping whose
       ``cube_id`` already has a cached entry. Operators who never primed
       the cache will see a clear RuntimeError below rather than a
       cryptic NOT-NULL violation.
    3. Fail loudly if any rows still have NULL ``product_id`` — the
       precedent from ``d678f1a14d73_enforce_slug_not_null_unique`` is
       to raise rather than silently corrupt the table.
    4. Alter to NOT NULL (uses :func:`batch_alter_table` for SQLite
       compatibility — the project's test fixtures run on SQLite).
    5. Index ``product_id`` for future "all mappings for cube product N"
       queries; mirrors the model ``__table_args__`` 1:1.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "2e15e3f4d1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    # Step 1 — add nullable so existing rows survive.
    op.add_column(
        "semantic_mappings",
        sa.Column("product_id", sa.BigInteger(), nullable=True),
    )

    # Step 2 — best-effort backfill from the StatCan metadata cache.
    # cube_metadata_cache has UNIQUE (cube_id), so the join is safe.
    op.execute(
        sa.text(
            "UPDATE semantic_mappings "
            "SET product_id = cmc.product_id "
            "FROM cube_metadata_cache cmc "
            "WHERE semantic_mappings.cube_id = cmc.cube_id "
            "AND semantic_mappings.product_id IS NULL"
        )
        if bind.dialect.name == "postgresql"
        # SQLite does not support UPDATE ... FROM in older versions; use
        # a correlated subquery so test fixtures still apply.
        else sa.text(
            "UPDATE semantic_mappings "
            "SET product_id = ("
            "  SELECT cmc.product_id FROM cube_metadata_cache cmc "
            "  WHERE cmc.cube_id = semantic_mappings.cube_id"
            ") "
            "WHERE product_id IS NULL"
        )
    )

    # Step 3 — fail loudly if any rows still lack product_id. Mirrors
    # the ``d678f1a14d73`` precedent: better to halt the migration than
    # to silently fabricate a value.
    null_count = bind.execute(
        sa.text(
            "SELECT COUNT(*) FROM semantic_mappings WHERE product_id IS NULL"
        )
    ).scalar()
    if null_count and null_count > 0:
        raise RuntimeError(
            f"Cannot enforce NOT NULL on semantic_mappings.product_id: "
            f"{null_count} row(s) have NULL product_id after best-effort "
            f"backfill from cube_metadata_cache. Prime the cache for the "
            f"affected cube_id values (or delete the orphan rows) before "
            f"re-running this migration."
        )

    # Step 4 — enforce NOT NULL. batch_alter_table for SQLite compat.
    with op.batch_alter_table("semantic_mappings") as batch:
        batch.alter_column("product_id", existing_type=sa.BigInteger(), nullable=False)

    # Step 5 — index.
    op.create_index(
        "ix_semantic_mappings_product_id",
        "semantic_mappings",
        ["product_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_semantic_mappings_product_id",
        table_name="semantic_mappings",
    )
    op.drop_column("semantic_mappings", "product_id")
