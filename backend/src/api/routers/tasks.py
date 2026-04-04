"""Task polling endpoint — ``GET /api/v1/admin/tasks/{task_id}``.

Clients that receive an HTTP 202 from a job-submission endpoint use this
route to poll the progress of their background task until it reaches
``COMPLETED`` or ``FAILED``.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from src.core.task_manager import TaskManager, TaskStatusResponse, get_task_manager

router = APIRouter(prefix="/api/v1/admin/tasks", tags=["tasks"])


@router.get(
    "/{task_id}",
    response_model=TaskStatusResponse,
    summary="Poll task status",
    responses={
        200: {"description": "Current task status returned."},
        404: {"description": "Unknown task_id."},
    },
)
async def get_task_status(
    task_id: str,
    tm: TaskManager = Depends(get_task_manager),
) -> TaskStatusResponse:
    """Return the current lifecycle status of the task identified by *task_id*.

    Parameters
    ----------
    task_id:
        UUID string returned by a previous submission endpoint.
    tm:
        Injected :class:`TaskManager` singleton.

    Returns
    -------
    TaskStatusResponse
        Current state including ``status``, optional ``result_url``, and
        human-readable ``detail``.

    Raises
    ------
    HTTPException (404)
        If *task_id* does not correspond to a known task.
    """
    try:
        return tm.get_task_status(task_id)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"Task not found: {task_id}",
        )
