"""add_editorial_and_visual_config_to_publication

Adds 7 new nullable columns to the ``publications`` table:

Editorial fields (4):
    * ``eyebrow``      — String(255), Optional kicker line.
    * ``description``  — Text, Optional gallery-card description.
    * ``source_text``  — String(500), Optional source attribution.
    * ``footnote``     — Text, Optional methodology / caveat.

Visual configuration (1):
    * ``visual_config`` — Text (JSON-serialised editor layer config).

Lifecycle timestamps (2):
    * ``updated_at``   — DateTime(tz), populated automatically by
      SQLAlchemy ``onupdate``.
    * ``published_at`` — DateTime(tz), set by the application when the
      status flips from ``DRAFT`` to ``PUBLISHED``.

All 7 new columns are ``nullable=True`` so existing rows remain valid
and no backfill is required. Together they power the public gallery
(editorial cards) and the in-house editor (layer persistence).

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
