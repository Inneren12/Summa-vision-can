"""add cube_metadata_cache

Phase 3.1aa: persistent cache of StatCan cube metadata used by the
semantic mapping validator (3.1ab). The cache is populated on first
admin save (auto-prime) and refreshed nightly by an APScheduler cron
job (`statcan_metadata_cache_refresh`).

Revision ID: 2e15e3f4d1f2
Revises: f3b8c2e91a4d
Create Date: 2026-05-01
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "2e15e3f4d1f2"
down_revision: Union[str, Sequence[str], None] = "f3b8c2e91a4d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cube_metadata_cache",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("cube_id", sa.String(length=50), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column(
            "dimensions",
            postgresql.JSONB(astext_type=sa.Text()).with_variant(
                sa.JSON(), "sqlite"
            ),
            nullable=False,
        ),
        sa.Column("frequency_code", sa.String(length=8), nullable=True),
        sa.Column("cube_title_en", sa.String(length=255), nullable=True),
        sa.Column("cube_title_fr", sa.String(length=255), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
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
        sa.UniqueConstraint("cube_id", name="uq_cube_metadata_cache_cube_id"),
    )
    op.create_index(
        "ix_cube_metadata_cache_fetched_at",
        "cube_metadata_cache",
        ["fetched_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_cube_metadata_cache_fetched_at", table_name="cube_metadata_cache"
    )
    op.drop_table("cube_metadata_cache")
