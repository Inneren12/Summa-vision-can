"""Drop llm_requests table (dead LLM infrastructure cleanup).

Revision ID: c4d8e1f23a01
Revises: a1c3f7d82e09
Create Date: 2026-04-12
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4d8e1f23a01"
down_revision: Union[str, Sequence[str], None] = "a1c3f7d82e09"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(sa.text("DROP TABLE IF EXISTS llm_requests"))


def downgrade() -> None:
    # The original table was created in 05de14ff39c6_initial.py.
    # Re-creating it here is intentionally omitted — the LLM feature
    # has been removed and the model no longer exists in the codebase.
    pass
