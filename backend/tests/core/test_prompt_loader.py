"""Tests for PromptLoader (PR-15).

Uses ``tmp_path`` pytest fixture for isolated YAML files — no real
file I/O to the production prompts directory in unit tests.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.core.exceptions import ValidationError
from src.core.prompt_loader import PromptLoader


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_yaml(directory: Path, name: str, content: str) -> Path:
    """Write *content* to ``{directory}/{name}.yaml`` and return the path."""
    filepath = directory / f"{name}.yaml"
    filepath.write_text(content, encoding="utf-8")
    return filepath


VALID_YAML = """\
version: "1.0"
system_prompt: |
  You are a helpful assistant.
  Dataset title: {dataset_title}
  Reference date: {reference_date}
"""

YAML_MISSING_KEY = """\
version: "1.0"
description: "No system_prompt key here."
"""

YAML_EMPTY_PROMPT = """\
version: "1.0"
system_prompt: ""
"""

YAML_NOT_A_MAPPING = """\
- item_one
- item_two
"""

YAML_MALFORMED = """\
version: "1.0"
system_prompt: |
  Unclosed string: {
  key: [missing bracket
"""


# ---------------------------------------------------------------------------
# PromptLoader.load()
# ---------------------------------------------------------------------------


class TestPromptLoaderLoad:
    """Tests for the ``load()`` method."""

    def test_load_valid_yaml(self, tmp_path: Path) -> None:
        """Valid YAML file should return the system_prompt string."""
        _write_yaml(tmp_path, "test_prompt", VALID_YAML)
        loader = PromptLoader(tmp_path)
        result = loader.load("test_prompt")
        assert "You are a helpful assistant." in result
        assert "{dataset_title}" in result  # un-rendered template var

    def test_load_returns_non_empty_string(self, tmp_path: Path) -> None:
        """The returned string should be non-empty."""
        _write_yaml(tmp_path, "test_prompt", VALID_YAML)
        loader = PromptLoader(tmp_path)
        result = loader.load("test_prompt")
        assert isinstance(result, str)
        assert len(result.strip()) > 0

    def test_missing_file_raises_validation_error(self, tmp_path: Path) -> None:
        """A missing YAML file should raise ValidationError."""
        loader = PromptLoader(tmp_path)
        with pytest.raises(ValidationError) as exc_info:
            loader.load("nonexistent")
        assert exc_info.value.error_code == "PROMPT_NOT_FOUND"

    def test_missing_system_prompt_key_raises(self, tmp_path: Path) -> None:
        """YAML without 'system_prompt' key should raise ValidationError."""
        _write_yaml(tmp_path, "bad_prompt", YAML_MISSING_KEY)
        loader = PromptLoader(tmp_path)
        with pytest.raises(ValidationError) as exc_info:
            loader.load("bad_prompt")
        assert exc_info.value.error_code == "PROMPT_MISSING_KEY"

    def test_empty_system_prompt_raises(self, tmp_path: Path) -> None:
        """An empty system_prompt value should raise ValidationError."""
        _write_yaml(tmp_path, "empty_prompt", YAML_EMPTY_PROMPT)
        loader = PromptLoader(tmp_path)
        with pytest.raises(ValidationError) as exc_info:
            loader.load("empty_prompt")
        assert exc_info.value.error_code == "PROMPT_EMPTY"

    def test_yaml_not_a_mapping_raises(self, tmp_path: Path) -> None:
        """A YAML file that parses to a list should raise ValidationError."""
        _write_yaml(tmp_path, "list_yaml", YAML_NOT_A_MAPPING)
        loader = PromptLoader(tmp_path)
        with pytest.raises(ValidationError) as exc_info:
            loader.load("list_yaml")
        assert exc_info.value.error_code == "PROMPT_YAML_ERROR"

    def test_malformed_yaml_raises(self, tmp_path: Path) -> None:
        """Truly malformed YAML should raise ValidationError with PROMPT_YAML_ERROR."""
        # Duplicate keys with invalid indentation → triggers yaml.YAMLError
        malformed = "key: value\n\tindented_with_tab: illegal"
        _write_yaml(tmp_path, "malformed", malformed)
        loader = PromptLoader(tmp_path)
        with pytest.raises(ValidationError) as exc_info:
            loader.load("malformed")
        assert exc_info.value.error_code == "PROMPT_YAML_ERROR"


# ---------------------------------------------------------------------------
# PromptLoader.render()
# ---------------------------------------------------------------------------


class TestPromptLoaderRender:
    """Tests for the ``render()`` method."""

    def test_render_replaces_placeholders(self, tmp_path: Path) -> None:
        """render() should replace {dataset_title} and {reference_date}."""
        _write_yaml(tmp_path, "test_prompt", VALID_YAML)
        loader = PromptLoader(tmp_path)
        result = loader.render(
            "test_prompt",
            dataset_title="CPI",
            reference_date="2025-01",
        )
        assert "CPI" in result
        assert "2025-01" in result
        assert "{dataset_title}" not in result
        assert "{reference_date}" not in result

    def test_render_missing_variable_raises(self, tmp_path: Path) -> None:
        """render() with missing kwargs should raise ValidationError."""
        _write_yaml(tmp_path, "test_prompt", VALID_YAML)
        loader = PromptLoader(tmp_path)
        with pytest.raises(ValidationError) as exc_info:
            loader.render("test_prompt")  # missing dataset_title & reference_date
        assert exc_info.value.error_code == "PROMPT_RENDER_ERROR"

    def test_render_missing_file_raises(self, tmp_path: Path) -> None:
        """render() with a missing file should raise ValidationError."""
        loader = PromptLoader(tmp_path)
        with pytest.raises(ValidationError):
            loader.render("nonexistent", dataset_title="CPI", reference_date="2025-01")


# ---------------------------------------------------------------------------
# Integration: real journalist.yaml
# ---------------------------------------------------------------------------


class TestJournalistYamlIntegration:
    """Integration tests using the real journalist.yaml file."""

    @pytest.fixture()
    def prompts_dir(self) -> Path:
        """Resolve the real prompts directory."""
        return Path(__file__).resolve().parents[2] / "prompts"

    def test_load_journalist_has_system_prompt(self, prompts_dir: Path) -> None:
        """journalist.yaml should have a non-empty system_prompt."""
        loader = PromptLoader(prompts_dir)
        result = loader.load("journalist")
        assert isinstance(result, str)
        assert len(result.strip()) > 0
        assert "data journalist" in result.lower()

    def test_render_journalist_injects_values(self, prompts_dir: Path) -> None:
        """render() should inject all three variables into journalist.yaml."""
        loader = PromptLoader(prompts_dir)
        result = loader.render(
            "journalist",
            dataset_title="CPI",
            dataset_description="Consumer prices",
            reference_date="2025-01",
        )
        assert "CPI" in result
        assert "Consumer prices" in result
        assert "2025-01" in result
        assert "{dataset_title}" not in result
        assert "{dataset_description}" not in result
        assert "{reference_date}" not in result

    def test_render_journalist_preserves_json_braces(self, prompts_dir: Path) -> None:
        """Escaped {{ / }} in journalist.yaml should become literal { / } after render."""
        loader = PromptLoader(prompts_dir)
        result = loader.render(
            "journalist",
            dataset_title="CPI",
            dataset_description="Consumer prices",
            reference_date="2025-01",
        )
        # The JSON example block should have real braces after rendering
        assert '"virality_score"' in result
        assert '"headline"' in result
