"""KPI aggregation service (C-5).

Collects metrics from domain tables (publications, leads, jobs)
and event counts from the AuditEvent table, returning a single
KPIResponse snapshot.

Architecture:
    Follows ARCH-DPEN-001 — session_factory injected via constructor.
    All queries use aggregate SQL (func.count, GROUP BY) — no rows
    loaded into memory.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.models.audit_event import AuditEvent
from src.models.job import Job, JobStatus
from src.models.lead import Lead
from src.models.publication import Publication, PublicationStatus
from src.schemas.kpi import KPIResponse


# Known ISP email domains — leads from these are classified as B2C/ISP.
_ISP_DOMAINS: frozenset[str] = frozenset({
    "gmail.com",
    "yahoo.com",
    "yahoo.ca",
    "hotmail.com",
    "outlook.com",
    "protonmail.com",
    "icloud.com",
    "aol.com",
    "live.com",
    "mail.com",
})

# Education domain suffixes.
_EDU_SUFFIXES: tuple[str, ...] = (".edu", ".edu.ca", ".ac.uk", ".edu.au")


class KPIService:
    """Aggregates KPI metrics from domain tables and audit events.

    Parameters
    ----------
    session_factory:
        An async session maker — each call to ``get_kpi`` opens and
        closes its own short-lived session.
    """

    def __init__(self, session_factory: async_sessionmaker) -> None:
        self._session_factory = session_factory

    async def get_kpi(self, days: int = 30) -> KPIResponse:
        """Return aggregated KPI data for the given time window.

        Parameters
        ----------
        days:
            Number of days to look back from now (default 30).
        """
        now = datetime.now(timezone.utc)
        period_start = now - timedelta(days=days)

        async with self._session_factory() as session:
            # ----------------------------------------------------------
            # Publications (all-time, not period-scoped)
            # ----------------------------------------------------------
            total_publications = (
                await session.scalar(select(func.count(Publication.id)))
            ) or 0

            published_count = (
                await session.scalar(
                    select(func.count(Publication.id)).where(
                        Publication.status == PublicationStatus.PUBLISHED
                    )
                )
            ) or 0

            draft_count = total_publications - published_count

            # ----------------------------------------------------------
            # Leads (within period)
            # ----------------------------------------------------------
            lead_base = select(func.count(Lead.id)).where(
                Lead.created_at >= period_start
            )
            total_leads = (await session.scalar(lead_base)) or 0

            b2b_leads = (
                await session.scalar(
                    lead_base.where(Lead.is_b2b.is_(True))
                )
            ) or 0

            # Education: company_domain ends with .edu / .edu.ca / etc.
            edu_conditions = [
                Lead.company_domain.ilike(f"%{suffix}")
                for suffix in _EDU_SUFFIXES
            ]
            from sqlalchemy import or_

            education_leads = (
                await session.scalar(
                    lead_base.where(or_(*edu_conditions))
                )
            ) or 0

            # ISP: company_domain in known ISP list
            isp_leads = (
                await session.scalar(
                    lead_base.where(
                        func.lower(Lead.company_domain).in_(_ISP_DOMAINS)
                    )
                )
            ) or 0

            # B2C: everything that's not B2B
            b2c_leads = total_leads - b2b_leads

            # ESP sync status (all-time)
            esp_synced_count = (
                await session.scalar(
                    select(func.count(Lead.id)).where(
                        Lead.esp_synced.is_(True)
                    )
                )
            ) or 0

            esp_failed_permanent_count = (
                await session.scalar(
                    select(func.count(Lead.id)).where(
                        Lead.esp_sync_failed_permanent.is_(True)
                    )
                )
            ) or 0

            # ----------------------------------------------------------
            # AuditEvent counts (within period)
            # ----------------------------------------------------------
            event_rows = await session.execute(
                select(
                    AuditEvent.event_type,
                    func.count(AuditEvent.id),
                ).where(
                    AuditEvent.created_at >= period_start
                ).group_by(AuditEvent.event_type)
            )
            counts_map: dict[str, int] = {
                row[0]: row[1] for row in event_rows
            }

            emails_sent = counts_map.get("lead.email_sent", 0)
            tokens_created = counts_map.get("token.created", 0)
            tokens_activated = counts_map.get("token.activated", 0)
            tokens_exhausted = counts_map.get("token.exhausted", 0)
            catalog_syncs = counts_map.get("catalog.synced", 0)
            data_contract_violations = counts_map.get(
                "data.contract_violation", 0
            )

            # ----------------------------------------------------------
            # Jobs (within period)
            # ----------------------------------------------------------
            job_base = select(func.count(Job.id)).where(
                Job.created_at >= period_start
            )
            total_jobs = (await session.scalar(job_base)) or 0

            jobs_succeeded = (
                await session.scalar(
                    job_base.where(Job.status == JobStatus.SUCCESS)
                )
            ) or 0

            jobs_failed = (
                await session.scalar(
                    job_base.where(Job.status == JobStatus.FAILED)
                )
            ) or 0

            jobs_queued = (
                await session.scalar(
                    job_base.where(Job.status == JobStatus.QUEUED)
                )
            ) or 0

            jobs_running = (
                await session.scalar(
                    job_base.where(Job.status == JobStatus.RUNNING)
                )
            ) or 0

            # Job failure breakdown by type
            failed_rows = await session.execute(
                select(
                    Job.job_type,
                    func.count(Job.id),
                ).where(
                    Job.status == JobStatus.FAILED,
                    Job.created_at >= period_start,
                ).group_by(Job.job_type)
            )
            failed_by_type: dict[str, int] = {
                row[0]: row[1] for row in failed_rows
            }

        return KPIResponse(
            total_publications=total_publications,
            published_count=published_count,
            draft_count=draft_count,
            total_leads=total_leads,
            b2b_leads=b2b_leads,
            education_leads=education_leads,
            isp_leads=isp_leads,
            b2c_leads=b2c_leads,
            esp_synced_count=esp_synced_count,
            esp_failed_permanent_count=esp_failed_permanent_count,
            emails_sent=emails_sent,
            tokens_created=tokens_created,
            tokens_activated=tokens_activated,
            tokens_exhausted=tokens_exhausted,
            total_jobs=total_jobs,
            jobs_succeeded=jobs_succeeded,
            jobs_failed=jobs_failed,
            jobs_queued=jobs_queued,
            jobs_running=jobs_running,
            failed_by_type=failed_by_type,
            catalog_syncs=catalog_syncs,
            data_contract_violations=data_contract_violations,
            period_start=period_start,
            period_end=now,
        )
