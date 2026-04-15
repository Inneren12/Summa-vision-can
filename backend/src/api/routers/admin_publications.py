"""Admin CRUD endpoints for publications (Editor + Gallery extension).

Six endpoints, all under ``/api/v1/admin/publications`` and protected by
:class:`AuthMiddleware` (X-API-KEY header):

* ``POST   /``                 — create a DRAFT publication
* ``GET    /``                 — list publications, optional status filter
* ``GET    /{publication_id}`` — fetch a single publication
* ``PATCH  /{publication_id}`` — partial update of editorial / visual fields
* ``POST   /{publication_id}/publish``    — DRAFT → PUBLISHED + audit event
* ``POST   /{publication_id}/unpublish``  — PUBLISHED → DRAFT + audit event

Architecture:
    Follows ARCH-DPEN-001. ``PublicationRepository`` and
    ``AuditWriter`` are injected via FastAPI ``Depends`` and never
    instantiated globally.
"""

from __future__ import annotations

import json
from typing import Literal

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.logging import get_logger
from src.models.publication import Publication, PublicationStatus
from src.repositories.publication_repository import PublicationRepository
from src.schemas.events import EventType
from src.schemas.publication import (
    PublicationCreate,
    PublicationResponse,
    PublicationUpdate,
    VisualConfig,
)
from src.services.audit import AuditWriter

logger: structlog.stdlib.BoundLogger = get_logger(module="admin_publications")

router = APIRouter(
    prefix="/api/v1/admin/publications",
    tags=["admin-publications"],
)


# ---------------------------------------------------------------------------
# Dependency helpers
# ---------------------------------------------------------------------------


def _get_repo(session: AsyncSession = Depends(get_db)) -> PublicationRepository:
    """Provide a :class:`PublicationRepository` via DI."""
    return PublicationRepository(session)


def _get_audit(session: AsyncSession = Depends(get_db)) -> AuditWriter:
    """Provide an :class:`AuditWriter` via DI."""
    return AuditWriter(session)


# ---------------------------------------------------------------------------
# Serialisation helper
# ---------------------------------------------------------------------------


def _serialize(publication: Publication) -> PublicationResponse:
    """Convert an ORM Publication into the admin response model.

    ``visual_config`` is parsed from its JSON string back into a
    :class:`VisualConfig` instance for ergonomic API consumption. If
    parsing fails (e.g. legacy free-form value) we silently drop it
    rather than 500-ing — the editor will rehydrate from defaults.
    """
    visual_config: VisualConfig | None = None
    if publication.visual_config:
        try:
            visual_config = VisualConfig.model_validate_json(
                publication.visual_config
            )
        except Exception:
            logger.warning(
                "publication_visual_config_parse_failed",
                publication_id=publication.id,
            )
            visual_config = None

    status_value = (
        publication.status.value
        if hasattr(publication.status, "value")
        else str(publication.status)
    )

    return PublicationResponse(
        id=str(publication.id),
        headline=publication.headline,
        chart_type=publication.chart_type,
        eyebrow=publication.eyebrow,
        description=publication.description,
        source_text=publication.source_text,
        footnote=publication.footnote,
        visual_config=visual_config,
        virality_score=publication.virality_score,
        status=status_value,
        cdn_url=None,
        created_at=publication.created_at,
        updated_at=publication.updated_at,
        published_at=publication.published_at,
    )


# ---------------------------------------------------------------------------
# POST /api/v1/admin/publications
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=PublicationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a draft publication",
    responses={
        201: {"description": "Publication created in DRAFT status."},
        401: {"description": "Missing or invalid X-API-KEY."},
        422: {"description": "Validation failure (e.g. invalid visual_config)."},
    },
)
async def create_publication(
    body: PublicationCreate,
    repo: PublicationRepository = Depends(_get_repo),
) -> PublicationResponse:
    """Create a new publication in ``DRAFT`` status."""
    publication = await repo.create_full(body.model_dump())
    logger.info(
        "publication_created",
        publication_id=publication.id,
        headline=publication.headline,
    )
    return _serialize(publication)


# ---------------------------------------------------------------------------
# GET /api/v1/admin/publications
# ---------------------------------------------------------------------------


_StatusQuery = Literal["draft", "published", "all"]


