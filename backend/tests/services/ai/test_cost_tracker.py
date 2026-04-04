"""Tests for ``cost_tracker`` — cost calculation and budget alerting.

Covers:
    * Correct cost calculation for known and unknown models.
    * Budget alert fires ``structlog.warning`` when spend exceeds limit.
    * Budget OK when spend is under limit.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.ai.cost_tracker import calculate_cost, log_and_check_budget


# ---------------------------------------------------------------------------
# calculate_cost
# ---------------------------------------------------------------------------


class TestCalculateCost:
    """Tests for ``calculate_cost``."""

    PRICING = {
        "gemini-2.0-flash": {"input": 0.10, "output": 0.40},
        "gemini-1.5-pro": {"input": 1.25, "output": 5.00},
    }

    def test_basic_cost(self) -> None:
        """100 input + 50 output tokens for gemini-2.0-flash."""
        cost = calculate_cost(
            model="gemini-2.0-flash",
            input_tokens=100,
            output_tokens=50,
            pricing=self.PRICING,
        )
        # (100 * 0.10 + 50 * 0.40) / 1_000_000 = 30.0 / 1_000_000
        expected = (100 * 0.10 + 50 * 0.40) / 1_000_000
        assert cost == round(expected, 8)

    def test_zero_tokens(self) -> None:
        """Zero tokens should produce zero cost."""
        cost = calculate_cost(
            model="gemini-2.0-flash",
            input_tokens=0,
            output_tokens=0,
            pricing=self.PRICING,
        )
        assert cost == 0.0

    def test_unknown_model(self) -> None:
        """Unknown model should return 0.0 and log a warning."""
        with patch("src.services.ai.cost_tracker.logger") as mock_logger:
            cost = calculate_cost(
                model="gpt-5-turbo",
                input_tokens=100,
                output_tokens=100,
                pricing=self.PRICING,
            )
            assert cost == 0.0
            mock_logger.warning.assert_called_once()

    def test_large_token_count(self) -> None:
        """1 million tokens should produce the listed rate."""
        cost = calculate_cost(
            model="gemini-1.5-pro",
            input_tokens=1_000_000,
            output_tokens=0,
            pricing=self.PRICING,
        )
        # 1_000_000 * 1.25 / 1_000_000 = 1.25
        assert cost == 1.25

    def test_output_only(self) -> None:
        """Cost with only output tokens."""
        cost = calculate_cost(
            model="gemini-2.0-flash",
            input_tokens=0,
            output_tokens=1_000_000,
            pricing=self.PRICING,
        )
        assert cost == 0.40


# ---------------------------------------------------------------------------
# log_and_check_budget
# ---------------------------------------------------------------------------


class TestLogAndCheckBudget:
    """Tests for ``log_and_check_budget``."""

    async def test_under_budget_no_warning(self) -> None:
        """Under budget should NOT emit a warning."""
        session = AsyncMock()
        scalar_result = MagicMock()
        scalar_result.scalar_one.return_value = 0.50
        session.execute.return_value = scalar_result

        with patch("src.services.ai.cost_tracker.logger") as mock_logger:
            total = await log_and_check_budget(
                session=session, budget_limit=5.00
            )
            assert total == 0.50
            mock_logger.warning.assert_not_called()

    async def test_over_budget_emits_warning(self) -> None:
        """Over budget should emit structlog.warning."""
        session = AsyncMock()
        scalar_result = MagicMock()
        scalar_result.scalar_one.return_value = 10.0
        session.execute.return_value = scalar_result

        with patch("src.services.ai.cost_tracker.logger") as mock_logger:
            total = await log_and_check_budget(
                session=session, budget_limit=5.00
            )
            assert total == 10.0
            mock_logger.warning.assert_called_once_with(
                "llm.budget_exceeded",
                today_spend_usd=10.0,
                daily_budget_usd=5.00,
            )

    async def test_exact_budget_no_warning(self) -> None:
        """Exactly at budget should NOT emit a warning (> not >=)."""
        session = AsyncMock()
        scalar_result = MagicMock()
        scalar_result.scalar_one.return_value = 5.00
        session.execute.return_value = scalar_result

        with patch("src.services.ai.cost_tracker.logger") as mock_logger:
            total = await log_and_check_budget(
                session=session, budget_limit=5.00
            )
            assert total == 5.00
            mock_logger.warning.assert_not_called()

    async def test_zero_spend(self) -> None:
        """Zero spend should return 0.0 and no warning."""
        session = AsyncMock()
        scalar_result = MagicMock()
        scalar_result.scalar_one.return_value = 0.0
        session.execute.return_value = scalar_result

        total = await log_and_check_budget(
            session=session, budget_limit=5.00
        )
        assert total == 0.0
