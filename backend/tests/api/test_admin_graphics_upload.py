"""Tests for POST /api/v1/admin/graphics/generate-from-data.

Covers the user-uploaded-data flow:

1. Validation of the incoming ``GenerateFromDataRequest`` payload.
2. Polars DataFrame construction + column dtype coercion.
3. Upload of the resulting Parquet bytes to ``temp/uploads/`` via the
   injected ``StorageInterface``.
4. Job enqueue with ``data_key`` pointing at the temp Parquet —
   ``GraphicPipeline`` itself is *not* exercised here (that's B-3's
   responsibility) because the pipeline is unchanged.
"""

from __future__ import annotations

import io
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import polars as pl
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.api.routers.admin_graphics import (
    _get_job_repo,
    _get_storage,
    router,
)
from src.models.job import Job, JobStatus
from src.repositories.job_repository import EnqueueResult


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _make_job(
    *,
    job_id: int = 1,
    status: JobStatus = JobStatus.QUEUED,
) -> Job:
    """Create a mock Job instance."""
    job = MagicMock(spec=Job)
    job.id = job_id
    job.job_type = "graphics_generate"
    job.status = status
    job.payload_json = '{"schema_version":1}'
    job.result_json = None
    job.error_code = None
    job.error_message = None
    job.created_at = datetime(2026, 4, 14, 10, 0, 0, tzinfo=timezone.utc)
    job.started_at = None
    job.finished_at = None
    job.dedupe_key = None
    return job


def _make_app(
    *,
    job_repo: AsyncMock,
    storage: AsyncMock,
) -> FastAPI:
    """Create a minimal FastAPI app with the upload endpoint and overrides."""
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[_get_job_repo] = lambda: job_repo
    app.dependency_overrides[_get_storage] = lambda: storage
    return app


@pytest.fixture()
def mock_job_repo() -> AsyncMock:
    """Return a mocked JobRepository with enqueue pre-configured."""
    repo = AsyncMock()
    repo.enqueue.return_value = EnqueueResult(job=_make_job(), created=True)
    return repo


@pytest.fixture()
def mock_storage() -> AsyncMock:
    """Return a mocked StorageInterface."""
    return AsyncMock()


# ---------------------------------------------------------------------------
# POST /api/v1/admin/graphics/generate-from-data
# ---------------------------------------------------------------------------


