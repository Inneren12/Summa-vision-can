"""Tests for POST /api/v1/public/leads/capture (D-2, C1).

Tests the full lead capture flow including Turnstile validation,
rate limiting, lead deduplication / resend logic, token creation,
and audit events.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from contextlib import asynccontextmanager

from src.core.security.ip_rate_limiter import InMemoryRateLimiter
from src.main import app
from src.models.download_token import DownloadToken
from src.models.lead import Lead
from src.models.publication import Publication, PublicationStatus
from tests.conftest import make_publication


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_session_factory():
    """Return a callable that produces async context managers yielding a mock session.

    Used to override ``get_session_factory`` so that background tasks
    don't attempt real database connections in unit tests.
    """
    mock_session = MagicMock()
    mock_session.get = AsyncMock(return_value=_make_lead())
    mock_session.flush = AsyncMock()
    mock_session.commit = AsyncMock()

    @asynccontextmanager
    async def _ctx():
        yield mock_session

    factory = MagicMock(side_effect=lambda: _ctx())
    return factory


def _make_published_pub(asset_id: int = 1) -> Publication:
    pub = make_publication(
        headline="Test Graphic",
        chart_type="BAR",
        virality_score=8.0,
        status=PublicationStatus.PUBLISHED,
        s3_key_lowres=f"graphics/{asset_id}/lowres.png",
        s3_key_highres=f"graphics/{asset_id}/highres.png",
    )
    pub.id = asset_id
    return pub


def _make_lead(lead_id: int = 1, email: str = "user@company.ca", asset_id: str = "1") -> Lead:
    lead = Lead(
        email=email,
        ip_address="127.0.0.1",
        asset_id=asset_id,
        is_b2b=True,
        company_domain="company.ca",
    )
    lead.id = lead_id
    return lead


def _make_token(
    token_id: int = 1,
    lead_id: int = 1,
    use_count: int = 0,
    max_uses: int = 5,
    revoked: bool = False,
) -> DownloadToken:
    token = DownloadToken(
        token_hash="fakehash",
        lead_id=lead_id,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=48),
        max_uses=max_uses,
        use_count=use_count,
        revoked=revoked,
    )
    token.id = token_id
    return token


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset_rate_limiters() -> None:
    """Reset all module-level rate limiters before each test."""
    from src.api.routers.public_leads import _lead_rate_limiter, _resend_rate_limiter
    _lead_rate_limiter.reset()
    _resend_rate_limiter.reset()


@pytest.fixture()
def mock_turnstile() -> AsyncMock:
    turnstile = AsyncMock()
    turnstile.validate = AsyncMock(return_value=True)
    return turnstile


@pytest.fixture()
def mock_email_service() -> AsyncMock:
    return AsyncMock()


@pytest.fixture()
def mock_pub_repo() -> AsyncMock:
    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=_make_published_pub())
    return repo


@pytest.fixture()
def mock_lead_repo() -> AsyncMock:
    repo = AsyncMock()
    repo.create = AsyncMock(return_value=_make_lead())
    repo.get_or_create = AsyncMock(return_value=(_make_lead(), True))
    repo.exists = AsyncMock(return_value=False)
    repo.get_by_email_and_asset = AsyncMock(return_value=None)
    return repo


@pytest.fixture()
def mock_token_repo() -> AsyncMock:
    repo = AsyncMock()
    repo.create = AsyncMock(return_value=_make_token())
    repo.get_by_lead_and_asset = AsyncMock(return_value=None)
    repo.revoke = AsyncMock()
    return repo


@pytest.fixture()
def mock_audit() -> AsyncMock:
    audit = AsyncMock()
    audit.log_event = AsyncMock()
    return audit


@pytest.fixture()
def client(
    mock_turnstile: AsyncMock,
    mock_email_service: AsyncMock,
    mock_pub_repo: AsyncMock,
    mock_lead_repo: AsyncMock,
    mock_token_repo: AsyncMock,
    mock_audit: AsyncMock,
) -> TestClient:
    from src.core.database import get_db, get_session_factory
    from src.api.routers.public_leads import (
        _get_turnstile_validator,
        _get_email_service,
        _get_slack_notifier,
        _get_esp_client,
    )

    async def override_db():
        mock_db = MagicMock()
        mock_db.flush = AsyncMock()
        mock_db.commit = AsyncMock()
        yield mock_db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_session_factory] = _mock_session_factory
    app.dependency_overrides[_get_turnstile_validator] = lambda: mock_turnstile
    app.dependency_overrides[_get_email_service] = lambda: mock_email_service
    app.dependency_overrides[_get_slack_notifier] = lambda: AsyncMock()
    app.dependency_overrides[_get_esp_client] = lambda: None

    with patch(
        "src.api.routers.public_leads.PublicationRepository",
        return_value=mock_pub_repo,
    ), patch(
        "src.api.routers.public_leads.LeadRepository",
        return_value=mock_lead_repo,
    ), patch(
        "src.api.routers.public_leads.DownloadTokenRepository",
        return_value=mock_token_repo,
    ), patch(
        "src.api.routers.public_leads.AuditWriter",
        return_value=mock_audit,
    ):
        yield TestClient(app)

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests: happy path
# ---------------------------------------------------------------------------

class TestLeadCaptureHappyPath:
    def test_returns_200_with_message(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/public/leads/capture",
            json={"email": "user@company.ca", "asset_id": 1, "turnstile_token": "valid-token"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "message" in body
        assert "email" in body["message"].lower() or "check" in body["message"].lower()

    def test_lead_saved_to_db(
        self,
        client: TestClient,
        mock_lead_repo: AsyncMock,
    ) -> None:
        client.post(
            "/api/v1/public/leads/capture",
            json={"email": "user@company.ca", "asset_id": 1, "turnstile_token": "valid-token"},
        )
        mock_lead_repo.get_or_create.assert_awaited_once()
        call_kwargs = mock_lead_repo.get_or_create.call_args.kwargs
        assert call_kwargs["email"] == "user@company.ca"
        assert call_kwargs["asset_id"] == "1"

    def test_token_created_with_correct_ttl_and_max_uses(
        self,
        client: TestClient,
        mock_token_repo: AsyncMock,
    ) -> None:
        client.post(
            "/api/v1/public/leads/capture",
            json={"email": "user@company.ca", "asset_id": 1, "turnstile_token": "valid-token"},
        )
        mock_token_repo.create.assert_awaited_once()
        call_kwargs = mock_token_repo.create.call_args.kwargs
        assert call_kwargs["max_uses"] == 5
        # Token should expire roughly 48 hours from now
        expected_min = datetime.now(timezone.utc) + timedelta(hours=47)
        assert call_kwargs["expires_at"] > expected_min

    def test_email_sent_with_magic_link(
        self,
        client: TestClient,
        mock_email_service: AsyncMock,
    ) -> None:
        resp = client.post(
            "/api/v1/public/leads/capture",
            json={"email": "user@company.ca", "asset_id": 1, "turnstile_token": "valid-token"},
        )
        assert resp.status_code == 200
        # BackgroundTasks: email_service.send_email is called via background task
        # In TestClient, background tasks run synchronously
        mock_email_service.send_email.assert_awaited_once()
        call_kwargs = mock_email_service.send_email.call_args.kwargs
        assert call_kwargs["to"] == "user@company.ca"
        assert "Summa Vision" in call_kwargs["subject"]
        assert "/downloading?token=" in call_kwargs["html_body"]

    def test_audit_events_written(
        self,
        client: TestClient,
        mock_audit: AsyncMock,
    ) -> None:
        client.post(
            "/api/v1/public/leads/capture",
            json={"email": "user@company.ca", "asset_id": 1, "turnstile_token": "valid-token"},
        )
        # Should write 4 audit events: lead.captured, lead.email_sent,
        # token.created (request), and lead.scored (background task).
        assert mock_audit.log_event.await_count == 4
        event_types = [call.kwargs["event_type"] for call in mock_audit.log_event.call_args_list]
        from src.schemas.events import EventType
        assert EventType.LEAD_CAPTURED in event_types
        assert EventType.LEAD_EMAIL_SENT in event_types
        assert EventType.TOKEN_CREATED in event_types
        assert EventType.LEAD_SCORED in event_types


# ---------------------------------------------------------------------------
# Tests: Turnstile failure
# ---------------------------------------------------------------------------

class TestTurnstileValidation:
    def test_403_if_turnstile_fails(
        self,
        mock_turnstile: AsyncMock,
        mock_email_service: AsyncMock,
        mock_pub_repo: AsyncMock,
        mock_lead_repo: AsyncMock,
        mock_token_repo: AsyncMock,
        mock_audit: AsyncMock,
    ) -> None:
        from src.core.database import get_db, get_session_factory
        from src.api.routers.public_leads import (
            _get_turnstile_validator, _get_email_service,
            _get_slack_notifier, _get_esp_client,
        )

        mock_turnstile.validate = AsyncMock(return_value=False)

        async def override_db():
            mock_db = MagicMock()
            mock_db.flush = AsyncMock()
            mock_db.commit = AsyncMock()
            yield mock_db

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_session_factory] = _mock_session_factory
        app.dependency_overrides[_get_turnstile_validator] = lambda: mock_turnstile
        app.dependency_overrides[_get_email_service] = lambda: mock_email_service
        app.dependency_overrides[_get_slack_notifier] = lambda: AsyncMock()
        app.dependency_overrides[_get_esp_client] = lambda: None

        with patch(
            "src.api.routers.public_leads.PublicationRepository",
            return_value=mock_pub_repo,
        ), patch(
            "src.api.routers.public_leads.LeadRepository",
            return_value=mock_lead_repo,
        ), patch(
            "src.api.routers.public_leads.DownloadTokenRepository",
            return_value=mock_token_repo,
        ), patch(
            "src.api.routers.public_leads.AuditWriter",
            return_value=mock_audit,
        ):
            c = TestClient(app)
            resp = c.post(
                "/api/v1/public/leads/capture",
                json={"email": "user@company.ca", "asset_id": 1, "turnstile_token": "bad-token"},
            )

        app.dependency_overrides.clear()
        assert resp.status_code == 403
        assert "CAPTCHA" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Tests: rate limiting
# ---------------------------------------------------------------------------

class TestRateLimit:
    def test_rate_limit_returns_429(self) -> None:
        from src.core.database import get_db, get_session_factory
        from src.api.routers.public_leads import (
            _get_turnstile_validator, _get_email_service,
            _get_slack_notifier, _get_esp_client,
        )

        mock_turnstile = AsyncMock()
        mock_turnstile.validate = AsyncMock(return_value=True)
        mock_email_service = AsyncMock()
        pub_repo = AsyncMock()
        pub_repo.get_by_id = AsyncMock(return_value=_make_published_pub())
        lead_repo = AsyncMock()
        lead_repo.create = AsyncMock(return_value=_make_lead())
        lead_repo.get_or_create = AsyncMock(return_value=(_make_lead(), True))
        lead_repo.get_by_email_and_asset = AsyncMock(return_value=None)
        token_repo = AsyncMock()
        token_repo.create = AsyncMock(return_value=_make_token())
        audit = AsyncMock()
        audit.log_event = AsyncMock()

        # Tight limiter: 3 req/min (default)
        tight_limiter = InMemoryRateLimiter(max_requests=3, window_seconds=60)

        async def override_db():
            mock_db = MagicMock()
            mock_db.flush = AsyncMock()
            mock_db.commit = AsyncMock()
            yield mock_db

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_session_factory] = _mock_session_factory
        app.dependency_overrides[_get_turnstile_validator] = lambda: mock_turnstile
        app.dependency_overrides[_get_email_service] = lambda: mock_email_service
        app.dependency_overrides[_get_slack_notifier] = lambda: AsyncMock()
        app.dependency_overrides[_get_esp_client] = lambda: None

        with patch(
            "src.api.routers.public_leads.PublicationRepository",
            return_value=pub_repo,
        ), patch(
            "src.api.routers.public_leads.LeadRepository",
            return_value=lead_repo,
        ), patch(
            "src.api.routers.public_leads.DownloadTokenRepository",
            return_value=token_repo,
        ), patch(
            "src.api.routers.public_leads.AuditWriter",
            return_value=audit,
        ), patch(
            "src.api.routers.public_leads._lead_rate_limiter",
            tight_limiter,
        ):
            c = TestClient(app)
            # First 3 requests pass
            for _ in range(3):
                resp = c.post(
                    "/api/v1/public/leads/capture",
                    json={"email": "user@company.ca", "asset_id": 1, "turnstile_token": "valid"},
                )
                assert resp.status_code == 200

            # 4th is rate-limited
            resp = c.post(
                "/api/v1/public/leads/capture",
                json={"email": "user@company.ca", "asset_id": 1, "turnstile_token": "valid"},
            )
            assert resp.status_code == 429

        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests: 404 — asset not found
# ---------------------------------------------------------------------------

class TestAssetValidation:
    def test_404_if_publication_not_found(
        self,
        mock_turnstile: AsyncMock,
        mock_email_service: AsyncMock,
        mock_lead_repo: AsyncMock,
        mock_token_repo: AsyncMock,
        mock_audit: AsyncMock,
    ) -> None:
        from src.core.database import get_db, get_session_factory
        from src.api.routers.public_leads import (
            _get_turnstile_validator, _get_email_service,
            _get_slack_notifier, _get_esp_client,
        )

        pub_repo = AsyncMock()
        pub_repo.get_by_id = AsyncMock(return_value=None)

        async def override_db():
            mock_db = MagicMock()
            mock_db.flush = AsyncMock()
            mock_db.commit = AsyncMock()
            yield mock_db

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_session_factory] = _mock_session_factory
        app.dependency_overrides[_get_turnstile_validator] = lambda: mock_turnstile
        app.dependency_overrides[_get_email_service] = lambda: mock_email_service
        app.dependency_overrides[_get_slack_notifier] = lambda: AsyncMock()
        app.dependency_overrides[_get_esp_client] = lambda: None

        with patch(
            "src.api.routers.public_leads.PublicationRepository",
            return_value=pub_repo,
        ), patch(
            "src.api.routers.public_leads.LeadRepository",
            return_value=mock_lead_repo,
        ), patch(
            "src.api.routers.public_leads.DownloadTokenRepository",
            return_value=mock_token_repo,
        ), patch(
            "src.api.routers.public_leads.AuditWriter",
            return_value=mock_audit,
        ):
            c = TestClient(app)
            resp = c.post(
                "/api/v1/public/leads/capture",
                json={"email": "user@company.ca", "asset_id": 999, "turnstile_token": "valid"},
            )

        app.dependency_overrides.clear()
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Tests: duplicate lead — resend flow
# ---------------------------------------------------------------------------

class TestResendFlow:
    def test_resend_revokes_old_token_and_creates_new_when_use_count_zero(
        self,
        mock_turnstile: AsyncMock,
        mock_email_service: AsyncMock,
        mock_pub_repo: AsyncMock,
        mock_audit: AsyncMock,
    ) -> None:
        from src.core.database import get_db, get_session_factory
        from src.api.routers.public_leads import (
            _get_turnstile_validator, _get_email_service,
            _get_slack_notifier, _get_esp_client,
        )

        existing_lead = _make_lead()
        existing_token = _make_token(use_count=0)

        lead_repo = AsyncMock()
        lead_repo.get_or_create = AsyncMock(return_value=(existing_lead, False))

        token_repo = AsyncMock()
        token_repo.get_by_lead_and_asset = AsyncMock(return_value=existing_token)
        token_repo.revoke = AsyncMock()
        token_repo.create = AsyncMock(return_value=_make_token(token_id=2))

        async def override_db():
            mock_db = MagicMock()
            mock_db.flush = AsyncMock()
            mock_db.commit = AsyncMock()
            yield mock_db

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_session_factory] = _mock_session_factory
        app.dependency_overrides[_get_turnstile_validator] = lambda: mock_turnstile
        app.dependency_overrides[_get_email_service] = lambda: mock_email_service
        app.dependency_overrides[_get_slack_notifier] = lambda: AsyncMock()
        app.dependency_overrides[_get_esp_client] = lambda: None

        with patch(
            "src.api.routers.public_leads.PublicationRepository",
            return_value=mock_pub_repo,
        ), patch(
            "src.api.routers.public_leads.LeadRepository",
            return_value=lead_repo,
        ), patch(
            "src.api.routers.public_leads.DownloadTokenRepository",
            return_value=token_repo,
        ), patch(
            "src.api.routers.public_leads.AuditWriter",
            return_value=mock_audit,
        ):
            c = TestClient(app)
            resp = c.post(
                "/api/v1/public/leads/capture",
                json={"email": "user@company.ca", "asset_id": 1, "turnstile_token": "valid"},
            )

        app.dependency_overrides.clear()
        assert resp.status_code == 200
        # Old token revoked, new one created
        token_repo.revoke.assert_awaited_once_with(existing_token.id)
        token_repo.create.assert_awaited_once()
        # Email re-sent
        mock_email_service.send_email.assert_awaited_once()

    def test_resend_revokes_old_and_creates_new_when_use_count_gt_zero(
        self,
        mock_turnstile: AsyncMock,
        mock_email_service: AsyncMock,
        mock_pub_repo: AsyncMock,
        mock_audit: AsyncMock,
    ) -> None:
        from src.core.database import get_db, get_session_factory
        from src.api.routers.public_leads import (
            _get_turnstile_validator, _get_email_service,
            _get_slack_notifier, _get_esp_client,
        )

        existing_lead = _make_lead()
        existing_token = _make_token(use_count=2)

        lead_repo = AsyncMock()
        lead_repo.get_or_create = AsyncMock(return_value=(existing_lead, False))

        token_repo = AsyncMock()
        token_repo.get_by_lead_and_asset = AsyncMock(return_value=existing_token)
        token_repo.revoke = AsyncMock()
        token_repo.create = AsyncMock(return_value=_make_token(token_id=2))

        async def override_db():
            mock_db = MagicMock()
            mock_db.flush = AsyncMock()
            mock_db.commit = AsyncMock()
            yield mock_db

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_session_factory] = _mock_session_factory
        app.dependency_overrides[_get_turnstile_validator] = lambda: mock_turnstile
        app.dependency_overrides[_get_email_service] = lambda: mock_email_service
        app.dependency_overrides[_get_slack_notifier] = lambda: AsyncMock()
        app.dependency_overrides[_get_esp_client] = lambda: None

        with patch(
            "src.api.routers.public_leads.PublicationRepository",
            return_value=mock_pub_repo,
        ), patch(
            "src.api.routers.public_leads.LeadRepository",
            return_value=lead_repo,
        ), patch(
            "src.api.routers.public_leads.DownloadTokenRepository",
            return_value=token_repo,
        ), patch(
            "src.api.routers.public_leads.AuditWriter",
            return_value=mock_audit,
        ):
            c = TestClient(app)
            resp = c.post(
                "/api/v1/public/leads/capture",
                json={"email": "user@company.ca", "asset_id": 1, "turnstile_token": "valid"},
            )

        app.dependency_overrides.clear()
        assert resp.status_code == 200
        # Old token revoked
        token_repo.revoke.assert_awaited_once_with(existing_token.id)
        # New token created
        token_repo.create.assert_awaited_once()
        # Email sent
        mock_email_service.send_email.assert_awaited_once()


# ---------------------------------------------------------------------------
# Tests: resend rate limit (A3)
# ---------------------------------------------------------------------------

class TestResendRateLimit:
    def test_resend_rate_limit_returns_429(
        self,
        mock_turnstile: AsyncMock,
        mock_email_service: AsyncMock,
        mock_pub_repo: AsyncMock,
        mock_audit: AsyncMock,
    ) -> None:
        from src.core.database import get_db, get_session_factory
        from src.api.routers.public_leads import (
            _get_turnstile_validator,
            _get_email_service,
            _get_slack_notifier,
            _get_esp_client,
            _resend_rate_limiter,
        )

        existing_lead = _make_lead()
        existing_token = _make_token(use_count=0)

        lead_repo = AsyncMock()
        lead_repo.get_or_create = AsyncMock(return_value=(existing_lead, False))

        token_repo = AsyncMock()
        token_repo.get_by_lead_and_asset = AsyncMock(return_value=existing_token)
        token_repo.revoke = AsyncMock()
        token_repo.create = AsyncMock(return_value=_make_token(token_id=2))

        # Use tight resend limiter: 1 resend per 120s
        tight_resend_limiter = InMemoryRateLimiter(max_requests=1, window_seconds=120)

        async def override_db():
            mock_db = MagicMock()
            mock_db.flush = AsyncMock()
            mock_db.commit = AsyncMock()
            yield mock_db

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_session_factory] = _mock_session_factory
        app.dependency_overrides[_get_turnstile_validator] = lambda: mock_turnstile
        app.dependency_overrides[_get_email_service] = lambda: mock_email_service
        app.dependency_overrides[_get_slack_notifier] = lambda: AsyncMock()
        app.dependency_overrides[_get_esp_client] = lambda: None

        with patch(
            "src.api.routers.public_leads.PublicationRepository",
            return_value=mock_pub_repo,
        ), patch(
            "src.api.routers.public_leads.LeadRepository",
            return_value=lead_repo,
        ), patch(
            "src.api.routers.public_leads.DownloadTokenRepository",
            return_value=token_repo,
        ), patch(
            "src.api.routers.public_leads.AuditWriter",
            return_value=mock_audit,
        ), patch(
            "src.api.routers.public_leads._resend_rate_limiter",
            tight_resend_limiter,
        ):
            c = TestClient(app)
            # First resend passes
            resp = c.post(
                "/api/v1/public/leads/capture",
                json={"email": "user@company.ca", "asset_id": 1, "turnstile_token": "valid"},
            )
            assert resp.status_code == 200

            # Second resend within 2 min is rate-limited
            resp = c.post(
                "/api/v1/public/leads/capture",
                json={"email": "user@company.ca", "asset_id": 1, "turnstile_token": "valid"},
            )
            assert resp.status_code == 429

        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests: validation
# ---------------------------------------------------------------------------

class TestInputValidation:
    def test_invalid_email_returns_422(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/public/leads/capture",
            json={"email": "not-an-email", "asset_id": 1, "turnstile_token": "valid"},
        )
        assert resp.status_code == 422

    def test_missing_turnstile_token_returns_422(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/public/leads/capture",
            json={"email": "user@company.ca", "asset_id": 1},
        )
        assert resp.status_code == 422
