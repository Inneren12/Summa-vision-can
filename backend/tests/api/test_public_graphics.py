"""Unit tests for the public gallery API — ``GET /api/v1/public/graphics``.

Tests exercise:
1. Pagination (limit/offset passthrough and capping).
2. JSON schema matches ``PublicationResponse``.
3. ``Cache-Control: public, max-age=3600`` header is present.
4. Rate limiting — 31st request from same IP returns HTTP 429.
5. ``preview_url`` is populated from mocked ``generate_presigned_url()``.
6. Sort parameter validation (newest, oldest, score, invalid).
7. Default query parameter values.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routers.public_graphics import (
    PaginatedGraphicsResponse,
    PublicationResponse,
    _get_repo,
    _get_storage,
    get_gallery_limiter,
    router,
)
from src.core.security.ip_rate_limiter import InMemoryRateLimiter
from src.core.storage import StorageInterface, StorageObjectMetadata


# ---------------------------------------------------------------------------
# Helpers & Fixtures
# ---------------------------------------------------------------------------


class _FakePublication:
    """Minimal stand-in for the Publication ORM model."""

    def __init__(
        self,
        id: int,
        headline: str,
        chart_type: str,
        virality_score: float,
        s3_key_lowres: str | None,
        s3_key_highres: str | None,
        created_at: datetime,
        status: str = "PUBLISHED",
        slug: str | None = None,
    ) -> None:
        self.id = id
        self.headline = headline
        self.chart_type = chart_type
        self.virality_score = virality_score
        self.s3_key_lowres = s3_key_lowres
        self.s3_key_highres = s3_key_highres
        self.created_at = created_at
        self.status = status
        self.slug = slug if slug is not None else f"headline-{id}"


def _make_publications(count: int = 3) -> list[_FakePublication]:
    """Create a list of fake published publications."""
    return [
        _FakePublication(
            id=i + 1,
            headline=f"Headline {i + 1}",
            chart_type="bar",
            virality_score=0.5 + (i * 0.1),
            s3_key_lowres=f"graphics/{i + 1}/preview.png",
            s3_key_highres=f"graphics/{i + 1}/full.png",
            created_at=datetime(2026, 3, 10 + i, tzinfo=timezone.utc),
        )
        for i in range(count)
    ]


class _MockStorage(StorageInterface):
    """Minimal mock storage that returns predictable presigned URLs."""

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

    async def iter_objects_with_metadata(self, prefix: str):
        yield []

    async def generate_presigned_url(self, path: str, ttl: int = 3600) -> str:
        return f"https://cdn.example.com/{path}?ttl={ttl}"

    async def delete_object(self, key: str) -> None:
        pass


def _build_test_app(
    publications: list[_FakePublication] | None = None,
    limiter: InMemoryRateLimiter | None = None,
) -> FastAPI:
    """Create an isolated FastAPI app with overridden dependencies."""
    test_app = FastAPI()
    test_app.include_router(router)

    pubs = publications if publications is not None else _make_publications()

    # --- Mock repo ---
    mock_repo = MagicMock()
    mock_repo.get_published_sorted = AsyncMock(return_value=pubs)

    test_app.dependency_overrides[_get_repo] = lambda: mock_repo
    test_app.dependency_overrides[_get_storage] = lambda: _MockStorage()
    if limiter is not None:
        test_app.dependency_overrides[get_gallery_limiter] = lambda: limiter

    return test_app


# ---------------------------------------------------------------------------
# Tests — Pagination
# ---------------------------------------------------------------------------


class TestPagination:
    """Pagination limit and offset are passed correctly."""

    def test_default_pagination(self) -> None:
        """Without explicit params, limit=12 and offset=0 should be used."""
        app = _build_test_app([])
        client = TestClient(app)
        resp = client.get("/api/v1/public/graphics")
        assert resp.status_code == 200
        data = resp.json()
        assert data["limit"] == 12
        assert data["offset"] == 0

    def test_custom_limit_and_offset(self) -> None:
        """Custom limit and offset should be reflected in the response."""
        app = _build_test_app([])
        client = TestClient(app)
        resp = client.get("/api/v1/public/graphics?limit=5&offset=10")
        assert resp.status_code == 200
        data = resp.json()
        assert data["limit"] == 5
        assert data["offset"] == 10

    def test_limit_exceeds_50_returns_422(self) -> None:
        """``limit > 50`` should be rejected with 422."""
        app = _build_test_app()
        client = TestClient(app)
        resp = client.get("/api/v1/public/graphics?limit=51")
        assert resp.status_code == 422

    def test_limit_zero_returns_422(self) -> None:
        """``limit=0`` should be rejected with 422."""
        app = _build_test_app()
        client = TestClient(app)
        resp = client.get("/api/v1/public/graphics?limit=0")
        assert resp.status_code == 422

    def test_negative_offset_returns_422(self) -> None:
        """``offset=-1`` should be rejected with 422."""
        app = _build_test_app()
        client = TestClient(app)
        resp = client.get("/api/v1/public/graphics?offset=-1")
        assert resp.status_code == 422

    def test_limit_and_offset_passed_to_repo(self) -> None:
        """The repo should receive the exact limit/offset values."""
        app = _build_test_app([])
        mock_repo = MagicMock()
        mock_repo.get_published_sorted = AsyncMock(return_value=[])
        app.dependency_overrides[_get_repo] = lambda: mock_repo

        client = TestClient(app)
        client.get("/api/v1/public/graphics?limit=7&offset=14&sort=oldest")

        mock_repo.get_published_sorted.assert_called_once_with(
            limit=7, offset=14, sort="oldest"
        )


# ---------------------------------------------------------------------------
# Tests — JSON Schema
# ---------------------------------------------------------------------------


class TestJsonSchema:
    """Response body matches ``PublicationResponse`` schema."""

    def test_response_contains_expected_fields(self) -> None:
        """Each item must have id, headline, chart_type, virality_score,
        preview_url, and created_at."""
        pubs = _make_publications(2)
        app = _build_test_app(pubs)
        client = TestClient(app)
        resp = client.get("/api/v1/public/graphics")
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 2

        for item in items:
            assert "id" in item
            assert "headline" in item
            assert "chart_type" in item
            assert "virality_score" in item
            assert "preview_url" in item
            assert "created_at" in item

    def test_s3_keys_not_exposed(self) -> None:
        """Internal S3 keys must NOT appear in the response."""
        pubs = _make_publications(1)
        app = _build_test_app(pubs)
        client = TestClient(app)
        resp = client.get("/api/v1/public/graphics")
        item = resp.json()["items"][0]
        assert "s3_key_lowres" not in item
        assert "s3_key_highres" not in item

    def test_publication_response_schema_from_attributes(self) -> None:
        """PublicationResponse can be constructed with from_attributes mode."""
        resp = PublicationResponse(
            id=1,
            headline="Test",
            chart_type="bar",
            virality_score=0.8,
            preview_url="https://example.com/img.png",
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        data = resp.model_dump()
        assert data["id"] == 1
        assert data["headline"] == "Test"


# ---------------------------------------------------------------------------
# Tests — Cache-Control Header
# ---------------------------------------------------------------------------


class TestCacheControl:
    """``Cache-Control: public, max-age=3600`` must be present on 200."""

    def test_cache_control_header_present(self) -> None:
        """The ``Cache-Control`` header should be set on every 200 response."""
        app = _build_test_app([])
        client = TestClient(app)
        resp = client.get("/api/v1/public/graphics")
        assert resp.status_code == 200
        assert resp.headers.get("cache-control") == "public, max-age=3600"

    def test_cache_control_header_with_results(self) -> None:
        """The header is present even when items are in the response."""
        pubs = _make_publications(5)
        app = _build_test_app(pubs)
        client = TestClient(app)
        resp = client.get("/api/v1/public/graphics")
        assert resp.status_code == 200
        assert resp.headers.get("cache-control") == "public, max-age=3600"


# ---------------------------------------------------------------------------
# Tests — Rate Limiting
# ---------------------------------------------------------------------------


class TestRateLimiting:
    """IP-based rate limiting at 30 req/min."""

    def test_rate_limit_exceeded_returns_429(self) -> None:
        """The 31st request within 60 seconds from the same IP should get 429."""
        limiter = InMemoryRateLimiter(max_requests=30, window_seconds=60)
        app = _build_test_app([], limiter)
        client = TestClient(app)

        # First 30 pass
        for i in range(30):
            resp = client.get("/api/v1/public/graphics")
            assert resp.status_code == 200, f"Request {i + 1} should pass"

        # 31st should be rejected
        resp = client.get("/api/v1/public/graphics")
        assert resp.status_code == 429
        assert resp.json()["detail"] == "Rate limit exceeded. Try again later."

    def test_rate_limit_allows_within_limit(self) -> None:
        """Requests within the limit should all succeed."""
        limiter = InMemoryRateLimiter(max_requests=30, window_seconds=60)
        app = _build_test_app([], limiter)
        client = TestClient(app)

        for _ in range(10):
            resp = client.get("/api/v1/public/graphics")
            assert resp.status_code == 200

    def test_429_does_not_have_cache_control(self) -> None:
        """Rate-limited responses should NOT have Cache-Control header."""
        limiter = InMemoryRateLimiter(max_requests=1, window_seconds=60)
        app = _build_test_app([], limiter)
        client = TestClient(app)

        # Exhaust the limit
        resp = client.get("/api/v1/public/graphics")
        assert resp.status_code == 200

        # This should be 429
        resp = client.get("/api/v1/public/graphics")
        assert resp.status_code == 429
        # 429 responses should NOT have Cache-Control
        assert "cache-control" not in resp.headers


# ---------------------------------------------------------------------------
# Tests — Presigned URL
# ---------------------------------------------------------------------------


class TestPresignedUrl:
    """``preview_url`` is populated from ``generate_presigned_url()``."""

    def test_preview_url_from_storage(self) -> None:
        """Each item's ``preview_url`` should be from the mock storage."""
        pubs = _make_publications(2)
        app = _build_test_app(pubs)
        client = TestClient(app)
        resp = client.get("/api/v1/public/graphics")
        items = resp.json()["items"]

        for i, item in enumerate(items):
            expected_path = f"graphics/{i + 1}/preview.png"
            assert item["preview_url"] == f"https://cdn.example.com/{expected_path}?ttl=3600"

    def test_preview_url_empty_when_no_s3_key(self) -> None:
        """When ``s3_key_lowres`` is None, ``preview_url`` should be empty."""
        pub = _FakePublication(
            id=99,
            headline="No Preview",
            chart_type="pie",
            virality_score=0.3,
            s3_key_lowres=None,
            s3_key_highres=None,
            created_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
        )
        app = _build_test_app([pub])
        client = TestClient(app)
        resp = client.get("/api/v1/public/graphics")
        item = resp.json()["items"][0]
        assert item["preview_url"] == ""


