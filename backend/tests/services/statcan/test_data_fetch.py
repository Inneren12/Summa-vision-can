"""Tests for DataFetchService (Polars-first).

Mocks HTTP client and storage. Tests parse, validate, quality check.
Verifies NO pandas import in the module (R4).
"""

from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import polars as pl
import pytest

from src.services.statcan.data_fetch import (
    DataFetchService,
    FetchResult,
    DataQualityReport,
    REQUIRED_COLUMNS,
    PERIODS_MAP,
    SCALAR_FACTOR_MAP,
)
from src.core.exceptions import DataSourceError


# ---- Helpers ----

SAMPLE_CSV = """\
REF_DATE,GEO,DGUID,UOM,UOM_ID,SCALAR_FACTOR,SCALAR_ID,VECTOR,COORDINATE,VALUE,STATUS,SYMBOL,TERMINATED,DECIMALS
2024-01,Canada,A000011124,Percent,239,units,0,v1,1.1,5.3,,,,1
2024-02,Canada,A000011124,Percent,239,units,0,v1,1.1,5.5,,,,1
2024-01,Alberta,A000011124,Percent,239,thousands,3,v2,1.2,2.1,,,,1
2024-02,Alberta,A000011124,Percent,239,thousands,3,v2,1.2,2.3,,,,1
""".strip()


def _mock_http(csv_data: str = SAMPLE_CSV) -> AsyncMock:
    """Create mock HTTP client returning CSV bytes."""
    response = MagicMock()
    response.content = csv_data.encode("utf-8")
    response.raise_for_status = MagicMock()
    client = AsyncMock()
    client.get = AsyncMock(return_value=response)
    client.request = AsyncMock(return_value=response)
    return client


@pytest.mark.asyncio
async def test_fetch_handles_zipped_csv() -> None:
    """DataFetchService handles zipped CSV files correctly."""
    import zipfile
    import io
    csv_content = b'REF_DATE,GEO,DGUID,VALUE,SCALAR_ID\n2024-01,Canada,,100,0\n'
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, 'w') as zf:
        zf.writestr('12345678-eng.csv', csv_content)
    zip_bytes = zip_buf.getvalue()

    # Mock the HTTP response to return zip_bytes
    http_mock = MagicMock()
    response_mock = MagicMock()
    response_mock.content = zip_bytes
    response_mock.raise_for_status = MagicMock()
    http_mock.get = AsyncMock(return_value=response_mock)
    http_mock.request = AsyncMock(return_value=response_mock)

    service = DataFetchService(
        http_client=http_mock,
        storage=_mock_storage(),
    )

    result = await service.fetch_cube_data("14-10-0127")

    assert result.rows == 1
    assert result.columns >= 4


def _mock_storage() -> AsyncMock:
    """Create mock storage with upload_bytes."""
    storage = AsyncMock()
    storage.upload_bytes = AsyncMock()
    return storage


def _mock_catalog_repo(frequency: str = "Monthly") -> AsyncMock:
    """Create mock catalog repo returning a cube with given frequency."""
    cube = MagicMock()
    cube.frequency = frequency
    repo = AsyncMock()
    repo.get_by_product_id = AsyncMock(return_value=cube)
    return repo


# ---- Parse and clean ----

def test_parse_csv_returns_polars_dataframe() -> None:
    """CSV bytes are parsed into Polars DataFrame."""
    df = DataFetchService._parse_and_clean(
        SAMPLE_CSV.encode(), "test", 120
    )
    assert isinstance(df, pl.DataFrame)
    assert df.height == 4
    assert "REF_DATE" in df.columns
    assert "VALUE" in df.columns
    assert "GEO" in df.columns


def test_parse_csv_casts_value_to_float() -> None:
    """VALUE column is cast to Float64."""
    df = DataFetchService._parse_and_clean(
        SAMPLE_CSV.encode(), "test", 120
    )
    assert df["VALUE"].dtype == pl.Float64


def test_parse_csv_applies_scalar_factor() -> None:
    """VALUE_SCALED column is created with scalar factor applied."""
    df = DataFetchService._parse_and_clean(
        SAMPLE_CSV.encode(), "test", 120
    )
    assert "VALUE_SCALED" in df.columns

    # Row with SCALAR_ID=0 (units): VALUE_SCALED == VALUE
    units_row = df.filter(
        (pl.col("GEO") == "Canada") & (pl.col("REF_DATE") == "2024-01")
    )
    assert abs(units_row["VALUE_SCALED"][0] - 5.3) < 0.01

    # Row with SCALAR_ID=3 (thousands): VALUE_SCALED == VALUE * 1000
    thou_row = df.filter(
        (pl.col("GEO") == "Alberta") & (pl.col("REF_DATE") == "2024-01")
    )
    assert abs(thou_row["VALUE_SCALED"][0] - 2100.0) < 0.1


def test_parse_csv_handles_nan_values() -> None:
    """Non-numeric VALUE entries become null, not crash."""
    csv_with_nan = SAMPLE_CSV.replace("5.3", "..")
    df = DataFetchService._parse_and_clean(
        csv_with_nan.encode(), "test", 120
    )
    null_count = df.select(pl.col("VALUE").is_null().sum()).item()
    assert null_count >= 1  # ".." became null


# ---- Schema validation ----

def test_validate_schema_passes_with_required_columns() -> None:
    """No error when all required columns present."""
    df = DataFetchService._parse_and_clean(
        SAMPLE_CSV.encode(), "test", 120
    )
    # Should not raise
    DataFetchService._validate_schema(df, "test")


