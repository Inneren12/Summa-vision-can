"""Unit tests for temp payload key extraction helpers."""

from src.services.storage.temp_payload_inspector import extract_graphics_generate_data_key


def test_extracts_key_from_valid_graphics_payload() -> None:
    payload = {
        "schema_version": 1,
        "data_key": "temp/uploads/abc123.parquet",
        "chart_type": "line",
    }

    assert extract_graphics_generate_data_key(payload) == "temp/uploads/abc123.parquet"


def test_returns_none_when_key_missing() -> None:
    assert extract_graphics_generate_data_key({"schema_version": 1}) is None


def test_returns_none_for_malformed_payload() -> None:
    assert extract_graphics_generate_data_key(None) is None
    assert extract_graphics_generate_data_key([]) is None
    assert extract_graphics_generate_data_key(123) is None


def test_handles_json_string_payload() -> None:
    payload = '{"schema_version":1,"data_key":"temp/uploads/z.parquet"}'

    assert extract_graphics_generate_data_key(payload) == "temp/uploads/z.parquet"
    assert extract_graphics_generate_data_key('{"schema_version":1') is None
