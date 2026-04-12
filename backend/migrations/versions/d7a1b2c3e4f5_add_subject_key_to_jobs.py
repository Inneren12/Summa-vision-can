"""add_subject_key_to_jobs

Revision ID: d7a1b2c3e4f5
Revises: c4d8e1f23a01
Create Date: 2026-04-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d7a1b2c3e4f5"
down_revision: Union[str, Sequence[str], None] = "c4d8e1f23a01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add subject_key column to jobs table for cooldown queries."""
    op.add_column("jobs", sa.Column("subject_key", sa.String(255), nullable=True))
    op.create_index("ix_jobs_subject_key", "jobs", ["subject_key"])


def downgrade() -> None:
    """Remove subject_key column from jobs table."""
    op.drop_index("ix_jobs_subject_key", table_name="jobs")
    op.drop_column("jobs", "subject_key")
