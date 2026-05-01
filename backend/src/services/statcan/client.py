"""Resilient StatCan HTTP Client with structured logging and retry logic.

Wraps :class:`httpx.AsyncClient` to enforce:

1. **Maintenance window guard** — blocks requests during the StatCan WDS
   daily maintenance window and raises :class:`DataSourceError`.
2. **Token-bucket rate limiting** — ensures outbound throughput stays within
   the StatCan rate-limit policy.
3. **Exponential-backoff retries** — automatically retries on HTTP 429
   (Too Many Requests), 409 (Conflict), and 503 (Service Unavailable)
   up to ``MAX_RETRIES`` times, with structured ``WARNING`` logs on every
   retry attempt.
4. **Structured exception mapping** — all transport-level errors (timeouts,
   connection resets, exhausted retries) are surfaced as
   :class:`DataSourceError` from the unified exception hierarchy.

Usage::

    client = StatCanClient(http, guard, bucket)
    response = await client.get("https://www150.statcan.gc.ca/...")
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Final

import httpx
import structlog

from src.core.exceptions import DataSourceError
from src.core.rate_limit import AsyncTokenBucket
from src.services.statcan.maintenance import StatCanMaintenanceGuard
from src.services.statcan.schemas import CubeMetadataResponse

_GET_CUBE_METADATA_URL: Final[str] = (
    "https://www150.statcan.gc.ca/t1/wds/rest/getCubeMetadata"
)

logger: structlog.stdlib.BoundLogger = structlog.get_logger(
    module="statcan.client",
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_RETRIES: Final[int] = 3
"""Maximum number of retry attempts for retryable HTTP status codes."""

BASE_DELAY: Final[float] = 1.0
"""Initial backoff delay in seconds (doubles each attempt)."""

_RETRYABLE_STATUS_CODES: Final[frozenset[int]] = frozenset({429, 409, 503})
"""HTTP status codes that trigger an automatic retry with backoff."""


class StatCanClient:
    """A resilient wrapper around :class:`httpx.AsyncClient` for StatCan APIs.

    All three collaborators are injected through the constructor so that every
    dependency can be replaced in tests.

    Parameters
    ----------
    http_client:
        A pre-configured ``httpx.AsyncClient``.
    maintenance_guard:
        Instance of :class:`StatCanMaintenanceGuard` used to block requests
        during the daily maintenance window.
    rate_limiter:
        Instance of :class:`AsyncTokenBucket` used to throttle outbound
        request throughput.
    """

    __slots__ = ("_http_client", "_maintenance_guard", "_rate_limiter")

    def __init__(
        self,
        http_client: httpx.AsyncClient,
        maintenance_guard: StatCanMaintenanceGuard,
        rate_limiter: AsyncTokenBucket,
    ) -> None:
        self._http_client: httpx.AsyncClient = http_client
        self._maintenance_guard: StatCanMaintenanceGuard = maintenance_guard
        self._rate_limiter: AsyncTokenBucket = rate_limiter

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get(self, url: str, **kwargs: Any) -> httpx.Response:
        """Convenience wrapper that delegates to :meth:`request` with ``GET``."""
        return await self.request("GET", url, **kwargs)

    async def get_cube_metadata(
        self, product_id: int
    ) -> CubeMetadataResponse | None:
        """POST to ``getCubeMetadata`` and return the validated envelope.

        Returns ``None`` when StatCan responds with a non-``SUCCESS`` status
        (e.g. unknown ``productId``).

        Raises
        ------
        DataSourceError
            For maintenance window, network, or retry-exhausted failures
            (existing :meth:`request` behavior).
        """
        response = await self.request(
            "POST",
            _GET_CUBE_METADATA_URL,
            json=[{"productId": product_id}],
        )
        # ``request`` only retries on {429, 409, 503} and returns any other
        # non-2xx response unwrapped. A raw ``raise_for_status()`` would leak
        # ``httpx.HTTPStatusError`` past the StatCan service boundary; cache-
        # required mode upstream needs to see ``DataSourceError`` only.
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise DataSourceError(
                message=(
                    f"StatCan returned HTTP {exc.response.status_code} "
                    f"for getCubeMetadata"
                ),
                error_code="DATASOURCE_HTTP_ERROR",
                context={
                    "url": _GET_CUBE_METADATA_URL,
                    "method": "POST",
                    "status_code": exc.response.status_code,
                    "product_id": product_id,
                },
            ) from exc
        payload = response.json()
        if not isinstance(payload, list) or not payload:
            return None
        envelope = payload[0]
        if envelope.get("status") != "SUCCESS" or "object" not in envelope:
            return None
        return CubeMetadataResponse.model_validate(envelope["object"])

    async def request(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """Execute an HTTP request with guard, rate-limit, and retry logic.

        Parameters
        ----------
        method:
            HTTP method (e.g. ``"GET"``, ``"POST"``).
        url:
            Fully-qualified URL to call.
        **kwargs:
            Forwarded verbatim to ``httpx.AsyncClient.request``.

        Returns
        -------
        httpx.Response
            The successful HTTP response.

        Raises
        ------
        DataSourceError
            * If the request is attempted during the maintenance window.
            * If a network/timeout error occurs.
            * If retries are exhausted for a retryable HTTP status code.
        """
        # 1. Maintenance-window check
        now: datetime = datetime.now(timezone.utc)
        if self._maintenance_guard.is_maintenance_window(now):
            raise DataSourceError(
                message="Cannot execute request: StatCan API is in maintenance window.",
                error_code="DATASOURCE_MAINTENANCE",
                context={"url": url, "method": method},
            )

        # 2. Retry loop with exponential backoff
        last_response: httpx.Response | None = None

        for attempt in range(MAX_RETRIES + 1):
            # 2a. Acquire a rate-limit token
            await self._rate_limiter.acquire()

            # 2b. Execute the HTTP call
            try:
                response: httpx.Response = await self._http_client.request(
                    method, url, **kwargs
                )
            except (httpx.TimeoutException, httpx.RequestError) as exc:
                raise DataSourceError(
                    message=f"Network error during StatCan request: {exc}",
                    error_code="DATASOURCE_NETWORK_ERROR",
                    context={"url": url, "method": method},
                ) from exc

            # 2c. If the status is NOT retryable, return immediately
            if response.status_code not in _RETRYABLE_STATUS_CODES:
                return response

            last_response = response

            # 2d. If we still have retries left, back off and log
            if attempt < MAX_RETRIES:
                sleep_duration: float = BASE_DELAY * (2**attempt)
                logger.warning(
                    "Retryable HTTP status received; backing off",
                    attempt=attempt + 1,
                    status_code=response.status_code,
                    sleep_duration=sleep_duration,
                    url=url,
                )
                await asyncio.sleep(sleep_duration)

        # 3. All retries exhausted — raise a DataSourceError
        status_code = last_response.status_code if last_response is not None else None
        raise DataSourceError(
            message=(
                f"StatCan request failed after {MAX_RETRIES} retries "
                f"with status {status_code}."
            ),
            error_code="DATASOURCE_RETRIES_EXHAUSTED",
            context={
                "url": url,
                "method": method,
                "status_code": status_code,
                "max_retries": MAX_RETRIES,
            },
        )
