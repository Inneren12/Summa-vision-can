"""Phase 3.1c — :class:`ResolvedValueResponse` DTO (schema).

Verbatim from the impl-addendum §"REPLACEMENT — Phase 6 schema content".
11 fields. ``value`` is nullable (FIX-2 missing-observation contract);
``missing`` is a required raw-passthrough boolean from the cache row.

NO ``populate_by_name`` (alias-driven serialization is intentionally
absent — fields use their snake_case names on the wire).
NO ``prime_warning`` field (recon F-fix-2 removed this — errors surface
via structured logs and ``RESOLVE_CACHE_MISS.details`` only).
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ResolvedValueResponse(BaseModel):
    cube_id: str = Field(description="Cube identifier.")
    semantic_key: str = Field(description="Semantic mapping key.")
    coord: str = Field(
        description=(
            "Service-derived StatCan coordinate string echoed from cache row."
        )
    )
    period: str = Field(description="Resolved period token (ref_period).")
    value: str | None = Field(
        default=None,
        description=(
            "Canonical stringified numeric value. None when the observation "
            "is suppressed/missing upstream (paired with missing=True)."
        ),
    )
    missing: bool = Field(
        description=(
            "Raw passthrough from cache row. True when the upstream "
            "observation is absent/suppressed; in that case value is None."
        ),
    )
    resolved_at: datetime = Field(
        description="Alias of cache row fetched_at timestamp."
    )
    source_hash: str = Field(description="Opaque cache provenance hash.")
    is_stale: bool = Field(description="Persisted stale marker from cache row.")
    units: str | None = Field(
        default=None,
        description="Unit from mapping.config.unit if string, else null.",
    )
    cache_status: Literal["hit", "primed"] = Field(description="Resolve status.")
    mapping_version: int | None = Field(
        default=None, description="Optional semantic mapping version."
    )


__all__ = ["ResolvedValueResponse"]
