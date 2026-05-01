"""add semantic mappings

Phase 3.1a: DB-backed semantic layer foundation. Operator-facing mappings
from cube cells (cube_id + dimension_filters) to semantic keys
(e.g. "cpi.canada.all_items.index"). Source of truth for the semantic
layer; YAML used only as seed/import format.

Validator and admin endpoints land in 3.1ab and 3.1b respectively.

Revision ID: f3b8c2e91a4d
Revises: c8a3f1d72b40
Create Date: 2026-04-30
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f3b8c2e91a4d"
down_revision: Union[str, Sequence[str], None] = "c8a3f1d72b40"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "semantic_mappings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("cube_id", sa.String(length=50), nullable=False),
        sa.Column("semantic_key", sa.String(length=200), nullable=False),
        sa.Column("label", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "config",
            postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
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
        sa.Column("updated_by", sa.String(length=100), nullable=True),
        sa.UniqueConstraint(
            "cube_id", "semantic_key", name="uq_semantic_mappings_cube_key"
        ),
    )
    op.create_index(
        "ix_semantic_mappings_cube_active",
        "semantic_mappings",
        ["cube_id", "is_active"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_semantic_mappings_cube_active", table_name="semantic_mappings"
    )
    op.drop_table("semantic_mappings")