# ---------------------------------------------------------------------------
# Tests — Sort Parameter
# ---------------------------------------------------------------------------


class TestSortParameter:
    """Sort parameter validation and passthrough."""

    def test_default_sort_is_newest(self) -> None:
        """Without explicit sort, 'newest' should be the default."""
        app = _build_test_app([])
        mock_repo = MagicMock()
        mock_repo.get_published_sorted = AsyncMock(return_value=[])
        app.dependency_overrides[_get_repo] = lambda: mock_repo

        client = TestClient(app)
        client.get("/api/v1/public/graphics")

        mock_repo.get_published_sorted.assert_called_once_with(
            limit=12, offset=0, sort="newest"
        )

    def test_sort_oldest(self) -> None:
        """``sort=oldest`` should be passed to the repo."""
        app = _build_test_app([])
        mock_repo = MagicMock()
        mock_repo.get_published_sorted = AsyncMock(return_value=[])
        app.dependency_overrides[_get_repo] = lambda: mock_repo

        client = TestClient(app)
        client.get("/api/v1/public/graphics?sort=oldest")

        mock_repo.get_published_sorted.assert_called_once_with(
            limit=12, offset=0, sort="oldest"
        )

    def test_sort_score(self) -> None:
        """``sort=score`` should be passed to the repo."""
        app = _build_test_app([])
        mock_repo = MagicMock()
        mock_repo.get_published_sorted = AsyncMock(return_value=[])
        app.dependency_overrides[_get_repo] = lambda: mock_repo

        client = TestClient(app)
        client.get("/api/v1/public/graphics?sort=score")

        mock_repo.get_published_sorted.assert_called_once_with(
            limit=12, offset=0, sort="score"
        )

    def test_invalid_sort_returns_422(self) -> None:
        """An unrecognized sort value should return 422."""
        app = _build_test_app()
        client = TestClient(app)
        resp = client.get("/api/v1/public/graphics?sort=random")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Tests — InMemoryRateLimiter unit tests
