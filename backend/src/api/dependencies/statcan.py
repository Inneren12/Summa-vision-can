"""Shared FastAPI dependencies for StatCan-backed services.

Extracted in Phase 3.1b fix R1 to fix a per-request httpx connection pool
leak. Both ``admin_semantic_mappings`` and ``admin_cube_metadata`` routers
use this single dependency to construct
:class:`StatCanMetadataCacheService` with a properly-managed
``httpx.AsyncClient`` lifecycle (closed after request via ``async with``
+ ``yield``).

A long-lived lifespan-managed app.state client is the next iteration but
out of scope for this fix — see production hardening backlog.
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime, timezone

import httpx
import structlog
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.database import get_session_factory
from src.core.rate_limit import AsyncTokenBucket
from src.services.statcan.client import StatCanClient
from src.services.statcan.maintenance import StatCanMaintenanceGuard
from src.repositories.semantic_mapping_repository import (
    SemanticMappingRepository,
)
from src.repositories.semantic_value_cache_repository import (
    SemanticValueCacheRepository,
)
from src.services.statcan.metadata_cache import StatCanMetadataCacheService
from src.services.statcan.value_cache import StatCanValueCacheService


def _session_factory_dep() -> async_sessionmaker[AsyncSession]:
    return get_session_factory()


async def get_statcan_metadata_cache_service(
    session_factory: async_sessionmaker[AsyncSession] = Depends(
        _session_factory_dep
    ),
) -> AsyncIterator[StatCanMetadataCacheService]:
    """Yield a :class:`StatCanMetadataCacheService` with managed
    ``httpx.AsyncClient``.

    The client is created per-request and closed via ``async with`` on
    request teardown, preventing connection pool leaks.
    """
    async with httpx.AsyncClient(timeout=30.0) as http_client:
        client = StatCanClient(
            http_client,
            StatCanMaintenanceGuard(),
            AsyncTokenBucket(capacity=10, refill_rate=10.0),
        )
        service = StatCanMetadataCacheService(
            session_factory=session_factory,
            client=client,
            clock=lambda: datetime.now(timezone.utc),
            logger=structlog.get_logger(module="statcan.metadata_cache"),
        )
        yield service


async def get_statcan_value_cache_service(
    session_factory: async_sessionmaker[AsyncSession] = Depends(
        _session_factory_dep
    ),
) -> AsyncIterator[StatCanValueCacheService]:
    """Phase 3.1aaa: yield :class:`StatCanValueCacheService` with managed
    ``httpx.AsyncClient``.

    Mirrors :func:`get_statcan_metadata_cache_service` for lifecycle.
    The metadata cache it depends on is constructed inline against the
    same ``http_client`` so both share a single connection pool for
    the duration of the request.
    """
    async with httpx.AsyncClient(timeout=30.0) as http_client:
        client = StatCanClient(
            http_client,
            StatCanMaintenanceGuard(),
            AsyncTokenBucket(capacity=10, refill_rate=10.0),
        )
        metadata_cache = StatCanMetadataCacheService(
            session_factory=session_factory,
            client=client,
            clock=lambda: datetime.now(timezone.utc),
            logger=structlog.get_logger(module="statcan.metadata_cache"),
        )
        service = StatCanValueCacheService(
            session_factory=session_factory,
            repository_factory=lambda s: SemanticValueCacheRepository(s),
            mapping_repository_factory=lambda s: SemanticMappingRepository(s),
            cube_metadata_cache=metadata_cache,
            statcan_client=client,
            clock=lambda: datetime.now(timezone.utc),
            logger=structlog.get_logger(module="statcan.value_cache"),
        )
        yield service


__all__ = [
    "get_statcan_metadata_cache_service",
    "get_statcan_value_cache_service",
]
