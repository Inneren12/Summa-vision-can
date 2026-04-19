"""add document_state to publication

Opaque full-canonical-document column introduced to close DEBT-026.
``document_state`` stores the serialised editor ``CanonicalDocument`` so
block-level edits (chart data, layout, per-block props) round-trip
losslessly across save/reload. Backend treats the column opaquely —
the frontend's ``validateImportStrict`` owns shape validation.

Stored as ``Text`` (not JSONB) for SQLite compatibility, matching the
existing ``review`` and ``visual_config`` columns.

Revision ID: a3e81c0f5d21
Revises: f2a7d9c3b481
Create Date: 2026-04-19 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a3e81c0f5d21"
down_revision: Union[str, Sequence[str], None] = "f2a7d9c3b481"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema — add the nullable ``document_state`` column."""
    with op.batch_alter_table("publications", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("document_state", sa.Text(), nullable=True)
        )


def downgrade() -> None:
    """Downgrade schema — drop the ``document_state`` column."""
    with op.batch_alter_table("publications", schema=None) as batch_op:
        batch_op.drop_column("document_state")
