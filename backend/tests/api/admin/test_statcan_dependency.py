"""Phase 3.1b fix R1: lifecycle test for the shared StatCan metadata cache
service dependency.

Without the ``async with`` + ``yield`` pattern, every request leaks a
connection pool. This test asserts that ``aclose()`` is called exactly
once after the request scope exits.
"""
from __future__ import annotations

from unittest.mock import AsyncMock

import httpx
import pytest

from src.api.dependencies.statcan import get_statcan_metadata_cache_service


@pytest.mark.asyncio
async def test_get_statcan_metadata_cache_service_closes_httpx_client_after_request(
    monkeypatch,
) -> None:
    """Reviewer R1 Blocker 1: dependency must close ``httpx.AsyncClient``
    on request teardown.

    We capture the constructed client instance via a wrapper around
    ``httpx.AsyncClient.__init__`` and assert that ``is_closed`` flips to
    ``True`` after the dependency generator returns. ``is_closed`` is the
    canonical post-close signal exposed by httpx — async-with on
    AsyncClient sets it from ``__aexit__`` regardless of the internal
    teardown path.
    """
    constructed: list[httpx.AsyncClient] = []
    real_init = httpx.AsyncClient.__init__

    def _tracking_init(self: httpx.AsyncClient, *args: object, **kwargs: object) -> None:
        real_init(self, *args, **kwargs)
        constructed.append(self)

    monkeypatch.setattr(httpx.AsyncClient, "__init__", _tracking_init)

    mock_session_factory = AsyncMock()
    gen = get_statcan_metadata_cache_service(
        session_factory=mock_session_factory
    )
    service = await gen.__anext__()
    assert service is not None, "dependency must yield a service instance"
    assert len(constructed) == 1, "dependency must construct exactly one client"
    assert constructed[0].is_closed is False, (
        "client must still be open while the request is in flight"
    )

    # Simulate end-of-request: generator returns, async-with exits,
    # httpx client is closed.
    with pytest.raises(StopAsyncIteration):
        await gen.__anext__()

    assert constructed[0].is_closed is True, (
        "httpx.AsyncClient must be closed after request teardown — "
        "without async-with-yield the connection pool leaks per request"
    )
