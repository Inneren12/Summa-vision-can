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
from datetime import datetime, timezone
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
    ReviewPayload,
    VisualConfig,
)
from src.services.audit import AuditWriter


# Mapping from a target ``review.workflow`` state to the audit
# ``EventType`` that should be emitted when a PATCH transitions into it.
# ``"published"`` is intentionally omitted — :attr:`EventType.PUBLICATION_PUBLISHED`
# is emitted separately to preserve the existing publish/unpublish
# semantics (admin-visibility). See ``docs/modules/editor.md``.
_WORKFLOW_EVENT_MAP: dict[str, EventType] = {
    "in_review": EventType.PUBLICATION_WORKFLOW_SUBMITTED,
    "approved": EventType.PUBLICATION_WORKFLOW_APPROVED,
    "draft": EventType.PUBLICATION_WORKFLOW_RETURNED_TO_DRAFT,
    "exported": EventType.PUBLICATION_WORKFLOW_EXPORTED,
}

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
# Review / workflow sync helper
# ---------------------------------------------------------------------------


_WORKFLOW_HISTORY_ACTIONS: dict[str, str] = {
    "published": "published",
    "draft": "returned_to_draft",
}


async def _sync_workflow_from_status(
    repo: PublicationRepository,
    publication: Publication,
    *,
    target_workflow: str,
    summary: str,
) -> Publication:
    """Mirror ``Publication.status`` changes into ``review.workflow``.

    Called by :func:`publish_publication` and :func:`unpublish_publication`
    so the status-driven admin endpoints keep the ``review`` subtree in
    sync with the gallery flag. Rows without an existing ``review``
    payload are left untouched — a publication that never had a
    frontend-authored review is published by status alone.

    The appended history entry uses ``author = "system"`` and
    ``fromWorkflow = None`` because the backend has no atomic snapshot
    of the prior workflow state; the frontend shape allows null
    ``fromWorkflow`` for system-emitted entries.
    """
    if publication.review is None:
        return publication

    try:
        review = json.loads(publication.review)
    except json.JSONDecodeError:
        logger.warning(
            "publication_review_parse_failed",
            publication_id=publication.id,
        )
        return publication

    review["workflow"] = target_workflow
    history = review.setdefault("history", [])
    history.append(
        {
            "ts": datetime.now(timezone.utc).isoformat(),
            "action": _WORKFLOW_HISTORY_ACTIONS.get(target_workflow, target_workflow),
            "summary": summary,
            "author": "system",
            "fromWorkflow": None,
            "toWorkflow": target_workflow,
        }
    )
    updated = await repo.update_fields(publication.id, {"review": review})
    return updated or publication


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

    # ``review`` is stored as a JSON string and must be parsed back
    # before :class:`PublicationResponse` accepts it. Parse failures
    # surface as warnings (rather than 500s) to match the
    # ``visual_config`` fallback behavior — the editor can always fetch
    # a fresh copy and re-save.
    review: ReviewPayload | None = None
    if publication.review:
        try:
            review = ReviewPayload.model_validate_json(publication.review)
        except Exception:
            logger.warning(
                "publication_review_parse_failed",
                publication_id=publication.id,
            )
            review = None

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
        review=review,
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
    audit: AuditWriter = Depends(_get_audit),
) -> PublicationResponse:
    """Apply a partial update; ``None`` fields are ignored.

    Workflow sync (Stage 3 PR 4):
        When the payload carries a ``review.workflow``, the backend
        mirrors that value into ``Publication.status`` so the public
        gallery can continue to filter on ``status``:

        * ``review.workflow == "published"`` → ``status = PUBLISHED``
          (and ``published_at`` stamped if not already set).
        * any other workflow on a previously-PUBLISHED row → ``status = DRAFT``
          (``published_at`` is deliberately preserved for historical audit).

        The workflow transition also emits an audit event keyed on the
        target state (``_WORKFLOW_EVENT_MAP``). ``PUBLICATION_PUBLISHED``
        is emitted *in addition* when the target is ``"published"``.
    """
    # Snapshot the previous workflow state so we can detect transitions
    # after ``update_fields`` mutates the row.
    previous = await repo.get_by_id(publication_id)
    if previous is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Publication not found",
        )
    previous_workflow: str | None = None
    if previous.review:
        try:
            previous_workflow = json.loads(previous.review).get("workflow")
        except json.JSONDecodeError:
            logger.warning(
                "publication_review_parse_failed",
                publication_id=publication_id,
            )

    payload = body.model_dump(exclude_unset=True)
    publication = await repo.update_fields(publication_id, payload)
    if publication is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Publication not found",
        )

    new_workflow: str | None = None
    if body.review is not None:
        new_workflow = body.review.workflow

        # Keep ``Publication.status`` in sync with ``review.workflow``.
        if new_workflow == "published" and publication.status != PublicationStatus.PUBLISHED:
            publication = await repo.publish(publication_id) or publication
        elif new_workflow != "published" and publication.status == PublicationStatus.PUBLISHED:
            await repo.update_status(publication_id, PublicationStatus.DRAFT)
            publication = await repo.get_by_id(publication_id) or publication

    # Emit audit events on a genuine workflow transition.
    if new_workflow is not None and new_workflow != previous_workflow:
        event_type = _WORKFLOW_EVENT_MAP.get(new_workflow)
        if event_type is not None:
            await audit.log_event(
                event_type=event_type,
                entity_type="publication",
                entity_id=str(publication.id),
                metadata={
                    "from": previous_workflow,
                    "to": new_workflow,
                },
                actor="admin_api",
            )
        if new_workflow == "published":
            await audit.log_event(
                event_type=EventType.PUBLICATION_PUBLISHED,
                entity_type="publication",
                entity_id=str(publication.id),
                metadata={
                    "from": previous_workflow,
                    "to": new_workflow,
                    "source": "patch_review",
                },
                actor="admin_api",
            )

    logger.info(
        "publication_updated",
        publication_id=publication.id,
        fields=list(payload.keys()),
        previous_workflow=previous_workflow,
        new_workflow=new_workflow,
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
    """Set status to PUBLISHED, stamp ``published_at``, and audit.

    If the row already carries a ``review`` payload the endpoint also
    mirrors ``review.workflow = "published"`` and appends a history
    entry authored as ``"system"`` so the frontend can render the
    transition in its timeline. Rows without a ``review`` payload are
    published by status alone (no review sync is attempted).
    """
    publication = await repo.publish(publication_id)
    if publication is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Publication not found",
        )

    # Mirror into review.workflow when a review payload exists. We
    # cannot know the ``fromWorkflow`` safely from the backend (no
    # atomic snapshot), so leave it ``None`` — the frontend shape
    # allows a null ``fromWorkflow`` for system-emitted entries.
    publication = await _sync_workflow_from_status(
        repo, publication, target_workflow="published",
        summary="Published via admin endpoint",
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
    audit: AuditWriter = Depends(_get_audit),
) -> PublicationResponse:
    """Revert the publication to DRAFT status and record an audit event.

    The audit trail must be symmetric with :func:`publish_publication` —
    there is currently no dedicated ``PUBLICATION_UNPUBLISHED`` member in
    :class:`EventType`, so we reuse :attr:`EventType.PUBLICATION_PUBLISHED`
    and distinguish the reversal via ``metadata.action = "unpublish"``
    (with ``new_status`` for dashboard filtering).
    """
    publication = await repo.unpublish(publication_id)
    if publication is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Publication not found",
        )

    publication = await _sync_workflow_from_status(
        repo, publication, target_workflow="draft",
        summary="Unpublished via admin endpoint; returned to draft",
    )

    await audit.log_event(
        event_type=EventType.PUBLICATION_PUBLISHED,
        entity_type="publication",
        entity_id=str(publication.id),
        metadata={
            "action": "unpublish",
            "new_status": "DRAFT",
            "headline": publication.headline,
        },
        actor="admin_api",
    )
    logger.info("publication_unpublished", publication_id=publication.id)
    return _serialize(publication)


__all__ = ["router"]
