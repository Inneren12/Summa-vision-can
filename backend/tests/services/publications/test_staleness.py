"""Phase 3.1d — :class:`PublicationStalenessService` unit tests.

Per ``docs/recon/phase-3-1d-recon.md`` §6.1. All ResolveService and
repository collaborators are mocked (AsyncMock); no DB / network.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.models.publication_block_snapshot import PublicationBlockSnapshot
from src.schemas.resolve import ResolvedValueResponse
from src.schemas.staleness import (
    BlockComparatorResult,
    Severity,
    StaleReason,
    StaleStatus,
)
from src.services.publications.staleness import PublicationStalenessService
from src.services.resolve.exceptions import (
    MappingNotFoundForResolveError,
    ResolveCacheMissError,
    ResolveInvalidFiltersError,
)


_PUBLICATION_ID = 42
_CAPTURED_AT = datetime(2026, 4, 1, 12, 0, 0, tzinfo=timezone.utc)
_RESOLVED_AT = datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc)


def _build_snapshot(
    *,
    block_id: str = "block-1",
    cube_id: str = "18-10-0004",
    semantic_key: str = "cpi.canada.all_items.index",
    coord: str = "1.2.3.4.5",
    period: str | None = "2024-01",
    dims: list[int] | None = None,
    members: list[int] | None = None,
    mapping_version: int | None = 7,
    source_hash: str = "sha-old",
    value: str | None = "100.5",
    missing: bool = False,
    is_stale: bool = False,
) -> PublicationBlockSnapshot:
    return PublicationBlockSnapshot(
        publication_id=_PUBLICATION_ID,
        block_id=block_id,
        cube_id=cube_id,
        semantic_key=semantic_key,
        coord=coord,
        period=period,
        dims_json=list(dims) if dims is not None else [1, 2, 3],
        members_json=list(members) if members is not None else [10, 20, 30],
        mapping_version_at_publish=mapping_version,
        source_hash_at_publish=source_hash,
        value_at_publish=value,
        missing_at_publish=missing,
        is_stale_at_publish=is_stale,
        captured_at=_CAPTURED_AT,
    )


def _build_resolved(
    *,
    mapping_version: int | None = 7,
    source_hash: str = "sha-old",
    value: str | None = "100.5",
    missing: bool = False,
    is_stale: bool = False,
    coord: str = "1.2.3.4.5",
    period: str = "2024-01",
) -> ResolvedValueResponse:
    return ResolvedValueResponse(
        cube_id="18-10-0004",
        semantic_key="cpi.canada.all_items.index",
        coord=coord,
        period=period,
        value=value,
        missing=missing,
        resolved_at=_RESOLVED_AT,
        source_hash=source_hash,
        is_stale=is_stale,
        units=None,
        cache_status="hit",
        mapping_version=mapping_version,
    )


def _make_service(
    *,
    snapshots: list[PublicationBlockSnapshot] | None = None,
    resolve_side_effect: Any = None,
    resolve_return: Any = None,
) -> tuple[
    PublicationStalenessService,
    AsyncMock,  # resolve_value mock
    AsyncMock,  # snapshot_repo.get_for_publication mock
    AsyncMock,  # snapshot_repo.upsert_for_block mock
]:
    snap_repo = MagicMock()
    snap_repo.get_for_publication = AsyncMock(return_value=snapshots or [])
    snap_repo.upsert_for_block = AsyncMock()
    pub_repo = MagicMock()
    resolve_service = MagicMock()
    if resolve_side_effect is not None:
        resolve_service.resolve_value = AsyncMock(
            side_effect=resolve_side_effect
        )
    else:
        resolve_service.resolve_value = AsyncMock(
            return_value=resolve_return or _build_resolved()
        )
    service = PublicationStalenessService(
        snapshot_repository=snap_repo,
        publication_repository=pub_repo,
        resolve_service=resolve_service,
    )
    return (
        service,
        resolve_service.resolve_value,
        snap_repo.get_for_publication,
        snap_repo.upsert_for_block,
    )


# ---------------------------------------------------------------------------
# Group 1 — shape validator
# ---------------------------------------------------------------------------


class TestValidateDimsMembers:
    def test_validate_dims_members_accepts_valid_input(self) -> None:
        PublicationStalenessService.validate_snapshot_dims_members(
            [1, 2, 10], [0, 5, 99]
        )

    def test_validate_dims_members_rejects_length_mismatch(self) -> None:
        with pytest.raises(ValueError, match="length mismatch"):
            PublicationStalenessService.validate_snapshot_dims_members(
                [1, 2], [10, 20, 30]
            )

    def test_validate_dims_members_rejects_dim_out_of_range(self) -> None:
        with pytest.raises(ValueError, match="out of 1..10"):
            PublicationStalenessService.validate_snapshot_dims_members(
                [0, 2, 3], [1, 2, 3]
            )
        with pytest.raises(ValueError, match="out of 1..10"):
            PublicationStalenessService.validate_snapshot_dims_members(
                [1, 2, 11], [1, 2, 3]
            )

    def test_validate_dims_members_rejects_negative_member(self) -> None:
        with pytest.raises(ValueError, match="non-negative"):
            PublicationStalenessService.validate_snapshot_dims_members(
                [1, 2, 3], [10, -1, 30]
            )

    def test_validate_dims_members_accepts_empty_arrays(self) -> None:
        PublicationStalenessService.validate_snapshot_dims_members([], [])


# ---------------------------------------------------------------------------
# Group 2 — compare: no-snapshot-rows
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compare_no_snapshot_rows_returns_single_synthetic_publication_result() -> None:
    service, resolve_mock, *_ = _make_service(snapshots=[])

    response = await service.compare_for_publication(
        publication_id=_PUBLICATION_ID
    )

    assert response.publication_id == _PUBLICATION_ID
    assert response.overall_status == StaleStatus.UNKNOWN
    assert response.overall_severity == Severity.INFO
    assert len(response.block_results) == 1
    synthetic = response.block_results[0]
    assert synthetic.block_id == ""
    assert synthetic.cube_id == ""
    assert synthetic.semantic_key == ""
    assert synthetic.stale_status == StaleStatus.UNKNOWN
    assert synthetic.stale_reasons == [StaleReason.SNAPSHOT_MISSING]
    assert synthetic.severity == Severity.INFO
    assert synthetic.snapshot is None
    assert synthetic.current is None
    assert synthetic.compare_basis.compare_kind == "snapshot_missing"
    assert synthetic.compare_basis.cause == "no_snapshot_row"
    # Resolve must NOT be called when there are no snapshots.
    resolve_mock.assert_not_awaited()


# ---------------------------------------------------------------------------
# Group 3 — compare: fresh / stale paths
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compare_fresh_when_all_fields_match() -> None:
    snap = _build_snapshot()
    service, *_ = _make_service(
        snapshots=[snap],
        resolve_return=_build_resolved(
            mapping_version=snap.mapping_version_at_publish,
            source_hash=snap.source_hash_at_publish,
            value=snap.value_at_publish,
            missing=snap.missing_at_publish,
            is_stale=False,
        ),
    )

    response = await service.compare_for_publication(
        publication_id=_PUBLICATION_ID
    )

    assert response.overall_status == StaleStatus.FRESH
    assert response.overall_severity == Severity.INFO
    assert len(response.block_results) == 1
    block = response.block_results[0]
    assert block.stale_status == StaleStatus.FRESH
    assert block.stale_reasons == []
    assert block.compare_basis.compare_kind == "drift_check"
    assert block.compare_basis.drift_fields == []
    assert set(block.compare_basis.matched_fields) == {
        "mapping_version",
        "source_hash",
        "value",
        "missing",
    }


@pytest.mark.asyncio
async def test_compare_value_changed() -> None:
    snap = _build_snapshot(value="100.5")
    service, *_ = _make_service(
        snapshots=[snap],
        resolve_return=_build_resolved(
            mapping_version=snap.mapping_version_at_publish,
            source_hash=snap.source_hash_at_publish,
            value="999.9",
        ),
    )

    response = await service.compare_for_publication(
        publication_id=_PUBLICATION_ID
    )

    block = response.block_results[0]
    assert block.stale_status == StaleStatus.STALE
    assert block.stale_reasons == [StaleReason.VALUE_CHANGED]
    assert block.severity == Severity.WARNING
    assert response.overall_status == StaleStatus.STALE
    assert "value" in block.compare_basis.drift_fields


@pytest.mark.asyncio
async def test_compare_mapping_version_changed_only() -> None:
    snap = _build_snapshot(mapping_version=7)
    service, *_ = _make_service(
        snapshots=[snap],
        resolve_return=_build_resolved(
            mapping_version=8,
            source_hash=snap.source_hash_at_publish,
            value=snap.value_at_publish,
        ),
    )

    response = await service.compare_for_publication(
        publication_id=_PUBLICATION_ID
    )

    block = response.block_results[0]
    assert block.stale_status == StaleStatus.STALE
    assert block.stale_reasons == [StaleReason.MAPPING_VERSION_CHANGED]
    assert block.severity == Severity.INFO


@pytest.mark.asyncio
async def test_compare_source_hash_only() -> None:
    snap = _build_snapshot(source_hash="sha-old")
    service, *_ = _make_service(
        snapshots=[snap],
        resolve_return=_build_resolved(
            mapping_version=snap.mapping_version_at_publish,
            source_hash="sha-new",
            value=snap.value_at_publish,
        ),
    )

    response = await service.compare_for_publication(
        publication_id=_PUBLICATION_ID
    )

    block = response.block_results[0]
    assert block.stale_reasons == [StaleReason.SOURCE_HASH_CHANGED]
    assert block.severity == Severity.INFO


@pytest.mark.asyncio
async def test_compare_missing_state_changed() -> None:
    snap = _build_snapshot(missing=False, value="100.5")
    service, *_ = _make_service(
        snapshots=[snap],
        resolve_return=_build_resolved(
            mapping_version=snap.mapping_version_at_publish,
            source_hash=snap.source_hash_at_publish,
            value=None,
            missing=True,
        ),
    )

    response = await service.compare_for_publication(
        publication_id=_PUBLICATION_ID
    )

    block = response.block_results[0]
    assert StaleReason.MISSING_STATE_CHANGED in block.stale_reasons
    assert block.severity == Severity.WARNING


@pytest.mark.asyncio
async def test_compare_cache_row_stale_when_current_is_stale() -> None:
    snap = _build_snapshot(is_stale=False)
    service, *_ = _make_service(
        snapshots=[snap],
        resolve_return=_build_resolved(
            mapping_version=snap.mapping_version_at_publish,
            source_hash=snap.source_hash_at_publish,
            value=snap.value_at_publish,
            is_stale=True,
        ),
    )

    response = await service.compare_for_publication(
        publication_id=_PUBLICATION_ID
    )

    block = response.block_results[0]
    assert StaleReason.CACHE_ROW_STALE in block.stale_reasons
    assert block.stale_status == StaleStatus.STALE


@pytest.mark.asyncio
async def test_compare_multiple_drift_reasons_aggregates() -> None:
    snap = _build_snapshot(
        mapping_version=7, source_hash="sha-old", value="1", missing=False
    )
    service, *_ = _make_service(
        snapshots=[snap],
        resolve_return=_build_resolved(
            mapping_version=8,
            source_hash="sha-new",
            value="2",
            missing=False,
            is_stale=True,
        ),
    )

    response = await service.compare_for_publication(
        publication_id=_PUBLICATION_ID
    )

    block = response.block_results[0]
    assert StaleReason.MAPPING_VERSION_CHANGED in block.stale_reasons
    assert StaleReason.SOURCE_HASH_CHANGED in block.stale_reasons
    assert StaleReason.VALUE_CHANGED in block.stale_reasons
    assert StaleReason.CACHE_ROW_STALE in block.stale_reasons
    assert block.severity == Severity.WARNING  # max(INFO, WARNING) = WARNING
    assert set(block.compare_basis.drift_fields) >= {
        "mapping_version",
        "source_hash",
        "value",
    }


# ---------------------------------------------------------------------------
# Group 4 — compare_failed paths
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compare_failed_on_cache_miss() -> None:
    snap = _build_snapshot()
    exc = ResolveCacheMissError(
        cube_id=snap.cube_id,
        semantic_key=snap.semantic_key,
        coord=snap.coord,
        period=snap.period,
        prime_attempted=False,
        prime_error_code=None,
    )
    service, *_ = _make_service(
        snapshots=[snap], resolve_side_effect=exc
    )

    response = await service.compare_for_publication(
        publication_id=_PUBLICATION_ID
    )

    block = response.block_results[0]
    assert block.stale_status == StaleStatus.UNKNOWN
    assert block.stale_reasons == [StaleReason.COMPARE_FAILED]
    assert block.severity == Severity.WARNING
    assert block.compare_basis.compare_kind == "compare_failed"
    assert block.compare_basis.resolve_error == "RESOLVE_CACHE_MISS"
    assert block.current is None
    assert block.snapshot is not None  # fingerprint preserved


@pytest.mark.asyncio
async def test_compare_failed_on_mapping_not_found() -> None:
    snap = _build_snapshot()
    exc = MappingNotFoundForResolveError(
        cube_id=snap.cube_id, semantic_key=snap.semantic_key
    )
    service, *_ = _make_service(
        snapshots=[snap], resolve_side_effect=exc
    )

    response = await service.compare_for_publication(
        publication_id=_PUBLICATION_ID
    )

    block = response.block_results[0]
    assert block.compare_basis.resolve_error == "MAPPING_NOT_FOUND"
    assert block.compare_basis.details.exception_type == (
        "MappingNotFoundForResolveError"
    )


@pytest.mark.asyncio
async def test_compare_failed_on_invalid_filters() -> None:
    snap = _build_snapshot()
    exc = ResolveInvalidFiltersError(reason="bad shape")
    service, *_ = _make_service(
        snapshots=[snap], resolve_side_effect=exc
    )

    response = await service.compare_for_publication(
        publication_id=_PUBLICATION_ID
    )

    block = response.block_results[0]
    assert block.compare_basis.resolve_error == "RESOLVE_INVALID_FILTERS"


@pytest.mark.asyncio
async def test_compare_failed_on_unexpected() -> None:
    snap = _build_snapshot()
    exc = RuntimeError("kaboom")
    service, *_ = _make_service(
        snapshots=[snap], resolve_side_effect=exc
    )

    response = await service.compare_for_publication(
        publication_id=_PUBLICATION_ID
    )

    block = response.block_results[0]
    assert block.compare_basis.resolve_error == "UNEXPECTED"
    assert block.compare_basis.details.exception_type == "RuntimeError"


@pytest.mark.asyncio
async def test_compare_failed_uses_cached_only_mode() -> None:
    """CRITICAL: locks recon §3.2 BLOCKER-1 cached-only contract."""
    snap = _build_snapshot()
    service, resolve_mock, *_ = _make_service(
        snapshots=[snap],
        resolve_return=_build_resolved(
            mapping_version=snap.mapping_version_at_publish,
            source_hash=snap.source_hash_at_publish,
            value=snap.value_at_publish,
        ),
    )

    await service.compare_for_publication(publication_id=_PUBLICATION_ID)

    assert resolve_mock.await_count == 1
    call = resolve_mock.await_args
    assert call.kwargs["allow_auto_prime"] is False
    assert call.kwargs["cube_id"] == snap.cube_id
    assert call.kwargs["semantic_key"] == snap.semantic_key
    assert call.kwargs["dims"] == snap.dims_json
    assert call.kwargs["members"] == snap.members_json
    assert call.kwargs["period"] == snap.period


@pytest.mark.asyncio
async def test_compare_failed_message_is_sanitized() -> None:
    snap = _build_snapshot()
    sensitive = (
        "SELECT * FROM users WHERE password='hunter2' "
        + ("X" * 1000)  # long payload to verify cap
    )
    exc = RuntimeError(sensitive)
    service, *_ = _make_service(snapshots=[snap], resolve_side_effect=exc)

    response = await service.compare_for_publication(
        publication_id=_PUBLICATION_ID
    )

    block = response.block_results[0]
    msg = block.compare_basis.details.message
    # Length capped per service contract.
    assert len(msg) <= 500
    # No newlines / stack-trace fragments leaked.
    assert "Traceback" not in msg


# ---------------------------------------------------------------------------
# Group 5 — aggregation
# ---------------------------------------------------------------------------


def _result(
    *,
    status: StaleStatus,
    severity: Severity = Severity.INFO,
) -> BlockComparatorResult:
    """Helper for aggregator unit tests — minimal valid drift_check shape."""
    return BlockComparatorResult(
        block_id="b",
        cube_id="c",
        semantic_key="k",
        stale_status=status,
        stale_reasons=[],
        severity=severity,
        compared_at=_RESOLVED_AT,
        snapshot=None,
        current=None,
        compare_basis={
            "compare_kind": "drift_check",
            "matched_fields": [],
            "drift_fields": [],
        },
    )


def test_aggregate_status_stale_dominates_unknown() -> None:
    results = [
        _result(status=StaleStatus.STALE),
        _result(status=StaleStatus.UNKNOWN),
        _result(status=StaleStatus.FRESH),
    ]
    assert (
        PublicationStalenessService._aggregate_status(results)
        == StaleStatus.STALE
    )


def test_aggregate_status_unknown_dominates_fresh() -> None:
    results = [
        _result(status=StaleStatus.UNKNOWN),
        _result(status=StaleStatus.FRESH),
    ]
    assert (
        PublicationStalenessService._aggregate_status(results)
        == StaleStatus.UNKNOWN
    )


def test_aggregate_status_all_fresh() -> None:
    results = [
        _result(status=StaleStatus.FRESH),
        _result(status=StaleStatus.FRESH),
    ]
    assert (
        PublicationStalenessService._aggregate_status(results)
        == StaleStatus.FRESH
    )


def test_aggregate_severity_blocking_dominates() -> None:
    results = [
        _result(status=StaleStatus.FRESH, severity=Severity.INFO),
        _result(status=StaleStatus.STALE, severity=Severity.WARNING),
        _result(status=StaleStatus.STALE, severity=Severity.BLOCKING),
    ]
    assert (
        PublicationStalenessService._aggregate_severity(results)
        == Severity.BLOCKING
    )


def test_aggregate_severity_warning_dominates_info() -> None:
    results = [
        _result(status=StaleStatus.FRESH, severity=Severity.INFO),
        _result(status=StaleStatus.STALE, severity=Severity.WARNING),
    ]
    assert (
        PublicationStalenessService._aggregate_severity(results)
        == Severity.WARNING
    )
