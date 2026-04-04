"""Prompt template loader for the AI scoring pipeline.

``PromptLoader`` reads YAML prompt files from a configurable directory
and renders them with dynamic values using :meth:`str.format`.

Architecture notes:
    * ``PromptLoader`` receives ``prompts_dir`` via constructor
      (ARCH-DPEN-001).  No hardcoded paths.
    * ``load()`` and ``render()`` perform only file I/O — no database
      calls, no HTTP (ARCH-PURA-001).
    * File-system or YAML errors are caught explicitly and re-raised
      as :class:`~src.core.exceptions.ValidationError`.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from src.core.exceptions import ValidationError


class PromptLoader:
    """Load and render YAML-based system prompts.

    Args:
        prompts_dir: Absolute or relative :class:`~pathlib.Path` to the
            directory containing ``*.yaml`` prompt files.
    """

    def __init__(self, prompts_dir: Path) -> None:
        self._prompts_dir = prompts_dir

    def load(self, name: str) -> str:
        """Read ``{prompts_dir}/{name}.yaml`` and return the ``system_prompt`` value.

        Args:
            name: Stem of the YAML file (without extension).

        Returns:
            The raw ``system_prompt`` string (un-rendered).

        Raises:
            ValidationError: If the file is missing, malformed YAML, or
                the ``system_prompt`` key is absent.
        """
        filepath = self._prompts_dir / f"{name}.yaml"

        try:
            raw = filepath.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise ValidationError(
                message=f"Prompt file not found: {filepath}",
                error_code="PROMPT_NOT_FOUND",
                context={"path": str(filepath)},
            ) from exc

        try:
            data = yaml.safe_load(raw)
        except yaml.YAMLError as exc:
            raise ValidationError(
                message=f"Malformed YAML in prompt file: {filepath}",
                error_code="PROMPT_YAML_ERROR",
                context={"path": str(filepath)},
            ) from exc

        if not isinstance(data, dict):
            raise ValidationError(
                message=f"Prompt file does not contain a YAML mapping: {filepath}",
                error_code="PROMPT_YAML_ERROR",
                context={"path": str(filepath)},
            )

        try:
            system_prompt: str = data["system_prompt"]
        except KeyError as exc:
            raise ValidationError(
                message=f"Prompt file missing 'system_prompt' key: {filepath}",
                error_code="PROMPT_MISSING_KEY",
                context={"path": str(filepath), "available_keys": list(data.keys())},
            ) from exc

        if not isinstance(system_prompt, str) or not system_prompt.strip():
            raise ValidationError(
                message=f"'system_prompt' is empty or not a string: {filepath}",
                error_code="PROMPT_EMPTY",
                context={"path": str(filepath)},
            )

        return system_prompt

    def render(self, name: str, **kwargs: object) -> str:
        """Load a prompt and render it with dynamic values.

        Calls :meth:`load` then ``str.format(**kwargs)`` on the result.

        Args:
            name: Stem of the YAML file (without extension).
            **kwargs: Template variables to inject (e.g.
                ``dataset_title``, ``reference_date``).

        Returns:
            The fully rendered prompt string.

        Raises:
            ValidationError: If loading or rendering fails.
        """
        template = self.load(name)

        try:
            return template.format(**kwargs)
        except KeyError as exc:
            raise ValidationError(
                message=f"Missing template variable in prompt '{name}': {exc}",
                error_code="PROMPT_RENDER_ERROR",
                context={"name": name, "missing_key": str(exc)},
            ) from exc
