"""Pydantic schemas for the admin graphics endpoints.

Request and response models for:

* ``GET /api/v1/admin/queue``  — draft publication listing
* ``POST /api/v1/admin/graphics/generate`` — generation trigger
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Shared response schema
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
# POST /generate
# ---------------------------------------------------------------------------


class GenerateRequest(BaseModel):
    """Request body for triggering graphic generation.

    Attributes:
        brief_id: Primary key of the ``Publication`` (DRAFT) to generate.
        size_preset: Target social-media platform size.
        dpi: Rendering DPI for SVG rasterisation (72–300).
        watermark: Whether to apply a semi-transparent watermark.
    """

    brief_id: int
    size_preset: Literal["instagram", "twitter", "reddit"] = "instagram"
    dpi: int = Field(default=150, ge=72, le=300)
    watermark: bool = True


class GenerateResponse(BaseModel):
    """Immediate response returned when generation is submitted (HTTP 202).

    Attributes:
        task_id: UUID string for polling via ``GET /tasks/{task_id}``.
        message: Human-readable confirmation.
    """

    task_id: str
    message: str = "Generation started"
