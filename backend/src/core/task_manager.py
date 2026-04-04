"""In-memory asynchronous Task Manager for long-running background jobs.

Wraps ``asyncio.create_task`` with status tracking so that HTTP handlers can
return an immediate ``202 Accepted`` and give the client a ``task_id`` to poll.

Usage::

    manager = TaskManager()
    task_id = manager.submit_task(some_async_coroutine())
    status  = manager.get_task_status(task_id)

The task lifecycle follows: **PENDING → RUNNING → COMPLETED | FAILED**.
"""

from __future__ import annotations

import asyncio
import enum
import uuid
from typing import Any, Coroutine

import structlog
from pydantic import BaseModel, ConfigDict

from src.core.logging import get_logger

logger: structlog.stdlib.BoundLogger = get_logger(module="task_manager")


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class TaskStatus(str, enum.Enum):
    """Possible states of a background task."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class TaskStatusResponse(BaseModel):
    """Response schema returned when a client polls task progress.

    Attributes:
        task_id: Unique identifier for this task (UUID string).
        status: Current lifecycle state of the task.
        result_url: Optional presigned URL (or similar) to download the
            result artefact once the task has completed.
        detail: Human-readable detail message (e.g. error description on
            failure).
    """

    model_config = ConfigDict(use_enum_values=True)

    task_id: str
    status: TaskStatus
    result_url: str | None = None
    detail: str | None = None


# ---------------------------------------------------------------------------
# Internal record
# ---------------------------------------------------------------------------


class _TaskRecord:
    """Mutable internal bookkeeping for a single submitted task.

    This is intentionally *not* a Pydantic model – it is a lightweight
    container that holds the ``asyncio.Task`` reference alongside its
    metadata.
    """

    __slots__ = ("task_id", "status", "result_url", "detail", "async_task")

    def __init__(self, task_id: str) -> None:
        self.task_id: str = task_id
        self.status: TaskStatus = TaskStatus.PENDING
        self.result_url: str | None = None
        self.detail: str | None = None
        self.async_task: asyncio.Task[Any] | None = None


# ---------------------------------------------------------------------------
# Task Manager
# ---------------------------------------------------------------------------


class TaskManager:
    """Manages the lifecycle of background asyncio tasks.

    Tasks are tracked in an in-memory ``dict`` keyed by UUID strings.  This
    is sufficient for the current single-process deployment; a production
    scale-out would swap this for Redis or a database-backed store.
    """

    def __init__(self) -> None:
        # TODO: migrate to Redis or DB-backed store for production
        # In-memory state is lost on server restart. All running/pending tasks
        # will be lost if the FastAPI process crashes or is redeployed.
        # Options: Redis (fast, ephemeral), PostgreSQL (durable, queryable).
        self._tasks: dict[str, _TaskRecord] = {}

    # -- public API ---------------------------------------------------------

    def submit_task(self, coro: Coroutine[Any, Any, Any]) -> str:
        """Submit *coro* for background execution and return the task ID.

        The coroutine is wrapped in an ``asyncio.Task`` with a
        ``done_callback`` that updates the internal record on completion or
        failure.

        Parameters
        ----------
        coro:
            An **unawaited** coroutine object (e.g.
            ``run_cmhc_extraction_pipeline(...)``).

        Returns
        -------
        str
            A UUID v4 string identifying the submitted task.
        """
        task_id: str = str(uuid.uuid4())
        record = _TaskRecord(task_id=task_id)
        record.status = TaskStatus.RUNNING
        self._tasks[task_id] = record

        async_task: asyncio.Task[Any] = asyncio.create_task(
            self._run_wrapper(record, coro),
            name=f"bg-task-{task_id}",
        )
        record.async_task = async_task

        logger.info("Task submitted", task_id=task_id)
        return task_id

    def get_task_status(self, task_id: str) -> TaskStatusResponse:
        """Return the current status of a previously submitted task.

        Parameters
        ----------
        task_id:
            UUID string returned by :meth:`submit_task`.

        Returns
        -------
        TaskStatusResponse
            A Pydantic model containing the current lifecycle state.

        Raises
        ------
        KeyError
            If *task_id* is not known to this manager.
        """
        record = self._tasks.get(task_id)
        if record is None:
            raise KeyError(f"Unknown task_id: {task_id}")

        return TaskStatusResponse(
            task_id=record.task_id,
            status=record.status,
            result_url=record.result_url,
            detail=record.detail,
        )

    @property
    def tasks(self) -> dict[str, _TaskRecord]:
        """Expose the internal registry (read-only intent; useful for tests)."""
        return self._tasks

    # -- internal -----------------------------------------------------------

    @staticmethod
    async def _run_wrapper(
        record: _TaskRecord,
        coro: Coroutine[Any, Any, Any],
    ) -> None:
        """Execute *coro* and update *record* on success or failure.

        This wrapper ensures that the record's ``status`` and ``detail``
        fields are always set, even if the coroutine raises.
        """
        try:
            result: Any = await coro
            record.status = TaskStatus.COMPLETED
            # If the coroutine returns a string (e.g. a presigned URL),
            # store it directly as the result_url.
            if isinstance(result, str):
                record.result_url = result
            record.detail = "Task completed successfully."
            logger.info(
                "Task completed",
                task_id=record.task_id,
            )
        except Exception as exc:  # noqa: BLE001
            record.status = TaskStatus.FAILED
            record.detail = f"{type(exc).__name__}: {exc}"
            logger.error(
                "Task failed",
                task_id=record.task_id,
                error=str(exc),
                exc_info=True,
            )


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_task_manager: TaskManager | None = None


def get_task_manager() -> TaskManager:
    """Return the global :class:`TaskManager` singleton.

    This function is designed to be used as a **FastAPI dependency**::

        @router.post("/start")
        async def start(tm: TaskManager = Depends(get_task_manager)):
            ...

    The singleton is lazily created on first call.
    """
    global _task_manager  # noqa: PLW0603
    if _task_manager is None:
        _task_manager = TaskManager()
    return _task_manager
