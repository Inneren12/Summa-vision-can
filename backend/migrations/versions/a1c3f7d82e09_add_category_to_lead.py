"""add_category_to_lead

Revision ID: a1c3f7d82e09
Revises: 421cd0e25873
Create Date: 2026-04-12 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1c3f7d82e09'
down_revision: Union[str, Sequence[str], None] = '421cd0e25873'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('leads', sa.Column('category', sa.String(20), nullable=True))
    op.create_index('ix_leads_category', 'leads', ['category'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_leads_category', table_name='leads')
    op.drop_column('leads', 'category')
