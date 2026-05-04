"""Phase 3.1d publication staleness service.

Per ``docs/recon/phase-3-1d-recon.md`` §3.2 (DI contract / cached-only
resolve), §4 (comparator algorithm), §5.3 (capture algorithm),
§6.1 (unit-test plan).

ARCH-DPEN-001: every collaborator (snapshot repository, publication
repository, resolve service) is supplied via ``__init__``.
ARCH-PURA-001: drift evaluation is pure — no I/O within
:py:meth:`_compute_drift_reasons`, :py:meth:`_drift_fields`,
:py:meth:`_severity_for_reasons`, :py:meth:`_aggregate_status`,
:py:meth:`_aggregate_severity`.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from src.models.publication_block_snapshot import PublicationBlockSnapshot
from src.repositories.publication_block_snapshot_repository import (
    PublicationBlockSnapshotRepository,
)
from src.repositories.publication_repository import PublicationRepository
from src.schemas.resolve import ResolvedValueResponse
from src.services.publications.exceptions import PublicationNotFoundError
from src.schemas.staleness import (
    BlockComparatorResult,
    BoundBlockReference,
    CompareFailedBasis,
    CompareFailedDetails,
    DriftCheckBasis,
    PublicationComparatorResponse,
    ResolveFingerprint,
    Severity,
    SnapshotFingerprint,
    SnapshotMissingBasis,
    StaleReason,
    StaleStatus,
)
from src.services.resolve.exceptions import (
    MappingNotFoundForResolveError,
    ResolveCacheMissError,
    ResolveInvalidFiltersError,
)
from src.services.resolve.service import ResolveService


logger = logging.getLogger(__name__)


_REASON_SEVERITY: dict[StaleReason, Severity] = {
    StaleReason.MAPPING_VERSION_CHANGED: Severity.INFO,
    StaleReason.SOURCE_HASH_CHANGED: Severity.INFO,
    StaleReason.VALUE_CHANGED: Severity.WARNING,
    StaleReason.MISSING_STATE_CHANGED: Severity.WARNING,
    StaleReason.CACHE_ROW_STALE: Severity.WARNING,
    StaleReason.COMPARE_FAILED: Severity.WARNING,
    StaleReason.SNAPSHOT_MISSING: Severity.INFO,
}

_SEVERITY_ORDER: dict[Severity, int] = {
    Severity.INFO: 0,
    Severity.WARNING: 1,
    Severity.BLOCKING: 2,
}

# Field names included in the drift_check basis diagnostic surface.
# Order is deterministic for stable output.
_DRIFT_FIELD_NAMES: tuple[str, ...] = (
    "mapping_version",
    "source_hash",
    "value",
    "missing",
    "is_stale",
)


class PublicationStalenessService:
    """Phase 3.1d service for snapshot capture and staleness comparison.

    Capture path uses default auto-prime so publish intentionally seeds
    the cache. Compare path forces ``allow_auto_prime=False`` so the
    operation is strictly side-effect-free at the storage layer
    (recon §3.2 BLOCKER-1 Option 1).
    """

    def __init__(
        self,
        *,
        snapshot_repository: PublicationBlockSnapshotRepository,
        publication_repository: PublicationRepository,
        resolve_service: ResolveService,
    ) -> None:
        self._snapshot_repo = snapshot_repository
        self._publication_repo = publication_repository
        self._resolve = resolve_service

    # ------------------------------------------------------------------
    # Shape validation (recon §2.1 invariants)
    # ------------------------------------------------------------------

    @staticmethod
    def validate_snapshot_dims_members(
        dims: list[int], members: list[int]
    ) -> None:
        """DB-shape guard for ``dims_json`` / ``members_json`` upserts.

        Semantic validation (cube/mapping consistency) is owned by the
        3.1c filter-validation route via
        :func:`validate_filters_against_mapping`. This is the minimum
        shape contract enforced before the row is written.

        Raises :class:`ValueError` on violation.
        """
        if len(dims) != len(members):
            raise ValueError(
                f"dims/members length mismatch: dims={len(dims)} != "
                f"members={len(members)}",
            )
        for dim in dims:
            if dim < 1 or dim > 10:
                raise ValueError(
                    f"dims values out of 1..10 range: {dims}",
                )
        for member in members:
            if member < 0:
                raise ValueError(
                    f"members values must be non-negative: {members}",
                )

    # ------------------------------------------------------------------
    # Capture (publish-time)
    # ------------------------------------------------------------------

    async def capture_for_publication(
        self,
        *,
        publication_id: int,
        bound_blocks: list[BoundBlockReference],
    ) -> int:
        """Phase 3.1d publish-time capture (recon §5.3).

        Best-effort: per-block resolve / upsert failures are logged and
        skipped so a partial capture failure NEVER fails the publish.
        Returns the count of successfully captured blocks.
        """
        # One publish action = one captured_at across all snapshot rows
        # (recon §3.3). Per-block now() would split rows from the same
        # publish into different timestamps, breaking deterministic
        # audit semantics.
        captured_at = datetime.now(timezone.utc)
        captured = 0
        for block in bound_blocks:
            try:
                self.validate_snapshot_dims_members(block.dims, block.members)
                resolved = await self._resolve.resolve_value(
                    cube_id=block.cube_id,
                    semantic_key=block.semantic_key,
                    dims=block.dims,
                    members=block.members,
                    period=block.period,
                )
                await self._snapshot_repo.upsert_for_block(
                    publication_id=publication_id,
                    block_id=block.block_id,
                    cube_id=block.cube_id,
                    semantic_key=block.semantic_key,
                    coord=resolved.coord,
                    period=block.period,
                    dims_json=block.dims,
                    members_json=block.members,
                    mapping_version_at_publish=resolved.mapping_version,
                    source_hash_at_publish=resolved.source_hash,
                    value_at_publish=resolved.value,
                    missing_at_publish=resolved.missing,
                    is_stale_at_publish=resolved.is_stale,
                    captured_at=captured_at,
                )
                captured += 1
            except Exception:  # noqa: BLE001 — best-effort capture
                logger.exception(
                    "publication_staleness.capture_block_failed",
                    extra={
                        "publication_id": publication_id,
                        "block_id": block.block_id,
                        "cube_id": block.cube_id,
                        "semantic_key": block.semantic_key,
                    },
                )
        return captured

    # ------------------------------------------------------------------
    # Compare (read-only)
    # ------------------------------------------------------------------

    async def compare_for_publication(
        self,
        *,
        publication_id: int,
    ) -> PublicationComparatorResponse:
        """Phase 3.1d compare endpoint logic (recon §4).

        Side-effect-free per recon §3.1 — uses cached-only resolve mode
        (``allow_auto_prime=False``).

        No-snapshot-rows case (recon §3.4 BLOCKER-2 Option C): returns
        a single synthetic publication-level :class:`BlockComparatorResult`.
        """
        # Existence guard (recon §3.1): 404 PUBLICATION_NOT_FOUND must
        # precede the snapshot_missing path so a nonexistent id does
        # not masquerade as a fresh-clone synthetic result.
        publication = await self._publication_repo.get_by_id(publication_id)
        if publication is None:
            raise PublicationNotFoundError(
                details={"publication_id": publication_id}
            )

        compared_at = datetime.now(timezone.utc)
        snapshots = await self._snapshot_repo.get_for_publication(publication_id)

        if not snapshots:
            synthetic = BlockComparatorResult(
                block_id="",
                cube_id="",
                semantic_key="",
                stale_status=StaleStatus.UNKNOWN,
                stale_reasons=[StaleReason.SNAPSHOT_MISSING],
                severity=Severity.INFO,
                compared_at=compared_at,
                snapshot=None,
                current=None,
                compare_basis=SnapshotMissingBasis(
                    compare_kind="snapshot_missing",
                    cause="no_snapshot_row",
                ),
            )
            return PublicationComparatorResponse(
                publication_id=publication_id,
                overall_status=StaleStatus.UNKNOWN,
                overall_severity=Severity.INFO,
                compared_at=compared_at,
                block_results=[synthetic],
            )

        block_results = [
            await self._compare_one_snapshot(snap, compared_at)
            for snap in snapshots
        ]
        return PublicationComparatorResponse(
            publication_id=publication_id,
            overall_status=self._aggregate_status(block_results),
            overall_severity=self._aggregate_severity(block_results),
            compared_at=compared_at,
            block_results=block_results,
        )

    async def _compare_one_snapshot(
        self,
        snap: PublicationBlockSnapshot,
        compared_at: datetime,
    ) -> BlockComparatorResult:
        """Compare a single snapshot row vs. current cached value."""
        try:
            current = await self._resolve.resolve_value(
                cube_id=snap.cube_id,
                semantic_key=snap.semantic_key,
                dims=list(snap.dims_json),
                members=list(snap.members_json),
                period=snap.period,
                allow_auto_prime=False,
            )
        except MappingNotFoundForResolveError as exc:
            return self._build_compare_failed(
                snap, compared_at, exc, "MAPPING_NOT_FOUND"
            )
        except ResolveCacheMissError as exc:
            return self._build_compare_failed(
                snap, compared_at, exc, "RESOLVE_CACHE_MISS"
            )
        except ResolveInvalidFiltersError as exc:
            return self._build_compare_failed(
                snap, compared_at, exc, "RESOLVE_INVALID_FILTERS"
            )
        except Exception as exc:  # noqa: BLE001 — defensive catch-all
            return self._build_compare_failed(
                snap, compared_at, exc, "UNEXPECTED"
            )

        reasons = self._compute_drift_reasons(snap, current)
        severity = self._severity_for_reasons(reasons)
        status = StaleStatus.STALE if reasons else StaleStatus.FRESH

        snapshot_fp = self._snapshot_fingerprint(snap)
        current_fp = ResolveFingerprint(
            mapping_version=current.mapping_version,
            source_hash=current.source_hash,
            value=current.value,
            missing=current.missing,
            is_stale=current.is_stale,
            # Carry the cache row's resolve provenance, not the compare
            # timestamp. Compare metadata lives in `compared_at` on the
            # parent BlockComparatorResult.
            resolved_at=current.resolved_at,
        )

        drift_fields = self._drift_fields(snap, current)
        matched_fields = [
            f for f in _DRIFT_FIELD_NAMES if f not in drift_fields
        ]

        return BlockComparatorResult(
            block_id=snap.block_id,
            cube_id=snap.cube_id,
            semantic_key=snap.semantic_key,
            stale_status=status,
            stale_reasons=reasons,
            severity=severity,
            compared_at=compared_at,
            snapshot=snapshot_fp,
            current=current_fp,
            compare_basis=DriftCheckBasis(
                compare_kind="drift_check",
                matched_fields=matched_fields,
                drift_fields=drift_fields,
            ),
        )

    # ------------------------------------------------------------------
    # Pure helpers (no I/O)
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_drift_reasons(
        snap: PublicationBlockSnapshot,
        current: ResolvedValueResponse,
    ) -> list[StaleReason]:
        """Per recon §4 step 4 — evaluate per-field drift.

        ``value_changed`` uses byte-equal string compare (canonical-string
        contract per recon §4).
        """
        reasons: list[StaleReason] = []
        if snap.mapping_version_at_publish != current.mapping_version:
            reasons.append(StaleReason.MAPPING_VERSION_CHANGED)
        if snap.source_hash_at_publish != current.source_hash:
            reasons.append(StaleReason.SOURCE_HASH_CHANGED)
        if snap.value_at_publish != current.value:
            reasons.append(StaleReason.VALUE_CHANGED)
        if snap.missing_at_publish != current.missing:
            reasons.append(StaleReason.MISSING_STATE_CHANGED)
        if current.is_stale:
            reasons.append(StaleReason.CACHE_ROW_STALE)
        return reasons

    @staticmethod
    def _drift_fields(
        snap: PublicationBlockSnapshot,
        current: ResolvedValueResponse,
    ) -> list[str]:
        fields: list[str] = []
        if snap.mapping_version_at_publish != current.mapping_version:
            fields.append("mapping_version")
        if snap.source_hash_at_publish != current.source_hash:
            fields.append("source_hash")
        if snap.value_at_publish != current.value:
            fields.append("value")
        if snap.missing_at_publish != current.missing:
            fields.append("missing")
        # cache_row_stale is triggered solely by the current row's flag,
        # not by snapshot-vs-current diff. Surface it on the diagnostic
        # so UI can explain why the reason fired.
        if current.is_stale:
            fields.append("is_stale")
        return fields

    @staticmethod
    def _severity_for_reasons(reasons: list[StaleReason]) -> Severity:
        if not reasons:
            return Severity.INFO
        return max(
            (_REASON_SEVERITY[r] for r in reasons),
            key=lambda s: _SEVERITY_ORDER[s],
        )

    @staticmethod
    def _aggregate_status(
        results: list[BlockComparatorResult],
    ) -> StaleStatus:
        if any(r.stale_status == StaleStatus.STALE for r in results):
            return StaleStatus.STALE
        if any(r.stale_status == StaleStatus.UNKNOWN for r in results):
            return StaleStatus.UNKNOWN
        return StaleStatus.FRESH

    @staticmethod
    def _aggregate_severity(
        results: list[BlockComparatorResult],
    ) -> Severity:
        return max(
            (r.severity for r in results),
            key=lambda s: _SEVERITY_ORDER[s],
        )

    @staticmethod
    def _snapshot_fingerprint(
        snap: PublicationBlockSnapshot,
    ) -> SnapshotFingerprint:
        return SnapshotFingerprint(
            mapping_version=snap.mapping_version_at_publish,
            source_hash=snap.source_hash_at_publish,
            value=snap.value_at_publish,
            missing=snap.missing_at_publish,
            is_stale=snap.is_stale_at_publish,
            captured_at=snap.captured_at,
        )

    # Whitelist of safe messages per resolve_error code. ``str(exc)``
    # is NEVER returned because the underlying exception may carry SQL
    # fragments, API keys, paths, or upstream payloads (recon §3.4 lock).
    _SAFE_COMPARE_FAILED_MESSAGES: dict[str, str] = {
        "MAPPING_NOT_FOUND": "Mapping not found for snapshot identity",
        "RESOLVE_CACHE_MISS": "Current cache row is missing",
        "RESOLVE_INVALID_FILTERS": "Snapshot filters are invalid",
        "UNEXPECTED": "Unexpected compare failure",
    }

    def _build_compare_failed(
        self,
        snap: PublicationBlockSnapshot,
        compared_at: datetime,
        exc: BaseException,
        resolve_error: str,
    ) -> BlockComparatorResult:
        """Build a ``compare_failed`` result with sanitized diagnostics.

        Per recon §3.4: ``message`` MUST NOT carry stack traces, SQL,
        API keys, or raw upstream payloads. We never return
        ``str(exc)`` — only a fixed whitelisted message per
        ``resolve_error`` code. The exception class name is safe to
        return because exception classes are part of code, not user
        data.
        """
        details = CompareFailedDetails(
            exception_type=type(exc).__name__,
            message=self._SAFE_COMPARE_FAILED_MESSAGES.get(
                resolve_error,
                self._SAFE_COMPARE_FAILED_MESSAGES["UNEXPECTED"],
            ),
        )
        return BlockComparatorResult(
            block_id=snap.block_id,
            cube_id=snap.cube_id,
            semantic_key=snap.semantic_key,
            stale_status=StaleStatus.UNKNOWN,
            stale_reasons=[StaleReason.COMPARE_FAILED],
            severity=Severity.WARNING,
            compared_at=compared_at,
            snapshot=self._snapshot_fingerprint(snap),
            current=None,
            compare_basis=CompareFailedBasis(
                compare_kind="compare_failed",
                resolve_error=resolve_error,  # type: ignore[arg-type]
                details=details,
            ),
        )


__all__ = ["PublicationStalenessService"]
