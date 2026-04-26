"""Pydantic schemas for the Transform API endpoints."""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, Field


class TransformOperation(BaseModel):
    """A single transformation step.

    Example:
        {"type": "filter_geo", "params": {"geography": "Alberta"}}
        {"type": "aggregate_time", "params": {"freq": "Q", "method": "mean"}}
        {"type": "calc_yoy_change", "params": {}}
    """

    type: str = Field(
        description="Transform function name from DataWorkbench"
    )
    params: dict[str, Any] = Field(
        default_factory=dict,
        description="Keyword arguments for the transform function",
    )


class TransformRequest(BaseModel):
    """Request body for POST /data/transform."""

    source_keys: list[str] = Field(
        min_length=1,
        description="S3/storage keys for Parquet source files",
    )
    operations: list[TransformOperation] = Field(
        min_length=1,
        description="Ordered list of transform operations to apply",
    )
    output_key: str | None = Field(
        default=None,
        description="Custom output storage key. Auto-generated if None.",
    )


class TransformResponse(BaseModel):
    """Response for POST /data/transform."""

    output_key: str = Field(description="Storage key for result Parquet")
    rows: int = Field(description="Number of rows in result")
    columns: int = Field(description="Number of columns in result")


class CubeFetchRequest(BaseModel):
    """Request body for POST /cubes/{product_id}/fetch."""

    periods: int | None = Field(
        default=None,
        description="Override dynamic periods (default: based on frequency)",
    )


class PreviewResponse(BaseModel):
    """Response for GET /data/preview/{storage_key}."""

    storage_key: str
    rows: int
    columns: int
    column_names: list[str]
    data: list[dict[str, Any]]
    product_id: str | None = None  # Phase 1.5: StatCan product ID parsed from storage_key (None for non-StatCan paths)
