"""Unit tests for the StatCan ETL Service (PR-06).

Tests cover:
* ``fetch_todays_releases`` — happy path, empty list, and mixed status codes.
* ``normalize_dataset`` — clean data, dirty data (``".."``), empty strings,
  ``None`` scalar factor, lowercase ``value`` column, no value column,
  high-NaN warning, zero-row edge case, and scalar factor 0.
"""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock

import pandas as pd
import pytest
from httpx import Response

from src.core.logging import setup_logging
from src.services.statcan.client import StatCanClient
from src.services.statcan.schemas import CubeMetadataResponse
from src.services.statcan.service import StatCanETLService
from src.services.statcan.validators import DataQualityReport


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _configure_structlog() -> None:
    """Ensure structlog routes through stdlib logging so caplog works."""
    setup_logging(force_json=False)


@pytest.fixture()
def mock_client() -> AsyncMock:
    """Return an ``AsyncMock`` that satisfies the ``StatCanClient`` interface."""
    return AsyncMock(spec=StatCanClient)


@pytest.fixture()
def service(mock_client: AsyncMock) -> StatCanETLService:
    """Return a ``StatCanETLService`` wired to a mocked client."""
    return StatCanETLService(mock_client)


# ===================================================================
# fetch_todays_releases
# ===================================================================


class TestFetchTodaysReleases:
    """Tests for ``StatCanETLService.fetch_todays_releases``."""

    @pytest.mark.asyncio
    async def test_returns_validated_metadata(
        self,
        mock_client: AsyncMock,
        service: StatCanETLService,
    ) -> None:
        """Happy path: one changed cube → one validated metadata response."""
        mock_get_response = AsyncMock(spec=Response)
        mock_get_response.json.return_value = [
            {
                "productId": 12345678,
                "cubeTitleEn": "Test Cube",
                "cubeTitleFr": "Cube de test",
                "releaseTime": "2026-03-09T08:30:00Z",
                "frequencyCode": 12,
            },
        ]
        mock_client.get.return_value = mock_get_response

        mock_meta_response = AsyncMock(spec=Response)
        mock_meta_response.json.return_value = [
            {
                "status": "SUCCESS",
                "object": {
                    "productId": 12345678,
                    "cubeTitleEn": "Test Cube",
                    "cubeTitleFr": "Cube de test",
                    "cubeStartDate": "2020-01-01T00:00:00Z",
                    "cubeEndDate": "2026-01-01T00:00:00Z",
                    "frequencyCode": 12,
                    "scalarFactorCode": 3,
                    "dimension": [
                        {
                            "dimensionNameEn": "Geography",
                            "dimensionNameFr": "Géographie",
                            "dimensionPositionId": 1,
                            "hasUom": False,
                        },
                    ],
                },
            },
        ]
        mock_client.request.return_value = mock_meta_response

        releases = await service.fetch_todays_releases()

        assert len(releases) == 1
        assert isinstance(releases[0], CubeMetadataResponse)
        assert releases[0].product_id == 12345678
        assert releases[0].scalar_factor_code == 3
        assert len(releases[0].dimensions) == 1

        mock_client.get.assert_called_once()
        mock_client.request.assert_called_once()

    @pytest.mark.asyncio
    async def test_empty_changed_cube_list(
        self,
        mock_client: AsyncMock,
        service: StatCanETLService,
    ) -> None:
        """No changed cubes → empty list, no metadata call."""
        mock_get_response = AsyncMock(spec=Response)
        mock_get_response.json.return_value = []
        mock_client.get.return_value = mock_get_response

        releases = await service.fetch_todays_releases()

        assert releases == []
        mock_client.get.assert_called_once()
        mock_client.request.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_non_success_entries(
        self,
        mock_client: AsyncMock,
        service: StatCanETLService,
    ) -> None:
        """Entries without status=SUCCESS are silently skipped."""
        mock_get_response = AsyncMock(spec=Response)
        mock_get_response.json.return_value = [
            {
                "productId": 11111111,
                "cubeTitleEn": "X",
                "cubeTitleFr": "X",
                "releaseTime": "2026-03-09T08:30:00Z",
                "frequencyCode": 1,
            },
        ]
        mock_client.get.return_value = mock_get_response

        mock_meta_response = AsyncMock(spec=Response)
        mock_meta_response.json.return_value = [
            {"status": "FAILED", "object": None},
        ]
        mock_client.request.return_value = mock_meta_response

        releases = await service.fetch_todays_releases()

        assert releases == []


# ===================================================================
# normalize_dataset
# ===================================================================


