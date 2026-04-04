"""Tests for the resilient StatCan HTTP Client (PR-04).

Coverage goals
--------------
* Happy-path GET / POST requests.
* Maintenance-window guard raises ``DataSourceError``.
* HTTP 429, 409, and **503** trigger exponential-backoff retries.
* Structured logger is called with correct attempt numbers and sleep durations.
* ``DataSourceError`` is raised when retries are exhausted.
* Network errors (``TimeoutException``, ``RequestError``) raise ``DataSourceError``.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock

import httpx
import pytest
import respx
import structlog

from src.core.exceptions import DataSourceError
from src.core.rate_limit import AsyncTokenBucket
from src.services.statcan.client import (
    BASE_DELAY,
    MAX_RETRIES,
    StatCanClient,
)
from src.services.statcan.maintenance import StatCanMaintenanceGuard

# URL used across all tests
_TEST_URL = "https://fake.statcan.gc.ca/data"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def http_client() -> httpx.AsyncClient:
    """Return a fresh ``httpx.AsyncClient`` (transport is mocked by respx)."""
    return httpx.AsyncClient()


@pytest.fixture()
def rate_limiter() -> AsyncTokenBucket:
    """Return a generous token bucket that never blocks."""
    return AsyncTokenBucket(capacity=100, refill_rate=100.0)


@pytest.fixture()
def maintenance_guard() -> StatCanMaintenanceGuard:
    """A guard that always says 'no maintenance'."""

    class _NoMaintenanceGuard(StatCanMaintenanceGuard):
        def is_maintenance_window(self, current_time: datetime) -> bool:
            return False

    return _NoMaintenanceGuard()


@pytest.fixture()
def client(
    http_client: httpx.AsyncClient,
    maintenance_guard: StatCanMaintenanceGuard,
    rate_limiter: AsyncTokenBucket,
) -> StatCanClient:
    """Fully-wired ``StatCanClient`` with maintenance guard that never blocks."""
    return StatCanClient(http_client, maintenance_guard, rate_limiter)


@pytest.fixture()
def _no_sleep(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    """Patch ``asyncio.sleep`` to be a no-op and capture delay args."""
    recorded: list[float] = []

    async def _mock_sleep(delay: float) -> None:
        recorded.append(delay)

    monkeypatch.setattr(asyncio, "sleep", _mock_sleep)
    return recorded


# ---------------------------------------------------------------------------
# Happy-path tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_successful_get_request(client: StatCanClient) -> None:
    """A 200 response should be returned without any retry."""
    with respx.mock:
        route = respx.get(_TEST_URL).mock(
            return_value=httpx.Response(200, json={"status": "ok"}),
        )
        response = await client.get(_TEST_URL)

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert route.called


@pytest.mark.asyncio
async def test_successful_post_request(client: StatCanClient) -> None:
    """POST requests should also work through the ``request`` method."""
    with respx.mock:
        route = respx.post(_TEST_URL).mock(
            return_value=httpx.Response(201, json={"id": 1}),
        )
        response = await client.request("POST", _TEST_URL, json={"foo": "bar"})

    assert response.status_code == 201
    assert route.called


# ---------------------------------------------------------------------------
# Maintenance-window tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_maintenance_guard_raises_datasource_error(
    http_client: httpx.AsyncClient,
    rate_limiter: AsyncTokenBucket,
) -> None:
    """When the guard says 'maintenance', ``DataSourceError`` must be raised."""

    class _AlwaysMaintenanceGuard(StatCanMaintenanceGuard):
        def is_maintenance_window(self, current_time: datetime) -> bool:
            return True

    locked_client = StatCanClient(
        http_client, _AlwaysMaintenanceGuard(), rate_limiter
    )

    with pytest.raises(DataSourceError, match="maintenance window") as exc_info:
        await locked_client.get(_TEST_URL)

    assert exc_info.value.error_code == "DATASOURCE_MAINTENANCE"
    assert exc_info.value.context["url"] == _TEST_URL


# ---------------------------------------------------------------------------
# Retry tests — 429 / 409 / 503
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_http_429_retries_then_succeeds(
    client: StatCanClient,
    _no_sleep: list[float],
) -> None:
    """A single 429 followed by 200 should succeed after one retry."""
    with respx.mock:
        route = respx.get(_TEST_URL).mock(
            side_effect=[
                httpx.Response(429),
                httpx.Response(200, json={"ok": True}),
            ],
        )
        response = await client.get(_TEST_URL)

    assert response.status_code == 200
    assert route.call_count == 2
    assert _no_sleep == [BASE_DELAY * (2**0)]  # 1.0 s


@pytest.mark.asyncio
async def test_http_409_retries_then_succeeds(
    client: StatCanClient,
    _no_sleep: list[float],
) -> None:
    """409 should be retried via the same backoff logic as 429."""
    with respx.mock:
        respx.get(_TEST_URL).mock(
            side_effect=[
                httpx.Response(409),
                httpx.Response(409),
                httpx.Response(200, json={"done": True}),
            ],
        )
        response = await client.get(_TEST_URL)

    assert response.status_code == 200
    assert _no_sleep == [1.0, 2.0]


@pytest.mark.asyncio
async def test_http_503_sequence_logs_warnings_and_raises(
    client: StatCanClient,
    _no_sleep: list[float],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Four consecutive 503 responses should:

    1. Log a WARNING on each retry (3 warnings for attempts 1-3).
    2. Eventually raise ``DataSourceError`` with ``DATASOURCE_RETRIES_EXHAUSTED``.
    """
    # Capture structured log calls
    log_calls: list[dict[str, Any]] = []
    mock_warning = AsyncMock(side_effect=lambda *a: None) if False else None

    # We use a synchronous mock for structlog's warning method
    def _capture_warning(event: str, **kw: Any) -> None:
        log_calls.append({"event": event, **kw})

    # Patch the module-level logger in client.py
    import src.services.statcan.client as client_module

    fake_logger = structlog.get_logger(module="statcan.client.test")
    monkeypatch.setattr(fake_logger, "warning", _capture_warning)
    monkeypatch.setattr(client_module, "logger", fake_logger)

    with respx.mock:
        route = respx.get(_TEST_URL).mock(
            side_effect=[
                httpx.Response(503),
                httpx.Response(503),
                httpx.Response(503),
                httpx.Response(503),
            ],
        )

        with pytest.raises(DataSourceError) as exc_info:
            await client.get(_TEST_URL)

    # Verify the exception
    assert exc_info.value.error_code == "DATASOURCE_RETRIES_EXHAUSTED"
    assert "503" in exc_info.value.message
    assert exc_info.value.context["max_retries"] == MAX_RETRIES

    # Verify the route was called 4 times (initial + 3 retries)
    assert route.call_count == 4

    # Verify log calls — exactly 3 warnings
    assert len(log_calls) == 3, f"Expected 3 log warnings, got {len(log_calls)}"

    expected_delays = [
        BASE_DELAY * (2**0),  # 1.0
        BASE_DELAY * (2**1),  # 2.0
        BASE_DELAY * (2**2),  # 4.0
    ]

    for i, log_entry in enumerate(log_calls):
        assert log_entry["attempt"] == i + 1
        assert log_entry["status_code"] == 503
        assert log_entry["sleep_duration"] == expected_delays[i]

    # Verify asyncio.sleep was called with the correct durations
    assert _no_sleep == expected_delays


