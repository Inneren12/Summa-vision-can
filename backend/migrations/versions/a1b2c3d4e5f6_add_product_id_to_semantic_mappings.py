"""add product_id to semantic_mappings

Revision ID: a1b2c3d4e5f6
Revises: 2e15e3f4d1f2
Create Date: 2026-05-02 00:00:00.000000

Phase 3.1b R3 — reviewer P1 fix.

Persists ``product_id`` on ``semantic_mappings`` so the admin edit flow can
hydrate the form from the row alone (no separate cache lookup). Production
has 0 rows at this revision, so adding the column NOT NULL is safe with
no backfill.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "2e15e3f4d1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "semantic_mappings",
        sa.Column("product_id", sa.BigInteger(), nullable=False),
    )
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
