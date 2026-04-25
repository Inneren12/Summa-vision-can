"""Cleanup for temporary uploaded Parquet objects."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import heapq

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
    max_delete_keys: int,
    max_list_keys: int,
    now: datetime | None = None,
) -> CleanupResult:
    """Delete expired objects not referenced by pending jobs.

    Cleanup enforces two caps:
    - ``max_list_keys`` bounds listed-object scan work per cycle.
    - ``max_delete_keys`` bounds delete work, prioritizing oldest expired
      candidates first across paginated listing pages.
    """
    result = CleanupResult()
    current_time = now or datetime.now(timezone.utc)
    cutoff = current_time - timedelta(hours=ttl_hours)

    oldest_expired: list[tuple[float, str, int, str]] = []
    listed_total = 0
    expired_seen_total = 0
    global_list_cap_hit = False
    list_cap_hit_prefixes: list[str] = []

    for prefix in prefixes:
        if global_list_cap_hit:
            break

        prefix_list_cap_hit = False
        try:
            async for page in storage.iter_objects_with_metadata(prefix):
                for obj in page:
                    if listed_total >= max_list_keys:
                        global_list_cap_hit = True
                        prefix_list_cap_hit = True
                        break
                    listed_total += 1

                    if obj.last_modified > cutoff:
                        continue

                    expired_seen_total += 1
                    if max_delete_keys <= 0:
                        continue

                    ts = obj.last_modified.timestamp()
                    entry = (-ts, obj.key, obj.size_bytes, prefix)
                    if len(oldest_expired) < max_delete_keys:
                        heapq.heappush(oldest_expired, entry)
                    else:
                        newest_selected_neg_ts = oldest_expired[0][0]
                        if -ts < newest_selected_neg_ts:
                            heapq.heapreplace(oldest_expired, entry)

                if prefix_list_cap_hit:
                    break
        except Exception as exc:  # noqa: BLE001
            result.errors.append(f"list({prefix}): {exc}")
            continue

        if prefix_list_cap_hit:
            list_cap_hit_prefixes.append(prefix)

    if global_list_cap_hit:
        logger.warning(
            "temp_uploads.cleanup.global_list_cap_reached",
            max_list_keys=max_list_keys,
            prefixes=list_cap_hit_prefixes,
            message=(
                "global list cap reached; listing stopped before scanning all "
                "prefixes this cycle"
            ),
        )

    if max_delete_keys > 0 and expired_seen_total > max_delete_keys:
        logger.warning(
            "temp_uploads.cleanup.global_delete_cap_reached",
            expired_seen_total=expired_seen_total,
            max_delete_keys=max_delete_keys,
            message=(
                "expired candidates seen exceed delete cap; processing oldest "
                "across all prefixes and deferring the remainder"
            ),
        )

    selected = sorted(
        [(-neg_ts, key, size_bytes, prefix) for neg_ts, key, size_bytes, prefix in oldest_expired],
    )
    candidates_by_key = {
        key: (prefix, size_bytes)
        for _ts, key, size_bytes, prefix in selected
    }

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
                max_delete_keys=self._settings.temp_cleanup_max_delete_keys_per_cycle,
                max_list_keys=self._settings.temp_cleanup_max_list_keys_per_cycle,
                now=self._clock(),
            )
