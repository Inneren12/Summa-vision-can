"""Tests for POST /api/v1/admin/leads/resync (D-3).

Validates ESP resync with exponential backoff, permanent failure marking,
and transient failure handling.

Functional tests use a minimal FastAPI app (no AuthMiddleware) so that
resync logic can be tested in isolation. The auth test uses the real app.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from src.api.routers.admin_leads import _get_esp_client, router
from src.core.exceptions import ESPPermanentError, ESPTransientError
from src.main import app as real_app
from src.models.lead import Lead


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_unsynced_lead(lead_id: int, email: str = "user@example.com") -> Lead:
    lead = Lead(
        email=email,
        ip_address="127.0.0.1",
        asset_id="1",
        is_b2b=True,
        company_domain="example.com",
        esp_synced=False,
        esp_sync_failed_permanent=False,
    )
    lead.id = lead_id
    return lead


def _make_app(esp_override: object | None = None) -> FastAPI:
    """Create a minimal test app with just the admin_leads router."""
    from src.core.database import get_db

    test_app = FastAPI()
    test_app.include_router(router)

    mock_db = MagicMock()
    mock_db.commit = AsyncMock()

    async def override_db():
        yield mock_db

    test_app.dependency_overrides[get_db] = override_db

    if esp_override is not None:
        test_app.dependency_overrides[_get_esp_client] = lambda: esp_override

    return test_app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def mock_esp() -> AsyncMock:
    esp = AsyncMock()
    esp.add_subscriber = AsyncMock()
    return esp


@pytest.fixture()
def mock_lead_repo() -> AsyncMock:
    repo = AsyncMock()
    repo.get_unsynced = AsyncMock(return_value=[])
    repo.mark_synced = AsyncMock()
    repo.mark_permanently_failed = AsyncMock()
    return repo


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestResync:
    @pytest.mark.asyncio
    async def test_resync_syncs_pending_leads(
        self, mock_lead_repo: AsyncMock, mock_esp: AsyncMock
    ) -> None:
        leads = [_make_unsynced_lead(i, f"user{i}@example.com") for i in range(1, 4)]
        mock_lead_repo.get_unsynced = AsyncMock(return_value=leads)

        test_app = _make_app(esp_override=mock_esp)

        with patch(
            "src.api.routers.admin_leads.LeadRepository",
            return_value=mock_lead_repo,
        ):
            transport = ASGITransport(app=test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post("/api/v1/admin/leads/resync")

        body = resp.json()
        assert body["total"] == 3
        assert body["synced"] == 3
        assert mock_lead_repo.mark_synced.await_count == 3

    @pytest.mark.asyncio
    async def test_resync_exponential_backoff(
        self, mock_lead_repo: AsyncMock
    ) -> None:
        leads = [_make_unsynced_lead(1, "user@example.com")]
        mock_lead_repo.get_unsynced = AsyncMock(return_value=leads)

        # Fail twice, succeed on third attempt
        esp = AsyncMock()
        esp.add_subscriber = AsyncMock(
            side_effect=[
                ESPTransientError(500, "fail"),
                ESPTransientError(500, "fail"),
                None,  # success
            ]
        )

        test_app = _make_app(esp_override=esp)

        with patch(
            "src.api.routers.admin_leads.LeadRepository",
            return_value=mock_lead_repo,
        ), patch("src.api.routers.admin_leads.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            transport = ASGITransport(app=test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post("/api/v1/admin/leads/resync")

        body = resp.json()
        assert body["synced"] == 1
        # sleep(1) then sleep(2)
        assert mock_sleep.await_count == 2
        sleep_args = [call.args[0] for call in mock_sleep.call_args_list]
        assert sleep_args == [1, 2]

    @pytest.mark.asyncio
    async def test_resync_permanent_failure_marks_lead(
        self, mock_lead_repo: AsyncMock
    ) -> None:
        leads = [_make_unsynced_lead(1)]
        mock_lead_repo.get_unsynced = AsyncMock(return_value=leads)

        esp = AsyncMock()
        esp.add_subscriber = AsyncMock(
            side_effect=ESPPermanentError(400, "Bad Request")
        )

        test_app = _make_app(esp_override=esp)

        with patch(
            "src.api.routers.admin_leads.LeadRepository",
            return_value=mock_lead_repo,
        ):
            transport = ASGITransport(app=test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post("/api/v1/admin/leads/resync")

        body = resp.json()
        assert body["failed_permanent"] == 1
        mock_lead_repo.mark_permanently_failed.assert_awaited_once_with(1)

    @pytest.mark.asyncio
    async def test_resync_transient_failure_3_attempts_skips(
        self, mock_lead_repo: AsyncMock
    ) -> None:
        leads = [_make_unsynced_lead(1)]
        mock_lead_repo.get_unsynced = AsyncMock(return_value=leads)

        esp = AsyncMock()
        esp.add_subscriber = AsyncMock(
            side_effect=ESPTransientError(500, "Server Error")
        )

        test_app = _make_app(esp_override=esp)

        with patch(
            "src.api.routers.admin_leads.LeadRepository",
            return_value=mock_lead_repo,
        ), patch("src.api.routers.admin_leads.asyncio.sleep", new_callable=AsyncMock):
            transport = ASGITransport(app=test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post("/api/v1/admin/leads/resync")

        body = resp.json()
        assert body["failed_transient"] == 1
        assert body["synced"] == 0
        # NOT marked as permanently failed
        mock_lead_repo.mark_permanently_failed.assert_not_awaited()
        # ESP was called 3 times
        assert esp.add_subscriber.await_count == 3

    def test_resync_requires_auth(self) -> None:
        """POST without X-API-KEY on the real app returns 401."""
        from src.core.database import get_db

        mock_db = MagicMock()

        async def override_db():
            yield mock_db

        real_app.dependency_overrides[get_db] = override_db
        real_app.dependency_overrides[_get_esp_client] = lambda: AsyncMock()

        client = TestClient(real_app)
        resp = client.post("/api/v1/admin/leads/resync")
        assert resp.status_code == 401
        real_app.dependency_overrides.clear()
