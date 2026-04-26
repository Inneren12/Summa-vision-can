"""Structured error response schemas for admin endpoints with error_code contract.

See docs/debt-030-recon.md for vocabulary and design rationale.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class StructuredErrorDetail(BaseModel):
    """Detail payload for HTTPException(detail=...) when emitting structured codes."""

    error_code: str = Field(
        ...,
        description="Stable machine-readable error identifier (UPPER_SNAKE_CASE).",
    )
    message: str = Field(
        ...,
        description="Human-readable EN fallback message.",
    )
    details: dict[str, Any] | None = Field(
        default=None,
        description="Optional structured context (e.g., field validation errors).",
    )


class StructuredErrorResponse(BaseModel):
    """Top-level FastAPI response shape: {'detail': {error_code, message, details?}}."""

    detail: StructuredErrorDetail
