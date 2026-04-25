"""Integration tests for temp cleanup safety logic with PostgreSQL."""

from __future__ import annotations

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
    ) -> None:
        self._objects: dict[str, StorageObjectMetadata] = {obj.key: obj for obj in objects}
        self.deleted: list[str] = []
        self.list_calls: list[str] = []
        self.missing_on_delete = set(missing_on_delete or set())

    async def upload_dataframe_as_csv(self, df: Any, path: str) -> None:
        return None

    async def upload_raw(self, data: str | bytes, path: str, content_type: str = "text/html") -> None:
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

    async def list_objects_with_metadata(self, prefix: str) -> list[StorageObjectMetadata]:
        self.list_calls.append(prefix)
        items = sorted(
            (obj for obj in self._objects.values() if obj.key.startswith(prefix)),
            key=lambda obj: obj.key,
        )
        return items

    async def generate_presigned_url(self, path: str, ttl: int = 3600) -> str:
        return ""

    def has_key(self, key: str) -> bool:
        return key in self._objects


def _meta(key: str, *, now: datetime, age_hours: int, size: int = 1) -> StorageObjectMetadata:
    return StorageObjectMetadata(
        key=key,
        size_bytes=size,
        last_modified=now - timedelta(hours=age_hours),
    )


async def _insert_job(pg_session, *, key: str, status: JobStatus, job_type: str = "graphics_generate") -> None:
    payload = {
        "schema_version": 1,
        "data_key": key,
        "chart_type": "line",
        "title": "t",
        "size": [1200, 900],
        "category": "housing",
        "source_product_id": None,
    }
    pg_session.add(
        Job(job_type=job_type, status=status, payload_json=json.dumps(payload))
    )
    await pg_session.commit()


@pytest.mark.anyio
async def test_deletes_old_unreferenced_keys(pg_session) -> None:
    now = datetime(2026, 4, 25, 12, 0, tzinfo=timezone.utc)
    storage = FakeStorage(objects=[_meta(f"temp/uploads/{i}.parquet", now=now, age_hours=30) for i in range(3)])

    result = await cleanup_temp_uploads(pg_session, storage, prefixes=["temp/uploads/"], ttl_hours=24, max_keys=1000, now=now)

    assert result.deleted == 3
    assert result.referenced_skipped == 0


@pytest.mark.anyio
async def test_skips_keys_referenced_by_queued_job(pg_session) -> None:
    now = datetime(2026, 4, 25, 12, 0, tzinfo=timezone.utc)
    keep_key = "temp/uploads/keep.parquet"
    storage = FakeStorage(objects=[_meta(keep_key, now=now, age_hours=30), _meta("temp/uploads/drop1.parquet", now=now, age_hours=30), _meta("temp/uploads/drop2.parquet", now=now, age_hours=30)])
    await _insert_job(pg_session, key=keep_key, status=JobStatus.QUEUED)

    result = await cleanup_temp_uploads(pg_session, storage, prefixes=["temp/uploads/"], ttl_hours=24, max_keys=1000, now=now)

    assert result.deleted == 2
    assert result.referenced_skipped == 1
    assert storage.has_key(keep_key)


@pytest.mark.anyio
async def test_skips_keys_referenced_by_running_job(pg_session) -> None:
    now = datetime(2026, 4, 25, 12, 0, tzinfo=timezone.utc)
    keep_key = "temp/uploads/run.parquet"
    storage = FakeStorage(objects=[_meta(keep_key, now=now, age_hours=30), _meta("temp/uploads/drop.parquet", now=now, age_hours=30)])
    await _insert_job(pg_session, key=keep_key, status=JobStatus.RUNNING)

    result = await cleanup_temp_uploads(pg_session, storage, prefixes=["temp/uploads/"], ttl_hours=24, max_keys=1000, now=now)

    assert result.deleted == 1
    assert result.referenced_skipped == 1


@pytest.mark.anyio
async def test_skips_keys_referenced_by_retrying_job(pg_session) -> None:
    retrying = getattr(JobStatus, "RETRYING", None)
    if retrying is None:
        pytest.skip("JobStatus.RETRYING not implemented in this codebase")

    now = datetime(2026, 4, 25, 12, 0, tzinfo=timezone.utc)
    keep_key = "temp/uploads/retry.parquet"
    storage = FakeStorage(objects=[_meta(keep_key, now=now, age_hours=30), _meta("temp/uploads/drop.parquet", now=now, age_hours=30)])
    await _insert_job(pg_session, key=keep_key, status=retrying)

    result = await cleanup_temp_uploads(pg_session, storage, prefixes=["temp/uploads/"], ttl_hours=24, max_keys=1000, now=now)

    assert result.deleted == 1
    assert result.referenced_skipped == 1


@pytest.mark.anyio
async def test_does_not_skip_keys_referenced_by_completed_job(pg_session) -> None:
    now = datetime(2026, 4, 25, 12, 0, tzinfo=timezone.utc)
    key = "temp/uploads/done.parquet"
    storage = FakeStorage(objects=[_meta(key, now=now, age_hours=30)])
    await _insert_job(pg_session, key=key, status=JobStatus.SUCCESS)

    result = await cleanup_temp_uploads(pg_session, storage, prefixes=["temp/uploads/"], ttl_hours=24, max_keys=1000, now=now)

    assert result.deleted == 1
    assert result.referenced_skipped == 0


