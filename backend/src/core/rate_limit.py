"""Async-safe Token Bucket rate limiter.

This module provides an ``AsyncTokenBucket`` that caps outbound request
throughput using the classic *token-bucket* algorithm with a **ticket
reservation** system that eliminates thundering-herd wake-ups.

Usage::

    bucket = AsyncTokenBucket(capacity=10, refill_rate=10.0)

    async def make_request() -> None:
        await bucket.acquire()   # blocks until a token is available
        ...                      # proceed with the request

Concurrency safety is guaranteed by an internal ``asyncio.Lock``.
"""

from __future__ import annotations

import asyncio
import time


class AsyncTokenBucket:
    """A token-bucket rate limiter for ``asyncio`` coroutines.

    Parameters
    ----------
    capacity:
        Maximum number of tokens the bucket can hold.  This also defines
        the burst size.
    refill_rate:
        Number of tokens added to the bucket **per second**.
    """

    __slots__ = ("_capacity", "_refill_rate", "_tokens", "_last_refill", "_lock")

    def __init__(self, capacity: int, refill_rate: float) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be a positive integer")
        if refill_rate <= 0:
            raise ValueError("refill_rate must be a positive number")

        self._capacity: int = capacity
        self._refill_rate: float = float(refill_rate)
        self._tokens: float = float(capacity)  # start full
        self._last_refill: float = time.monotonic()
        self._lock: asyncio.Lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Properties (read-only)
    # ------------------------------------------------------------------

    @property
    def capacity(self) -> int:
        """Maximum number of tokens the bucket can hold."""
        return self._capacity

    @property
    def refill_rate(self) -> float:
        """Tokens added per second."""
        return self._refill_rate

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _refill(self) -> None:
        """Add tokens accrued since the last refill.

        Must be called while holding ``self._lock``.
        """
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(
            self._capacity,
            self._tokens + elapsed * self._refill_rate,
        )
        self._last_refill = now

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def acquire(self) -> None:
        """Consume one token, waiting if necessary.

        Uses a **ticket reservation** strategy: each caller reserves its
        slot under the lock, computes a personal wait time, then sleeps
        *exactly once* outside the lock.  Tokens are allowed to go
        negative, which schedules subsequent callers at progressively
        later wake-up times — no thundering-herd retries.
        """
        async with self._lock:
            self._refill()
            self._tokens -= 1.0

            if self._tokens >= 0.0:
                return

            # Tokens are negative → compute the exact wait for this caller.
            wait_time: float = -self._tokens / self._refill_rate

        # Sleep outside the lock — each caller sleeps exactly once.
        await asyncio.sleep(wait_time)
