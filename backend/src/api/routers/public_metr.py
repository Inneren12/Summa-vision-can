"""Public METR calculator endpoints — Theme #2 (Marginal Tax Rate Meatgrinder).

Provides three public endpoints for computing and comparing Marginal
Effective Tax Rates across Canadian provinces:

* ``GET /api/v1/public/metr/calculate`` — METR at a specific income point
* ``GET /api/v1/public/metr/curve``     — full METR curve across income range
* ``GET /api/v1/public/metr/compare``   — provincial METR comparison

All endpoints are **public** (no auth required). Rate-limited to
200 req/min per IP via :class:`InMemoryRateLimiter`.

Architecture: pure CPU calculations — no DB, no network I/O.
The engine functions are pure (ARCH-PURA-001).
"""

from __future__ import annotations

from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse

from src.core.security.ip_rate_limiter import InMemoryRateLimiter
from src.schemas.metr import (
    AnnotationResponse,
    CurvePoint,
    DeadZoneResponse,
    METRCalculateResponse,
    METRCompareResponse,
    METRComponentsResponse,
    METRCurveResponse,
    PeakResponse,
    ProvinceCompareItem,
)
from src.services.metr.engine import (
    FamilyType,
    METRInput,
    Province,
    calculate_metr,
    classify_zone,
    find_dead_zones,
    generate_curve,
)

router = APIRouter(prefix="/api/v1/public/metr", tags=["public-metr"])


# ---------------------------------------------------------------------------
# Rate limiter — 200 requests per minute per IP (lightweight CPU calculations)
# ---------------------------------------------------------------------------


# Slider UI debounces at 500ms (theoretical max ~120/min per user).
# 200/min gives headroom for rapid parameter changes. CPU-only, no DB.
METR_RATE_LIMIT_PER_MINUTE = 200


@lru_cache(maxsize=1)
def get_metr_limiter() -> InMemoryRateLimiter:
    """Singleton METR rate limiter. Tests override via app.dependency_overrides."""
    return InMemoryRateLimiter(max_requests=METR_RATE_LIMIT_PER_MINUTE, window_seconds=60)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/calculate",
    response_model=METRCalculateResponse,
    status_code=status.HTTP_200_OK,
    summary="Calculate METR at a specific income point",
    responses={
        200: {"description": "METR calculation with component breakdown."},
        429: {"description": "Rate limit exceeded."},
    },
)
async def calculate_metr_endpoint(
    request: Request,
    income: int = Query(ge=0, le=500_000, description="Annual gross employment income."),
    province: Province = Query(default=Province.ON, description="Province code (ON, BC, AB, QC)."),
    family_type: FamilyType = Query(default=FamilyType.SINGLE, description="Family type."),
    n_children: int = Query(default=0, ge=0, le=6, description="Number of children."),
    children_under_6: int = Query(default=0, ge=0, le=6, description="Children under age 6."),
    limiter: InMemoryRateLimiter = Depends(get_metr_limiter),
) -> JSONResponse:
    """Calculate METR at a specific income point with full component breakdown."""
    client_ip = request.client.host if request.client else "unknown"
    if not limiter.is_allowed(client_ip):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Rate limit exceeded. Try again later.")

    if children_under_6 > n_children:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"children_under_6 ({children_under_6}) cannot exceed n_children ({n_children})",
        )

    inp = METRInput(
        gross_income=income,
        province=province,
        family_type=family_type,
        n_children=n_children,
        children_under_6=children_under_6,
    )
    result = calculate_metr(inp)

    body = METRCalculateResponse(
        gross_income=result.gross_income,
        net_income=result.net_income,
        metr=result.metr,
        zone=classify_zone(result.metr),
        keep_per_dollar=round(1 - result.metr / 100, 3),
        components=METRComponentsResponse(
            federal_tax=result.components.federal_tax,
            provincial_tax=result.components.provincial_tax,
            cpp=result.components.cpp,
            cpp2=result.components.cpp2,
            ei=result.components.ei,
            ohp=result.components.ohp,
            ccb=result.components.ccb,
            gst_credit=result.components.gst_credit,
            cwb=result.components.cwb,
            provincial_benefits=result.components.provincial_benefits,
        ),
    )

    return JSONResponse(
        content=body.model_dump(mode="json"),
        status_code=status.HTTP_200_OK,
    )


