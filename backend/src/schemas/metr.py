"""Pydantic response schemas for METR API endpoints.

These are the API-layer contracts — they define the JSON shape
returned to clients.  The calculation engine uses its own frozen
dataclasses internally.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class METRComponentsResponse(BaseModel):
    """Breakdown of tax/benefit components at a given income point."""

    model_config = ConfigDict(from_attributes=True)

    federal_tax: float
    provincial_tax: float
    cpp: float
    cpp2: float
    ei: float
    ohp: float
    ccb: float
    gst_credit: float
    cwb: float
    provincial_benefits: float


class METRCalculateResponse(BaseModel):
    """Response for ``GET /api/v1/public/metr/calculate``."""

    gross_income: int
    net_income: int
    metr: float
    zone: str
    keep_per_dollar: float
    components: METRComponentsResponse


class CurvePoint(BaseModel):
    """Single point on the METR curve."""

    gross: int
    net: int
    metr: float
    zone: str


class DeadZoneResponse(BaseModel):
    """Contiguous income range where METR exceeds threshold."""

    start: int
    end: int
    peak_metr: float


class PeakResponse(BaseModel):
    """Peak METR point on the curve."""

    gross: int
    metr: float


class AnnotationResponse(BaseModel):
    """Annotation for a notable point on the curve."""

    gross: int
    metr: float
    label: str


class METRCurveResponse(BaseModel):
    """Response for ``GET /api/v1/public/metr/curve``."""

    province: str
    family_type: str
    n_children: int
    children_under_6: int
    curve: list[CurvePoint]
    dead_zones: list[DeadZoneResponse]
    peak: PeakResponse
    annotations: list[AnnotationResponse]


class ProvinceCompareItem(BaseModel):
    """METR result for one province in the comparison."""

    province: str
    metr: float
    zone: str


class METRCompareResponse(BaseModel):
    """Response for ``GET /api/v1/public/metr/compare``."""

    income: int
    family_type: str
    provinces: list[ProvinceCompareItem]
