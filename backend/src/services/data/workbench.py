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

    groups_to_sort = [period_col] + (group_cols or [])
    result = working.group_by(groups).agg(agg_expr).sort(groups_to_sort)

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
    match_mode: str = "contains",
) -> pl.DataFrame:
    """Filter DataFrame by geography.

    Args:
        df: Input DataFrame.
        geography: Geography name to filter.
        geo_col: Column name containing geography.
        match_mode: 'exact' for exact case-insensitive match,
                    'contains' for substring match (default).

    Returns:
        New filtered DataFrame.
    """
    _validate_columns(df, [geo_col])

    if match_mode == "exact":
        return df.filter(
            pl.col(geo_col).str.to_lowercase() == geography.lower()
        )
    elif match_mode == "contains":
        return df.filter(
            pl.col(geo_col).str.to_lowercase().str.contains(geography.lower())
        )
    else:
        raise WorkbenchError(
            message=f"Invalid match_mode: {match_mode!r}. Must be 'exact' or 'contains'.",
            error_code="INVALID_MATCH_MODE",
            context={"match_mode": match_mode},
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

    IMPORTANT: Assumes continuous monthly series with no gaps.
    For quarterly or annual data, or series with missing months,
    results will be incorrect. Use only on validated monthly data.

    Args:
        df: Input DataFrame sorted by date.
        value_col: Column with numeric values.
        date_col: Date column for ordering.
        group_cols: Group by these before calculating (e.g. ``["GEO"]``).
        output_col: Name for the result column.

    Returns:
        DataFrame with added YoY change column.

    Raises:
        WorkbenchError: If data does not appear to be continuous monthly.
    """
    _validate_columns(df, [value_col, date_col])

    working = _ensure_date_column(df, date_col).sort(date_col)

    geo_col = group_cols[0] if group_cols else "GEO"
    if geo_col in working.columns:
        _validate_monthly_continuity(working, date_col, geo_col)

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

    IMPORTANT: Assumes continuous monthly series with no gaps.

    Raises:
        WorkbenchError: If data does not appear to be continuous monthly.
    """
    _validate_columns(df, [value_col, date_col])

    working = _ensure_date_column(df, date_col).sort(date_col)

    geo_col = group_cols[0] if group_cols else "GEO"
    if geo_col in working.columns:
        _validate_monthly_continuity(working, date_col, geo_col)

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


def _validate_monthly_continuity(
    df: pl.DataFrame,
    date_col: str,
    geo_col: str,
) -> None:
    """Check that data looks like continuous monthly series.

    Validates by checking the most common interval between dates
    within each geography. If it's not ~28-31 days, raises error.
    """
    if df.height < 3:
        return  # Too few rows to validate

    # Sample the first geography
    geos = df.select(geo_col).unique()
    if geos.height == 0:
        return

    first_geo = geos[0, 0]
    subset = (
        df.filter(pl.col(geo_col) == first_geo)
        .sort(date_col)
        .select(date_col)
    )

    if subset.height < 3:
        return

    # Check interval between consecutive dates
    diffs = subset.with_columns(
        pl.col(date_col).diff().dt.total_days().alias("_diff_days")
    ).drop_nulls("_diff_days")

    if diffs.height == 0:
        return

    median_diff = diffs.select(pl.col("_diff_days").median()).item()

    # Monthly data should have ~28-31 day intervals
    if median_diff < 20 or median_diff > 45:
        raise WorkbenchError(
            message=(
                f"Data does not appear to be monthly series. "
                f"Median interval between dates is {median_diff:.0f} days. "
                f"YoY/MoM calculations require continuous monthly data."
            ),
            error_code="NON_MONTHLY_DATA",
            context={
                "median_interval_days": float(median_diff),
                "geo_sample": first_geo,
            },
        )


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

_VALID_JOIN_TYPES = {"inner", "left", "outer", "cross", "full"}

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
    if how not in _VALID_JOIN_TYPES:
        raise WorkbenchError(
            message=f"Invalid join type: {how!r}. Must be one of: {sorted(_VALID_JOIN_TYPES)}",
            error_code="INVALID_JOIN_TYPE",
            context={"how": how},
        )

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
    for i, right_df in enumerate(dfs[1:]):
        suffix = suffixes[i] if suffixes and i < len(suffixes) else f"_{i + 1}"

        # Rename conflicting columns in right_df
        conflicting = [c for c in right_df.columns if c not in merge_keys and c in result.columns]
        rename_map = {c: f"{c}{suffix}" for c in conflicting}
        right_renamed = right_df.rename(rename_map)

        # Determine correct full join parameter
        join_type = "full" if how == "outer" else how

        # coalesce=True handles merge_keys properly in full joins avoiding key duplication
        result = result.join(
            right_renamed,
            on=merge_keys,
            how=join_type,  # type: ignore[arg-type]
            coalesce=True,
            suffix="_right_tmp" # temporary suffix for any unforeseen duplicate names not handled manually
        )

        # Clean up any leftover temporary suffixes if they sneaked in
        tmp_cols = [c for c in result.columns if c.endswith("_right_tmp")]
        if tmp_cols:
            raise WorkbenchError(
                message=(
                    f"Unexpected column conflicts after merge: {tmp_cols}. "
                    f"This means the rename logic did not fully resolve all "
                    f"conflicting column names before the join."
                ),
                error_code="MERGE_COLUMN_CONFLICT",
                context={"conflicting_columns": tmp_cols, "merge_keys": merge_keys},
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
    """Ensure date column is Date type. Parse from string if needed.

    Raises:
        WorkbenchError: If parsing fails (all nulls after parse) or type unsupported.
    """
    if date_col not in df.columns:
        raise WorkbenchError(
            message=f"Column '{date_col}' not found in DataFrame",
            error_code="MISSING_COLUMN",
            context={"date_col": date_col, "columns": df.columns},
        )

    col_dtype = df[date_col].dtype

    if col_dtype == pl.Date or col_dtype == pl.Datetime:
        return df

    if col_dtype == pl.Utf8 or col_dtype == pl.String:
        # Count non-null values before parse
        non_null_before = df.select(pl.col(date_col).is_not_null().sum()).item()

        parsed = df.with_columns(
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

        # Check if parse produced all nulls from non-null input
        non_null_after = parsed.select(pl.col(date_col).is_not_null().sum()).item()

        if non_null_before > 0 and non_null_after == 0:
            raise WorkbenchError(
                message=(
                    f"Date column '{date_col}' could not be parsed. "
                    f"All {non_null_before} non-null values became null after parsing."
                ),
                error_code="DATE_PARSE_FAILED",
                context={"date_col": date_col, "sample": df[date_col].head(5).to_list()},
            )

        return parsed

    raise WorkbenchError(
        message=f"Column '{date_col}' has unsupported type {col_dtype} for date operations",
        error_code="INVALID_DATE_TYPE",
        context={"date_col": date_col, "dtype": str(col_dtype)},
    )


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
