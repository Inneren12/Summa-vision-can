"""Unit tests for the persistent job scheduler (``src.core.scheduler``).

Tests verify:
- Scheduler starts and registers jobs when ``scheduler_enabled=True``.
- Scheduler does NOT start when ``scheduler_enabled=False``.
- ``scheduled_fetch_todays_releases`` calls the service and logs on success.
- ``scheduled_fetch_todays_releases`` catches exceptions and logs errors.
- ``shutdown_scheduler`` cleanly stops the scheduler.
- The CRON job is configured correctly (Mon–Fri, 09:00 EST).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.config import Settings
from src.core.scheduler import (
    _create_scheduler,
    get_scheduler,
    scheduled_audit_cleanup,
    scheduled_fetch_todays_releases,
    shutdown_scheduler,
    start_scheduler,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_settings(**overrides: object) -> Settings:
    """Build a ``Settings`` instance with scheduler defaults for tests.

    Uses an in-memory SQLite so no file is created on disk.
    """
    defaults = {
        "scheduler_db_url": "sqlite://",  # in-memory
        "scheduler_enabled": True,
        "admin_api_key": "test-key",
    }
    defaults.update(overrides)
    return Settings(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# _create_scheduler
# ---------------------------------------------------------------------------


class TestCreateScheduler:
    """Tests for the scheduler factory function."""

    def test_creates_scheduler_with_jobstore(self) -> None:
        """The factory should return a scheduler with an SQLAlchemy job store."""
        settings = _make_settings()
        scheduler = _create_scheduler(settings)
        assert scheduler is not None
        assert "default" in scheduler._jobstores  # noqa: SLF001

    def test_scheduler_is_not_running(self) -> None:
        """Newly created scheduler should not be running yet."""
        settings = _make_settings()
        scheduler = _create_scheduler(settings)
        assert not scheduler.running


# ---------------------------------------------------------------------------
# start_scheduler / shutdown_scheduler
# ---------------------------------------------------------------------------


class TestStartShutdown:
    """Tests for the scheduler lifecycle functions.

    These tests must be ``async`` because ``AsyncIOScheduler.start()``
    requires a running event loop.
    """

    def teardown_method(self) -> None:
        """Ensure the module-level singleton is cleaned up."""
        shutdown_scheduler()

    @pytest.mark.asyncio
    async def test_start_registers_cron_job(self) -> None:
        """Starting the scheduler should register the cron jobs."""
        settings = _make_settings()
        start_scheduler(settings)

        scheduler = get_scheduler()
        assert scheduler is not None
        assert scheduler.running

        jobs = scheduler.get_jobs()
        assert len(jobs) == 2

        job_ids = {j.id for j in jobs}
        assert "fetch_todays_releases" in job_ids
        assert "audit_cleanup" in job_ids

        fetch_job = scheduler.get_job("fetch_todays_releases")
        assert fetch_job is not None
        assert fetch_job.name == "Fetch today's StatCan releases"

        audit_job = scheduler.get_job("audit_cleanup")
        assert audit_job is not None
        assert audit_job.name == "Delete expired audit events"

    @pytest.mark.asyncio
    async def test_cron_job_timezone_is_eastern(self) -> None:
        """The fetch CRON trigger must use US/Eastern timezone."""
        settings = _make_settings()
        start_scheduler(settings)

        scheduler = get_scheduler()
        assert scheduler is not None
        job = scheduler.get_job("fetch_todays_releases")
        assert job is not None
        trigger = job.trigger
        tz = str(trigger.timezone)
        assert "Eastern" in tz or "US/Eastern" in tz

    @pytest.mark.asyncio
    async def test_cron_runs_on_weekdays_only(self) -> None:
        """The fetch job must be configured for Monday through Friday."""
        settings = _make_settings()
        start_scheduler(settings)

        scheduler = get_scheduler()
        assert scheduler is not None
        job = scheduler.get_job("fetch_todays_releases")
        assert job is not None
        trigger = job.trigger

        # APScheduler stores day_of_week fields — verify mon-fri (0-4)
        dow_field = trigger.fields[4]  # day_of_week is index 4
        expr_str = str(dow_field)
        assert "mon" in expr_str or "0-4" in expr_str

    @pytest.mark.asyncio
    async def test_disabled_scheduler_does_not_start(self) -> None:
        """When ``scheduler_enabled=False``, no scheduler is created."""
        settings = _make_settings(scheduler_enabled=False)
        start_scheduler(settings)

        scheduler = get_scheduler()
        assert scheduler is None

    @pytest.mark.asyncio
    async def test_shutdown_stops_running_scheduler(self) -> None:
        """Shutting down a running scheduler should stop it."""
        settings = _make_settings()
        start_scheduler(settings)

        scheduler = get_scheduler()
        assert scheduler is not None
        assert scheduler.running

        shutdown_scheduler()
        assert get_scheduler() is None

    @pytest.mark.asyncio
    async def test_shutdown_noop_when_none(self) -> None:
        """Shutting down when there is no scheduler should not raise."""
        shutdown_scheduler()  # should be a no-op
        assert get_scheduler() is None

    @pytest.mark.asyncio
    async def test_replace_existing_prevents_duplicates(self) -> None:
        """Calling start_scheduler twice should not duplicate jobs."""
        settings = _make_settings()
        start_scheduler(settings)
        # Shut down and restart — the job store might still have the old entry
        shutdown_scheduler()
        start_scheduler(settings)

        scheduler = get_scheduler()
        assert scheduler is not None
        jobs = scheduler.get_jobs()
        assert len(jobs) == 2  # fetch_todays_releases + audit_cleanup


# ---------------------------------------------------------------------------
# scheduled_fetch_todays_releases
# ---------------------------------------------------------------------------


class TestScheduledFetchTodaysReleases:
    """Tests for the scheduled job wrapper function."""

    @pytest.mark.asyncio
    async def test_success_path(self) -> None:
        """On success, the job should call ``fetch_todays_releases``."""
        mock_service_instance = MagicMock()
        mock_service_instance.fetch_todays_releases = AsyncMock(return_value=[])

        mock_http_client = AsyncMock()

        # Provide app reference with http_client (ARCH-DPEN-001)
        mock_app = MagicMock()
        mock_app.state.http_client = mock_http_client

        with (
            patch("src.core.scheduler._app_ref", mock_app),
            patch(
                "src.services.statcan.service.StatCanETLService",
                return_value=mock_service_instance,
            ),
            patch("src.services.statcan.client.StatCanClient"),
            patch("src.services.statcan.maintenance.StatCanMaintenanceGuard"),
            patch("src.core.rate_limit.AsyncTokenBucket"),
        ):
            await scheduled_fetch_todays_releases()

            mock_service_instance.fetch_todays_releases.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_exception_is_caught_and_logged(self) -> None:
        """A failing job must NOT propagate the exception."""
        with patch("httpx.AsyncClient", side_effect=RuntimeError("network down")):
            # Should not raise — the broad except catches it.
            await scheduled_fetch_todays_releases()

    @pytest.mark.asyncio
    async def test_service_error_is_caught(self) -> None:
        """An error during ``fetch_todays_releases`` is caught."""
        mock_service_instance = MagicMock()
        mock_service_instance.fetch_todays_releases = AsyncMock(
            side_effect=ValueError("bad data"),
        )

        mock_http_client = AsyncMock()

        with (
            patch("httpx.AsyncClient") as mock_async_client,
            patch(
                "src.services.statcan.service.StatCanETLService",
                return_value=mock_service_instance,
            ),
            patch("src.services.statcan.client.StatCanClient"),
            patch("src.services.statcan.maintenance.StatCanMaintenanceGuard"),
            patch("src.core.rate_limit.AsyncTokenBucket"),
        ):
            mock_async_client.return_value.__aenter__ = AsyncMock(
                return_value=mock_http_client,
            )
            mock_async_client.return_value.__aexit__ = AsyncMock(
                return_value=False,
            )

            # Should not raise
            await scheduled_fetch_todays_releases()
