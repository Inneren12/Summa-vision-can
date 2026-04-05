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
      - SummaVisionError subclass with retryable=False → permanent failure
      - Any other exception → retryable failure (will be retried)
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
