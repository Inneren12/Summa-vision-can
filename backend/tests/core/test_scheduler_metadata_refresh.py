"""Phase 3.1aa: scheduler unit tests for ``statcan_metadata_cache_refresh``."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from src.core.config import Settings
from src.core.scheduler import (
    get_scheduler,
    shutdown_scheduler,
    start_scheduler,
)
from src.services.statcan.maintenance import StatCanMaintenanceGuard


def _settings() -> Settings:
    return Settings(  # type: ignore[arg-type]
        scheduler_db_url="sqlite://",
        scheduler_enabled=True,
        admin_api_key="test-key",
    )


class TestMetadataRefreshSchedulerJob:
    def teardown_method(self) -> None:
        shutdown_scheduler()

    @pytest.mark.asyncio
    async def test_metadata_refresh_job_registers_with_correct_id_and_cron(
        self,
    ) -> None:
        start_scheduler(_settings())
        scheduler = get_scheduler()
        assert scheduler is not None

        job = scheduler.get_job("statcan_metadata_cache_refresh")
        assert job is not None
        assert job.name == "StatCan metadata cache nightly refresh"
        assert job.coalesce is True
        assert job.max_instances == 1
        assert job.misfire_grace_time == 3600

        # Verify the cron trigger is configured to fire at 15:00 UTC.
        trigger = job.trigger
        tz = str(trigger.timezone)
        assert "UTC" in tz

        hour_field = next(f for f in trigger.fields if f.name == "hour")
        minute_field = next(f for f in trigger.fields if f.name == "minute")
        assert "15" in str(hour_field)
        assert "0" in str(minute_field)

    @pytest.mark.asyncio
    async def test_metadata_refresh_cron_does_not_overlap_maintenance_window(
        self,
    ) -> None:
        start_scheduler(_settings())
        scheduler = get_scheduler()
        assert scheduler is not None
        job = scheduler.get_job("statcan_metadata_cache_refresh")
        assert job is not None

        guard = StatCanMaintenanceGuard()

        # Sample dates spanning DST transitions (Mar/Nov 2026) plus a few
        # ordinary dates. For each, ask the trigger when it would fire next
        # and assert the resulting instant is outside the 00:00–08:30 EST
        # maintenance window.
        sample_anchors = [
            datetime(2026, 1, 15, 0, 0, tzinfo=timezone.utc),
            datetime(2026, 3, 7, 0, 0, tzinfo=timezone.utc),  # before DST
            datetime(2026, 3, 8, 0, 0, tzinfo=timezone.utc),  # DST start (US)
            datetime(2026, 3, 9, 0, 0, tzinfo=timezone.utc),
            datetime(2026, 7, 1, 0, 0, tzinfo=timezone.utc),
            datetime(2026, 11, 1, 0, 0, tzinfo=timezone.utc),  # DST end (US)
            datetime(2026, 11, 2, 0, 0, tzinfo=timezone.utc),
            datetime(2026, 12, 31, 0, 0, tzinfo=timezone.utc),
        ]
        for anchor in sample_anchors:
            fire_time = job.trigger.get_next_fire_time(None, anchor - timedelta(seconds=1))
            assert fire_time is not None
            assert not guard.is_maintenance_window(fire_time), (
                f"15:00 UTC fire at {fire_time.isoformat()} fell inside maintenance window"
            )
