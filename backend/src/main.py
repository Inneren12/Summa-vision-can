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
from src.core.config import Settings, get_settings
from src.core.error_handler import register_exception_handlers
from src.core.logging import setup_logging
from src.core.scheduler import shutdown_scheduler, start_scheduler
from src.core.security.auth import AuthMiddleware

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
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage startup/shutdown lifecycle events."""
    start_scheduler()
    yield
    shutdown_scheduler()


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

# ---------------------------------------------------------------------------
# Health-check endpoint
# ---------------------------------------------------------------------------


@app.get("/api/health")
async def health(
    settings: Settings = Depends(get_settings),
) -> dict[str, str]:
    """Liveness probe – returns service status and current UTC timestamp.

    This endpoint is used by AWS ALB health checks and CI/CD pipelines.
    The ``settings`` dependency is injected to prove the DI wiring works
    and to make the endpoint easily configurable in the future.
    """
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
