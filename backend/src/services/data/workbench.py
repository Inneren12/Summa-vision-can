"""DataWorkbench — pure Polars transformations for StatCan data.

Architecture rules:
    ARCH-PURA-001 — ALL functions are pure. No I/O, no DB, no HTTP.
    R4  — Polars-only. NO pandas import.
    R14 — merge_cubes validates key uniqueness before joining.

Every function:
    - Takes Polars DataFrame(s) as input
    - Returns a NEW DataFrame (never mutates input)
    - Raises WorkbenchError on invalid input

This file is in the POLARS ZONE.
"""

from __future__ import annotations

from datetime import date

import polars as pl
import structlog

# Import WorkbenchError from wherever exceptions live in this project:
from src.core.exceptions import WorkbenchError

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Time aggregation
# ---------------------------------------------------------------------------

def aggregate_time(
    df: pl.DataFrame,
    freq: str,
    method: str = "mean",
    date_col: str = "REF_DATE",
    value_col: str = "VALUE",
    group_cols: list[str] | None = None,
) -> pl.DataFrame:
    """Aggregate time series to a coarser frequency.

    Args:
        df: Input DataFrame with a date/period column.
        freq: Target frequency — ``"M"`` (monthly), ``"Q"`` (quarterly),
            ``"Y"`` (yearly).
        method: Aggregation method — ``"mean"``, ``"sum"``, ``"first"``,
            ``"last"``, ``"min"``, ``"max"``.
        date_col: Name of the date column.
        value_col: Name of the value column to aggregate.
        group_cols: Additional grouping columns (e.g. ``["GEO"]``).
            If None, groups by date only.

    Returns:
        New DataFrame with aggregated values.

    Raises:
        WorkbenchError: If date_col or value_col not found, or invalid freq/method.
    """
    _validate_columns(df, [date_col, value_col])

    # Parse date column to proper date type if it's string
    working = _ensure_date_column(df, date_col)

    # Build truncation expression
    trunc_map = {
        "M": "1mo",
        "Q": "1q",
        "Y": "1y",
        "monthly": "1mo",
        "quarterly": "1q",
        "yearly": "1y",
        "annual": "1y",
    }
    interval = trunc_map.get(freq) or trunc_map.get(freq.lower())
    if interval is None:
        raise WorkbenchError(
            f"Invalid frequency: '{freq}'. Must be one of: M, Q, Y",
            context={"freq": freq},
        )

    # Truncate date to target period
    period_col = "__period__"
    working = working.with_columns(
        pl.col(date_col).dt.truncate(interval).alias(period_col)
    )

    # Build group-by columns
    groups = [period_col]
    if group_cols:
        _validate_columns(df, group_cols)
        groups.extend(group_cols)

    # Apply aggregation
    agg_map = {
        "mean": pl.col(value_col).mean(),
        "sum": pl.col(value_col).sum(),
        "first": pl.col(value_col).first(),
        "last": pl.col(value_col).last(),
        "min": pl.col(value_col).min(),
        "max": pl.col(value_col).max(),
    }
    agg_expr = agg_map.get(method)
    if agg_expr is None:
        raise WorkbenchError(
            f"Invalid method: '{method}'. Must be one of: {list(agg_map.keys())}",
            context={"method": method},
        )

    result = working.group_by(groups).agg(agg_expr).sort(period_col)

    # Rename period column back to original date column name
    result = result.rename({period_col: date_col})

    return result


# ---------------------------------------------------------------------------
# Geographic filtering
# ---------------------------------------------------------------------------

def filter_geo(
    df: pl.DataFrame,
    geography: str,
    geo_col: str = "GEO",
) -> pl.DataFrame:
    """Filter DataFrame to a specific geography.

    Args:
        df: Input DataFrame.
        geography: Geography value to keep (e.g. ``"Alberta"``).
            Case-insensitive contains match.
        geo_col: Name of the geography column.

    Returns:
        New filtered DataFrame.
    """
    _validate_columns(df, [geo_col])

    return df.filter(
        pl.col(geo_col).str.to_lowercase().str.contains(
            geography.lower()
        )
    )


# ---------------------------------------------------------------------------
# Date range filtering
# ---------------------------------------------------------------------------

