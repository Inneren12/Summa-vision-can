"""Tests for admin jobs dashboard endpoints (C-4).

Covers:
* ``GET  /api/v1/admin/jobs``                — list jobs with filters
* ``POST /api/v1/admin/jobs/{job_id}/retry`` — retry a failed job
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.api.routers.admin_jobs import _get_job_repo, router
from src.models.job import Job, JobStatus


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_app(job_repo_override: object | None = None) -> FastAPI:
    """Create a minimal test FastAPI app with dependency overrides."""
    app = FastAPI()
    app.include_router(router)

    if job_repo_override is not None:
        app.dependency_overrides[_get_job_repo] = lambda: job_repo_override

    return app


def _make_job(
    *,
    job_id: int = 1,
    job_type: str = "graphics_generate",
    status: JobStatus = JobStatus.QUEUED,
    payload_json: str = '{"schema_version":1}',
    result_json: str | None = None,
    error_code: str | None = None,
    error_message: str | None = None,
    attempt_count: int = 0,
    max_attempts: int = 3,
    created_by: str | None = "admin_api",
    dedupe_key: str | None = None,
) -> Job:
    """Create a mock Job instance."""
    job = MagicMock(spec=Job)
    job.id = job_id
    job.job_type = job_type
    job.status = status
    job.payload_json = payload_json
    job.result_json = result_json
    job.error_code = error_code
    job.error_message = error_message
    job.attempt_count = attempt_count
    job.max_attempts = max_attempts
    job.created_at = datetime(2026, 4, 12, 10, 0, 0, tzinfo=timezone.utc)
    job.started_at = None
    job.finished_at = None
    job.created_by = created_by
    job.dedupe_key = dedupe_key
    return job


@pytest.fixture()
def mock_job_repo() -> AsyncMock:
    """Return a mocked JobRepository."""
    return AsyncMock()


# ---------------------------------------------------------------------------
# GET /api/v1/admin/jobs
# ---------------------------------------------------------------------------


class TestListJobs:
    """Tests for the GET /api/v1/admin/jobs endpoint."""

    @pytest.mark.asyncio()
    async def test_list_jobs_returns_items_and_total(
        self, mock_job_repo: AsyncMock
    ) -> None:
        """A list of jobs should be returned with total count."""
        job1 = _make_job(job_id=1)
        job2 = _make_job(job_id=2, job_type="cube_fetch")
        mock_job_repo.list_jobs.return_value = [job1, job2]

        app = _make_app(job_repo_override=mock_job_repo)
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/admin/jobs")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 2
        assert data["total"] == 2

    @pytest.mark.asyncio()
    async def test_list_jobs_empty_returns_empty_list(
        self, mock_job_repo: AsyncMock
    ) -> None:
        """An empty job list should return 200 with empty items."""
        mock_job_repo.list_jobs.return_value = []

        app = _make_app(job_repo_override=mock_job_repo)
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/admin/jobs")

        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio()
    async def test_list_jobs_passes_filters(
        self, mock_job_repo: AsyncMock
    ) -> None:
        """Filter params should be forwarded to the repository."""
        mock_job_repo.list_jobs.return_value = []

        app = _make_app(job_repo_override=mock_job_repo)
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            await client.get(
                "/api/v1/admin/jobs?job_type=cube_fetch&status=failed&limit=10"
            )

        mock_job_repo.list_jobs.assert_called_once_with(
            job_type="cube_fetch",
            status=JobStatus.FAILED,
            limit=10,
        )

    @pytest.mark.asyncio()
    async def test_list_jobs_default_limit(
        self, mock_job_repo: AsyncMock
    ) -> None:
        """Without limit param, default 50 should be used."""
        mock_job_repo.list_jobs.return_value = []

        app = _make_app(job_repo_override=mock_job_repo)
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            await client.get("/api/v1/admin/jobs")

        call_kwargs = mock_job_repo.list_jobs.call_args[1]
        assert call_kwargs["limit"] == 50

    @pytest.mark.asyncio()
    async def test_list_jobs_invalid_status_returns_422(
        self, mock_job_repo: AsyncMock
    ) -> None:
        """Invalid status value should return 422."""
        app = _make_app(job_repo_override=mock_job_repo)
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/admin/jobs?status=invalid")

        assert resp.status_code == 422

    @pytest.mark.asyncio()
    async def test_list_jobs_response_includes_all_fields(
        self, mock_job_repo: AsyncMock
    ) -> None:
        """Response items must contain all expected fields."""
        job = _make_job(
            job_id=5,
            dedupe_key="fetch:13-10-0888-01:2026-04-01",
            error_code="STORAGE_ERROR",
            error_message="S3 bucket not found",
        )
        mock_job_repo.list_jobs.return_value = [job]

        app = _make_app(job_repo_override=mock_job_repo)
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/admin/jobs")

        item = resp.json()["items"][0]
        expected_keys = {
            "id",
            "job_type",
            "status",
            "payload_json",
            "result_json",
            "error_code",
            "error_message",
            "attempt_count",
            "max_attempts",
            "created_at",
            "started_at",
            "finished_at",
            "created_by",
            "dedupe_key",
        }
        assert expected_keys == set(item.keys())


# ---------------------------------------------------------------------------
# POST /api/v1/admin/jobs/{job_id}/retry
# ---------------------------------------------------------------------------


class TestRetryJob:
    """Tests for the POST /api/v1/admin/jobs/{job_id}/retry endpoint."""

    @pytest.mark.asyncio()
    async def test_retry_failed_job_returns_202(
        self, mock_job_repo: AsyncMock
    ) -> None:
        """A failed job with remaining attempts should be retried (202)."""
        job = _make_job(
            job_id=7,
            status=JobStatus.FAILED,
            attempt_count=1,
            max_attempts=3,
            error_code="STORAGE_ERROR",
            error_message="S3 error",
        )
        mock_job_repo.get_job.return_value = job

        app = _make_app(job_repo_override=mock_job_repo)
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            resp = await client.post("/api/v1/admin/jobs/7/retry")

        assert resp.status_code == 202
        data = resp.json()
        assert data["job_id"] == "7"
        assert data["status"] == "queued"

    @pytest.mark.asyncio()
    async def test_retry_not_found_returns_404(
        self, mock_job_repo: AsyncMock
    ) -> None:
        """Non-existent job should return 404."""
        mock_job_repo.get_job.return_value = None

        app = _make_app(job_repo_override=mock_job_repo)
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            resp = await client.post("/api/v1/admin/jobs/999/retry")

        assert resp.status_code == 404

    @pytest.mark.asyncio()
    async def test_retry_success_job_returns_409(
        self, mock_job_repo: AsyncMock
    ) -> None:
        """A successful job should not be retryable (409)."""
        job = _make_job(job_id=5, status=JobStatus.SUCCESS)
        mock_job_repo.get_job.return_value = job

        app = _make_app(job_repo_override=mock_job_repo)
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            resp = await client.post("/api/v1/admin/jobs/5/retry")

        assert resp.status_code == 409
        assert "Only failed jobs" in resp.json()["detail"]

    @pytest.mark.asyncio()
    async def test_retry_exhausted_job_returns_409(
        self, mock_job_repo: AsyncMock
    ) -> None:
        """A failed job with max attempts reached should return 409."""
        job = _make_job(
            job_id=8,
            status=JobStatus.FAILED,
            attempt_count=3,
            max_attempts=3,
        )
        mock_job_repo.get_job.return_value = job

        app = _make_app(job_repo_override=mock_job_repo)
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            resp = await client.post("/api/v1/admin/jobs/8/retry")

        assert resp.status_code == 409
        assert "exhausted" in resp.json()["detail"]

    @pytest.mark.asyncio()
    async def test_retry_clears_error_fields(
        self, mock_job_repo: AsyncMock
    ) -> None:
        """After retry, error_code and error_message should be cleared."""
        job = _make_job(
            job_id=7,
            status=JobStatus.FAILED,
            attempt_count=1,
            max_attempts=3,
            error_code="STORAGE_ERROR",
            error_message="S3 error",
        )
        mock_job_repo.get_job.return_value = job

        app = _make_app(job_repo_override=mock_job_repo)
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            resp = await client.post("/api/v1/admin/jobs/7/retry")

        assert resp.status_code == 202
        # Verify error fields were cleared on the mock
        assert job.error_code is None
        assert job.error_message is None

    @pytest.mark.asyncio()
    async def test_retry_running_job_returns_409(
        self, mock_job_repo: AsyncMock
    ) -> None:
        """A running job should not be retryable (409)."""
        job = _make_job(job_id=3, status=JobStatus.RUNNING)
        mock_job_repo.get_job.return_value = job

        app = _make_app(job_repo_override=mock_job_repo)
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            resp = await client.post("/api/v1/admin/jobs/3/retry")

        assert resp.status_code == 409
