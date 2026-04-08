"""DataFetchService — download, validate, clean and persist StatCan cube data.

Architecture decisions:
    R2  — Heavy parsing under data_sem + run_in_threadpool.
    R3  — Output is Parquet ONLY. No CSV internal storage.
    R4  — Polars-first. NO pandas import. NO legacy normalize_dataset().
    R6  — DB sessions are short-lived. No session during heavy transform.
    R13 — Dynamic periods based on cube frequency.
    R14 — Duplicate key validation before save.

This file is in the POLARS ZONE. The following are FORBIDDEN:
    pandas
    from src.services.statcan.service import normalize_dataset
    df.duplicated()
    df.astype(object)
    df.replace({pd.NA: None})
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from datetime import date, datetime, timezone

import polars as pl
import structlog

from src.core.exceptions import DataSourceError

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Required columns in StatCan CSV response (R14 schema contract)
REQUIRED_COLUMNS: frozenset[str] = frozenset({
    "REF_DATE", "GEO", "VALUE", "SCALAR_ID",
})

# Dynamic periods by frequency (R13)
PERIODS_MAP: dict[str, int] = {
    "Daily": 1000,
    "Monthly": 120,
    "Quarterly": 40,
    "Annual": 20,
}

# S3 key pattern for processed data (R3)
PROCESSED_KEY_TEMPLATE = "statcan/processed/{product_id}/{date}.parquet"
RAW_KEY_TEMPLATE = "statcan/raw/{product_id}/{date}.csv"

# Scalar factor multipliers (StatCan SCALAR_ID values)
SCALAR_FACTOR_MAP: dict[int, float] = {
    0: 1.0,           # units
    1: 10.0,
    2: 100.0,
    3: 1_000.0,       # thousands
    4: 10_000.0,
    5: 100_000.0,
    6: 1_000_000.0,   # millions
    7: 10_000_000.0,
    8: 100_000_000.0,
    9: 1_000_000_000.0,  # billions
}

# Data quality threshold (percentage of null values in VALUE column)
NULL_WARNING_THRESHOLD: float = 20.0


# ---------------------------------------------------------------------------
# Result schema
# ---------------------------------------------------------------------------

@dataclass
class DataQualityReport:
    """Data quality metrics for a fetched cube."""

    total_rows: int
    valid_rows: int
    null_rows: int
    null_percentage: float


@dataclass
class FetchResult:
    """Result of a cube data fetch operation."""

    product_id: str
    rows: int
    columns: int
    storage_key: str
    quality: DataQualityReport


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class DataFetchService:
    """Downloads and processes StatCan cube data vectors.

    Args:
        http_client: StatCanClient or any async HTTP client with
            a method to download CSV data.
        storage: StorageInterface for saving raw CSV and processed Parquet.
        catalog_repo: CubeCatalogRepository for reading cube metadata
            (frequency, for dynamic periods).
    """

    def __init__(
        self,
        http_client: object,
        storage: object,
        catalog_repo: object,
    ) -> None:
        self._http_client = http_client
        self._storage = storage
        self._catalog_repo = catalog_repo

    async def fetch_cube_data(
        self,
        product_id: str,
        periods: int = 120,
        frequency: str = "Monthly",
    ) -> FetchResult:
        """Download, validate, clean, and store cube data.

        Pipeline (R6 — short DB sessions):
            1. Open DB → read cube metadata → close DB (handled by caller)
            2. Download CSV bytes (io_sem in caller)
            3. Parse + clean + validate (data_sem + threadpool in caller)
            4. Save Parquet to storage
            5. Return FetchResult

        Args:
            product_id: StatCan product ID (e.g. "14-10-0127-01").
            periods: Number of distinct reference periods to keep.
            frequency: StatCan reporting frequency (e.g., 'Monthly').

        Returns:
            FetchResult with storage key and quality report.

        Raises:
            DataSourceError: If schema invalid, or download fails.
        """
        log = logger.bind(product_id=product_id)
        today = date.today().isoformat()

        log.info(
            "fetch_started",
            frequency=frequency,
            periods=periods,
        )

        # --- Stage 2: Download CSV bytes ---
        csv_bytes = await self._download_csv(product_id)
        log.info("fetch_downloaded", size_bytes=len(csv_bytes))

        # --- Stage 3: Save raw CSV (for debugging/audit) ---
        raw_key = RAW_KEY_TEMPLATE.format(product_id=product_id, date=today)
        await self._save_raw(raw_key, csv_bytes)

        # --- Stage 4: Parse, clean, validate (CPU-heavy, use threadpool) ---
        df = self._parse_and_clean(csv_bytes, product_id, periods)
        quality = self._assess_quality(df)

        if quality.null_percentage > NULL_WARNING_THRESHOLD:
            log.warning(
                "data_quality_warning",
                null_percentage=round(quality.null_percentage, 1),
                total_rows=quality.total_rows,
            )

        # --- Stage 5: Validate schema contract ---
        self._validate_schema(df, product_id)
        self._validate_duplicates(df, product_id)

        # --- Stage 6: Save as Parquet (R3) ---
        processed_key = PROCESSED_KEY_TEMPLATE.format(
            product_id=product_id, date=today
        )
        await self._save_parquet(processed_key, df)

        log.info(
            "fetch_completed",
            rows=df.height,
            columns=df.width,
            storage_key=processed_key,
            null_pct=round(quality.null_percentage, 1),
        )

        return FetchResult(
            product_id=product_id,
            rows=df.height,
            columns=df.width,
            storage_key=processed_key,
            quality=quality,
        )

    # ------------------------------------------------------------------
    # Internal methods
    # ------------------------------------------------------------------


    async def _download_csv(
        self,
        product_id: str,
    ) -> bytes:
        """Download full table CSV data from StatCan API.

        StatCan CSV is always a full download; the `periods` dynamic
        configuration is used for post-parse truncation, not the download.
        """
        # StatCan full table download URL
        # Format: getFullTableDownloadCSV/{productId}
        url = (
            f"https://www150.statcan.gc.ca/n1/tbl/csv/"
            f"{product_id.replace('-', '')}-eng.zip"
        )

        try:
            if hasattr(self._http_client, "request"):
                response = await self._http_client.request("GET", url)
            elif hasattr(self._http_client, "get"):
                response = await self._http_client.get(url)
            else:
                raise TypeError(f"HTTP client has no get/request method")

            response.raise_for_status()
            return response.content
        except Exception as exc:
            raise DataSourceError(
                message=f"Failed to download data for '{product_id}': {exc}",
                error_code="DOWNLOAD_FAILED",
                context={"product_id": product_id, "url": url},
            ) from exc

    @staticmethod
    def _parse_and_clean(
        csv_bytes: bytes,
        product_id: str,
        periods: int,
    ) -> pl.DataFrame:
        """Parse CSV bytes into a clean Polars DataFrame.

        This is a PURE function (ARCH-PURA-001 compatible).
        No I/O, no DB, no network.

        Steps:
            1. Parse CSV with Polars
            2. Select relevant columns
            3. Cast VALUE to Float64 (coerce errors to null)
            4. Cast SCALAR_ID to Int32
            5. Apply scalar factor normalization
            6. Filter to the latest `periods` reference dates
        """
        try:
            # StatCan CSVs may be inside a ZIP — handle both
            if csv_bytes[:2] == b"PK":
                # ZIP file — extract first CSV
                import zipfile
                with zipfile.ZipFile(io.BytesIO(csv_bytes)) as zf:
                    csv_names = [
                        n for n in zf.namelist()
                        if n.endswith(".csv") and not n.startswith("__MACOSX")
                    ]
                    if not csv_names:
                        raise DataSourceError(
                            message="ZIP contains no CSV files",
                            error_code="DATA_CONTRACT_VIOLATION",
                            context={"product_id": product_id},
                        )
                    csv_bytes = zf.read(csv_names[0])

            df = pl.read_csv(
                io.BytesIO(csv_bytes),
                infer_schema_length=10000,
                ignore_errors=True,
            )
        except pl.exceptions.ComputeError as exc:
            raise DataSourceError(
                message=f"Failed to parse CSV: {exc}",
                error_code="DATA_CONTRACT_VIOLATION",
                context={"product_id": product_id},
            ) from exc

        # Normalize column names (strip whitespace, uppercase)
        df = df.rename({
            col: col.strip().upper().replace('"', '')
            for col in df.columns
        })

        # Cast VALUE to float (coerce non-numeric to null)
        if "VALUE" in df.columns:
            df = df.with_columns(
                pl.col("VALUE").cast(pl.Float64, strict=False)
            )

        # Cast SCALAR_ID to int
        if "SCALAR_ID" in df.columns:
            df = df.with_columns(
                pl.col("SCALAR_ID").cast(pl.Int32, strict=False)
            )

        # Apply scalar factor normalization
        if "VALUE" in df.columns and "SCALAR_ID" in df.columns:
            df = df.with_columns(
                (
                    pl.col("VALUE")
                    * pl.col("SCALAR_ID").map_elements(
                        lambda sid: SCALAR_FACTOR_MAP.get(sid, 1.0)
                            if sid is not None else 1.0,
                        return_dtype=pl.Float64,
                    )
                ).alias("VALUE_SCALED")
            )

        # Truncation strategy (v1):
        # - Takes the N latest DISTINCT REF_DATE values globally across all series
        # - Filters DataFrame to keep only rows matching those dates
        # - This is a global date window, NOT a per-series rolling window
        # - For cubes where different geographies have different date coverage,
        #   some series may have fewer than N periods after truncation
        if "REF_DATE" in df.columns:
            latest_dates = (
                df.select("REF_DATE")
                .unique()
                .sort("REF_DATE", descending=True)
                .head(periods)
            )
            df = df.join(latest_dates, on="REF_DATE", how="inner")

        return df

    @staticmethod
    def _assess_quality(df: pl.DataFrame) -> DataQualityReport:
        """Calculate data quality metrics."""
        total = df.height
        if total == 0:
            return DataQualityReport(0, 0, 0, 0.0)

        null_count = 0
        if "VALUE" in df.columns:
            null_count = df.select(pl.col("VALUE").is_null().sum()).item()

        valid = total - null_count
        pct = (null_count / total * 100) if total > 0 else 0.0

        return DataQualityReport(
            total_rows=total,
            valid_rows=valid,
            null_rows=null_count,
            null_percentage=pct,
        )

    @staticmethod
    def _validate_schema(df: pl.DataFrame, product_id: str) -> None:
        """Validate that required columns exist (data contract)."""
        actual = set(df.columns)
        missing = REQUIRED_COLUMNS - actual

        if missing:
            raise DataSourceError(
                message=(
                    f"StatCan response for '{product_id}' missing columns: "
                    f"{sorted(missing)}. Got: {sorted(actual)}. "
                    f"Data format may have changed."
                ),
                error_code="DATA_CONTRACT_VIOLATION",
                context={
                    "product_id": product_id,
                    "missing": sorted(missing),
                    "actual": sorted(actual),
                },
            )

    @staticmethod
    def _validate_duplicates(
        df: pl.DataFrame,
        product_id: str,
    ) -> None:
        """Check for duplicate rows by key columns (R14)."""
        key_cols = ["REF_DATE", "GEO"]
        available_keys = [k for k in key_cols if k in df.columns]

        if len(available_keys) < 2:
            return  # Not enough key columns to check

        dupes = (
            df.group_by(available_keys)
            .len()
            .filter(pl.col("len") > 1)
        )

        if dupes.height > 0:
            logger.warning(
                "data_duplicate_keys",
                product_id=product_id,
                duplicate_groups=dupes.height,
                sample=dupes.head(5).to_dicts(),
            )
            # WARNING, not error — StatCan data may have legitimate
            # multiple series per (REF_DATE, GEO) with different UOM/VECTOR

    async def _save_raw(self, key: str, data: bytes) -> None:
        """Save raw CSV/ZIP to storage for audit trail."""
        if not self._storage:
            logger.warning('no_storage_configured', key=key)
            return
        if hasattr(self._storage, 'upload_bytes'):
            await self._storage.upload_bytes(data, key)
        else:
            logger.warning('storage_missing_upload_bytes', key=key)

    async def _save_parquet(self, key: str, df: pl.DataFrame) -> None:
        """Save Polars DataFrame as Parquet to storage (R3)."""
        if not self._storage:
            from src.core.exceptions import StorageError
            raise StorageError(message='Storage not configured', error_code='STORAGE_ERROR', context={'key': key})
        buf = io.BytesIO()
        df.write_parquet(buf)
        parquet_bytes = buf.getvalue()

        if hasattr(self._storage, 'upload_bytes'):
            await self._storage.upload_bytes(parquet_bytes, key)
        else:
            from src.core.exceptions import StorageError
            raise StorageError(message='Storage lacks upload_bytes', error_code='STORAGE_ERROR', context={'key': key})
