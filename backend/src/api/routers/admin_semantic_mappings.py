"""Phase 3.1b admin CRUD router for semantic mappings.

Endpoints (all guarded by :class:`AuthMiddleware` via ``X-API-KEY``):

* ``POST   /api/v1/admin/semantic-mappings/upsert`` — idempotent on
  ``(cube_id, semantic_key)``. Hybrid optimistic concurrency: accepts
  ``If-Match`` header OR ``if_match_version`` body field (header wins
  if both are present). Returns 412 ``VERSION_CONFLICT`` on mismatch.
* ``GET    /api/v1/admin/semantic-mappings`` — paginated list with
  optional ``cube_id`` / ``semantic_key`` / ``is_active`` filters.
* ``GET    /api/v1/admin/semantic-mappings/{id}`` — fetch single row.
* ``DELETE /api/v1/admin/semantic-mappings/{id}`` — soft delete
  (sets ``is_active=false``). Idempotent.

Mirrors the structure of :mod:`src.api.routers.admin_publications`:
explicit ``response_model``, ``status_code``, ``responses`` map per
route; helper deps via :func:`Depends(get_db)` for short-lived sessions.
"""
from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.api.schemas.semantic_mapping_admin import (
    SemanticMappingListItem,
    SemanticMappingListResponse,
    SemanticMappingResponse,
    SemanticMappingUpsertRequest,
)
from src.core.database import get_db, get_session_factory
from src.core.logging import get_logger
from src.repositories.semantic_mapping_repository import (
    SemanticMappingRepository,
)
from src.services.semantic_mappings.exceptions import (
    CubeNotInCacheError,
    DimensionMismatchError,
    MappingNotFoundError,
    MemberMismatchError,
    MetadataValidationError,
    VersionConflictError,
)
from src.services.semantic_mappings.service import SemanticMappingService
from src.services.statcan.client import StatCanClient
from src.services.statcan.maintenance import StatCanMaintenanceGuard
from src.services.statcan.metadata_cache import StatCanMetadataCacheService

logger: structlog.stdlib.BoundLogger = get_logger(
    module="admin_semantic_mappings"
)

router = APIRouter(
    prefix="/api/v1/admin/semantic-mappings",
    tags=["admin", "semantic-mappings"],
)


# ---------------------------------------------------------------------------
# Dependency helpers
# ---------------------------------------------------------------------------


def _get_session_factory() -> async_sessionmaker[AsyncSession]:
    return get_session_factory()


def _get_metadata_cache_service(
    factory: async_sessionmaker[AsyncSession] = Depends(_get_session_factory),
) -> StatCanMetadataCacheService:
    """Build a :class:`StatCanMetadataCacheService` per request.

    Tests override this with an :class:`AsyncMock` (or a fully-stubbed
    instance) so no real StatCan I/O occurs.
    """
    from datetime import datetime, timezone

    import httpx

    from src.core.rate_limit import AsyncTokenBucket

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


def _get_service(
    factory: async_sessionmaker[AsyncSession] = Depends(_get_session_factory),
    metadata_cache: StatCanMetadataCacheService = Depends(
        _get_metadata_cache_service
    ),
) -> SemanticMappingService:
    return SemanticMappingService(
        session_factory=factory,
        repository_factory=SemanticMappingRepository,
        metadata_cache=metadata_cache,
        logger=structlog.get_logger(module="semantic_mappings.service"),
    )


# ---------------------------------------------------------------------------
# Envelope + concurrency helpers
# ---------------------------------------------------------------------------


def _resolve_if_match(header: str | None, body_field: int | None) -> int | None:
    """Hybrid concurrency: header takes precedence; body fallback.

    Malformed header (non-integer after stripping ``W/`` and quotes) is
    silently ignored so the body field is consulted. This keeps the form
    flow forgiving — the operator only sees a 412 when there is a real
    version mismatch, not when an upstream proxy mangles the header.
    See DEBT-054 for the convention divergence vs publications.
    """
    if header is not None:
        cleaned = header.strip()
        if cleaned.startswith("W/"):
            cleaned = cleaned[2:].strip()
        cleaned = cleaned.strip('"')
        try:
            return int(cleaned)
        except ValueError:
            pass
    return body_field


def _build_envelope(
    error_code: str, exc: MetadataValidationError
) -> dict[str, Any]:
    """Render a :class:`MetadataValidationError` into the DEBT-030 envelope."""
    return {
        "error_code": error_code,
        "message": str(exc),
        "details": {
            "cube_id": exc.cube_id,
            "errors": [
                {
                    "error_code": e.error_code,
                    "dimension_name": e.dimension_name,
                    "member_name": e.member_name,
                    "resolved_dimension_position_id": e.resolved_dimension_position_id,
                    "resolved_member_id": e.resolved_member_id,
                    "suggested_member_name_en": e.suggested_member_name_en,
                    "message": e.message,
                }
                for e in exc.result.errors
            ],
        },
    }


# ---------------------------------------------------------------------------
# POST /upsert
# ---------------------------------------------------------------------------


