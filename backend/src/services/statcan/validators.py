"""Data-quality validation models for Statistics Canada ETL pipelines.

These lightweight Pydantic models capture quality metrics produced
during data normalisation so that downstream consumers (charts, alerts,
monitoring dashboards) can make informed decisions about trustworthiness.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class DataQualityReport(BaseModel):
    """Summary of data-quality metrics for a normalised StatCan dataset.

    Attributes
    ----------
    total_rows:
        Total number of rows in the ingested CSV.
    valid_rows:
        Rows whose target value column contains a non-NaN numeric value
        **after** ``pd.to_numeric(..., errors='coerce')`` has been applied.
    nan_rows:
        Rows whose target value is ``NaN`` (either originally missing or
        coerced from non-numeric strings such as ``".."``).
    nan_percentage:
        ``nan_rows / total_rows * 100``.  ``0.0`` when ``total_rows`` is 0.
    """

    model_config = ConfigDict(frozen=True)

    total_rows: int
    valid_rows: int
    nan_rows: int
    nan_percentage: float
