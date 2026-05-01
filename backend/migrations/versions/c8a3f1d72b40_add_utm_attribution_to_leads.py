"""add utm attribution to leads

Revision ID: c8a3f1d72b40
Revises: d678f1a14d73
Create Date: 2026-04-30

Phase 2.3 UTM-to-lineage attribution. Adds nullable utm_* columns to
the leads table. Backfill not needed (existing rows pre-attribution).
Index on utm_content (= lineage_key) so per-publication lookup
(``WHERE utm_content = '<lineage_key>'``) is the primary access pattern.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "c8a3f1d72b40"
down_revision: Union[str, Sequence[str], None] = "d678f1a14d73"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("leads", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("utm_source", sa.String(length=100), nullable=True)
        )
        batch_op.add_column(
            sa.Column("utm_medium", sa.String(length=100), nullable=True)
        )
        batch_op.add_column(
            sa.Column("utm_campaign", sa.String(length=200), nullable=True)
        )
        batch_op.add_column(
            sa.Column("utm_content", sa.String(length=200), nullable=True)
        )

    op.create_index("ix_leads_utm_content", "leads", ["utm_content"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_leads_utm_content", table_name="leads")
    with op.batch_alter_table("leads", schema=None) as batch_op:
        batch_op.drop_column("utm_content")
        batch_op.drop_column("utm_campaign")
        batch_op.drop_column("utm_medium")
        batch_op.drop_column("utm_source")
