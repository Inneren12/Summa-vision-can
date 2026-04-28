"""Lineage helpers for Publication R19 versioning.

Pure functions per ARCH-PURA-001. No DB access here.
"""
from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from src.models.publication import Publication

try:
    from uuid import uuid7  # type: ignore[attr-defined]  # Python 3.13+ stdlib
except ImportError:
    from uuid_utils import uuid7  # uuid-utils package per pyproject.toml

_DEFAULT_SIZE: tuple[int, int] = (1080, 1080)
logger = structlog.get_logger(__name__)

# Mirrors frontend-public/src/components/editor/config/sizes.ts.
# Keep in sync; if presets ever diverge, file as DEBT.
_PRESET_SIZES: dict[str, tuple[int, int]] = {
    "instagram_1080": (1080, 1080),
    "instagram_port": (1080, 1350),
    "instagram": (1080, 1080),
    "twitter": (1200, 675),
    "reddit": (1200, 900),
    "linkedin": (1200, 627),
    "story": (1080, 1920),
}


def compute_config_hash(
    chart_type: str,
    size: tuple[int, int],
    title: str,
) -> str:
    """Compute a deterministic SHA-256 hex digest of the chart config."""
    config_dict = {
        "chart_type": chart_type,
        "size": list(size),
        "title": title,
    }
    return hashlib.sha256(
        json.dumps(config_dict, sort_keys=True).encode("utf-8")
    ).hexdigest()


def derive_size_from_visual_config(
    visual_config_json: str | None,
) -> tuple[int, int]:
    """Extract a `(width, height)` tuple from a publication `visual_config` JSON string."""
    if not visual_config_json:
        logger.warning(
            "publication_clone_size_fallback",
            reason="visual_config_empty",
            default_size=_DEFAULT_SIZE,
        )
        return _DEFAULT_SIZE
    try:
        cfg = json.loads(visual_config_json)
    except (json.JSONDecodeError, TypeError) as exc:
        logger.warning(
            "publication_clone_size_fallback",
            reason="visual_config_invalid_json",
            error=str(exc),
            default_size=_DEFAULT_SIZE,
        )
        return _DEFAULT_SIZE
    if not isinstance(cfg, dict):
        logger.warning(
            "publication_clone_size_fallback",
            reason="visual_config_not_dict",
            default_size=_DEFAULT_SIZE,
        )
        return _DEFAULT_SIZE

    root_size = cfg.get("size")
    if isinstance(root_size, str):
        if root_size in _PRESET_SIZES:
            return _PRESET_SIZES[root_size]
        logger.warning(
            "publication_clone_size_fallback",
            reason="unknown_preset",
            preset=root_size,
            default_size=_DEFAULT_SIZE,
        )
        return _DEFAULT_SIZE

    page = cfg.get("page")
    if not isinstance(page, dict):
        logger.warning(
            "publication_clone_size_fallback",
            reason="visual_config_no_page",
            default_size=_DEFAULT_SIZE,
        )
        return _DEFAULT_SIZE

    size = page.get("size")
    if isinstance(size, str):
        if size in _PRESET_SIZES:
            return _PRESET_SIZES[size]
        logger.warning(
            "publication_clone_size_fallback",
            reason="unknown_preset",
            preset=size,
            default_size=_DEFAULT_SIZE,
        )
        return _DEFAULT_SIZE
    if isinstance(size, dict):
        w = size.get("w")
        h = size.get("h")
        if isinstance(w, int) and isinstance(h, int):
            return (w, h)

    logger.warning(
        "publication_clone_size_fallback",
        reason="visual_config_size_unrecognized",
        size_value=str(size)[:100],
        default_size=_DEFAULT_SIZE,
    )
    return _DEFAULT_SIZE


def generate_lineage_key() -> str:
    """Generate a fresh UUID v7 string for a new (non-clone) publication's
    lineage. Time-sortable + globally unique. Used by the create path.

    Returns:
        Canonical 36-char UUID v7 string, e.g.
        ``'01923f9e-3c12-7c7e-8b32-1d4f5e6a7b8c'``.

    Pure function (ARCH-PURA-001 compliant): module-imported uuid7 is
    deterministic given current wall-clock; no I/O, no DB.
    """
    return str(uuid7())


def derive_clone_lineage_key(source: "Publication") -> str:
    """Return ``source.lineage_key`` directly. Wrapper exists to make the
    inheritance contract explicit at clone call sites.

    Future hook for "manual lineage break" UI (Phase 4+): this function
    would consult an override flag and call :func:`generate_lineage_key`
    instead when set. Today, always inherits.

    Pure function: no I/O, no side effects.

    Raises:
        ValueError: if ``source.lineage_key`` is ``None`` (data integrity
            violation; should be impossible post-Phase-2.2.0 migration).
    """
    if source.lineage_key is None:
        raise ValueError(
            f"Publication id={source.id} has null lineage_key; "
            "data integrity violation post-Phase-2.2.0 migration"
        )
    return source.lineage_key
