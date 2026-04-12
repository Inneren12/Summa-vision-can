"""KPI response schema for the admin dashboard (C-5).

Aggregates metrics from domain tables (publications, leads, jobs) and
event counts from the AuditEvent table grouped by event_type.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class KPIResponse(BaseModel):
    """Aggregated KPI metrics for the admin dashboard."""

    # Publications
    total_publications: int
    published_count: int
    draft_count: int

    # Leads
    total_leads: int
    b2b_leads: int
    education_leads: int
    isp_leads: int
    b2c_leads: int
    esp_synced_count: int
    esp_failed_permanent_count: int

    # Download funnel (from AuditEvent)
    emails_sent: int
    tokens_created: int
    tokens_activated: int
    tokens_exhausted: int

    # Jobs
    total_jobs: int
    jobs_succeeded: int
    jobs_failed: int
    jobs_queued: int
    jobs_running: int
    failed_by_type: dict[str, int]

    # System (from AuditEvent)
    catalog_syncs: int
    data_contract_violations: int

    # Time range
    period_start: datetime
    period_end: datetime
