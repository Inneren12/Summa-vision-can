"""enforce slug not null unique

Revision ID: d678f1a14d73
Revises: 77889c0ea7e3
Create Date: 2026-04-30

Phase 2.2.0.5 backend slug infrastructure — Part 2.
Enforces NOT NULL and UNIQUE constraints on publications.slug column.
This is the second half of the expand-contract sequence; runs after
Chunks 2-4 deployed and write paths populate slug for all new rows.

OPS NOTE: do not downgrade in production after Phase 2.2 frontend ships.
Slug is the public URL path; column drop or revert breaks inbound links.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "d678f1a14d73"
down_revision: Union[str, Sequence[str], None] = "77889c0ea7e3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Precheck: any NULL or duplicate slugs at this point indicate
    # write-path drift between Chunks 2-4 deploy and this migration.
    # Failing loudly is better than silently corrupting URL identity.
    bind = op.get_bind()

    null_count = bind.execute(
        sa.text("SELECT COUNT(*) FROM publications WHERE slug IS NULL")
    ).scalar()
    if null_count and null_count > 0:
        raise RuntimeError(
            f"Cannot enforce NOT NULL: {null_count} rows have NULL slug. "
            f"Investigate write paths and backfill before re-running."
        )

    dup_count = bind.execute(
        sa.text(
            "SELECT COUNT(*) FROM ("
            "SELECT slug FROM publications WHERE slug IS NOT NULL "
            "GROUP BY slug HAVING COUNT(*) > 1"
            ") AS dups"
        )
    ).scalar()
    if dup_count and dup_count > 0:
        raise RuntimeError(
            f"Cannot enforce UNIQUE: {dup_count} duplicate slug groups. "
            f"Resolve duplicates before re-running."
        )

    with op.batch_alter_table("publications", schema=None) as batch_op:
        batch_op.alter_column(
            "slug",
            existing_type=sa.String(length=200),
            nullable=False,
        )
        batch_op.create_unique_constraint("uq_publications_slug", ["slug"])


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("publications", schema=None) as batch_op:
        batch_op.drop_constraint("uq_publications_slug", type_="unique")
        batch_op.alter_column(
            "slug",
            existing_type=sa.String(length=200),
            nullable=True,
        )
