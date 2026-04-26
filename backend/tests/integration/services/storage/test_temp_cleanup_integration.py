"""Integration tests for temp cleanup safety logic with PostgreSQL."""

from __future__ import annotations

import copy
import json
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from sqlalchemy import select

from src.core.storage import StorageInterface, StorageObjectMetadata
from src.models.job import Job, JobStatus
from src.services.storage.temp_cleanup import cleanup_temp_uploads

pytestmark = pytest.mark.integration


class FakeStorage(StorageInterface):
    def __init__(
        self,
        *,
        objects: list[StorageObjectMetadata],
        missing_on_delete: set[str] | None = None,
        page_size: int = 100,
    ) -> None:
        self._objects: dict[str, StorageObjectMetadata] = {
            obj.key: obj for obj in objects
        }
        self.deleted: list[str] = []
        self.list_calls: list[str] = []
        self.missing_on_delete = set(missing_on_delete or set())
        self._page_size = page_size

    async def upload_dataframe_as_csv(self, df: Any, path: str) -> None:
        return None

    async def upload_raw(
        self,
        data: str | bytes,
        path: str,
        content_type: str = "text/html",
    ) -> None:
        return None

    async def upload_bytes(self, data: bytes, key: str) -> None:
        return None

    async def download_bytes(self, key: str) -> bytes:
        return b""

    async def download_csv(self, path: str) -> Any:
        return None

    async def delete_object(self, key: str) -> None:
        if key in self.missing_on_delete:
            raise FileNotFoundError(key)
        self.deleted.append(key)
        self._objects.pop(key, None)

    async def list_objects(self, prefix: str) -> list[str]:
        return sorted(k for k in self._objects if k.startswith(prefix))

    async def iter_objects_with_metadata(self, prefix: str):
        self.list_calls.append(prefix)
        items = sorted(
            (obj for obj in self._objects.values() if obj.key.startswith(prefix)),
            key=lambda obj: obj.key,
        )
        for idx in range(0, len(items), self._page_size):
            yield items[idx : idx + self._page_size]

    async def generate_presigned_url(self, path: str, ttl: int = 3600) -> str:
        return ""

    def has_key(self, key: str) -> bool:
        return key in self._objects

    def snapshot_before_cleanup(self) -> dict[str, StorageObjectMetadata]:
        return copy.deepcopy(self._objects)

    def all_objects(self) -> list[StorageObjectMetadata]:
        return list(self._objects.values())


def _meta(
    key: str,
    *,
    now: datetime,
    age_hours: int,
    size: int = 1,
) -> StorageObjectMetadata:
    return StorageObjectMetadata(
        key=key,
        size_bytes=size,
        last_modified=now - timedelta(hours=age_hours),
    )


async def _insert_job(
    pg_session,
    *,
    key: str,
    status: JobStatus,
    job_type: str = "graphics_generate",
) -> None:
    payload = {
        "schema_version": 1,
        "data_key": key,
        "chart_type": "line",
        "title": "t",
        "size": [1200, 900],
        "category": "housing",
        "source_product_id": None,
    }
    pg_session.add(Job(job_type=job_type, status=status, payload_json=json.dumps(payload)))
    await pg_session.commit()


@pytest.mark.anyio
async def test_deletes_old_unreferenced_keys(pg_session) -> None:
    now = datetime(2026, 4, 25, 12, 0, tzinfo=timezone.utc)
    storage = FakeStorage(
        objects=[_meta(f"temp/uploads/{i}.parquet", now=now, age_hours=30) for i in range(3)],
    )

    result = await cleanup_temp_uploads(
        pg_session,
        storage,
        prefixes=["temp/uploads/"],
        ttl_hours=24,
        max_delete_keys=1000,
        max_list_keys=50000,
        now=now,
    )

    assert result.deleted == 3
    assert result.referenced_skipped == 0


