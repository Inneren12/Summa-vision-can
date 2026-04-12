"""Typed event taxonomy for operational audit trail (R18).

Every AuditEvent must use a value from this enum. Arbitrary strings
are rejected at write time. New event types are added here as new
features are built — the enum is the single source of truth.

When adding a new event type:
    1. Add it to EventType below.
    2. Add the writer call in the relevant service/handler.
    3. Update the KPI dashboard query if needed (Étape C).
"""

from __future__ import annotations

import enum


class EventType(str, enum.Enum):
    """Canonical event types for the audit trail."""

    # --- Jobs ---
    JOB_CREATED = "job.created"
    JOB_STARTED = "job.started"
    JOB_SUCCEEDED = "job.succeeded"
    JOB_FAILED = "job.failed"

    # --- Leads (added in Étape D) ---
    LEAD_CAPTURED = "lead.captured"
    LEAD_EMAIL_SENT = "lead.email_sent"
    LEAD_EMAIL_BOUNCED = "lead.email_bounced"

    # --- Tokens (added in Étape D) ---
    TOKEN_CREATED = "token.created"
    TOKEN_ACTIVATED = "token.activated"
    TOKEN_EXHAUSTED = "token.exhausted"
    TOKEN_EXPIRED = "token.expired"
    TOKEN_REVOKED = "token.revoked"

    # --- Publications (added in Étape B) ---
    PUBLICATION_GENERATED = "publication.generated"
    PUBLICATION_PUBLISHED = "publication.published"

    # --- ESP Sync (added in D-3) ---
    LEAD_ESP_SYNCED = "lead.esp_synced"
    LEAD_ESP_FAILED = "lead.esp_failed"
    LEAD_SCORED = "lead.scored"

    # --- Sponsorship (added in D-3) ---
    SPONSORSHIP_INQUIRY = "sponsorship.inquiry"

    # --- System ---
    CATALOG_SYNCED = "catalog.synced"
    DATA_CONTRACT_VIOLATION = "data.contract_violation"
