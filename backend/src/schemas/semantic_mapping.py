"""Phase 3.1a: Pydantic schemas for SemanticMapping."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


# Frequency must match resolver branches in 3.1c
Frequency = Literal["monthly", "quarterly", "annual"]

# Metrics supported in Phase 3.1
SupportedMetric = Literal[
    "current_value",
    "year_over_year_change",
    "previous_period_change",
]


class SemanticMappingConfig(BaseModel):
    """JSONB ``config`` shape for SemanticMapping.

    Validated at app layer (read/write boundary). DB stores as opaque
    JSONB so config shape can evolve without migration during early
    Phase 3 iteration.
    """

    dimension_filters: dict[str, str] = Field(
        ...,
        min_length=1,  # at least one filter — empty cell selection is meaningless
        description=(
            "Fixed filters identifying the specific cube cell. Example: "
            "{'Geography': 'Canada', 'Products': 'All-items'}. "
            "Operator-facing labels in EN (FR support deferred)."
        ),
    )
    measure: str = Field(
        ...,
        min_length=1,
        description="Cube measure column name to read (e.g. 'Value').",
    )
    unit: str = Field(
        ...,
        min_length=1,
        description="Display unit ('index', 'CAD', '%', 'persons').",
    )
    frequency: Frequency = Field(
        ...,
        description=(
            "Cube reporting frequency. Drives metric calculation in "
            "resolver (3.1c): MoM/QoQ/YoY = previous_period_change for "
            "monthly/quarterly/annual."
        ),
    )
    supported_metrics: list[SupportedMetric] = Field(
        default_factory=lambda: [
            "current_value",
            "year_over_year_change",
            "previous_period_change",
        ],
        description="Which metrics the resolver can compute for this mapping.",
    )
    default_geo: str | None = Field(
        default=None,
        description="Display hint for picker UI; not used at resolution time.",
    )
    notes: str | None = None

    model_config = ConfigDict(extra="forbid")


class SemanticMappingCreate(BaseModel):
    cube_id: str = Field(..., min_length=1, max_length=50)
    product_id: int = Field(
        ...,
        ge=1,
        description=(
            "StatCan WDS productId. Persisted on the row so admin edit "
            "flows can hydrate the form without a cache round-trip."
        ),
    )
    semantic_key: str = Field(
        ..., min_length=1, max_length=200, pattern=r"^[a-z0-9_.-]+$"
    )
    label: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    config: SemanticMappingConfig
    is_active: bool = True

    model_config = ConfigDict(extra="forbid")


class SemanticMappingUpdate(BaseModel):
    """Partial update — admin CRUD in 3.1b will use this."""

    label: str | None = None
    description: str | None = None
    config: SemanticMappingConfig | None = None
    is_active: bool | None = None

    model_config = ConfigDict(extra="forbid")


class SemanticMappingResponse(BaseModel):
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
