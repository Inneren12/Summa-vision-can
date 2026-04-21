"""Tests for POST /api/v1/public/sponsorship/inquire (D-3, PR-37/38).

Validates B2C rejection, tiered Slack handling, and rate limiting
for sponsorship inquiries.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.core.security.ip_rate_limiter import InMemoryRateLimiter
from src.main import app
from src.models.lead import Lead


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_lead(
    lead_id: int = 1,
    email: str = "user@company.ca",
    is_b2b: bool = True,
) -> Lead:
    lead = Lead(
        email=email,
        ip_address="127.0.0.1",
        asset_id="sponsorship_inquiry",
        is_b2b=is_b2b,
        company_domain="company.ca" if is_b2b else None,
    )
    lead.id = lead_id
    return lead


def _valid_payload(email: str = "ceo@tdbank.ca") -> dict:
    return {
        "name": "John Doe",
        "email": email,
        "budget": "$500-$1000/month",
        "message": "We are interested in sponsoring your platform for data insights.",
        "turnstile_token": "valid-token",
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset_rate_limiter() -> None:
    from src.api.routers.public_sponsorship import _sponsorship_rate_limiter
    _sponsorship_rate_limiter.reset()


@pytest.fixture()
def mock_slack() -> AsyncMock:
    slack = AsyncMock()
    slack.notify_lead = AsyncMock(return_value=True)
    return slack


@pytest.fixture()
def mock_turnstile() -> AsyncMock:
    turnstile = AsyncMock()
    turnstile.validate = AsyncMock(return_value=True)
    return turnstile


@pytest.fixture()
def mock_lead_repo() -> AsyncMock:
    repo = AsyncMock()
    repo.get_or_create = AsyncMock(return_value=(_make_lead(), True))
    return repo


@pytest.fixture()
def mock_audit() -> AsyncMock:
    audit = AsyncMock()
    audit.log_event = AsyncMock()
    return audit


def _build_client(
    mock_slack: AsyncMock,
    mock_lead_repo: AsyncMock,
    mock_audit: AsyncMock,
    mock_turnstile: AsyncMock | None = None,
) -> TestClient:
    from src.core.database import get_db
    from src.api.routers.public_sponsorship import (
        _get_slack_notifier,
        _get_turnstile_validator,
    )

    mock_db = MagicMock()

    async def override_db():
        yield mock_db

    if mock_turnstile is None:
        mock_turnstile = AsyncMock()
        mock_turnstile.validate = AsyncMock(return_value=True)

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[_get_slack_notifier] = lambda: mock_slack
    app.dependency_overrides[_get_turnstile_validator] = lambda: mock_turnstile

    return TestClient(app)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestSponsorshipEndpoint:
    def test_b2c_email_rejected_422(
        self,
        mock_slack: AsyncMock,
        mock_lead_repo: AsyncMock,
        mock_audit: AsyncMock,
    ) -> None:
        with patch(
            "src.api.routers.public_sponsorship.LeadRepository",
            return_value=mock_lead_repo,
        ), patch(
            "src.api.routers.public_sponsorship.AuditWriter",
            return_value=mock_audit,
        ):
            client = _build_client(mock_slack, mock_lead_repo, mock_audit)
            resp = client.post(
                "/api/v1/public/sponsorship/inquire",
                json=_valid_payload("user@gmail.com"),
            )
        assert resp.status_code == 422
        assert "corporate email" in resp.json()["detail"].lower()
        app.dependency_overrides.clear()

    def test_b2b_email_accepted_slack_called(
        self,
        mock_slack: AsyncMock,
        mock_lead_repo: AsyncMock,
        mock_audit: AsyncMock,
    ) -> None:
        with patch(
            "src.api.routers.public_sponsorship.LeadRepository",
            return_value=mock_lead_repo,
        ), patch(
            "src.api.routers.public_sponsorship.AuditWriter",
            return_value=mock_audit,
        ):
            client = _build_client(mock_slack, mock_lead_repo, mock_audit)
            resp = client.post(
                "/api/v1/public/sponsorship/inquire",
                json=_valid_payload("ceo@tdbank.ca"),
            )
        assert resp.status_code == 200
        mock_slack.notify_lead.assert_awaited_once()
        call_kwargs = mock_slack.notify_lead.call_args.kwargs
        assert call_kwargs["category"] == "b2b"
        assert call_kwargs["dedupe_key"] == "inquiry:ceo@tdbank.ca"
        app.dependency_overrides.clear()

    def test_education_accepted_with_tag(
        self,
        mock_slack: AsyncMock,
        mock_lead_repo: AsyncMock,
        mock_audit: AsyncMock,
    ) -> None:
        edu_lead = _make_lead(email="prof@utoronto.ca", is_b2b=False)
        mock_lead_repo.get_or_create = AsyncMock(return_value=(edu_lead, True))

        with patch(
            "src.api.routers.public_sponsorship.LeadRepository",
            return_value=mock_lead_repo,
        ), patch(
            "src.api.routers.public_sponsorship.AuditWriter",
            return_value=mock_audit,
        ):
            client = _build_client(mock_slack, mock_lead_repo, mock_audit)
            resp = client.post(
                "/api/v1/public/sponsorship/inquire",
                json=_valid_payload("prof@utoronto.ca"),
            )
        assert resp.status_code == 200
        mock_slack.notify_lead.assert_awaited_once()
        call_kwargs = mock_slack.notify_lead.call_args.kwargs
        assert call_kwargs["category"] == "education"
        app.dependency_overrides.clear()

    def test_isp_accepted_no_slack(
        self,
        mock_slack: AsyncMock,
        mock_lead_repo: AsyncMock,
        mock_audit: AsyncMock,
    ) -> None:
        isp_lead = _make_lead(email="user@rogers.com", is_b2b=False)
        mock_lead_repo.get_or_create = AsyncMock(return_value=(isp_lead, True))

        with patch(
            "src.api.routers.public_sponsorship.LeadRepository",
            return_value=mock_lead_repo,
        ), patch(
            "src.api.routers.public_sponsorship.AuditWriter",
            return_value=mock_audit,
        ):
            client = _build_client(mock_slack, mock_lead_repo, mock_audit)
            resp = client.post(
                "/api/v1/public/sponsorship/inquire",
                json=_valid_payload("user@rogers.com"),
            )
        assert resp.status_code == 200
        mock_slack.notify_lead.assert_not_awaited()
        app.dependency_overrides.clear()

    def test_rate_limit_1_per_5min(
        self,
        mock_slack: AsyncMock,
        mock_lead_repo: AsyncMock,
        mock_audit: AsyncMock,
    ) -> None:
        with patch(
            "src.api.routers.public_sponsorship.LeadRepository",
            return_value=mock_lead_repo,
        ), patch(
            "src.api.routers.public_sponsorship.AuditWriter",
            return_value=mock_audit,
        ):
            client = _build_client(mock_slack, mock_lead_repo, mock_audit)

            # First request passes
            resp = client.post(
                "/api/v1/public/sponsorship/inquire",
                json=_valid_payload("ceo@tdbank.ca"),
            )
            assert resp.status_code == 200

            # Second request within 5 min is rate-limited
            resp = client.post(
                "/api/v1/public/sponsorship/inquire",
                json=_valid_payload("ceo@tdbank.ca"),
            )
            assert resp.status_code == 429

        app.dependency_overrides.clear()

    def test_missing_turnstile_token_returns_422(
        self,
        mock_slack: AsyncMock,
        mock_lead_repo: AsyncMock,
        mock_audit: AsyncMock,
    ) -> None:
        """Pydantic schema rejects payloads without the turnstile_token field."""
        with patch(
            "src.api.routers.public_sponsorship.LeadRepository",
            return_value=mock_lead_repo,
        ), patch(
            "src.api.routers.public_sponsorship.AuditWriter",
            return_value=mock_audit,
        ):
            client = _build_client(mock_slack, mock_lead_repo, mock_audit)
            payload = _valid_payload("ceo@tdbank.ca")
            payload.pop("turnstile_token")
            resp = client.post(
                "/api/v1/public/sponsorship/inquire",
                json=payload,
            )
        assert resp.status_code == 422
        app.dependency_overrides.clear()

    def test_invalid_turnstile_token_returns_403(
        self,
        mock_slack: AsyncMock,
        mock_lead_repo: AsyncMock,
        mock_audit: AsyncMock,
    ) -> None:
        """Turnstile rejection yields a generic 403 with no CF error leakage."""
        bad_turnstile = AsyncMock()
        bad_turnstile.validate = AsyncMock(return_value=False)

        with patch(
            "src.api.routers.public_sponsorship.LeadRepository",
            return_value=mock_lead_repo,
        ), patch(
            "src.api.routers.public_sponsorship.AuditWriter",
            return_value=mock_audit,
        ):
            client = _build_client(
                mock_slack,
                mock_lead_repo,
                mock_audit,
                mock_turnstile=bad_turnstile,
            )
            resp = client.post(
                "/api/v1/public/sponsorship/inquire",
                json=_valid_payload("ceo@tdbank.ca"),
            )

        assert resp.status_code == 403
        body = resp.json()
        assert body["detail"] == "CAPTCHA verification failed"
        # No Slack notification when CAPTCHA fails.
        mock_slack.notify_lead.assert_not_awaited()
        # Lead never persisted when CAPTCHA fails.
        mock_lead_repo.get_or_create.assert_not_called()
        app.dependency_overrides.clear()

    def test_turnstile_validated_before_rate_limit_and_scoring(
        self,
        mock_slack: AsyncMock,
        mock_lead_repo: AsyncMock,
        mock_audit: AsyncMock,
    ) -> None:
        """Valid Turnstile token still flows through the rest of the pipeline."""
        turnstile = AsyncMock()
        turnstile.validate = AsyncMock(return_value=True)

        with patch(
            "src.api.routers.public_sponsorship.LeadRepository",
            return_value=mock_lead_repo,
        ), patch(
            "src.api.routers.public_sponsorship.AuditWriter",
            return_value=mock_audit,
        ):
            client = _build_client(
                mock_slack,
                mock_lead_repo,
                mock_audit,
                mock_turnstile=turnstile,
            )
            resp = client.post(
                "/api/v1/public/sponsorship/inquire",
                json=_valid_payload("ceo@tdbank.ca"),
            )

        assert resp.status_code == 200
        turnstile.validate.assert_awaited_once()
        app.dependency_overrides.clear()

    def test_captcha_failure_does_not_consume_rate_limit(
        self,
        mock_slack: AsyncMock,
        mock_lead_repo: AsyncMock,
        mock_audit: AsyncMock,
    ) -> None:
        """Regression test (ChatGPT Codex P1 fix):

        A CAPTCHA rejection must not burn the rate-limit slot. After a
        403 on a bad token, the same client_ip must still be able to
        submit successfully with a valid token immediately — no 429.
        """
        bad_turnstile = AsyncMock()
        bad_turnstile.validate = AsyncMock(return_value=False)

        good_turnstile = AsyncMock()
        good_turnstile.validate = AsyncMock(return_value=True)

        with patch(
            "src.api.routers.public_sponsorship.LeadRepository",
            return_value=mock_lead_repo,
        ), patch(
            "src.api.routers.public_sponsorship.AuditWriter",
            return_value=mock_audit,
        ):
            # First attempt: bad CAPTCHA → 403, rate slot NOT consumed.
            client = _build_client(
                mock_slack,
                mock_lead_repo,
                mock_audit,
                mock_turnstile=bad_turnstile,
            )
            resp1 = client.post(
                "/api/v1/public/sponsorship/inquire",
                json=_valid_payload("ceo@tdbank.ca"),
            )
            assert resp1.status_code == 403

            # Swap in a good turnstile validator for the retry.
            from src.api.routers.public_sponsorship import (
                _get_turnstile_validator,
            )
            app.dependency_overrides[_get_turnstile_validator] = (
                lambda: good_turnstile
            )

            # Second attempt: good CAPTCHA → 200 (not 429). If this
            # returns 429, the first attempt wrongly consumed the slot.
            resp2 = client.post(
                "/api/v1/public/sponsorship/inquire",
                json=_valid_payload("ceo@tdbank.ca"),
            )
            assert resp2.status_code == 200, (
                f"CAPTCHA failure consumed rate-limit slot — "
                f"retry got {resp2.status_code}, expected 200. "
                f"Response: {resp2.json()}"
            )

        app.dependency_overrides.clear()
