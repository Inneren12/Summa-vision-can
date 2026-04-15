"""add_editorial_and_visual_config_to_publication

Adds editorial fields (eyebrow, description, source_text, footnote) and a
JSON-serialised ``visual_config`` column to the ``publications`` table so
the public gallery can render rich editorial cards and the new in-house
editor can persist its layer configuration.

Also adds two lifecycle timestamps:

* ``updated_at`` — populated automatically by SQLAlchemy ``onupdate``.
* ``published_at`` — set by the application when the status flips from
  ``DRAFT`` to ``PUBLISHED``.

All new columns are ``nullable=True`` so existing rows remain valid and
no backfill is required.

Revision ID: e9b4f8a72c10
Revises: d7a1b2c3e4f5
Create Date: 2026-04-15 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e9b4f8a72c10"
down_revision: Union[str, Sequence[str], None] = "d7a1b2c3e4f5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema — add editorial + visual_config + timestamp columns."""
    with op.batch_alter_table("publications", schema=None) as batch_op:
        batch_op.add_column(sa.Column("eyebrow", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("description", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("source_text", sa.String(length=500), nullable=True))
        batch_op.add_column(sa.Column("footnote", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("visual_config", sa.Text(), nullable=True))
        batch_op.add_column(
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.add_column(
            sa.Column("published_at", sa.DateTime(timezone=True), nullable=True)
        )


def downgrade() -> None:
    """Downgrade schema — drop the columns added above."""
    with op.batch_alter_table("publications", schema=None) as batch_op:
        batch_op.drop_column("published_at")
        batch_op.drop_column("updated_at")
        batch_op.drop_column("visual_config")
        batch_op.drop_column("footnote")
        batch_op.drop_column("source_text")
        batch_op.drop_column("description")
        batch_op.drop_column("eyebrow")
