"""Phase 3.1b admin read endpoint for the StatCan cube metadata cache.

Single endpoint:

* ``GET /api/v1/admin/cube-metadata/{cube_id}`` — default behaviour is a
  read-only cache lookup that returns 404 on miss. The hybrid
  ``?prime=true&product_id=N`` mode opts the operator into an
  auto-prime fetch (may hit StatCan) for cubes that are not yet cached.
  See DEBT-053 for the rationale behind the explicit opt-in.
"""
from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.database import get_db, get_session_factory
from src.core.logging import get_logger
from src.services.statcan.metadata_cache import (
    CubeMetadataCacheEntry,
    CubeMetadataProductMismatchError,
    CubeNotFoundError,
    StatCanMetadataCacheService,
    StatCanUnavailableError,
)

logger: structlog.stdlib.BoundLogger = get_logger(module="admin_cube_metadata")

router = APIRouter(
    prefix="/api/v1/admin/cube-metadata",
    tags=["admin", "cube-metadata"],
)


# ---------------------------------------------------------------------------
# Response model — minimal shape suitable for Flutter autocomplete UX
# ---------------------------------------------------------------------------


class CubeMetadataCacheEntryResponse(BaseModel):
    cube_id: str
    product_id: int
    dimensions: dict
    frequency_code: str | None
    cube_title_en: str | None
    cube_title_fr: str | None

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Dependency helpers (overridable in tests)
# ---------------------------------------------------------------------------


def _get_session_factory() -> async_sessionmaker[AsyncSession]:
    return get_session_factory()


def _get_metadata_cache_service(
    factory: async_sessionmaker[AsyncSession] = Depends(_get_session_factory),
) -> StatCanMetadataCacheService:
    """Per-request cache service. Tests override with an :class:`AsyncMock`."""
    from datetime import datetime, timezone

    import httpx

    from src.core.rate_limit import AsyncTokenBucket
    from src.services.statcan.client import StatCanClient
    from src.services.statcan.maintenance import StatCanMaintenanceGuard

    http_client = httpx.AsyncClient(timeout=30.0)
    client = StatCanClient(
        http_client,
        StatCanMaintenanceGuard(),
        AsyncTokenBucket(capacity=10, refill_rate=10.0),
    )
    return StatCanMetadataCacheService(
        session_factory=factory,
        client=client,
        clock=lambda: datetime.now(timezone.utc),
        logger=structlog.get_logger(module="statcan.metadata_cache"),
    )


# ---------------------------------------------------------------------------
# GET /{cube_id}
# ---------------------------------------------------------------------------


@router.get(
    "/{cube_id}",
    response_model=CubeMetadataCacheEntryResponse,
    status_code=status.HTTP_200_OK,
    summary="Read cached cube metadata (autocomplete source)",
    responses={
        200: {"description": "Cache entry found."},
        400: {"description": "prime=true requires product_id query param."},
        401: {"description": "Missing or invalid X-API-KEY."},
        404: {
            "description": (
                "Cube not in cache. Use ?prime=true&product_id=N to "
                "fetch from StatCan."
            )
        },
        503: {"description": "StatCan unreachable while priming."},
    },
)
async def get_cube_metadata(
    cube_id: str,
    prime: bool = Query(
        default=False,
        description=(
            "If true, fetch from StatCan on cache miss (auto-prime). "
            "Requires ``product_id`` query param. See DEBT-053."
        ),
    ),
    product_id: int | None = Query(
        default=None,
        ge=1,
        description=(
            "StatCan numeric product id. Required when ``prime=true`` "
            "(option A in the recon § F2 question)."
        ),
    ),
    service: StatCanMetadataCacheService = Depends(_get_metadata_cache_service),
) -> CubeMetadataCacheEntryResponse:
    if prime:
        if product_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error_code": "PRIME_REQUIRES_PRODUCT_ID",
                    "message": (
                        "?prime=true requires product_id query param so "
                        "the cache can fetch from StatCan."
                    ),
                },
            )
        try:
            entry = await service.get_or_fetch(cube_id, product_id)
        except StatCanUnavailableError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "error_code": "STATCAN_UNAVAILABLE",
                    "message": str(exc),
                },
            ) from exc
        except CubeNotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error_code": "CUBE_NOT_IN_CACHE",
                    "message": str(exc),
                },
            ) from exc
        except CubeMetadataProductMismatchError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error_code": "CUBE_PRODUCT_MISMATCH",
                    "message": str(exc),
                    "details": {
                        "cube_id": exc.cube_id,
                        "expected_product_id": exc.expected_product_id,
                        "actual_product_id": exc.actual_product_id,
                    },
                },
            ) from exc
    else:
        entry = await service.get_cached(cube_id)
        if entry is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error_code": "CUBE_NOT_IN_CACHE",
                    "message": (
                        f"Cube {cube_id!r} not in cache. "
                        f"Use ?prime=true&product_id=N to fetch from StatCan."
                    ),
                },
            )

    return _serialize(entry)


def _serialize(entry: CubeMetadataCacheEntry) -> CubeMetadataCacheEntryResponse:
    return CubeMetadataCacheEntryResponse(
        cube_id=entry.cube_id,
        product_id=entry.product_id,
        dimensions=entry.dimensions,
        frequency_code=entry.frequency_code,
        cube_title_en=entry.cube_title_en,
        cube_title_fr=entry.cube_title_fr,
    )


_ = get_db  # keep import used for parity with sibling routers


__all__ = ["router", "CubeMetadataCacheEntryResponse"]
