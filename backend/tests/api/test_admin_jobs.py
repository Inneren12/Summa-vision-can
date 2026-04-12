import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import FastAPI

from src.models.job import Job, JobStatus
from src.core.database import get_db
from src.main import app

API_KEY_HEADER = {"X-API-KEY": "test-ci-key"}

@pytest.fixture
async def client_no_auth(db_session: AsyncSession) -> AsyncClient:
    app.dependency_overrides[get_db] = lambda: db_session
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac
    app.dependency_overrides.clear()

@pytest.fixture(autouse=True)
def _set_test_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ADMIN_API_KEY", "test-ci-key")
    from src.main import settings_on_startup
    settings_on_startup.admin_api_key = "test-ci-key"
    for middleware in app.user_middleware:
        if middleware.cls.__name__ == 'AuthMiddleware':
            middleware.kwargs['admin_api_key'] = "test-ci-key"
            from src.core.security.ip_rate_limiter import InMemoryRateLimiter
            middleware.kwargs['rate_limiter'] = InMemoryRateLimiter(max_requests=10000, window_seconds=60)

@pytest.fixture
async def client(client_no_auth: AsyncClient) -> AsyncClient:
    """Provide an AsyncClient with the correct test auth headers."""
    client_no_auth.headers.update(API_KEY_HEADER)
    yield client_no_auth


@pytest.fixture
async def job_factory(db_session: AsyncSession):
    """Fixture to create a test job in the database."""
    async def _create_job(
        job_type="test_job",
        status=JobStatus.QUEUED,
        attempt_count=0,
        max_attempts=3,
        error_code=None,
        error_message=None
    ):
        job = Job(
            job_type=job_type,
            status=status,
            payload_json='{"key": "value"}',
            attempt_count=attempt_count,
            max_attempts=max_attempts,
            error_code=error_code,
            error_message=error_message
        )
        db_session.add(job)
        await db_session.flush()
        return job
    return _create_job


@pytest.mark.asyncio
async def test_list_jobs_success(client: AsyncClient, job_factory):
    """Test GET /api/v1/admin/jobs returns a paginated list of jobs."""
    await job_factory(job_type="type_a", status=JobStatus.QUEUED)
    await job_factory(job_type="type_a", status=JobStatus.SUCCESS)
    await job_factory(job_type="type_b", status=JobStatus.FAILED)

    # List all jobs
    response = await client.get(
        "/api/v1/admin/jobs",
        headers=API_KEY_HEADER
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["items"]) == 3

    # Filter by job_type
    response = await client.get(
        "/api/v1/admin/jobs?job_type=type_a",
        headers=API_KEY_HEADER
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2

    # Filter by status
    response = await client.get(
        "/api/v1/admin/jobs?status=failed",
        headers=API_KEY_HEADER
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["status"] == "failed"


@pytest.mark.asyncio
async def test_get_job_success(client: AsyncClient, job_factory):
    """Test GET /api/v1/admin/jobs/{job_id} returns a single job."""
    job = await job_factory()

    response = await client.get(
        f"/api/v1/admin/jobs/{job.id}",
        headers=API_KEY_HEADER
    )
    assert response.status_code == 200
    data = response.json()
    print("response data", data)
    assert data["id"] == str(job.id)


@pytest.mark.asyncio
async def test_retry_job_success(client: AsyncClient, job_factory, db_session: AsyncSession):
    """Test POST /api/v1/admin/jobs/{job_id}/retry succeeds on retryable failed job."""
    job = await job_factory(
        status=JobStatus.FAILED,
        attempt_count=1,
        max_attempts=3,
        error_code="TEST_ERROR",
        error_message="A bad thing happened"
    )

    response = await client.post(
        f"/api/v1/admin/jobs/{job.id}/retry",
        headers=API_KEY_HEADER
    )

    assert response.status_code == 202
    data = response.json()
    assert data["job_id"] == str(job.id)

    # Check DB state
    await db_session.refresh(job)
    assert job.status == JobStatus.QUEUED
    assert job.error_code is None
    assert job.error_message is None
    assert job.attempt_count == 2


@pytest.mark.asyncio
async def test_retry_job_not_found(client: AsyncClient):
    """Test POST /api/v1/admin/jobs/{job_id}/retry returns 404 if not found."""
    response = await client.post(
        "/api/v1/admin/jobs/99999/retry",
        headers=API_KEY_HEADER
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_retry_job_not_failed(client: AsyncClient, job_factory):
    """Test POST /api/v1/admin/jobs/{job_id}/retry returns 409 if job is not failed."""
    job = await job_factory(status=JobStatus.SUCCESS)

    response = await client.post(
        f"/api/v1/admin/jobs/{job.id}/retry",
        headers=API_KEY_HEADER
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_retry_job_exhausted(client: AsyncClient, job_factory):
    """Test POST /api/v1/admin/jobs/{job_id}/retry returns 409 if attempts are maxed out."""
    job = await job_factory(status=JobStatus.FAILED, attempt_count=3, max_attempts=3)

    response = await client.post(
        f"/api/v1/admin/jobs/{job.id}/retry",
        headers=API_KEY_HEADER
    )
    assert response.status_code == 409
