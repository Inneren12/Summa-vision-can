"""phase 3.1d: publication_block_snapshot table

Phase 3.1d: snapshot persistence for publish-time freshness capture +
admin-only staleness comparison. See ``docs/recon/phase-3-1d-recon.md``
§2.1 for the locked column types and constraints.

Revision ID: 3d1d5a17abcd
Revises: 478d906c6410
Create Date: 2026-05-04
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "3d1d5a17abcd"
down_revision: Union[str, Sequence[str], None] = "478d906c6410"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "publication_block_snapshot",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "publication_id",
            sa.Integer(),
            sa.ForeignKey("publications.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("block_id", sa.String(length=128), nullable=False),
        sa.Column("cube_id", sa.String(length=50), nullable=False),
        sa.Column("semantic_key", sa.String(length=200), nullable=False),
        sa.Column("coord", sa.String(length=50), nullable=False),
        sa.Column("period", sa.String(length=20), nullable=True),
        sa.Column(
            "dims_json",
            postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite"),
            nullable=False,
        ),
        sa.Column(
            "members_json",
            postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite"),
            nullable=False,
        ),
        sa.Column("mapping_version_at_publish", sa.Integer(), nullable=True),
        sa.Column("source_hash_at_publish", sa.String(length=64), nullable=False),
        sa.Column("value_at_publish", sa.Text(), nullable=True),
        sa.Column("missing_at_publish", sa.Boolean(), nullable=False),
        sa.Column("is_stale_at_publish", sa.Boolean(), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "publication_id",
            "block_id",
            name="uq_publication_block_snapshot_pub_block",
        ),
    )
    op.create_index(
        "ix_publication_block_snapshot_publication_id",
        "publication_block_snapshot",
        ["publication_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_publication_block_snapshot_publication_id",
        table_name="publication_block_snapshot",
    )
    op.drop_table("publication_block_snapshot")
