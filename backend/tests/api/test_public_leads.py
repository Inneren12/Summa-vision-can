"""Tests for POST /api/v1/public/leads/capture."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.core.security.ip_rate_limiter import InMemoryRateLimiter
from src.main import app
from src.models.publication import Publication, PublicationStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_published_pub(asset_id: int = 1) -> Publication:
    pub = Publication(
        headline="Test",
        chart_type="BAR",
        virality_score=8.0,
        status=PublicationStatus.PUBLISHED,
        s3_key_lowres=f"graphics/{asset_id}/lowres.png",
        s3_key_highres=f"graphics/{asset_id}/highres.png",
    )
    pub.id = asset_id
    return pub


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset_rate_limiter() -> None:
    """Reset the module-level rate limiter before each test."""
    from src.api.routers.public_leads import _lead_rate_limiter
    _lead_rate_limiter.reset()

@pytest.fixture()
def mock_pub_repo() -> AsyncMock:
    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=_make_published_pub())
    return repo


@pytest.fixture()
def mock_lead_repo() -> AsyncMock:
    repo = AsyncMock()
    repo.create = AsyncMock()
    return repo


@pytest.fixture()
def mock_storage() -> AsyncMock:
    storage = AsyncMock()
    storage.generate_presigned_url = AsyncMock(
        return_value="https://s3.example.com/presigned-url?token=abc"
    )
    return storage


@pytest.fixture()
def client(
    mock_pub_repo: AsyncMock,
    mock_lead_repo: AsyncMock,
    mock_storage: AsyncMock,
) -> TestClient:
    from src.core.database import get_db
    from src.api.routers.public_leads import _get_storage

    async def override_db():
        yield MagicMock()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[_get_storage] = lambda: mock_storage

    with patch(
        "src.api.routers.public_leads.PublicationRepository",
        return_value=mock_pub_repo,
    ), patch(
        "src.api.routers.public_leads.LeadRepository",
        return_value=mock_lead_repo,
    ):
        yield TestClient(app)

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests: happy path
# ---------------------------------------------------------------------------

class TestLeadCapture:
    def test_returns_200_with_download_url(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/public/leads/capture",
            json={"email": "user@company.ca", "asset_id": 1},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "download_url" in body
        assert "presigned" in body["download_url"] or "s3" in body["download_url"]

    def test_lead_saved_to_db(
        self,
        client: TestClient,
        mock_lead_repo: AsyncMock,
    ) -> None:
        client.post(
            "/api/v1/public/leads/capture",
            json={"email": "user@company.ca", "asset_id": 1},
        )
        mock_lead_repo.create.assert_awaited_once()
        call_kwargs = mock_lead_repo.create.call_args.kwargs
        assert call_kwargs["email"] == "user@company.ca"
        assert call_kwargs["asset_id"] == "1"

    def test_b2b_email_flagged_correctly(
        self,
        client: TestClient,
        mock_lead_repo: AsyncMock,
    ) -> None:
        client.post(
            "/api/v1/public/leads/capture",
            json={"email": "ceo@tdbank.ca", "asset_id": 1},
        )
        call_kwargs = mock_lead_repo.create.call_args.kwargs
        assert call_kwargs["is_b2b"] is True
        assert call_kwargs["company_domain"] == "tdbank.ca"

    def test_consumer_email_not_b2b(
        self,
        client: TestClient,
        mock_lead_repo: AsyncMock,
    ) -> None:
        client.post(
            "/api/v1/public/leads/capture",
            json={"email": "user@gmail.com", "asset_id": 1},
        )
        call_kwargs = mock_lead_repo.create.call_args.kwargs
        assert call_kwargs["is_b2b"] is False


# ---------------------------------------------------------------------------
# Tests: 404 — asset not found
# ---------------------------------------------------------------------------

class TestAssetValidation:
    def test_404_if_publication_not_found(
        self,
        mock_lead_repo: AsyncMock,
        mock_storage: AsyncMock,
    ) -> None:
        from src.core.database import get_db
        from src.api.routers.public_leads import _get_storage

        pub_repo = AsyncMock()
        pub_repo.get_by_id = AsyncMock(return_value=None)

        async def override_db():
            yield MagicMock()

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[_get_storage] = lambda: mock_storage

        with patch(
            "src.api.routers.public_leads.PublicationRepository",
            return_value=pub_repo,
        ), patch(
            "src.api.routers.public_leads.LeadRepository",
            return_value=mock_lead_repo,
        ):
            c = TestClient(app)
            resp = c.post(
                "/api/v1/public/leads/capture",
                json={"email": "user@company.ca", "asset_id": 999},
            )

        app.dependency_overrides.clear()
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_404_if_publication_is_draft(
        self,
        mock_lead_repo: AsyncMock,
        mock_storage: AsyncMock,
    ) -> None:
        from src.core.database import get_db
        from src.api.routers.public_leads import _get_storage

        draft_pub = _make_published_pub()
        draft_pub.status = PublicationStatus.DRAFT

        pub_repo = AsyncMock()
        pub_repo.get_by_id = AsyncMock(return_value=draft_pub)

        async def override_db():
            yield MagicMock()

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[_get_storage] = lambda: mock_storage

        with patch(
            "src.api.routers.public_leads.PublicationRepository",
            return_value=pub_repo,
        ), patch(
            "src.api.routers.public_leads.LeadRepository",
            return_value=mock_lead_repo,
        ):
            c = TestClient(app)
            resp = c.post(
                "/api/v1/public/leads/capture",
                json={"email": "user@company.ca", "asset_id": 1},
            )

        app.dependency_overrides.clear()
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Tests: 429 — rate limiting
# ---------------------------------------------------------------------------

class TestRateLimit:
    def test_rate_limit_returns_429(self) -> None:
        from src.core.database import get_db
        from src.api.routers.public_leads import _get_storage

        pub_repo = AsyncMock()
        pub_repo.get_by_id = AsyncMock(return_value=_make_published_pub())
        lead_repo = AsyncMock()
        lead_repo.create = AsyncMock()
        storage = AsyncMock()
        storage.generate_presigned_url = AsyncMock(return_value="https://s3.example.com/url")

        # Tight limiter: 2 req/min
        tight_limiter = InMemoryRateLimiter(max_requests=2, window_seconds=60)

        async def override_db():
            yield MagicMock()

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[_get_storage] = lambda: storage

        with patch(
            "src.api.routers.public_leads.PublicationRepository",
            return_value=pub_repo,
        ), patch(
            "src.api.routers.public_leads.LeadRepository",
            return_value=lead_repo,
        ), patch(
            "src.api.routers.public_leads._lead_rate_limiter",
            tight_limiter,
        ):
            c = TestClient(app)
            # First 2 requests pass
            for _ in range(2):
                resp = c.post(
                    "/api/v1/public/leads/capture",
                    json={"email": "user@company.ca", "asset_id": 1},
                )
                assert resp.status_code == 200

            # 3rd is rate-limited
            resp = c.post(
                "/api/v1/public/leads/capture",
                json={"email": "user@company.ca", "asset_id": 1},
            )
            assert resp.status_code == 429

        app.dependency_overrides.clear()

    def test_invalid_email_returns_422(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/public/leads/capture",
            json={"email": "not-an-email", "asset_id": 1},
        )
        assert resp.status_code == 422
