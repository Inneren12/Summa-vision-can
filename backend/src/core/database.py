"""Async database engine, session factory, and FastAPI dependency.

Connects to PostgreSQL via ``DATABASE_URL`` from application settings.
SQLite is NOT supported as a runtime database — it is used only in
unit test fixtures.

Architecture note:
    Route handlers receive ``AsyncSession`` via dependency injection.
    They must never create their own engine or session.
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

_engine = None
_session_factory = None


def get_engine():
    global _engine
    if _engine is None:
        _settings = get_settings()
        _engine = create_async_engine(
            _settings.database_url,
            echo=_settings.debug,
            pool_size=8,
            max_overflow=8,
            pool_pre_ping=True,
        )
    return _engine


def get_session_factory():
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


__all__ = ["Base", "get_engine", "get_session_factory", "get_db"]


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
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
