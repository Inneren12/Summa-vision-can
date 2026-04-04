"""In-memory per-IP rate limiter using a sliding-window counter.

Provides :class:`InMemoryRateLimiter`, a reusable limiter that tracks
request counts per client IP within a configurable time window.  Different
endpoints can instantiate the limiter with different limits:

* Public gallery: ``InMemoryRateLimiter(max_requests=30, window_seconds=60)``
* Lead capture:   ``InMemoryRateLimiter(max_requests=3, window_seconds=60)``
* Sponsorship:    ``InMemoryRateLimiter(max_requests=1, window_seconds=300)``

The implementation is fully synchronous and thread-safe for single-process
async deployments (no ``asyncio.Lock`` needed since the GIL serialises
access and no ``await`` appears between read and write).
"""

from __future__ import annotations

import time
from collections import defaultdict


class InMemoryRateLimiter:
    """Sliding-window counter rate limiter keyed by client IP.

    Parameters
    ----------
    max_requests:
        Maximum number of requests allowed within the time window.
    window_seconds:
        Duration of the sliding window in seconds.

    Example
    -------
    ::

        limiter = InMemoryRateLimiter(max_requests=30, window_seconds=60)

        if not limiter.is_allowed("192.168.1.1"):
            return JSONResponse(status_code=429, ...)
    """

    __slots__ = ("_max_requests", "_window_seconds", "_requests")

    def __init__(self, max_requests: int, window_seconds: int) -> None:
        if max_requests <= 0:
            raise ValueError("max_requests must be a positive integer")
        if window_seconds <= 0:
            raise ValueError("window_seconds must be a positive integer")

        self._max_requests: int = max_requests
        self._window_seconds: int = window_seconds
        # IP → list of request timestamps (monotonic)
        self._requests: dict[str, list[float]] = defaultdict(list)

    @property
    def max_requests(self) -> int:
        """Maximum requests allowed in the window."""
        return self._max_requests

    @property
    def window_seconds(self) -> int:
        """Window duration in seconds."""
        return self._window_seconds

    def is_allowed(self, client_ip: str) -> bool:
        """Check whether *client_ip* is within the rate limit.

        If allowed, the request is **recorded** (counted).  If denied,
        no side-effects occur — the caller should return HTTP 429.

        Args:
            client_ip: The client IP address string.

        Returns:
            ``True`` if the request is allowed, ``False`` if rate-limited.
        """
        now = time.monotonic()
        cutoff = now - self._window_seconds

        # Prune expired timestamps.
        timestamps = self._requests[client_ip]
        self._requests[client_ip] = [t for t in timestamps if t > cutoff]
        timestamps = self._requests[client_ip]

        if len(timestamps) >= self._max_requests:
            return False

        timestamps.append(now)
        return True

    def reset(self) -> None:
        """Clear all tracked state.  Useful for testing."""
        self._requests.clear()
