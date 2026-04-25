"""Cleanup for temporary uploaded Parquet objects."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.config import Settings
from src.core.storage import StorageInterface
from src.models.job import Job, JobStatus
from src.services.storage.temp_payload_inspector import extract_graphics_generate_data_key

logger = structlog.get_logger(__name__)


@dataclass
class CleanupResult:
    """Outcome of a temp upload cleanup run."""

    scanned: int = 0
    referenced_skipped: int = 0
    deleted: int = 0
    bytes_freed: int = 0
    errors: list[str] = field(default_factory=list)


async def collect_keys_referenced_by_pending_jobs(
    session: AsyncSession,
    *,
    candidates: set[str],
) -> set[str]:
    """Collect candidate keys still referenced by active graphics jobs."""
    if not candidates:
        return set()

    pending_statuses: list[JobStatus] = [JobStatus.QUEUED, JobStatus.RUNNING]
    retrying = getattr(JobStatus, "RETRYING", None)
    if retrying is not None:
        pending_statuses.append(retrying)
    stmt = select(Job.payload_json).where(
        Job.job_type == "graphics_generate",
        Job.status.in_(pending_statuses),
    )
    rows = (await session.execute(stmt)).scalars().all()

    referenced: set[str] = set()
    for payload_json in rows:
        data_key = extract_graphics_generate_data_key(payload_json)
        if data_key in candidates:
            referenced.add(data_key)
    return referenced


async def cleanup_temp_uploads(
    session: AsyncSession,
    storage: StorageInterface,
    *,
    prefixes: Sequence[str],
    ttl_hours: int,
    max_keys: int,
    now: datetime | None = None,
) -> CleanupResult:
    """Delete expired objects not referenced by pending jobs.

    ``max_keys`` applies to the expired candidate set (oldest first), not
    the raw storage listing. Storage listings are key-ordered, so capping
    raw listing size can hide expired keys behind fresh keys that sort
    earlier lexicographically.
    """
    result = CleanupResult()
    current_time = now or datetime.now(timezone.utc)
    cutoff = current_time - timedelta(hours=ttl_hours)

    candidates_by_key: dict[str, tuple[str, int]] = {}

    for prefix in prefixes:
        try:
            objects = await storage.list_objects_with_metadata(prefix)
        except Exception as exc:  # noqa: BLE001
            result.errors.append(f"list({prefix}): {exc}")
            continue

        expired = [obj for obj in objects if obj.last_modified <= cutoff]
        expired.sort(key=lambda item: item.last_modified)

        if len(expired) > max_keys:
            logger.warning(
                "temp_uploads.cleanup.expired_candidates_exceed_max_keys_cap",
                prefix=prefix,
                expired_candidates=len(expired),
                max_keys=max_keys,
                message=(
                    "expired candidates exceed max_keys cap; processing oldest "
                    "subset this cycle"
                ),
            )
            expired = expired[:max_keys]

        for obj in expired:
            candidates_by_key.setdefault(obj.key, (prefix, obj.size_bytes))

    if not candidates_by_key:
        logger.info(
            "temp_uploads.cleanup.done",
            scanned=0,
            referenced_skipped=0,
            deleted=0,
            bytes_freed=0,
            errors=len(result.errors),
        )
        return result

    result.scanned = len(candidates_by_key)
    candidate_keys = set(candidates_by_key.keys())
    referenced = await collect_keys_referenced_by_pending_jobs(
        session,
        candidates=candidate_keys,
    )

    deletable = sorted(candidate_keys - referenced)
    result.referenced_skipped = len(referenced)

    for key in deletable:
        size_bytes = candidates_by_key[key][1]
        try:
            await storage.delete_object(key)
        except FileNotFoundError:
            result.deleted += 1
            result.bytes_freed += size_bytes
            continue
        except Exception as exc:  # noqa: BLE001
            result.errors.append(f"{key}: {exc}")
            continue

        result.deleted += 1
        result.bytes_freed += size_bytes

    logger.info(
        "temp_uploads.cleanup.done",
        scanned=result.scanned,
        referenced_skipped=result.referenced_skipped,
        deleted=result.deleted,
        bytes_freed=result.bytes_freed,
        errors=len(result.errors),
    )
    return result


class TempUploadCleaner:
    """Delete expired objects from configured temp prefixes."""

    def __init__(
        self,
        storage: StorageInterface,
        settings: Settings,
        session_factory: async_sessionmaker[AsyncSession],
        clock: Callable[[], datetime],
    ) -> None:
        self._storage = storage
        self._settings = settings
        self._session_factory = session_factory
        self._clock = clock

    async def run_once(self) -> CleanupResult:
        """Delete objects at or beyond the configured TTL."""
        async with self._session_factory() as session:
            return await cleanup_temp_uploads(
                session,
                self._storage,
                prefixes=self._settings.temp_cleanup_prefixes,
                ttl_hours=self._settings.temp_upload_ttl_hours,
                max_keys=self._settings.temp_cleanup_max_keys_per_cycle,
                now=self._clock(),
            )