@pytest.mark.asyncio
async def test_http_503_retry_succeeds_on_last_attempt(
    client: StatCanClient,
    _no_sleep: list[float],
) -> None:
    """If the service recovers on the last retry, success is returned."""
    with respx.mock:
        respx.get(_TEST_URL).mock(
            side_effect=[
                httpx.Response(503),
                httpx.Response(503),
                httpx.Response(503),
                httpx.Response(200, json={"recovered": True}),
            ],
        )
        response = await client.get(_TEST_URL)

    assert response.status_code == 200
    assert _no_sleep == [1.0, 2.0, 4.0]


@pytest.mark.asyncio
async def test_http_429_max_retries_raises_datasource_error(
    client: StatCanClient,
    _no_sleep: list[float],
) -> None:
    """Exhausting retries on 429 must raise ``DataSourceError``."""
    with respx.mock:
        respx.get(_TEST_URL).mock(
            side_effect=[httpx.Response(429)] * (MAX_RETRIES + 1),
        )

        with pytest.raises(DataSourceError) as exc_info:
            await client.get(_TEST_URL)

    assert exc_info.value.error_code == "DATASOURCE_RETRIES_EXHAUSTED"
    assert len(_no_sleep) == MAX_RETRIES


@pytest.mark.asyncio
async def test_http_409_max_retries_raises_datasource_error(
    client: StatCanClient,
    _no_sleep: list[float],
) -> None:
    """Exhausting retries on 409 must raise ``DataSourceError``."""
    with respx.mock:
        respx.get(_TEST_URL).mock(
            side_effect=[httpx.Response(409)] * (MAX_RETRIES + 1),
        )

        with pytest.raises(DataSourceError) as exc_info:
            await client.get(_TEST_URL)

    assert exc_info.value.error_code == "DATASOURCE_RETRIES_EXHAUSTED"
    assert exc_info.value.context["status_code"] == 409


# ---------------------------------------------------------------------------
# Network / transport error tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_timeout_raises_datasource_error(client: StatCanClient) -> None:
    """``httpx.TimeoutException`` should be wrapped in ``DataSourceError``."""
    with respx.mock:
        respx.get(_TEST_URL).mock(side_effect=httpx.TimeoutException("timed out"))

        with pytest.raises(DataSourceError) as exc_info:
            await client.get(_TEST_URL)

    assert exc_info.value.error_code == "DATASOURCE_NETWORK_ERROR"
    assert "timed out" in exc_info.value.message


