"""Phase 3.1d publication staleness comparator schemas.

Per ``docs/recon/phase-3-1d-recon.md`` §3.2 (publish-time bound block
contract) and §3.4 (locked Pydantic schema + discriminated CompareBasis
union).

Sentinel rule (§3.4 BLOCKER-2 Option C): a :class:`BlockComparatorResult`
with empty ``block_id`` / ``cube_id`` / ``semantic_key`` AND
``compare_basis.compare_kind == "snapshot_missing"`` denotes the
publication-level synthetic result emitted when the publication has zero
snapshot rows. UI MUST discriminate on those two conditions.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Status / reason / severity enums
# ---------------------------------------------------------------------------


class StaleStatus(str, Enum):
    FRESH = "fresh"
    STALE = "stale"
    UNKNOWN = "unknown"


class StaleReason(str, Enum):
    MAPPING_VERSION_CHANGED = "mapping_version_changed"
    SOURCE_HASH_CHANGED = "source_hash_changed"
    VALUE_CHANGED = "value_changed"
    MISSING_STATE_CHANGED = "missing_state_changed"
    CACHE_ROW_STALE = "cache_row_stale"
    COMPARE_FAILED = "compare_failed"
    SNAPSHOT_MISSING = "snapshot_missing"


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    BLOCKING = "blocking"


# ---------------------------------------------------------------------------
# Fingerprint payloads
# ---------------------------------------------------------------------------


class SnapshotFingerprint(BaseModel):
    mapping_version: int | None
    source_hash: str
    value: str | None
    missing: bool
    is_stale: bool
    captured_at: datetime


class ResolveFingerprint(BaseModel):
    mapping_version: int | None
    source_hash: str
    value: str | None
    missing: bool
    is_stale: bool
    resolved_at: datetime


# ---------------------------------------------------------------------------
# CompareBasis discriminated union
# ---------------------------------------------------------------------------


class CompareKind(str, Enum):
    """Discriminator values for :data:`CompareBasis` variants."""

    DRIFT_CHECK = "drift_check"
    SNAPSHOT_MISSING = "snapshot_missing"
    COMPARE_FAILED = "compare_failed"


class CompareFailedDetails(BaseModel):
    """Diagnostic detail for the ``compare_failed`` reason.

    ``message`` MUST be sanitized — no stack traces, SQL, API keys, or
    raw upstream payloads (recon §3.4 lock).
    """

    exception_type: str
    message: str


class DriftCheckBasis(BaseModel):
    compare_kind: Literal["drift_check"]
    matched_fields: list[str]
    drift_fields: list[str]


class SnapshotMissingBasis(BaseModel):
    compare_kind: Literal["snapshot_missing"]
    cause: Literal["no_snapshot_row"]


class CompareFailedBasis(BaseModel):
    compare_kind: Literal["compare_failed"]
    resolve_error: Literal[
        "MAPPING_NOT_FOUND",
        "RESOLVE_CACHE_MISS",
        "RESOLVE_INVALID_FILTERS",
        "UNEXPECTED",
    ]
    details: CompareFailedDetails


CompareBasis = Annotated[
    DriftCheckBasis | SnapshotMissingBasis | CompareFailedBasis,
    Field(discriminator="compare_kind"),
]


# ---------------------------------------------------------------------------
# Block + publication response shapes
# ---------------------------------------------------------------------------


class BlockComparatorResult(BaseModel):
    """Per-block comparator result.

    Sentinel: empty ``block_id`` / ``cube_id`` / ``semantic_key`` paired
    with ``compare_basis.compare_kind == "snapshot_missing"`` marks the
    publication-level synthetic result (§3.4 BLOCKER-2 Option C).
    """

    block_id: str
    cube_id: str
    semantic_key: str
    stale_status: StaleStatus
    stale_reasons: list[StaleReason]
    severity: Severity
    compared_at: datetime
    snapshot: SnapshotFingerprint | None
    current: ResolveFingerprint | None
    compare_basis: CompareBasis


class PublicationComparatorResponse(BaseModel):
    publication_id: int
    overall_status: StaleStatus
    overall_severity: Severity
    compared_at: datetime
    block_results: list[BlockComparatorResult]


# ---------------------------------------------------------------------------
# Publish-time capture wrapper (recon §3.2)
# ---------------------------------------------------------------------------


class BoundBlockReference(BaseModel):
    """Phase 3.1d publish-time bound block reference (recon §3.2)."""

    block_id: str
    cube_id: str
    semantic_key: str
    dims: list[int]
    members: list[int]
    period: str | None = None


class PublicationPublishRequest(BaseModel):
    """Phase 3.1d optional publish-body wrapper.

    Backward-compatible: no body / null / ``{}`` / object body all parse
    to empty ``bound_blocks``. Bare array body is NOT accepted. Future
    extension fields land here with backward-compatible defaults
    (recon §3.2).
    """

    bound_blocks: list[BoundBlockReference] = Field(default_factory=list)


__all__ = [
    "BlockComparatorResult",
    "BoundBlockReference",
    "CompareBasis",
    "CompareFailedBasis",
    "CompareFailedDetails",
    "CompareKind",
    "DriftCheckBasis",
    "PublicationComparatorResponse",
    "PublicationPublishRequest",
    "ResolveFingerprint",
    "Severity",
    "SnapshotFingerprint",
    "SnapshotMissingBasis",
    "StaleReason",
    "StaleStatus",
]