@pytest.mark.anyio
async def test_skips_keys_referenced_by_queued_job(pg_session) -> None:
    now = datetime(2026, 4, 25, 12, 0, tzinfo=timezone.utc)
    keep_key = "temp/uploads/keep.parquet"
    storage = FakeStorage(
        objects=[
            _meta(keep_key, now=now, age_hours=30),
            _meta("temp/uploads/drop1.parquet", now=now, age_hours=30),
            _meta("temp/uploads/drop2.parquet", now=now, age_hours=30),
        ],
    )
    await _insert_job(pg_session, key=keep_key, status=JobStatus.QUEUED)

    result = await cleanup_temp_uploads(
        pg_session,
        storage,
        prefixes=["temp/uploads/"],
        ttl_hours=24,
        max_delete_keys=1000,
        max_list_keys=50000,
        now=now,
    )

    assert result.deleted == 2
    assert result.referenced_skipped == 1
    assert storage.has_key(keep_key)


@pytest.mark.anyio
async def test_skips_keys_referenced_by_running_job(pg_session) -> None:
    now = datetime(2026, 4, 25, 12, 0, tzinfo=timezone.utc)
    keep_key = "temp/uploads/run.parquet"
    storage = FakeStorage(
        objects=[
            _meta(keep_key, now=now, age_hours=30),
            _meta("temp/uploads/drop.parquet", now=now, age_hours=30),
        ],
    )
    await _insert_job(pg_session, key=keep_key, status=JobStatus.RUNNING)

    result = await cleanup_temp_uploads(
        pg_session,
        storage,
        prefixes=["temp/uploads/"],
        ttl_hours=24,
        max_delete_keys=1000,
        max_list_keys=50000,
        now=now,
    )

    assert result.deleted == 1
    assert result.referenced_skipped == 1


@pytest.mark.anyio
async def test_skips_keys_referenced_by_retrying_job(pg_session) -> None:
    retrying = getattr(JobStatus, "RETRYING", None)
    if retrying is None:
        pytest.skip("JobStatus.RETRYING not implemented in this codebase")

    now = datetime(2026, 4, 25, 12, 0, tzinfo=timezone.utc)
    keep_key = "temp/uploads/retry.parquet"
    storage = FakeStorage(
        objects=[
            _meta(keep_key, now=now, age_hours=30),
            _meta("temp/uploads/drop.parquet", now=now, age_hours=30),
        ],
    )
    await _insert_job(pg_session, key=keep_key, status=retrying)

    result = await cleanup_temp_uploads(
        pg_session,
        storage,
        prefixes=["temp/uploads/"],
        ttl_hours=24,
        max_delete_keys=1000,
        max_list_keys=50000,
        now=now,
    )

    assert result.deleted == 1
    assert result.referenced_skipped == 1


@pytest.mark.anyio
async def test_does_not_skip_keys_referenced_by_completed_job(pg_session) -> None:
    now = datetime(2026, 4, 25, 12, 0, tzinfo=timezone.utc)
    key = "temp/uploads/done.parquet"
    storage = FakeStorage(objects=[_meta(key, now=now, age_hours=30)])
    await _insert_job(pg_session, key=key, status=JobStatus.SUCCESS)

    result = await cleanup_temp_uploads(
        pg_session,
        storage,
        prefixes=["temp/uploads/"],
        ttl_hours=24,
        max_delete_keys=1000,
        max_list_keys=50000,
        now=now,
    )

    assert result.deleted == 1
    assert result.referenced_skipped == 0


@pytest.mark.anyio
async def test_does_not_skip_keys_referenced_by_failed_job(pg_session) -> None:
    now = datetime(2026, 4, 25, 12, 0, tzinfo=timezone.utc)
    key = "temp/uploads/failed.parquet"
    storage = FakeStorage(objects=[_meta(key, now=now, age_hours=30)])
    await _insert_job(pg_session, key=key, status=JobStatus.FAILED)

    result = await cleanup_temp_uploads(
        pg_session,
        storage,
        prefixes=["temp/uploads/"],
        ttl_hours=24,
        max_delete_keys=1000,
        max_list_keys=50000,
        now=now,
    )

    assert result.deleted == 1