@pytest.mark.asyncio
async def test_request_error_raises_datasource_error(
    client: StatCanClient,
) -> None:
    """``httpx.RequestError`` should be wrapped in ``DataSourceError``."""
    with respx.mock:
        respx.get(_TEST_URL).mock(
            side_effect=httpx.RequestError("connection refused"),
        )

        with pytest.raises(DataSourceError) as exc_info:
            await client.get(_TEST_URL)

    assert exc_info.value.error_code == "DATASOURCE_NETWORK_ERROR"
    assert "connection refused" in exc_info.value.message


# ---------------------------------------------------------------------------
# Non-retryable status codes
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_non_retryable_status_returns_immediately(
    client: StatCanClient,
    _no_sleep: list[float],
) -> None:
    """Status codes NOT in {429, 409, 503} must be returned without retry."""
    with respx.mock:
        respx.get(_TEST_URL).mock(return_value=httpx.Response(500, text="oops"))
        response = await client.get(_TEST_URL)

    assert response.status_code == 500
    assert _no_sleep == []  # no retries


@pytest.mark.asyncio
async def test_404_returns_without_retry(
    client: StatCanClient,
    _no_sleep: list[float],
) -> None:
    """A 404 is not retryable and must be returned as-is."""
    with respx.mock:
        respx.get(_TEST_URL).mock(return_value=httpx.Response(404))
        response = await client.get(_TEST_URL)

    assert response.status_code == 404
    assert _no_sleep == []


# ---------------------------------------------------------------------------
# Backoff timing verification
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_exponential_backoff_timing(
    client: StatCanClient,
    _no_sleep: list[float],
) -> None:
    """Verify that sleep durations follow the 1·2·4 pattern."""
    with respx.mock:
        respx.get(_TEST_URL).mock(
            side_effect=[
                httpx.Response(429),
                httpx.Response(429),
                httpx.Response(429),
                httpx.Response(200),
            ],
        )
        response = await client.get(_TEST_URL)

    assert response.status_code == 200
    assert _no_sleep == [1.0, 2.0, 4.0]


# ---------------------------------------------------------------------------
# Logger integration tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_logger_called_with_correct_fields_on_retry(
    client: StatCanClient,
    _no_sleep: list[float],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Every retry must log *attempt*, *status_code*, and *sleep_duration*."""
    log_calls: list[dict[str, Any]] = []

    def _capture_warning(event: str, **kw: Any) -> None:
        log_calls.append({"event": event, **kw})

    import src.services.statcan.client as client_module

    fake_logger = structlog.get_logger(module="test.logger")
    monkeypatch.setattr(fake_logger, "warning", _capture_warning)
    monkeypatch.setattr(client_module, "logger", fake_logger)

    with respx.mock:
        respx.get(_TEST_URL).mock(
            side_effect=[
                httpx.Response(429),
                httpx.Response(200, json={"ok": True}),
            ],
        )
        await client.get(_TEST_URL)

    assert len(log_calls) == 1
    entry = log_calls[0]
    assert entry["attempt"] == 1
    assert entry["status_code"] == 429
    assert entry["sleep_duration"] == 1.0
    assert entry["url"] == _TEST_URL


@pytest.mark.asyncio
async def test_no_log_on_success_without_retry(
    client: StatCanClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No warning should be logged when the first request succeeds."""
    log_calls: list[dict[str, Any]] = []

    def _capture_warning(event: str, **kw: Any) -> None:
        log_calls.append({"event": event, **kw})

    import src.services.statcan.client as client_module

    fake_logger = structlog.get_logger(module="test.logger")
    monkeypatch.setattr(fake_logger, "warning", _capture_warning)
    monkeypatch.setattr(client_module, "logger", fake_logger)

    with respx.mock:
        respx.get(_TEST_URL).mock(return_value=httpx.Response(200))
        await client.get(_TEST_URL)

    assert log_calls == []


# ---------------------------------------------------------------------------
# Dependency-injection sanity checks
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rate_limiter_acquire_called(
    http_client: httpx.AsyncClient,
    maintenance_guard: StatCanMaintenanceGuard,
) -> None:
    """``rate_limiter.acquire()`` must be called before every HTTP call."""
    acquire_count = 0
    original_acquire = AsyncTokenBucket.acquire

    class _CountingBucket(AsyncTokenBucket):
        async def acquire(self) -> None:
            nonlocal acquire_count
            acquire_count += 1

    bucket = _CountingBucket(capacity=10, refill_rate=10.0)
    c = StatCanClient(http_client, maintenance_guard, bucket)

    with respx.mock:
        respx.get(_TEST_URL).mock(return_value=httpx.Response(200))
        await c.get(_TEST_URL)

    assert acquire_count == 1
