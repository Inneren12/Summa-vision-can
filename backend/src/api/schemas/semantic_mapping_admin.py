"""Phase 3.1b: admin request/response models for semantic mappings.

The flat 3.1a :class:`SemanticMappingCreate` is reused for the validated
upsert payload; this module adds the admin-only fields ``product_id``
(StatCan numeric ID required by the cache lookup) and the optimistic
concurrency token ``if_match_version`` (also accepted via ``If-Match``
header per the hybrid concurrency convention; see DEBT-054).
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from src.schemas.semantic_mapping import (
    SemanticMappingConfig,
    SemanticMappingResponse,
)


class SemanticMappingUpsertRequest(BaseModel):
    """Body for ``POST /api/v1/admin/semantic-mappings/upsert``."""

    cube_id: str = Field(..., min_length=1, max_length=50)
    product_id: int = Field(..., ge=1)
    semantic_key: str = Field(
        ..., min_length=1, max_length=200, pattern=r"^[a-z0-9_.-]+$"
    )
    label: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    config: SemanticMappingConfig
    is_active: bool = True
    updated_by: str | None = None
    if_match_version: int | None = Field(
        default=None,
        description=(
            "Optimistic concurrency token. Hybrid: header ``If-Match`` "
            "takes precedence; falls back to this body field."
        ),
    )

    model_config = ConfigDict(extra="forbid")


class SemanticMappingListItem(BaseModel):
    """Single row in the admin list response."""

    id: int
    cube_id: str
    product_id: int
    semantic_key: str
    label: str
    description: str | None
    config: SemanticMappingConfig
    is_active: bool
    version: int
    created_at: datetime
    updated_at: datetime
    updated_by: str | None

    model_config = ConfigDict(from_attributes=True)


class SemanticMappingListResponse(BaseModel):
    """Pagination wrapper for the admin list endpoint."""

    items: list[SemanticMappingListItem]
    total: int
    limit: int
    offset: int


# Re-export the canonical row response so router imports stay flat.
__all__ = [
    "SemanticMappingListItem",
    "SemanticMappingListResponse",
    "SemanticMappingResponse",
    "SemanticMappingUpsertRequest",
]