@pytest.mark.anyio
async def test_oldest_expired_prioritized_across_pages(pg_session) -> None:
    now = datetime(2026, 4, 25, 12, 0, tzinfo=timezone.utc)
    base = now - timedelta(hours=25)
    objects: list[StorageObjectMetadata] = []
    for i in range(500):
        age_offset = (i * 7) % 500
        objects.append(
            StorageObjectMetadata(
                key=f"temp/uploads/expired_{i:04d}.parquet",
                size_bytes=1,
                last_modified=base - timedelta(minutes=age_offset),
            ),
        )
    storage = FakeStorage(objects=objects, page_size=50)
    snapshot = storage.snapshot_before_cleanup()

    result = await cleanup_temp_uploads(
        pg_session,
        storage,
        prefixes=["temp/uploads/"],
        ttl_hours=24,
        max_delete_keys=100,
        max_list_keys=10000,
        now=now,
    )

    assert result.scanned == 100
    assert result.deleted == 100

    expected_oldest_keys = {
        item.key
        for item in sorted(snapshot.values(), key=lambda obj: obj.last_modified)[:100]
    }
    remaining = {obj.key for obj in storage.all_objects()}
    for expected_key in expected_oldest_keys:
        assert expected_key not in remaining


@pytest.mark.anyio
async def test_expired_beyond_fresh_listing_still_reached(pg_session) -> None:
    now = datetime(2026, 4, 25, 12, 0, tzinfo=timezone.utc)
    objects = [
        _meta(
            f"temp/uploads/{chr(ord('a') + (i % 13))}{i:04d}.parquet",
            now=now,
            age_hours=1,
        )
        for i in range(1500)
    ]
    objects.append(_meta("temp/uploads/zzz_old.parquet", now=now, age_hours=30))
    storage = FakeStorage(objects=objects)

    result = await cleanup_temp_uploads(
        pg_session,
        storage,
        prefixes=["temp/uploads/"],
        ttl_hours=24,
        max_delete_keys=1000,
        max_list_keys=10000,
        now=now,
    )

    assert result.scanned == 1
    assert result.deleted == 1
    assert not storage.has_key("temp/uploads/zzz_old.parquet")


@pytest.mark.anyio
async def test_list_cap_bounds_memory_on_huge_prefix(pg_session) -> None:
    now = datetime(2026, 4, 25, 12, 0, tzinfo=timezone.utc)
    objects = [
        _meta(f"temp/uploads/fresh_{i:05d}.parquet", now=now, age_hours=1)
        for i in range(10000)
    ]
    objects.append(_meta("temp/uploads/zzz_old.parquet", now=now, age_hours=30))
    storage = FakeStorage(objects=objects, page_size=100)

    result = await cleanup_temp_uploads(
        pg_session,
        storage,
        prefixes=["temp/uploads/"],
        ttl_hours=24,
        max_delete_keys=1000,
        max_list_keys=500,
        now=now,
    )

    assert result.scanned == 0
    assert result.deleted == 0


@pytest.mark.anyio
async def test_cap_hit_logs_warning(pg_session, monkeypatch) -> None:
    now = datetime(2026, 4, 25, 12, 0, tzinfo=timezone.utc)
    storage = FakeStorage(
        objects=[_meta(f"temp/uploads/old_{i:04d}.parquet", now=now, age_hours=30) for i in range(100)],
    )

    warnings: list[str] = []

    def _capture_warning(event, **kwargs):
        warnings.append(f"{event} {kwargs.get('message', '')}")

    monkeypatch.setattr(
        "src.services.storage.temp_cleanup.logger.warning",
        _capture_warning,
    )

    await cleanup_temp_uploads(
        pg_session,
        storage,
        prefixes=["temp/uploads/"],
        ttl_hours=24,
        max_delete_keys=50,
        max_list_keys=50000,
        now=now,
    )

    assert any("exceed delete cap" in warning for warning in warnings), (
        f"Expected delete-cap warning, got: {warnings}"
    )


@pytest.mark.anyio
async def test_idempotent_on_404_delete(pg_session) -> None:
    now = datetime(2026, 4, 25, 12, 0, tzinfo=timezone.utc)
    key = "temp/uploads/missing.parquet"
    storage = FakeStorage(
        objects=[_meta(key, now=now, age_hours=30)],
        missing_on_delete={key},
    )

    result = await cleanup_temp_uploads(
        pg_session,
        storage,
        prefixes=["temp/uploads/"],
        ttl_hours=24,
        max_delete_keys=1000,
        max_list_keys=50000,
        now=now,
    )

    assert result.deleted == 1
    assert result.errors == []


