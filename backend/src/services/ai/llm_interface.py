"""Abstract LLM interface and Gemini implementation.

Defines ``LLMInterface`` — the provider-agnostic contract every LLM
client must satisfy — and ``GeminiClient``, the concrete implementation
backed by the ``google-genai`` SDK.

Architecture notes:
    * ``GeminiClient`` receives **all** heavy dependencies via its
      constructor (ARCH-DPEN-001).  It never instantiates its own
      ``AsyncSession``, ``LLMRequestRepository``, or cache.
    * API credentials are loaded from ``Settings.gemini_api_key``;
      they are **never** hardcoded.
    * Only ``google.api_core.exceptions.GoogleAPIError`` is caught
      explicitly — bare ``except:`` is forbidden.
"""

from __future__ import annotations

import hashlib
import json
from abc import ABC, abstractmethod
from typing import TypeVar

import structlog
from google import genai
from google.genai import errors as genai_errors
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import Settings
from src.core.exceptions import AIServiceError
from src.repositories.llm_request_repository import LLMRequestRepository
from src.services.ai.cost_tracker import calculate_cost, log_and_check_budget
from src.services.ai.llm_cache import LLMCache

logger = structlog.get_logger(module="llm_interface")

T = TypeVar("T", bound=BaseModel)

# ---------------------------------------------------------------------------
# Configurable pricing — per-million-token pricing (USD)
# ---------------------------------------------------------------------------

DEFAULT_PRICING: dict[str, dict[str, float]] = {
    "gemini-2.0-flash": {"input": 0.10, "output": 0.40},
    "gemini-2.5-flash-preview-05-20": {"input": 0.15, "output": 0.60},
    "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
    "gemini-1.5-pro": {"input": 1.25, "output": 5.00},
}


# ---------------------------------------------------------------------------
# Abstract base class
# ---------------------------------------------------------------------------


class LLMInterface(ABC):
    """Provider-agnostic contract for LLM text generation."""

    @abstractmethod
    async def generate_text(
        self, prompt: str, *, data_hash: str = ""
    ) -> str:
        """Generate free-form text from a prompt.

        Args:
            prompt: The user/system prompt to send.
            data_hash: Optional hash of the underlying data to
                       incorporate into the cache key.

        Returns:
            The generated text string.
        """

    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        schema: type[BaseModel],
        *,
        data_hash: str = "",
    ) -> BaseModel:
        """Generate a structured response validated against *schema*.

        Args:
            prompt: The user/system prompt to send.
            schema: Pydantic model class used for validation.
            data_hash: Optional hash of the underlying data.

        Returns:
            A validated Pydantic model instance.
        """


# ---------------------------------------------------------------------------
# Gemini implementation
# ---------------------------------------------------------------------------


class GeminiClient(LLMInterface):
    """Concrete LLM client backed by Google Gemini (``google-genai``).

    All heavy dependencies arrive via constructor injection:

    * ``settings`` — configuration (API key, model name, budget).
    * ``session``  — ``AsyncSession`` for database persistence.
    * ``repository`` — ``LLMRequestRepository`` for cost logging.
    * ``cache`` — ``LLMCache`` for prompt-level response caching.
    * ``pricing`` — per-model token-cost dictionary (optional override).
    """

    def __init__(
        self,
        *,
        settings: Settings,
        session: AsyncSession,
        repository: LLMRequestRepository,
        cache: LLMCache,
        pricing: dict[str, dict[str, float]] | None = None,
    ) -> None:
        if not settings.gemini_api_key:
            raise AIServiceError(
                message="GEMINI_API_KEY is not configured",
                error_code="AI_CONFIG_ERROR",
            )
        self._settings = settings
        self._session = session
        self._repository = repository
        self._cache = cache
        self._pricing = pricing or DEFAULT_PRICING
        self._model_name = settings.gemini_model

        self._client = genai.Client(api_key=settings.gemini_api_key)

    # -- public API --------------------------------------------------------

    async def generate_text(
        self, prompt: str, *, data_hash: str = ""
    ) -> str:
        """Generate text via Gemini, with caching and cost tracking."""
        cache_key = self._cache.build_key(prompt, data_hash)
        cached = self._cache.get(cache_key)
        if cached is not None:
            logger.info("llm.cache_hit", cache_key=cache_key)
            return cached

        response_text, input_tokens, output_tokens = await self._call_api(
            prompt
        )

        await self._track(
            prompt=prompt,
            response_text=response_text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

        self._cache.set(cache_key, response_text)
        return response_text

    async def generate_structured(
        self,
        prompt: str,
        schema: type[BaseModel],
        *,
        data_hash: str = "",
    ) -> BaseModel:
        """Generate structured JSON validated against a Pydantic model."""
        cache_key = self._cache.build_key(prompt, data_hash)
        cached = self._cache.get(cache_key)
        if cached is not None:
            logger.info("llm.cache_hit", cache_key=cache_key)
            return schema.model_validate_json(cached)

        response_text, input_tokens, output_tokens = (
            await self._call_api(prompt)
        )

        # Validate before caching — a malformed response should not
        # pollute the cache.
        result = schema.model_validate_json(response_text)

        await self._track(
            prompt=prompt,
            response_text=response_text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

        self._cache.set(cache_key, response_text)
        return result

    # -- private helpers ---------------------------------------------------

    async def _call_api(
        self, prompt: str
    ) -> tuple[str, int, int]:
        """Send *prompt* to Gemini and return ``(text, in_tokens, out_tokens)``.

        Raises:
            AIServiceError: on any ``GoogleAPIError`` from the SDK.
        """
        try:
            response = self._client.models.generate_content(
                model=self._model_name,
                contents=prompt,
            )
        except genai_errors.APIError as exc:
            raise AIServiceError(
                message=f"Gemini API call failed: {exc}",
                error_code="AI_API_ERROR",
                context={"model": self._model_name},
            ) from exc

        text: str = response.text or ""

        usage = response.usage_metadata
        input_tokens = usage.prompt_token_count if usage else 0
        output_tokens = usage.candidates_token_count if usage else 0
        return text, input_tokens, output_tokens

    async def _track(
        self,
        *,
        prompt: str,
        response_text: str,
        input_tokens: int,
        output_tokens: int,
    ) -> None:
        """Persist the request log and check budget."""
        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()
        cost = calculate_cost(
            model=self._model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            pricing=self._pricing,
        )
        total_tokens = input_tokens + output_tokens

        response_json = json.dumps(
            {
                "text": response_text,
                "model": self._model_name,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
            }
        )

        await self._repository.log_request(
            prompt_hash=prompt_hash,
            response=response_json,
            tokens=total_tokens,
            cost=cost,
        )

        await log_and_check_budget(
            session=self._session,
            budget_limit=self._settings.daily_llm_budget,
        )