def test_validate_schema_raises_on_missing_column() -> None:
    """DataContractError when required column is missing."""
    df = pl.DataFrame({"REF_DATE": ["2024-01"], "GEO": ["Canada"]})
    with pytest.raises(DataSourceError) as exc_info:
        DataFetchService._validate_schema(df, "test")
    assert exc_info.value.error_code == "DATA_CONTRACT_VIOLATION"
    assert "VALUE" in str(exc_info.value)


# ---- Periods Truncation ----

@pytest.mark.asyncio
async def test_periods_truncation_keeps_latest_dates() -> None:
    """Monthly cube with periods=2 keeps only 2 latest REF_DATEs."""
    csv_content = (
        "REF_DATE,GEO,DGUID,VALUE,SCALAR_ID\n"
        "2024-01,Canada,,100.0,0\n"
        "2024-02,Canada,,200.0,0\n"
        "2024-03,Canada,,300.0,0\n"
        "2024-04,Canada,,400.0,0\n"
        "2024-01,Ontario,,110.0,0\n"
        "2024-02,Ontario,,210.0,0\n"
        "2024-03,Ontario,,310.0,0\n"
        "2024-04,Ontario,,410.0,0\n"
    )

    result_df = DataFetchService._parse_and_clean(
        csv_bytes=csv_content.encode(),
        product_id="test",
        periods=2,
    )

    unique_dates = result_df.select("REF_DATE").unique().sort("REF_DATE")
    assert unique_dates.height == 2
    assert unique_dates["REF_DATE"].to_list() == ["2024-03", "2024-04"]


@pytest.mark.asyncio
async def test_periods_truncation_annual() -> None:
    """Annual cube with periods=1 keeps only latest year."""
    csv_content = (
        "REF_DATE,GEO,DGUID,VALUE,SCALAR_ID\n"
        "2020,Canada,,1.0,0\n"
        "2021,Canada,,2.0,0\n"
        "2022,Canada,,3.0,0\n"
        "2023,Canada,,4.0,0\n"
    )

    result_df = DataFetchService._parse_and_clean(
        csv_bytes=csv_content.encode(),
        product_id="test",
        periods=1,
    )

    unique_dates = result_df.select("REF_DATE").unique().sort("REF_DATE")
    assert unique_dates.height == 1
    assert str(unique_dates["REF_DATE"].to_list()[0]) == "2023"


# ---- Data quality ----

def test_quality_report_accuracy() -> None:
    """DataQualityReport counts nulls correctly."""
    df = DataFetchService._parse_and_clean(
        SAMPLE_CSV.encode(), "test", 120
    )
    quality = DataFetchService._assess_quality(df)
    assert quality.total_rows == 4
    assert quality.null_rows == 0
    assert quality.null_percentage == 0.0


def test_quality_report_with_nulls() -> None:
    """Null values are counted in quality report."""
    csv = SAMPLE_CSV.replace("5.3", "").replace("5.5", "")
    df = DataFetchService._parse_and_clean(csv.encode(), "test", 120)
    quality = DataFetchService._assess_quality(df)
    assert quality.null_rows >= 1
    assert quality.null_percentage > 0


# ---- Dynamic periods ----

# ---- Full pipeline ----

@pytest.mark.asyncio
async def test_fetch_cube_data_full_pipeline() -> None:
    """Full fetch pipeline: download → parse → validate → save Parquet."""
    service = DataFetchService(
        _mock_http(),
        _mock_storage(),
    )

    result = await service.fetch_cube_data(
        "14-10-0127-01", periods=120, frequency="Monthly"
    )

    assert isinstance(result, FetchResult)
    assert result.product_id == "14-10-0127-01"
    assert result.rows == 4
    assert result.storage_key.endswith(".parquet")
    assert "processed" in result.storage_key


@pytest.mark.asyncio
async def test_fetch_saves_parquet_to_storage() -> None:
    """Parquet file is saved via storage.upload_bytes."""
    storage = _mock_storage()
    service = DataFetchService(
        _mock_http(), storage
    )

    await service.fetch_cube_data("14-10-0127-01", periods=120, frequency="Monthly")

    # upload_bytes called at least once for parquet
    assert storage.upload_bytes.call_count >= 1
    # Check that one call has .parquet key
    parquet_calls = [
        call for call in storage.upload_bytes.call_args_list
        if ".parquet" in str(call)
    ]
    assert len(parquet_calls) >= 1


# ---- R4 compliance: no pandas import ----

def test_no_pandas_import() -> None:
    """data_fetch.py must NOT import pandas (R4)."""
    source = (Path(__file__).parent.parent.parent.parent / "src" / "services" / "statcan" / "data_fetch.py").read_text()
    # Ensure it's not imported in the actual code
    import ast

    parsed = ast.parse(source)
    for node in ast.walk(parsed):
        if isinstance(node, ast.Import):
            for name in node.names:
                assert name.name != "pandas", "FORBIDDEN: pandas import in Polars-zone file"
        elif isinstance(node, ast.ImportFrom):
            assert node.module != "pandas", "FORBIDDEN: pandas import in Polars-zone file"


# ---- Handler registration ----

def test_cube_fetch_handler_registered() -> None:
    """cube_fetch handler is in HANDLER_REGISTRY."""
    from src.services.jobs.handlers import HANDLER_REGISTRY
    assert "cube_fetch" in HANDLER_REGISTRY