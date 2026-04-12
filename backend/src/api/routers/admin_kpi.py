"""Admin KPI endpoint — aggregated dashboard metrics (C-5).

Provides a single endpoint returning all KPI data needed for the
Flutter admin dashboard.

Architecture:
    Follows ARCH-DPEN-001 — KPIService injected via ``Depends``.
    Protected by AuthMiddleware (under ``/api/v1/admin/*``).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status

from src.core.database import get_session_factory
from src.schemas.kpi import KPIResponse
from src.services.kpi.kpi_service import KPIService

# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


# ---------------------------------------------------------------------------
# Dependency helpers
# ---------------------------------------------------------------------------


def _get_kpi_service() -> KPIService:
    """Provide a KPIService with the shared session factory."""
    return KPIService(get_session_factory())


# ---------------------------------------------------------------------------
# GET /api/v1/admin/kpi
# ---------------------------------------------------------------------------


@router.get(
    "/kpi",
    response_model=KPIResponse,
    status_code=status.HTTP_200_OK,
    summary="Get KPI dashboard metrics",
    responses={
        200: {"description": "Aggregated KPI metrics for the given period."},
    },
)
async def get_kpi(
    days: int = Query(default=30, ge=1, le=365),
    kpi_service: KPIService = Depends(_get_kpi_service),
) -> KPIResponse:
    """Return aggregated KPI metrics over the specified time window.

    Query parameters:
        days: Aggregation window in days (1–365, default 30).
    """
    return await kpi_service.get_kpi(days=days)
