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

from src.api.dependencies.statcan import get_statcan_metadata_cache_service
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
    service: StatCanMetadataCacheService = Depends(get_statcan_metadata_cache_service),
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


__all__ = ["router", "CubeMetadataCacheEntryResponse"]
