"""Repository for LLMRequest logging.

Every LLM API call is recorded for cost tracking, auditing, and
potential response caching.  This repository intentionally provides
only a ``log_request`` method — there is no update or delete API for
audit records.

Commit semantics:
    Repositories perform ``session.flush()`` and ``session.refresh()``
    on create operations but do **not** call ``session.commit()``.
    Commits are handled by the FastAPI ``get_db`` dependency (auto-commit
    on successful request, rollback on exception).  Callers outside of
    a request context (e.g. background tasks, scripts) must commit
    explicitly.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.llm_request import LLMRequest


class LLMRequestRepository:
    """Encapsulates persistence logic for :class:`LLMRequest`.

    Attributes:
        _session: The injected async database session.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialise with an injected ``AsyncSession``.

        Args:
            session: An active SQLAlchemy async session provided by DI.
        """
        self._session = session

    async def log_request(
        self,
        *,
        prompt_hash: str,
        response: str,
        tokens: int,
        cost: float,
    ) -> LLMRequest:
        """Log a single LLM API call.

        Args:
            prompt_hash: SHA-256 hash (or similar) of the prompt text.
            response: Raw JSON response from the LLM.
            tokens: Total token count (prompt + completion).
            cost: Estimated cost in US dollars.

        Returns:
            The newly created ``LLMRequest`` instance.
        """
        llm_request = LLMRequest(
            prompt_hash=prompt_hash,
            response_json=response,
            tokens_used=tokens,
            cost_usd=cost,
        )
        self._session.add(llm_request)
        await self._session.flush()
        await self._session.refresh(llm_request)
        return llm_request
