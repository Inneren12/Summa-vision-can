"""Tests for StatCan storage key parsing."""
from __future__ import annotations

from src.services.statcan.key_parser import (
    extract_product_id_from_storage_key,
)


class TestExtractProductIdFromStorageKey:
    def test_canonical_statcan_path(self) -> None:
        result = extract_product_id_from_storage_key(
            "statcan/processed/18-10-0004-01/2026-04-26.parquet"
        )
        assert result == "18-10-0004-01"

    def test_dotted_product_id(self) -> None:
        # Some StatCan product IDs use dot notation
        result = extract_product_id_from_storage_key(
            "statcan/processed/18.10.0004/2026-04-26.parquet"
        )
        assert result == "18.10.0004"

    def test_temp_upload_path_returns_none(self) -> None:
        # Graphics upload temp files shouldn't match
        assert extract_product_id_from_storage_key(
            "temp/uploads/abc-123-def.parquet"
        ) is None

    def test_transformed_output_path_returns_none(self) -> None:
        # Transform endpoint outputs shouldn't match
        assert extract_product_id_from_storage_key(
            "statcan/transformed/2026-04-26/abc123.parquet"
        ) is None

    def test_empty_string_returns_none(self) -> None:
        assert extract_product_id_from_storage_key("") is None

    def test_missing_date_segment_returns_none(self) -> None:
        # Path without {date}.parquet suffix shouldn't match
        assert extract_product_id_from_storage_key(
            "statcan/processed/18-10-0004-01/"
        ) is None

    def test_non_parquet_extension_returns_none(self) -> None:
        # Only .parquet files match (raw .csv keys exist but aren't preview-able)
        assert extract_product_id_from_storage_key(
            "statcan/processed/18-10-0004-01/2026-04-26.csv"
        ) is None

    def test_extra_path_segments_returns_none(self) -> None:
        # Defense against future path structure changes — strict match
        assert extract_product_id_from_storage_key(
            "statcan/processed/extra/18-10-0004-01/2026-04-26.parquet"
        ) is None

    def test_partial_path_returns_none(self) -> None:
        assert extract_product_id_from_storage_key(
            "processed/18-10-0004-01/2026-04-26.parquet"
        ) is None
