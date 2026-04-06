"""Add full-text search and trigram indexes to cube_catalog.

This migration uses PostgreSQL-specific features:
- pg_trgm extension for typo-tolerant similarity search
- Generated tsvector column with GIN index for full-text search
- Trigram GIN indexes on title_en and title_fr

These features are NOT available in SQLite. Unit tests that use
SQLite will work with the base table but without FTS capabilities.
The CubeCatalogRepository handles this with a fallback LIKE search
for SQLite (R11).
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '378407da6dfa'
down_revision = '6703b5b8dfa4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Skip on SQLite (unit tests)
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return

    # Enable pg_trgm extension
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # Add generated search_vector column
    # Weighted: title_en gets weight A (highest), subject_en gets weight B
    op.execute("""
        ALTER TABLE cube_catalog
        ADD COLUMN search_vector tsvector
        GENERATED ALWAYS AS (
            setweight(to_tsvector('english', coalesce(title_en, '')), 'A') ||
            setweight(to_tsvector('french', coalesce(title_fr, '')), 'A') ||
            setweight(to_tsvector('english', coalesce(subject_en, '')), 'B')
        ) STORED
    """)

    # GIN index on search_vector for fast full-text queries
    op.execute("""
        CREATE INDEX ix_cube_catalog_search_vector
        ON cube_catalog
        USING GIN (search_vector)
    """)

    # Trigram indexes for typo-tolerant similarity search
    op.execute("""
        CREATE INDEX ix_cube_catalog_title_en_trgm
        ON cube_catalog
        USING GIN (title_en gin_trgm_ops)
    """)

    op.execute("""
        CREATE INDEX ix_cube_catalog_title_fr_trgm
        ON cube_catalog
        USING GIN (title_fr gin_trgm_ops)
    """)


def downgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return

    op.execute("DROP INDEX IF EXISTS ix_cube_catalog_title_fr_trgm")
    op.execute("DROP INDEX IF EXISTS ix_cube_catalog_title_en_trgm")
    op.execute("DROP INDEX IF EXISTS ix_cube_catalog_search_vector")
    op.execute("ALTER TABLE cube_catalog DROP COLUMN IF EXISTS search_vector")
    # Note: we don't drop pg_trgm extension — it may be used elsewhere
