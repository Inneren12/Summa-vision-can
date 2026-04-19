"""add_review_to_publication

Adds the ``review`` column to ``publications``: a nullable Text column
that stores the frontend ``CanonicalDocument.review`` subtree as a
JSON string (workflow state, workflow history, comments). Stored as
Text (not JSONB) for SQLite test compatibility, consistent with the
``visual_config`` column added in ``e9b4f8a72c10``.

Revision ID: f2a7d9c3b481
Revises: e9b4f8a72c10
Create Date: 2026-04-19 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f2a7d9c3b481"
down_revision: Union[str, Sequence[str], None] = "e9b4f8a72c10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema — add the nullable ``review`` column."""
    with op.batch_alter_table("publications", schema=None) as batch_op:
        batch_op.add_column(sa.Column("review", sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema — drop the ``review`` column."""
    with op.batch_alter_table("publications", schema=None) as batch_op:
        batch_op.drop_column("review")
