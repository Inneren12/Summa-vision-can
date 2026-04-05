"""Health check endpoints (R12).

- ``/api/health`` — liveness, always 200.
- ``/api/health/ready`` — readiness, checks DB + temp dir.

These endpoints do NOT use the ``get_db`` dependency to avoid
circular imports and connection pool contention.
"""

from __future__ import annotations

import os
import tempfile
from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from src.core.database import engine

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
async def liveness() -> dict[str, str]:
    """Liveness probe. Always 200 if process is alive."""
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/health/ready")
async def readiness() -> JSONResponse:
    """Readiness probe. Checks DB connectivity and temp dir writable."""
    checks: dict[str, str] = {}

    # Check 1: Database
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = f"fail: {exc}"
        return JSONResponse(
            {"status": "not ready", "checks": checks},
            status_code=503,
        )

    # Check 2: Temp directory writable
    try:
        with tempfile.NamedTemporaryFile(dir=tempfile.gettempdir(), delete=True):
            pass
        checks["temp_dir"] = "ok"
    except Exception as exc:
        checks["temp_dir"] = f"fail: {exc}"
        return JSONResponse(
            {"status": "not ready", "checks": checks},
            status_code=503,
        )

    return JSONResponse({"status": "ready", "checks": checks})
