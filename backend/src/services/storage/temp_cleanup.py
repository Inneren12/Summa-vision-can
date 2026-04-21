"""Cleanup for temporary uploaded Parquet objects."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import structlog

from src.core.config import Settings
from src.core.storage import StorageInterface

logger = structlog.get_logger(__name__)


@dataclass
class CleanupResult:
    """Outcome of a temp upload cleanup run."""

    scanned: int = 0
    deleted: int = 0
    bytes_freed: int = 0
    errors: list[str] = field(default_factory=list)


class TempUploadCleaner:
    """Delete expired objects from ``temp/uploads/``."""

    def __init__(
        self,
        storage: StorageInterface,
        settings: Settings,
        clock: Callable[[], datetime],
    ) -> None:
        self._storage = storage
        self._settings = settings
        self._clock = clock

    async def run_once(self) -> CleanupResult:
        """Delete objects at or beyond the configured TTL."""
        result = CleanupResult()
        ttl = timedelta(hours=self._settings.temp_upload_ttl_hours)
        now = self._clock()

        try:
            objects = await self._storage.list_objects_with_metadata("temp/uploads/")
        except Exception as exc:  # noqa: BLE001
            result.errors.append(str(exc))
            logger.info(
                "temp_uploads.cleanup.done",
                scanned=result.scanned,
                deleted=result.deleted,
                bytes_freed=result.bytes_freed,
                errors=len(result.errors),
            )
            return result

        result.scanned = len(objects)

        for obj in objects:
            age = now - obj.last_modified
            if age < ttl:
                continue

            try:
                await self._storage.delete_object(obj.key)
            except Exception as exc:  # noqa: BLE001
                result.errors.append(f"{obj.key}: {exc}")
                continue

            result.deleted += 1
            result.bytes_freed += obj.size_bytes

        logger.info(
            "temp_uploads.cleanup.done",
            scanned=result.scanned,
            deleted=result.deleted,
            bytes_freed=result.bytes_freed,
            errors=len(result.errors),
        )
        return result
