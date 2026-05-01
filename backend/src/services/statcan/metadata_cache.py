"""Phase 3.1aa: ``StatCanMetadataCacheService``.

Persistent cache of StatCan cube metadata used by the semantic mapping
validator (3.1ab) in cache-required mode. Populated either on first
admin save (auto-prime via :meth:`get_or_fetch`) or by the nightly
scheduler refresh job; never directly by a user-facing endpoint.

Architecture notes
------------------
* **R6 — short-lived sessions:** the service holds a
  ``async_sessionmaker`` factory and opens one session per call. It
  never holds a session across awaits at module scope.
* **ARCH-DPEN-001 — DI:** every collaborator (session factory, client,
  clock, logger) is injected through ``__init__``.
* **ARCH-PURA-001 — pure helpers:** :func:`normalize_dimensions` is a
  pure function with no I/O / clock / logger dependency.
* **DTO at the service boundary:** repository returns ORM objects;
  this service converts them into the immutable
  :class:`CubeMetadataCacheEntry` dataclass before returning.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

import structlog
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.exceptions import DataSourceError
from src.repositories.cube_metadata_cache_repository import (
    CubeMetadataCacheRepository,
)
from src.services.statcan.client import StatCanClient
from src.services.statcan.schemas import CubeMetadataResponse


# ---------------------------------------------------------------------------
# DTOs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CubeMetadataCacheEntry:
    """Immutable view of a single ``cube_metadata_cache`` row."""

    cube_id: str
    product_id: int
    dimensions: dict
    frequency_code: str | None
    cube_title_en: str | None
    cube_title_fr: str | None
    fetched_at: datetime


@dataclass(frozen=True)
class RefreshSummary:
    """Aggregate result of a stale-sweep refresh pass."""

    refreshed: int
    failed: int
    skipped: int


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class MetadataCacheError(Exception):
    """Base class for cache-service errors."""


class CubeNotFoundError(MetadataCacheError):
    """StatCan returned no metadata envelope for the requested ``productId``."""

    def __init__(self, *, cube_id: str, product_id: int) -> None:
        super().__init__(
            f"StatCan returned no metadata for cube_id={cube_id!r} "
            f"product_id={product_id}"
        )
        self.cube_id = cube_id
        self.product_id = product_id


class StatCanUnavailableError(MetadataCacheError):
    """StatCan is unreachable AND no cached row is available."""

    def __init__(self, *, cube_id: str) -> None:
        super().__init__(
            f"StatCan unavailable and no cache row for cube_id={cube_id!r}"
        )
        self.cube_id = cube_id


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def normalize_dimensions(payload: CubeMetadataResponse) -> dict:
    """Project a :class:`CubeMetadataResponse` into the cached JSONB shape.

    Pure function — no I/O, no clock, no logger.
    """
    dims: list[dict] = []
    for dim in payload.dimensions:
        members = [
            {
                "member_id": m.member_id,
                "name_en": m.member_name_en,
                "name_fr": m.member_name_fr,
            }
            for m in dim.members
        ]
        dims.append(
            {
                "position_id": dim.dimension_position_id,
                "name_en": dim.dimension_name_en,
                "name_fr": dim.dimension_name_fr,
                "has_uom": dim.has_uom,
                "members": members,
            }
        )
    return {"dimensions": dims}


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class StatCanMetadataCacheService:
    """Cache facade in front of ``getCubeMetadata`` for the validator."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        client: StatCanClient,
        clock: Callable[[], datetime],
        logger: structlog.stdlib.BoundLogger,
    ) -> None:
        self._session_factory = session_factory
        self._client = client
        self._clock = clock
        self._logger = logger

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    async def get_cached(self, cube_id: str) -> CubeMetadataCacheEntry | None:
        """Pure cache read. Returns ``None`` on miss; never calls StatCan."""
        async with self._session_factory() as session:
            repo = CubeMetadataCacheRepository(session)
            row = await repo.get_by_cube_id(cube_id)
        return _to_dto(row) if row is not None else None

    # ------------------------------------------------------------------
    # Read-through
    # ------------------------------------------------------------------

    async def get_or_fetch(
        self, cube_id: str, product_id: int
    ) -> CubeMetadataCacheEntry:
        """Cache-hit → return; cache-miss → fetch + persist; race-safe.

        Raises
        ------
        StatCanUnavailableError
            On cache miss when the StatCan API is unreachable.
        CubeNotFoundError
            On cache miss when StatCan responds without a SUCCESS envelope.
        """
        async with self._session_factory() as session:
            repo = CubeMetadataCacheRepository(session)
            cached = await repo.get_by_cube_id(cube_id)
        if cached is not None:
            return _to_dto(cached)

        try:
            payload = await self._client.get_cube_metadata(product_id)
        except DataSourceError as exc:
            raise StatCanUnavailableError(cube_id=cube_id) from exc

        if payload is None:
            raise CubeNotFoundError(cube_id=cube_id, product_id=product_id)

        return await self._persist(cube_id, product_id, payload)

    # ------------------------------------------------------------------
    # Force refresh
    # ------------------------------------------------------------------

    async def refresh(
        self,
        cube_id: str,
        product_id: int,
        *,
        force: bool = False,
    ) -> CubeMetadataCacheEntry:
        """Always fetch from StatCan and upsert.

        ``force`` is reserved for future invalidation paths (DEBT-045)
        and is currently a no-op flag — the method always fetches.

        Raises
        ------
        StatCanUnavailableError
            When the StatCan API is unreachable. No cache fallback.
        CubeNotFoundError
            When StatCan responds without a SUCCESS envelope.
        """
        del force  # reserved for DEBT-045 (event-driven invalidation)

        try:
            payload = await self._client.get_cube_metadata(product_id)
        except DataSourceError as exc:
            raise StatCanUnavailableError(cube_id=cube_id) from exc

        if payload is None:
            raise CubeNotFoundError(cube_id=cube_id, product_id=product_id)

        return await self._persist(cube_id, product_id, payload)

    # ------------------------------------------------------------------
    # Stale sweep
    # ------------------------------------------------------------------

    async def refresh_all_stale(
        self, stale_after: timedelta
    ) -> RefreshSummary:
        """Refresh every cached row whose ``fetched_at`` is older than
        ``stale_after`` ago. Per-cube errors are caught and counted."""
        threshold = self._clock() - stale_after

        async with self._session_factory() as session:
            repo = CubeMetadataCacheRepository(session)
            stale_rows = await repo.list_stale(before=threshold)

        targets = [(row.cube_id, row.product_id) for row in stale_rows]
        self._logger.info(
            "metadata_cache.refresh_all_stale.started",
            stale_count=len(targets),
            threshold=threshold.isoformat(),
        )

        refreshed = 0
        failed = 0
        for cube_id, product_id in targets:
            try:
                await self.refresh(cube_id, product_id)
                refreshed += 1
            except Exception as exc:  # noqa: BLE001
                failed += 1
                self._logger.warning(
                    "metadata_cache.refresh_all_stale.cube_failed",
                    cube_id=cube_id,
                    product_id=product_id,
                    error=str(exc),
                )

        summary = RefreshSummary(refreshed=refreshed, failed=failed, skipped=0)
        self._logger.info(
            "metadata_cache.refresh_all_stale.completed",
            refreshed=summary.refreshed,
            failed=summary.failed,
            skipped=summary.skipped,
        )
        return summary

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    async def _persist(
        self,
        cube_id: str,
        product_id: int,
        payload: CubeMetadataResponse,
    ) -> CubeMetadataCacheEntry:
        """Upsert the normalized payload, surviving a concurrent insert."""
        normalized = normalize_dimensions(payload)
        fetched_at = self._clock()
        frequency_code = (
            str(payload.frequency_code)
            if payload.frequency_code is not None
            else None
        )

        async with self._session_factory() as session:
            repo = CubeMetadataCacheRepository(session)
            try:
                entity, _changed = await repo.upsert(
                    cube_id=cube_id,
                    product_id=product_id,
                    dimensions=normalized,
                    frequency_code=frequency_code,
                    cube_title_en=payload.cube_title_en,
                    cube_title_fr=payload.cube_title_fr,
                    fetched_at=fetched_at,
                )
                await session.commit()
            except IntegrityError:
                # Concurrent INSERT won the race — read the final row.
                await session.rollback()
                entity = await repo.get_by_cube_id(cube_id)
                if entity is None:
                    raise

        return _to_dto(entity)


def _to_dto(row) -> CubeMetadataCacheEntry:
    """Convert an ORM row into the immutable service-boundary DTO."""
    return CubeMetadataCacheEntry(
        cube_id=row.cube_id,
        product_id=row.product_id,
        dimensions=row.dimensions,
        frequency_code=row.frequency_code,
        cube_title_en=row.cube_title_en,
        cube_title_fr=row.cube_title_fr,
        fetched_at=row.fetched_at,
    )
