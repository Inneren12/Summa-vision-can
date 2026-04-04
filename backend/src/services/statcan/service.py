"""StatCan ETL Service — fetch, validate, and normalise Statistics Canada data.

This module is the **internal service/orchestration layer** of the StatCan
integration.  It sits between the HTTP client (``StatCanClient``) and the API
routers, providing two key capabilities:

1. **Metadata retrieval** — ``fetch_todays_releases`` calls the StatCan WDS
   ``getChangedCubeList`` and ``getCubeMetadata`` endpoints, validates the
   payloads through Pydantic schemas, and returns typed models.
2. **Safe Pandas ETL** — ``normalize_dataset`` ingests a raw CSV string,
   coerces the value column to numeric (turning artefacts like ``".."`` and
   empty strings into ``NaN``), applies the scalar factor, and returns a
   data-quality report alongside the cleaned ``DataFrame``.

Usage::

    service = StatCanETLService(client)
    releases = await service.fetch_todays_releases()
    df, report = service.normalize_dataset(csv_text, scalar_factor_code=3)
"""

from __future__ import annotations

import io
from typing import Final

import pandas as pd
import structlog

from src.services.statcan.client import StatCanClient
from src.services.statcan.schemas import ChangedCubeResponse, CubeMetadataResponse
from src.services.statcan.validators import DataQualityReport

logger: structlog.stdlib.BoundLogger = structlog.get_logger(
    module="statcan.service",
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_HIGH_NAN_THRESHOLD: Final[float] = 50.0
"""Percentage of NaN rows above which a WARNING is emitted."""


class StatCanETLService:
    """Service layer that orchestrates the StatCan HTTP client.

    The service is designed for **dependency injection**: the constructor
    receives a fully-configured :class:`StatCanClient`, making it trivial
    to swap in mocks during unit testing.

    Parameters
    ----------
    client:
        A pre-initialised :class:`StatCanClient` used for all outbound
        HTTP calls.
    """

    __slots__ = ("_client",)

    def __init__(self, client: StatCanClient) -> None:
        self._client: StatCanClient = client

    # ------------------------------------------------------------------
    # Metadata retrieval
    # ------------------------------------------------------------------

    async def fetch_todays_releases(self) -> list[CubeMetadataResponse]:
        """Fetch today's released cubes and return their validated metadata.

        Calls the StatCan ``getChangedCubeList`` endpoint, then issues a
        batch ``getCubeMetadata`` request for every returned product ID.
        Only entries with ``status == "SUCCESS"`` are included in the
        result.

        Returns
        -------
        list[CubeMetadataResponse]
            Zero or more validated metadata envelopes.
        """
        # 1. Retrieve the list of cubes that changed today.
        res = await self._client.get(
            "https://www150.statcan.gc.ca/t1/wds/rest/getChangedCubeList",
        )
        res.raise_for_status()

        data = res.json()
        changed_cubes = [ChangedCubeResponse.model_validate(item) for item in data]

        if not changed_cubes:
            return []

        # 2. Fetch metadata for the changed cubes in a single batch call.
        payload = [{"productId": cube.product_id} for cube in changed_cubes]
        meta_res = await self._client.request(
            "POST",
            "https://www150.statcan.gc.ca/t1/wds/rest/getCubeMetadata",
            json=payload,
        )
        meta_res.raise_for_status()

        meta_data = meta_res.json()
        metadata_responses: list[CubeMetadataResponse] = []
        for item in meta_data:
            if item.get("status") == "SUCCESS" and "object" in item:
                metadata_responses.append(
                    CubeMetadataResponse.model_validate(item["object"]),
                )

        return metadata_responses

    # ------------------------------------------------------------------
    # Safe Pandas ETL
    # ------------------------------------------------------------------

    def normalize_dataset(
        self,
        raw_csv_content: str,
        scalar_factor_code: int | None,
    ) -> tuple[pd.DataFrame, DataQualityReport]:
        """Normalise a raw StatCan CSV by coercing values and scaling.

        Processing steps
        ~~~~~~~~~~~~~~~~
        1. Default *scalar_factor_code* to ``0`` when ``None``.
        2. Read the CSV into a ``DataFrame``.
        3. Locate the target column (``VALUE`` or ``value``).
        4. Force the column to numeric with ``pd.to_numeric(...,
           errors='coerce')`` — this turns non-numeric artefacts
           (``".."``, empty strings, etc.) into ``NaN``.
        5. Multiply by ``10 ** scalar_factor_code``.
        6. Compute NaN metrics and build a :class:`DataQualityReport`.
        7. If ``nan_percentage > 50 %``, emit a ``WARNING`` log.

        Parameters
        ----------
        raw_csv_content:
            A string containing the full CSV payload.
        scalar_factor_code:
            Power-of-ten multiplier. ``None`` is treated as ``0``
            (i.e. no scaling).

        Returns
        -------
        tuple[pd.DataFrame, DataQualityReport]
            The cleaned ``DataFrame`` and the corresponding quality report.
        """
        # 1. Default scalar_factor_code to 0 if None.
        if scalar_factor_code is None:
            scalar_factor_code = 0

        # 2. Read raw CSV into DataFrame.
        df: pd.DataFrame = pd.read_csv(io.StringIO(raw_csv_content))

        # 3. Identify the target value column.
        value_col: str | None = None
        if "VALUE" in df.columns:
            value_col = "VALUE"
        elif "value" in df.columns:
            value_col = "value"

        if value_col is not None:
            # 4. CRITICAL: coerce to numeric BEFORE any math.
            df[value_col] = pd.to_numeric(df[value_col], errors="coerce")

            # 5. Apply scalar factor.
            multiplier: int = 10**scalar_factor_code
            df[value_col] = df[value_col] * multiplier

        # 6. Calculate NaN metrics.
        total_rows: int = len(df)
        if value_col is not None:
            nan_rows: int = int(df[value_col].isna().sum())
        else:
            nan_rows = 0

        valid_rows: int = total_rows - nan_rows
        nan_percentage: float = (
            (nan_rows / total_rows * 100.0) if total_rows > 0 else 0.0
        )

        report = DataQualityReport(
            total_rows=total_rows,
            valid_rows=valid_rows,
            nan_rows=nan_rows,
            nan_percentage=nan_percentage,
        )

        # 7. Warn when data quality is poor.
        if nan_percentage > _HIGH_NAN_THRESHOLD:
            logger.warning(
                "High NaN percentage detected in dataset",
                nan_percentage=nan_percentage,
                nan_rows=nan_rows,
                total_rows=total_rows,
            )

        return df, report
