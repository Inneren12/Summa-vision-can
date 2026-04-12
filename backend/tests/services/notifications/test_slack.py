"""Tests for SlackNotifierService (D-3, PR-37/38).

Validates Slack webhook integration, dedupe, error handling,
and empty-config behaviour.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.core.config import Settings
from src.services.notifications.slack import SlackNotifierService


def _make_settings(webhook_url: str = "https://hooks.slack.com/test") -> Settings:
    """Create a Settings instance with the given webhook URL."""
    return Settings(
        SLACK_WEBHOOK_URL=webhook_url,
        database_url="sqlite+aiosqlite:///:memory:",
        admin_api_key="test-key",
    )


@pytest.fixture()
def mock_http_client() -> AsyncMock:
    client = AsyncMock(spec=httpx.AsyncClient)
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = 200
    resp.raise_for_status = MagicMock()
    client.post = AsyncMock(return_value=resp)
    return client


@pytest.fixture()
def slack_service(mock_http_client: AsyncMock) -> SlackNotifierService:
    return SlackNotifierService(
        http_client=mock_http_client,
        settings=_make_settings(),
    )


class TestSlackNotification:
    @pytest.mark.asyncio
    async def test_notify_b2b_sends_slack(
        self, slack_service: SlackNotifierService, mock_http_client: AsyncMock
    ) -> None:
        result = await slack_service.notify_lead(
            email="ceo@tdbank.ca",
            category="b2b",
            company_domain="tdbank.ca",
        )
        assert result is True
        mock_http_client.post.assert_awaited_once()

        call_kwargs = mock_http_client.post.call_args
        payload = call_kwargs.kwargs["json"]
        assert "[B2B LEAD]" in payload["text"]
        assert "ceo@tdbank.ca" in payload["text"]
        block_text = payload["blocks"][0]["text"]["text"]
        assert "tdbank.ca" in block_text
        assert "b2b" in block_text

    @pytest.mark.asyncio
    async def test_notify_education_sends_tag(
        self, slack_service: SlackNotifierService, mock_http_client: AsyncMock
    ) -> None:
        result = await slack_service.notify_lead(
            email="prof@utoronto.ca",
            category="education",
            company_domain="utoronto.ca",
        )
        assert result is True
        payload = mock_http_client.post.call_args.kwargs["json"]
        assert "[EDUCATION]" in payload["text"]

    @pytest.mark.asyncio
    async def test_slack_failure_returns_false(
        self, mock_http_client: AsyncMock
    ) -> None:
        mock_http_client.post = AsyncMock(side_effect=httpx.HTTPError("timeout"))
        service = SlackNotifierService(
            http_client=mock_http_client,
            settings=_make_settings(),
        )
        result = await service.notify_lead(
            email="ceo@tdbank.ca",
            category="b2b",
            company_domain="tdbank.ca",
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_dedupe_prevents_duplicate(
        self, slack_service: SlackNotifierService, mock_http_client: AsyncMock
    ) -> None:
        await slack_service.notify_lead(
            email="ceo@tdbank.ca",
            category="b2b",
            company_domain="tdbank.ca",
            dedupe_key="test-key-1",
        )
        await slack_service.notify_lead(
            email="ceo@tdbank.ca",
            category="b2b",
            company_domain="tdbank.ca",
            dedupe_key="test-key-1",
        )
        # Webhook should only be called once
        assert mock_http_client.post.await_count == 1

    @pytest.mark.asyncio
    async def test_empty_webhook_url_skips(self, mock_http_client: AsyncMock) -> None:
        service = SlackNotifierService(
            http_client=mock_http_client,
            settings=_make_settings(webhook_url=""),
        )
        result = await service.notify_lead(
            email="ceo@tdbank.ca",
            category="b2b",
            company_domain="tdbank.ca",
        )
        assert result is False
        mock_http_client.post.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_context_included_in_payload(
        self, slack_service: SlackNotifierService, mock_http_client: AsyncMock
    ) -> None:
        await slack_service.notify_lead(
            email="ceo@tdbank.ca",
            category="b2b",
            company_domain="tdbank.ca",
            context={"budget": "$1000/month", "name": "John"},
        )
        payload = mock_http_client.post.call_args.kwargs["json"]
        block_text = payload["blocks"][0]["text"]["text"]
        assert "Budget" in block_text
        assert "$1000/month" in block_text

    @pytest.mark.asyncio
    async def test_different_dedupe_keys_both_sent(
        self, slack_service: SlackNotifierService, mock_http_client: AsyncMock
    ) -> None:
        await slack_service.notify_lead(
            email="a@a.com", category="b2b", company_domain="a.com",
            dedupe_key="key-a",
        )
        await slack_service.notify_lead(
            email="b@b.com", category="b2b", company_domain="b.com",
            dedupe_key="key-b",
        )
        assert mock_http_client.post.await_count == 2
