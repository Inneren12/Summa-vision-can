"""HTML parser for CMHC real-estate data tables.

Extracts tabular data from CMHC portal pages using BeautifulSoup and
converts the result into a Pandas ``DataFrame``.  A structural validation
step is run **before** parsing to ensure the expected DOM elements are
present; if they are missing (e.g. CMHC changed their DOM), a ``CRITICAL``
log is emitted and a :class:`DataSourceError` is raised.

Usage::

    parser = CMHCParser()
    if parser.validate_structure(html):
        df = parser.parse(html)
"""

from __future__ import annotations

import io
from typing import Final

import pandas as pd
import structlog
from bs4 import BeautifulSoup, Tag

from src.core.exceptions import DataSourceError

logger: structlog.stdlib.BoundLogger = structlog.get_logger(
    module="cmhc.parser",
)

# ---------------------------------------------------------------------------
# Expected CSS selectors – update when CMHC redesigns their portal.
# ---------------------------------------------------------------------------

_EXPECTED_TABLE_TAG: Final[str] = "table"
"""The HTML element we expect to contain the data."""

_EXPECTED_HEADER_TAG: Final[str] = "thead"
"""The ``<thead>`` element expected inside the data table."""


class CMHCParser:
    """Parse CMHC HTML pages into Pandas DataFrames.

    The parser is stateless; a single instance can be reused across pages.
    """

    # ------------------------------------------------------------------ #
    # Structural validation                                               #
    # ------------------------------------------------------------------ #

    def validate_structure(self, html: str) -> bool:
        """Check that *html* contains the expected CMHC data-table markup.

        .. important::

           If this method returns ``False``, **do not** attempt to call
           :meth:`parse`.  A ``CRITICAL`` log is already emitted and the
           caller should raise :class:`DataSourceError`.

        Parameters
        ----------
        html:
            The full HTML document source returned by the CMHC portal.

        Returns
        -------
        bool
            ``True`` when the expected ``<table>`` element (with a
            ``<thead>``) is found; ``False`` otherwise.
        """
        soup = BeautifulSoup(html, "html.parser")

        table: Tag | None = soup.find(_EXPECTED_TABLE_TAG)
        if table is None:
            logger.critical(
                "CMHC DOM validation failed: no <table> element found",
                expected_tag=_EXPECTED_TABLE_TAG,
            )
            return False

        # Ensure the table has column headers (not just a stray <table>).
        if not isinstance(table, Tag) or table.find(_EXPECTED_HEADER_TAG) is None:
            logger.critical(
                "CMHC DOM validation failed: <table> has no <thead>",
                expected_tag=_EXPECTED_HEADER_TAG,
            )
            return False

        return True

    # ------------------------------------------------------------------ #
    # Parsing                                                             #
    # ------------------------------------------------------------------ #

    def parse(self, html: str) -> pd.DataFrame:
        """Parse the first HTML ``<table>`` in *html* into a DataFrame.

        This method assumes :meth:`validate_structure` has already been
        called and returned ``True``.  If the page contains multiple
        ``<table>`` elements, only the **first** is used.

        Parameters
        ----------
        html:
            The full HTML page source.

        Returns
        -------
        pd.DataFrame
            A DataFrame whose columns correspond to the ``<th>`` headers
            and whose rows correspond to each ``<tr>`` in the table body.

        Raises
        ------
        DataSourceError
            If the HTML cannot be parsed into a valid DataFrame.
        """
        try:
            dfs: list[pd.DataFrame] = pd.read_html(
                io.StringIO(html), flavor="bs4"
            )
        except ValueError as exc:
            raise DataSourceError(
                message="Failed to parse CMHC HTML into a DataFrame",
                error_code="CMHC_PARSE_FAILED",
                context={"original_error": str(exc)},
            ) from exc

        if not dfs:
            raise DataSourceError(
                message="No tables found in CMHC HTML after pd.read_html",
                error_code="CMHC_NO_TABLES",
            )

        df: pd.DataFrame = dfs[0]

        logger.info(
            "CMHC table parsed successfully",
            rows=len(df),
            columns=list(df.columns),
        )

        return df
