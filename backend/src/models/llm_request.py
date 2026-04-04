"""LLMRequest ORM model.

Logs every LLM API call for cost tracking and response caching.
The ``prompt_hash`` is a deterministic hash of the prompt text so
that identical prompts can be de-duplicated or cache-hit without
storing the (potentially large) raw prompt.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class LLMRequest(Base):
    """An auditable record of a single LLM API call.

    Attributes:
        id: Auto-incrementing primary key.
        prompt_hash: SHA-256 (or similar) hash of the prompt text.
        response_json: Raw JSON response from the LLM (stored as text).
        tokens_used: Total token count (prompt + completion).
        cost_usd: Estimated cost in US dollars for this call.
        created_at: UTC timestamp of record creation.
    """

    __tablename__ = "llm_requests"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    prompt_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    response_json: Mapped[str] = mapped_column(Text, nullable=False)
    tokens_used: Mapped[int] = mapped_column(Integer, nullable=False)
    cost_usd: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<LLMRequest(id={self.id}, prompt_hash={self.prompt_hash!r}, "
            f"tokens={self.tokens_used})>"
        )
