"""Phase 2.3 — UTM-to-lineage attribution tests.

Covers:
* ``POST /api/v1/public/leads/capture`` persists ``utm_*`` body fields.
* Capture without UTM still succeeds; columns stay NULL.
* ``LeadCaptureRequest`` ``extra="forbid"`` rejects unknown keys.
* ``GET /api/v1/admin/publications/{id}/leads`` filters by ``utm_content``
  (= ``Publication.lineage_key``) and 404s on unknown publication.
"""
from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.api.routers.admin_publications import (
    _get_audit,
    _get_repo,
    router as admin_router,
)
from src.api.schemas.public_leads import LeadCaptureRequest
from src.core.database import Base, get_db
from src.core.error_handler import register_exception_handlers
from src.core.security.auth import AuthMiddleware
from src.main import app as main_app
from src.models.lead import Lead
from src.models.publication import Publication, PublicationStatus
from src.repositories.publication_repository import PublicationRepository
from src.services.audit import AuditWriter
from tests.conftest import make_publication


# ---------------------------------------------------------------------------
# Public capture: UTM persistence tests (mirrors test_lead_capture.py shape)
# ---------------------------------------------------------------------------


def _make_published_pub(asset_id: int = 1) -> Publication:
    pub = make_publication(
        headline="Test Graphic",
        chart_type="BAR",
        status=PublicationStatus.PUBLISHED,
        s3_key_lowres=f"graphics/{asset_id}/lowres.png",
        s3_key_highres=f"graphics/{asset_id}/highres.png",
    )
    pub.id = asset_id
    return pub


def _make_lead(lead_id: int = 1) -> Lead:
    lead = Lead(
        email="user@company.ca",
        ip_address="127.0.0.1",
        asset_id="1",
        is_b2b=True,
        company_domain="company.ca",
    )
    lead.id = lead_id
    return lead


def _mock_session_factory():
    mock_session = MagicMock()
    mock_session.get = AsyncMock(return_value=_make_lead())
    mock_session.flush = AsyncMock()
    mock_session.commit = AsyncMock()

    @asynccontextmanager
    async def _ctx():
        yield mock_session

    return MagicMock(side_effect=lambda: _ctx())


@pytest.fixture(autouse=True)
def _reset_rate_limiters() -> None:
    from src.api.routers.public_leads import _lead_rate_limiter, _resend_rate_limiter
    _lead_rate_limiter.reset()
    _resend_rate_limiter.reset()


@pytest.fixture()
def capture_client() -> TestClient:
    """Yield a TestClient with the lead-capture deps stubbed.

    Mirrors ``test_lead_capture.py``'s fixture so we can assert on the
    UTM-related kwargs forwarded to ``LeadRepository.get_or_create``.
    """
    from src.core.database import get_session_factory
    from src.api.routers.public_leads import (
        _get_email_service,
        _get_esp_client,
        _get_slack_notifier,
        _get_turnstile_validator,
    )

    mock_turnstile = AsyncMock()
    mock_turnstile.validate = AsyncMock(return_value=True)

    mock_pub_repo = AsyncMock()
    mock_pub_repo.get_by_id = AsyncMock(return_value=_make_published_pub())

    mock_lead_repo = AsyncMock()
    mock_lead_repo.get_or_create = AsyncMock(return_value=(_make_lead(), True))

    mock_token_repo = AsyncMock()
    from src.models.download_token import DownloadToken
    from datetime import datetime, timedelta, timezone
    token = DownloadToken(
        token_hash="hash",
        lead_id=1,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=48),
        max_uses=5,
        use_count=0,
        revoked=False,
    )
    token.id = 1
    mock_token_repo.create = AsyncMock(return_value=token)
    mock_token_repo.get_by_lead_and_asset = AsyncMock(return_value=None)
    mock_token_repo.revoke = AsyncMock()

    mock_audit = AsyncMock()
    mock_audit.log_event = AsyncMock()

    async def override_db():
        mock_db = MagicMock()
        mock_db.flush = AsyncMock()
        mock_db.commit = AsyncMock()
        yield mock_db

    main_app.dependency_overrides[get_db] = override_db
    main_app.dependency_overrides[get_session_factory] = _mock_session_factory
    main_app.dependency_overrides[_get_turnstile_validator] = lambda: mock_turnstile
    main_app.dependency_overrides[_get_email_service] = lambda: AsyncMock()
    main_app.dependency_overrides[_get_slack_notifier] = lambda: AsyncMock()
    main_app.dependency_overrides[_get_esp_client] = lambda: None

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
        client = TestClient(main_app)
        client.mock_lead_repo = mock_lead_repo  # type: ignore[attr-defined]
        yield client

    main_app.dependency_overrides.clear()


