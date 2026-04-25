"""Helpers for extracting temp storage references from job payloads."""

from __future__ import annotations

import json
from collections.abc import Mapping


def extract_graphics_generate_data_key(payload: object) -> str | None:
    """Return ``graphics_generate`` payload ``data_key`` when present.

    Accepts either a parsed mapping or a JSON string. Returns ``None`` for
    malformed payloads, unknown shapes, or missing/invalid ``data_key``.
    """
    parsed = _coerce_payload_mapping(payload)
    if parsed is None:
        return None

    data_key = parsed.get("data_key")
    if not isinstance(data_key, str) or not data_key:
        return None
    return data_key


def _coerce_payload_mapping(payload: object) -> Mapping[str, object] | None:
    """Normalize payload value into a mapping without raising."""
    if isinstance(payload, str):
        try:
            decoded = json.loads(payload)
        except json.JSONDecodeError:
            return None
        if isinstance(decoded, Mapping):
            return decoded
        return None

    if isinstance(payload, Mapping):
        return payload

    return None
