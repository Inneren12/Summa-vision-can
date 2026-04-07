"""Job handler registry and base protocol.

Each job_type maps to an async handler function that receives a typed
payload and returns a result dict (or None). Handlers are registered
here so the runner can dispatch without importing business logic
directly.

New handlers are added as new job types are introduced in later PRs
(catalog_sync in A-3, cube_fetch in A-5, graphics_generate in B-4).
For now, the registry contains a single ``echo`` test handler.

Handler contract:
    - Receives: typed Pydantic payload (from parse_payload)
    - Receives: app state (for semaphores, settings, etc.)
    - Returns: dict serializable to JSON (stored as result_json), or None
    - Raises: Any exception
      - Exception with retryable=False attribute → permanent failure
      - Exception with error_code in NON_RETRYABLE_CODES → permanent failure
      - Any other exception → retryable failure (will be retried
        if attempt_count < max_attempts)
"""

from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel


class JobHandlerFunc(Protocol):
    """Callable protocol for job handlers."""

    async def __call__(
        self,
        payload: BaseModel,
        *,
        app_state: Any,
    ) -> dict[str, Any] | None: ...


# ---------------------------------------------------------------------------
# Handler registry — populated by later PRs
# ---------------------------------------------------------------------------

HANDLER_REGISTRY: dict[str, JobHandlerFunc] = {}


def register_handler(job_type: str, handler: JobHandlerFunc) -> None:
    """Register a handler function for a job type."""
    if job_type in HANDLER_REGISTRY:
        raise ValueError(f"Handler already registered for '{job_type}'")
    HANDLER_REGISTRY[job_type] = handler


def get_handler(job_type: str) -> JobHandlerFunc | None:
    """Look up the handler for a job type. Returns None if not found."""
    return HANDLER_REGISTRY.get(job_type)


# ---------------------------------------------------------------------------
# Catalog sync handler (A-3)
# ---------------------------------------------------------------------------

async def handle_catalog_sync(
    payload: BaseModel,
    *,
    app_state: Any,
) -> dict[str, Any] | None:
    """Execute catalog_sync job: download and sync StatCan cube list."""
    from src.core.database import async_session_factory
    from src.repositories.cube_catalog_repository import CubeCatalogRepository
    from src.services.statcan.catalog_sync import CatalogSyncService

    async with async_session_factory() as session:
        repo = CubeCatalogRepository(session)

        # Use StatCanClient from app_state if available,
        # otherwise create a simple httpx client
        http_client = getattr(app_state, "statcan_client", None)
        if http_client is None:
            import httpx
            http_client = httpx.AsyncClient(timeout=60.0)

        service = CatalogSyncService(http_client, repo)

        try:
            report = await service.sync_full_catalog()
            await session.commit()
        finally:
            # Clean up httpx client if we created it
            if not hasattr(app_state, "statcan_client"):
                await http_client.aclose()

    return {
        "total": report.total,
        "new": report.new,
        "updated": report.updated,
        "errors": report.errors,
    }


register_handler("catalog_sync", handle_catalog_sync)
