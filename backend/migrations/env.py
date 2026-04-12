"""Alembic async migration environment.

Configures Alembic to use the Summa Vision ``Base.metadata`` for
autogenerate support and reads the ``DATABASE_URL`` from application
settings so that ``alembic.ini`` does not need to contain credentials.

To generate the initial migration::

    alembic revision --autogenerate -m "initial schema"

To apply migrations::

    alembic upgrade head
"""

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# ---------------------------------------------------------------------------
# Import our models so that Base.metadata is fully populated
# ---------------------------------------------------------------------------
from src.core.database import Base  # noqa: F401
from src.models import Lead, Publication  # noqa: F401
from src.core.config import get_settings

# ---------------------------------------------------------------------------
# Alembic Config object – provides access to .ini values
# ---------------------------------------------------------------------------

config = context.config

# Override sqlalchemy.url from application settings when available
_settings = get_settings()
if _settings.database_url:
    config.set_main_option("sqlalchemy.url", _settings.database_url)

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Wire up our metadata for autogenerate support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    Configures the context with just a URL and not an Engine,
    so that a DBAPI is not required to be available.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Configure and run migrations inside a synchronous connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create an async engine and run migrations."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
