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
from fastapi import APIRouter, Body, Depends, Header, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.routers.admin_resolve import _get_resolve_service
from src.api.schemas.admin_leads import AdminLeadResponse
from src.core.database import get_db
from src.core.logging import get_logger
from src.models.publication import Publication, PublicationStatus
from src.repositories.lead_repository import LeadRepository
from src.repositories.publication_block_snapshot_repository import (
    PublicationBlockSnapshotRepository,
)
from src.repositories.publication_repository import PublicationRepository
from src.schemas.events import EventType
from src.schemas.publication import (
    PublicationCreate,
    PublicationResponse,
    PublicationUpdate,
    ReviewPayload,
    VisualConfig,
)
from src.schemas.staleness import (
    PublicationComparatorResponse,
    PublicationPublishRequest,
)
from src.services.audit import AuditWriter
from src.services.publications.clone import clone_publication
from src.services.publications.etag import compute_etag
from src.services.publications.exceptions import (
    PublicationCloneNotAllowedError,
    PublicationNotFoundError,
    PublicationPreconditionFailedError,
)
from src.services.publications.lineage import generate_lineage_key
from src.services.publications.staleness import PublicationStalenessService
from src.services.resolve.service import ResolveService


def _classify_workflow_event(
    previous: str | None, target: str
) -> EventType | None:
    """Return the audit event type for a workflow transition.

    Returns ``None`` if the transition is not one we audit at the backend
    level (``published`` is handled separately via
    :attr:`EventType.PUBLICATION_PUBLISHED`).

    Emitted event reflects business semantics, not just the target state:

    * ``in_review → draft``        = ``CHANGES_REQUESTED``
    * anything else → ``draft``    = ``RETURNED_TO_DRAFT``
    * ``draft → in_review``        = ``SUBMITTED``
    * ``in_review → approved``     = ``APPROVED``
    * ``approved → exported``      = ``EXPORTED``

    The ``draft → CHANGES_REQUESTED`` vs ``draft → RETURNED_TO_DRAFT``
    distinction is the reason this is a function rather than a flat map:
    two semantically different business events share the same target
    state (``draft``) and must be disambiguated via ``previous``.
    """
    if target == "draft":
        if previous == "in_review":
            return EventType.PUBLICATION_WORKFLOW_CHANGES_REQUESTED
        return EventType.PUBLICATION_WORKFLOW_RETURNED_TO_DRAFT
    if target == "in_review":
        return EventType.PUBLICATION_WORKFLOW_SUBMITTED
    if target == "approved":
        return EventType.PUBLICATION_WORKFLOW_APPROVED
    if target == "exported":
        return EventType.PUBLICATION_WORKFLOW_EXPORTED
    # target == "published" → handled via PUBLICATION_PUBLISHED (existing)
    return None

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


def _get_snapshot_repo(
    session: AsyncSession = Depends(get_db),
) -> PublicationBlockSnapshotRepository:
    """Provide a :class:`PublicationBlockSnapshotRepository` via DI."""
    return PublicationBlockSnapshotRepository(session)


