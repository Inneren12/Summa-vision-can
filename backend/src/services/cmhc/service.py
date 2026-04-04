"""CMHC extraction pipeline — browser, snapshot, parse.

Orchestrates the full scraping workflow:

1. Open a stealth browser context via :func:`get_stealth_context`.
2. Navigate to the CMHC portal page for the requested *city*.
3. Capture the raw HTML page source.
4. **Save an HTML snapshot** to storage for debugging / auditing.
5. Validate the DOM structure and parse the data table into a DataFrame.

Usage::

    storage = get_storage_manager()
    df = await run_cmhc_extraction_pipeline("toronto", storage)
"""

from __future__ import annotations

from datetime import date, timezone, datetime

import pandas as pd
import structlog
from playwright.async_api import async_playwright

from src.core.exceptions import DataSourceError
from src.core.storage import StorageInterface
from src.services.cmhc.browser import get_stealth_context
from src.services.cmhc.parser import CMHCParser

logger: structlog.stdlib.BoundLogger = structlog.get_logger(
    module="cmhc.service",
)

# ---------------------------------------------------------------------------
# URL template
# ---------------------------------------------------------------------------

_CMHC_BASE_URL: str = (
    "https://www.cmhc-schl.gc.ca/professionals/"
    "housing-markets-data-and-research/housing-data/data-tables/"
    "household-characteristics/{city}"
)
"""Placeholder CMHC URL template.  Replace with the real portal URL."""


def _build_url(city: str) -> str:
    """Build the CMHC target URL for *city*.

    Parameters
    ----------
    city:
        City slug (e.g. ``"toronto"``).

    Returns
    -------
    str
        Fully-qualified URL.
    """
    return _CMHC_BASE_URL.format(city=city.lower().strip())


def _snapshot_key(city: str) -> str:
    """Generate a storage key for today's HTML snapshot.

    Format: ``cmhc/snapshots/{YYYY-MM-DD}_{city}.html``

    Parameters
    ----------
    city:
        City slug.

    Returns
    -------
    str
        Deterministic storage key.
    """
    today: str = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    return f"cmhc/snapshots/{today}_{city.lower().strip()}.html"


# ---------------------------------------------------------------------------
# Public pipeline
# ---------------------------------------------------------------------------


async def run_cmhc_extraction_pipeline(
    city: str,
    storage: StorageInterface,
) -> pd.DataFrame:
    """Execute the full CMHC scraping and parsing pipeline.

    Parameters
    ----------
    city:
        The city to scrape (used to build the target URL and the snapshot
        storage key).
    storage:
        A :class:`StorageInterface` implementation used to persist the
        raw HTML snapshot before parsing.

    Returns
    -------
    pd.DataFrame
        The parsed tabular data from the CMHC portal.

    Raises
    ------
    DataSourceError
        If DOM validation fails (CMHC changed their HTML structure) or if
        the page cannot be parsed.
    """
    url: str = _build_url(city)
    logger.info("Starting CMHC extraction", city=city, url=url)

    # 1. Fetch the page via stealth browser.
    async with async_playwright() as pw:
        context = await get_stealth_context(pw)
        page = await context.new_page()
        try:
            await page.goto(url, wait_until="networkidle", timeout=60_000)
            html: str = await page.content()
        finally:
            await context.close()

    logger.info(
        "HTML fetched from CMHC",
        city=city,
        html_length=len(html),
    )

    # 2. Snapshot: persist raw HTML BEFORE parsing.
    snapshot_path: str = _snapshot_key(city)
    await storage.upload_raw(data=html, path=snapshot_path)
    logger.info("HTML snapshot saved", path=snapshot_path)

    # 3. Validate structure and parse.
    parser = CMHCParser()

    if not parser.validate_structure(html):
        raise DataSourceError(
            message=(
                "CMHC HTML structure validation failed — the portal may "
                "have changed its DOM layout."
            ),
            error_code="CMHC_STRUCTURE_INVALID",
            context={"city": city, "snapshot_path": snapshot_path},
        )

    df: pd.DataFrame = parser.parse(html)

    logger.info(
        "CMHC extraction complete",
        city=city,
        rows=len(df),
        columns=len(df.columns),
    )

    return df
