"""Admin endpoints for the Jobs Dashboard (C-4).

Provides three endpoints:

* ``GET  /api/v1/admin/jobs``                — list jobs with filters
* ``GET  /api/v1/admin/jobs/{job_id}``       — get a single job by ID
* ``POST /api/v1/admin/jobs/{job_id}/retry`` — retry a failed job

Architecture:
    Follows ARCH-DPEN-001 — all services arrive via ``Depends``.
"""

from __future__ import annotations

from datetime import datetime

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.exceptions import ConflictError, NotFoundError
from src.core.logging import get_logger
from src.models.job import Job, JobStatus
from src.repositories.job_repository import JobRepository

logger: structlog.stdlib.BoundLogger = get_logger(module="admin_jobs")

# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class JobItemResponse(BaseModel):
    """Full job representation for the dashboard list."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    job_type: str
    status: str
    payload_json: str | None = None
    result_json: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    attempt_count: int
    max_attempts: int
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_by: str | None = None
    dedupe_key: str | None = None


class JobListResponse(BaseModel):
    """Paginated job list response."""

    items: list[JobItemResponse]
    total: int


class RetryJobResponse(BaseModel):
    """Response after successfully retrying a job."""

    job_id: str
    status: str


# ---------------------------------------------------------------------------
# Dependency helpers
# ---------------------------------------------------------------------------


def _get_job_repo(session: AsyncSession = Depends(get_db)) -> JobRepository:
    """Provide a JobRepository via dependency injection."""
    return JobRepository(session)


# ---------------------------------------------------------------------------
# GET /api/v1/admin/jobs
# ---------------------------------------------------------------------------


@router.get(
    "/jobs",
    response_model=JobListResponse,
    status_code=status.HTTP_200_OK,
    summary="List jobs with optional filters",
    responses={
        200: {"description": "List of jobs matching filters."},
    },
)
async def list_jobs(
    job_type: str | None = Query(default=None, description="Filter by job type"),
    status_filter: str | None = Query(
        default=None, alias="status", description="Filter by status"
    ),
    limit: int = Query(default=50, ge=1, le=200),
    job_repo: JobRepository = Depends(_get_job_repo),
) -> JobListResponse:
    """Return jobs ordered by created_at descending, with optional filters."""
    parsed_status: JobStatus | None = None
    if status_filter is not None:
        try:
            parsed_status = JobStatus(status_filter)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid status: {status_filter}",
            )

    total = await job_repo.count_jobs(
        job_type=job_type,
        status=parsed_status,
    )

    jobs = await job_repo.list_jobs(
        job_type=job_type,
        status=parsed_status,
        limit=limit,
    )

    items = [
        JobItemResponse(
            id=str(job.id),
            job_type=job.job_type,
            status=job.status.value,
            payload_json=job.payload_json,
            result_json=job.result_json,
            error_code=job.error_code,
            error_message=job.error_message,
            attempt_count=job.attempt_count,
            max_attempts=job.max_attempts,
            created_at=job.created_at,
            started_at=job.started_at,
            finished_at=job.finished_at,
            created_by=job.created_by,
            dedupe_key=job.dedupe_key,
        )
        for job in jobs
    ]

    return JobListResponse(items=items, total=total)


# ---------------------------------------------------------------------------
# GET /api/v1/admin/jobs/{job_id}
# ---------------------------------------------------------------------------


@router.get(
    "/jobs/{job_id}",
    response_model=JobItemResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a single job by ID",
    responses={
        200: {"description": "Job details."},
        404: {"description": "Job not found."},
    },
)
async def get_job(
    job_id: int,
    job_repo: JobRepository = Depends(_get_job_repo),
) -> JobItemResponse:
    """Return a single job by its primary key."""
    job = await job_repo.get_job(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    return JobItemResponse(
        id=str(job.id),
        job_type=job.job_type,
        status=job.status.value,
        payload_json=job.payload_json,
        result_json=job.result_json,
        error_code=job.error_code,
        error_message=job.error_message,
        attempt_count=job.attempt_count,
        max_attempts=job.max_attempts,
        created_at=job.created_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
        created_by=job.created_by,
        dedupe_key=job.dedupe_key,
    )


# ---------------------------------------------------------------------------
# POST /api/v1/admin/jobs/{job_id}/retry
# ---------------------------------------------------------------------------


@router.post(
    "/jobs/{job_id}/retry",
    response_model=RetryJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Retry a failed job",
    responses={
        202: {"description": "Job re-enqueued for retry."},
        404: {"description": "Job not found."},
        409: {"description": "Job is not retryable."},
    },
)
async def retry_job(
    job_id: int,
    job_repo: JobRepository = Depends(_get_job_repo),
) -> RetryJobResponse:
    """Re-enqueue a failed job if it has remaining retry attempts.

    Delegates all validation and state mutation to
    ``JobRepository.retry_failed_job`` to keep the router thin
    and preserve the dedupe invariant.
    """
    try:
        job = await job_repo.retry_failed_job(job_id)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )
    except ConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )

    logger.info(
        "job_retried",
        job_id=job.id,
        job_type=job.job_type,
        attempt_count=job.attempt_count,
    )

    return RetryJobResponse(
        job_id=str(job.id),
        status=job.status.value,
    )
