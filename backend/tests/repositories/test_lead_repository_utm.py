"""Phase 2.3 UTM-attribution persistence tests for :class:`LeadRepository`.

These tests use the in-memory SQLite ``db_session`` fixture so we are
exercising the real ORM round-trip — they catch column / migration drift
that the router-level mocks in ``tests/api/test_inquiries_utm.py`` cannot.
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.lead_repository import LeadRepository


@pytest.mark.asyncio
class TestLeadRepositoryUtmPersistence:
    async def test_get_or_create_persists_all_utm_fields(
        self, db_session: AsyncSession
    ) -> None:
        repo = LeadRepository(db_session)

        lead, is_new = await repo.get_or_create(
            email="user@example.com",
            ip_address="127.0.0.1",
            asset_id="1",
            is_b2b=False,
            company_domain=None,
            utm_source="reddit",
            utm_medium="social",
            utm_campaign="publish_kit",
            utm_content="ln_abc123",
        )
        await db_session.commit()

        assert is_new is True
        assert lead.utm_source == "reddit"
        assert lead.utm_medium == "social"
        assert lead.utm_campaign == "publish_kit"
        assert lead.utm_content == "ln_abc123"

    async def test_get_or_create_persists_null_utm_when_not_provided(
        self, db_session: AsyncSession
    ) -> None:
        repo = LeadRepository(db_session)

        lead, is_new = await repo.get_or_create(
            email="user2@example.com",
            ip_address="127.0.0.1",
            asset_id="1",
            is_b2b=False,
            company_domain=None,
        )
        await db_session.commit()

        assert is_new is True
        assert lead.utm_source is None
        assert lead.utm_medium is None
        assert lead.utm_campaign is None
        assert lead.utm_content is None

    async def test_create_persists_all_utm_fields(
        self, db_session: AsyncSession
    ) -> None:
        repo = LeadRepository(db_session)

        lead = await repo.create(
            email="direct@example.com",
            ip_address="127.0.0.1",
            asset_id="2",
            utm_source="reddit",
            utm_medium="social",
            utm_campaign="publish_kit",
            utm_content="ln_direct_xyz",
        )
        await db_session.commit()

        # Round-trip via a fresh query to prove these are columns, not just
        # in-memory attributes.
        refetched = await repo.get_by_email_and_asset(
            "direct@example.com", "2"
        )
        assert refetched is not None
        assert refetched.utm_source == "reddit"
        assert refetched.utm_medium == "social"
        assert refetched.utm_campaign == "publish_kit"
        assert refetched.utm_content == "ln_direct_xyz"


@pytest.mark.asyncio
class TestLeadRepositoryExistingLeadBackfill:
    """Phase 2.3: organic-then-attributed flows must record UTM.

    Founder-locked semantics: first non-null attribution wins. Already-
    set UTM fields are never overwritten on a re-submit.
    """

    async def test_existing_lead_backfills_missing_utm(
        self, db_session: AsyncSession
    ) -> None:
        repo = LeadRepository(db_session)

        # First submit: no UTM (organic)
        lead1, _ = await repo.get_or_create(
            email="user@example.com",
            ip_address="127.0.0.1",
            asset_id="1",
            is_b2b=False,
            company_domain=None,
        )
        await db_session.commit()
        assert lead1.utm_content is None

        # Second submit: with UTM (visitor came back via publish-kit URL)
        lead2, is_new = await repo.get_or_create(
            email="user@example.com",
            ip_address="127.0.0.1",
            asset_id="1",
            is_b2b=False,
            company_domain=None,
            utm_source="reddit",
            utm_medium="social",
            utm_campaign="publish_kit",
            utm_content="ln_abc123",
        )
        await db_session.commit()

        assert is_new is False
        assert lead2.id == lead1.id
        assert lead2.utm_source == "reddit"
        assert lead2.utm_medium == "social"
        assert lead2.utm_campaign == "publish_kit"
        assert lead2.utm_content == "ln_abc123"

    async def test_existing_lead_does_not_overwrite_utm(
        self, db_session: AsyncSession
    ) -> None:
        repo = LeadRepository(db_session)

        # First submit: with UTM
        await repo.get_or_create(
            email="user@example.com",
            ip_address="127.0.0.1",
            asset_id="1",
            is_b2b=False,
            company_domain=None,
            utm_source="reddit",
            utm_content="ln_first",
        )
        await db_session.commit()

        # Second submit: different UTM
        lead2, is_new = await repo.get_or_create(
            email="user@example.com",
            ip_address="127.0.0.1",
            asset_id="1",
            is_b2b=False,
            company_domain=None,
            utm_source="twitter",
            utm_content="ln_second",
        )
        await db_session.commit()

        # First-touch attribution preserved.
        assert is_new is False
        assert lead2.utm_source == "reddit"
        assert lead2.utm_content == "ln_first"

    async def test_existing_lead_backfills_only_null_fields(
        self, db_session: AsyncSession
    ) -> None:
        """A partially-attributed lead has its NULL fields filled,
        but already-set fields keep the original value."""
        repo = LeadRepository(db_session)

        # First submit: only utm_content set (e.g. share URL with just
        # lineage_key, no other params).
        await repo.get_or_create(
            email="user@example.com",
            ip_address="127.0.0.1",
            asset_id="1",
            is_b2b=False,
            company_domain=None,
            utm_content="ln_locked",
        )
        await db_session.commit()

        # Second submit: utm_source set + different utm_content.
        lead2, _ = await repo.get_or_create(
            email="user@example.com",
            ip_address="127.0.0.1",
            asset_id="1",
            is_b2b=False,
            company_domain=None,
            utm_source="reddit",
            utm_content="ln_other",
        )
        await db_session.commit()

        # utm_source was NULL → filled. utm_content was already set →
        # NOT overwritten.
        assert lead2.utm_source == "reddit"
        assert lead2.utm_content == "ln_locked"
