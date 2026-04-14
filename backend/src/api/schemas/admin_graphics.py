"""Pydantic schemas for the admin graphics endpoints.

Request and response models for:

* ``GET  /api/v1/admin/queue``                        — draft publication listing
* ``POST /api/v1/admin/graphics/generate``            — enqueue generation job (B-4)
* ``POST /api/v1/admin/graphics/generate-from-data``  — enqueue generation job from uploaded data
* ``GET  /api/v1/admin/jobs/{job_id}``                — job status lookup (B-4)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, field_validator


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
# POST /graphics/generate-from-data  (user-uploaded JSON/CSV)
# ---------------------------------------------------------------------------


class RawDataColumn(BaseModel):
    """Column definition used to apply dtype coercion on an uploaded row set.

    Attributes:
        name: Column name as it appears in the uploaded rows.
        dtype: Target Polars dtype.  ``"str"`` leaves the column unchanged;
            ``"int"``/``"float"`` cast via Polars; ``"date"`` parses ISO
            ``yyyy-mm-dd`` strings.
    """

    name: str
    dtype: Literal["str", "int", "float", "date"] = "str"


class GenerateFromDataRequest(BaseModel):
    """Request body for generating a graphic from user-uploaded data.

    The caller supplies raw rows (parsed from JSON or CSV on the client)
    and column definitions.  The endpoint writes a temporary Parquet
    under ``temp/uploads/{uuid}.parquet`` and then enqueues the existing
    ``graphics_generate`` job referencing that key — the downstream
    pipeline is *unchanged*.

    Attributes:
        data: Rows as a list of dicts.  Must be non-empty and must
            contain at most ``10_000`` rows (R15 hard cap).
        columns: Column definitions for optional dtype coercion.
        chart_type: Chart variant (``"line"``, ``"bar"``, ``"area"``, ...).
        title: Chart headline text.
        size: Output pixel dimensions ``(width, height)`` — default 1200×900.
        category: Background template category.
        source_label: Human-readable source tag stored on metadata instead
            of a StatCan ``source_product_id``.  Defaults to ``"custom"``.
    """

    data: list[dict[str, Any]]
    columns: list[RawDataColumn]
    chart_type: str
    title: str
    size: tuple[int, int] = (1200, 900)
    category: str
    source_label: str = "custom"

    @field_validator("data")
    @classmethod
    def validate_data_not_empty(cls, v: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Reject empty row sets and enforce the R15 10k-row hard cap."""
        if not v:
            raise ValueError("data must contain at least one row")
        if len(v) > 10_000:
            raise ValueError("data must not exceed 10,000 rows (R15)")
        return v

    @field_validator("size")
    @classmethod
    def validate_size(cls, v: tuple[int, int]) -> tuple[int, int]:
        """Clamp dimensions to the 1–4096 px admissible range."""
        w, h = v
        if w <= 0 or h <= 0 or w > 4096 or h > 4096:
            raise ValueError("dimensions must be 1-4096")
        return v


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
