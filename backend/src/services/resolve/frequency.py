"""Phase 3.1c — frequency-code resolution helper for auto-prime.

Recon §10 question 4: prefer ``mapping.config.frequency`` if it carries
the StatCan numeric code; else fall back to a metadata-cache lookup;
else ``None`` (the value-cache service has its own retention default
when ``frequency_code`` is ``None``).

Pure async helper — only I/O is the metadata-cache read, which uses the
already-cached entry whenever possible (no StatCan network call here).
"""
from __future__ import annotations

from src.models.semantic_mapping import SemanticMapping
from src.services.statcan.metadata_cache import StatCanMetadataCacheService


_FREQ_NAME_TO_CODE: dict[str, int] = {
    # StatCan WDS reference codes (subset used in Summa Vision today).
    "monthly": 6,
    "quarterly": 9,
    "annual": 12,
    "yearly": 12,
}


async def resolve_frequency_code(
    *,
    mapping: SemanticMapping,
    metadata_cache: StatCanMetadataCacheService,
) -> int | None:
    """Best-effort lookup of ``frequency_code`` for ``auto_prime``.

    Order of preference:
    1. ``mapping.config["frequency"]`` parsed as int (numeric code).
    2. ``mapping.config["frequency"]`` mapped from a known name string
       (``monthly`` → 6, ``quarterly`` → 9, ``annual`` → 12).
    3. Cached cube metadata (``frequency_code`` field on
       :class:`CubeMetadataCacheEntry`) parsed as int.
    4. ``None`` when nothing usable is found — value-cache service
       falls back to its retention default (recon §C2).
    """
    config = mapping.config or {}
    if isinstance(config, dict):
        raw = config.get("frequency")
        if isinstance(raw, int):
            return raw
        if isinstance(raw, str):
            stripped = raw.strip().lower()
            try:
                return int(stripped)
            except ValueError:
                code = _FREQ_NAME_TO_CODE.get(stripped)
                if code is not None:
                    return code

    entry = await metadata_cache.get_cached(mapping.cube_id)
    if entry is not None and entry.frequency_code is not None:
        try:
            return int(entry.frequency_code)
        except (TypeError, ValueError):
            return None
    return None


__all__ = ["resolve_frequency_code"]
