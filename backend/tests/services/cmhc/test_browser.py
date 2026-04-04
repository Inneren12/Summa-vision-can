"""Unit tests for the CMHC stealth browser context factory.

We cannot launch a real Chromium instance in CI, so the Playwright API
is fully mocked.  ``playwright-stealth`` uses a lazy import inside the
function, so we mock at the ``playwright_stealth`` package level.
"""

from __future__ import annotations

import sys
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.cmhc.browser import get_stealth_context


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_playwright() -> MagicMock:
    """Build a mock ``Playwright`` object with the expected async chain."""
    pw = MagicMock()

    # browser = await playwright.chromium.launch(...)
    mock_browser = AsyncMock()
    pw.chromium.launch = AsyncMock(return_value=mock_browser)

    # context = await browser.new_context(...)
    mock_context = AsyncMock()
    mock_browser.new_context = AsyncMock(return_value=mock_context)

    # page = await context.new_page()
    mock_page = AsyncMock()
    mock_context.new_page = AsyncMock(return_value=mock_page)

    return pw


@pytest.fixture(autouse=True)
def _mock_playwright_stealth() -> Any:
    """Auto-mock the ``playwright_stealth`` package for every test.

    Since the import is inside the function body, we inject a fake module
    into ``sys.modules`` so the ``from playwright_stealth import stealth_async``
    inside ``get_stealth_context`` resolves to our mock.
    """
    mock_module = MagicMock()
    mock_module.stealth_async = AsyncMock()

    with patch.dict(sys.modules, {"playwright_stealth": mock_module}):
        yield mock_module


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestGetStealthContext:
    """Tests for ``get_stealth_context``."""

    @pytest.mark.asyncio
    async def test_returns_browser_context(
        self, _mock_playwright_stealth: MagicMock
    ) -> None:
        """get_stealth_context should return the BrowserContext object."""
        pw = _make_mock_playwright()

        ctx = await get_stealth_context(pw)

        # The context is what browser.new_context() returned.
        expected_ctx = pw.chromium.launch.return_value.new_context.return_value
        assert ctx is expected_ctx

    @pytest.mark.asyncio
    async def test_launches_headless_by_default(
        self, _mock_playwright_stealth: MagicMock
    ) -> None:
        """Chromium should be launched with ``headless=True``."""
        pw = _make_mock_playwright()

        await get_stealth_context(pw)

        pw.chromium.launch.assert_awaited_once_with(headless=True)

    @pytest.mark.asyncio
    async def test_headless_false_when_requested(
        self, _mock_playwright_stealth: MagicMock
    ) -> None:
        """Caller can disable headless mode for debugging."""
        pw = _make_mock_playwright()

        await get_stealth_context(pw, headless=False)

        pw.chromium.launch.assert_awaited_once_with(headless=False)

    @pytest.mark.asyncio
    async def test_locale_and_timezone_forwarded(
        self, _mock_playwright_stealth: MagicMock
    ) -> None:
        """Custom locale / timezone should appear in context kwargs."""
        pw = _make_mock_playwright()

        await get_stealth_context(
            pw, locale="fr-CA", timezone_id="America/Montreal"
        )

        browser = pw.chromium.launch.return_value
        call_kwargs: dict[str, Any] = browser.new_context.call_args.kwargs
        assert call_kwargs["locale"] == "fr-CA"
        assert call_kwargs["timezone_id"] == "America/Montreal"

    @pytest.mark.asyncio
    async def test_user_agent_override(
        self, _mock_playwright_stealth: MagicMock
    ) -> None:
        """When user_agent is supplied, it should be passed to new_context."""
        pw = _make_mock_playwright()
        custom_ua = "CustomBot/1.0"

        await get_stealth_context(pw, user_agent=custom_ua)

        browser = pw.chromium.launch.return_value
        call_kwargs: dict[str, Any] = browser.new_context.call_args.kwargs
        assert call_kwargs["user_agent"] == custom_ua

    @pytest.mark.asyncio
    async def test_no_user_agent_by_default(
        self, _mock_playwright_stealth: MagicMock
    ) -> None:
        """When user_agent is None (default), the key should not be set."""
        pw = _make_mock_playwright()

        await get_stealth_context(pw)

        browser = pw.chromium.launch.return_value
        call_kwargs: dict[str, Any] = browser.new_context.call_args.kwargs
        assert "user_agent" not in call_kwargs

    @pytest.mark.asyncio
    async def test_stealth_async_called_on_page(
        self, _mock_playwright_stealth: MagicMock
    ) -> None:
        """playwright-stealth must be applied to a page."""
        pw = _make_mock_playwright()

        await get_stealth_context(pw)

        _mock_playwright_stealth.stealth_async.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_temporary_page_closed_after_stealth(
        self, _mock_playwright_stealth: MagicMock
    ) -> None:
        """The temporary page used for stealth patching should be closed."""
        pw = _make_mock_playwright()
        mock_context = pw.chromium.launch.return_value.new_context.return_value
        mock_page = mock_context.new_page.return_value

        await get_stealth_context(pw)

        mock_page.close.assert_awaited_once()
