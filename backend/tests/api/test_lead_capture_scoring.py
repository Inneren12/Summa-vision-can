"""Tests for lead capture + D-3 scoring/Slack/ESP integration.

Extends D-2 lead capture tests to verify that the background task
scores leads, triggers Slack notifications, and syncs to ESP.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.core.exceptions import ESPPermanentError, ESPTransientError
from src.main import app
from src.models.download_token import DownloadToken
from src.models.lead import Lead
from src.models.publication import Publication, PublicationStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_published_pub(asset_id: int = 1) -> Publication:
    pub = Publication(
        headline="Test Graphic",
        chart_type="BAR",
        virality_score=8.0,
        status=PublicationStatus.PUBLISHED,
        s3_key_lowres=f"graphics/{asset_id}/lowres.png",
        s3_key_highres=f"graphics/{asset_id}/highres.png",
    )
    pub.id = asset_id
    return pub


def _make_lead(
    lead_id: int = 1,
    email: str = "user@company.ca",
    asset_id: str = "1",
    is_b2b: bool = True,
    company_domain: str | None = "company.ca",
) -> Lead:
    lead = Lead(
        email=email,
        ip_address="127.0.0.1",
        asset_id=asset_id,
        is_b2b=is_b2b,
        company_domain=company_domain,
        esp_synced=False,
        esp_sync_failed_permanent=False,
    )
    lead.id = lead_id
    return lead


def _make_token(token_id: int = 1, lead_id: int = 1) -> DownloadToken:
    token = DownloadToken(
        token_hash="fakehash",
        lead_id=lead_id,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=48),
        max_uses=5,
        use_count=0,
        revoked=False,
    )
    token.id = token_id
    return token


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset_rate_limiters() -> None:
    from src.api.routers.public_leads import _lead_rate_limiter, _resend_rate_limiter
    _lead_rate_limiter.reset()
    _resend_rate_limiter.reset()


@pytest.fixture()
def mock_slack() -> AsyncMock:
    slack = AsyncMock()
    slack.notify_lead = AsyncMock(return_value=True)
    return slack


@pytest.fixture()
def mock_esp() -> AsyncMock:
    esp = AsyncMock()
    esp.add_subscriber = AsyncMock()
    esp.add_tag = AsyncMock()
    return esp


@pytest.fixture()
def mock_lead_repo() -> AsyncMock:
    lead = _make_lead(email="ceo@tdbank.ca", company_domain="tdbank.ca")
    repo = AsyncMock()
    repo.get_or_create = AsyncMock(return_value=(lead, True))
    repo.get_by_id = AsyncMock(return_value=lead)
    return repo


def _build_client(
    mock_lead_repo: AsyncMock,
    mock_slack: AsyncMock,
    mock_esp: AsyncMock | None,
) -> TestClient:
    """Build a TestClient with all dependencies mocked."""
    from src.core.database import get_db
    from src.api.routers.public_leads import (
        _get_turnstile_validator,
        _get_email_service,
        _get_slack_notifier,
        _get_esp_client,
    )

    mock_turnstile = AsyncMock()
    mock_turnstile.validate = AsyncMock(return_value=True)
    mock_email_service = AsyncMock()
    mock_pub_repo = AsyncMock()
    mock_pub_repo.get_by_id = AsyncMock(return_value=_make_published_pub())
    mock_token_repo = AsyncMock()
    mock_token_repo.create = AsyncMock(return_value=_make_token())
    mock_audit = AsyncMock()
    mock_audit.log_event = AsyncMock()

    mock_db = MagicMock()
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()

    async def override_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[_get_turnstile_validator] = lambda: mock_turnstile
    app.dependency_overrides[_get_email_service] = lambda: mock_email_service
    app.dependency_overrides[_get_slack_notifier] = lambda: mock_slack
    app.dependency_overrides[_get_esp_client] = lambda: mock_esp

    return TestClient(app)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestBackgroundTaskScoring:
    def test_background_task_scores_and_updates_lead(
        self,
        mock_lead_repo: AsyncMock,
        mock_slack: AsyncMock,
        mock_esp: AsyncMock,
    ) -> None:
        with patch(
            "src.api.routers.public_leads.PublicationRepository",
            return_value=AsyncMock(get_by_id=AsyncMock(return_value=_make_published_pub())),
        ), patch(
            "src.api.routers.public_leads.LeadRepository",
            return_value=mock_lead_repo,
        ), patch(
            "src.api.routers.public_leads.DownloadTokenRepository",
            return_value=AsyncMock(create=AsyncMock(return_value=_make_token())),
        ), patch(
            "src.api.routers.public_leads.AuditWriter",
            return_value=AsyncMock(log_event=AsyncMock()),
        ):
            client = _build_client(mock_lead_repo, mock_slack, mock_esp)
            resp = client.post(
                "/api/v1/public/leads/capture",
                json={"email": "ceo@tdbank.ca", "asset_id": 1, "turnstile_token": "valid"},
            )
            assert resp.status_code == 200

        # The background task should have called get_by_id to update the lead
        mock_lead_repo.get_by_id.assert_awaited()
        app.dependency_overrides.clear()

    def test_b2b_lead_triggers_slack(
        self,
        mock_lead_repo: AsyncMock,
        mock_slack: AsyncMock,
        mock_esp: AsyncMock,
    ) -> None:
        with patch(
            "src.api.routers.public_leads.PublicationRepository",
            return_value=AsyncMock(get_by_id=AsyncMock(return_value=_make_published_pub())),
        ), patch(
            "src.api.routers.public_leads.LeadRepository",
            return_value=mock_lead_repo,
        ), patch(
            "src.api.routers.public_leads.DownloadTokenRepository",
            return_value=AsyncMock(create=AsyncMock(return_value=_make_token())),
        ), patch(
            "src.api.routers.public_leads.AuditWriter",
            return_value=AsyncMock(log_event=AsyncMock()),
        ):
            client = _build_client(mock_lead_repo, mock_slack, mock_esp)
            resp = client.post(
                "/api/v1/public/leads/capture",
                json={"email": "ceo@tdbank.ca", "asset_id": 1, "turnstile_token": "valid"},
            )
            assert resp.status_code == 200

        mock_slack.notify_lead.assert_awaited_once()
        call_kwargs = mock_slack.notify_lead.call_args.kwargs
        assert call_kwargs["category"] == "b2b"
        app.dependency_overrides.clear()

    def test_isp_lead_no_slack(
        self,
        mock_slack: AsyncMock,
        mock_esp: AsyncMock,
    ) -> None:
        isp_lead = _make_lead(email="user@rogers.com", company_domain=None, is_b2b=False)
        lead_repo = AsyncMock()
        lead_repo.get_or_create = AsyncMock(return_value=(isp_lead, True))
        lead_repo.get_by_id = AsyncMock(return_value=isp_lead)

        with patch(
            "src.api.routers.public_leads.PublicationRepository",
            return_value=AsyncMock(get_by_id=AsyncMock(return_value=_make_published_pub())),
        ), patch(
            "src.api.routers.public_leads.LeadRepository",
            return_value=lead_repo,
        ), patch(
            "src.api.routers.public_leads.DownloadTokenRepository",
            return_value=AsyncMock(create=AsyncMock(return_value=_make_token())),
        ), patch(
            "src.api.routers.public_leads.AuditWriter",
            return_value=AsyncMock(log_event=AsyncMock()),
        ):
            client = _build_client(lead_repo, mock_slack, mock_esp)
            resp = client.post(
                "/api/v1/public/leads/capture",
                json={"email": "user@rogers.com", "asset_id": 1, "turnstile_token": "valid"},
            )
            assert resp.status_code == 200

        mock_slack.notify_lead.assert_not_awaited()
        app.dependency_overrides.clear()

    def test_esp_5xx_sets_unsynced(
        self,
        mock_lead_repo: AsyncMock,
        mock_slack: AsyncMock,
    ) -> None:
        failing_esp = AsyncMock()
        failing_esp.add_subscriber = AsyncMock(
            side_effect=ESPTransientError(status_code=500, detail="Server Error"),
        )

        lead = _make_lead(email="ceo@tdbank.ca")
        mock_lead_repo.get_by_id = AsyncMock(return_value=lead)

        with patch(
            "src.api.routers.public_leads.PublicationRepository",
            return_value=AsyncMock(get_by_id=AsyncMock(return_value=_make_published_pub())),
        ), patch(
            "src.api.routers.public_leads.LeadRepository",
            return_value=mock_lead_repo,
        ), patch(
            "src.api.routers.public_leads.DownloadTokenRepository",
            return_value=AsyncMock(create=AsyncMock(return_value=_make_token())),
        ), patch(
            "src.api.routers.public_leads.AuditWriter",
            return_value=AsyncMock(log_event=AsyncMock()),
        ):
            client = _build_client(mock_lead_repo, mock_slack, failing_esp)
            resp = client.post(
                "/api/v1/public/leads/capture",
                json={"email": "ceo@tdbank.ca", "asset_id": 1, "turnstile_token": "valid"},
            )
            assert resp.status_code == 200

        assert lead.esp_synced is False
        assert lead.esp_sync_failed_permanent is False
        app.dependency_overrides.clear()

    def test_esp_4xx_sets_permanent_failure(
        self,
        mock_lead_repo: AsyncMock,
        mock_slack: AsyncMock,
    ) -> None:
        failing_esp = AsyncMock()
        failing_esp.add_subscriber = AsyncMock(
            side_effect=ESPPermanentError(status_code=400, detail="Bad Request"),
        )

        lead = _make_lead(email="ceo@tdbank.ca")
        mock_lead_repo.get_by_id = AsyncMock(return_value=lead)

        with patch(
            "src.api.routers.public_leads.PublicationRepository",
            return_value=AsyncMock(get_by_id=AsyncMock(return_value=_make_published_pub())),
        ), patch(
            "src.api.routers.public_leads.LeadRepository",
            return_value=mock_lead_repo,
        ), patch(
            "src.api.routers.public_leads.DownloadTokenRepository",
            return_value=AsyncMock(create=AsyncMock(return_value=_make_token())),
        ), patch(
            "src.api.routers.public_leads.AuditWriter",
            return_value=AsyncMock(log_event=AsyncMock()),
        ):
            client = _build_client(mock_lead_repo, mock_slack, failing_esp)
            resp = client.post(
                "/api/v1/public/leads/capture",
                json={"email": "ceo@tdbank.ca", "asset_id": 1, "turnstile_token": "valid"},
            )
            assert resp.status_code == 200

        assert lead.esp_sync_failed_permanent is True
        app.dependency_overrides.clear()

    def test_esp_success_sets_synced(
        self,
        mock_lead_repo: AsyncMock,
        mock_slack: AsyncMock,
        mock_esp: AsyncMock,
    ) -> None:
        lead = _make_lead(email="ceo@tdbank.ca")
        mock_lead_repo.get_by_id = AsyncMock(return_value=lead)

        with patch(
            "src.api.routers.public_leads.PublicationRepository",
            return_value=AsyncMock(get_by_id=AsyncMock(return_value=_make_published_pub())),
        ), patch(
            "src.api.routers.public_leads.LeadRepository",
            return_value=mock_lead_repo,
        ), patch(
            "src.api.routers.public_leads.DownloadTokenRepository",
            return_value=AsyncMock(create=AsyncMock(return_value=_make_token())),
        ), patch(
            "src.api.routers.public_leads.AuditWriter",
            return_value=AsyncMock(log_event=AsyncMock()),
        ):
            client = _build_client(mock_lead_repo, mock_slack, mock_esp)
            resp = client.post(
                "/api/v1/public/leads/capture",
                json={"email": "ceo@tdbank.ca", "asset_id": 1, "turnstile_token": "valid"},
            )
            assert resp.status_code == 200

        assert lead.esp_synced is True
        app.dependency_overrides.clear()
