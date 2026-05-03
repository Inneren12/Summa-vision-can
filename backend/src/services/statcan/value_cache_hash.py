"""Phase 3.1aaa: ``source_hash`` canonical derivation for value cache rows.

Per recon §C6: SHA-256 of canonical-JSON-encoded row state. Excludes
all timestamps (``fetched_at``, ``release_time``, ``created_at``,
``updated_at``) so that re-fetching an unchanged data point produces
the same hash and the row reads as "unchanged" rather than as a
spurious update on every nightly refresh.
"""
from __future__ import annotations

import hashlib
import json
from decimal import Decimal


def compute_source_hash(
    *,
    product_id: int,
    cube_id: str,
    semantic_key: str,
    coord: str,
    ref_period: str,
    value: Decimal | None,
    missing: bool,
    decimals: int,
    scalar_factor_code: int,
    symbol_code: int,
    security_level_code: int,
    status_code: int,
    frequency_code: int | None,
    vector_id: int | None,
    response_status_code: int | None,
) -> str:
    """Compute deterministic ``source_hash`` for a value cache row.

    Excludes timestamp columns to prevent false-stale detection on
    cache refresh when the underlying data point is unchanged.
    """
    payload = {
        "product_id": product_id,
        "cube_id": cube_id,
        "semantic_key": semantic_key,
        "coord": coord,
        "ref_period": ref_period,
        "value": str(value) if value is not None else None,
        "missing": missing,
        "decimals": decimals,
        "scalar_factor_code": scalar_factor_code,
        "symbol_code": symbol_code,
        "security_level_code": security_level_code,
        "status_code": status_code,
        "frequency_code": frequency_code,
        "vector_id": vector_id,
        "response_status_code": response_status_code,
    }
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