@pytest.mark.anyio
async def test_does_not_skip_keys_referenced_by_failed_job(pg_session) -> None:
    now = datetime(2026, 4, 25, 12, 0, tzinfo=timezone.utc)
    key = "temp/uploads/failed.parquet"
    storage = FakeStorage(objects=[_meta(key, now=now, age_hours=30)])
    await _insert_job(pg_session, key=key, status=JobStatus.FAILED)

    result = await cleanup_temp_uploads(pg_session, storage, prefixes=["temp/uploads/"], ttl_hours=24, max_keys=1000, now=now)

    assert result.deleted == 1


@pytest.mark.anyio
async def test_max_keys_caps_expired_candidates_not_raw_listing(pg_session) -> None:
    now = datetime(2026, 4, 25, 12, 0, tzinfo=timezone.utc)
    objects = [_meta(f"temp/uploads/fresh_{i:04d}.parquet", now=now, age_hours=1) for i in range(500)]
    for i in range(1500):
        objects.append(
            StorageObjectMetadata(
                key=f"temp/uploads/old_{i:04d}.parquet",
                size_bytes=1,
                last_modified=now - timedelta(hours=25, minutes=i),
            )
        )
    storage = FakeStorage(objects=objects)

    result = await cleanup_temp_uploads(
        pg_session,
        storage,
        prefixes=["temp/uploads/"],
        ttl_hours=24,
        max_keys=1000,
        now=now,
    )

    assert result.scanned == 1000
    assert result.deleted == 1000
    assert len([k for k in storage._objects if k.startswith("temp/uploads/fresh_")]) == 500
    remaining_expired = [k for k in storage._objects if k.startswith("temp/uploads/old_")]
    assert len(remaining_expired) == 500


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
        max_keys=1000,
        now=now,
    )

    assert result.scanned == 1
    assert result.deleted == 1
    assert not storage.has_key("temp/uploads/zzz_old.parquet")


@pytest.mark.anyio
async def test_cap_hit_logs_warning(pg_session, caplog) -> None:
    now = datetime(2026, 4, 25, 12, 0, tzinfo=timezone.utc)
    storage = FakeStorage(
        objects=[_meta(f"temp/uploads/old_{i:04d}.parquet", now=now, age_hours=30) for i in range(100)]
    )

    with caplog.at_level("WARNING"):
        await cleanup_temp_uploads(
            pg_session,
            storage,
            prefixes=["temp/uploads/"],
            ttl_hours=24,
            max_keys=50,
            now=now,
        )

    assert any(
        "exceed max_keys cap" in record.message
        for record in caplog.records
    )


@pytest.mark.anyio
async def test_idempotent_on_404_delete(pg_session) -> None:
    now = datetime(2026, 4, 25, 12, 0, tzinfo=timezone.utc)
    key = "temp/uploads/missing.parquet"
    storage = FakeStorage(objects=[_meta(key, now=now, age_hours=30)], missing_on_delete={key})

    result = await cleanup_temp_uploads(pg_session, storage, prefixes=["temp/uploads/"], ttl_hours=24, max_keys=1000, now=now)

    assert result.deleted == 1
    assert result.errors == []


@pytest.mark.anyio
async def test_handles_empty_prefix_gracefully(pg_session) -> None:
    now = datetime(2026, 4, 25, 12, 0, tzinfo=timezone.utc)
    storage = FakeStorage(objects=[])

    result = await cleanup_temp_uploads(pg_session, storage, prefixes=["temp/uploads/"], ttl_hours=24, max_keys=1000, now=now)

    assert result.scanned == 0
    assert result.deleted == 0
    assert result.referenced_skipped == 0


@pytest.mark.anyio
async def test_multiple_prefixes_processed_in_order(pg_session) -> None:
    now = datetime(2026, 4, 25, 12, 0, tzinfo=timezone.utc)
    storage = FakeStorage(objects=[_meta("temp/uploads/a.parquet", now=now, age_hours=30), _meta("temp/staging/b.parquet", now=now, age_hours=30)])

    result = await cleanup_temp_uploads(pg_session, storage, prefixes=["temp/uploads/", "temp/staging/"], ttl_hours=24, max_keys=1000, now=now)

    assert result.deleted == 2
    assert storage.list_calls == ["temp/uploads/", "temp/staging/"]


@pytest.mark.anyio
async def test_end_to_end_upload_then_cleanup_with_pending_job_preserves_input(pg_session) -> None:
    now = datetime(2026, 4, 25, 12, 0, tzinfo=timezone.utc)
    key = "temp/uploads/pipeline.parquet"
    storage = FakeStorage(objects=[_meta(key, now=now, age_hours=30)])

    await _insert_job(pg_session, key=key, status=JobStatus.QUEUED)

    first = await cleanup_temp_uploads(pg_session, storage, prefixes=["temp/uploads/"], ttl_hours=24, max_keys=1000, now=now)
    assert first.deleted == 0
    assert storage.has_key(key)

    job = (
        await pg_session.execute(select(Job).where(Job.status == JobStatus.QUEUED))
    ).scalars().first()
    assert job is not None
    job.status = JobStatus.SUCCESS
    await pg_session.commit()

    second = await cleanup_temp_uploads(pg_session, storage, prefixes=["temp/uploads/"], ttl_hours=24, max_keys=1000, now=now)
    assert second.deleted == 1
    assert not storage.has_key(key)