def _get_staleness_service(
    snapshot_repo: PublicationBlockSnapshotRepository = Depends(_get_snapshot_repo),
    publication_repo: PublicationRepository = Depends(_get_repo),
    resolve_service: ResolveService = Depends(_get_resolve_service),
) -> PublicationStalenessService:
    """Provide a :class:`PublicationStalenessService` via DI.

    Reuses ``_get_resolve_service`` from ``admin_resolve`` so the cached-only
    compare path runs through the same composed ResolveService that the
    interactive resolve endpoint uses (ARCH-DPEN-001).
    """
    return PublicationStalenessService(
        snapshot_repository=snapshot_repo,
        publication_repository=publication_repo,
        resolve_service=resolve_service,
    )


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

    The appended history entry uses ``author = "system"``. ``fromWorkflow``
    is read from the stored ``review.workflow`` before it is overwritten
    so the audit trail preserves the actual prior state; the frontend
    shape allows ``null`` for the edge case where the stored review has
    no ``workflow`` key at all.
    """
    if publication.review is None:
        return publication

    try:
        review = json.loads(publication.review)
    except (json.JSONDecodeError, TypeError):
        logger.warning(
            "publication_review_parse_failed",
            publication_id=publication.id,
        )
        return publication

    # Capture the prior workflow BEFORE overwriting — history entry is
    # only honest if it reports the actual transition. Missing key →
    # ``None`` (shape-valid edge case, not silently fabricated).
    previous_workflow = review.get("workflow")

    review["workflow"] = target_workflow
    history = review.setdefault("history", [])
    history.append(
        {
            "ts": datetime.now(timezone.utc).isoformat(),
            "action": _WORKFLOW_HISTORY_ACTIONS.get(target_workflow, target_workflow),
            "summary": summary,
            "author": "system",
            "fromWorkflow": previous_workflow,
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
        lineage_key=publication.lineage_key,
        slug=publication.slug,
        # Opaque JSON string — never parsed here. Frontend owns rehydrate.
        document_state=publication.document_state,
        virality_score=publication.virality_score,
        status=status_value,
        cdn_url=None,
        created_at=publication.created_at,
        updated_at=publication.updated_at,
        published_at=publication.published_at,
        cloned_from_publication_id=publication.cloned_from_publication_id,
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
    data = body.model_dump()
    data["lineage_key"] = generate_lineage_key()
    publication = await repo.create_full(data)
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
    response: Response,
    repo: PublicationRepository = Depends(_get_repo),
) -> PublicationResponse:
    """Return a single publication by primary key.

    Sets ``ETag`` response header per docs/architecture/ARCHITECTURE_INVARIANTS.md §7.
    """
    publication = await repo.get_by_id(publication_id)
    if publication is None:
        raise PublicationNotFoundError()
    response.headers["ETag"] = compute_etag(publication)
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
        412: {"description": "ETag does not match — publication has changed."},
        422: {"description": "Validation failure."},
    },
)
async def update_publication(
    publication_id: int,
    body: PublicationUpdate,
    response: Response,
    if_match: str | None = Header(default=None, alias="If-Match"),
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

        The workflow transition also emits an audit event resolved by
        :func:`_classify_workflow_event`, which distinguishes
        ``in_review → draft`` (``CHANGES_REQUESTED``) from other
        ``* → draft`` transitions (``RETURNED_TO_DRAFT``).
        ``PUBLICATION_PUBLISHED`` is emitted *in addition* when the
        target is ``"published"``.
    """
    # Snapshot the previous workflow state so we can detect transitions
    # after ``update_fields`` mutates the row.
    previous = await repo.get_by_id(publication_id)
    if previous is None:
        raise PublicationNotFoundError()

    if if_match is None:
        # Q3=(a) tolerate-absent: warn-log, proceed without precondition check.
        # See DEBT-042 for 2-week hardening flip to 428 Precondition Required.
        logger.warning(
            "patch_publication_missing_if_match",
            publication_id=publication_id,
        )
    else:
        server_etag = compute_etag(previous)
        if if_match != server_etag:
            raise PublicationPreconditionFailedError(
                server_etag=server_etag,
                client_etag=if_match,
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
        raise PublicationNotFoundError()

    new_workflow: str | None = None
    if body.review is not None:
        new_workflow = body.review.workflow

        # Keep ``Publication.status`` in sync with ``review.workflow``.
        if new_workflow == "published" and publication.status != PublicationStatus.PUBLISHED:
            publication = await repo.publish(publication_id) or publication
        elif new_workflow != "published" and publication.status == PublicationStatus.PUBLISHED:
            await repo.update_status(publication_id, PublicationStatus.DRAFT)
            publication = await repo.get_by_id(publication_id) or publication

    # Emit workflow-transition audit events ONLY on a genuine transition
    # between two known states. ``previous_workflow is None`` is the
    # first-write case (row had no ``review`` yet): initial state
    # assignment is not a transition and must not pollute transition
    # metrics with a phantom ``RETURNED_TO_DRAFT`` (or any other) event.
    # The creation signal is already captured by
    # :attr:`EventType.PUBLICATION_GENERATED` at create time.
    if (
        previous_workflow is not None
        and new_workflow is not None
        and new_workflow != previous_workflow
    ):
        event_type = _classify_workflow_event(
            previous=previous_workflow, target=new_workflow
        )
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

    # Admin-visibility audit channel. Distinct from the workflow-
    # transition channel above: PUBLICATION_PUBLISHED tracks "row is
    # publicly visible", which is meaningful even on a first-write
    # PATCH that bypasses a prior draft state. Guarded only on the
    # value-change predicate so a PATCH that keeps ``workflow="published"``
    # does not re-emit.
    if new_workflow == "published" and new_workflow != previous_workflow:
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
    response.headers["ETag"] = compute_etag(publication)
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
        412: {"description": "ETag does not match — publication has changed."},
    },
)
async def publish_publication(
    publication_id: int,
    response: Response,
    payload: PublicationPublishRequest | None = Body(default=None),
    if_match: str | None = Header(default=None, alias="If-Match"),
    repo: PublicationRepository = Depends(_get_repo),
    audit: AuditWriter = Depends(_get_audit),
    staleness: PublicationStalenessService = Depends(_get_staleness_service),
) -> PublicationResponse:
    """Set status to PUBLISHED, stamp ``published_at``, audit, and capture snapshots.

    If the row already carries a ``review`` payload the endpoint also
    mirrors ``review.workflow = "published"`` and appends a history
    entry authored as ``"system"`` so the frontend can render the
    transition in its timeline. Rows without a ``review`` payload are
    published by status alone (no review sync is attempted).

    Phase 3.1d: optional ``payload.bound_blocks`` triggers publish-time
    snapshot capture per recon §5. Backward-compat: no body / null /
    ``{}`` / object body all parse to empty bound_blocks. Bare array
    body is NOT accepted. Capture is best-effort — per-block resolve or
    upsert failures are logged inside the service and never raise into
    the caller, so publish success is not rolled back.
    """
    # Phase 3.1d Slice 4b (Recon Delta 03): optional If-Match precondition
    # check on POST /publish. Mirrors PATCH semantics. v1 tolerates absent
    # If-Match (warn-log + Deprecation header) per DEBT-079.
    #
    # R2 (reviewer P1 BLOCKER): the row is read with a SELECT ... FOR UPDATE
    # so the ETag check and the subsequent ``repo.publish`` UPDATE happen
    # inside the same locked transaction. ``get_db`` commits at the end of
    # the request, releasing the lock; concurrent publish requests against
    # the same row serialise. PATCH's same TOCTOU window is tracked
    # separately under DEBT-043 and is out of scope for this slice.
    previous = await repo.get_by_id_for_update(publication_id)
    if previous is None:
        raise PublicationNotFoundError()

    if if_match is None:
        response.headers["Deprecation"] = "true"
        logger.warning(
            "publish_publication_missing_if_match",
            publication_id=publication_id,
        )
    else:
        server_etag = compute_etag(previous)
        if if_match != server_etag:
            raise PublicationPreconditionFailedError(
                server_etag=server_etag,
                client_etag=if_match,
            )

    publication = await repo.publish(publication_id)
    if publication is None:
        raise PublicationNotFoundError()

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

    # Phase 3.1d snapshot capture (recon §5). Best-effort: capture
    # failures are logged inside the service and never raise into the
    # caller, so publish success is not rolled back.
    bound_blocks = payload.bound_blocks if payload else []
    if bound_blocks:
        captured = await staleness.capture_for_publication(
            publication_id=publication.id,
            bound_blocks=bound_blocks,
        )
        logger.info(
            "publication_snapshots_captured",
            publication_id=publication.id,
            bound_count=len(bound_blocks),
            captured_count=captured,
        )

    logger.info("publication_published", publication_id=publication.id)
    response.headers["ETag"] = compute_etag(publication)
    return _serialize(publication)


