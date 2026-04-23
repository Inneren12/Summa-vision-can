"""Unit tests for temp upload cleanup."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import patch

import pytest

from src.core.config import Settings
from src.core.storage import StorageInterface, StorageObjectMetadata
from src.services.storage.temp_cleanup import CleanupResult, TempUploadCleaner


class FakeStorage(StorageInterface):
    """Storage fake for exercising temp upload cleanup logic."""

    def __init__(
        self,
        objects: list[StorageObjectMetadata] | None = None,
        delete_failures: set[str] | None = None,
    ) -> None:
        self.objects = list(objects or [])
        self.delete_failures = set(delete_failures or set())
        self.deleted_keys: list[str] = []

    async def upload_dataframe_as_csv(self, df: Any, path: str) -> None:
        return None

    async def upload_raw(
        self, data: str | bytes, path: str, content_type: str = "text/html"
    ) -> None:
        return None

    async def upload_bytes(self, data: bytes, key: str) -> None:
        return None

    async def download_bytes(self, key: str) -> bytes:
        return b""

    async def download_csv(self, path: str) -> Any:
        return None

    async def delete_object(self, key: str) -> None:
        if key in self.delete_failures:
            raise RuntimeError(f"delete failed for {key}")
        self.deleted_keys.append(key)

    async def list_objects(self, prefix: str) -> list[str]:
        return [obj.key for obj in self.objects if obj.key.startswith(prefix)]

    async def list_objects_with_metadata(
        self, prefix: str
    ) -> list[StorageObjectMetadata]:
        return [obj for obj in self.objects if obj.key.startswith(prefix)]

    async def generate_presigned_url(self, path: str, ttl: int = 3600) -> str:
        return f"mock://{path}?ttl={ttl}"


@pytest.fixture
def fixed_now() -> datetime:
    """Deterministic UTC timestamp for cleanup tests."""
    return datetime(2026, 4, 21, 12, 0, 0, tzinfo=timezone.utc)


def _make_settings(**overrides: object) -> Settings:
    defaults = {
        "admin_api_key": "test-key",
        "temp_upload_ttl_hours": 24,
        "temp_upload_cleanup_interval_minutes": 60,
    }
    defaults.update(overrides)
    return Settings(**defaults)  # type: ignore[arg-type]


def _make_object(
    *,
    key: str,
    size_bytes: int,
    last_modified: datetime,
) -> StorageObjectMetadata:
    return StorageObjectMetadata(
        key=key,
        size_bytes=size_bytes,
        last_modified=last_modified,
    )


@pytest.mark.asyncio
async def test_expired_object_deleted(fixed_now: datetime) -> None:
    storage = FakeStorage(
        [
            _make_object(
                key="temp/uploads/expired.parquet",
                size_bytes=128,
                last_modified=fixed_now - timedelta(hours=25),
            )
        ]
    )
    cleaner = TempUploadCleaner(storage, _make_settings(), clock=lambda: fixed_now)

    result = await cleaner.run_once()

    assert result.deleted == 1
    assert result.scanned == 1
    assert result.bytes_freed == 128
    assert storage.deleted_keys == ["temp/uploads/expired.parquet"]


@pytest.mark.asyncio
async def test_fresh_object_kept(fixed_now: datetime) -> None:
    storage = FakeStorage(
        [
            _make_object(
                key="temp/uploads/fresh.parquet",
                size_bytes=64,
                last_modified=fixed_now - timedelta(hours=1),
            )
        ]
    )
    cleaner = TempUploadCleaner(storage, _make_settings(), clock=lambda: fixed_now)

    result = await cleaner.run_once()

    assert result == CleanupResult(scanned=1, deleted=0, bytes_freed=0, errors=[])
    assert storage.deleted_keys == []


@pytest.mark.asyncio
async def test_boundary_object_deleted_at_exact_ttl(fixed_now: datetime) -> None:
    storage = FakeStorage(
        [
            _make_object(
                key="temp/uploads/boundary.parquet",
                size_bytes=32,
                last_modified=fixed_now - timedelta(hours=24),
            )
        ]
    )
    cleaner = TempUploadCleaner(storage, _make_settings(), clock=lambda: fixed_now)

    result = await cleaner.run_once()

    assert result.deleted == 1
    assert storage.deleted_keys == ["temp/uploads/boundary.parquet"]


@pytest.mark.asyncio
async def test_empty_prefix_returns_empty_result(fixed_now: datetime) -> None:
    storage = FakeStorage()
    cleaner = TempUploadCleaner(storage, _make_settings(), clock=lambda: fixed_now)

    result = await cleaner.run_once()

    assert result == CleanupResult(scanned=0, deleted=0, bytes_freed=0, errors=[])


@pytest.mark.asyncio
async def test_delete_error_is_non_fatal(fixed_now: datetime) -> None:
    storage = FakeStorage(
        [
            _make_object(
                key="temp/uploads/fail.parquet",
                size_bytes=12,
                last_modified=fixed_now - timedelta(hours=30),
            ),
            _make_object(
                key="temp/uploads/ok.parquet",
                size_bytes=20,
                last_modified=fixed_now - timedelta(hours=26),
            ),
        ],
        delete_failures={"temp/uploads/fail.parquet"},
    )
    cleaner = TempUploadCleaner(storage, _make_settings(), clock=lambda: fixed_now)

    result = await cleaner.run_once()

    assert result.deleted == 1
    assert result.scanned == 2
    assert result.bytes_freed == 20
    assert len(result.errors) == 1
    assert "temp/uploads/fail.parquet" in result.errors[0]
    assert storage.deleted_keys == ["temp/uploads/ok.parquet"]


@pytest.mark.asyncio
async def test_clock_is_injected_and_logger_emits_single_summary(
    fixed_now: datetime,
) -> None:
    storage = FakeStorage(
        [
            _make_object(
                key="temp/uploads/expired.parquet",
                size_bytes=99,
                last_modified=fixed_now - timedelta(hours=48),
            )
        ]
    )
    cleaner = TempUploadCleaner(storage, _make_settings(), clock=lambda: fixed_now)

    with patch("src.services.storage.temp_cleanup.logger.info") as mock_info:
        result = await cleaner.run_once()

    assert result.deleted == 1
    mock_info.assert_called_once_with(
        "temp_uploads.cleanup.done",
        scanned=1,
        deleted=1,
        bytes_freed=99,
        errors=0,
    )
