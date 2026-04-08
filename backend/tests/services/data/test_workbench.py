"""Tests for DataWorkbench — pure Polars transformations.

All tests use in-memory Polars DataFrames, no DB or I/O.
Verifies ARCH-PURA-001 compliance and R14 merge safety.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import polars as pl
import pytest

from src.services.data.workbench import (
    aggregate_time,
    filter_geo,
    filter_date_range,
    calc_yoy_change,
    calc_mom_change,
    calc_rolling_avg,
    merge_cubes,
)
from src.core.exceptions import WorkbenchError


# ---- Shared test data ----

def _monthly_df(months: int = 24, geo: str = "Canada") -> pl.DataFrame:
    """Create a realistic monthly StatCan-shaped DataFrame."""
    dates = [f"2023-{m:02d}-01" for m in range(1, 13)] + \
            [f"2024-{m:02d}-01" for m in range(1, min(months - 12 + 1, 13))]
    dates = dates[:months]
    return pl.DataFrame({
        "REF_DATE": dates,
        "GEO": [geo] * len(dates),
        "VALUE": [100.0 + i * 2.5 for i in range(len(dates))],
    }).with_columns(
        pl.col("REF_DATE").str.strptime(pl.Date, "%Y-%m-%d")
    )


def _multi_geo_df() -> pl.DataFrame:
    """Monthly data for two geographies."""
    canada = _monthly_df(24, "Canada")
    alberta = _monthly_df(24, "Alberta").with_columns(
        (pl.col("VALUE") * 0.8).alias("VALUE")
    )
    return pl.concat([canada, alberta])


# ---- aggregate_time ----

def test_aggregate_monthly_to_quarterly() -> None:
    """Monthly data aggregated to quarterly reduces rows."""
    df = _monthly_df(12)
    result = aggregate_time(df, freq="Q", method="mean")
    assert result.height == 4  # 12 months → 4 quarters
    assert "VALUE" in result.columns


def test_aggregate_monthly_to_yearly() -> None:
    """Monthly data aggregated to yearly."""
    df = _monthly_df(12)
    result = aggregate_time(df, freq="Y", method="sum")
    assert result.height == 1
    total = result["VALUE"][0]
    assert total > 0


def test_aggregate_with_group_cols() -> None:
    """Aggregation respects group columns."""
    df = _multi_geo_df()
    result = aggregate_time(df, freq="Q", method="mean", group_cols=["GEO"])
    geos = result["GEO"].unique().to_list()
    assert "Canada" in geos
    assert "Alberta" in geos


def test_aggregate_invalid_freq_raises() -> None:
    """Invalid frequency raises WorkbenchError."""
    df = _monthly_df(12)
    with pytest.raises(WorkbenchError, match="Invalid frequency"):
        aggregate_time(df, freq="X", method="mean")


def test_aggregate_invalid_method_raises() -> None:
    """Invalid method raises WorkbenchError."""
    df = _monthly_df(12)
    with pytest.raises(WorkbenchError, match="Invalid method"):
        aggregate_time(df, freq="Q", method="median_invalid")


# ---- filter_geo ----

def test_filter_geo_canada() -> None:
    """Filter to Canada only."""
    df = _multi_geo_df()
    result = filter_geo(df, "Canada")
    assert all(g == "Canada" for g in result["GEO"].to_list())


def test_filter_geo_case_insensitive() -> None:
    """Filtering is case-insensitive."""
    df = _multi_geo_df()
    result = filter_geo(df, "alberta")
    assert result.height > 0
    assert all("Alberta" in g for g in result["GEO"].to_list())


def test_filter_geo_no_match_returns_empty() -> None:
    """Non-matching geography returns empty DataFrame."""
    df = _multi_geo_df()
    result = filter_geo(df, "Nunavut")
    assert result.height == 0


# ---- filter_date_range ----

def test_filter_date_range_both_bounds() -> None:
    """Filter with start and end date."""
    df = _monthly_df(24)
    result = filter_date_range(df, start="2023-06-01", end="2023-09-01")
    assert result.height > 0
    assert result.height < df.height


def test_filter_date_range_start_only() -> None:
    """Filter with only start date."""
    df = _monthly_df(24)
    result = filter_date_range(df, start="2024-01-01")
    assert result.height > 0
    assert result.height < df.height


def test_filter_date_range_end_only() -> None:
    """Filter with only end date."""
    df = _monthly_df(24)
    result = filter_date_range(df, end="2023-06-01")
    assert result.height > 0


# ---- calc_yoy_change ----

def test_yoy_change_produces_column() -> None:
    """YoY change adds output column."""
    df = _monthly_df(24)
    result = calc_yoy_change(df)
    assert "YOY_CHANGE_PCT" in result.columns


def test_yoy_change_first_12_are_null() -> None:
    """First 12 months have null YoY (no prior year data)."""
    df = _monthly_df(24)
    result = calc_yoy_change(df)
    nulls = result.head(12)["YOY_CHANGE_PCT"].is_null().sum()
    assert nulls == 12


def test_yoy_change_values_non_null_after_12() -> None:
    """After 12 months, YoY values are calculated."""
    df = _monthly_df(24)
    result = calc_yoy_change(df)
    non_null = result.tail(12)["YOY_CHANGE_PCT"].is_not_null().sum()
    assert non_null == 12


# ---- calc_mom_change ----

def test_mom_change_produces_column() -> None:
    """MoM change adds output column."""
    df = _monthly_df(12)
    result = calc_mom_change(df)
    assert "MOM_CHANGE_PCT" in result.columns


def test_mom_change_first_is_null() -> None:
    """First month has null MoM."""
    df = _monthly_df(12)
    result = calc_mom_change(df)
    assert result["MOM_CHANGE_PCT"][0] is None


# ---- calc_rolling_avg ----

def test_rolling_avg_produces_column() -> None:
    """Rolling average adds output column."""
    df = _monthly_df(24)
    result = calc_rolling_avg(df, window=3)
    assert "ROLLING_AVG" in result.columns


def test_rolling_avg_window_1_equals_value() -> None:
    """Rolling average with window=1 equals original values."""
    df = _monthly_df(12)
    result = calc_rolling_avg(df, window=1)
    # Values should be (approximately) equal
    for v, r in zip(result["VALUE"].to_list(), result["ROLLING_AVG"].to_list()):
        if r is not None:
            assert abs(v - r) < 0.01


def test_rolling_avg_invalid_window_raises() -> None:
    """Window < 1 raises WorkbenchError."""
    df = _monthly_df(12)
    with pytest.raises(WorkbenchError, match="window"):
        calc_rolling_avg(df, window=0)


# ---- merge_cubes ----

def test_merge_two_cubes() -> None:
    """Merging two cubes on REF_DATE + GEO."""
    df1 = _monthly_df(12, "Canada").rename({"VALUE": "VACANCY"})
    df2 = _monthly_df(12, "Canada").rename({"VALUE": "RENT"})
    result = merge_cubes([df1, df2], merge_keys=["REF_DATE", "GEO"])
    assert "VACANCY" in result.columns
    assert "RENT" in result.columns
    assert result.height == 12


def test_merge_validates_keys_exist() -> None:
    """Missing merge key raises WorkbenchError."""
    df1 = _monthly_df(12)
    df2 = pl.DataFrame({"X": [1, 2], "Y": [3, 4]})
    with pytest.raises(WorkbenchError, match="missing merge keys"):
        merge_cubes([df1, df2], merge_keys=["REF_DATE", "GEO"])


def test_merge_validates_key_uniqueness() -> None:
    """Duplicate keys in input raise WorkbenchError."""
    df1 = pl.DataFrame({
        "REF_DATE": [date(2024, 1, 1), date(2024, 1, 1)],
        "GEO": ["Canada", "Canada"],
        "VALUE": [1.0, 2.0],
    })
    df2 = _monthly_df(2, "Canada")
    with pytest.raises(WorkbenchError, match="duplicate merge keys"):
        merge_cubes([df1, df2], merge_keys=["REF_DATE", "GEO"])


def test_merge_requires_minimum_two() -> None:
    """Single DataFrame raises WorkbenchError."""
    df = _monthly_df(12)
    with pytest.raises(WorkbenchError, match="at least 2"):
        merge_cubes([df])


# --- YoY/MoM frequency validation ---

def test_yoy_rejects_non_monthly_data() -> None:
    """YoY raises WorkbenchError on quarterly data."""
    df = pl.DataFrame({
        "REF_DATE": ["2020-01-01", "2020-04-01", "2020-07-01", "2020-10-01",
                     "2021-01-01", "2021-04-01", "2021-07-01", "2021-10-01"],
        "GEO": ["Canada"] * 8,
        "VALUE": [100.0] * 8,
    })
    df = df.with_columns(pl.col("REF_DATE").str.to_date())

    with pytest.raises(WorkbenchError, match="NON_MONTHLY_DATA|not.*monthly"):
        calc_yoy_change(df)


def test_mom_rejects_annual_data() -> None:
    """MoM raises WorkbenchError on annual data."""
    df = pl.DataFrame({
        "REF_DATE": ["2019-01-01", "2020-01-01", "2021-01-01", "2022-01-01"],
        "GEO": ["Canada"] * 4,
        "VALUE": [100.0, 110.0, 120.0, 130.0],
    })
    df = df.with_columns(pl.col("REF_DATE").str.to_date())

    with pytest.raises(WorkbenchError, match="NON_MONTHLY_DATA|not.*monthly"):
        calc_mom_change(df)


# --- merge_cubes validation ---

def test_merge_rejects_invalid_how() -> None:
    """merge_cubes raises WorkbenchError on invalid join type."""
    df = pl.DataFrame({"REF_DATE": ["2024-01"], "GEO": ["Canada"], "V": [1]})
    with pytest.raises(WorkbenchError, match="INVALID_JOIN_TYPE|Invalid join"):
        merge_cubes([df, df], merge_keys=["REF_DATE", "GEO"], how="banana")


def test_merge_suffix_indexing() -> None:
    """First suffix applies to first right DataFrame."""
    df1 = pl.DataFrame({"REF_DATE": ["2024-01"], "GEO": ["Canada"], "VALUE": [100]})
    df2 = pl.DataFrame({"REF_DATE": ["2024-01"], "GEO": ["Canada"], "VALUE": [200]})
    df3 = pl.DataFrame({"REF_DATE": ["2024-01"], "GEO": ["Canada"], "VALUE": [300]})

    result = merge_cubes(
        [df1, df2, df3],
        merge_keys=["REF_DATE", "GEO"],
        suffixes=["_rent", "_vacancy"],
    )
    assert "VALUE_rent" in result.columns, f"Expected VALUE_rent, got {result.columns}"
    assert "VALUE_vacancy" in result.columns, f"Expected VALUE_vacancy, got {result.columns}"


def test_merge_raises_on_unresolved_column_conflict() -> None:
    """merge_cubes raises WorkbenchError if column conflicts remain after rename."""
    # Create two DataFrames with a column that will conflict
    # even after the suffix rename logic
    df1 = pl.DataFrame({
        "REF_DATE": ["2024-01"],
        "GEO": ["Canada"],
        "VALUE": [100],
        "VALUE_rent": [50],  # This already has the suffix name
    })
    df2 = pl.DataFrame({
        "REF_DATE": ["2024-01"],
        "GEO": ["Canada"],
        "VALUE": [200],
    })

    # With suffix "_rent", df2's VALUE becomes VALUE_rent,
    # but df1 already has VALUE_rent → Polars creates VALUE_rent_right_tmp
    with pytest.raises(WorkbenchError, match="MERGE_COLUMN_CONFLICT|column conflicts"):
        merge_cubes(
            [df1, df2],
            merge_keys=["REF_DATE", "GEO"],
            suffixes=["_rent"],
        )


# --- date parse failure ---

def test_ensure_date_column_fails_on_bad_format() -> None:
    """Unparseable date strings raise WorkbenchError."""
    from src.services.data.workbench import _ensure_date_column
    df = pl.DataFrame({"REF_DATE": ["not-a-date", "also-bad", "nope"]})
    with pytest.raises(WorkbenchError) as exc_info:
        _ensure_date_column(df, "REF_DATE")
    assert exc_info.value.error_code == "DATE_PARSE_FAILED"


# --- filter_geo match modes ---

def test_filter_geo_exact_mode() -> None:
    """Exact match filters precisely."""
    df = pl.DataFrame({
        "GEO": ["Nova Scotia", "Scotia Bank HQ", "Canada"],
        "VALUE": [1, 2, 3],
    })
    result = filter_geo(df, "Nova Scotia", match_mode="exact")
    assert result.height == 1
    assert result["GEO"][0] == "Nova Scotia"


def test_filter_geo_contains_mode() -> None:
    """Contains match finds substrings."""
    df = pl.DataFrame({
        "GEO": ["Nova Scotia", "Scotia Bank HQ", "Canada"],
        "VALUE": [1, 2, 3],
    })
    result = filter_geo(df, "Scotia", match_mode="contains")
    assert result.height == 2


# ---- Missing columns ----

def test_missing_column_raises_workbench_error() -> None:
    """Functions raise WorkbenchError for missing required columns."""
    df = pl.DataFrame({"X": [1], "Y": [2]})
    with pytest.raises(WorkbenchError, match="Missing required columns"):
        filter_geo(df, "Canada")


# ---- R4 compliance ----

def test_no_pandas_import() -> None:
    """workbench.py must NOT import pandas (R4)."""
    # Find the actual file path
    import importlib
    import src.services.data.workbench as wb

    source_file = Path(wb.__file__)
    source = source_file.read_text()
    assert "import pandas" not in source, "FORBIDDEN: pandas import"
    assert "from pandas" not in source, "FORBIDDEN: pandas import"


# ---- Immutability ----

def test_functions_dont_mutate_input() -> None:
    """Original DataFrame is not modified by any function."""
    df = _monthly_df(24)
    original_height = df.height
    original_cols = df.columns.copy()

    _ = filter_geo(df, "Canada")
    _ = calc_yoy_change(df)
    _ = calc_mom_change(df)
    _ = calc_rolling_avg(df, window=3)

    assert df.height == original_height
    assert df.columns == original_cols
