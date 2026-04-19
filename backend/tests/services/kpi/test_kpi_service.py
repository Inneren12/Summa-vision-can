"""Integration tests for KPIService (C-5 / FIX 2).

Tests run against an in-memory SQLite database to verify that
``KPIService.get_kpi()`` produces correct, mutually exclusive lead
classifications and accurate aggregate counts.

Fixtures reuse the shared ``async_engine`` from ``conftest.py`` and
create an ``async_sessionmaker`` that ``KPIService`` expects.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
)

from src.models.audit_event import AuditEvent
from src.models.job import Job, JobStatus
from src.models.lead import Lead
from src.models.publication import Publication, PublicationStatus
from src.services.kpi.kpi_service import KPIService

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _utc_now() -> datetime:
    """Live UTC timestamp.

    Seed rows are stamped relative to ``datetime.now(timezone.utc)`` so
    the suite is date-agnostic. ``KPIService.get_kpi(days=N)`` computes
    the period window from the same live clock, which means ``now - 1h``
    is always inside any ``days >= 1`` window regardless of when CI runs.
    """
    return datetime.now(timezone.utc)


@pytest.fixture()
def session_factory(async_engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Return an async_sessionmaker bound to the test engine."""
    return async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


@pytest.fixture()
def kpi_service(session_factory: async_sessionmaker[AsyncSession]) -> KPIService:
    """Return a KPIService wired to the in-memory test DB."""
    return KPIService(session_factory)


async def _seed_lead(
    session: AsyncSession,
    *,
    email: str,
    is_b2b: bool = False,
    company_domain: str | None = None,
    created_at: datetime | None = None,
) -> Lead:
    """Insert a Lead row and return it."""
    lead = Lead(
        email=email,
        ip_address="127.0.0.1",
        asset_id="asset-1",
        is_b2b=is_b2b,
        company_domain=company_domain,
        created_at=created_at or _utc_now(),
    )
    session.add(lead)
    await session.flush()
    return lead


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestKPIServiceLeadClassification:
    """Lead categories must be mutually exclusive (B2B → Edu → ISP → B2C)."""

    @pytest.mark.asyncio()
    async def test_kpi_lead_categories_mutually_exclusive(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        kpi_service: KPIService,
    ) -> None:
        """A B2B lead with an .edu domain must count as B2B only, not Education."""
        async with session_factory() as session:
            # B2B + .edu domain — should be B2B, NOT education
            await _seed_lead(
                session,
                email="alice@mit.edu",
                is_b2b=True,
                company_domain="mit.edu",
            )
            # Pure education (not B2B)
            await _seed_lead(
                session,
                email="bob@stanford.edu",
                is_b2b=False,
                company_domain="stanford.edu",
            )
            # B2B + ISP domain — should be B2B, NOT ISP
            await _seed_lead(
                session,
                email="carol@gmail.com",
                is_b2b=True,
                company_domain="gmail.com",
            )
            # Pure ISP (not B2B, not edu)
            await _seed_lead(
                session,
                email="dave@yahoo.com",
                is_b2b=False,
                company_domain="yahoo.com",
            )
            # B2C — not B2B, not edu, not ISP
            await _seed_lead(
                session,
                email="eve@example.com",
                is_b2b=False,
                company_domain="example.com",
            )
            await session.commit()

        result = await kpi_service.get_kpi(days=30)

        assert result.total_leads == 5
        assert result.b2b_leads == 2       # alice + carol
        assert result.education_leads == 1  # bob
        assert result.isp_leads == 1        # dave
        assert result.b2c_leads == 1        # eve
        # Invariant: sum equals total
        assert (
            result.b2b_leads
            + result.education_leads
            + result.isp_leads
            + result.b2c_leads
        ) == result.total_leads

    @pytest.mark.asyncio()
    async def test_kpi_lead_classification_b2b(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        kpi_service: KPIService,
    ) -> None:
        """All B2B-flagged leads count in b2b_leads regardless of domain."""
        async with session_factory() as session:
            await _seed_lead(session, email="a@corp.com", is_b2b=True, company_domain="corp.com")
            await _seed_lead(session, email="b@uni.edu", is_b2b=True, company_domain="uni.edu")
            await _seed_lead(session, email="c@gmail.com", is_b2b=True, company_domain="gmail.com")
            await session.commit()

        result = await kpi_service.get_kpi(days=30)

        assert result.b2b_leads == 3
        assert result.education_leads == 0
        assert result.isp_leads == 0
        assert result.b2c_leads == 0

    @pytest.mark.asyncio()
    async def test_kpi_lead_classification_education(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        kpi_service: KPIService,
    ) -> None:
        """Non-B2B leads with .edu domains count as education."""
        async with session_factory() as session:
            await _seed_lead(session, email="a@harvard.edu", is_b2b=False, company_domain="harvard.edu")
            await _seed_lead(session, email="b@uottawa.edu.ca", is_b2b=False, company_domain="uottawa.edu.ca")
            await _seed_lead(session, email="c@oxford.ac.uk", is_b2b=False, company_domain="oxford.ac.uk")
            await session.commit()

        result = await kpi_service.get_kpi(days=30)

        assert result.education_leads == 3
        assert result.b2b_leads == 0
        assert result.isp_leads == 0
        assert result.b2c_leads == 0