# ---------------------------------------------------------------------------


class TestInMemoryRateLimiter:
    """Direct unit tests for the rate limiter class."""

    def test_allows_requests_within_limit(self) -> None:
        """Requests within max_requests should be allowed."""
        limiter = InMemoryRateLimiter(max_requests=5, window_seconds=60)
        for _ in range(5):
            assert limiter.is_allowed("192.168.1.1")

    def test_denies_over_limit(self) -> None:
        """The request after max_requests should be denied."""
        limiter = InMemoryRateLimiter(max_requests=3, window_seconds=60)
        for _ in range(3):
            assert limiter.is_allowed("10.0.0.1")
        assert not limiter.is_allowed("10.0.0.1")

    def test_different_ips_are_independent(self) -> None:
        """Different IPs should have separate counters."""
        limiter = InMemoryRateLimiter(max_requests=1, window_seconds=60)
        assert limiter.is_allowed("10.0.0.1")
        assert not limiter.is_allowed("10.0.0.1")
        # Different IP should still be allowed.
        assert limiter.is_allowed("10.0.0.2")

    def test_reset_clears_all_state(self) -> None:
        """``reset()`` should clear all tracked requests."""
        limiter = InMemoryRateLimiter(max_requests=1, window_seconds=60)
        assert limiter.is_allowed("10.0.0.1")
        assert not limiter.is_allowed("10.0.0.1")
        limiter.reset()
        assert limiter.is_allowed("10.0.0.1")

    def test_invalid_max_requests_raises(self) -> None:
        """max_requests <= 0 should raise ValueError."""
        import pytest
        with pytest.raises(ValueError, match="max_requests"):
            InMemoryRateLimiter(max_requests=0, window_seconds=60)

    def test_invalid_window_seconds_raises(self) -> None:
        """window_seconds <= 0 should raise ValueError."""
        import pytest
        with pytest.raises(ValueError, match="window_seconds"):
            InMemoryRateLimiter(max_requests=5, window_seconds=0)

    def test_properties(self) -> None:
        """Properties should expose constructor values."""
        limiter = InMemoryRateLimiter(max_requests=30, window_seconds=60)
        assert limiter.max_requests == 30
        assert limiter.window_seconds == 60