class TestGenerateFromData:
    """End-to-end tests for the uploaded-data graphic generation endpoint."""

    @pytest.mark.asyncio()
    async def test_returns_202_with_valid_data(
        self, mock_job_repo: AsyncMock, mock_storage: AsyncMock
    ) -> None:
        """POST with valid rows + chart config → 202 + job_id."""
        app = _make_app(job_repo=mock_job_repo, storage=mock_storage)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/admin/graphics/generate-from-data",
                json={
                    "data": [
                        {"year": "2020", "value": 100},
                        {"year": "2021", "value": 120},
                        {"year": "2022", "value": 115},
                    ],
                    "columns": [
                        {"name": "year", "dtype": "str"},
                        {"name": "value", "dtype": "float"},
                    ],
                    "chart_type": "line",
                    "title": "Test Chart",
                    "category": "housing",
                },
            )

        assert resp.status_code == 202
        body = resp.json()
        assert "job_id" in body
        assert body["job_id"] == "1"
        assert body["status"] == "queued"

    @pytest.mark.asyncio()
    async def test_empty_data_returns_422(
        self, mock_job_repo: AsyncMock, mock_storage: AsyncMock
    ) -> None:
        """An empty ``data`` list must fail validation with 422."""
        app = _make_app(job_repo=mock_job_repo, storage=mock_storage)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/admin/graphics/generate-from-data",
                json={
                    "data": [],
                    "columns": [],
                    "chart_type": "line",
                    "title": "T",
                    "category": "housing",
                },
            )
        assert resp.status_code == 422
        mock_storage.upload_bytes.assert_not_called()
        mock_job_repo.enqueue.assert_not_called()

    @pytest.mark.asyncio()
    async def test_oversized_data_returns_422(
        self, mock_job_repo: AsyncMock, mock_storage: AsyncMock
    ) -> None:
        """More than 10,000 rows → 422 (R15 hard cap)."""
        rows = [{"x": i} for i in range(10_001)]
        app = _make_app(job_repo=mock_job_repo, storage=mock_storage)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/admin/graphics/generate-from-data",
                json={
                    "data": rows,
                    "columns": [{"name": "x", "dtype": "int"}],
                    "chart_type": "bar",
                    "title": "T",
                    "category": "housing",
                },
            )
        assert resp.status_code == 422
        mock_storage.upload_bytes.assert_not_called()
        mock_job_repo.enqueue.assert_not_called()

    @pytest.mark.asyncio()
    async def test_oversized_dimensions_returns_422(
        self, mock_job_repo: AsyncMock, mock_storage: AsyncMock
    ) -> None:
        """Width/height beyond 4096 px → 422."""
        app = _make_app(job_repo=mock_job_repo, storage=mock_storage)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/admin/graphics/generate-from-data",
                json={
                    "data": [{"x": 1}],
                    "columns": [{"name": "x", "dtype": "int"}],
                    "chart_type": "bar",
                    "title": "T",
                    "category": "housing",
                    "size": [5000, 5000],
                },
            )
        assert resp.status_code == 422

    @pytest.mark.asyncio()
    async def test_missing_required_fields_returns_422(
        self, mock_job_repo: AsyncMock, mock_storage: AsyncMock
    ) -> None:
        """Missing ``chart_type``/``title``/``category`` must return 422."""
        app = _make_app(job_repo=mock_job_repo, storage=mock_storage)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/admin/graphics/generate-from-data",
                json={"data": [{"x": 1}], "columns": []},
            )
        assert resp.status_code == 422

    @pytest.mark.asyncio()
    async def test_parquet_uploaded_to_temp_path(
        self, mock_job_repo: AsyncMock, mock_storage: AsyncMock
    ) -> None:
        """Verify the temp Parquet is uploaded under ``temp/uploads/``."""
        app = _make_app(job_repo=mock_job_repo, storage=mock_storage)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/admin/graphics/generate-from-data",
                json={
                    "data": [{"x": 1, "y": 2}],
                    "columns": [
                        {"name": "x", "dtype": "int"},
                        {"name": "y", "dtype": "int"},
                    ],
                    "chart_type": "bar",
                    "title": "T",
                    "category": "housing",
                },
            )

        assert resp.status_code == 202
        mock_storage.upload_bytes.assert_called_once()
        call = mock_storage.upload_bytes.call_args
        key = call.kwargs.get("key") or call.args[1] if len(call.args) > 1 else None
        # Endpoint uses kwargs-form call, so prefer kwargs.
        key = call.kwargs.get("key", key)
        assert key is not None
        assert key.startswith("temp/uploads/")
        assert key.endswith(".parquet")

    @pytest.mark.asyncio()
    async def test_enqueued_payload_references_temp_key(
        self, mock_job_repo: AsyncMock, mock_storage: AsyncMock
    ) -> None:
        """The enqueued payload's ``data_key`` must be the uploaded temp key."""
        app = _make_app(job_repo=mock_job_repo, storage=mock_storage)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.post(
                "/api/v1/admin/graphics/generate-from-data",
                json={
                    "data": [{"x": 1}],
                    "columns": [{"name": "x", "dtype": "int"}],
                    "chart_type": "bar",
                    "title": "T",
                    "category": "housing",
                },
            )

        import json

        enqueue_kwargs = mock_job_repo.enqueue.call_args.kwargs
        assert enqueue_kwargs["job_type"] == "graphics_generate"
        payload = json.loads(enqueue_kwargs["payload_json"])

        upload_key = mock_storage.upload_bytes.call_args.kwargs["key"]
        assert payload["data_key"] == upload_key
        assert payload["source_product_id"] is None
        # Dedupe key uses the "custom" marker instead of a product id.
        assert enqueue_kwargs["dedupe_key"].startswith("graphics:custom:")

    @pytest.mark.asyncio()
    async def test_column_type_casting(
        self, mock_job_repo: AsyncMock, mock_storage: AsyncMock
    ) -> None:
        """Verify column types are applied before Parquet conversion."""
        app = _make_app(job_repo=mock_job_repo, storage=mock_storage)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.post(
                "/api/v1/admin/graphics/generate-from-data",
                json={
                    "data": [{"amount": "123.45", "count": "7"}],
                    "columns": [
                        {"name": "amount", "dtype": "float"},
                        {"name": "count", "dtype": "int"},
                    ],
                    "chart_type": "bar",
                    "title": "T",
                    "category": "housing",
                },
            )

        parquet_bytes = mock_storage.upload_bytes.call_args.kwargs["data"]
        df = pl.read_parquet(io.BytesIO(parquet_bytes))
        assert df["amount"].dtype == pl.Float64
        assert df["count"].dtype == pl.Int64
        assert df["amount"][0] == pytest.approx(123.45)
        assert df["count"][0] == 7

    @pytest.mark.asyncio()
    async def test_dedupe_returns_existing_job(
        self, mock_storage: AsyncMock
    ) -> None:
        """Re-submitting identical upload reuses the active job via dedupe."""
        existing = _make_job(job_id=99, status=JobStatus.RUNNING)
        repo = AsyncMock()
        repo.enqueue.return_value = EnqueueResult(job=existing, created=False)

        app = _make_app(job_repo=repo, storage=mock_storage)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/admin/graphics/generate-from-data",
                json={
                    "data": [{"x": 1}],
                    "columns": [{"name": "x", "dtype": "int"}],
                    "chart_type": "bar",
                    "title": "T",
                    "category": "housing",
                },
            )

        assert resp.status_code == 202
        body = resp.json()
        assert body["job_id"] == "99"
        assert body["status"] == "running"

    @pytest.mark.asyncio()
    async def test_default_size_is_1200_900(
        self, mock_job_repo: AsyncMock, mock_storage: AsyncMock
    ) -> None:
        """When ``size`` is omitted the payload carries the (1200, 900) default."""
        import json

        app = _make_app(job_repo=mock_job_repo, storage=mock_storage)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.post(
                "/api/v1/admin/graphics/generate-from-data",
                json={
                    "data": [{"x": 1}],
                    "columns": [{"name": "x", "dtype": "int"}],
                    "chart_type": "bar",
                    "title": "T",
                    "category": "housing",
                },
            )
        payload = json.loads(mock_job_repo.enqueue.call_args.kwargs["payload_json"])
        assert payload["size"] == [1200, 900]
