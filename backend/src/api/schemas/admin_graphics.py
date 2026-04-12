"""Pydantic schemas for the admin graphics endpoints.

Request and response models for:

* ``GET  /api/v1/admin/queue``                — draft publication listing
* ``POST /api/v1/admin/graphics/generate``    — enqueue generation job (B-4)
* ``GET  /api/v1/admin/jobs/{job_id}``        — job status lookup (B-4)
"""

from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, ConfigDict


# ---------------------------------------------------------------------------
# Shared response schema (queue endpoint)
# ---------------------------------------------------------------------------


class PublicationResponse(BaseModel):
    """Admin-facing publication representation for the queue endpoint.

    Attributes:
        id: Publication primary key.
        headline: Short title of the graphic.
        chart_type: Type of chart (e.g. ``"BAR"``, ``"LINE"``).
        virality_score: AI-estimated virality score (0.0 – 10.0).
        status: Current lifecycle status (``DRAFT`` or ``PUBLISHED``).
        created_at: UTC timestamp of record creation.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    headline: str
    chart_type: str
    virality_score: float | None = None
    status: str
    created_at: datetime


# ---------------------------------------------------------------------------
# POST /graphics/generate  (B-4 — persistent job)
# ---------------------------------------------------------------------------


class GraphicsGenerateRequest(BaseModel):
    """Request body for enqueuing a graphic generation job.

    Attributes:
        data_key: S3 key to source Parquet file.
        chart_type: Chart variant (``"line"``, ``"bar"``, ``"area"``, etc.).
        title: Chart headline text.
        size: Output pixel dimensions ``(width, height)``.
        category: Background template category.
        source_product_id: Optional StatCan product ID for versioning lineage.
    """

    data_key: str
    chart_type: str
    title: str
    size: tuple[int, int] = (1080, 1080)
    category: str
    source_product_id: str | None = None


class GraphicsGenerateResponse(BaseModel):
    """Immediate response when a generation job is enqueued (HTTP 202).

    Attributes:
        job_id: Persistent job primary key (as string).
        status: Job status at time of response (``"queued"`` or ``"running"``).
    """

    job_id: str
    status: str


# ---------------------------------------------------------------------------
# GET /jobs/{job_id}  (B-4 — job status)
# ---------------------------------------------------------------------------


class JobStatusResponse(BaseModel):
    """Full job status representation for the admin panel.

    Attributes:
        job_id: Job primary key.
        job_type: Job type identifier.
        status: Current lifecycle status.
        result_json: JSON result on success (contains GenerationResult fields).
        error_code: Machine-readable error code on failure.
        error_message: Human-readable error description on failure.
        created_at: When the job was enqueued.
        started_at: When the job was last claimed by a runner.
        finished_at: When the job reached a terminal state.
    """

    job_id: str
    job_type: str
    status: str
    result_json: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
