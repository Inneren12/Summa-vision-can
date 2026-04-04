"""Tests for LLMRequestRepository.

Covers log_request functionality and verifies that all fields
are persisted correctly.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.llm_request import LLMRequest
from src.repositories.llm_request_repository import LLMRequestRepository


@pytest.mark.asyncio
class TestLLMRequestRepository:
    """Test suite for :class:`LLMRequestRepository`."""

    async def test_log_request(self, db_session: AsyncSession) -> None:
        """log_request should persist all fields and assign an id."""
        repo = LLMRequestRepository(db_session)

        record = await repo.log_request(
            prompt_hash="abc123def456",
            response='{"text": "Generated response"}',
            tokens=150,
            cost=0.003,
        )

        assert record.id is not None
        assert record.prompt_hash == "abc123def456"
        assert record.response_json == '{"text": "Generated response"}'
        assert record.tokens_used == 150
        assert record.cost_usd == pytest.approx(0.003)
        assert record.created_at is not None

    async def test_log_request_persists_to_db(
        self, db_session: AsyncSession
    ) -> None:
        """The record should be queryable from the database after commit."""
        repo = LLMRequestRepository(db_session)

        await repo.log_request(
            prompt_hash="hash_001",
            response='{"result": "ok"}',
            tokens=200,
            cost=0.004,
        )
        await db_session.commit()

        stmt = select(LLMRequest).where(
            LLMRequest.prompt_hash == "hash_001"
        )
        result = await db_session.execute(stmt)
        found = result.scalar_one()

        assert found.tokens_used == 200
        assert found.cost_usd == pytest.approx(0.004)

    async def test_log_multiple_requests(
        self, db_session: AsyncSession
    ) -> None:
        """Multiple calls to log_request should create separate records."""
        repo = LLMRequestRepository(db_session)

        r1 = await repo.log_request(
            prompt_hash="multi_1",
            response='{"a": 1}',
            tokens=100,
            cost=0.002,
        )
        r2 = await repo.log_request(
            prompt_hash="multi_2",
            response='{"b": 2}',
            tokens=200,
            cost=0.004,
        )
        await db_session.commit()

        assert r1.id != r2.id
        assert r1.prompt_hash == "multi_1"
        assert r2.prompt_hash == "multi_2"

    async def test_log_request_same_hash(
        self, db_session: AsyncSession
    ) -> None:
        """Logging the same prompt_hash twice creates two records (no dedup)."""
        repo = LLMRequestRepository(db_session)

        r1 = await repo.log_request(
            prompt_hash="same_hash",
            response='{"v": 1}',
            tokens=50,
            cost=0.001,
        )
        r2 = await repo.log_request(
            prompt_hash="same_hash",
            response='{"v": 2}',
            tokens=75,
            cost=0.0015,
        )
        await db_session.commit()

        assert r1.id != r2.id

        stmt = select(LLMRequest).where(
            LLMRequest.prompt_hash == "same_hash"
        )
        result = await db_session.execute(stmt)
        all_records = result.scalars().all()
        assert len(all_records) == 2

    async def test_log_request_large_response(
        self, db_session: AsyncSession
    ) -> None:
        """Verify that a large response JSON body can be persisted."""
        repo = LLMRequestRepository(db_session)
        large_response = '{"data": "' + "x" * 10_000 + '"}'

        record = await repo.log_request(
            prompt_hash="large_hash",
            response=large_response,
            tokens=5000,
            cost=0.10,
        )
        await db_session.commit()

        assert record.id is not None
        assert len(record.response_json) > 10_000

    async def test_log_request_zero_cost(
        self, db_session: AsyncSession
    ) -> None:
        """Zero-cost requests (e.g. cached) should persist fine."""
        repo = LLMRequestRepository(db_session)

        record = await repo.log_request(
            prompt_hash="free_tier",
            response='{"cached": true}',
            tokens=0,
            cost=0.0,
        )
        await db_session.commit()

        assert record.tokens_used == 0
        assert record.cost_usd == pytest.approx(0.0)
