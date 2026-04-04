"""Unit tests for ``AuthMiddleware`` — API key authentication for admin namespace.

Tests exercise:
1. Admin endpoints require ``X-API-KEY`` header → 401 if missing or wrong.
2. Valid key returns the upstream response (200).
3. Public endpoints (``/api/v1/public/*``) bypass auth → 200 without key.
4. Health endpoint (``/api/health``) bypasses auth → 200 without key.
5. Docs/OpenAPI endpoints bypass auth.
6. Unconfigured API key (``""``) returns 503 for admin paths.
7. Rate limiting: 11th request with valid key returns 429.
8. Rate limiting does NOT affect public endpoints.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from src.core.security.auth import AuthMiddleware
from src.core.security.ip_rate_limiter import InMemoryRateLimiter


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_VALID_KEY = "test-admin-api-key-12345"
_WRONG_KEY = "wrong-key-xxxx"


# ---------------------------------------------------------------------------
# Helpers — build minimal FastAPI apps with AuthMiddleware
# ---------------------------------------------------------------------------


def _build_app(
    *,
    admin_api_key: str = _VALID_KEY,
    rate_limiter: InMemoryRateLimiter | None = None,
    include_admin: bool = True,
    include_public: bool = True,
    include_health: bool = True,
    include_docs: bool = True,
) -> FastAPI:
    """Create a minimal FastAPI app with AuthMiddleware for testing.

    Each test gets its own fresh app instance so rate limiter state and
    middleware configuration are fully isolated.
    """
    app = FastAPI(
        docs_url="/docs" if include_docs else None,
        redoc_url="/redoc" if include_docs else None,
    )

    # --- Admin router ---
    if include_admin:
        admin_router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

        @admin_router.get("/queue")
        async def admin_queue() -> dict[str, str]:
            return {"queue": "ok"}

        @admin_router.post("/graphics/generate")
        async def admin_generate() -> dict[str, str]:
            return {"generate": "ok"}

        app.include_router(admin_router)

    # --- Public router ---
    if include_public:
        public_router = APIRouter(prefix="/api/v1/public", tags=["public"])

        @public_router.get("/graphics")
        async def public_graphics() -> dict[str, str]:
            return {"graphics": "ok"}

        app.include_router(public_router)

    # --- Health endpoint ---
    if include_health:

        @app.get("/api/health")
        async def health() -> dict[str, str]:
            return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}

    # --- Register AuthMiddleware AFTER routers ---
    app.add_middleware(
        AuthMiddleware,
        admin_api_key=admin_api_key,
        rate_limiter=rate_limiter,
    )

    return app


def _client(
    *,
    admin_api_key: str = _VALID_KEY,
    rate_limiter: InMemoryRateLimiter | None = None,
    **kwargs: Any,
) -> TestClient:
    """Shorthand: build app + TestClient in one call."""
    app = _build_app(admin_api_key=admin_api_key, rate_limiter=rate_limiter, **kwargs)
    return TestClient(app)


# ---------------------------------------------------------------------------
# Tests — Admin endpoint without key → 401
# ---------------------------------------------------------------------------


class TestAdminEndpointWithoutKey:
    """``GET /api/v1/admin/queue`` without ``X-API-KEY`` header → 401."""

    def test_admin_endpoint_without_key_returns_401(self) -> None:
        client = _client()
        resp = client.get("/api/v1/admin/queue")
        assert resp.status_code == 401
        body = resp.json()
        assert "error" in body
        assert body["error"] == "Missing X-API-KEY header"

    def test_admin_post_endpoint_without_key_returns_401(self) -> None:
        client = _client()
        resp = client.post("/api/v1/admin/graphics/generate")
        assert resp.status_code == 401
        body = resp.json()
        assert "error" in body


# ---------------------------------------------------------------------------
# Tests — Admin endpoint with invalid key → 401
# ---------------------------------------------------------------------------


class TestAdminEndpointWithInvalidKey:
    """``GET /api/v1/admin/queue`` with wrong ``X-API-KEY`` → 401."""

    def test_admin_endpoint_with_invalid_key_returns_401(self) -> None:
        client = _client()
        resp = client.get(
            "/api/v1/admin/queue",
            headers={"X-API-KEY": _WRONG_KEY},
        )
        assert resp.status_code == 401
        body = resp.json()
        assert "error" in body
        assert body["error"] == "Invalid API key"

    def test_admin_endpoint_with_empty_key_returns_401(self) -> None:
        """An explicitly empty X-API-KEY header is treated as missing."""
        client = _client()
        resp = client.get(
            "/api/v1/admin/queue",
            headers={"X-API-KEY": ""},
        )
        assert resp.status_code == 401
        body = resp.json()
        assert body["error"] == "Missing X-API-KEY header"


# ---------------------------------------------------------------------------
# Tests — Admin endpoint with valid key → 200
# ---------------------------------------------------------------------------


class TestAdminEndpointWithValidKey:
    """``GET /api/v1/admin/queue`` with correct ``X-API-KEY`` → 200."""

    def test_admin_endpoint_with_valid_key_returns_200(self) -> None:
        client = _client()
        resp = client.get(
            "/api/v1/admin/queue",
            headers={"X-API-KEY": _VALID_KEY},
        )
        assert resp.status_code == 200
        assert resp.json() == {"queue": "ok"}

    def test_admin_post_endpoint_with_valid_key_returns_200(self) -> None:
        client = _client()
        resp = client.post(
            "/api/v1/admin/graphics/generate",
            headers={"X-API-KEY": _VALID_KEY},
        )
        assert resp.status_code == 200
        assert resp.json() == {"generate": "ok"}


# ---------------------------------------------------------------------------
# Tests — Public endpoint without key → 200
# ---------------------------------------------------------------------------


class TestPublicEndpointBypassesAuth:
    """``GET /api/v1/public/graphics`` without ``X-API-KEY`` → 200."""

    def test_public_endpoint_without_key_returns_200(self) -> None:
        client = _client()
        resp = client.get("/api/v1/public/graphics")
        assert resp.status_code == 200
        assert resp.json() == {"graphics": "ok"}

    def test_public_endpoint_with_wrong_key_still_200(self) -> None:
        """Public endpoints ignore the API key entirely."""
        client = _client()
        resp = client.get(
            "/api/v1/public/graphics",
            headers={"X-API-KEY": _WRONG_KEY},
        )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Tests — Health endpoint bypasses auth → 200
# ---------------------------------------------------------------------------


class TestHealthEndpointBypassesAuth:
    """``GET /api/health`` without ``X-API-KEY`` → 200."""

    def test_health_endpoint_bypasses_auth(self) -> None:
        client = _client()
        resp = client.get("/api/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert "timestamp" in body


# ---------------------------------------------------------------------------
# Tests — Docs bypass auth
# ---------------------------------------------------------------------------


class TestDocsEndpointsbypassAuth:
    """``/docs`` and ``/openapi.json`` bypass auth."""

    def test_docs_bypass_auth(self) -> None:
        client = _client()
        resp = client.get("/docs")
        # FastAPI /docs returns 200 HTML
        assert resp.status_code == 200

    def test_openapi_json_bypass_auth(self) -> None:
        client = _client()
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        assert "openapi" in resp.json()

    def test_redoc_bypass_auth(self) -> None:
        client = _client()
        resp = client.get("/redoc")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Tests — Unconfigured API key → 401
# ---------------------------------------------------------------------------


class TestUnconfiguredApiKey:
    """When admin_api_key is empty string, admin endpoints return 401."""

    def test_unconfigured_api_key_returns_401(self) -> None:
        client = _client(admin_api_key="")
        resp = client.get("/api/v1/admin/queue")
        assert resp.status_code == 401
        body = resp.json()
        assert "error" in body
        assert body["error"] == "Admin API key not configured"

    def test_unconfigured_key_does_not_affect_public(self) -> None:
        """Public endpoints should still work when admin key is empty."""
        client = _client(admin_api_key="")
        resp = client.get("/api/v1/public/graphics")
        assert resp.status_code == 200

    def test_unconfigured_key_does_not_affect_health(self) -> None:
        """Health endpoint should still work when admin key is empty."""
        client = _client(admin_api_key="")
        resp = client.get("/api/health")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Tests — Rate Limiting (10 req/min for admin)
# ---------------------------------------------------------------------------


class TestRateLimitAdmin:
    """Secondary rate limit: ten requests per minute for admin endpoints with valid key."""

    def test_rate_limit_after_10_requests_returns_429(self) -> None:
        """First 10 requests pass, requests 11-15 return 429."""
        limiter = InMemoryRateLimiter(max_requests=10, window_seconds=60)
        client = _client(rate_limiter=limiter)

        # First 10 requests should pass
        for i in range(10):
            resp = client.get(
                "/api/v1/admin/queue",
                headers={"X-API-KEY": _VALID_KEY},
            )
            assert resp.status_code == 200, f"Request {i + 1} should return 200"

        # Requests 11-15 should be rate limited
        for i in range(5):
            resp = client.get(
                "/api/v1/admin/queue",
                headers={"X-API-KEY": _VALID_KEY},
            )
            assert resp.status_code == 429, f"Request {11 + i} should return 429"
            body = resp.json()
            assert "error" in body
            assert "Rate limit exceeded" in body["error"]

    def test_rate_limit_does_not_affect_public_endpoints(self) -> None:
        """Public endpoints have no secondary rate limit from AuthMiddleware."""
        limiter = InMemoryRateLimiter(max_requests=10, window_seconds=60)
        client = _client(rate_limiter=limiter)

        # Send 20 requests to public endpoint — all should succeed
        for i in range(20):
            resp = client.get("/api/v1/public/graphics")
            assert resp.status_code == 200, f"Request {i + 1} should return 200"

    def test_rate_limit_does_not_affect_health_endpoint(self) -> None:
        """Health endpoint has no secondary rate limit."""
        limiter = InMemoryRateLimiter(max_requests=10, window_seconds=60)
        client = _client(rate_limiter=limiter)

        for _ in range(15):
            resp = client.get("/api/health")
            assert resp.status_code == 200

    def test_rate_limit_keyed_by_api_key_prefix(self) -> None:
        """Rate limit is keyed by first 8 chars of the API key."""
        limiter = InMemoryRateLimiter(max_requests=2, window_seconds=60)
        # Use a key where first 8 chars differ from default
        custom_key = "AAAAAAAAcustom-rest"
        client = _client(admin_api_key=custom_key, rate_limiter=limiter)

        # 2 requests should pass
        for _ in range(2):
            resp = client.get(
                "/api/v1/admin/queue",
                headers={"X-API-KEY": custom_key},
            )
            assert resp.status_code == 200

        # 3rd should be rate limited
        resp = client.get(
            "/api/v1/admin/queue",
            headers={"X-API-KEY": custom_key},
        )
        assert resp.status_code == 429

    def test_invalid_key_not_rate_limited(self) -> None:
        """Invalid keys should be rejected at auth level (401), not rate limit."""
        limiter = InMemoryRateLimiter(max_requests=10, window_seconds=60)
        client = _client(rate_limiter=limiter)

        for _ in range(15):
            resp = client.get(
                "/api/v1/admin/queue",
                headers={"X-API-KEY": _WRONG_KEY},
            )
            # Always 401, never 429 — rejected before rate check
            assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Tests — Default rate limiter
# ---------------------------------------------------------------------------


class TestDefaultRateLimiter:
    """When no rate_limiter is provided, a default one is created."""

    def test_default_rate_limiter_created(self) -> None:
        """AuthMiddleware creates a default InMemoryRateLimiter(10, 60)."""
        from starlette.applications import Starlette

        middleware = AuthMiddleware(
            Starlette(),
            admin_api_key="test-key",
        )
        assert middleware._rate_limiter.max_requests == 10
        assert middleware._rate_limiter.window_seconds == 60

    def test_custom_rate_limiter_injected(self) -> None:
        """A custom rate limiter should replace the default."""
        from starlette.applications import Starlette

        custom_limiter = InMemoryRateLimiter(max_requests=5, window_seconds=30)
        middleware = AuthMiddleware(
            Starlette(),
            admin_api_key="test-key",
            rate_limiter=custom_limiter,
        )
        assert middleware._rate_limiter is custom_limiter


# ---------------------------------------------------------------------------
# Tests — Non-admin, non-public paths pass through
# ---------------------------------------------------------------------------


class TestOtherPathsPassThrough:
    """Paths that are neither admin nor public/health/docs pass through."""

    def test_unknown_path_passes_through(self) -> None:
        """A random path not under /api/v1/admin/ should not be blocked."""
        app = _build_app()

        @app.get("/some/other/path")
        async def other() -> dict[str, str]:
            return {"other": "ok"}

        client = TestClient(app)
        resp = client.get("/some/other/path")
        # Should pass through without auth check
        assert resp.status_code == 200
        assert resp.json() == {"other": "ok"}
