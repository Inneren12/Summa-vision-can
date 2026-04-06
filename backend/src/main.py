"""Summa Vision API – application entry point."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routers.admin_graphics import router as admin_graphics_router
from src.api.routers.cmhc import router as cmhc_router
from src.api.routers.public_graphics import router as public_graphics_router
from src.api.routers.public_leads import router as public_leads_router
from src.api.routers.tasks import router as tasks_router
from src.api.routers.health import router as health_router
from src.core.config import Settings, get_settings
from src.core.error_handler import register_exception_handlers
from src.core.logging import setup_logging
from src.core.scheduler import shutdown_scheduler, start_scheduler
from src.core.security.auth import AuthMiddleware
import structlog

import sys
import asyncio

# Windows requires ProactorEventLoop for asyncio subprocess support.
# Deprecated in Python 3.12+ where it is the default on Windows.
if sys.platform == "win32" and sys.version_info < (3, 12):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
# ---------------------------------------------------------------------------
# Structured logging (must run before anything else logs)
# ---------------------------------------------------------------------------

setup_logging()

# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

settings_on_startup: Settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage startup/shutdown lifecycle events."""
    start_scheduler()

    # --- Startup ---
    # Resource semaphores (R2)
    app.state.data_sem = asyncio.Semaphore(2)
    app.state.render_sem = asyncio.Semaphore(2)
    app.state.io_sem = asyncio.Semaphore(10)
    app.state.shutting_down = False

    # Zombie reaper (R8) — runs once on startup
    from src.core.database import get_session_factory
    from src.repositories.job_repository import JobRepository

    factory = get_session_factory()
    async with factory() as session:
        job_repo = JobRepository(session)
        requeued = await job_repo.requeue_stale_running(stale_threshold_minutes=10)
        await session.commit()
        if requeued > 0:
            structlog.get_logger().warning(
                "zombie_reaper_requeued",
                count=requeued,
                threshold_minutes=10,
            )

    structlog.get_logger().info("app_started", semaphores="initialized")

    # Job runner — background loop (R7)
    from src.services.jobs.runner import JobRunner
    from src.core.database import get_session_factory

    runner = JobRunner(get_session_factory(), app.state)
    runner_task = asyncio.create_task(runner.run_loop(poll_interval=2.0))

    yield

    # --- Shutdown (R20) ---
    app.state.shutting_down = True
    structlog.get_logger().info("shutdown_initiated", grace_period_s=30)

    shutdown_scheduler()

    # Wait for runner to finish current job (up to 30s)
    try:
        await asyncio.wait_for(runner_task, timeout=30.0)
    except asyncio.TimeoutError:
        structlog.get_logger().warning(
            "shutdown_timeout",
            message="Runner did not finish within 30s. "
            "Leaving job in 'running' state for zombie reaper.",
        )
        runner_task.cancel()
        # NOTE: cancel() may interrupt the handler mid-execution.
        # This is intentional (R20): the job stays in 'running' status
        # and the zombie reaper will pick it up on next startup.
        try:
            await runner_task
        except asyncio.CancelledError:
            pass

    # Dispose DB engine
    from src.core.database import get_engine
    await get_engine().dispose()

    structlog.get_logger().info("app_stopped")


app = FastAPI(
    title=settings_on_startup.app_name,
    version="0.1.0",
    description="Canadian housing data ETL and visualization API.",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# Global exception handlers
# ---------------------------------------------------------------------------

register_exception_handlers(app)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(health_router)
app.include_router(tasks_router)
app.include_router(cmhc_router)
app.include_router(public_graphics_router)
app.include_router(public_leads_router)
app.include_router(admin_graphics_router)

# ---------------------------------------------------------------------------
# Middlewares (registered AFTER routers — Starlette wraps the full app)
# Order matters: outermost middleware is added LAST.
# CORSMiddleware must be added AFTER AuthMiddleware so it runs FIRST
# and handles OPTIONS preflight requests before auth blocks them.
# ---------------------------------------------------------------------------

app.add_middleware(
    AuthMiddleware,
    admin_api_key=settings_on_startup.admin_api_key,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://summa.vision",
        "https://www.summa.vision",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

