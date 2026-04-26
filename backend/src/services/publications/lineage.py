"""Lineage helpers for Publication R19 versioning.

Pure functions per ARCH-PURA-001. No DB access here.
"""
from __future__ import annotations

import hashlib
import json

_DEFAULT_SIZE: tuple[int, int] = (1080, 1080)

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
    """Compute a deterministic SHA-256 hex digest of the chart config.

    Callers typically slice the first 16 chars for dedupe keys.

    Inputs:
        chart_type: e.g. "bar", "line", "infographic"
        size: (width, height) in pixels
        title: the publication headline
    """
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
        return _DEFAULT_SIZE
    try:
        cfg = json.loads(visual_config_json)
    except (json.JSONDecodeError, TypeError):
        return _DEFAULT_SIZE
    if not isinstance(cfg, dict):
        return _DEFAULT_SIZE

    # Current persisted shape from editor persistence:
    #   {"layout": ..., "size": "instagram|twitter|...", ...}
    root_size = cfg.get("size")
    if isinstance(root_size, str):
        return _PRESET_SIZES.get(root_size, _DEFAULT_SIZE)

    # Defensive compatibility with historical/nested shape:
    #   {"page": {"size": "instagram_1080" | {"w": ..., "h": ...}}}
    page = cfg.get("page")
    if not isinstance(page, dict):
        return _DEFAULT_SIZE
    size = page.get("size")

    if isinstance(size, str):
        return _PRESET_SIZES.get(size, _DEFAULT_SIZE)
    if isinstance(size, dict):
        w = size.get("w")
        h = size.get("h")
        if isinstance(w, int) and isinstance(h, int):
            return (w, h)
    return _DEFAULT_SIZE