@pytest.mark.anyio
async def test_handles_empty_prefix_gracefully(pg_session) -> None:
    now = datetime(2026, 4, 25, 12, 0, tzinfo=timezone.utc)
    storage = FakeStorage(objects=[])

    result = await cleanup_temp_uploads(
        pg_session,
        storage,
        prefixes=["temp/uploads/"],
        ttl_hours=24,
        max_delete_keys=1000,
        max_list_keys=50000,
        now=now,
    )

    assert result.scanned == 0
    assert result.deleted == 0
    assert result.referenced_skipped == 0


@pytest.mark.anyio
async def test_multiple_prefixes_processed_in_order(pg_session) -> None:
    now = datetime(2026, 4, 25, 12, 0, tzinfo=timezone.utc)
    storage = FakeStorage(
        objects=[
            _meta("temp/uploads/a.parquet", now=now, age_hours=30),
            _meta("temp/staging/b.parquet", now=now, age_hours=30),
        ],
    )

    result = await cleanup_temp_uploads(
        pg_session,
        storage,
        prefixes=["temp/uploads/", "temp/staging/"],
        ttl_hours=24,
        max_delete_keys=1000,
        max_list_keys=50000,
        now=now,
    )

    assert result.deleted == 2
    assert storage.list_calls == ["temp/uploads/", "temp/staging/"]


@pytest.mark.anyio
async def test_max_delete_keys_is_global_across_prefixes(pg_session) -> None:
    """Delete cap is per cleanup cycle globally — does NOT multiply by prefix count."""
    now = datetime(2026, 4, 25, 12, 0, tzinfo=timezone.utc)
    objects = [
        _meta("temp/a/expired_0.parquet", now=now, age_hours=30),
        _meta("temp/a/expired_1.parquet", now=now, age_hours=30),
        _meta("temp/b/expired_0.parquet", now=now, age_hours=30),
        _meta("temp/b/expired_1.parquet", now=now, age_hours=30),
    ]
    storage = FakeStorage(objects=objects)

    result = await cleanup_temp_uploads(
        pg_session,
        storage,
        prefixes=["temp/a/", "temp/b/"],
        ttl_hours=24,
        max_delete_keys=2,
        max_list_keys=10_000,
        now=now,
    )

    assert result.scanned == 2, f"Global cap=2 must limit candidates to 2, got {result.scanned}"
    assert result.deleted == 2, f"Exactly 2 deletions allowed per cycle, got {result.deleted}"

    remaining = [obj.key for obj in storage.all_objects() if "expired_" in obj.key]
    assert len(remaining) == 2, (
        f"Exactly 2 expired candidates must remain for next cycle, got {len(remaining)}"
    )


@pytest.mark.anyio
async def test_max_list_keys_is_global_across_prefixes(
    pg_session,
    monkeypatch,
) -> None:
    """List cap is per cleanup cycle globally — does NOT multiply by prefix count."""
    now = datetime(2026, 4, 25, 12, 0, tzinfo=timezone.utc)
    objects = [
        _meta("temp/a/fresh_0.parquet", now=now, age_hours=1),
        _meta("temp/a/fresh_1.parquet", now=now, age_hours=1),
        _meta("temp/b/fresh_0.parquet", now=now, age_hours=1),
        _meta("temp/b/fresh_1.parquet", now=now, age_hours=1),
        _meta("temp/b/expired.parquet", now=now, age_hours=30),
    ]
    storage = FakeStorage(objects=objects)

    warnings_captured: list[str] = []

    def _capture_warning(event: str, **kwargs: Any) -> None:
        warnings_captured.append(f"{event} {kwargs.get('message', '')}")

    monkeypatch.setattr(
        "src.services.storage.temp_cleanup.logger.warning",
        _capture_warning,
    )

    result = await cleanup_temp_uploads(
        pg_session,
        storage,
        prefixes=["temp/a/", "temp/b/"],
        ttl_hours=24,
        max_delete_keys=1000,
        max_list_keys=3,
        now=now,
    )

    assert result.deleted == 0, (
        "List cap must halt listing before expired object reached, "
        f"deleted={result.deleted}"
    )
    assert storage.has_key("temp/b/expired.parquet")
    assert any("global list cap" in w for w in warnings_captured), (
        f"Expected global list cap warning, got: {warnings_captured}"
    )


