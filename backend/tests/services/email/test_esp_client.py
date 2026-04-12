"""Tests for BeehiivClient ESP client (D-3, PR-34/49).

Validates subscriber creation, tag adding, and error classification
(permanent vs transient).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from src.core.exceptions import ESPPermanentError, ESPTransientError
from src.services.email.esp_client import BeehiivClient


@pytest.fixture()
def mock_http_client() -> AsyncMock:
    return AsyncMock(spec=httpx.AsyncClient)


@pytest.fixture()
def esp_client(mock_http_client: AsyncMock) -> BeehiivClient:
    return BeehiivClient(
        http_client=mock_http_client,
        api_key="test-api-key",
        publication_id="pub-123",
    )


def _make_response(status_code: int, text: str = "ok") -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.text = text
    return resp


class TestBeehiivClient:
    @pytest.mark.asyncio
    async def test_add_subscriber_success(
        self, esp_client: BeehiivClient, mock_http_client: AsyncMock
    ) -> None:
        mock_http_client.request = AsyncMock(return_value=_make_response(200))
        await esp_client.add_subscriber("user@example.com")
        mock_http_client.request.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_add_subscriber_4xx_raises_permanent(
        self, esp_client: BeehiivClient, mock_http_client: AsyncMock
    ) -> None:
        mock_http_client.request = AsyncMock(
            return_value=_make_response(400, "Bad Request")
        )
        with pytest.raises(ESPPermanentError) as exc_info:
            await esp_client.add_subscriber("bad@example.com")
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_add_subscriber_5xx_raises_transient(
        self, esp_client: BeehiivClient, mock_http_client: AsyncMock
    ) -> None:
        mock_http_client.request = AsyncMock(
            return_value=_make_response(500, "Internal Server Error")
        )
        with pytest.raises(ESPTransientError) as exc_info:
            await esp_client.add_subscriber("user@example.com")
        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_add_subscriber_timeout_raises_transient(
        self, esp_client: BeehiivClient, mock_http_client: AsyncMock
    ) -> None:
        mock_http_client.request = AsyncMock(
            side_effect=httpx.TimeoutException("timed out")
        )
        with pytest.raises(ESPTransientError) as exc_info:
            await esp_client.add_subscriber("user@example.com")
        assert exc_info.value.status_code == 0

    @pytest.mark.asyncio
    async def test_add_tag_success(
        self, esp_client: BeehiivClient, mock_http_client: AsyncMock
    ) -> None:
        mock_http_client.request = AsyncMock(return_value=_make_response(200))
        await esp_client.add_tag("user@example.com", "b2b")
        mock_http_client.request.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_add_tag_4xx_raises_permanent(
        self, esp_client: BeehiivClient, mock_http_client: AsyncMock
    ) -> None:
        mock_http_client.request = AsyncMock(
            return_value=_make_response(422, "Unprocessable")
        )
        with pytest.raises(ESPPermanentError):
            await esp_client.add_tag("user@example.com", "bad_tag")

    @pytest.mark.asyncio
    async def test_add_subscriber_with_metadata(
        self, esp_client: BeehiivClient, mock_http_client: AsyncMock
    ) -> None:
        mock_http_client.request = AsyncMock(return_value=_make_response(200))
        await esp_client.add_subscriber(
            "user@example.com",
            metadata={"category": "b2b", "company_domain": "example.com"},
        )
        call_kwargs = mock_http_client.request.call_args
        payload = call_kwargs.kwargs["json"]
        assert "custom_fields" in payload
        assert len(payload["custom_fields"]) == 2

    @pytest.mark.asyncio
    async def test_connect_error_raises_transient(
        self, esp_client: BeehiivClient, mock_http_client: AsyncMock
    ) -> None:
        mock_http_client.request = AsyncMock(
            side_effect=httpx.ConnectError("connection refused")
        )
        with pytest.raises(ESPTransientError):
            await esp_client.add_subscriber("user@example.com")
