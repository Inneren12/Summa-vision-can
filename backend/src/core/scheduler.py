"""Persistent job scheduler backed by APScheduler + SQLAlchemy job store.

Integrates :class:`~apscheduler.schedulers.asyncio.AsyncIOScheduler` with
FastAPI's lifespan so that scheduled jobs survive server restarts via an
SQLite-backed (or PostgreSQL-backed) job store.

Usage::

    # In FastAPI lifespan:
    from src.core.scheduler import start_scheduler, shutdown_scheduler

    async def lifespan(app: FastAPI):
        start_scheduler()
        yield
        shutdown_scheduler()

The scheduler is configured with a single CRON job
(``fetch_todays_releases()``) running at **09:00 EST** Monday–Friday.
Additional jobs can be registered via :func:`get_scheduler`.
"""

from __future__ import annotations

import structlog
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.core.config import Settings, get_settings
from src.core.logging import get_logger

logger: structlog.stdlib.BoundLogger = get_logger(module="scheduler")


# ---------------------------------------------------------------------------
# Scheduler singleton
# ---------------------------------------------------------------------------

_scheduler: AsyncIOScheduler | None = None
_app_ref: object | None = None  # FastAPI app reference for DI


def _create_scheduler(settings: Settings) -> AsyncIOScheduler:
    """Build an ``AsyncIOScheduler`` with the configured SQLAlchemy job store.

    Parameters
    ----------
    settings:
        Application settings containing ``scheduler_db_url``.

    Returns
    -------
    AsyncIOScheduler
        A configured but **not yet started** scheduler instance.
    """
    jobstores = {
        "default": SQLAlchemyJobStore(url=settings.scheduler_db_url),
    }
    return AsyncIOScheduler(jobstores=jobstores)


def get_scheduler() -> AsyncIOScheduler | None:
    """Return the module-level scheduler singleton (may be ``None``)."""
    return _scheduler


# ---------------------------------------------------------------------------
# Scheduled job target
# ---------------------------------------------------------------------------


async def scheduled_fetch_todays_releases() -> None:
    """Wrapper executed by APScheduler to fetch today's StatCan releases.

    This function performs a *lazy import* of the heavy service module so
    that importing ``scheduler.py`` itself remains lightweight.  All
    exceptions are caught and logged — a failing job **must not** crash the
    scheduler.

    Uses the app-scoped ``http_client`` from ``app.state`` (ARCH-DPEN-001)
    instead of creating an inline ``httpx.AsyncClient()``.
    """
    try:
        logger.info("Scheduled job started: fetch_todays_releases")

        # Lazy import to avoid circular dependencies at module load time.
        from src.services.statcan.client import StatCanClient  # noqa: PLC0415
        from src.services.statcan.service import StatCanETLService  # noqa: PLC0415

        from src.core.rate_limit import AsyncTokenBucket  # noqa: PLC0415
        from src.services.statcan.maintenance import (  # noqa: PLC0415
            StatCanMaintenanceGuard,
        )

        # ARCH-DPEN-001: use app-scoped http_client, not inline creation
        if _app_ref is None or not hasattr(_app_ref, "state"):
            raise RuntimeError(
                "Scheduler requires app reference for http_client "
                "(ARCH-DPEN-001: no inline httpx client creation)"
            )
        http_client = getattr(_app_ref.state, "http_client", None)
        if http_client is None:
            raise RuntimeError(
                "app.state.http_client not set — ensure lifespan initializes it"
            )

        guard = StatCanMaintenanceGuard()
        bucket = AsyncTokenBucket()
        client = StatCanClient(
            client=http_client,
            guard=guard,
            bucket=bucket,
        )
        service = StatCanETLService(client=client)
        releases = await service.fetch_todays_releases()

        logger.info(
            "Scheduled job completed: fetch_todays_releases",
            releases_count=len(releases),
        )
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "Scheduled job failed: fetch_todays_releases",
            error=str(exc),
            exc_info=True,
        )


async def scheduled_audit_cleanup() -> None:
    """Wrapper executed by APScheduler to delete expired audit events.

    Follows the same lazy-import + catch-all pattern used by
    ``scheduled_fetch_todays_releases``.  Pulls ``session_factory`` via
    ``get_session_factory()`` and ``retention_days`` from settings.
    """
    try:
        logger.info("Scheduled job started: audit_cleanup")

        from src.core.config import get_settings  # noqa: PLC0415
        from src.core.database import get_session_factory  # noqa: PLC0415
        from src.services.audit.cleanup import cleanup_old_audit_events  # noqa: PLC0415

        settings = get_settings()
        factory = get_session_factory()

        deleted = await cleanup_old_audit_events(
            session_factory=factory,
            retention_days=settings.audit_retention_days,
        )

        logger.info(
            "Scheduled job completed: audit_cleanup",
            deleted=deleted,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "Scheduled job failed: audit_cleanup",
            error=str(exc),
            exc_info=True,
        )


# ---------------------------------------------------------------------------
# Lifecycle management
# ---------------------------------------------------------------------------


def start_scheduler(settings: Settings | None = None, app: object | None = None) -> None:
    """Create, configure, and start the scheduler.

    If ``settings.scheduler_enabled`` is ``False`` (e.g. during tests) the
    scheduler is **not** started.

    Parameters
    ----------
    settings:
        Application settings.  Defaults to ``get_settings()`` if omitted.
    app:
        FastAPI app instance — provides ``app.state.http_client`` to
        scheduled jobs (ARCH-DPEN-001).
    """
    global _scheduler, _app_ref  # noqa: PLW0603

    _app_ref = app

    if settings is None:
        settings = get_settings()

    if not settings.scheduler_enabled:
        logger.info("Scheduler disabled via SCHEDULER_ENABLED=false")
        return

    _scheduler = _create_scheduler(settings)

    # Register the daily StatCan fetch job (Mon–Fri at 09:00 EST).
    _scheduler.add_job(
        scheduled_fetch_todays_releases,
        trigger="cron",
        day_of_week="mon-fri",
        hour=9,
        minute=0,
        timezone="US/Eastern",
        id="fetch_todays_releases",
        name="Fetch today's StatCan releases",
        replace_existing=True,
    )

    # Register daily audit event cleanup (04:00 UTC).
    _scheduler.add_job(
        scheduled_audit_cleanup,
        trigger="cron",
        hour=4,
        minute=0,
        id="audit_cleanup",
        name="Delete expired audit events",
        replace_existing=True,
    )

    _scheduler.start()
    logger.info("Scheduler started", jobs=len(_scheduler.get_jobs()))


def shutdown_scheduler() -> None:
    """Gracefully shut down the scheduler if it is running."""
    global _scheduler  # noqa: PLW0603

    if _scheduler is not None:
        try:
            if _scheduler.running:
                _scheduler.shutdown(wait=False)
                logger.info("Scheduler shut down")
        except RuntimeError:
            # Event loop may already be closed (e.g. in tests).
            pass

    _scheduler = None
