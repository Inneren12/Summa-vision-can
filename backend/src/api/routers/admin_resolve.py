"""Phase 3.1c — admin resolve router.

Singular endpoint:

    GET /api/v1/admin/resolve/{cube_id}/{semantic_key}

Auth: inherits :class:`AuthMiddleware` X-API-KEY enforcement (R3).
Error envelope: flat handler-detail style consistent with
:mod:`src.api.routers.admin_semantic_mappings` (R2).

The handler is intentionally thin — all business logic lives in
:class:`ResolveService`. The handler ONLY:

    * declares Path / Query params (recon §2.2 / §2.3);
    * zips raw ``dim`` / ``member`` query lists into pairs;
    * forwards to the service;
    * translates typed exceptions into HTTP envelopes.

Per recon §5.1 invariants, the handler MUST NOT call ``derive_coord``
(that's the service's job — C3 keeps coord derivation centralised).
"""
from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.api.dependencies.statcan import (
    get_statcan_metadata_cache_service,
    get_statcan_value_cache_service,
)
from src.core.database import get_session_factory
from src.core.error_codes import (
    MAPPING_NOT_FOUND,
    RESOLVE_CACHE_MISS,
    RESOLVE_INVALID_FILTERS,
)
from src.core.logging import get_logger
from src.repositories.semantic_mapping_repository import (
    SemanticMappingRepository,
)
from src.schemas.resolve import ResolvedValueResponse
from src.services.resolve.exceptions import (
    MappingNotFoundForResolveError,
    ResolveCacheMissError,
    ResolveInvalidFiltersError,
)
from src.services.resolve.service import ResolveService
from src.services.statcan.metadata_cache import StatCanMetadataCacheService
from src.services.statcan.value_cache import StatCanValueCacheService


logger: structlog.stdlib.BoundLogger = get_logger(module="admin_resolve")


router = APIRouter(
    prefix="/api/v1/admin/resolve",
    tags=["admin-resolve"],
)


# ---------------------------------------------------------------------------
# Dependency helpers
# ---------------------------------------------------------------------------


def _get_session_factory_dep() -> async_sessionmaker[AsyncSession]:
    return get_session_factory()


def _get_resolve_service(
    factory: async_sessionmaker[AsyncSession] = Depends(
        _get_session_factory_dep
    ),
    value_cache_service: StatCanValueCacheService = Depends(
        get_statcan_value_cache_service
    ),
    metadata_cache: StatCanMetadataCacheService = Depends(
        get_statcan_metadata_cache_service
    ),
) -> ResolveService:
    return ResolveService(
        session_factory=factory,
        mapping_repository_factory=SemanticMappingRepository,
        value_cache_service=value_cache_service,
        metadata_cache=metadata_cache,
        logger=structlog.get_logger(module="services.resolve"),
    )


# ---------------------------------------------------------------------------
# GET /{cube_id}/{semantic_key}
# ---------------------------------------------------------------------------


@router.get(
    "/{cube_id}/{semantic_key}",
    response_model=ResolvedValueResponse,
    status_code=status.HTTP_200_OK,
    summary="Resolve a semantic value (cache-first; auto-prime on miss)",
    responses={
        200: {"description": "Cache hit or successful prime."},
        400: {"description": "Invalid filter set (RESOLVE_INVALID_FILTERS)."},
        401: {"description": "Missing or invalid X-API-KEY."},
        404: {
            "description": (
                "Mapping missing/inactive (MAPPING_NOT_FOUND) or no row "
                "after auto-prime (RESOLVE_CACHE_MISS)."
            )
        },
    },
)
async def resolve_value_handler(
    cube_id: str = Path(..., min_length=1, max_length=50),
    semantic_key: str = Path(..., min_length=1, max_length=100),
    dim: list[int] = Query(default_factory=list),
    member: list[int] = Query(default_factory=list),
    period: str | None = Query(default=None, max_length=20),
    service: ResolveService = Depends(_get_resolve_service),
) -> ResolvedValueResponse:
    """Resolve a single (cube, semantic_key, filters, [period]) cell.

    Query encoding (recon §2.3 Encoding 1): repeated ``dim`` + ``member``
    pairs, e.g. ``?dim=1&member=1&dim=2&member=10&period=2025-12``.
    """
    try:
        return await service.resolve_value(
            cube_id=cube_id,
            semantic_key=semantic_key,
            raw_filters=list(zip(dim, member, strict=False)),
            period=period,
        )
    except MappingNotFoundForResolveError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": MAPPING_NOT_FOUND,
                "message": str(exc),
            },
        ) from exc
    except ResolveInvalidFiltersError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": RESOLVE_INVALID_FILTERS,
                "message": (
                    f"Invalid filter set: {exc.reason}. Mapping requires "
                    f"dimensions {exc.expected}; got {exc.provided}."
                ),
                "details": {
                    "expected": exc.expected,
                    "provided": exc.provided,
                    "reason": exc.reason,
                },
            },
        ) from exc
    except ResolveCacheMissError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": RESOLVE_CACHE_MISS,
                "message": str(exc),
                "details": {
                    "cube_id": exc.cube_id,
                    "semantic_key": exc.semantic_key,
                    "coord": exc.coord,
                    "period": exc.period,
                    "prime_attempted": exc.prime_attempted,
                    "prime_error_code": exc.prime_error_code,
                },
            },
        ) from exc
    except Exception as exc:  # noqa: BLE001
        # Generic 500 — recon §2.5 explicitly forbids a resolve-specific
        # internal error code (Appendix B grep E found no precedent).
        logger.exception(
            "resolve.internal_error",
            cube_id=cube_id,
            semantic_key=semantic_key,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": "Internal server error.",
            },
        ) from exc


__all__ = ["router", "_get_resolve_service"]
