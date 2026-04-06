import os
import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from src.core.database import Base

@pytest.fixture
async def pg_session():
    """PostgreSQL session with schema applied via Alembic migrations.

    This ensures we test against the REAL production schema,
    including partial indexes, generated columns, and FTS indexes
    that are defined in migration SQL, not in SQLAlchemy metadata.
    """
    pg_url = os.environ.get("TEST_DATABASE_URL")
    if not pg_url or "sqlite" in pg_url:
        pytest.skip("TEST_DATABASE_URL not set to PostgreSQL — skipping PG integration test")

    from alembic.config import Config
    from alembic import command

    alembic_cfg = Config(os.path.join(os.path.dirname(__file__), "..", "..", "alembic.ini"))
    alembic_cfg.set_main_option("sqlalchemy.url", pg_url.replace("+asyncpg", ""))
    alembic_cfg.set_main_option("script_location", os.path.join(os.path.dirname(__file__), "..", "..", "migrations"))
    command.upgrade(alembic_cfg, "head")

    engine = create_async_engine(pg_url, echo=False)
    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        yield session

    # Cleanup: drop all tables
    from src.core.database import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
