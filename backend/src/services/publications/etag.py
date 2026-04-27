"""ETag derivation for Publication resources.

Pure module. No I/O, no clock reads, no DB access.
ARCH-PURA-001 + ARCH-DPEN-001 trivially satisfied (no class, no DI).
"""

from __future__ import annotations

import hashlib

from src.models.publication import Publication


def compute_etag(pub: Publication) -> str:
    """Derive a strong ETag for a Publication row.

    Per docs/architecture/ARCHITECTURE_INVARIANTS.md §6 + §7:
      - Inputs: id, updated_at OR created_at fallback, config_hash OR ""
      - Separator: '|' (ASCII 0x7C)
      - Hash: SHA-256, truncated to 16 hex chars
      - Output: strong ETag, e.g. '"a1b2c3d4e5f60718"'
        Strong because the validator is derived from row metadata (id + timestamp +
        config_hash) — not the response body — so identical inputs always produce
        byte-identical ETags. RFC 7232 §2.3 strong validator semantics apply.
        Strong ETags are the correct fit for If-Match (lost-update protection).

    The created_at fallback handles fresh DRAFT rows where updated_at is NULL.
    The "" substitution for config_hash handles non-clone rows.
    Both are deterministic; both keep the function pure.

    Separator '|' is collision-safe in this domain: id is integer-stringified,
    timestamp is ISO-8601, config_hash is 64-char hex — none can contain '|'.
    """
    timestamp = (pub.updated_at or pub.created_at).isoformat()
    config = pub.config_hash or ""
    raw = f"{pub.id}|{timestamp}|{config}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    return f'"{digest}"'
