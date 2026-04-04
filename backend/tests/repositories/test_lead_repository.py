"""Tests for LeadRepository.

Covers creation, deduplication via ``exists()``, and edge cases
around the email + asset_id uniqueness check.
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.lead_repository import LeadRepository


@pytest.mark.asyncio
class TestLeadRepository:
    """Test suite for :class:`LeadRepository`."""

    async def test_create_lead(self, db_session: AsyncSession) -> None:
        """Creating a lead should persist it and assign an id."""
        repo = LeadRepository(db_session)

        lead = await repo.create(
            email="user@example.com",
            ip_address="192.168.1.1",
            asset_id="pub-001",
            is_b2b=True,
            company_domain="example.com",
        )

        assert lead.id is not None
        assert lead.email == "user@example.com"
        assert lead.ip_address == "192.168.1.1"
        assert lead.asset_id == "pub-001"
        assert lead.is_b2b is True
        assert lead.company_domain == "example.com"
        assert lead.created_at is not None

    async def test_create_lead_defaults(
        self, db_session: AsyncSession
    ) -> None:
        """Creating with minimal args should use sane defaults."""
        repo = LeadRepository(db_session)

        lead = await repo.create(
            email="min@example.com",
            ip_address="10.0.0.1",
            asset_id="pub-002",
        )

        assert lead.is_b2b is False
        assert lead.company_domain is None

    async def test_exists_returns_false_when_no_match(
        self, db_session: AsyncSession
    ) -> None:
        """exists() returns False when there is no matching lead."""
        repo = LeadRepository(db_session)

        result = await repo.exists(
            email="nobody@example.com", asset_id="pub-999"
        )

        assert result is False

    async def test_exists_returns_true_after_create(
        self, db_session: AsyncSession
    ) -> None:
        """exists() returns True after creating a matching lead."""
        repo = LeadRepository(db_session)

        await repo.create(
            email="dup@example.com",
            ip_address="10.0.0.1",
            asset_id="pub-010",
        )
        await db_session.commit()

        assert await repo.exists(email="dup@example.com", asset_id="pub-010") is True

    async def test_exists_different_asset_returns_false(
        self, db_session: AsyncSession
    ) -> None:
        """exists() returns False when email matches but asset_id differs."""
        repo = LeadRepository(db_session)

        await repo.create(
            email="multi@example.com",
            ip_address="10.0.0.1",
            asset_id="pub-020",
        )
        await db_session.commit()

        # Same email, different asset — should NOT be considered a dup
        assert (
            await repo.exists(email="multi@example.com", asset_id="pub-021")
            is False
        )

    async def test_exists_different_email_returns_false(
        self, db_session: AsyncSession
    ) -> None:
        """exists() returns False when asset matches but email differs."""
        repo = LeadRepository(db_session)

        await repo.create(
            email="a@example.com",
            ip_address="10.0.0.1",
            asset_id="pub-030",
        )
        await db_session.commit()

        assert (
            await repo.exists(email="b@example.com", asset_id="pub-030")
            is False
        )

    async def test_exists_case_sensitive_email(
        self, db_session: AsyncSession
    ) -> None:
        """exists() is case-sensitive on email by default."""
        repo = LeadRepository(db_session)

        await repo.create(
            email="CaSe@Example.COM",
            ip_address="10.0.0.1",
            asset_id="pub-040",
        )
        await db_session.commit()

        # Exact case match
        assert (
            await repo.exists(email="CaSe@Example.COM", asset_id="pub-040")
            is True
        )

    async def test_deduplication_full_flow(
        self, db_session: AsyncSession
    ) -> None:
        """Full deduplication flow: check → create → check again."""
        repo = LeadRepository(db_session)
        email = "flow@example.com"
        asset = "pub-050"

        # Not yet present
        assert await repo.exists(email=email, asset_id=asset) is False

        # Create
        lead = await repo.create(
            email=email,
            ip_address="172.16.0.1",
            asset_id=asset,
            is_b2b=False,
        )
        await db_session.commit()
        assert lead.id is not None

        # Now present
        assert await repo.exists(email=email, asset_id=asset) is True

    async def test_multiple_leads_same_email_different_assets(
        self, db_session: AsyncSession
    ) -> None:
        """A user can legitimately have leads for multiple different assets."""
        repo = LeadRepository(db_session)
        email = "multi-asset@example.com"

        await repo.create(
            email=email, ip_address="10.0.0.1", asset_id="pub-A"
        )
        await repo.create(
            email=email, ip_address="10.0.0.1", asset_id="pub-B"
        )
        await db_session.commit()

        assert await repo.exists(email=email, asset_id="pub-A") is True
        assert await repo.exists(email=email, asset_id="pub-B") is True
        assert await repo.exists(email=email, asset_id="pub-C") is False