class TestNormalizeDataset:
    """Tests for ``StatCanETLService.normalize_dataset``."""

    # ---- clean data ---------------------------------------------------

    def test_clean_data_with_scalar(self, service: StatCanETLService) -> None:
        """Numeric values are multiplied by 10^scalar_factor_code."""
        raw_csv = "REF_DATE,GEO,VALUE\n2026-01,Canada,5.2\n2026-02,Canada,3.0\n"

        df, report = service.normalize_dataset(raw_csv, scalar_factor_code=3)

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert df["VALUE"].iloc[0] == pytest.approx(5200.0)
        assert df["VALUE"].iloc[1] == pytest.approx(3000.0)

        assert report.total_rows == 2
        assert report.valid_rows == 2
        assert report.nan_rows == 0
        assert report.nan_percentage == pytest.approx(0.0)

    def test_lowercase_value_column(self, service: StatCanETLService) -> None:
        """The ``value`` column (lowercase) is handled identically."""
        raw_csv = "REF_DATE,GEO,value\n2026-01,Canada,10\n"

        df, report = service.normalize_dataset(raw_csv, scalar_factor_code=2)

        assert df["value"].iloc[0] == pytest.approx(1000.0)
        assert report.total_rows == 1
        assert report.valid_rows == 1
        assert report.nan_rows == 0

    # ---- scalar_factor_code = None ------------------------------------

    def test_none_scalar_defaults_to_zero(
        self,
        service: StatCanETLService,
    ) -> None:
        """When scalar_factor_code is None, it defaults to 0 (no scaling)."""
        raw_csv = "REF_DATE,GEO,VALUE\n2026-01,Canada,7.5\n"

        df, report = service.normalize_dataset(raw_csv, scalar_factor_code=None)

        # 10 ** 0 == 1 → value unchanged.
        assert df["VALUE"].iloc[0] == pytest.approx(7.5)
        assert report.valid_rows == 1
        assert report.nan_rows == 0

    # ---- scalar_factor_code = 0 ---------------------------------------

    def test_scalar_factor_zero(self, service: StatCanETLService) -> None:
        """Scalar factor 0 means multiply by 1 — values stay the same."""
        raw_csv = "REF_DATE,GEO,VALUE\n2026-01,Canada,42\n"

        df, report = service.normalize_dataset(raw_csv, scalar_factor_code=0)

        assert df["VALUE"].iloc[0] == pytest.approx(42.0)
        assert report.valid_rows == 1

    # ---- dirty data: "..", empty strings, mixed -----------------------

    def test_double_dot_coerced_to_nan(self, service: StatCanETLService) -> None:
        """The StatCan artefact ``".."`` is coerced to NaN."""
        raw_csv = 'REF_DATE,GEO,VALUE\n2026-01,Canada,".."'

        df, report = service.normalize_dataset(raw_csv, scalar_factor_code=3)

        assert pd.isna(df["VALUE"].iloc[0])
        assert report.total_rows == 1
        assert report.nan_rows == 1
        assert report.valid_rows == 0
        assert report.nan_percentage == pytest.approx(100.0)

    def test_empty_string_coerced_to_nan(self, service: StatCanETLService) -> None:
        """Empty strings in the value column become NaN."""
        raw_csv = "REF_DATE,GEO,VALUE\n2026-01,Canada,\n"

        df, report = service.normalize_dataset(raw_csv, scalar_factor_code=1)

        assert pd.isna(df["VALUE"].iloc[0])
        assert report.nan_rows == 1

    def test_mixed_valid_and_invalid_values(
        self,
        service: StatCanETLService,
    ) -> None:
        """Mix of valid numbers, ``".."``, and empty strings."""
        raw_csv = (
            "REF_DATE,GEO,VALUE\n"
            "2026-01,Canada,5.0\n"
            '2026-02,Canada,".."\n'
            "2026-03,Canada,\n"
            "2026-04,Canada,10.0\n"
        )

        df, report = service.normalize_dataset(raw_csv, scalar_factor_code=0)

        # Two valid, two NaN.
        assert df["VALUE"].iloc[0] == pytest.approx(5.0)
        assert pd.isna(df["VALUE"].iloc[1])
        assert pd.isna(df["VALUE"].iloc[2])
        assert df["VALUE"].iloc[3] == pytest.approx(10.0)

        assert report.total_rows == 4
        assert report.valid_rows == 2
        assert report.nan_rows == 2
        assert report.nan_percentage == pytest.approx(50.0)

    def test_text_artefacts_coerced_to_nan(
        self,
        service: StatCanETLService,
    ) -> None:
        """Arbitrary text like ``"x"`` or ``"N/A"`` also becomes NaN."""
        raw_csv = "REF_DATE,GEO,VALUE\n2026-01,Canada,x\n2026-02,Canada,N/A\n"

        df, report = service.normalize_dataset(raw_csv, scalar_factor_code=1)

        assert report.nan_rows == 2
        assert report.valid_rows == 0
        assert report.nan_percentage == pytest.approx(100.0)

    # ---- high NaN warning log -----------------------------------------

    def test_high_nan_percentage_logs_warning(
        self,
        service: StatCanETLService,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """A WARNING is logged when nan_percentage > 50 %."""
        # 3 out of 4 rows are bad → 75 %
        raw_csv = (
            "REF_DATE,GEO,VALUE\n"
            '2026-01,Canada,".."\n'
            "2026-02,Canada,\n"
            "2026-03,Canada,x\n"
            "2026-04,Canada,1.0\n"
        )

        with caplog.at_level(logging.WARNING, logger="statcan.service"):
            _, report = service.normalize_dataset(raw_csv, scalar_factor_code=0)

        assert report.nan_percentage == pytest.approx(75.0)
        assert any("High NaN percentage" in rec.message for rec in caplog.records)

    def test_exactly_50_percent_nan_no_warning(
        self,
        service: StatCanETLService,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """A nan_percentage of exactly 50.0 should NOT trigger a warning."""
        raw_csv = (
            "REF_DATE,GEO,VALUE\n"
            "2026-01,Canada,1.0\n"
            '2026-02,Canada,".."\n'
        )

        with caplog.at_level(logging.WARNING, logger="statcan.service"):
            _, report = service.normalize_dataset(raw_csv, scalar_factor_code=0)

        assert report.nan_percentage == pytest.approx(50.0)
        assert not any("High NaN percentage" in rec.message for rec in caplog.records)

    def test_below_50_percent_nan_no_warning(
        self,
        service: StatCanETLService,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Below 50 % NaN → no warning."""
        raw_csv = (
            "REF_DATE,GEO,VALUE\n"
            "2026-01,Canada,1.0\n"
            "2026-02,Canada,2.0\n"
            '2026-03,Canada,".."\n'
        )

        with caplog.at_level(logging.WARNING, logger="statcan.service"):
            _, report = service.normalize_dataset(raw_csv, scalar_factor_code=0)

        assert report.nan_percentage < 50.0
        assert not any("High NaN percentage" in rec.message for rec in caplog.records)

    # ---- edge cases ---------------------------------------------------

    def test_no_value_column(self, service: StatCanETLService) -> None:
        """CSV without VALUE or value column → report shows 0 NaN rows."""
        raw_csv = "REF_DATE,GEO,SCORE\n2026-01,Canada,99\n"

        df, report = service.normalize_dataset(raw_csv, scalar_factor_code=3)

        assert report.total_rows == 1
        assert report.nan_rows == 0
        assert report.valid_rows == 1
        assert report.nan_percentage == pytest.approx(0.0)

    def test_empty_csv_body(self, service: StatCanETLService) -> None:
        """CSV with headers only → zero rows, 0 % NaN."""
        raw_csv = "REF_DATE,GEO,VALUE\n"

        df, report = service.normalize_dataset(raw_csv, scalar_factor_code=3)

        assert len(df) == 0
        assert report.total_rows == 0
        assert report.nan_rows == 0
        assert report.nan_percentage == pytest.approx(0.0)

    def test_all_nan_values(self, service: StatCanETLService) -> None:
        """All rows are non-numeric → 100 % NaN, warning logged."""
        raw_csv = (
            "REF_DATE,GEO,VALUE\n"
            '2026-01,Canada,".."\n'
            '2026-02,Canada,".."\n'
        )

        _, report = service.normalize_dataset(raw_csv, scalar_factor_code=0)

        assert report.nan_percentage == pytest.approx(100.0)
        assert report.nan_rows == 2
        assert report.valid_rows == 0

    # ---- DataQualityReport type checks --------------------------------

    def test_report_is_frozen_pydantic_model(
        self,
        service: StatCanETLService,
    ) -> None:
        """DataQualityReport is a frozen Pydantic BaseModel."""
        raw_csv = "REF_DATE,GEO,VALUE\n2026-01,Canada,1\n"
        _, report = service.normalize_dataset(raw_csv, scalar_factor_code=0)

        assert isinstance(report, DataQualityReport)
        with pytest.raises(Exception):
            report.total_rows = 999  # type: ignore[misc]
