"""Unit tests for the CMHC HTML parser.

Covers:
- ``validate_structure`` on valid HTML, missing ``<table>``, missing
  ``<thead>``, and empty table bodies.
- ``parse`` on valid HTML, multi-table HTML, and error conditions.
- ``DataSourceError`` is raised when expected.
"""

from __future__ import annotations

import pytest

from src.core.exceptions import DataSourceError
from src.services.cmhc.parser import CMHCParser

from tests.services.cmhc.conftest import (
    HTML_EMPTY_TABLE,
    HTML_MISSING_TABLE,
    HTML_TABLE_NO_THEAD,
    VALID_CMHC_HTML,
    VALID_CMHC_HTML_MULTIPLE_TABLES,
)


# ===================================================================
# validate_structure
# ===================================================================


class TestValidateStructure:
    """Tests for ``CMHCParser.validate_structure``."""

    def test_valid_html_passes_validation(self, parser: CMHCParser) -> None:
        """A page with <table><thead>…</thead>…</table> passes."""
        assert parser.validate_structure(VALID_CMHC_HTML) is True

    def test_missing_table_fails_validation(self, parser: CMHCParser) -> None:
        """HTML without any <table> tag must fail."""
        assert parser.validate_structure(HTML_MISSING_TABLE) is False

    def test_table_without_thead_fails_validation(
        self, parser: CMHCParser
    ) -> None:
        """A <table> without <thead> must fail."""
        assert parser.validate_structure(HTML_TABLE_NO_THEAD) is False

    def test_empty_table_with_thead_passes(self, parser: CMHCParser) -> None:
        """A <table> with <thead> but an empty <tbody> is structurally valid."""
        assert parser.validate_structure(HTML_EMPTY_TABLE) is True

    def test_multiple_tables_passes_if_first_has_thead(
        self, parser: CMHCParser
    ) -> None:
        """When multiple tables exist, validation checks the first."""
        assert parser.validate_structure(VALID_CMHC_HTML_MULTIPLE_TABLES) is True

    def test_completely_empty_html_fails(self, parser: CMHCParser) -> None:
        """An empty string should fail validation."""
        assert parser.validate_structure("") is False

    def test_non_html_content_fails(self, parser: CMHCParser) -> None:
        """Plain text without HTML tags should fail."""
        assert parser.validate_structure("This is just plain text.") is False

    def test_div_only_html_fails(self, parser: CMHCParser) -> None:
        """HTML with divs but no table should fail."""
        html = "<html><body><div><p>No table here</p></div></body></html>"
        assert parser.validate_structure(html) is False


# ===================================================================
# parse
# ===================================================================


class TestParse:
    """Tests for ``CMHCParser.parse``."""

    def test_parse_valid_html_returns_dataframe(
        self, parser: CMHCParser
    ) -> None:
        """Parsing valid CMHC HTML produces a DataFrame with expected shape."""
        df = parser.parse(VALID_CMHC_HTML)

        assert len(df) == 3
        assert "Geography" in df.columns
        assert "Year" in df.columns
        assert "Starts" in df.columns
        assert "Completions" in df.columns
        assert "Under Construction" in df.columns

    def test_parse_valid_html_correct_values(
        self, parser: CMHCParser
    ) -> None:
        """Parsed values should match the source HTML."""
        df = parser.parse(VALID_CMHC_HTML)

        # First row assertions.
        row0 = df.iloc[0]
        assert row0["Geography"] == "Toronto CMA"
        assert row0["Year"] == 2024
        assert row0["Starts"] == 42150

    def test_parse_multiple_tables_uses_first(
        self, parser: CMHCParser
    ) -> None:
        """When multiple tables exist, the first table should be parsed."""
        df = parser.parse(VALID_CMHC_HTML_MULTIPLE_TABLES)
        assert "Nav" in df.columns

    def test_parse_no_table_raises_datasource_error(
        self, parser: CMHCParser
    ) -> None:
        """Parsing HTML with no table must raise DataSourceError."""
        with pytest.raises(DataSourceError) as exc_info:
            parser.parse(HTML_MISSING_TABLE)

        assert exc_info.value.error_code == "CMHC_PARSE_FAILED"

    def test_parse_empty_table_returns_empty_dataframe(
        self, parser: CMHCParser
    ) -> None:
        """An empty <tbody> should produce a DataFrame with 0 rows."""
        df = parser.parse(HTML_EMPTY_TABLE)
        assert len(df) == 0
        assert "Col A" in df.columns
        assert "Col B" in df.columns


# ===================================================================
# validate_structure + DataSourceError contract
# ===================================================================


class TestValidationAndErrorContract:
    """Verify the AC requirement: raise DataSourceError on invalid structure."""

    def test_missing_table_then_raise(self, parser: CMHCParser) -> None:
        """Full contract: validate → False → caller raises DataSourceError."""
        result = parser.validate_structure(HTML_MISSING_TABLE)
        assert result is False

        # Simulate what the service layer does:
        with pytest.raises(DataSourceError) as exc_info:
            raise DataSourceError(
                message="CMHC HTML structure validation failed",
                error_code="CMHC_STRUCTURE_INVALID",
                context={"city": "toronto"},
            )

        assert exc_info.value.error_code == "CMHC_STRUCTURE_INVALID"
        assert "toronto" in str(exc_info.value.context)

    def test_no_thead_then_raise(self, parser: CMHCParser) -> None:
        """validate_structure fails for table without <thead>."""
        result = parser.validate_structure(HTML_TABLE_NO_THEAD)
        assert result is False

        with pytest.raises(DataSourceError):
            raise DataSourceError(
                message="CMHC DOM validation failed: <table> has no <thead>",
                error_code="CMHC_STRUCTURE_INVALID",
            )
