"""Async database engine, session factory, and FastAPI dependency.

This module sets up the SQLAlchemy 2.0 async engine and session maker.
The ``DATABASE_URL`` is read from the application settings (via
``pydantic-settings``).  When the variable is empty or not set, it falls
back to a local SQLite file for development.

Usage in FastAPI routes::

    from src.core.database import get_db

    @router.get("/items")
    async def list_items(session: AsyncSession = Depends(get_db)):
        ...

Architecture note:
    Route handlers (and services) receive an ``AsyncSession`` via
    dependency injection.  They must **never** create their own engine or
    session – this module is the single source of truth for DB wiring.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from src.core.config import get_settings

# ---------------------------------------------------------------------------
# Declarative Base
# ---------------------------------------------------------------------------


class Base(AsyncAttrs, DeclarativeBase):
    """Base class for all ORM models.

    Inherits from :class:`AsyncAttrs` so that lazy-loaded relationships
    work transparently in async contexts, and from
    :class:`DeclarativeBase` to provide the registry and metadata.
    """


# ---------------------------------------------------------------------------
# Engine & session factory
# ---------------------------------------------------------------------------

_settings = get_settings()

DATABASE_URL: str = (
    _settings.database_url
    if _settings.database_url
    else "sqlite+aiosqlite:///./summa.db"
)

engine = create_async_engine(
    DATABASE_URL,
    echo=_settings.debug,
    # Required for SQLite — ignored by PostgreSQL drivers.
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)

async_session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an ``AsyncSession`` and guarantee it is closed after use.

    Intended to be used as a **FastAPI Depends** dependency::

        session: AsyncSession = Depends(get_db)

    The session is committed automatically on successful completion;
    any exception triggers a rollback before the session is closed.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