@router.get(
    "/curve",
    response_model=METRCurveResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate full METR curve for the interactive chart",
    responses={
        200: {"description": "METR curve with dead zones and annotations."},
        429: {"description": "Rate limit exceeded."},
    },
)
async def metr_curve_endpoint(
    request: Request,
    province: Province = Query(default=Province.ON, description="Province code."),
    family_type: FamilyType = Query(default=FamilyType.SINGLE, description="Family type."),
    n_children: int = Query(default=0, ge=0, le=6, description="Number of children."),
    children_under_6: int = Query(default=0, ge=0, le=6, description="Children under 6."),
    income_min: int = Query(default=15_000, ge=0, description="Income range start."),
    income_max: int = Query(default=155_000, le=500_000, description="Income range end."),
    step: int = Query(default=1_000, ge=500, le=5_000, description="Income step size."),
    limiter: InMemoryRateLimiter = Depends(get_metr_limiter),
) -> JSONResponse:
    """Generate full METR curve across an income range."""
    client_ip = request.client.host if request.client else "unknown"
    if not limiter.is_allowed(client_ip):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Rate limit exceeded. Try again later.")

    if children_under_6 > n_children:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"children_under_6 ({children_under_6}) cannot exceed n_children ({n_children})",
        )

    curve = generate_curve(
        province=province,
        family_type=family_type,
        n_children=n_children,
        children_under_6=children_under_6,
        income_min=income_min,
        income_max=income_max,
        step=step,
    )

    dead_zones = find_dead_zones(curve)

    # Find peak METR
    peak_point = max(curve, key=lambda p: p.metr) if curve else None

    # Build annotations for notable points
    annotations: list[AnnotationResponse] = []
    if peak_point and peak_point.metr >= 45:
        keep = round(1 - peak_point.metr / 100, 2)
        annotations.append(AnnotationResponse(
            gross=peak_point.gross,
            metr=peak_point.metr,
            label=f"Earn $1 more. Keep {keep * 100:.0f}\u00a2.",
        ))

    # Find the point where METR drops back to normal after dead zones
    if dead_zones:
        last_dz_end = dead_zones[-1].end
        for p in curve:
            if p.gross > last_dz_end and p.metr < 45:
                annotations.append(AnnotationResponse(
                    gross=p.gross,
                    metr=p.metr,
                    label="Clawbacks cleared",
                ))
                break

    body = METRCurveResponse(
        province=province.value,
        family_type=family_type.value,
        n_children=n_children,
        children_under_6=children_under_6,
        curve=[CurvePoint(gross=p.gross, net=p.net, metr=p.metr, zone=p.zone) for p in curve],
        dead_zones=[
            DeadZoneResponse(start=dz.start, end=dz.end, peak_metr=dz.peak_metr)
            for dz in dead_zones
        ],
        peak=PeakResponse(
            gross=peak_point.gross if peak_point else 0,
            metr=peak_point.metr if peak_point else 0,
        ),
        annotations=annotations,
    )

    return JSONResponse(
        content=body.model_dump(mode="json"),
        status_code=status.HTTP_200_OK,
    )


@router.get(
    "/compare",
    response_model=METRCompareResponse,
    status_code=status.HTTP_200_OK,
    summary="Compare METR across all 4 provinces at a given income point",
    responses={
        200: {"description": "Provincial METR comparison, sorted by METR descending."},
        429: {"description": "Rate limit exceeded."},
    },
)
async def metr_compare_provinces(
    request: Request,
    income: int = Query(ge=15_000, le=300_000, description="Gross income."),
    family_type: FamilyType = Query(default=FamilyType.SINGLE_PARENT, description="Family type."),
    n_children: int = Query(default=2, ge=0, le=6, description="Number of children."),
    children_under_6: int = Query(default=2, ge=0, le=6, description="Children under 6."),
    limiter: InMemoryRateLimiter = Depends(get_metr_limiter),
) -> JSONResponse:
    """Compare METR across all 4 provinces at a given income point.

    Note: Quebec results use simplified modelling (separate Revenu Québec
    filing is not modelled).
    """
    client_ip = request.client.host if request.client else "unknown"
    if not limiter.is_allowed(client_ip):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Rate limit exceeded. Try again later.")

    if children_under_6 > n_children:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"children_under_6 ({children_under_6}) cannot exceed n_children ({n_children})",
        )

    results: list[ProvinceCompareItem] = []
    for prov in Province:
        inp = METRInput(
            gross_income=income,
            province=prov,
            family_type=family_type,
            n_children=n_children,
            children_under_6=children_under_6,
        )
        result = calculate_metr(inp)
        results.append(ProvinceCompareItem(
            province=prov.value,
            metr=result.metr,
            zone=classify_zone(result.metr),
        ))

    # Sort by METR descending
    results.sort(key=lambda x: x.metr, reverse=True)

    body = METRCompareResponse(
        income=income,
        family_type=family_type.value,
        provinces=results,
    )

    return JSONResponse(
        content=body.model_dump(mode="json"),
        status_code=status.HTTP_200_OK,
    )