@router.post(
    "/upsert",
    response_model=SemanticMappingResponse,
    status_code=status.HTTP_200_OK,
    summary="Validated idempotent upsert by (cube_id, semantic_key)",
    responses={
        200: {"description": "Existing mapping updated."},
        201: {"description": "New mapping created."},
        400: {"description": "Validation failure (dimension/member/cube/product)."},
        401: {"description": "Missing or invalid X-API-KEY."},
        412: {
            "description": (
                "Version conflict (If-Match header or if_match_version body "
                "mismatch)."
            )
        },
    },
)
async def upsert_semantic_mapping(
    body: SemanticMappingUpsertRequest,
    response: Response,
    if_match_header: str | None = Header(default=None, alias="If-Match"),
    service: SemanticMappingService = Depends(_get_service),
) -> SemanticMappingResponse:
    """Validate the mapping against StatCan cache and upsert by composite key.

    Hybrid optimistic concurrency: ``If-Match`` header takes precedence
    over the ``if_match_version`` body field; either form is accepted.
    """
    if_match_version = _resolve_if_match(if_match_header, body.if_match_version)

    try:
        mapping, was_created = await service.upsert_validated(
            cube_id=body.cube_id,
            product_id=body.product_id,
            semantic_key=body.semantic_key,
            label=body.label,
            description=body.description,
            config=body.config.model_dump(),
            is_active=body.is_active,
            updated_by=body.updated_by,
            if_match_version=if_match_version,
        )
    except VersionConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_412_PRECONDITION_FAILED,
            detail={
                "error_code": "VERSION_CONFLICT",
                "message": str(exc),
                "details": {
                    "cube_id": exc.cube_id,
                    "semantic_key": exc.semantic_key,
                    "expected_version": exc.expected_version,
                    "actual_version": exc.actual_version,
                },
            },
        ) from exc
    except CubeNotInCacheError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_build_envelope("CUBE_NOT_IN_CACHE", exc),
        ) from exc
    except DimensionMismatchError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_build_envelope("DIMENSION_NOT_FOUND", exc),
        ) from exc
    except MemberMismatchError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_build_envelope("MEMBER_NOT_FOUND", exc),
        ) from exc
    except MetadataValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_build_envelope(exc.error_code, exc),
        ) from exc

    if was_created:
        response.status_code = status.HTTP_201_CREATED

    logger.info(
        "semantic_mapping_upserted",
        mapping_id=mapping.id,
        cube_id=mapping.cube_id,
        semantic_key=mapping.semantic_key,
        was_created=was_created,
        version=mapping.version,
    )
    return SemanticMappingResponse.model_validate(mapping)


# ---------------------------------------------------------------------------
# GET (list)
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=SemanticMappingListResponse,
    status_code=status.HTTP_200_OK,
    summary="List semantic mappings (paginated, with filters)",
    responses={401: {"description": "Missing or invalid X-API-KEY."}},
)
async def list_semantic_mappings(
    cube_id: str | None = Query(default=None),
    semantic_key: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    service: SemanticMappingService = Depends(_get_service),
) -> SemanticMappingListResponse:
    rows, total = await service.list_mappings(
        cube_id=cube_id,
        semantic_key=semantic_key,
        is_active=is_active,
        limit=limit,
        offset=offset,
    )
    return SemanticMappingListResponse(
        items=[SemanticMappingListItem.model_validate(r) for r in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


# ---------------------------------------------------------------------------
# GET /{id}
# ---------------------------------------------------------------------------


@router.get(
    "/{mapping_id}",
    response_model=SemanticMappingResponse,
    status_code=status.HTTP_200_OK,
    summary="Fetch a single semantic mapping by id",
    responses={
        401: {"description": "Missing or invalid X-API-KEY."},
        404: {"description": "Mapping not found."},
    },
)
async def get_semantic_mapping(
    mapping_id: int,
    service: SemanticMappingService = Depends(_get_service),
) -> SemanticMappingResponse:
    try:
        mapping = await service.get_mapping(mapping_id)
    except MappingNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "MAPPING_NOT_FOUND",
                "message": str(exc),
            },
        ) from exc
    return SemanticMappingResponse.model_validate(mapping)


# ---------------------------------------------------------------------------
# DELETE /{id}
# ---------------------------------------------------------------------------


@router.delete(
    "/{mapping_id}",
    response_model=SemanticMappingResponse,
    status_code=status.HTTP_200_OK,
    summary="Soft-delete a semantic mapping (idempotent)",
    responses={
        401: {"description": "Missing or invalid X-API-KEY."},
        404: {"description": "Mapping not found."},
    },
)
async def delete_semantic_mapping(
    mapping_id: int,
    service: SemanticMappingService = Depends(_get_service),
) -> SemanticMappingResponse:
    """Soft delete: sets ``is_active=false``. Already-inactive returns 200
    with the current row unchanged (no version bump)."""
    try:
        mapping = await service.soft_delete(mapping_id)
    except MappingNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "MAPPING_NOT_FOUND",
                "message": str(exc),
            },
        ) from exc
    logger.info(
        "semantic_mapping_soft_deleted",
        mapping_id=mapping.id,
        cube_id=mapping.cube_id,
        semantic_key=mapping.semantic_key,
    )
    return SemanticMappingResponse.model_validate(mapping)


# Tests / DI ergonomics: keep the unused-import lint suppressed by leaving
# get_db imported even though the helper deps go through the session
# factory directly. Tests override _get_service / _get_metadata_cache_service.
_ = get_db


__all__ = ["router"]
