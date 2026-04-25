"""Unit tests for temp upload cleanup."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.storage import StorageInterface, StorageObjectMetadata
from src.services.storage.temp_cleanup import CleanupResult, TempUploadCleaner, cleanup_temp_uploads


class FakeStorage(StorageInterface):
    def __init__(
        self,
        objects: list[StorageObjectMetadata] | None = None,
        delete_missing: set[str] | None = None,
    ) -> None:
        self.objects = list(objects or [])
        self.delete_missing = set(delete_missing or set())
        self._delete_errors: dict[str, BaseException] = {}
        self.deleted_keys: list[str] = []

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

    def set_delete_to_raise(self, key: str, exc: BaseException) -> None:
        self._delete_errors[key] = exc

    async def delete_object(self, key: str) -> None:
        if key in self.delete_missing:
            raise FileNotFoundError(key)
        if key in self._delete_errors:
            raise self._delete_errors[key]
        self.deleted_keys.append(key)

    async def list_objects(self, prefix: str) -> list[str]:
        return [obj.key for obj in self.objects if obj.key.startswith(prefix)]

    async def list_objects_with_metadata(self, prefix: str, max_keys: int | None = None) -> list[StorageObjectMetadata]:
        return [obj for obj in self.objects if obj.key.startswith(prefix)]

    async def generate_presigned_url(self, path: str, ttl: int = 3600) -> str:
        return ""


def _obj(key: str, age_hours: int, *, now: datetime, size: int = 10) -> StorageObjectMetadata:
    return StorageObjectMetadata(
        key=key,
        size_bytes=size,
        last_modified=now - timedelta(hours=age_hours),
    )


@pytest.mark.anyio
async def test_cleanup_deletes_only_expired_unreferenced_keys() -> None:
    now = datetime(2026, 4, 25, 10, 0, tzinfo=timezone.utc)
    storage = FakeStorage(
        [
            _obj("temp/uploads/a.parquet", 30, now=now),
            _obj("temp/uploads/fresh.parquet", 2, now=now),
        ]
    )
    session = AsyncMock()
    execute_result = MagicMock()
    execute_result.scalars.return_value.all.return_value = []
    session.execute.return_value = execute_result

    result = await cleanup_temp_uploads(
        session,
        storage,
        prefixes=["temp/uploads/"],
        ttl_hours=24,
        max_keys=1000,
        now=now,
    )

    assert result == CleanupResult(scanned=1, referenced_skipped=0, deleted=1, bytes_freed=10, errors=[])
    assert storage.deleted_keys == ["temp/uploads/a.parquet"]


@pytest.mark.anyio
async def test_cleanup_treats_404_delete_as_success() -> None:
    now = datetime(2026, 4, 25, 10, 0, tzinfo=timezone.utc)
    key = "temp/uploads/missing.parquet"
    storage = FakeStorage([_obj(key, 30, now=now)], delete_missing={key})
    session = AsyncMock()
    execute_result = MagicMock()
    execute_result.scalars.return_value.all.return_value = []
    session.execute.return_value = execute_result

    result = await cleanup_temp_uploads(
        session,
        storage,
        prefixes=["temp/uploads/"],
        ttl_hours=24,
        max_keys=1000,
        now=now,
    )

    assert result.deleted == 1
    assert result.errors == []


@pytest.mark.anyio
async def test_cleaner_uses_short_lived_session_factory() -> None:
    now = datetime(2026, 4, 25, 10, 0, tzinfo=timezone.utc)
    storage = FakeStorage()

    class SessionCtx:
        def __init__(self) -> None:
            self.session = AsyncMock()
            execute_result = MagicMock()
            execute_result.scalars.return_value.all.return_value = []
            self.session.execute = AsyncMock(return_value=execute_result)
            self.entered = False
            self.exited = False

        async def __aenter__(self):
            self.entered = True
            return self.session

        async def __aexit__(self, exc_type, exc, tb):
            self.exited = True
            return False

    ctx = SessionCtx()
    def session_factory():
        return ctx

    settings = type(
        "SettingsObj",
        (),
        {
            "temp_cleanup_prefixes": ["temp/uploads/"],
            "temp_upload_ttl_hours": 24,
            "temp_cleanup_max_keys_per_cycle": 1000,
        },
    )()

    cleaner = TempUploadCleaner(storage, settings, session_factory=session_factory, clock=lambda: now)

    result = await cleaner.run_once()

    assert result == CleanupResult(scanned=0, referenced_skipped=0, deleted=0, bytes_freed=0, errors=[])
    assert ctx.entered is True
    assert ctx.exited is True


@pytest.mark.anyio
async def test_delete_error_is_non_fatal_and_continues() -> None:
    """One delete failure must not abort the rest of the cycle."""
    now = datetime(2026, 4, 25, 10, 0, tzinfo=timezone.utc)
    storage = FakeStorage(
        [
            _obj("temp/uploads/a.parquet", 30, now=now),
            _obj("temp/uploads/b.parquet", 30, now=now),
        ]
    )
    storage.set_delete_to_raise("temp/uploads/a.parquet", RuntimeError("network blip"))

    session = AsyncMock()
    execute_result = MagicMock()
    execute_result.scalars.return_value.all.return_value = []
    session.execute.return_value = execute_result

    result = await cleanup_temp_uploads(
        session,
        storage,
        prefixes=["temp/uploads/"],
        ttl_hours=24,
        max_keys=100,
        now=now,
    )

    assert result.deleted == 1
    assert len(result.errors) == 1
    assert "temp/uploads/a.parquet" in result.errors[0]
    assert "network blip" in result.errors[0]
    assert storage.deleted_keys == ["temp/uploads/b.parquet"]
