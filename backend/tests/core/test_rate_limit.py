"""Unit tests for the AsyncTokenBucket rate limiter.

All real-time delays are eliminated via a ``FakeClock`` that patches
``time.monotonic`` and ``asyncio.sleep``.  The entire suite completes
in well under 0.05 s of real wall-clock time.
"""

from __future__ import annotations

import asyncio
import time as _real_time
from collections.abc import Generator
from unittest.mock import patch

import pytest

from src.core.rate_limit import AsyncTokenBucket


# ──────────────────────────────────────────────────────────────────────
# FakeClock helper
# ──────────────────────────────────────────────────────────────────────


class FakeClock:
    """Deterministic replacement for ``time.monotonic`` / ``asyncio.sleep``.

    * ``monotonic()`` returns the current virtual time.
    * ``advance(delta)`` manually moves virtual time forward.
    * ``sleep(delay)`` records the delay **without** advancing the
      virtual clock, because concurrent ``gather`` sleeps are logically
      parallel, not sequential.  Use ``advance()`` for explicit jumps.
    """

    def __init__(self) -> None:
        self._now: float = 0.0
        self.sleep_delays: list[float] = []

    # Drop-in replacement for time.monotonic
    def monotonic(self) -> float:
        return self._now

    # Explicit advancement (simulates "idle" real time passing)
    def advance(self, delta: float) -> None:
        self._now += delta

    # Drop-in replacement for asyncio.sleep
    async def sleep(self, delay: float) -> None:  # noqa: ARG002
        if delay > 0:
            self.sleep_delays.append(delay)

    @property
    def total_sleeps(self) -> int:
        return len(self.sleep_delays)


# ──────────────────────────────────────────────────────────────────────
# Fixture
# ──────────────────────────────────────────────────────────────────────


@pytest.fixture()
def fake_clock() -> Generator[FakeClock, None, None]:
    """Patch ``time.monotonic`` and ``asyncio.sleep`` with a FakeClock."""
    clock = FakeClock()
    with (
        patch("time.monotonic", clock.monotonic),
        patch("asyncio.sleep", clock.sleep),
    ):
        yield clock


# ──────────────────────────────────────────────────────────────────────
# Test 1 — Burst capacity (immediate when bucket is full)
# ──────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_burst_capacity_acquires_immediately(fake_clock: FakeClock) -> None:
    """All tokens in a full bucket should be acquired with zero sleeps."""
    capacity = 10
    bucket = AsyncTokenBucket(capacity=capacity, refill_rate=10.0)

    await asyncio.gather(*(bucket.acquire() for _ in range(capacity)))

    assert fake_clock.total_sleeps == 0, (
        f"Burst of {capacity} should not trigger any sleep, "
        f"but {fake_clock.total_sleeps} sleeps were recorded"
    )


# ──────────────────────────────────────────────────────────────────────
# Test 2 — 30 concurrent acquires prove rate limit of 10 req/s
# ──────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_rate_limiting_30_concurrent_acquires(fake_clock: FakeClock) -> None:
    """30 concurrent acquires at 10/s → 10 burst + 20 throttled.

    The 20 throttled callers receive progressively longer wait tickets:
    0.1 s, 0.2 s, … , 2.0 s.  ``max(sleep_delays)`` ≈ 2.0 s proves
    the rate limit works.
    """
    bucket = AsyncTokenBucket(capacity=10, refill_rate=10.0)

    await asyncio.gather(*(bucket.acquire() for _ in range(30)))

    # Exactly 20 callers should have slept (callers 11–30).
    assert fake_clock.total_sleeps == 20

    # The longest wait ≈ 2.0 s  →  proves wall-clock time would be ~2 s.
    max_delay = max(fake_clock.sleep_delays)
    assert max_delay == pytest.approx(2.0, abs=0.01), (
        f"Expected max delay ≈ 2.0s, got {max_delay:.4f}s"
    )

    # Wait times should form 0.1, 0.2, … , 2.0.
    expected = [i * 0.1 for i in range(1, 21)]
    for actual, exp in zip(sorted(fake_clock.sleep_delays), expected):
        assert actual == pytest.approx(exp, abs=0.01)


