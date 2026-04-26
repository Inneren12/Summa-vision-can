"""add cloned_from_publication_id to publication

Revision ID: b4f9a21c8d77
Revises: a3e81c0f5d21
Create Date: 2026-04-26 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b4f9a21c8d77"
down_revision: Union[str, Sequence[str], None] = "a3e81c0f5d21"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "publications",
        sa.Column(
            "cloned_from_publication_id",
            sa.Integer(),
            sa.ForeignKey("publications.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_publications_cloned_from_publication_id",
        "publications",
        ["cloned_from_publication_id"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_publications_cloned_from_publication_id",
        table_name="publications",
    )
    op.drop_column("publications", "cloned_from_publication_id")
