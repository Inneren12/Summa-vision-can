"""Admin endpoints for publication queue, graphic generation, and job status.

Provides three endpoints:

* ``GET  /api/v1/admin/queue``                — list DRAFT publications
* ``POST /api/v1/admin/graphics/generate``    — enqueue persistent generation job (B-4)
* ``GET  /api/v1/admin/jobs/{job_id}``        — check job status / result (B-4)

Architecture:
    Follows ARCH-DPEN-001 — all services arrive via ``Depends``.
    Follows ARCH-JOBS-001 — generation is submitted as a persistent job,
    not executed synchronously. Endpoint returns HTTP 202 immediately.
"""

from __future__ import annotations

import hashlib
import json

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas.admin_graphics import (
    GraphicsGenerateRequest,
    GraphicsGenerateResponse,
    JobStatusResponse,
    PublicationResponse,
)
from src.core.database import get_db
from src.core.logging import get_logger
from src.models.publication import PublicationStatus
from src.repositories.job_repository import JobRepository
from src.repositories.publication_repository import PublicationRepository
from src.schemas.job_payloads import GraphicsGeneratePayload

logger: structlog.stdlib.BoundLogger = get_logger(module="admin_graphics")

# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


# ---------------------------------------------------------------------------
# Dependency helpers
# ---------------------------------------------------------------------------


def _get_repo(session: AsyncSession = Depends(get_db)) -> PublicationRepository:
    """Provide a PublicationRepository via dependency injection."""
    return PublicationRepository(session)


def _get_job_repo(session: AsyncSession = Depends(get_db)) -> JobRepository:
    """Provide a JobRepository via dependency injection."""
    return JobRepository(session)


# ---------------------------------------------------------------------------
# GET /api/v1/admin/queue
# ---------------------------------------------------------------------------


@router.get(
    "/queue",
    response_model=list[PublicationResponse],
    status_code=status.HTTP_200_OK,
    summary="List draft publications",
    responses={
        200: {"description": "List of DRAFT publications (may be empty)."},
    },
)
async def get_queue(
    limit: int = Query(default=20, ge=1, le=100),
    pub_repo: PublicationRepository = Depends(_get_repo),
) -> list[PublicationResponse]:
    """Return draft publications ordered by virality score (highest first).

    If no drafts exist, an empty list is returned (never 404).
    """
    publications = await pub_repo.get_drafts(limit=limit)
    return [
        PublicationResponse(
            id=pub.id,
            headline=pub.headline,
            chart_type=pub.chart_type,
            virality_score=pub.virality_score,
            status=pub.status.value,
            created_at=pub.created_at,
        )
        for pub in publications
    ]


# ---------------------------------------------------------------------------
# POST /api/v1/admin/graphics/generate  (B-4 — persistent job)
# ---------------------------------------------------------------------------


@router.post(
    "/graphics/generate",
    response_model=GraphicsGenerateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Enqueue graphic generation job",
    responses={
        202: {"description": "Job enqueued — poll GET /api/v1/admin/jobs/{job_id}."},
    },
)
async def generate_graphic(
    body: GraphicsGenerateRequest,
    job_repo: JobRepository = Depends(_get_job_repo),
) -> GraphicsGenerateResponse:
    """Enqueue a persistent graphic generation job.

    The endpoint validates the request, builds a typed payload, computes
    a dedupe key, and enqueues the job via ``JobRepository``.  It does
    **not** block on pipeline execution (ARCH-JOBS-001).

    If a job with the same dedupe key is already active (queued/running),
    the existing job's ID is returned instead of creating a duplicate.
    """
    # 1. Build typed payload
    payload = GraphicsGeneratePayload(
        data_key=body.data_key,
        chart_type=body.chart_type,
        title=body.title,
        size=body.size,
        category=body.category,
        source_product_id=body.source_product_id,
    )

    # 2. Compute dedupe key
    config_dict = {
        "chart_type": body.chart_type,
        "size": list(body.size),
        "title": body.title,
    }
    config_hash = hashlib.sha256(
        json.dumps(config_dict, sort_keys=True).encode("utf-8")
    ).hexdigest()[:16]
    dedupe_key = (
        f"graphics:{body.source_product_id or 'manual'}"
        f":{body.data_key}:{config_hash}"
    )

    # 3. Enqueue
    result = await job_repo.enqueue(
        job_type="graphics_generate",
        payload_json=payload.model_dump_json(),
        dedupe_key=dedupe_key,
        created_by="admin_api",
    )

    logger.info(
        "graphics_generate_enqueued",
        job_id=result.job.id,
        created=result.created,
        dedupe_key=dedupe_key,
    )

    return GraphicsGenerateResponse(
        job_id=str(result.job.id),
        status=result.job.status.value,
    )


# ---------------------------------------------------------------------------
# GET /api/v1/admin/jobs/{job_id}  (B-4 — job status)
# ---------------------------------------------------------------------------


@router.get(
    "/jobs/{job_id}",
    response_model=JobStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get job status",
    responses={
        200: {"description": "Full job status including result on completion."},
        404: {"description": "Job not found."},
    },
)
async def get_job_status(
    job_id: int,
    job_repo: JobRepository = Depends(_get_job_repo),
) -> JobStatusResponse:
    """Get the status and result of a specific job by ID.

    Used for polling after submitting a generation request.
    Returns the full job record including result_json when complete.
    """
    job = await job_repo.get_job(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    return JobStatusResponse(
        job_id=str(job.id),
        job_type=job.job_type,
        status=job.status.value,
        result_json=job.result_json,
        error_code=job.error_code,
        error_message=job.error_message,
        created_at=job.created_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
    )