class TestKPIServicePeriodFiltering:
    """Verify that the ``days`` parameter scopes lead/job/event counts."""

    @pytest.mark.asyncio()
    async def test_kpi_period_filtering(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        kpi_service: KPIService,
    ) -> None:
        """Leads outside the period window must be excluded."""
        now = _utc_now()
        async with session_factory() as session:
            # Inside 7-day window — one hour ago is always inside any
            # days>=1 window regardless of when the suite runs.
            await _seed_lead(
                session,
                email="recent@example.com",
                created_at=now - timedelta(hours=1),
            )
            # Outside 7-day window — eight days ago is always outside
            # a 7-day window regardless of when the suite runs.
            await _seed_lead(
                session,
                email="old@example.com",
                created_at=now - timedelta(days=8),
            )
            await session.commit()

        result = await kpi_service.get_kpi(days=7)

        assert result.total_leads == 1
        assert result.b2c_leads == 1


class TestKPIServiceEventAggregation:
    """Verify AuditEvent counts are aggregated correctly."""

    @pytest.mark.asyncio()
    async def test_kpi_event_aggregation(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        kpi_service: KPIService,
    ) -> None:
        """Event counts from audit_events are grouped by event_type."""
        async with session_factory() as session:
            for event_type, count in [
                ("lead.email_sent", 5),
                ("token.created", 3),
                ("token.activated", 2),
                ("catalog.synced", 1),
                ("data.contract_violation", 4),
            ]:
                for i in range(count):
                    session.add(
                        AuditEvent(
                            event_type=event_type,
                            entity_type="test",
                            entity_id=str(i),
                            created_at=_utc_now() - timedelta(hours=1),
                        )
                    )
            await session.commit()

        result = await kpi_service.get_kpi(days=30)

        assert result.emails_sent == 5
        assert result.tokens_created == 3
        assert result.tokens_activated == 2
        assert result.catalog_syncs == 1
        assert result.data_contract_violations == 4


class TestKPIServiceJobFailures:
    """Verify job failure breakdown by type."""

    @pytest.mark.asyncio()
    async def test_kpi_job_failure_breakdown(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        kpi_service: KPIService,
    ) -> None:
        """Failed jobs are grouped by job_type in failed_by_type."""
        async with session_factory() as session:
            for job_type, count in [("graphics_generate", 3), ("cube_fetch", 2)]:
                for i in range(count):
                    session.add(
                        Job(
                            job_type=job_type,
                            status=JobStatus.FAILED,
                            payload_json="{}",
                            created_at=_utc_now() - timedelta(hours=1),
                        )
                    )
            # A successful job — should NOT appear in failed_by_type
            session.add(
                Job(
                    job_type="graphics_generate",
                    status=JobStatus.SUCCESS,
                    payload_json="{}",
                    created_at=_utc_now() - timedelta(hours=1),
                )
            )
            await session.commit()

        result = await kpi_service.get_kpi(days=30)

        assert result.failed_by_type == {"graphics_generate": 3, "cube_fetch": 2}
        assert result.jobs_failed == 5
        assert result.jobs_succeeded == 1
        assert result.total_jobs == 6


class TestKPIServiceEmptyDB:
    """Verify behaviour with an empty database."""

    @pytest.mark.asyncio()
    async def test_kpi_empty_db(self, kpi_service: KPIService) -> None:
        """Empty database returns all-zero KPI without errors."""
        result = await kpi_service.get_kpi(days=30)

        assert result.total_publications == 0
        assert result.published_count == 0
        assert result.draft_count == 0
        assert result.total_leads == 0
        assert result.b2b_leads == 0
        assert result.education_leads == 0
        assert result.isp_leads == 0
        assert result.b2c_leads == 0
        assert result.total_jobs == 0
        assert result.jobs_succeeded == 0
        assert result.jobs_failed == 0
        assert result.failed_by_type == {}
        assert result.emails_sent == 0
        assert result.catalog_syncs == 0
        assert result.data_contract_violations == 0
