"""Phase 3.1aa: scheduler unit tests for ``statcan_metadata_cache_refresh``."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core import scheduler as scheduler_module
from src.core.config import Settings
from src.core.scheduler import (
    get_scheduler,
    scheduled_metadata_cache_refresh,
    shutdown_scheduler,
    start_scheduler,
)
from src.services.statcan.maintenance import StatCanMaintenanceGuard
from src.services.statcan.metadata_cache import RefreshSummary


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


class TestMetadataRefreshWrapperRuntime:
    """Reviewer R3 P1-1: registration tests don't execute the wrapper body, so
    a NameError on ``datetime``/``timezone`` would slip past CI. This guards it.
    """

    @pytest.mark.asyncio
    async def test_wrapper_resolves_runtime_symbols_and_invokes_refresh_all_stale(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        captured: dict = {}

        class _StubService:
            def __init__(self, *, session_factory, client, clock, logger):
                captured["clock"] = clock
                captured["constructed"] = True

            async def refresh_all_stale(self, *, stale_after):
                captured["stale_after"] = stale_after
                return RefreshSummary(refreshed=0, failed=0, skipped=0)

        # Wrapper does a lazy local import — patch at the source module so the
        # stub is what gets imported. Also stub the StatCanClient deps so the
        # wrapper reaches service construction without choking on real
        # constructor signatures (the goal of this test is the lambda body,
        # not the client wiring).
        import src.services.statcan.metadata_cache as metadata_cache_module
        import src.core.rate_limit as rate_limit_module
        import src.services.statcan.client as client_module
        import src.services.statcan.maintenance as maintenance_module

        monkeypatch.setattr(
            metadata_cache_module,
            "StatCanMetadataCacheService",
            _StubService,
            raising=True,
        )
        monkeypatch.setattr(
            rate_limit_module, "AsyncTokenBucket", lambda *a, **kw: MagicMock(), raising=True
        )
        monkeypatch.setattr(
            client_module, "StatCanClient", lambda *a, **kw: MagicMock(), raising=True
        )
        monkeypatch.setattr(
            maintenance_module,
            "StatCanMaintenanceGuard",
            lambda *a, **kw: MagicMock(),
            raising=True,
        )
        # Wrapper reads app.state.http_client; AsyncMock is acceptable here
        # because the stubbed StatCanClient never calls it.
        fake_app = SimpleNamespace(
            state=SimpleNamespace(http_client=AsyncMock())
        )
        monkeypatch.setattr(scheduler_module, "_app_ref", fake_app, raising=False)
        # Avoid touching the real DB engine for session_factory.
        monkeypatch.setattr(
            scheduler_module, "get_session_factory", lambda: MagicMock(), raising=True
        )

        # Must not raise — proves datetime/timezone resolve and the wrapper
        # actually executes through service construction + lambda definition.
        await scheduled_metadata_cache_refresh()

        assert captured.get("constructed") is True
        # The clock lambda is the line most exposed to NameError. Force eval.
        now = captured["clock"]()
        assert now.tzinfo is not None
        assert captured["stale_after"] == timedelta(hours=23)
