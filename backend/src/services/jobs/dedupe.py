"""Dedupe key generation for job types.

Uses UTC date by default to avoid timezone ambiguity.
Callers can pass an explicit date for business-day alignment.
"""

from __future__ import annotations

from datetime import date, datetime, timezone


def catalog_sync_key(target_date: date | None = None) -> str:
    """Generate dedupe key for catalog sync."""
    d = target_date or datetime.now(timezone.utc).date()
    return f"catalog_sync:{d.isoformat()}"


def cube_fetch_key(
    product_id: str, target_date: date | None = None
) -> str:
    """Generate dedupe key for cube data fetch."""
    d = target_date or datetime.now(timezone.utc).date()
    return f"fetch:{product_id}:{d.isoformat()}"
