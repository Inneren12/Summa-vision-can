"""Storage key parsing helpers for StatCan paths.

Pure functions per ARCH-PURA-001. No DB access, no I/O.

Used by the admin preview endpoint to extract metadata (currently
just product_id) from storage keys without requiring backend
catalog lookups. Frontend treats parsing failures as "no diff
baseline available" and degrades gracefully.
"""
from __future__ import annotations

import re


# Matches StatCan processed-data keys produced by data_fetch.py:
#   statcan/processed/{product_id}/{date}.parquet
# Captures product_id segment. Other path families (temp/uploads/,
# statcan/transformed/) intentionally do NOT match — they have no
# stable product_id and the endpoint returns product_id=None for them.
_STATCAN_PRODUCT_ID_PATTERN = re.compile(
    r"^statcan/processed/([^/]+)/[^/]+\.parquet$"
)


def extract_product_id_from_storage_key(storage_key: str) -> str | None:
    """Extract the StatCan product_id from a processed-data storage key.

    Args:
        storage_key: An S3-style storage key, e.g.
            ``statcan/processed/18-10-0004-01/2026-04-26.parquet``.

    Returns:
        The product_id segment if the key matches StatCan processed
        path structure; None otherwise (user uploads, transformed
        outputs, malformed keys, empty strings).
    """
    match = _STATCAN_PRODUCT_ID_PATTERN.match(storage_key)
    return match.group(1) if match else None