def filter_date_range(
    df: pl.DataFrame,
    start: date | str | None = None,
    end: date | str | None = None,
    date_col: str = "REF_DATE",
) -> pl.DataFrame:
    """Filter DataFrame to a date range.

    Args:
        df: Input DataFrame.
        start: Inclusive start date (None = no lower bound).
        end: Inclusive end date (None = no upper bound).
        date_col: Name of the date column.

    Returns:
        New filtered DataFrame.
    """
    _validate_columns(df, [date_col])

    working = _ensure_date_column(df, date_col)

    if start is not None:
        start_dt = _parse_date(start)
        working = working.filter(pl.col(date_col) >= start_dt)

    if end is not None:
        end_dt = _parse_date(end)
        working = working.filter(pl.col(date_col) <= end_dt)

    return working


# ---------------------------------------------------------------------------
# Derived metrics
# ---------------------------------------------------------------------------

def calc_yoy_change(
    df: pl.DataFrame,
    value_col: str = "VALUE",
    date_col: str = "REF_DATE",
    group_cols: list[str] | None = None,
    output_col: str = "YOY_CHANGE_PCT",
) -> pl.DataFrame:
    """Calculate Year-over-Year percentage change.

    Args:
        df: Input DataFrame sorted by date.
        value_col: Column with numeric values.
        date_col: Date column for ordering.
        group_cols: Group by these before calculating (e.g. ``["GEO"]``).
        output_col: Name for the result column.

    Returns:
        DataFrame with added YoY change column.
    """
    _validate_columns(df, [value_col, date_col])

    working = _ensure_date_column(df, date_col).sort(date_col)

    if group_cols:
        _validate_columns(df, group_cols)
        result = working.with_columns(
            ((pl.col(value_col) / pl.col(value_col).shift(12).over(group_cols)) - 1.0)
            .mul(100.0)
            .alias(output_col)
        )
    else:
        result = working.with_columns(
            ((pl.col(value_col) / pl.col(value_col).shift(12)) - 1.0)
            .mul(100.0)
            .alias(output_col)
        )

    return result


def calc_mom_change(
    df: pl.DataFrame,
    value_col: str = "VALUE",
    date_col: str = "REF_DATE",
    group_cols: list[str] | None = None,
    output_col: str = "MOM_CHANGE_PCT",
) -> pl.DataFrame:
    """Calculate Month-over-Month percentage change.

    Same as YoY but with shift(1) instead of shift(12).
    """
    _validate_columns(df, [value_col, date_col])

    working = _ensure_date_column(df, date_col).sort(date_col)

    if group_cols:
        _validate_columns(df, group_cols)
        result = working.with_columns(
            ((pl.col(value_col) / pl.col(value_col).shift(1).over(group_cols)) - 1.0)
            .mul(100.0)
            .alias(output_col)
        )
    else:
        result = working.with_columns(
            ((pl.col(value_col) / pl.col(value_col).shift(1)) - 1.0)
            .mul(100.0)
            .alias(output_col)
        )

    return result


def calc_rolling_avg(
    df: pl.DataFrame,
    value_col: str = "VALUE",
    window: int = 12,
    date_col: str = "REF_DATE",
    group_cols: list[str] | None = None,
    output_col: str = "ROLLING_AVG",
) -> pl.DataFrame:
    """Calculate rolling average.

    Args:
        df: Input DataFrame.
        value_col: Column with numeric values.
        window: Rolling window size (default 12 = 12-month moving avg).
        date_col: Date column for ordering.
        group_cols: Group by these before calculating.
        output_col: Name for the result column.

    Returns:
        DataFrame with added rolling average column.
    """
    _validate_columns(df, [value_col, date_col])

    if window < 1:
        raise WorkbenchError(
            f"Rolling window must be >= 1, got {window}",
            context={"window": window},
        )

    working = _ensure_date_column(df, date_col).sort(date_col)

    if group_cols:
        _validate_columns(df, group_cols)
        result = working.with_columns(
            pl.col(value_col)
            .rolling_mean(window_size=window)
            .over(group_cols)
            .alias(output_col)
        )
    else:
        result = working.with_columns(
            pl.col(value_col)
            .rolling_mean(window_size=window)
            .alias(output_col)
        )

    return result


# ---------------------------------------------------------------------------
# Multi-cube merge
# ---------------------------------------------------------------------------

