"""Tests for GET /api/v1/public/download (D-2, C2).

Tests token exchange flow: valid token → 307 redirect,
expired/exhausted/revoked/unknown tokens → 403.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.models.download_token import DownloadToken
from src.models.lead import Lead
from src.models.publication import Publication, PublicationStatus
from tests.conftest import make_publication


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_token(
    token_id: int = 1,
    lead_id: int = 1,
    use_count: int = 1,
    max_uses: int = 5,
    revoked: bool = False,
    expired: bool = False,
) -> DownloadToken:
    token = DownloadToken(
        token_hash="fakehash",
        lead_id=lead_id,
        expires_at=(
            datetime.now(timezone.utc) - timedelta(hours=1)
            if expired
            else datetime.now(timezone.utc) + timedelta(hours=48)
        ),
        max_uses=max_uses,
        use_count=use_count,
        revoked=revoked,
    )
    token.id = token_id
    return token


def _make_lead(lead_id: int = 1) -> Lead:
    lead = Lead(
        email="user@company.ca",
        ip_address="127.0.0.1",
        asset_id="1",
        is_b2b=True,
    )
    lead.id = lead_id
    return lead


def _make_pub(asset_id: int = 1) -> Publication:
    pub = make_publication(
        headline="Test",
        chart_type="BAR",
        status=PublicationStatus.PUBLISHED,
        s3_key_lowres="graphics/1/lowres.png",
        s3_key_highres="graphics/1/highres.png",
    )
    pub.id = asset_id
    return pub


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def mock_token_repo() -> AsyncMock:
    repo = AsyncMock()
    repo.activate_atomic = AsyncMock(return_value=_make_token(use_count=1))
    repo.get_error_reason = AsyncMock(return_value=None)
    return repo


@pytest.fixture()
def mock_lead_repo() -> AsyncMock:
    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=_make_lead())
    return repo


@pytest.fixture()
def mock_pub_repo() -> AsyncMock:
    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=_make_pub())
    return repo


@pytest.fixture()
def mock_storage() -> AsyncMock:
    storage = AsyncMock()
    storage.generate_presigned_url = AsyncMock(
        return_value="https://s3.example.com/presigned-url?token=abc"
    )
    return storage


@pytest.fixture()
def mock_audit() -> AsyncMock:
    audit = AsyncMock()
    audit.log_event = AsyncMock()
    return audit


@pytest.fixture()
def client(
    mock_token_repo: AsyncMock,
    mock_lead_repo: AsyncMock,
    mock_pub_repo: AsyncMock,
    mock_storage: AsyncMock,
    mock_audit: AsyncMock,
) -> TestClient:
    from src.core.database import get_db
    from src.api.routers.public_download import _get_storage

    async def override_db():
        yield MagicMock()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[_get_storage] = lambda: mock_storage

    with patch(
        "src.api.routers.public_download.DownloadTokenRepository",
        return_value=mock_token_repo,
    ), patch(
        "src.api.routers.public_download.LeadRepository",
        return_value=mock_lead_repo,
    ), patch(
        "src.api.routers.public_download.PublicationRepository",
        return_value=mock_pub_repo,
    ), patch(
        "src.api.routers.public_download.AuditWriter",
        return_value=mock_audit,
    ):
        yield TestClient(app, follow_redirects=False)

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests: valid token → 307 redirect
# ---------------------------------------------------------------------------

class TestValidToken:
    def test_307_redirect_to_presigned_url(
        self,
        client: TestClient,
        mock_storage: AsyncMock,
    ) -> None:
        resp = client.get("/api/v1/public/download?token=valid-raw-token")
        assert resp.status_code == 307
        assert resp.headers["location"] == "https://s3.example.com/presigned-url?token=abc"

    def test_token_activated_audit_event(
        self,
        client: TestClient,
        mock_audit: AsyncMock,
    ) -> None:
        client.get("/api/v1/public/download?token=valid-raw-token")
        from src.schemas.events import EventType
        event_types = [call.kwargs["event_type"] for call in mock_audit.log_event.call_args_list]
        assert EventType.TOKEN_ACTIVATED in event_types


# ---------------------------------------------------------------------------
# Tests: expired token → 403
# ---------------------------------------------------------------------------

class TestExpiredToken:
    def test_expired_token_returns_403(
        self,
        mock_lead_repo: AsyncMock,
        mock_pub_repo: AsyncMock,
        mock_storage: AsyncMock,
        mock_audit: AsyncMock,
    ) -> None:
        from src.core.database import get_db
        from src.api.routers.public_download import _get_storage

        token_repo = AsyncMock()
        token_repo.activate_atomic = AsyncMock(return_value=None)
        token_repo.get_error_reason = AsyncMock(return_value="expired")

        async def override_db():
            yield MagicMock()

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[_get_storage] = lambda: mock_storage

        with patch(
            "src.api.routers.public_download.DownloadTokenRepository",
            return_value=token_repo,
        ), patch(
            "src.api.routers.public_download.LeadRepository",
            return_value=mock_lead_repo,
        ), patch(
            "src.api.routers.public_download.PublicationRepository",
            return_value=mock_pub_repo,
        ), patch(
            "src.api.routers.public_download.AuditWriter",
            return_value=mock_audit,
        ):
            c = TestClient(app, follow_redirects=False)
            resp = c.get("/api/v1/public/download?token=expired-token")

        app.dependency_overrides.clear()
        assert resp.status_code == 403
        assert "expired" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Tests: exhausted token → 403
# ---------------------------------------------------------------------------

class TestExhaustedToken:
    def test_exhausted_token_returns_403(
        self,
        mock_lead_repo: AsyncMock,
        mock_pub_repo: AsyncMock,
        mock_storage: AsyncMock,
        mock_audit: AsyncMock,
    ) -> None:
        from src.core.database import get_db
        from src.api.routers.public_download import _get_storage

        token_repo = AsyncMock()
        token_repo.activate_atomic = AsyncMock(return_value=None)
        token_repo.get_error_reason = AsyncMock(return_value="exhausted")

        async def override_db():
            yield MagicMock()

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[_get_storage] = lambda: mock_storage

        with patch(
            "src.api.routers.public_download.DownloadTokenRepository",
            return_value=token_repo,
        ), patch(
            "src.api.routers.public_download.LeadRepository",
            return_value=mock_lead_repo,
        ), patch(
            "src.api.routers.public_download.PublicationRepository",
            return_value=mock_pub_repo,
        ), patch(
            "src.api.routers.public_download.AuditWriter",
            return_value=mock_audit,
        ):
            c = TestClient(app, follow_redirects=False)
            resp = c.get("/api/v1/public/download?token=exhausted-token")

        app.dependency_overrides.clear()
        assert resp.status_code == 403
        assert "used too many times" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Tests: revoked token → 403
# ---------------------------------------------------------------------------

class TestRevokedToken:
    def test_revoked_token_returns_403(
        self,
        mock_lead_repo: AsyncMock,
        mock_pub_repo: AsyncMock,
        mock_storage: AsyncMock,
        mock_audit: AsyncMock,
    ) -> None:
        from src.core.database import get_db
        from src.api.routers.public_download import _get_storage

        token_repo = AsyncMock()
        token_repo.activate_atomic = AsyncMock(return_value=None)
        token_repo.get_error_reason = AsyncMock(return_value="revoked")

        async def override_db():
            yield MagicMock()

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[_get_storage] = lambda: mock_storage

        with patch(
            "src.api.routers.public_download.DownloadTokenRepository",
            return_value=token_repo,
        ), patch(
            "src.api.routers.public_download.LeadRepository",
            return_value=mock_lead_repo,
        ), patch(
            "src.api.routers.public_download.PublicationRepository",
            return_value=mock_pub_repo,
        ), patch(
            "src.api.routers.public_download.AuditWriter",
            return_value=mock_audit,
        ):
            c = TestClient(app, follow_redirects=False)
            resp = c.get("/api/v1/public/download?token=revoked-token")

        app.dependency_overrides.clear()
        assert resp.status_code == 403
        assert "revoked" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Tests: unknown token → 403
# ---------------------------------------------------------------------------

class TestUnknownToken:
    def test_unknown_token_returns_403(
        self,
        mock_lead_repo: AsyncMock,
        mock_pub_repo: AsyncMock,
        mock_storage: AsyncMock,
        mock_audit: AsyncMock,
    ) -> None:
        from src.core.database import get_db
        from src.api.routers.public_download import _get_storage

        token_repo = AsyncMock()
        token_repo.activate_atomic = AsyncMock(return_value=None)
        token_repo.get_error_reason = AsyncMock(return_value=None)

        async def override_db():
            yield MagicMock()

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[_get_storage] = lambda: mock_storage

        with patch(
            "src.api.routers.public_download.DownloadTokenRepository",
            return_value=token_repo,
        ), patch(
            "src.api.routers.public_download.LeadRepository",
            return_value=mock_lead_repo,
        ), patch(
            "src.api.routers.public_download.PublicationRepository",
            return_value=mock_pub_repo,
        ), patch(
            "src.api.routers.public_download.AuditWriter",
            return_value=mock_audit,
        ):
            c = TestClient(app, follow_redirects=False)
            resp = c.get("/api/v1/public/download?token=unknown-token")

        app.dependency_overrides.clear()
        assert resp.status_code == 403
        assert "invalid" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Tests: last use triggers token.exhausted event
# ---------------------------------------------------------------------------

class TestTokenExhaustedEvent:
    def test_last_use_triggers_exhausted_event(
        self,
        mock_lead_repo: AsyncMock,
        mock_pub_repo: AsyncMock,
        mock_storage: AsyncMock,
    ) -> None:
        from src.core.database import get_db
        from src.api.routers.public_download import _get_storage

        # Token at max uses after activation
        exhausting_token = _make_token(use_count=5, max_uses=5)

        token_repo = AsyncMock()
        token_repo.activate_atomic = AsyncMock(return_value=exhausting_token)

        audit = AsyncMock()
        audit.log_event = AsyncMock()

        async def override_db():
            yield MagicMock()

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[_get_storage] = lambda: mock_storage

        with patch(
            "src.api.routers.public_download.DownloadTokenRepository",
            return_value=token_repo,
        ), patch(
            "src.api.routers.public_download.LeadRepository",
            return_value=mock_lead_repo,
        ), patch(
            "src.api.routers.public_download.PublicationRepository",
            return_value=mock_pub_repo,
        ), patch(
            "src.api.routers.public_download.AuditWriter",
            return_value=audit,
        ):
            c = TestClient(app, follow_redirects=False)
            resp = c.get("/api/v1/public/download?token=valid-token")

        app.dependency_overrides.clear()
        assert resp.status_code == 307

        from src.schemas.events import EventType
        event_types = [call.kwargs["event_type"] for call in audit.log_event.call_args_list]
        assert EventType.TOKEN_ACTIVATED in event_types
        assert EventType.TOKEN_EXHAUSTED in event_types
