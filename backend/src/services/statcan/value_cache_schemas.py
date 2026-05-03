"""Phase 3.1aaa: Pydantic + dataclass schemas for the value-cache pipeline.

Three families live here:

1. **Wire-format Pydantic models** for parsing
   ``getDataFromCubePidCoordAndLatestNPeriods`` responses
   (``StatCanDataPoint``, ``StatCanDataResponse``, ``StatCanDataEnvelope``).
2. **Internal DTOs** (frozen dataclasses) used at the
   repository ↔ service boundary (``ValueCacheRow``, ``ValueCacheUpsertItem``).
3. **Service-result objects** returned by
   :class:`StatCanValueCacheService` (``AutoPrimeResult``,
   ``RefreshSummary``, ``ResolvedValue``).

Mirrors ``src/services/statcan/schemas.py`` style: Pydantic V2,
``populate_by_name=True``, alias-driven camelCase → snake_case mapping.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---------------------------------------------------------------------------
# Wire format — StatCan getDataFromCubePidCoordAndLatestNPeriods
# ---------------------------------------------------------------------------


class StatCanDataPoint(BaseModel):
    """A single ``vectorDataPoint`` element from the WDS response.

    Permissive on dispensable text fields (``refPer2``, ``refPerRaw2``)
    because the StatCan response shape varies across cube types.
    """

    ref_per: str = Field(alias="refPer")
    ref_per2: str = Field(default="", alias="refPer2")
    ref_per_raw: str = Field(default="", alias="refPerRaw")
    ref_per_raw2: str = Field(default="", alias="refPerRaw2")
    value: Decimal | None = None
    decimals: int = 0
    scalar_factor_code: int = Field(default=0, alias="scalarFactorCode")
    symbol_code: int = Field(default=0, alias="symbolCode")
    security_level_code: int = Field(default=0, alias="securityLevelCode")
    status_code: int = Field(default=0, alias="statusCode")
    frequency_code: int | None = Field(default=None, alias="frequencyCode")
    release_time: datetime | None = Field(default=None, alias="releaseTime")
    missing: bool = False

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("missing", mode="before")
    @classmethod
    def _coerce_missing(cls, v: object) -> bool:
        # WDS occasionally serialises this as the string "false"/"true".
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.strip().lower() == "true"
        return bool(v)


class StatCanDataResponse(BaseModel):
    """Inner ``object`` payload of a SUCCESS envelope."""

    response_status_code: int | None = Field(
        default=None, alias="responseStatusCode"
    )
    product_id: int = Field(alias="productId")
    coordinate: str
    vector_id: int | None = Field(default=None, alias="vectorId")
    vector_data_point: list[StatCanDataPoint] = Field(
        default_factory=list, alias="vectorDataPoint"
    )

    model_config = ConfigDict(populate_by_name=True)


class StatCanDataEnvelope(BaseModel):
    """Top-level array item: ``{"status": "SUCCESS"|"FAILED", "object": ...}``."""

    status: str
    object: StatCanDataResponse | str | None = None

    model_config = ConfigDict(populate_by_name=True)


# ---------------------------------------------------------------------------
# Internal DTOs — repository ↔ service
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ValueCacheRow:
    """Immutable view of a ``semantic_value_cache`` row."""

    id: int
    cube_id: str
    product_id: int
    semantic_key: str
    coord: str
    ref_period: str
    period_start: date | None
    value: Decimal | None
    missing: bool
    decimals: int
    scalar_factor_code: int
    symbol_code: int
    security_level_code: int
    status_code: int
    frequency_code: int | None
    vector_id: int | None
    response_status_code: int | None
    source_hash: str
    fetched_at: datetime
    release_time: datetime | None
    is_stale: bool


@dataclass(frozen=True)
class ValueCacheUpsertItem:
    """Input for ``SemanticValueCacheRepository.upsert_periods_batch``."""

    cube_id: str
    product_id: int
    semantic_key: str
    coord: str
    data_point: StatCanDataPoint
    fetched_at: datetime


# ---------------------------------------------------------------------------
# Service-result objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AutoPrimeResult:
    """Returned from :meth:`StatCanValueCacheService.auto_prime`.

    Per founder lock Q-3 (best-effort): a non-``None`` ``error`` means
    the prime did not execute successfully but the caller should
    continue. ``error is None`` and zero counts together mean a no-op
    (e.g. nothing to insert).
    """

    rows_inserted: int
    rows_updated: int
    rows_unchanged: int
    error: str | None = None


@dataclass(frozen=True)
class RefreshSummary:
    """Returned from :meth:`StatCanValueCacheService.refresh_all` (nightly)."""

    mappings_processed: int
    rows_upserted: int
    rows_marked_stale: int
    errors: list[str]


class ResolvedValue(BaseModel):
    """API-boundary DTO that 3.1c will consume from ``get_cached``.

    ``value`` is the canonical stringification of the underlying
    ``Decimal`` (founder lock Q-4): preserves precision across
    JSON/HTTP boundaries. ``units`` is reserved for the canonical
    units-mapping work tracked under DEBT-060.
    """

    cube_id: str
    product_id: int
    semantic_key: str
    coord: str
    ref_period: str
    period_start: date | None = None
    value: str
    missing: bool
    decimals: int
    units: str | None = None
    source_hash: str
    fetched_at: datetime
    is_stale: bool

    model_config = ConfigDict(populate_by_name=True)
