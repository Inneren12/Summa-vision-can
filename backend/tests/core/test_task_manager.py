"""Unit tests for :mod:`src.core.task_manager`.

Covers the full lifecycle of the :class:`TaskManager` — submission, status
transitions (RUNNING → COMPLETED, RUNNING → FAILED), the module-level
singleton accessor, and edge cases such as unknown task IDs.
"""

from __future__ import annotations

import asyncio

import pytest

from src.core.task_manager import (
    TaskManager,
    TaskStatus,
    TaskStatusResponse,
    _TaskRecord,
    get_task_manager,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _succeed_after(seconds: float = 0.05) -> str:
    """A minimal coroutine that sleeps, then returns a result URL."""
    await asyncio.sleep(seconds)
    return "https://example.com/result.csv"


async def _fail_after(seconds: float = 0.05) -> None:
    """A minimal coroutine that sleeps, then raises."""
    await asyncio.sleep(seconds)
    raise RuntimeError("Something went wrong")


async def _instant_no_return() -> None:
    """A coroutine that completes immediately with no return value."""
    await asyncio.sleep(0)


# ---------------------------------------------------------------------------
# TaskManager.submit_task
# ---------------------------------------------------------------------------


class TestSubmitTask:
    """Tests for :meth:`TaskManager.submit_task`."""

    async def test_returns_uuid_string(self) -> None:
        """``submit_task`` must return a non-empty UUID string."""
        tm = TaskManager()
        task_id = tm.submit_task(_succeed_after())
        assert isinstance(task_id, str)
        assert len(task_id) == 36  # UUID v4 length
        # Allow the background task to finish.
        await asyncio.sleep(0.1)

    async def test_task_is_registered(self) -> None:
        """The returned task_id must be present in the internal registry."""
        tm = TaskManager()
        task_id = tm.submit_task(_succeed_after())
        assert task_id in tm.tasks
        await asyncio.sleep(0.1)

    async def test_initial_status_is_running(self) -> None:
        """Immediately after submission the status should be RUNNING."""
        tm = TaskManager()
        coro = _succeed_after(0.2)
        task_id = tm.submit_task(coro)
        status = tm.get_task_status(task_id)
        assert status.status == TaskStatus.RUNNING
        # Cancel the task to avoid warnings and close the inner coroutine
        # which may never have been awaited if _run_wrapper hadn't started.
        tm.tasks[task_id].async_task.cancel()  # type: ignore[union-attr]
        await asyncio.sleep(0.05)
        coro.close()


# ---------------------------------------------------------------------------
# Status transitions
# ---------------------------------------------------------------------------


class TestStatusTransitions:
    """Verify that status progresses from RUNNING to COMPLETED or FAILED."""

    async def test_transitions_to_completed(self) -> None:
        """A successful coroutine should drive the status to COMPLETED."""
        tm = TaskManager()
        task_id = tm.submit_task(_succeed_after(0.05))
        # Give it time to finish.
        await asyncio.sleep(0.2)
        status = tm.get_task_status(task_id)
        assert status.status == TaskStatus.COMPLETED
        assert status.result_url == "https://example.com/result.csv"
        assert status.detail == "Task completed successfully."

    async def test_transitions_to_failed(self) -> None:
        """A failing coroutine should drive the status to FAILED."""
        tm = TaskManager()
        task_id = tm.submit_task(_fail_after(0.05))
        await asyncio.sleep(0.2)
        status = tm.get_task_status(task_id)
        assert status.status == TaskStatus.FAILED
        assert status.detail is not None
        assert "RuntimeError" in status.detail
        assert "Something went wrong" in status.detail

    async def test_completed_with_none_return(self) -> None:
        """A coroutine that returns ``None`` should still reach COMPLETED."""
        tm = TaskManager()
        task_id = tm.submit_task(_instant_no_return())
        await asyncio.sleep(0.1)
        status = tm.get_task_status(task_id)
        assert status.status == TaskStatus.COMPLETED
        assert status.result_url is None


# ---------------------------------------------------------------------------
# TaskManager.get_task_status
# ---------------------------------------------------------------------------


class TestGetTaskStatus:
    """Tests for :meth:`TaskManager.get_task_status`."""

    async def test_returns_task_status_response(self) -> None:
        """The return type must be :class:`TaskStatusResponse`."""
        tm = TaskManager()
        task_id = tm.submit_task(_succeed_after())
        result = tm.get_task_status(task_id)
        assert isinstance(result, TaskStatusResponse)
        await asyncio.sleep(0.1)

    async def test_unknown_task_id_raises_key_error(self) -> None:
        """Querying a non-existent task_id must raise KeyError."""
        tm = TaskManager()
        with pytest.raises(KeyError, match="Unknown task_id"):
            tm.get_task_status("not-a-real-id")

    async def test_response_contains_task_id(self) -> None:
        """The response's ``task_id`` field must match the input."""
        tm = TaskManager()
        task_id = tm.submit_task(_succeed_after())
        result = tm.get_task_status(task_id)
        assert result.task_id == task_id
        await asyncio.sleep(0.1)


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class TestModels:
    """Tests for the Pydantic data models."""

    def test_task_status_values(self) -> None:
        """The ``TaskStatus`` enum must expose exactly four members."""
        assert set(TaskStatus) == {
            TaskStatus.PENDING,
            TaskStatus.RUNNING,
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
        }

    def test_task_status_response_serialisation(self) -> None:
        """``TaskStatusResponse`` should round-trip through JSON correctly."""
        resp = TaskStatusResponse(
            task_id="abc-123",
            status=TaskStatus.COMPLETED,
            result_url="https://example.com/result.csv",
            detail="done",
        )
        data = resp.model_dump()
        assert data["status"] == "COMPLETED"
        assert data["result_url"] == "https://example.com/result.csv"

    def test_task_status_response_optional_fields(self) -> None:
        """Optional fields should default to ``None``."""
        resp = TaskStatusResponse(
            task_id="abc-123",
            status=TaskStatus.RUNNING,
        )
        assert resp.result_url is None
        assert resp.detail is None


# ---------------------------------------------------------------------------
# _TaskRecord
# ---------------------------------------------------------------------------


class TestTaskRecord:
    """Tests for the internal :class:`_TaskRecord`."""

    def test_initial_state(self) -> None:
        """A fresh record should be PENDING with no result."""
        rec = _TaskRecord("test-id")
        assert rec.task_id == "test-id"
        assert rec.status == TaskStatus.PENDING
        assert rec.result_url is None
        assert rec.detail is None
        assert rec.async_task is None


# ---------------------------------------------------------------------------
# Singleton accessor
# ---------------------------------------------------------------------------


class TestGetTaskManager:
    """Tests for the module-level :func:`get_task_manager` singleton."""

    def test_returns_task_manager(self) -> None:
        """Must return a :class:`TaskManager` instance."""
        import src.core.task_manager as tm_module

        # Reset the singleton for a clean test.
        tm_module._task_manager = None
        manager = get_task_manager()
        assert isinstance(manager, TaskManager)
        # Clean up.
        tm_module._task_manager = None

    def test_returns_same_instance(self) -> None:
        """Two successive calls must yield the same object."""
        import src.core.task_manager as tm_module

        tm_module._task_manager = None
        m1 = get_task_manager()
        m2 = get_task_manager()
        assert m1 is m2
        tm_module._task_manager = None


# ---------------------------------------------------------------------------
# Concurrent submissions
# ---------------------------------------------------------------------------


class TestConcurrentSubmissions:
    """Verify the manager handles multiple concurrent tasks correctly."""

    async def test_multiple_tasks(self) -> None:
        """Submit several tasks and confirm each gets a unique ID."""
        tm = TaskManager()
        ids: list[str] = []
        for _ in range(5):
            ids.append(tm.submit_task(_succeed_after(0.02)))

        assert len(set(ids)) == 5  # all unique
        await asyncio.sleep(0.2)

        for tid in ids:
            status = tm.get_task_status(tid)
            assert status.status == TaskStatus.COMPLETED