# ---------------------------------------------------------------------------
# POST /api/v1/admin/publications/{publication_id}/compare
# ---------------------------------------------------------------------------


@router.post(
    "/{publication_id}/compare",
    response_model=PublicationComparatorResponse,
    status_code=status.HTTP_200_OK,
    summary="Compare publication snapshot fingerprint vs current cache",
    responses={
        404: {"description": "Publication not found."},
    },
)
async def compare_publication(
    publication_id: int,
    staleness: PublicationStalenessService = Depends(_get_staleness_service),
) -> PublicationComparatorResponse:
    """Phase 3.1d staleness comparator endpoint.

    Per recon §3.1: side-effect-free except for structured logs and
    metrics. The endpoint never writes to ``publication_block_snapshot``,
    never mutates publications, never auto-primes the cache, never
    emits AuditEvent rows.

    Per §3.2 BLOCKER-1: cached-only resolve mode is enforced inside
    :class:`PublicationStalenessService` — cache miss surfaces as
    ``compare_failed(resolve_error="RESOLVE_CACHE_MISS")``, never as a
    write to ``semantic_value_cache``.

    Per §3.4 BLOCKER-2 Option C: when no snapshot rows exist for a
    published publication, returns a single synthetic
    publication-level :class:`BlockComparatorResult` with
    ``stale_reasons=[snapshot_missing]`` and
    ``overall_status=unknown``.
    """
    response = await staleness.compare_for_publication(
        publication_id=publication_id,
    )
    logger.info(
        "publication_staleness_compared",
        publication_id=publication_id,
        overall_status=response.overall_status.value,
        overall_severity=response.overall_severity.value,
        block_count=len(response.block_results),
    )
    return response


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
        raise PublicationNotFoundError()

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