@router.get(
    "",
    response_model=list[PublicationResponse],
    status_code=status.HTTP_200_OK,
    summary="List publications (optionally filter by status)",
)
async def list_publications(
    status_filter: _StatusQuery = Query(
        default="all",
        alias="status",
        description="One of 'draft', 'published', or 'all' (default).",
    ),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    repo: PublicationRepository = Depends(_get_repo),
) -> list[PublicationResponse]:
    """Return publications filtered by lifecycle status."""
    status_map: dict[str, PublicationStatus | None] = {
        "draft": PublicationStatus.DRAFT,
        "published": PublicationStatus.PUBLISHED,
        "all": None,
    }
    publications = await repo.list_by_status(
        status_filter=status_map[status_filter],
        limit=limit,
        offset=offset,
    )
    return [_serialize(pub) for pub in publications]


# ---------------------------------------------------------------------------
# GET /api/v1/admin/publications/{publication_id}
# ---------------------------------------------------------------------------


@router.get(
    "/{publication_id}",
    response_model=PublicationResponse,
    status_code=status.HTTP_200_OK,
    summary="Fetch a single publication",
    responses={
        404: {"description": "Publication not found."},
    },
)
async def get_publication(
    publication_id: int,
    repo: PublicationRepository = Depends(_get_repo),
) -> PublicationResponse:
    """Return a single publication by primary key."""
    publication = await repo.get_by_id(publication_id)
    if publication is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Publication not found",
        )
    return _serialize(publication)


# ---------------------------------------------------------------------------
# PATCH /api/v1/admin/publications/{publication_id}
# ---------------------------------------------------------------------------


@router.patch(
    "/{publication_id}",
    response_model=PublicationResponse,
    status_code=status.HTTP_200_OK,
    summary="Partial update of a publication",
    responses={
        404: {"description": "Publication not found."},
        422: {"description": "Validation failure."},
    },
)
async def update_publication(
    publication_id: int,
    body: PublicationUpdate,
    repo: PublicationRepository = Depends(_get_repo),
) -> PublicationResponse:
    """Apply a partial update; ``None`` fields are ignored."""
    payload = body.model_dump(exclude_unset=True)
    publication = await repo.update_fields(publication_id, payload)
    if publication is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Publication not found",
        )
    logger.info(
        "publication_updated",
        publication_id=publication.id,
        fields=list(payload.keys()),
    )
    return _serialize(publication)


# ---------------------------------------------------------------------------
# POST /api/v1/admin/publications/{publication_id}/publish
# ---------------------------------------------------------------------------


@router.post(
    "/{publication_id}/publish",
    response_model=PublicationResponse,
    status_code=status.HTTP_200_OK,
    summary="Publish a draft publication",
    responses={
        404: {"description": "Publication not found."},
    },
)
async def publish_publication(
    publication_id: int,
    repo: PublicationRepository = Depends(_get_repo),
    audit: AuditWriter = Depends(_get_audit),
) -> PublicationResponse:
    """Set status to PUBLISHED, stamp ``published_at``, and audit."""
    publication = await repo.publish(publication_id)
    if publication is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Publication not found",
        )

    await audit.log_event(
        event_type=EventType.PUBLICATION_PUBLISHED,
        entity_type="publication",
        entity_id=str(publication.id),
        metadata={"headline": publication.headline},
        actor="admin_api",
    )
    logger.info("publication_published", publication_id=publication.id)
    return _serialize(publication)


# ---------------------------------------------------------------------------
# POST /api/v1/admin/publications/{publication_id}/unpublish
# ---------------------------------------------------------------------------


@router.post(
    "/{publication_id}/unpublish",
    response_model=PublicationResponse,
    status_code=status.HTTP_200_OK,
    summary="Unpublish a publication (revert to DRAFT)",
    responses={
        404: {"description": "Publication not found."},
    },
)
async def unpublish_publication(
    publication_id: int,
    repo: PublicationRepository = Depends(_get_repo),
) -> PublicationResponse:
    """Revert the publication to DRAFT status."""
    publication = await repo.unpublish(publication_id)
    if publication is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Publication not found",
        )
    logger.info("publication_unpublished", publication_id=publication.id)
    return _serialize(publication)


__all__ = ["router"]