def merge_cubes(
    dfs: list[pl.DataFrame],
    merge_keys: list[str] | None = None,
    how: str = "outer",
    suffixes: list[str] | None = None,
) -> pl.DataFrame:
    """Merge multiple cube DataFrames on common keys (R14).

    Args:
        dfs: List of DataFrames to merge (minimum 2).
        merge_keys: Columns to join on. REQUIRED. Default
            ``["REF_DATE", "GEO"]``.
        how: Join type — ``"outer"``, ``"inner"``, ``"left"``.
        suffixes: Optional suffixes for disambiguating value columns.
            If None, uses ``"_1"``, ``"_2"``, etc.

    Returns:
        Merged DataFrame.

    Raises:
        WorkbenchError: If fewer than 2 DataFrames, missing keys,
            or duplicate keys found in any input.
    """
    if merge_keys is None:
        merge_keys = ["REF_DATE", "GEO"]

    if len(dfs) < 2:
        raise WorkbenchError(
            "merge_cubes requires at least 2 DataFrames",
            context={"count": len(dfs)},
        )

    # Validate all keys exist in all DataFrames
    for i, df in enumerate(dfs):
        missing = set(merge_keys) - set(df.columns)
        if missing:
            raise WorkbenchError(
                f"DataFrame {i} missing merge keys: {sorted(missing)}",
                context={"index": i, "missing": sorted(missing), "available": df.columns},
            )

    # Validate key uniqueness in each DataFrame (R14)
    for i, df in enumerate(dfs):
        dupes = (
            df.group_by(merge_keys)
            .len()
            .filter(pl.col("len") > 1)
        )
        if dupes.height > 0:
            raise WorkbenchError(
                f"DataFrame {i} has duplicate merge keys. "
                f"Found {dupes.height} duplicate groups. "
                f"Merge would produce a Cartesian explosion.",
                context={
                    "index": i,
                    "duplicate_groups": dupes.height,
                    "sample": dupes.head(3).to_dicts(),
                },
            )

    # Sequential merge
    result = dfs[0]
    for i, right in enumerate(dfs[1:], start=1):
        suffix = (suffixes[i] if suffixes and i < len(suffixes)
                  else f"_{i}")

        # Determine correct full join parameter
        join_type = "full" if how == "outer" else how
        result = result.join(
            right,
            on=merge_keys,
            how=join_type,  # type: ignore[arg-type]
            suffix=suffix,
        )

    # Warn if result is suspiciously large
    largest_input = max(df.height for df in dfs)
    if result.height > largest_input * 10:
        logger.warning(
            "merge_result_large",
            result_rows=result.height,
            largest_input_rows=largest_input,
            ratio=round(result.height / largest_input, 1),
        )

    return result


# ---------------------------------------------------------------------------
# Helpers (internal)
# ---------------------------------------------------------------------------

def _validate_columns(df: pl.DataFrame, required: list[str]) -> None:
    """Raise WorkbenchError if any required column is missing."""
    actual = set(df.columns)
    missing = set(required) - actual
    if missing:
        raise WorkbenchError(
            f"Missing required columns: {sorted(missing)}",
            context={"missing": sorted(missing), "available": sorted(actual)},
        )


def _ensure_date_column(
    df: pl.DataFrame,
    date_col: str,
) -> pl.DataFrame:
    """Cast date column to Date type if it's a string.

    Handles StatCan date formats: "2024-01", "2024-01-01", "2024".
    """
    if df[date_col].dtype == pl.Utf8 or df[date_col].dtype == pl.String:
        return df.with_columns(
            pl.col(date_col)
            .str.strptime(pl.Date, "%Y-%m-%d", strict=False)
            .fill_null(
                pl.col(date_col)
                .str.strptime(pl.Date, "%Y-%m", strict=False)
            )
            .fill_null(
                pl.col(date_col)
                .str.strptime(pl.Date, "%Y", strict=False)
            )
            .alias(date_col)
        )
    return df


def _parse_date(d: date | str) -> date:
    """Parse a date from string or pass through date object."""
    if isinstance(d, date):
        return d
    # Try common formats
    from datetime import datetime as dt
    for fmt in ("%Y-%m-%d", "%Y-%m", "%Y"):
        try:
            return dt.strptime(d, fmt).date()
        except ValueError:
            continue
    raise WorkbenchError(
        f"Cannot parse date: '{d}'",
        context={"value": d},
    )
