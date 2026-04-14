"""Admin endpoints for publication queue, graphic generation, and job status.

Provides four endpoints:

* ``GET  /api/v1/admin/queue``                        — list DRAFT publications
* ``POST /api/v1/admin/graphics/generate``            — enqueue persistent generation job (B-4)
* ``POST /api/v1/admin/graphics/generate-from-data``  — same, but from uploaded JSON/CSV data
* ``GET  /api/v1/admin/jobs/{job_id}``                — check job status / result (B-4)

Architecture:
    Follows ARCH-DPEN-001 — all services arrive via ``Depends``.
    Follows ARCH-JOBS-001 — generation is submitted as a persistent job,
    not executed synchronously. Endpoint returns HTTP 202 immediately.

    The "generate-from-data" endpoint converts user-supplied rows to a
    temporary Parquet in S3 (``temp/uploads/{uuid}.parquet``) and then
    enqueues the *same* ``graphics_generate`` job type with that key —
    the ``GraphicPipeline`` itself is unchanged (it simply loads the
    Parquet from Stage 1).
"""

from __future__ import annotations

import hashlib
import io
import json
import uuid

import polars as pl
import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas.admin_graphics import (
    GenerateFromDataRequest,
    GraphicsGenerateRequest,
    GraphicsGenerateResponse,
    JobStatusResponse,
    PublicationResponse,
)
from src.core.database import get_db
from src.core.logging import get_logger
from src.core.storage import StorageInterface, get_storage_manager
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


def _get_storage() -> StorageInterface:
    """Provide a StorageInterface via dependency injection."""
    return get_storage_manager()


def _compute_config_hash(chart_type: str, size: tuple[int, int], title: str) -> str:
    """Compute a deterministic SHA-256 hex digest of the chart config.

    Callers typically slice the first 16 chars for dedupe keys.
    """
    config_dict = {
        "chart_type": chart_type,
        "size": list(size),
        "title": title,
    }
    return hashlib.sha256(
        json.dumps(config_dict, sort_keys=True).encode("utf-8")
    ).hexdigest()


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
    config_hash = _compute_config_hash(body.chart_type, body.size, body.title)[:16]
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
# POST /api/v1/admin/graphics/generate-from-data  (uploaded JSON/CSV)
# ---------------------------------------------------------------------------


def _cast_uploaded_dataframe(
    df: pl.DataFrame, columns: list, *, strict: bool = False
) -> pl.DataFrame:
    """Apply per-column dtype coercion as specified by the caller.

    Columns whose ``dtype`` is ``"str"`` are left untouched; ``"int"``
    and ``"float"`` go through Polars ``cast``; ``"date"`` goes through
    ``str.to_date``.  Values that fail to coerce become ``None``
    (``strict=False``), matching the UX expectation that an upload with
    a single malformed cell should not 500 the whole request.
    """
    for col in columns:
        if col.name not in df.columns:
            continue
        if col.dtype == "int":
            df = df.with_columns(pl.col(col.name).cast(pl.Int64, strict=strict))
        elif col.dtype == "float":
            df = df.with_columns(pl.col(col.name).cast(pl.Float64, strict=strict))
        elif col.dtype == "date":
            df = df.with_columns(
                pl.col(col.name).cast(pl.Utf8).str.to_date(strict=strict)
            )
    return df


@router.post(
    "/graphics/generate-from-data",
    response_model=GraphicsGenerateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Enqueue graphic generation from uploaded data",
    responses={
        202: {"description": "Job enqueued — poll GET /api/v1/admin/jobs/{job_id}."},
        422: {"description": "Data is empty, oversized, or cannot be parsed."},
    },
)
async def generate_from_data(
    body: GenerateFromDataRequest,
    job_repo: JobRepository = Depends(_get_job_repo),
    storage: StorageInterface = Depends(_get_storage),
) -> GraphicsGenerateResponse:
    """Enqueue a graphic generation job from user-uploaded JSON/CSV data.

    Flow:
        1. Build a Polars DataFrame from ``body.data`` and apply the
           requested column dtypes.
        2. Serialize the DataFrame to Parquet bytes.
        3. Upload to ``temp/uploads/{uuid}.parquet`` via
           ``StorageInterface.upload_bytes``.
        4. Enqueue a ``graphics_generate`` job whose ``data_key`` points
           at the temp Parquet — downstream ``GraphicPipeline`` is
           unchanged (Stage 1 loads the Parquet from storage).

    Returns HTTP 202 with ``job_id`` and current ``status``.
    """
    # 1. Build + coerce DataFrame
    try:
        df = pl.DataFrame(body.data)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to build DataFrame from data: {exc}",
        )
    df = _cast_uploaded_dataframe(df, body.columns)

    # 2. Serialize to Parquet bytes via an in-memory buffer.
    buf = io.BytesIO()
    df.write_parquet(buf)
    parquet_bytes = buf.getvalue()

    # 3. Upload under temp/uploads/
    temp_key = f"temp/uploads/{uuid.uuid4().hex}.parquet"
    await storage.upload_bytes(data=parquet_bytes, key=temp_key)

    # 4. Build payload + dedupe key, then enqueue same job type
    payload = GraphicsGeneratePayload(
        data_key=temp_key,
        chart_type=body.chart_type,
        title=body.title,
        size=body.size,
        category=body.category,
        source_product_id=None,  # not a StatCan source
    )
    config_hash = _compute_config_hash(body.chart_type, body.size, body.title)
    dedupe_key = f"graphics:custom:{temp_key}:{config_hash[:16]}"

    result = await job_repo.enqueue(
        job_type="graphics_generate",
        payload_json=payload.model_dump_json(),
        dedupe_key=dedupe_key,
        created_by="admin_api",
    )

    logger.info(
        "graphics_generate_from_data_enqueued",
        job_id=result.job.id,
        created=result.created,
        temp_key=temp_key,
        source_label=body.source_label,
        row_count=len(body.data),
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