class TestCaptureUtmPersistence:
    def test_capture_with_utm_forwards_to_repo(self, capture_client: TestClient) -> None:
        resp = capture_client.post(
            "/api/v1/public/leads/capture",
            json={
                "email": "user@company.ca",
                "asset_id": 1,
                "turnstile_token": "valid",
                "utm_source": "reddit",
                "utm_medium": "social",
                "utm_campaign": "publish_kit",
                "utm_content": "ln_abc123",
            },
        )
        assert resp.status_code == 200
        kwargs = capture_client.mock_lead_repo.get_or_create.call_args.kwargs  # type: ignore[attr-defined]
        assert kwargs["utm_source"] == "reddit"
        assert kwargs["utm_medium"] == "social"
        assert kwargs["utm_campaign"] == "publish_kit"
        assert kwargs["utm_content"] == "ln_abc123"

    def test_capture_without_utm_passes_none(self, capture_client: TestClient) -> None:
        resp = capture_client.post(
            "/api/v1/public/leads/capture",
            json={
                "email": "user@company.ca",
                "asset_id": 1,
                "turnstile_token": "valid",
            },
        )
        assert resp.status_code == 200
        kwargs = capture_client.mock_lead_repo.get_or_create.call_args.kwargs  # type: ignore[attr-defined]
        assert kwargs["utm_source"] is None
        assert kwargs["utm_medium"] is None
        assert kwargs["utm_campaign"] is None
        assert kwargs["utm_content"] is None

    def test_capture_rejects_unknown_field(self, capture_client: TestClient) -> None:
        """``extra="forbid"`` regression: surprise keys must 422."""
        resp = capture_client.post(
            "/api/v1/public/leads/capture",
            json={
                "email": "user@company.ca",
                "asset_id": 1,
                "turnstile_token": "valid",
                "utm_evil": "drop-tables",
            },
        )
        assert resp.status_code == 422


class TestLeadCaptureRequestSchema:
    def test_extra_forbid_default(self) -> None:
        with pytest.raises(Exception):  # ValidationError, but cheap import
            LeadCaptureRequest(
                email="user@example.com",
                asset_id=1,
                turnstile_token="t",
                some_unknown_key="x",  # type: ignore[call-arg]
            )

    def test_utm_fields_optional(self) -> None:
        req = LeadCaptureRequest(
            email="user@example.com",
            asset_id=1,
            turnstile_token="t",
        )
        assert req.utm_source is None
        assert req.utm_content is None


# ---------------------------------------------------------------------------
# Admin: per-publication leads endpoint
# ---------------------------------------------------------------------------


@pytest.fixture()
async def engine() -> AsyncGenerator[AsyncEngine, None]:
    eng = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest.fixture()
async def session_factory(engine: AsyncEngine):
    return async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )


def _make_admin_app(session_factory) -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(admin_router)

    async def _override_repo() -> AsyncGenerator[PublicationRepository, None]:
        async with session_factory() as session:
            try:
                yield PublicationRepository(session)
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def _override_audit() -> AsyncGenerator[AuditWriter, None]:
        async with session_factory() as session:
            try:
                yield AuditWriter(session)
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def _override_db() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[_get_repo] = _override_repo
    app.dependency_overrides[_get_audit] = _override_audit
    app.dependency_overrides[get_db] = _override_db

    app.add_middleware(AuthMiddleware, admin_api_key="test-admin-key")
    return app


def _auth() -> dict[str, str]:
    return {"X-API-KEY": "test-admin-key"}


async def _seed_publication_with_leads(
    session_factory,
    *,
    lineage_key: str,
    matching_emails: list[str],
    other_lineage_emails: list[str] | None = None,
) -> int:
    """Insert one publication + leads with matching/non-matching utm_content.

    Returns the publication id.
    """
    other_lineage_emails = other_lineage_emails or []
    async with session_factory() as session:
        pub = make_publication(
            headline="Attribution test",
            status=PublicationStatus.PUBLISHED,
            lineage_key=lineage_key,
        )
        session.add(pub)
        await session.flush()
        pub_id = pub.id

        for i, email in enumerate(matching_emails):
            lead = Lead(
                email=email,
                ip_address="127.0.0.1",
                asset_id=str(pub_id),
                utm_source="reddit",
                utm_medium="social",
                utm_campaign="publish_kit",
                utm_content=lineage_key,
            )
            session.add(lead)

        for email in other_lineage_emails:
            lead = Lead(
                email=email,
                ip_address="127.0.0.1",
                asset_id=str(pub_id),
                utm_content="ln_other_pub",
            )
            session.add(lead)

        # Also insert a lead with no UTM at all — must be excluded.
        session.add(
            Lead(
                email="organic@example.com",
                ip_address="127.0.0.1",
                asset_id=str(pub_id),
            )
        )
        await session.commit()
        return pub_id


@pytest.mark.asyncio
async def test_list_publication_leads_filters_by_lineage(
    session_factory,
) -> None:
    pub_id = await _seed_publication_with_leads(
        session_factory,
        lineage_key="ln_target_pub_123",
        matching_emails=["a@x.com", "b@x.com"],
        other_lineage_emails=["c@x.com"],
    )

    app = _make_admin_app(session_factory)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            f"/api/v1/admin/publications/{pub_id}/leads",
            headers=_auth(),
        )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    emails = sorted(row["email"] for row in data)
    assert emails == ["a@x.com", "b@x.com"]
    for row in data:
        assert row["utm_content"] == "ln_target_pub_123"


@pytest.mark.asyncio
async def test_list_publication_leads_returns_404_when_missing(
    session_factory,
) -> None:
    app = _make_admin_app(session_factory)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/admin/publications/999999/leads",
            headers=_auth(),
        )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_publication_leads_requires_auth(session_factory) -> None:
    app = _make_admin_app(session_factory)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/admin/publications/1/leads")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_list_publication_leads_empty_when_no_match(
    session_factory,
) -> None:
    pub_id = await _seed_publication_with_leads(
        session_factory,
        lineage_key="ln_no_traffic",
        matching_emails=[],
        other_lineage_emails=["foo@x.com"],
    )

    app = _make_admin_app(session_factory)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            f"/api/v1/admin/publications/{pub_id}/leads",
            headers=_auth(),
        )
    assert resp.status_code == 200
    assert resp.json() == []
