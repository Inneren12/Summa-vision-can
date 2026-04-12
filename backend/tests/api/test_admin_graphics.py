"""Tests for admin graphics endpoints.

Covers:
* ``GET  /api/v1/admin/queue``                — draft publication listing
* ``POST /api/v1/admin/graphics/generate``    — enqueue generation job (B-4)
* ``GET  /api/v1/admin/jobs/{job_id}``        — job status lookup (B-4)
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.api.routers.admin_graphics import (
    _get_job_repo,
    _get_repo,
    router,
)
from src.models.job import Job, JobStatus
from src.models.publication import Publication, PublicationStatus
from src.repositories.job_repository import EnqueueResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_app(
    repo_override: object | None = None,
    job_repo_override: object | None = None,
) -> FastAPI:
    """Create a minimal test FastAPI app with dependency overrides."""
    app = FastAPI()
    app.include_router(router)

    if repo_override is not None:
        app.dependency_overrides[_get_repo] = lambda: repo_override
    if job_repo_override is not None:
        app.dependency_overrides[_get_job_repo] = lambda: job_repo_override

    return app


def _make_publication(
    *,
    pub_id: int = 1,
    headline: str = "Test Headline",
    chart_type: str = "BAR",
    virality_score: float = 7.5,
    status: PublicationStatus = PublicationStatus.DRAFT,
) -> Publication:
    """Create a mock Publication instance."""
    pub = MagicMock(spec=Publication)
    pub.id = pub_id
    pub.headline = headline
    pub.chart_type = chart_type
    pub.virality_score = virality_score
    pub.status = status
    pub.created_at = datetime(2026, 3, 15, 12, 0, 0, tzinfo=timezone.utc)
    pub.s3_key_lowres = None
    pub.s3_key_highres = None
    return pub


def _make_job(
    *,
    job_id: int = 1,
    job_type: str = "graphics_generate",
    status: JobStatus = JobStatus.QUEUED,
    payload_json: str = '{"schema_version":1}',
    result_json: str | None = None,
    error_code: str | None = None,
    error_message: str | None = None,
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
    job.created_at = datetime(2026, 4, 12, 10, 0, 0, tzinfo=timezone.utc)
    job.started_at = None
    job.finished_at = None
    job.dedupe_key = None
    return job


@pytest.fixture()
def mock_repo() -> AsyncMock:
    """Return a mocked PublicationRepository."""
    return AsyncMock()


@pytest.fixture()
def mock_job_repo() -> AsyncMock:
    """Return a mocked JobRepository."""
    return AsyncMock()


# ---------------------------------------------------------------------------
# GET /api/v1/admin/queue
# ---------------------------------------------------------------------------


class TestGetQueue:
    """Tests for the GET /api/v1/admin/queue endpoint."""

    @pytest.mark.asyncio()
    async def test_get_queue_returns_draft_publications(
        self, mock_repo: AsyncMock
    ) -> None:
        """Two DRAFT publications should be returned as a list of 2 items."""
        pub1 = _make_publication(pub_id=1, virality_score=8.0)
        pub2 = _make_publication(pub_id=2, virality_score=6.0)
        mock_repo.get_drafts.return_value = [pub1, pub2]

        app = _make_app(repo_override=mock_repo)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/admin/queue")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["id"] == 1
        assert data[1]["id"] == 2

    @pytest.mark.asyncio()
    async def test_get_queue_empty_returns_empty_list(
        self, mock_repo: AsyncMock
    ) -> None:
        """An empty draft list should return HTTP 200 with ``[]``."""
        mock_repo.get_drafts.return_value = []

        app = _make_app(repo_override=mock_repo)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/admin/queue")

        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio()
    async def test_get_queue_respects_limit_param(
        self, mock_repo: AsyncMock
    ) -> None:
        """The ``limit`` query param should be forwarded to ``get_drafts``."""
        mock_repo.get_drafts.return_value = []

        app = _make_app(repo_override=mock_repo)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.get("/api/v1/admin/queue?limit=5")

        mock_repo.get_drafts.assert_called_once_with(limit=5)

    @pytest.mark.asyncio()
    async def test_get_queue_response_schema(
        self, mock_repo: AsyncMock
    ) -> None:
        """Response items must contain the expected keys."""
        pub = _make_publication()
        mock_repo.get_drafts.return_value = [pub]

        app = _make_app(repo_override=mock_repo)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/admin/queue")

        item = resp.json()[0]
        expected_keys = {"id", "headline", "chart_type", "virality_score", "status", "created_at"}
        assert expected_keys == set(item.keys())

    @pytest.mark.asyncio()
    async def test_get_queue_default_limit(
        self, mock_repo: AsyncMock
    ) -> None:
        """Without an explicit limit, the default (20) should be used."""
        mock_repo.get_drafts.return_value = []

        app = _make_app(repo_override=mock_repo)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.get("/api/v1/admin/queue")

        mock_repo.get_drafts.assert_called_once_with(limit=20)


# ---------------------------------------------------------------------------
# POST /api/v1/admin/graphics/generate  (B-4)
# ---------------------------------------------------------------------------


class TestGenerateGraphic:
    """Tests for the POST /api/v1/admin/graphics/generate endpoint."""

    _VALID_BODY = {
        "data_key": "data/housing.parquet",
        "chart_type": "bar",
        "title": "Housing Starts",
        "category": "housing",
    }

    @pytest.mark.asyncio()
    async def test_generate_returns_202_with_job_id(
        self, mock_job_repo: AsyncMock
    ) -> None:
        """A valid request should return HTTP 202 with job_id and status."""
        job = _make_job(job_id=7, status=JobStatus.QUEUED)
        mock_job_repo.enqueue.return_value = EnqueueResult(job=job, created=True)

        app = _make_app(job_repo_override=mock_job_repo)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/admin/graphics/generate",
                json=self._VALID_BODY,
            )

        assert resp.status_code == 202
        data = resp.json()
        assert data["job_id"] == "7"
        assert data["status"] == "queued"

    @pytest.mark.asyncio()
    async def test_generate_enqueues_with_correct_job_type(
        self, mock_job_repo: AsyncMock
    ) -> None:
        """Enqueue must be called with job_type='graphics_generate'."""
        job = _make_job()
        mock_job_repo.enqueue.return_value = EnqueueResult(job=job, created=True)

        app = _make_app(job_repo_override=mock_job_repo)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.post(
                "/api/v1/admin/graphics/generate",
                json=self._VALID_BODY,
            )

        call_kwargs = mock_job_repo.enqueue.call_args[1]
        assert call_kwargs["job_type"] == "graphics_generate"
        assert call_kwargs["created_by"] == "admin_api"

    @pytest.mark.asyncio()
    async def test_generate_dedupe_returns_existing_job(
        self, mock_job_repo: AsyncMock
    ) -> None:
        """If dedupe finds an existing running job, return it without error."""
        existing_job = _make_job(job_id=42, status=JobStatus.RUNNING)
        mock_job_repo.enqueue.return_value = EnqueueResult(job=existing_job, created=False)

        app = _make_app(job_repo_override=mock_job_repo)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/admin/graphics/generate",
                json=self._VALID_BODY,
            )

        assert resp.status_code == 202
        data = resp.json()
        assert data["job_id"] == "42"
        assert data["status"] == "running"

    @pytest.mark.asyncio()
    async def test_generate_does_not_block_on_pipeline(
        self, mock_job_repo: AsyncMock
    ) -> None:
        """Endpoint must only enqueue and return, not execute the pipeline."""
        job = _make_job()
        mock_job_repo.enqueue.return_value = EnqueueResult(job=job, created=True)

        app = _make_app(job_repo_override=mock_job_repo)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/admin/graphics/generate",
                json=self._VALID_BODY,
            )

        # Endpoint should return 202 — enqueue was called exactly once
        assert resp.status_code == 202
        mock_job_repo.enqueue.assert_called_once()

    @pytest.mark.asyncio()
    async def test_generate_computes_correct_dedupe_key(
        self, mock_job_repo: AsyncMock
    ) -> None:
        """dedupe_key must follow the spec: graphics:{product_id}:{data_key}:{config_hash}."""
        job = _make_job()
        mock_job_repo.enqueue.return_value = EnqueueResult(job=job, created=True)

        body = {
            "data_key": "data/test.parquet",
            "chart_type": "line",
            "title": "My Chart",
            "size": [1080, 1080],
            "category": "housing",
            "source_product_id": "14-10-0127",
        }

        # Compute expected config hash
        config_dict = {
            "chart_type": "line",
            "size": [1080, 1080],
            "title": "My Chart",
        }
        expected_hash = hashlib.sha256(
            json.dumps(config_dict, sort_keys=True).encode("utf-8")
        ).hexdigest()[:16]
        expected_dedupe = f"graphics:14-10-0127:data/test.parquet:{expected_hash}"

        app = _make_app(job_repo_override=mock_job_repo)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.post(
                "/api/v1/admin/graphics/generate",
                json=body,
            )

        call_kwargs = mock_job_repo.enqueue.call_args[1]
        assert call_kwargs["dedupe_key"] == expected_dedupe

    @pytest.mark.asyncio()
    async def test_generate_dedupe_key_uses_manual_when_no_product_id(
        self, mock_job_repo: AsyncMock
    ) -> None:
        """Without source_product_id, dedupe key uses 'manual' placeholder."""
        job = _make_job()
        mock_job_repo.enqueue.return_value = EnqueueResult(job=job, created=True)

        app = _make_app(job_repo_override=mock_job_repo)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.post(
                "/api/v1/admin/graphics/generate",
                json=self._VALID_BODY,
            )

        call_kwargs = mock_job_repo.enqueue.call_args[1]
        assert call_kwargs["dedupe_key"].startswith("graphics:manual:")

    @pytest.mark.asyncio()
    async def test_generate_payload_json_contains_all_fields(
        self, mock_job_repo: AsyncMock
    ) -> None:
        """The payload_json passed to enqueue must contain all request fields."""
        job = _make_job()
        mock_job_repo.enqueue.return_value = EnqueueResult(job=job, created=True)

        body = {
            "data_key": "data/test.parquet",
            "chart_type": "bar",
            "title": "Test",
            "size": [1200, 900],
            "category": "housing",
            "source_product_id": "14-10-0127",
        }

        app = _make_app(job_repo_override=mock_job_repo)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.post(
                "/api/v1/admin/graphics/generate",
                json=body,
            )

        call_kwargs = mock_job_repo.enqueue.call_args[1]
        payload = json.loads(call_kwargs["payload_json"])
        assert payload["data_key"] == "data/test.parquet"
        assert payload["chart_type"] == "bar"
        assert payload["title"] == "Test"
        assert payload["size"] == [1200, 900]
        assert payload["category"] == "housing"
        assert payload["source_product_id"] == "14-10-0127"
        assert payload["schema_version"] == 1

    @pytest.mark.asyncio()
    async def test_generate_returns_422_on_missing_required_fields(
        self, mock_job_repo: AsyncMock
    ) -> None:
        """Missing required fields in request body must return 422."""
        app = _make_app(job_repo_override=mock_job_repo)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/admin/graphics/generate",
                json={"data_key": "test.parquet"},  # missing chart_type, title, category
            )

        assert resp.status_code == 422

    @pytest.mark.asyncio()
    async def test_generate_default_size(
        self, mock_job_repo: AsyncMock
    ) -> None:
        """Default size should be (1080, 1080)."""
        job = _make_job()
        mock_job_repo.enqueue.return_value = EnqueueResult(job=job, created=True)

        app = _make_app(job_repo_override=mock_job_repo)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.post(
                "/api/v1/admin/graphics/generate",
                json=self._VALID_BODY,
            )

        call_kwargs = mock_job_repo.enqueue.call_args[1]
        payload = json.loads(call_kwargs["payload_json"])
        assert payload["size"] == [1080, 1080]


# ---------------------------------------------------------------------------
# GET /api/v1/admin/jobs/{job_id}  (B-4)
# ---------------------------------------------------------------------------


class TestGetJobStatus:
    """Tests for the GET /api/v1/admin/jobs/{job_id} endpoint."""

    @pytest.mark.asyncio()
    async def test_get_job_returns_status(
        self, mock_job_repo: AsyncMock
    ) -> None:
        """Existing job should return full status object."""
        job = _make_job(job_id=10, job_type="graphics_generate", status=JobStatus.QUEUED)
        mock_job_repo.get_job.return_value = job

        app = _make_app(job_repo_override=mock_job_repo)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/admin/jobs/10")

        assert resp.status_code == 200
        data = resp.json()
        assert data["job_id"] == "10"
        assert data["job_type"] == "graphics_generate"
        assert data["status"] == "queued"

    @pytest.mark.asyncio()
    async def test_get_job_404_when_not_found(
        self, mock_job_repo: AsyncMock
    ) -> None:
        """Non-existent job ID should return 404."""
        mock_job_repo.get_job.return_value = None

        app = _make_app(job_repo_override=mock_job_repo)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/admin/jobs/999")

        assert resp.status_code == 404

    @pytest.mark.asyncio()
    async def test_get_job_includes_result_json_on_success(
        self, mock_job_repo: AsyncMock
    ) -> None:
        """Completed job should include result_json in response."""
        result_data = json.dumps({
            "publication_id": 42,
            "cdn_url_lowres": "http://cdn/pub/42/v1/lowres.png",
            "s3_key_highres": "publications/42/v1/highres.png",
            "version": 1,
        })
        job = _make_job(
            job_id=5,
            status=JobStatus.SUCCESS,
            result_json=result_data,
        )
        job.finished_at = datetime(2026, 4, 12, 10, 5, 0, tzinfo=timezone.utc)
        mock_job_repo.get_job.return_value = job

        app = _make_app(job_repo_override=mock_job_repo)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/admin/jobs/5")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["result_json"] is not None
        parsed_result = json.loads(data["result_json"])
        assert parsed_result["publication_id"] == 42

    @pytest.mark.asyncio()
    async def test_get_job_includes_error_on_failure(
        self, mock_job_repo: AsyncMock
    ) -> None:
        """Failed job should include error_code and error_message."""
        job = _make_job(
            job_id=6,
            status=JobStatus.FAILED,
            error_code="STORAGE_ERROR",
            error_message="S3 bucket not found",
        )
        job.finished_at = datetime(2026, 4, 12, 10, 5, 0, tzinfo=timezone.utc)
        mock_job_repo.get_job.return_value = job

        app = _make_app(job_repo_override=mock_job_repo)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/admin/jobs/6")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "failed"
        assert data["error_code"] == "STORAGE_ERROR"
        assert data["error_message"] == "S3 bucket not found"

    @pytest.mark.asyncio()
    async def test_get_job_response_schema(
        self, mock_job_repo: AsyncMock
    ) -> None:
        """Response must contain all expected fields."""
        job = _make_job(job_id=1)
        mock_job_repo.get_job.return_value = job

        app = _make_app(job_repo_override=mock_job_repo)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/admin/jobs/1")

        data = resp.json()
        expected_keys = {
            "job_id", "job_type", "status", "result_json",
            "error_code", "error_message", "created_at",
            "started_at", "finished_at",
        }
        assert expected_keys == set(data.keys())
