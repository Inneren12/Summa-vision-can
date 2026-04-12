"""Tests for DownloadTokenRepository (D-2, C3).

Uses in-memory SQLite via the shared conftest.py fixtures.
Tests CRUD, atomic activation, revocation, and error reason detection.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.download_token import DownloadToken
from src.models.lead import Lead
from src.repositories.download_token_repository import DownloadTokenRepository


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _create_lead(session: AsyncSession) -> Lead:
    """Create a test lead record for FK reference."""
    lead = Lead(
        email="test@company.ca",
        ip_address="127.0.0.1",
        asset_id="1",
        is_b2b=True,
    )
    session.add(lead)
    await session.flush()
    await session.refresh(lead)
    return lead


# ---------------------------------------------------------------------------
# Tests: create()
# ---------------------------------------------------------------------------

class TestCreate:
    @pytest.mark.asyncio
    async def test_create_stores_token_with_correct_fields(
        self, db_session: AsyncSession
    ) -> None:
        lead = await _create_lead(db_session)
        repo = DownloadTokenRepository(db_session)

        expires = datetime.now(timezone.utc) + timedelta(hours=48)
        token = await repo.create(
            lead_id=lead.id,
            token_hash="abc123hash",
            expires_at=expires,
            max_uses=5,
        )

        assert token.id is not None
        assert token.lead_id == lead.id
        assert token.token_hash == "abc123hash"
        assert token.max_uses == 5
        assert token.use_count == 0
        assert token.revoked is False


# ---------------------------------------------------------------------------
# Tests: activate_atomic()
# ---------------------------------------------------------------------------

class TestActivateAtomic:
    @pytest.mark.asyncio
    async def test_activate_increments_use_count(
        self, db_session: AsyncSession
    ) -> None:
        lead = await _create_lead(db_session)
        repo = DownloadTokenRepository(db_session)

        token = await repo.create(
            lead_id=lead.id,
            token_hash="activatable_hash",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=48),
            max_uses=5,
        )

        result = await repo.activate_atomic("activatable_hash")
        assert result is not None
        assert result.use_count == 1

    @pytest.mark.asyncio
    async def test_activate_expired_returns_none(
        self, db_session: AsyncSession
    ) -> None:
        lead = await _create_lead(db_session)
        repo = DownloadTokenRepository(db_session)

        await repo.create(
            lead_id=lead.id,
            token_hash="expired_hash",
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
            max_uses=5,
        )

        result = await repo.activate_atomic("expired_hash")
        assert result is None

    @pytest.mark.asyncio
    async def test_activate_exhausted_returns_none(
        self, db_session: AsyncSession
    ) -> None:
        lead = await _create_lead(db_session)
        repo = DownloadTokenRepository(db_session)

        token = DownloadToken(
            lead_id=lead.id,
            token_hash="exhausted_hash",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=48),
            max_uses=5,
            use_count=5,
        )
        db_session.add(token)
        await db_session.flush()

        result = await repo.activate_atomic("exhausted_hash")
        assert result is None

    @pytest.mark.asyncio
    async def test_activate_revoked_returns_none(
        self, db_session: AsyncSession
    ) -> None:
        lead = await _create_lead(db_session)
        repo = DownloadTokenRepository(db_session)

        token = DownloadToken(
            lead_id=lead.id,
            token_hash="revoked_hash",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=48),
            max_uses=5,
            use_count=0,
            revoked=True,
        )
        db_session.add(token)
        await db_session.flush()

        result = await repo.activate_atomic("revoked_hash")
        assert result is None


# ---------------------------------------------------------------------------
# Tests: revoke()
# ---------------------------------------------------------------------------

class TestRevoke:
    @pytest.mark.asyncio
    async def test_revoke_sets_revoked_true(
        self, db_session: AsyncSession
    ) -> None:
        lead = await _create_lead(db_session)
        repo = DownloadTokenRepository(db_session)

        token = await repo.create(
            lead_id=lead.id,
            token_hash="to_revoke_hash",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=48),
            max_uses=5,
        )
        assert token.revoked is False

        await repo.revoke(token.id)
        await db_session.refresh(token)
        assert token.revoked is True


# ---------------------------------------------------------------------------
# Tests: get_by_lead_and_asset()
# ---------------------------------------------------------------------------

class TestGetByLeadAndAsset:
    @pytest.mark.asyncio
    async def test_returns_latest_non_revoked_token(
        self, db_session: AsyncSession
    ) -> None:
        lead = await _create_lead(db_session)
        repo = DownloadTokenRepository(db_session)

        # Create first token (will be revoked)
        token1 = await repo.create(
            lead_id=lead.id,
            token_hash="first_hash",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=48),
            max_uses=5,
        )
        await repo.revoke(token1.id)

        # Create second token (active)
        token2 = await repo.create(
            lead_id=lead.id,
            token_hash="second_hash",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=48),
            max_uses=5,
        )

        result = await repo.get_by_lead_and_asset(lead.id)
        assert result is not None
        assert result.id == token2.id
        assert result.token_hash == "second_hash"

    @pytest.mark.asyncio
    async def test_returns_none_when_no_tokens(
        self, db_session: AsyncSession
    ) -> None:
        lead = await _create_lead(db_session)
        repo = DownloadTokenRepository(db_session)

        result = await repo.get_by_lead_and_asset(lead.id)
        assert result is None


# ---------------------------------------------------------------------------
# Tests: get_error_reason()
# ---------------------------------------------------------------------------

class TestGetErrorReason:
    @pytest.mark.asyncio
    async def test_returns_none_for_unknown_hash(
        self, db_session: AsyncSession
    ) -> None:
        repo = DownloadTokenRepository(db_session)
        result = await repo.get_error_reason("nonexistent_hash")
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_expired_for_expired_token(
        self, db_session: AsyncSession
    ) -> None:
        lead = await _create_lead(db_session)
        repo = DownloadTokenRepository(db_session)

        await repo.create(
            lead_id=lead.id,
            token_hash="expired_reason_hash",
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
            max_uses=5,
        )

        result = await repo.get_error_reason("expired_reason_hash")
        assert result == "expired"

    @pytest.mark.asyncio
    async def test_returns_exhausted_for_maxed_token(
        self, db_session: AsyncSession
    ) -> None:
        lead = await _create_lead(db_session)
        repo = DownloadTokenRepository(db_session)

        token = DownloadToken(
            lead_id=lead.id,
            token_hash="exhausted_reason_hash",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=48),
            max_uses=5,
            use_count=5,
        )
        db_session.add(token)
        await db_session.flush()

        result = await repo.get_error_reason("exhausted_reason_hash")
        assert result == "exhausted"

    @pytest.mark.asyncio
    async def test_returns_revoked_for_revoked_token(
        self, db_session: AsyncSession
    ) -> None:
        lead = await _create_lead(db_session)
        repo = DownloadTokenRepository(db_session)

        token = DownloadToken(
            lead_id=lead.id,
            token_hash="revoked_reason_hash",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=48),
            max_uses=5,
            use_count=0,
            revoked=True,
        )
        db_session.add(token)
        await db_session.flush()

        result = await repo.get_error_reason("revoked_reason_hash")
        assert result == "revoked"