@router.post(
    "/{publication_id}/clone",
    response_model=PublicationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Clone a published publication into a new draft",
    responses={
        404: {"description": "Publication not found."},
        409: {"description": "Publication is not published and cannot be cloned."},
    },
)
async def clone_publication_endpoint(
    publication_id: int,
    response: Response,
    session: AsyncSession = Depends(get_db),
) -> PublicationResponse:
    """Clone a published publication into a new draft.

    Sets ``ETag`` response header on the clone so the editor can use it as
    the seed ``If-Match`` for the first PATCH (Phase 1.3 fork-path).
    """
    try:
        clone = await clone_publication(session=session, source_id=publication_id)
    except (PublicationNotFoundError, PublicationCloneNotAllowedError) as exc:
        raise exc
    response.headers["ETag"] = compute_etag(clone)
    return _serialize(clone)


# ---------------------------------------------------------------------------
# GET /api/v1/admin/publications/{publication_id}/leads
# Phase 2.3 — UTM-to-lineage attribution: per-publication lead listing.
# Match key is ``utm_content == publication.lineage_key`` (set at submit
# time by the lead-capture endpoint).
# ---------------------------------------------------------------------------


@router.get(
    "/{publication_id}/leads",
    response_model=list[AdminLeadResponse],
    status_code=status.HTTP_200_OK,
    summary="List leads attributed to this publication via UTM",
    responses={
        404: {"description": "Publication not found."},
    },
)
async def list_publication_leads(
    publication_id: int,
    limit: int = Query(default=200, ge=1, le=500),
    repo: PublicationRepository = Depends(_get_repo),
    session: AsyncSession = Depends(get_db),
) -> list[AdminLeadResponse]:
    """Return leads attributed to a publication via ``utm_content``.

    Phase 2.3 contract: a lead's ``utm_content`` mirrors the source
    publication's ``lineage_key``, set when the visitor arrives via a
    publish-kit share URL. Ordered newest-first.
    """
    publication = await repo.get_by_id(publication_id)
    if publication is None:
        raise PublicationNotFoundError()

    lead_repo = LeadRepository(session)
    leads = await lead_repo.list_by_utm_content(
        publication.lineage_key, limit=limit
    )
    return [AdminLeadResponse.model_validate(lead) for lead in leads]


__all__ = ["router"]
