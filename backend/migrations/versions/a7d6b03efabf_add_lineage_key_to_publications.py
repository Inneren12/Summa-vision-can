"""add lineage_key to publications

Revision ID: a7d6b03efabf
Revises: b4f9a21c8d77
Create Date: 2026-04-28 12:00:00.000000

Phase 2.2.0 backend lineage_key infrastructure. Adds nullable column,
backfills existing rows by walking the cloned_from_publication_id graph
in id-ascending order, then enforces NOT NULL + adds index. Atomic
within one revision so a mid-backfill failure rolls cleanly.

OPS NOTE: lineage_keys are NOT stable across down -> up cycles. Once
Phase 2.3 starts logging ?utm_content=<lineage_key> on lead funnels,
downgrading and re-upgrading this migration regenerates fresh root
keys, orphaning historical UTM data. Do NOT downgrade once Phase 2.3
ships. Tracked in DEBT.md (Phase 2.2.0 ops-runbook entry).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "a7d6b03efabf"
down_revision: Union[str, Sequence[str], None] = "b4f9a21c8d77"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Step 1: add nullable column (batch_alter_table for SQLite portability)
    with op.batch_alter_table("publications", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("lineage_key", sa.String(length=36), nullable=True),
        )

    # Step 2: backfill via Python loop (UUID v7 unavailable in pure SQL)
    _backfill_lineage_keys()

    # Step 3: enforce NOT NULL after backfill + index for Phase 2.3
    # attribution queries. Wrapped in batch so SQLite copy-and-move
    # picks up both changes in one rebuild.
    with op.batch_alter_table("publications", schema=None) as batch_op:
        batch_op.alter_column(
            "lineage_key",
            existing_type=sa.String(length=36),
            nullable=False,
        )
        batch_op.create_index(
            "ix_publications_lineage_key",
            ["lineage_key"],
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("publications", schema=None) as batch_op:
        batch_op.drop_index("ix_publications_lineage_key")
        batch_op.drop_column("lineage_key")


def _backfill_lineage_keys() -> None:
    """Walk publications by id ASC. Roots get fresh uuid7. Clones inherit
    lineage_key from parent.

    Business invariant: clones are created via auto-increment PK after
    their source row exists, so clone.id > parent.id and the parent's
    lineage_key is already in ``key_by_id`` by the time the loop reaches
    the clone. This invariant is enforced by application logic, not by a
    DB constraint. If the invariant is violated (e.g. legacy or manually
    inserted data where clone.id < parent.id), the affected clone falls
    into the ``else`` branch and receives a fresh lineage_key — treated
    as an orphan root rather than an exception.
    """
    try:
        from uuid import uuid7  # type: ignore[attr-defined]  # Python 3.13+ stdlib
    except ImportError:
        from uuid_utils import uuid7  # uuid-utils package

    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            "SELECT id, cloned_from_publication_id "
            "FROM publications ORDER BY id ASC"
        )
    ).fetchall()

    key_by_id: dict[int, str] = {}
    for row in rows:
        pub_id = row.id
        parent_id = row.cloned_from_publication_id
        if parent_id is not None and parent_id in key_by_id:
            key = key_by_id[parent_id]
        else:
            # Root, OR orphaned clone (parent hard-deleted via SET NULL)
            key = str(uuid7())
        key_by_id[pub_id] = key
        bind.execute(
            sa.text(
                "UPDATE publications SET lineage_key = :k WHERE id = :i"
            ),
            {"k": key, "i": pub_id},
        )
