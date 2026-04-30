"""Admin-side response schemas for the leads surface.

Phase 2.3 introduces a per-publication lead listing endpoint
(``GET /api/v1/admin/publications/{id}/leads``) that needs to expose
fields beyond the public capture response. Kept separate from the public
schema to avoid leaking admin-visible attributes (e.g. ``ip_address``,
``utm_*``) into public payloads.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AdminLeadResponse(BaseModel):
    """Admin view of a captured lead.

    Includes UTM attribution fields (Phase 2.3) so admin tooling can
    audit the source publication of each lead.
    """

    id: int
    email: str
    asset_id: str
    is_b2b: bool
    company_domain: str | None
    category: str | None
    esp_synced: bool
    esp_sync_failed_permanent: bool
    utm_source: str | None
    utm_medium: str | None
    utm_campaign: str | None
    utm_content: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
