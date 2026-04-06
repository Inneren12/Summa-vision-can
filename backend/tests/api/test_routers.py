"""Unit tests for the task-polling and CMHC REST API routers.

Uses ``httpx.AsyncClient`` via FastAPI's ``TestClient`` to exercise:

* ``GET /api/v1/admin/tasks/{task_id}``  – polling a known/unknown task.
* ``POST /api/v1/admin/cmhc/sync``       – submitting a CMHC extraction and
  verifying the ``202 Accepted`` response.
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routers.cmhc import CMHCSyncRequest, CMHCSyncResponse, _get_storage, router as cmhc_router
from src.api.routers.tasks import router as tasks_router
from src.core.storage import StorageInterface
from src.core.task_manager import (
    TaskManager,
    TaskStatus,
    _TaskRecord,
    get_task_manager,
)


# ---------------------------------------------------------------------------
# App fixture — isolated from the production ``main.py``
# ---------------------------------------------------------------------------


def _build_test_app() -> FastAPI:
    """Create a minimal test app with only the routers under test."""
    test_app = FastAPI()
    test_app.include_router(tasks_router)
    test_app.include_router(cmhc_router)
    return test_app


# Per-test TaskManager so tests don't leak state.
_test_tm: TaskManager | None = None


def _override_task_manager() -> TaskManager:
    """Return a per-test TaskManager instance."""
    assert _test_tm is not None
    return _test_tm


class _MockStorage(StorageInterface):
    """Minimal mock storage that satisfies the abstract interface."""

    async def upload_bytes(self, data: bytes, key: str) -> None:
        pass

    async def download_bytes(self, key: str) -> bytes:
        from src.core.exceptions import StorageError
        raise StorageError(f"File not found: {key}")

    async def upload_dataframe_as_csv(self, df: Any, path: str) -> None:
        pass

    async def upload_raw(
        self, data: str | bytes, path: str, content_type: str = "text/html"
    ) -> None:
        pass

    async def download_csv(self, path: str) -> Any:
        import pandas as pd
        return pd.DataFrame()

    async def list_objects(self, prefix: str) -> list[str]:
        return []

    async def generate_presigned_url(self, path: str, ttl: int = 3600) -> str:
        return f"file:///mock/{path}"


def _override_storage() -> StorageInterface:
    """Provide a mock storage instance."""
    return _MockStorage()


test_app = _build_test_app()
test_app.dependency_overrides[get_task_manager] = _override_task_manager
test_app.dependency_overrides[_get_storage] = _override_storage


# ---------------------------------------------------------------------------
# GET /api/v1/admin/tasks/{task_id}
# ---------------------------------------------------------------------------


class TestTasksRouter:
    """Tests for the task-polling endpoint."""

    def setup_method(self) -> None:
        global _test_tm
        _test_tm = TaskManager()

    def test_get_known_task(self) -> None:
        """Polling a submitted task should return 200 with status info."""
        assert _test_tm is not None
        # Manually inject a RUNNING record (no event loop needed).
        record = _TaskRecord("fake-task-1")
        record.status = TaskStatus.RUNNING
        _test_tm.tasks["fake-task-1"] = record

        client = TestClient(test_app)
        resp = client.get("/api/v1/admin/tasks/fake-task-1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["task_id"] == "fake-task-1"
        assert data["status"] == TaskStatus.RUNNING.value

    def test_get_unknown_task_returns_404(self) -> None:
        """Polling a non-existent task_id should return 404."""
        client = TestClient(test_app)
        resp = client.get("/api/v1/admin/tasks/does-not-exist")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_completed_task_has_result_url(self) -> None:
        """After a task completes with a string result, result_url is set."""
        assert _test_tm is not None
        record = _TaskRecord("fake-task-2")
        record.status = TaskStatus.COMPLETED
        record.result_url = "https://cdn.example.com/report.csv"
        record.detail = "Task completed successfully."
        _test_tm.tasks["fake-task-2"] = record

        client = TestClient(test_app)
        resp = client.get("/api/v1/admin/tasks/fake-task-2")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == TaskStatus.COMPLETED.value
        assert data["result_url"] == "https://cdn.example.com/report.csv"

    def test_failed_task_has_detail(self) -> None:
        """After a task fails, status is FAILED and detail contains error."""
        assert _test_tm is not None
        record = _TaskRecord("fake-task-3")
        record.status = TaskStatus.FAILED
        record.detail = "ValueError: kaboom"
        _test_tm.tasks["fake-task-3"] = record

        client = TestClient(test_app)
        resp = client.get("/api/v1/admin/tasks/fake-task-3")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == TaskStatus.FAILED.value
        assert "kaboom" in (data.get("detail") or "")


# ---------------------------------------------------------------------------
# POST /api/v1/admin/cmhc/sync
# ---------------------------------------------------------------------------


class TestCmhcRouter:
    """Tests for the CMHC extraction submission endpoint."""

    def setup_method(self) -> None:
        global _test_tm
        _test_tm = TaskManager()

    @patch("src.api.routers.cmhc.run_cmhc_extraction_pipeline")
    def test_returns_202_accepted(self, mock_pipeline: MagicMock) -> None:
        """``POST /api/v1/admin/cmhc/sync`` should return 202 immediately."""
        # The mock should return a coroutine that sleeps forever so we
        # never actually run the real pipeline.
        async def _stub(*a: object, **kw: object) -> None:
            await asyncio.sleep(10)

        mock_pipeline.side_effect = _stub

        client = TestClient(test_app)
        resp = client.post("/api/v1/admin/cmhc/sync", json={"city": "toronto"})

        assert resp.status_code == 202
        data = resp.json()
        assert "task_id" in data
        assert isinstance(data["task_id"], str)
        assert len(data["task_id"]) == 36  # UUID

        # Cleanup
        assert _test_tm is not None
        record = _test_tm.tasks.get(data["task_id"])
        if record and record.async_task and not record.async_task.done():
            record.async_task.cancel()

    @patch("src.api.routers.cmhc.run_cmhc_extraction_pipeline")
    def test_task_id_is_pollable(self, mock_pipeline: MagicMock) -> None:
        """The ``task_id`` from the 202 response must be pollable via GET."""
        async def _stub(*a: object, **kw: object) -> None:
            await asyncio.sleep(10)

        mock_pipeline.side_effect = _stub

        client = TestClient(test_app)
        post_resp = client.post("/api/v1/admin/cmhc/sync", json={"city": "vancouver"})
        task_id = post_resp.json()["task_id"]

        get_resp = client.get(f"/api/v1/admin/tasks/{task_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["task_id"] == task_id

        # Cleanup
        assert _test_tm is not None
        record = _test_tm.tasks.get(task_id)
        if record and record.async_task and not record.async_task.done():
            record.async_task.cancel()

    def test_missing_city_returns_422(self) -> None:
        """A request without ``city`` should be rejected with 422."""
        client = TestClient(test_app)
        resp = client.post("/api/v1/admin/cmhc/sync", json={})
        assert resp.status_code == 422

    def test_empty_city_returns_422(self) -> None:
        """An empty ``city`` string should be rejected with 422."""
        client = TestClient(test_app)
        resp = client.post("/api/v1/admin/cmhc/sync", json={"city": ""})
        assert resp.status_code == 422

    @patch("src.api.routers.cmhc.run_cmhc_extraction_pipeline")
    def test_pipeline_is_called_with_city(self, mock_pipeline: MagicMock) -> None:
        """The pipeline coroutine must be constructed with the requested city."""
        async def _stub(city: str, storage: StorageInterface) -> None:
            await asyncio.sleep(10)

        mock_pipeline.side_effect = _stub

        client = TestClient(test_app)
        resp = client.post("/api/v1/admin/cmhc/sync", json={"city": "ottawa"})
        assert resp.status_code == 202

        mock_pipeline.assert_called_once()
        call_kwargs = mock_pipeline.call_args
        assert call_kwargs.kwargs.get("city") == "ottawa" or call_kwargs.args[0] == "ottawa"

        # Cleanup
        assert _test_tm is not None
        task_id = resp.json()["task_id"]
        record = _test_tm.tasks.get(task_id)
        if record and record.async_task and not record.async_task.done():
            record.async_task.cancel()


# ---------------------------------------------------------------------------
# CMHCSyncRequest / CMHCSyncResponse schema tests
# ---------------------------------------------------------------------------


class TestCMHCSchemas:
    """Unit tests for the request / response Pydantic models."""

    def test_sync_request_valid(self) -> None:
        """A valid city string should parse without error."""
        req = CMHCSyncRequest(city="toronto")
        assert req.city == "toronto"

    def test_sync_request_strips_whitespace(self) -> None:
        """Leading/trailing whitespace on ``city`` should be stripped."""
        req = CMHCSyncRequest(city="  vancouver  ")
        assert req.city == "vancouver"

    def test_sync_response_round_trip(self) -> None:
        """``CMHCSyncResponse`` should serialise correctly."""
        resp = CMHCSyncResponse(task_id="abc-123")
        assert resp.model_dump() == {"task_id": "abc-123"}
