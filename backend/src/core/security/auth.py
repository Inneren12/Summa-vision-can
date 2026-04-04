"""API Key authentication middleware for admin namespace.

Protects all routes under ``/api/v1/admin/*`` with ``X-API-KEY`` header auth.
Public routes (``/api/v1/public/*``, ``/api/health``, ``/docs``,
``/openapi.json``, ``/redoc``) bypass this middleware entirely.

Architecture:
    Follows ARCH-DPEN-001 — ``admin_api_key`` and ``rate_limiter`` are
    injected via constructor; this class never reads ``os.environ`` directly.

# TODO (future B2B expansion): Replace X-API-KEY with JWT Bearer tokens.
# Each B2B client will receive a signed JWT with claims:
#   - sub: client_id
#   - scope: ["read:graphics", "write:graphics"]
#   - exp: expiry timestamp
# Validate via: python-jose or PyJWT with RS256 public key.
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from src.core.security.ip_rate_limiter import InMemoryRateLimiter

# Paths that bypass authentication entirely.
_BYPASS_PREFIXES: tuple[str, ...] = (
    "/api/v1/public/",
)
_BYPASS_EXACT: frozenset[str] = frozenset({
    "/api/health",
    "/docs",
    "/openapi.json",
    "/redoc",
})

# Paths that require admin API key authentication.
_ADMIN_PREFIX: str = "/api/v1/admin/"


class AuthMiddleware(BaseHTTPMiddleware):
    """API Key authentication middleware for admin namespace.

    Protects all routes under ``/api/v1/admin/*`` with ``X-API-KEY`` header
    auth.  Public routes (``/api/v1/public/*``, ``/api/health``, ``/docs``,
    ``/openapi.json``, ``/redoc``) bypass this middleware entirely.

    Parameters
    ----------
    app:
        The ASGI application to wrap.
    admin_api_key:
        The expected API key value.  If empty, admin endpoints return
        HTTP 503 ("Admin API key not configured").
    rate_limiter:
        Optional :class:`InMemoryRateLimiter` for secondary rate limiting
        of admin endpoints (default: 10 req/min).

    # TODO (future B2B expansion): Replace X-API-KEY with JWT Bearer tokens.
    # Each B2B client will receive a signed JWT with claims:
    #   - sub: client_id
    #   - scope: ["read:graphics", "write:graphics"]
    #   - exp: expiry timestamp
    # Validate via: python-jose or PyJWT with RS256 public key.
    """

    def __init__(
        self,
        app: object,
        *,
        admin_api_key: str,
        rate_limiter: InMemoryRateLimiter | None = None,
    ) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self._admin_api_key: str = admin_api_key
        self._rate_limiter: InMemoryRateLimiter = rate_limiter or InMemoryRateLimiter(
            max_requests=10,
            window_seconds=60,
        )

    async def dispatch(self, request: Request, call_next: object) -> Response:
        """Route requests through auth checks for admin paths.

        Decision tree:

        1. **Bypass paths** — pass through without any checks.
        2. **Admin paths** — validate API key, then apply rate limit.
        3. **All other paths** — pass through without checks.

        Parameters
        ----------
        request:
            The incoming Starlette request.
        call_next:
            Callable to invoke the next middleware or route handler.

        Returns
        -------
        Response
            Either the upstream response or a JSON error response
            (401 / 429 / 503).
        """
        path: str = request.url.path

        # 1. Bypass paths — skip authentication entirely
        if path in _BYPASS_EXACT:
            return await call_next(request)  # type: ignore[misc]

        for prefix in _BYPASS_PREFIXES:
            if path.startswith(prefix):
                return await call_next(request)  # type: ignore[misc]

        # 2. Admin paths — require API key + rate limit
        if path.startswith(_ADMIN_PREFIX):
            # 2a. Check that admin_api_key is configured
            if self._admin_api_key == "":
                return JSONResponse(
                    {"error": "Admin API key not configured"},
                    status_code=401,
                )

            # 2b. Extract and validate API key from header
            api_key: str = request.headers.get("X-API-KEY", "")

            if api_key == "":
                return JSONResponse(
                    {"error": "Missing X-API-KEY header"},
                    status_code=401,
                )

            if api_key != self._admin_api_key:
                return JSONResponse(
                    {"error": "Invalid API key"},
                    status_code=401,
                )

            # 2c. Secondary rate limit keyed by first 8 chars of API key
            client_key: str = api_key[:8]
            if not self._rate_limiter.is_allowed(client_key):
                return JSONResponse(
                    {"error": "Rate limit exceeded. Max 10 requests/min for admin endpoints."},
                    status_code=429,
                )

            return await call_next(request)  # type: ignore[misc]

        # 3. All other paths — pass through
        return await call_next(request)  # type: ignore[misc]