@pytest.mark.anyio
async def test_referenced_pending_keys_do_not_consume_delete_cap(pg_session) -> None:
    """Cleanup must continue past pending-referenced oldest keys to find
    unreferenced expired ones, until max_delete_keys are deleted.

    Regression: B-starve from FR6 review. With the old post-selection skip,
    cap was consumed by referenced keys, leaving 0 actual deletions even
    when safe expired files existed beyond the locked ones.
    """
    now = datetime(2026, 4, 25, 12, 0, tzinfo=timezone.utc)

    pending_1 = "temp/uploads/a_pending_1.parquet"
    pending_2 = "temp/uploads/b_pending_2.parquet"
    safe_1 = "temp/uploads/c_safe_1.parquet"
    safe_2 = "temp/uploads/d_safe_2.parquet"

    storage = FakeStorage(
        objects=[
            _meta(pending_1, now=now, age_hours=100),
            _meta(pending_2, now=now, age_hours=90),
            _meta(safe_1, now=now, age_hours=80),
            _meta(safe_2, now=now, age_hours=70),
        ],
    )

    await _insert_job(pg_session, key=pending_1, status=JobStatus.QUEUED)
    await _insert_job(pg_session, key=pending_2, status=JobStatus.RUNNING)

    result = await cleanup_temp_uploads(
        pg_session,
        storage,
        prefixes=["temp/uploads/"],
        ttl_hours=24,
        max_delete_keys=2,
        max_list_keys=100,
        now=now,
    )

    assert result.referenced_skipped == 2
    assert result.deleted == 2, (
        f"Expected 2 unreferenced deletions, got {result.deleted}. "
        f"Cleanup starved by referenced oldest."
    )
    assert storage.has_key(pending_1)
    assert storage.has_key(pending_2)
    assert not storage.has_key(safe_1)
    assert not storage.has_key(safe_2)


@pytest.mark.anyio
async def test_oldest_expired_chosen_when_newer_keys_listed_first(pg_session) -> None:
    """Heap must select OLDEST expired even when newer expired arrives first
    in iteration order.

    Regression: F1 from FR6 review. Old condition `if -ts < newest_selected_neg_ts`
    accumulated newest instead of oldest.
    """
    now = datetime(2026, 4, 25, 12, 0, tzinfo=timezone.utc)
    storage = FakeStorage(
        objects=[
            _meta("temp/uploads/a_newer.parquet", now=now, age_hours=25),
            _meta("temp/uploads/b_middle.parquet", now=now, age_hours=50),
            _meta("temp/uploads/z_oldest.parquet", now=now, age_hours=100),
        ],
    )

    result = await cleanup_temp_uploads(
        pg_session,
        storage,
        prefixes=["temp/uploads/"],
        ttl_hours=24,
        max_delete_keys=1,
        max_list_keys=100,
        now=now,
    )

    assert result.deleted == 1
    assert not storage.has_key("temp/uploads/z_oldest.parquet"), (
        "Oldest expired must be deleted when cap=1, regardless of "
        "iteration/lex order."
    )
    assert storage.has_key("temp/uploads/a_newer.parquet")
    assert storage.has_key("temp/uploads/b_middle.parquet")


@pytest.mark.anyio
async def test_end_to_end_upload_then_cleanup_with_pending_job_preserves_input(pg_session) -> None:
    now = datetime(2026, 4, 25, 12, 0, tzinfo=timezone.utc)
    key = "temp/uploads/pipeline.parquet"
    storage = FakeStorage(objects=[_meta(key, now=now, age_hours=30)])

    await _insert_job(pg_session, key=key, status=JobStatus.QUEUED)

    first = await cleanup_temp_uploads(
        pg_session,
        storage,
        prefixes=["temp/uploads/"],
        ttl_hours=24,
        max_delete_keys=1000,
        max_list_keys=50000,
        now=now,
    )
    assert first.deleted == 0
    assert storage.has_key(key)

    job = (
        await pg_session.execute(select(Job).where(Job.status == JobStatus.QUEUED))
    ).scalars().first()
    assert job is not None
    job.status = JobStatus.SUCCESS
    await pg_session.commit()

    second = await cleanup_temp_uploads(
        pg_session,
        storage,
        prefixes=["temp/uploads/"],
        ttl_hours=24,
        max_delete_keys=1000,
        max_list_keys=50000,
        now=now,
    )
    assert second.deleted == 1
    assert not storage.has_key(key)
