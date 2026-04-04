"""LLM cost calculation and daily budget alerting.

Provides two functions consumed by ``GeminiClient``:

* ``calculate_cost`` — pure function mapping (model, tokens) → USD cost.
* ``log_and_check_budget`` — sums today's spend from the DB and emits a
  ``structlog.warning`` if the daily budget is exceeded.

Architecture notes:
    * ``calculate_cost`` is a pure function — no I/O, no side effects.
    * ``log_and_check_budget`` is an async function that executes a
      lightweight SQL aggregate.
"""

from __future__ import annotations

from datetime import datetime, timezone

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.llm_request import LLMRequest

logger = structlog.get_logger(module="cost_tracker")


# ---------------------------------------------------------------------------
# Pure cost calculation
# ---------------------------------------------------------------------------


def calculate_cost(
    *,
    model: str,
    input_tokens: int,
    output_tokens: int,
    pricing: dict[str, dict[str, float]],
) -> float:
    """Calculate the USD cost for a single LLM call.

    The *pricing* dict maps model names to per-**million**-token rates::

        {"gemini-2.0-flash": {"input": 0.10, "output": 0.40}}

    Args:
        model: Name of the model used.
        input_tokens: Number of prompt/input tokens.
        output_tokens: Number of completion/output tokens.
        pricing: Pricing dictionary (per million tokens).

    Returns:
        Cost in US dollars, rounded to 8 decimal places.
    """
    model_pricing = pricing.get(model)
    if model_pricing is None:
        logger.warning(
            "cost.unknown_model",
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
        return 0.0

    input_rate = model_pricing.get("input", 0.0)
    output_rate = model_pricing.get("output", 0.0)

    cost = (input_tokens * input_rate + output_tokens * output_rate) / 1_000_000
    return round(cost, 8)


# ---------------------------------------------------------------------------
# Budget check
# ---------------------------------------------------------------------------


async def log_and_check_budget(
    *,
    session: AsyncSession,
    budget_limit: float,
) -> float:
    """Sum today's LLM spend and warn if it exceeds *budget_limit*.

    Args:
        session: Active ``AsyncSession`` for querying ``llm_requests``.
        budget_limit: Maximum daily spend in USD.

    Returns:
        Today's cumulative cost.
    """
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    stmt = select(func.coalesce(func.sum(LLMRequest.cost_usd), 0.0)).where(
        LLMRequest.created_at >= today_start
    )
    result = await session.execute(stmt)
    today_total: float = float(result.scalar_one())

    if today_total > budget_limit:
        logger.warning(
            "llm.budget_exceeded",
            today_spend_usd=round(today_total, 4),
            daily_budget_usd=budget_limit,
        )

    return today_total