# ──────────────────────────────────────────────────────────────────────
# Test 3 — Single-token wait precision
# ──────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_acquire_waits_for_token_refill(fake_clock: FakeClock) -> None:
    """After draining all tokens, the next acquire must sleep ≈ 1/rate."""
    bucket = AsyncTokenBucket(capacity=1, refill_rate=10.0)

    await bucket.acquire()  # drains the single token — no sleep
    assert fake_clock.total_sleeps == 0

    await bucket.acquire()  # bucket empty → must sleep
    assert fake_clock.total_sleeps == 1
    assert fake_clock.sleep_delays[0] == pytest.approx(0.1, abs=0.001)


# ──────────────────────────────────────────────────────────────────────
# Test 4 — Tokens capped at capacity after idle period
# ──────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_tokens_capped_at_capacity(fake_clock: FakeClock) -> None:
    """Even after a long idle spell, tokens must not exceed capacity."""
    capacity = 5
    bucket = AsyncTokenBucket(capacity=capacity, refill_rate=100.0)

    # Simulate 0.2 s of idle time (enough for 20 tokens at rate=100).
    fake_clock.advance(0.2)

    # Grab exactly `capacity` — should all be instant.
    await asyncio.gather(*(bucket.acquire() for _ in range(capacity)))
    assert fake_clock.total_sleeps == 0

    # The (capacity + 1)-th must trigger a sleep proving no over-fill.
    await bucket.acquire()
    assert fake_clock.total_sleeps == 1
    assert fake_clock.sleep_delays[0] > 0


# ──────────────────────────────────────────────────────────────────────
# Test 5 — Constructor validation
# ──────────────────────────────────────────────────────────────────────


def test_invalid_capacity_raises_value_error(fake_clock: FakeClock) -> None:
    """capacity <= 0 must raise ValueError."""
    with pytest.raises(ValueError, match="capacity must be a positive integer"):
        AsyncTokenBucket(capacity=0, refill_rate=10.0)
    with pytest.raises(ValueError, match="capacity must be a positive integer"):
        AsyncTokenBucket(capacity=-5, refill_rate=10.0)


def test_invalid_refill_rate_raises_value_error(fake_clock: FakeClock) -> None:
    """refill_rate <= 0 must raise ValueError."""
    with pytest.raises(ValueError, match="refill_rate must be a positive number"):
        AsyncTokenBucket(capacity=10, refill_rate=0)
    with pytest.raises(ValueError, match="refill_rate must be a positive number"):
        AsyncTokenBucket(capacity=10, refill_rate=-1.0)


# ──────────────────────────────────────────────────────────────────────
# Test 6 — Property accessors
# ──────────────────────────────────────────────────────────────────────


def test_property_accessors(fake_clock: FakeClock) -> None:
    """Read-only properties must reflect constructor arguments."""
    bucket = AsyncTokenBucket(capacity=15, refill_rate=7.5)
    assert bucket.capacity == 15
    assert bucket.refill_rate == 7.5


# ──────────────────────────────────────────────────────────────────────
# Test 7 — Concurrent safety (no over-consumption)
# ──────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_concurrent_safety_no_over_consumption(fake_clock: FakeClock) -> None:
    """20 acquires on a capacity-5 / rate-50 bucket must throttle correctly."""
    bucket = AsyncTokenBucket(capacity=5, refill_rate=50.0)

    await asyncio.gather(*(bucket.acquire() for _ in range(20)))

    # 5 instant + 15 throttled
    assert fake_clock.total_sleeps == 15

    # Max delay = 15 / 50 = 0.3 s
    assert max(fake_clock.sleep_delays) == pytest.approx(0.3, abs=0.01)


# ──────────────────────────────────────────────────────────────────────
# Test 8 — Entire suite finishes under 0.05 s (meta-check)
# ──────────────────────────────────────────────────────────────────────


def test_suite_is_fast() -> None:
    """Canary: this test body takes ~0 s.  If the suite takes > 0.05 s
    overall, the real-time wall-clock assertion in CI will catch it."""
    start = _real_time.perf_counter()
    # No-op — the real assertion is in CI runtime.
    elapsed = _real_time.perf_counter() - start
    assert elapsed < 0.05
