"""CMHC extraction endpoint — ``POST /api/v1/admin/cmhc/sync``.

Despite the ``/sync`` suffix (retained for client-side clarity), this
endpoint is **asynchronous**: it submits the CMHC extraction pipeline as a
background task and returns ``HTTP 202 Accepted`` with a ``task_id`` that
the client can poll via ``GET /api/v1/admin/tasks/{task_id}``.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, Field

from src.core.storage import StorageInterface, get_storage_manager
from src.core.task_manager import TaskManager, get_task_manager
from src.services.cmhc.service import run_cmhc_extraction_pipeline

router = APIRouter(prefix="/api/v1/admin/cmhc", tags=["cmhc"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class CMHCSyncRequest(BaseModel):
    """Request body for triggering a CMHC extraction run.

    Attributes:
        city: City slug to scrape (e.g. ``"toronto"``).
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    city: str = Field(
        ...,
        min_length=1,
        description="City slug (e.g. 'toronto').",
        examples=["toronto", "vancouver"],
    )


class CMHCSyncResponse(BaseModel):
    """Response body returned immediately upon task submission.

    Attributes:
        task_id: UUID of the submitted background task.  Use
            ``GET /api/v1/admin/tasks/{task_id}`` to poll for results.
    """

    task_id: str


# ---------------------------------------------------------------------------
# Dependency helpers
# ---------------------------------------------------------------------------


def _get_storage() -> StorageInterface:
    """Provide a StorageInterface via dependency injection.

    In production this reads the ``STORAGE_BACKEND`` setting; tests can
    override this dependency with a mock.
    """
    return get_storage_manager()


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.post(
    "/sync",
    response_model=CMHCSyncResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger CMHC extraction",
    responses={
        202: {
            "description": "Extraction submitted — poll /api/v1/admin/tasks/{task_id}."
        },
    },
)
async def trigger_cmhc_sync(
    body: CMHCSyncRequest,
    tm: TaskManager = Depends(get_task_manager),
    storage: StorageInterface = Depends(_get_storage),
) -> CMHCSyncResponse:
    """Submit the CMHC extraction pipeline as a background task.

    The endpoint builds the extraction coroutine and hands it to the
    :class:`TaskManager`.  The HTTP response is returned **immediately**
    with status ``202 Accepted``; the actual scraping runs in the
    background.

    Parameters
    ----------
    body:
        JSON body containing the ``city`` slug.
    tm:
        Injected :class:`TaskManager` singleton.
    storage:
        Injected :class:`StorageInterface` implementation.

    Returns
    -------
    CMHCSyncResponse
        Contains the ``task_id`` for subsequent polling.
    """
    coro = run_cmhc_extraction_pipeline(city=body.city, storage=storage)
    task_id: str = tm.submit_task(coro)
    return CMHCSyncResponse(task_id=task_id)
