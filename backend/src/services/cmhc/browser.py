"""Stealth browser context for CMHC scraping.

CMHC's portal is protected by bot-detection services (Cloudflare / Akamai).
We use ``playwright`` with ``playwright-stealth`` patches to present a
realistic browser fingerprint that avoids automated-browser detection.

Usage::

    from src.services.cmhc.browser import get_stealth_context

    async with async_playwright() as pw:
        ctx = await get_stealth_context(pw)
        page = await ctx.new_page()
        await page.goto("https://www.cmhc-schl.gc.ca/...")
        ...
        await ctx.close()
"""

from __future__ import annotations

from playwright.async_api import BrowserContext, Playwright


async def get_stealth_context(
    playwright: Playwright,
    *,
    headless: bool = True,
    locale: str = "en-CA",
    timezone_id: str = "America/Toronto",
    user_agent: str | None = None,
) -> BrowserContext:
    """Launch a headless Chromium browser and return a stealth context.

    The returned :class:`BrowserContext` has ``playwright-stealth`` patches
    applied so that common bot-detection scripts (e.g. navigator.webdriver,
    Chrome DevTools Protocol checks) are bypassed.

    Parameters
    ----------
    playwright:
        An already-initialised ``Playwright`` instance (from
        ``async_playwright().__aenter__()``).
    headless:
        Whether to run headless.  Defaults to ``True`` for production/CI.
    locale:
        Browser locale sent in the ``Accept-Language`` header.
    timezone_id:
        IANA timezone identifier used by the browser.
    user_agent:
        Optional override for the ``User-Agent`` header.  When ``None``,
        Playwright's default realistic UA string is used.

    Returns
    -------
    BrowserContext
        A Playwright browser context with stealth patches applied.
    """
    browser = await playwright.chromium.launch(headless=headless)

    context_kwargs: dict[str, object] = {
        "locale": locale,
        "timezone_id": timezone_id,
    }
    if user_agent is not None:
        context_kwargs["user_agent"] = user_agent

    context: BrowserContext = await browser.new_context(**context_kwargs)

    # Apply stealth patches to every page created from this context.
    # stealth_async expects a Page, so we create a blank page, patch it,
    # and subsequent pages inherit the context-level overrides.
    from playwright_stealth import stealth_async  # type: ignore[import-untyped]

    page = await context.new_page()
    await stealth_async(page)
    await page.close()

    return context