# ---------------------------------------------------------------------------
# Tests — PaginatedGraphicsResponse Schema
# ---------------------------------------------------------------------------


class TestPaginatedGraphicsResponseSchema:
    """Pydantic schema round-trip tests."""

    def test_round_trip(self) -> None:
        """Paginated response should serialise correctly."""
        item = PublicationResponse(
            id=1,
            headline="Test Graphic",
            chart_type="bar",
            virality_score=0.9,
            preview_url="https://cdn.example.com/preview.png",
            created_at=datetime(2026, 3, 15, tzinfo=timezone.utc),
        )
        response = PaginatedGraphicsResponse(
            items=[item], limit=12, offset=0
        )
        data = response.model_dump()
        assert len(data["items"]) == 1
        assert data["limit"] == 12
        assert data["offset"] == 0

    def test_empty_items(self) -> None:
        """An empty items list should be valid."""
        response = PaginatedGraphicsResponse(items=[], limit=12, offset=0)
        data = response.model_dump()
        assert data["items"] == []


# ---------------------------------------------------------------------------
# Tests — Empty results
# ---------------------------------------------------------------------------


class TestEmptyResults:
    """Edge case: no published graphics."""

    def test_empty_gallery(self) -> None:
        """When no publications exist, items should be an empty list."""
        app = _build_test_app([])
        client = TestClient(app)
        resp = client.get("/api/v1/public/graphics")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["limit"] == 12
        assert data["offset"] == 0
