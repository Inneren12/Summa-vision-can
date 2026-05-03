"""Phase 3.1aaa: scheduler tests for ``statcan_value_cache_refresh``."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core import scheduler as scheduler_module
from src.core.config import Settings
from src.core.scheduler import (
    get_scheduler,
    scheduled_value_cache_refresh,
    shutdown_scheduler,
    start_scheduler,
)
from src.services.statcan.value_cache_schemas import RefreshSummary


def _settings() -> Settings:
    return Settings(  # type: ignore[arg-type]
        scheduler_db_url="sqlite://",
        scheduler_enabled=True,
        admin_api_key="test-key",
    )


class TestValueCacheRefreshSchedulerJob:
    def teardown_method(self) -> None:
        shutdown_scheduler()

    @pytest.mark.asyncio
    async def test_job_registered_with_correct_cron_and_flags(self) -> None:
        start_scheduler(_settings())
        scheduler = get_scheduler()
        assert scheduler is not None

        job = scheduler.get_job("statcan_value_cache_refresh")
        assert job is not None
        assert job.name == "StatCan value cache nightly refresh"
        assert job.coalesce is True
        assert job.max_instances == 1
        assert job.misfire_grace_time == 3600
        trigger = job.trigger
        assert "UTC" in str(trigger.timezone)
        hour_field = next(f for f in trigger.fields if f.name == "hour")
        assert "16" in str(hour_field)

    @pytest.mark.asyncio
    async def test_wrapper_invokes_refresh_all(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        captured: dict = {}

        class _StubService:
            def __init__(self, **kwargs):
                captured.update(kwargs)

            async def refresh_all(self):
                captured["refresh_called"] = True
                return RefreshSummary(
                    mappings_processed=0,
                    rows_upserted=0,
                    rows_marked_stale=0,
                    errors=[],
                )

        import src.services.statcan.value_cache as vc_module
        import src.services.statcan.metadata_cache as mc_module
        import src.core.rate_limit as rate_limit_module
        import src.services.statcan.client as client_module
        import src.services.statcan.maintenance as maintenance_module

        monkeypatch.setattr(
            vc_module, "StatCanValueCacheService", _StubService, raising=True
        )
        monkeypatch.setattr(
            mc_module,
            "StatCanMetadataCacheService",
            lambda *a, **kw: MagicMock(),
            raising=True,
        )
        monkeypatch.setattr(
            rate_limit_module,
            "AsyncTokenBucket",
            lambda *a, **kw: MagicMock(),
            raising=True,
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
        fake_app = SimpleNamespace(state=SimpleNamespace(http_client=AsyncMock()))
        monkeypatch.setattr(scheduler_module, "_app_ref", fake_app, raising=False)
        monkeypatch.setattr(
            scheduler_module, "get_session_factory", lambda: MagicMock(), raising=True
        )

        await scheduled_value_cache_refresh()
        assert captured.get("refresh_called") is True

    @pytest.mark.asyncio
    async def test_wrapper_swallows_inner_exceptions(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Force a hard failure inside the lazy import path; wrapper must
        # log + return without raising.
        monkeypatch.setattr(scheduler_module, "_app_ref", None, raising=False)
        # Should not raise.
        await scheduled_value_cache_refresh()
