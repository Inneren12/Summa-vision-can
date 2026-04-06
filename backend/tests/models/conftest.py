import os
import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from src.core.database import Base

@pytest.fixture
async def pg_session():
    """PostgreSQL session for integration tests.

    Creates base schema via ORM, then applies PG-specific FTS
    features via raw SQL because Alembic programmatic usage is currently
    blocked by module-level engine creation.
    """
    pg_url = os.environ.get("TEST_DATABASE_URL")
    if not pg_url or "sqlite" in pg_url:
        pytest.skip("TEST_DATABASE_URL not set to PostgreSQL — skipping PG integration test")

    engine = create_async_engine(pg_url, echo=False)

    from src.core.database import Base
    from sqlalchemy import text

    # Create base schema from ORM metadata
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Apply PG-specific FTS features that exist only in migration SQL
    async with engine.begin() as conn:
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS pg_trgm'))
        await conn.execute(text('''
            ALTER TABLE cube_catalog
            ADD COLUMN IF NOT EXISTS search_vector tsvector
            GENERATED ALWAYS AS (
                setweight(to_tsvector('english', coalesce(title_en, '')), 'A') ||
                setweight(to_tsvector('french', coalesce(title_fr, '')), 'A') ||
                setweight(to_tsvector('english', coalesce(subject_en, '')), 'B')
            ) STORED
        '''))
        await conn.execute(text('''
            CREATE INDEX IF NOT EXISTS ix_cube_catalog_search_vector
            ON cube_catalog USING GIN (search_vector)
        '''))
        await conn.execute(text('''
            CREATE INDEX IF NOT EXISTS ix_cube_catalog_title_en_trgm
            ON cube_catalog USING GIN (title_en gin_trgm_ops)
        '''))
        await conn.execute(text('''
            CREATE INDEX IF NOT EXISTS ix_cube_catalog_title_fr_trgm
            ON cube_catalog USING GIN (title_fr gin_trgm_ops)
        '''))

    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        yield session

    # Cleanup: drop all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
