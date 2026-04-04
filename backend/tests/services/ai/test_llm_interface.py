"""Tests for ``LLMInterface`` and ``GeminiClient``.

All external network calls are mocked — no real Gemini API calls.
Tests verify:
    * Cache hit / miss behaviour with same and different ``data_hash``.
    * Cost tracking persistence via ``LLMRequestRepository.log_request()``.
    * Budget alerting on exceeded daily spend.
    * ``AIServiceError`` raised on missing API key and API failures.
    * ``generate_structured`` validation against a Pydantic schema.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import BaseModel

from src.core.config import Settings
from src.core.exceptions import AIServiceError
from src.services.ai.llm_cache import LLMCache
from src.services.ai.llm_interface import GeminiClient


# ---------------------------------------------------------------------------
# Test helpers & fixtures
# ---------------------------------------------------------------------------


class _SummarySchema(BaseModel):
    """Tiny schema used to test ``generate_structured``."""

    title: str
    score: float


def _make_settings(**overrides: object) -> Settings:
    """Create a ``Settings`` instance with test defaults."""
    defaults: dict[str, object] = {
        "gemini_api_key": "test-api-key",
        "gemini_model": "gemini-2.0-flash",
        "daily_llm_budget": 1.00,
        "llm_cache_ttl_seconds": 86_400,
    }
    defaults.update(overrides)
    return Settings(**defaults)  # type: ignore[arg-type]


def _mock_genai_response(
    text: str = "Hello from Gemini",
    prompt_tokens: int = 10,
    completion_tokens: int = 20,
) -> MagicMock:
    """Build a mock Gemini ``GenerateContentResponse``."""
    usage = SimpleNamespace(
        prompt_token_count=prompt_tokens,
        candidates_token_count=completion_tokens,
    )
    response = MagicMock()
    response.text = text
    response.usage_metadata = usage
    return response


@pytest.fixture()
def settings() -> Settings:
    return _make_settings()


@pytest.fixture()
def cache() -> LLMCache:
    return LLMCache(ttl_seconds=300, max_size=128)


@pytest.fixture()
def mock_session() -> AsyncMock:
    session = AsyncMock()
    # For budget check query — return 0 spend by default
    scalar_result = MagicMock()
    scalar_result.scalar_one.return_value = 0.0
    session.execute.return_value = scalar_result
    return session


@pytest.fixture()
def mock_repo() -> AsyncMock:
    repo = AsyncMock()
    repo.log_request = AsyncMock()
    return repo


@pytest.fixture()
def client(
    settings: Settings,
    mock_session: AsyncMock,
    mock_repo: AsyncMock,
    cache: LLMCache,
) -> GeminiClient:
    """Build a ``GeminiClient`` with all deps mocked."""
    with patch("src.services.ai.llm_interface.genai") as mock_genai:
        mock_genai.Client.return_value = MagicMock()
        c = GeminiClient(
            settings=settings,
            session=mock_session,
            repository=mock_repo,
            cache=cache,
        )
    return c


# ---------------------------------------------------------------------------
# Tests: configuration
# ---------------------------------------------------------------------------


class TestGeminiClientConfig:
    """Configuration validation tests."""

    async def test_missing_api_key_raises(
        self, mock_session: AsyncMock, mock_repo: AsyncMock, cache: LLMCache
    ) -> None:
        """GEMINI_API_KEY must be set."""
        bad_settings = _make_settings(gemini_api_key="")
        with pytest.raises(AIServiceError, match="GEMINI_API_KEY"):
            GeminiClient(
                settings=bad_settings,
                session=mock_session,
                repository=mock_repo,
                cache=cache,
            )


# ---------------------------------------------------------------------------
# Tests: generate_text
# ---------------------------------------------------------------------------


class TestGenerateText:
    """Tests for ``generate_text``."""

    async def test_calls_api_and_logs(
        self,
        client: GeminiClient,
        mock_repo: AsyncMock,
    ) -> None:
        """First call should hit the API and persist a log entry."""
        client._client.models.generate_content = MagicMock(
            return_value=_mock_genai_response("result-A")
        )
        text = await client.generate_text("Tell me about housing")

        assert text == "result-A"
        mock_repo.log_request.assert_awaited_once()
        call_kwargs = mock_repo.log_request.call_args.kwargs
        assert call_kwargs["tokens"] == 30  # 10 + 20
        assert call_kwargs["cost"] > 0

    async def test_cache_hit_same_data_hash(
        self,
        client: GeminiClient,
        mock_repo: AsyncMock,
    ) -> None:
        """Identical prompt + same data_hash → API called once (cache hit)."""
        client._client.models.generate_content = MagicMock(
            return_value=_mock_genai_response("cached-text")
        )

        r1 = await client.generate_text("prompt-A", data_hash="hash-1")
        r2 = await client.generate_text("prompt-A", data_hash="hash-1")

        assert r1 == r2 == "cached-text"
        # API should only have been called once
        assert client._client.models.generate_content.call_count == 1
        # Repository should only have been called once
        assert mock_repo.log_request.await_count == 1

    async def test_cache_miss_different_data_hash(
        self,
        client: GeminiClient,
        mock_repo: AsyncMock,
    ) -> None:
        """Identical prompt + different data_hash → API called twice."""
        client._client.models.generate_content = MagicMock(
            return_value=_mock_genai_response("fresh")
        )

        await client.generate_text("prompt-A", data_hash="hash-1")
        await client.generate_text("prompt-A", data_hash="hash-2")

        assert client._client.models.generate_content.call_count == 2
        assert mock_repo.log_request.await_count == 2

    async def test_api_error_raises_ai_service_error(
        self,
        client: GeminiClient,
    ) -> None:
        """APIError should be wrapped in AIServiceError."""
        from google.genai import errors as genai_errors

        client._client.models.generate_content = MagicMock(
            side_effect=genai_errors.APIError(
                code=429, response_json={"error": "quota exceeded"}
            )
        )

        with pytest.raises(AIServiceError, match="Gemini API call failed"):
            await client.generate_text("boom")


# ---------------------------------------------------------------------------
# Tests: generate_structured
# ---------------------------------------------------------------------------


class TestGenerateStructured:
    """Tests for ``generate_structured``."""

    async def test_returns_validated_model(
        self,
        client: GeminiClient,
        mock_repo: AsyncMock,
    ) -> None:
        """Valid JSON should deserialise into the target schema."""
        payload = json.dumps({"title": "Housing Report", "score": 8.5})
        client._client.models.generate_content = MagicMock(
            return_value=_mock_genai_response(payload)
        )

        result = await client.generate_structured(
            "Summarise", _SummarySchema
        )

        assert isinstance(result, _SummarySchema)
        assert result.title == "Housing Report"
        assert result.score == 8.5
        mock_repo.log_request.assert_awaited_once()

    async def test_structured_cache_hit(
        self,
        client: GeminiClient,
    ) -> None:
        """Cache hit should return deserialised model, not call API again."""
        payload = json.dumps({"title": "Cached", "score": 9.0})
        client._client.models.generate_content = MagicMock(
            return_value=_mock_genai_response(payload)
        )

        r1 = await client.generate_structured(
            "Summarise", _SummarySchema, data_hash="d1"
        )
        r2 = await client.generate_structured(
            "Summarise", _SummarySchema, data_hash="d1"
        )

        assert r1.title == r2.title == "Cached"
        assert client._client.models.generate_content.call_count == 1

    async def test_invalid_json_raises(
        self,
        client: GeminiClient,
    ) -> None:
        """Non-JSON response should raise a validation error."""
        client._client.models.generate_content = MagicMock(
            return_value=_mock_genai_response("not a json string")
        )
        with pytest.raises(Exception):
            await client.generate_structured("Summarise", _SummarySchema)


# ---------------------------------------------------------------------------
# Tests: budget alerting
# ---------------------------------------------------------------------------


class TestBudgetAlert:
    """Tests for daily budget exceeded warning."""

    async def test_budget_exceeded_logs_warning(
        self,
        settings: Settings,
        mock_repo: AsyncMock,
        cache: LLMCache,
    ) -> None:
        """When daily spend exceeds budget, structlog warning should fire."""
        mock_session = AsyncMock()

        # Return high spend from the budget query
        scalar_result = MagicMock()
        scalar_result.scalar_one.return_value = 99.0
        mock_session.execute.return_value = scalar_result

        with patch("src.services.ai.llm_interface.genai") as mock_genai:
            mock_genai.Client.return_value = MagicMock()
            c = GeminiClient(
                settings=settings,
                session=mock_session,
                repository=mock_repo,
                cache=cache,
            )

        c._client.models.generate_content = MagicMock(
            return_value=_mock_genai_response("answer")
        )

        with patch(
            "src.services.ai.cost_tracker.logger"
        ) as mock_logger:
            await c.generate_text("expensive prompt")
            mock_logger.warning.assert_called_once_with(
                "llm.budget_exceeded",
                today_spend_usd=99.0,
                daily_budget_usd=1.00,
            )


# ---------------------------------------------------------------------------
# Tests: usage metadata edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Edge-case coverage."""

    async def test_no_usage_metadata(
        self,
        client: GeminiClient,
        mock_repo: AsyncMock,
    ) -> None:
        """Response with no usage_metadata should default tokens to 0."""
        response = MagicMock()
        response.text = "ok"
        response.usage_metadata = None
        client._client.models.generate_content = MagicMock(
            return_value=response
        )

        text = await client.generate_text("hello")
        assert text == "ok"
        call_kwargs = mock_repo.log_request.call_args.kwargs
        assert call_kwargs["tokens"] == 0
        assert call_kwargs["cost"] == 0.0

    async def test_empty_text_from_api(
        self,
        client: GeminiClient,
    ) -> None:
        """Response with ``text=None`` should return empty string."""
        response = MagicMock()
        response.text = None
        response.usage_metadata = SimpleNamespace(
            prompt_token_count=5, candidates_token_count=0
        )
        client._client.models.generate_content = MagicMock(
            return_value=response
        )

        text = await client.generate_text("nothing")
        assert text == ""
