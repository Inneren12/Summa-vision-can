"""Dedupe key generation for job types.

Canonical dedupe key patterns:
    catalog_sync → "catalog_sync:{yyyy-mm-dd}"
    cube_fetch   → "fetch:{product_id}:{yyyy-mm-dd}"

These ensure:
    - Only one catalog sync per day.
    - Only one fetch per cube per day.
    - Jobs from different days are independent.
"""

from __future__ import annotations

from datetime import date


def catalog_sync_key(target_date: date | None = None) -> str:
    """Generate dedupe key for catalog sync."""
    d = target_date or date.today()
    return f"catalog_sync:{d.isoformat()}"


def cube_fetch_key(
    product_id: str, target_date: date | None = None
) -> str:
    """Generate dedupe key for cube data fetch."""
    d = target_date or date.today()
    return f"fetch:{product_id}:{d.isoformat()}"
