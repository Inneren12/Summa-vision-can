"""Unit tests for the CMHC extraction pipeline (``run_cmhc_extraction_pipeline``).

The browser is fully mocked — no Chromium process is spawned.  Tests
focus on the **orchestration logic**: snapshot upload, structural
validation, error propagation, and correct DataFrame return.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from src.core.exceptions import DataSourceError
from src.services.cmhc.service import (
    _build_url,
    _snapshot_key,
    run_cmhc_extraction_pipeline,
)

from tests.services.cmhc.conftest import (
    HTML_MISSING_TABLE,
    MockStorage,
    VALID_CMHC_HTML,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _patch_browser(html: str) -> MagicMock:
    """Build a mock for ``async_playwright`` that returns *html* on goto.

    The mock follows the chain:
        async_playwright() -> __aenter__  -> pw
        pw -> get_stealth_context          -> context
        context.new_page()                 -> page
        page.goto(...)                     -> None
        page.content()                     -> html
        context.close()                    -> None
    """
    mock_page = AsyncMock()
    mock_page.goto = AsyncMock()
    mock_page.content = AsyncMock(return_value=html)

    mock_context = AsyncMock()
    mock_context.new_page = AsyncMock(return_value=mock_page)
    mock_context.close = AsyncMock()

    return mock_context


# ---------------------------------------------------------------------------
# Unit helpers
# ---------------------------------------------------------------------------


class TestBuildUrl:
    """Tests for the internal ``_build_url`` helper."""

    def test_basic_city(self) -> None:
        url = _build_url("toronto")
        assert "toronto" in url
        assert url.startswith("https://")

    def test_city_is_lowered_and_stripped(self) -> None:
        url = _build_url("  Vancouver  ")
        assert "vancouver" in url
        assert "  " not in url


class TestSnapshotKey:
    """Tests for the internal ``_snapshot_key`` helper."""

    def test_key_format(self) -> None:
        key = _snapshot_key("toronto")
        assert key.startswith("cmhc/snapshots/")
        assert key.endswith("_toronto.html")

    def test_key_lowered_and_stripped(self) -> None:
        key = _snapshot_key("  Vancouver  ")
        assert "vancouver" in key
        assert "  " not in key


# ---------------------------------------------------------------------------
# Pipeline integration tests (with mocked browser)
# ---------------------------------------------------------------------------


class TestRunCmhcExtractionPipeline:
    """Tests for ``run_cmhc_extraction_pipeline``."""

    @pytest.mark.asyncio
    async def test_successful_extraction_returns_dataframe(
        self, mock_storage: MockStorage
    ) -> None:
        """Happy path: valid HTML → snapshot saved → DataFrame returned."""
        mock_context = _patch_browser(VALID_CMHC_HTML)

        with patch(
            "src.services.cmhc.service.get_stealth_context",
            new_callable=AsyncMock,
            return_value=mock_context,
        ), patch(
            "src.services.cmhc.service.async_playwright",
        ) as mock_pw_factory:
            # Wire up the async context manager
            mock_pw_instance = AsyncMock()
            mock_pw_factory.return_value.__aenter__ = AsyncMock(
                return_value=mock_pw_instance
            )
            mock_pw_factory.return_value.__aexit__ = AsyncMock(
                return_value=False
            )

            with patch(
                "src.services.cmhc.service.get_stealth_context",
                new_callable=AsyncMock,
                return_value=mock_context,
            ):
                df = await run_cmhc_extraction_pipeline(
                    "toronto", mock_storage
                )

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 3
        assert "Geography" in df.columns

    @pytest.mark.asyncio
    async def test_snapshot_is_saved_before_parsing(
        self, mock_storage: MockStorage
    ) -> None:
        """The raw HTML must be uploaded to storage."""
        mock_context = _patch_browser(VALID_CMHC_HTML)

        with patch(
            "src.services.cmhc.service.get_stealth_context",
            new_callable=AsyncMock,
            return_value=mock_context,
        ), patch(
            "src.services.cmhc.service.async_playwright",
        ) as mock_pw_factory:
            mock_pw_instance = AsyncMock()
            mock_pw_factory.return_value.__aenter__ = AsyncMock(
                return_value=mock_pw_instance
            )
            mock_pw_factory.return_value.__aexit__ = AsyncMock(
                return_value=False
            )

            with patch(
                "src.services.cmhc.service.get_stealth_context",
                new_callable=AsyncMock,
                return_value=mock_context,
            ):
                await run_cmhc_extraction_pipeline("toronto", mock_storage)

        # At least one snapshot should be saved
        assert len(mock_storage.uploaded_raw) == 1
        key = list(mock_storage.uploaded_raw.keys())[0]
        assert "cmhc/snapshots/" in key
        assert "_toronto.html" in key

        # The uploaded content should be the HTML string
        assert mock_storage.uploaded_raw[key] == VALID_CMHC_HTML

    @pytest.mark.asyncio
    async def test_invalid_structure_raises_datasource_error(
        self, mock_storage: MockStorage
    ) -> None:
        """When CMHC changes their DOM, a DataSourceError must be raised."""
        mock_context = _patch_browser(HTML_MISSING_TABLE)

        with patch(
            "src.services.cmhc.service.get_stealth_context",
            new_callable=AsyncMock,
            return_value=mock_context,
        ), patch(
            "src.services.cmhc.service.async_playwright",
        ) as mock_pw_factory:
            mock_pw_instance = AsyncMock()
            mock_pw_factory.return_value.__aenter__ = AsyncMock(
                return_value=mock_pw_instance
            )
            mock_pw_factory.return_value.__aexit__ = AsyncMock(
                return_value=False
            )

            with patch(
                "src.services.cmhc.service.get_stealth_context",
                new_callable=AsyncMock,
                return_value=mock_context,
            ):
                with pytest.raises(DataSourceError) as exc_info:
                    await run_cmhc_extraction_pipeline(
                        "toronto", mock_storage
                    )

        assert exc_info.value.error_code == "CMHC_STRUCTURE_INVALID"
        assert "toronto" in str(exc_info.value.context)

    @pytest.mark.asyncio
    async def test_snapshot_saved_even_when_validation_fails(
        self, mock_storage: MockStorage
    ) -> None:
        """Snapshot must be persisted BEFORE validation, so it's available
        for debugging even when the DOM check fails."""
        mock_context = _patch_browser(HTML_MISSING_TABLE)

        with patch(
            "src.services.cmhc.service.get_stealth_context",
            new_callable=AsyncMock,
            return_value=mock_context,
        ), patch(
            "src.services.cmhc.service.async_playwright",
        ) as mock_pw_factory:
            mock_pw_instance = AsyncMock()
            mock_pw_factory.return_value.__aenter__ = AsyncMock(
                return_value=mock_pw_instance
            )
            mock_pw_factory.return_value.__aexit__ = AsyncMock(
                return_value=False
            )

            with patch(
                "src.services.cmhc.service.get_stealth_context",
                new_callable=AsyncMock,
                return_value=mock_context,
            ):
                with pytest.raises(DataSourceError):
                    await run_cmhc_extraction_pipeline(
                        "toronto", mock_storage
                    )

        # Even on failure, snapshot was saved
        assert len(mock_storage.uploaded_raw) == 1

    @pytest.mark.asyncio
    async def test_context_closed_after_fetch(
        self, mock_storage: MockStorage
    ) -> None:
        """The browser context must be closed after fetching, even on success."""
        mock_context = _patch_browser(VALID_CMHC_HTML)

        with patch(
            "src.services.cmhc.service.get_stealth_context",
            new_callable=AsyncMock,
            return_value=mock_context,
        ), patch(
            "src.services.cmhc.service.async_playwright",
        ) as mock_pw_factory:
            mock_pw_instance = AsyncMock()
            mock_pw_factory.return_value.__aenter__ = AsyncMock(
                return_value=mock_pw_instance
            )
            mock_pw_factory.return_value.__aexit__ = AsyncMock(
                return_value=False
            )

            with patch(
                "src.services.cmhc.service.get_stealth_context",
                new_callable=AsyncMock,
                return_value=mock_context,
            ):
                await run_cmhc_extraction_pipeline("toronto", mock_storage)

        mock_context.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_city_name_case_insensitive(
        self, mock_storage: MockStorage
    ) -> None:
        """City name should be normalised (lowered, stripped)."""
        mock_context = _patch_browser(VALID_CMHC_HTML)

        with patch(
            "src.services.cmhc.service.get_stealth_context",
            new_callable=AsyncMock,
            return_value=mock_context,
        ), patch(
            "src.services.cmhc.service.async_playwright",
        ) as mock_pw_factory:
            mock_pw_instance = AsyncMock()
            mock_pw_factory.return_value.__aenter__ = AsyncMock(
                return_value=mock_pw_instance
            )
            mock_pw_factory.return_value.__aexit__ = AsyncMock(
                return_value=False
            )

            with patch(
                "src.services.cmhc.service.get_stealth_context",
                new_callable=AsyncMock,
                return_value=mock_context,
            ):
                df = await run_cmhc_extraction_pipeline(
                    "  TORONTO  ", mock_storage
                )

        assert isinstance(df, pd.DataFrame)
        key = list(mock_storage.uploaded_raw.keys())[0]
        assert "_toronto.html" in key
