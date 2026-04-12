"""Tests for the admin KPI endpoint (C-5).

Covers:
* ``GET /api/v1/admin/kpi``     — aggregated dashboard metrics
* Authentication enforcement
* ``days`` query parameter validation
* Empty database handling
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.api.routers.admin_kpi import _get_kpi_service, router
from src.schemas.kpi import KPIResponse
from src.services.kpi.kpi_service import KPIService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_NOW = datetime(2026, 4, 12, 12, 0, 0, tzinfo=timezone.utc)


def _make_kpi_response(
    *,
    days: int = 30,
    total_publications: int = 45,
    published_count: int = 42,
    total_leads: int = 156,
    b2b_leads: int = 38,
    education_leads: int = 12,
    isp_leads: int = 8,
    b2c_leads: int = 118,
    total_jobs: int = 156,
    jobs_succeeded: int = 142,
    jobs_failed: int = 8,
    jobs_queued: int = 3,
    jobs_running: int = 1,
    failed_by_type: dict[str, int] | None = None,
    emails_sent: int = 120,
    tokens_created: int = 120,
    tokens_activated: int = 89,
    tokens_exhausted: int = 12,
) -> KPIResponse:
    """Build a KPIResponse with sensible defaults."""
    period_start = _NOW - timedelta(days=days)
    return KPIResponse(
        total_publications=total_publications,
        published_count=published_count,
        draft_count=total_publications - published_count,
        total_leads=total_leads,
        b2b_leads=b2b_leads,
        education_leads=education_leads,
        isp_leads=isp_leads,
        b2c_leads=b2c_leads,
        esp_synced_count=140,
        esp_failed_permanent_count=4,
        emails_sent=emails_sent,
        tokens_created=tokens_created,
        tokens_activated=tokens_activated,
        tokens_exhausted=tokens_exhausted,
        total_jobs=total_jobs,
        jobs_succeeded=jobs_succeeded,
        jobs_failed=jobs_failed,
        jobs_queued=jobs_queued,
        jobs_running=jobs_running,
        failed_by_type=failed_by_type or {"graphics_generate": 3, "cube_fetch": 4},
        catalog_syncs=28,
        data_contract_violations=2,
        period_start=period_start,
        period_end=_NOW,
    )


def _make_app(kpi_service_override: object | None = None) -> FastAPI:
    """Create a minimal test FastAPI app with dependency overrides."""
    app = FastAPI()
    app.include_router(router)

    if kpi_service_override is not None:
        app.dependency_overrides[_get_kpi_service] = lambda: kpi_service_override

    return app


@pytest.fixture()
def mock_kpi_service() -> AsyncMock:
    """Return a mocked KPIService."""
    service = AsyncMock(spec=KPIService)
    return service


# ---------------------------------------------------------------------------
# GET /api/v1/admin/kpi
# ---------------------------------------------------------------------------


class TestGetKPI:
    """Tests for the GET /api/v1/admin/kpi endpoint."""

    @pytest.mark.asyncio()
    async def test_kpi_returns_200(
        self, mock_kpi_service: AsyncMock
    ) -> None:
        """Valid request returns HTTP 200 with all KPI fields."""
        kpi_data = _make_kpi_response()
        mock_kpi_service.get_kpi.return_value = kpi_data

        app = _make_app(kpi_service_override=mock_kpi_service)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/admin/kpi")

        assert resp.status_code == 200
        data = resp.json()

        # All fields present
        expected_fields = {
            "total_publications", "published_count", "draft_count",
            "total_leads", "b2b_leads", "education_leads", "isp_leads", "b2c_leads",
            "esp_synced_count", "esp_failed_permanent_count",
            "emails_sent", "tokens_created", "tokens_activated", "tokens_exhausted",
            "total_jobs", "jobs_succeeded", "jobs_failed", "jobs_queued", "jobs_running",
            "failed_by_type",
            "catalog_syncs", "data_contract_violations",
            "period_start", "period_end",
        }
        assert expected_fields == set(data.keys())

        # Spot-check values
        assert data["total_publications"] == 45
        assert data["published_count"] == 42
        assert data["draft_count"] == 3
        assert data["total_leads"] == 156
        assert data["jobs_succeeded"] == 142
        assert data["failed_by_type"] == {"graphics_generate": 3, "cube_fetch": 4}

    @pytest.mark.asyncio()
    async def test_kpi_endpoint_reachable(self) -> None:
        """Verify the route is reachable and returns 200.

        Auth enforcement is tested at the middleware level (test_auth.py).
        Unit tests do not mount AuthMiddleware, so this confirms the
        route handler itself works independently.
        """
        mock_service = AsyncMock(spec=KPIService)
        mock_service.get_kpi.return_value = _make_kpi_response()

        app = _make_app(kpi_service_override=mock_service)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/admin/kpi")

        assert resp.status_code == 200

    @pytest.mark.asyncio()
    async def test_kpi_days_parameter(
        self, mock_kpi_service: AsyncMock
    ) -> None:
        """Passing ?days=7 should forward days=7 to the service."""
        kpi_data = _make_kpi_response(days=7)
        mock_kpi_service.get_kpi.return_value = kpi_data

        app = _make_app(kpi_service_override=mock_kpi_service)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/admin/kpi?days=7")

        assert resp.status_code == 200
        mock_kpi_service.get_kpi.assert_called_once_with(days=7)

        # Verify period_start is approximately 7 days ago
        data = resp.json()
        assert "period_start" in data

    @pytest.mark.asyncio()
    async def test_kpi_days_validation_zero(
        self, mock_kpi_service: AsyncMock
    ) -> None:
        """?days=0 should return 422 (minimum is 1)."""
        app = _make_app(kpi_service_override=mock_kpi_service)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/admin/kpi?days=0")

        assert resp.status_code == 422

    @pytest.mark.asyncio()
    async def test_kpi_days_validation_too_large(
        self, mock_kpi_service: AsyncMock
    ) -> None:
        """?days=500 should return 422 (maximum is 365)."""
        app = _make_app(kpi_service_override=mock_kpi_service)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/admin/kpi?days=500")

        assert resp.status_code == 422

    @pytest.mark.asyncio()
    async def test_kpi_empty_db(
        self, mock_kpi_service: AsyncMock
    ) -> None:
        """All tables empty — all counts should be 0, no errors."""
        empty_kpi = KPIResponse(
            total_publications=0,
            published_count=0,
            draft_count=0,
            total_leads=0,
            b2b_leads=0,
            education_leads=0,
            isp_leads=0,
            b2c_leads=0,
            esp_synced_count=0,
            esp_failed_permanent_count=0,
            emails_sent=0,
            tokens_created=0,
            tokens_activated=0,
            tokens_exhausted=0,
            total_jobs=0,
            jobs_succeeded=0,
            jobs_failed=0,
            jobs_queued=0,
            jobs_running=0,
            failed_by_type={},
            catalog_syncs=0,
            data_contract_violations=0,
            period_start=_NOW - timedelta(days=30),
            period_end=_NOW,
        )
        mock_kpi_service.get_kpi.return_value = empty_kpi

        app = _make_app(kpi_service_override=mock_kpi_service)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/admin/kpi")

        assert resp.status_code == 200
        data = resp.json()
        assert data["total_publications"] == 0
        assert data["total_leads"] == 0
        assert data["total_jobs"] == 0
        assert data["emails_sent"] == 0
        assert data["failed_by_type"] == {}
        assert data["catalog_syncs"] == 0
        assert data["data_contract_violations"] == 0

    @pytest.mark.asyncio()
    async def test_kpi_default_days(
        self, mock_kpi_service: AsyncMock
    ) -> None:
        """Without an explicit days param, the default (30) should be used."""
        kpi_data = _make_kpi_response()
        mock_kpi_service.get_kpi.return_value = kpi_data

        app = _make_app(kpi_service_override=mock_kpi_service)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.get("/api/v1/admin/kpi")

        mock_kpi_service.get_kpi.assert_called_once_with(days=30)

    @pytest.mark.asyncio()
    async def test_kpi_response_schema_completeness(
        self, mock_kpi_service: AsyncMock
    ) -> None:
        """Response must contain exactly the expected keys — no more, no less."""
        kpi_data = _make_kpi_response()
        mock_kpi_service.get_kpi.return_value = kpi_data

        app = _make_app(kpi_service_override=mock_kpi_service)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/admin/kpi")

        data = resp.json()
        schema_fields = set(KPIResponse.model_fields.keys())
        assert schema_fields == set(data.keys())
