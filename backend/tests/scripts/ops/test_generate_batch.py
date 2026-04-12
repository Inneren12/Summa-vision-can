"""Tests for the batch graphic generation CLI script.

Covers:
* Argument parsing (manifest mode, single-item mode, dry-run)
* Manifest validation
* Entry validation
* Dry-run output (no pipeline execution)
* Error handling for missing files and invalid JSON
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure the scripts package is importable
_backend_dir = Path(__file__).resolve().parent.parent.parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from scripts.ops.generate_batch import (
    _build_parser,
    _parse_entries,
    _run_batch,
    _validate_entry,
    main,
)


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------


class TestBuildParser:
    """Tests for the argparse configuration."""

    def test_parser_accepts_manifest(self) -> None:
        parser = _build_parser()
        args = parser.parse_args(["--manifest", "manifest.json"])
        assert args.manifest == Path("manifest.json")

    def test_parser_accepts_single_item_args(self) -> None:
        parser = _build_parser()
        args = parser.parse_args([
            "--data-key", "data/test.parquet",
            "--chart-type", "bar",
            "--title", "Test Chart",
        ])
        assert args.data_key == "data/test.parquet"
        assert args.chart_type == "bar"
        assert args.title == "Test Chart"

    def test_parser_default_size(self) -> None:
        parser = _build_parser()
        args = parser.parse_args(["--manifest", "m.json"])
        assert args.size == [1080, 1080]

    def test_parser_custom_size(self) -> None:
        parser = _build_parser()
        args = parser.parse_args([
            "--data-key", "test.parquet",
            "--chart-type", "bar",
            "--title", "T",
            "--size", "1200", "900",
        ])
        assert args.size == [1200, 900]

    def test_parser_default_concurrency(self) -> None:
        parser = _build_parser()
        args = parser.parse_args(["--manifest", "m.json"])
        assert args.concurrency == 2

    def test_parser_dry_run_flag(self) -> None:
        parser = _build_parser()
        args = parser.parse_args(["--manifest", "m.json", "--dry-run"])
        assert args.dry_run is True

    def test_parser_rejects_zero_concurrency(self) -> None:
        parser = _build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["--manifest", "m.json", "--concurrency", "0"])

    def test_parser_rejects_negative_concurrency(self) -> None:
        parser = _build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["--manifest", "m.json", "--concurrency", "-1"])


# ---------------------------------------------------------------------------
# Entry validation
# ---------------------------------------------------------------------------


class TestValidateEntry:
    """Tests for _validate_entry."""

    def test_valid_entry_has_no_errors(self) -> None:
        entry = {
            "data_key": "data/test.parquet",
            "chart_type": "bar",
            "title": "Test",
        }
        assert _validate_entry(entry, 0) == []

    def test_missing_data_key(self) -> None:
        entry = {"chart_type": "bar", "title": "Test"}
        errors = _validate_entry(entry, 0)
        assert len(errors) == 1
        assert "data_key" in errors[0]

    def test_missing_multiple_fields(self) -> None:
        errors = _validate_entry({}, 0)
        assert len(errors) == 3  # data_key, chart_type, title

    def test_invalid_size_format(self) -> None:
        entry = {
            "data_key": "test.parquet",
            "chart_type": "bar",
            "title": "Test",
            "size": [1080],  # missing height
        }
        errors = _validate_entry(entry, 0)
        assert len(errors) == 1
        assert "size" in errors[0]


# ---------------------------------------------------------------------------
# _parse_entries
# ---------------------------------------------------------------------------


class TestParseEntries:
    """Tests for _parse_entries."""

    def test_parse_manifest_file(self, tmp_path: Path) -> None:
        manifest = tmp_path / "manifest.json"
        entries = [
            {"data_key": "a.parquet", "chart_type": "bar", "title": "A", "category": "housing"},
            {"data_key": "b.parquet", "chart_type": "line", "title": "B", "category": "housing"},
        ]
        manifest.write_text(json.dumps(entries))

        parser = _build_parser()
        args = parser.parse_args(["--manifest", str(manifest)])
        result = _parse_entries(args)
        assert len(result) == 2
        assert result[0]["data_key"] == "a.parquet"

    def test_parse_single_item(self) -> None:
        parser = _build_parser()
        args = parser.parse_args([
            "--data-key", "data/test.parquet",
            "--chart-type", "bar",
            "--title", "Test",
            "--category", "housing",
            "--source-product-id", "14-10-0127",
        ])
        result = _parse_entries(args)
        assert len(result) == 1
        assert result[0]["data_key"] == "data/test.parquet"
        assert result[0]["source_product_id"] == "14-10-0127"

    def test_parse_exits_when_manifest_not_found(self) -> None:
        parser = _build_parser()
        args = parser.parse_args(["--manifest", "/nonexistent/path.json"])
        with pytest.raises(SystemExit):
            _parse_entries(args)

    def test_parse_exits_when_no_data_key(self) -> None:
        parser = _build_parser()
        args = parser.parse_args(["--chart-type", "bar", "--title", "T"])
        # data_key will be None, which triggers sys.exit
        with pytest.raises(SystemExit):
            _parse_entries(args)


# ---------------------------------------------------------------------------
# main() — dry-run mode
# ---------------------------------------------------------------------------


class TestMainDryRun:
    """Tests for main() in dry-run mode."""

    def test_dry_run_does_not_execute_pipeline(self, tmp_path: Path) -> None:
        manifest = tmp_path / "manifest.json"
        entries = [
            {"data_key": "a.parquet", "chart_type": "bar", "title": "A", "category": "housing"},
        ]
        manifest.write_text(json.dumps(entries))

        exit_code = main(["--manifest", str(manifest), "--dry-run"])
        assert exit_code == 0

    def test_dry_run_with_invalid_entries_returns_error(self, tmp_path: Path) -> None:
        manifest = tmp_path / "manifest.json"
        entries = [{"title": "incomplete"}]  # missing data_key, chart_type
        manifest.write_text(json.dumps(entries))

        exit_code = main(["--manifest", str(manifest), "--dry-run"])
        assert exit_code == 1


# ---------------------------------------------------------------------------
# main() — batch execution (mocked pipeline)
# ---------------------------------------------------------------------------


class TestMainExecution:
    """Tests for main() with mocked pipeline execution."""

    def test_successful_batch(self, tmp_path: Path) -> None:
        manifest = tmp_path / "manifest.json"
        entries = [
            {"data_key": "a.parquet", "chart_type": "bar", "title": "A", "category": "housing"},
        ]
        manifest.write_text(json.dumps(entries))

        mock_result = MagicMock()
        mock_result.publication_id = 42
        mock_result.version = 1
        mock_result.model_dump.return_value = {
            "publication_id": 42,
            "cdn_url_lowres": "http://cdn/test",
            "s3_key_highres": "test/highres.png",
            "version": 1,
        }

        mock_pipeline_instance = AsyncMock()
        mock_pipeline_instance.generate.return_value = mock_result

        with (
            patch("src.core.config.get_settings", return_value=MagicMock()),
            patch("src.core.database.get_session_factory", return_value=MagicMock()),
            patch("src.core.storage.get_storage_manager", return_value=MagicMock()),
            patch("src.services.graphics.pipeline.GraphicPipeline", return_value=mock_pipeline_instance),
            patch("src.core.database.get_engine") as mock_engine,
        ):
            mock_engine.return_value.dispose = AsyncMock()
            exit_code = main(["--manifest", str(manifest)])

        assert exit_code == 0
        mock_pipeline_instance.generate.assert_called_once()

    def test_failed_entry_returns_nonzero(self, tmp_path: Path) -> None:
        manifest = tmp_path / "manifest.json"
        entries = [
            {"data_key": "a.parquet", "chart_type": "bar", "title": "A", "category": "housing"},
        ]
        manifest.write_text(json.dumps(entries))

        mock_pipeline_instance = AsyncMock()
        mock_pipeline_instance.generate.side_effect = RuntimeError("Boom")

        with (
            patch("src.core.config.get_settings", return_value=MagicMock()),
            patch("src.core.database.get_session_factory", return_value=MagicMock()),
            patch("src.core.storage.get_storage_manager", return_value=MagicMock()),
            patch("src.services.graphics.pipeline.GraphicPipeline", return_value=mock_pipeline_instance),
            patch("src.core.database.get_engine") as mock_engine,
        ):
            mock_engine.return_value.dispose = AsyncMock()
            exit_code = main(["--manifest", str(manifest)])

        assert exit_code == 1


# ---------------------------------------------------------------------------
# Concurrency verification
# ---------------------------------------------------------------------------


class TestBatchConcurrency:
    """Tests verifying real concurrent execution in _run_batch."""

    @pytest.mark.asyncio()
    async def test_batch_concurrency_is_real(self) -> None:
        """Verify that batch processing runs items concurrently, not sequentially.

        Setup: 4 items with concurrency=2, each taking 0.5s.
        If sequential: 4 * 0.5s = 2.0s minimum.
        If concurrent (2 at a time): 2 * 0.5s = 1.0s minimum.
        """

        async def mock_generate(**kwargs):
            await asyncio.sleep(0.5)  # simulate 500ms work per item
            result = MagicMock()
            result.publication_id = 1
            result.version = 1
            result.model_dump.return_value = {"publication_id": 1, "version": 1}
            return result

        pipeline = MagicMock()
        pipeline.generate = mock_generate

        entries = [
            {"data_key": f"key-{i}", "chart_type": "bar", "title": f"Title {i}", "category": "housing"}
            for i in range(4)
        ]

        start = asyncio.get_event_loop().time()
        results = await _run_batch(entries, pipeline, concurrency=2)
        elapsed = asyncio.get_event_loop().time() - start

        ok_count = sum(1 for r in results if r["status"] == "ok")
        assert ok_count == 4
        # Concurrent: should complete in ~1.0s, not ~2.0s
        assert elapsed < 1.5, f"Batch took {elapsed:.1f}s — expected <1.5s with concurrency=2"

    @pytest.mark.asyncio()
    async def test_batch_failure_does_not_stop_others(self) -> None:
        """One failing item must not prevent other items from completing."""
        call_count = 0

        async def mock_generate(**kwargs):
            nonlocal call_count
            call_count += 1
            if kwargs.get("data_key") == "key-fail":
                raise RuntimeError("Simulated failure")
            result = MagicMock()
            result.publication_id = 1
            result.version = 1
            result.model_dump.return_value = {"publication_id": 1, "version": 1}
            return result

        pipeline = MagicMock()
        pipeline.generate = mock_generate

        entries = [
            {"data_key": "key-ok-1", "chart_type": "bar", "title": "OK 1", "category": "housing"},
            {"data_key": "key-fail", "chart_type": "bar", "title": "Fail", "category": "housing"},
            {"data_key": "key-ok-2", "chart_type": "bar", "title": "OK 2", "category": "housing"},
        ]

        results = await _run_batch(entries, pipeline, concurrency=2)

        assert call_count == 3  # all items were attempted
        ok_count = sum(1 for r in results if r["status"] == "ok")
        fail_count = sum(1 for r in results if r["status"] == "error")
        assert ok_count == 2
        assert fail_count == 1
