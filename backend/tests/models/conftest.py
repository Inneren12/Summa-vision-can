import os
import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from src.core.database import Base

@pytest.fixture
async def pg_session():
    """PostgreSQL session for integration tests.

    Requires PostgreSQL to be available (e.g. via docker-compose
    or GitHub Actions services block).
    """
    pg_url = os.environ.get("TEST_DATABASE_URL")
    if not pg_url or "sqlite" in pg_url:
        pytest.skip("TEST_DATABASE_URL not set to PostgreSQL — skipping PG integration test")

    engine = create_async_engine(pg_url)
    async with engine.begin() as conn:
        # We need to run migrations to get the FTS features
        await conn.run_sync(Base.metadata.create_all)

        # Add the trigram extension for testing
        await conn.execute(sa.text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))

        # Add the generated search_vector column since Base.metadata.create_all doesn't run our raw SQL migrations
        await conn.execute(sa.text("""
            ALTER TABLE cube_catalog
            ADD COLUMN IF NOT EXISTS search_vector tsvector
            GENERATED ALWAYS AS (
                setweight(to_tsvector('english', coalesce(title_en, '')), 'A') ||
                setweight(to_tsvector('english', coalesce(subject_en, '')), 'B')
            ) STORED
        """))

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
