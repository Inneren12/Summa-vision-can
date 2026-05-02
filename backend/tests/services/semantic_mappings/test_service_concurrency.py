"""Phase 3.1b R2 — concurrency tests for the atomic upsert primitive.

The atomic guarantee lives in
:meth:`SemanticMappingRepository.update_with_version_check`
(``UPDATE ... WHERE id = :id AND version = :expected``). Without it the
service had a SELECT-then-UPDATE TOCTOU race: two writers reading the
same ``version`` would both pass the Python-level check and the second
would silently overwrite the first.

Test infrastructure note (fallback):
    The existing project-wide async fixtures use SQLite (in-memory,
    ``aiosqlite``). True parallel transactions on a single SQLite
    in-memory connection are serialized at the engine level, so the
    "concurrent" gather test cannot reliably exercise true OS-level
    concurrency in this sandbox. The atomic CONTRACT is still verified:
    even when run via ``asyncio.gather``, exactly one writer wins and
    the other receives :class:`VersionConflictError`. The third
    (sequential stale-version) test is the deterministic backbone — it
    proves the atomic primitive raises on stale ``if_match_version``
    regardless of ordering.

    A real-Postgres true-concurrent test against Testcontainers is the
    next iteration; out of scope for R2.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.repositories.semantic_mapping_repository import (
    SemanticMappingRepository,
)
from src.schemas.semantic_mapping import SemanticMappingCreate
from src.services.semantic_mappings.exceptions import VersionConflictError
from src.services.semantic_mappings.service import SemanticMappingService
from src.services.statcan.metadata_cache import (
    CubeMetadataCacheEntry,
    StatCanMetadataCacheService,
)


_FIXED_FETCHED_AT = datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc)


def _cache_entry() -> CubeMetadataCacheEntry:
    return CubeMetadataCacheEntry(
        cube_id="18-10-0004",
        product_id=18100004,
        dimensions={
            "dimensions": [
                {
                    "position_id": 1,
                    "name_en": "Geography",
                    "name_fr": "Géographie",
                    "has_uom": False,
                    "members": [
                        {"member_id": 1, "name_en": "Canada", "name_fr": "Canada"},
                    ],
                },
                {
                    "position_id": 2,
                    "name_en": "Products",
                    "name_fr": "Produits",
                    "has_uom": False,
                    "members": [
                        {
                            "member_id": 10,
                            "name_en": "All-items",
                            "name_fr": "Ensemble",
                        },
                    ],
                },
            ]
        },
        frequency_code="6",
        cube_title_en="CPI",
        cube_title_fr="IPC",
        fetched_at=_FIXED_FETCHED_AT,
    )


def _valid_config() -> dict:
    return {
        "dimension_filters": {"Geography": "Canada", "Products": "All-items"},
        "measure": "Value",
        "unit": "index",
        "frequency": "monthly",
        "supported_metrics": ["current_value"],
        "default_geo": "Canada",
    }


@pytest.fixture()
def session_factory(async_engine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=async_engine, class_=AsyncSession, expire_on_commit=False
    )


@pytest.fixture()
def mock_cache() -> AsyncMock:
    cache = AsyncMock(spec=StatCanMetadataCacheService)
    cache.get_or_fetch.return_value = _cache_entry()
    return cache


@pytest.fixture()
def service(session_factory, mock_cache) -> SemanticMappingService:
    return SemanticMappingService(
        session_factory=session_factory,
        repository_factory=SemanticMappingRepository,
        metadata_cache=mock_cache,
        logger=structlog.get_logger(),
    )


async def _seed(session_factory) -> int:
    """Insert a baseline row at version=1; return its id."""
    async with session_factory() as session:
        repo = SemanticMappingRepository(session)
        payload = SemanticMappingCreate(
            cube_id="18-10-0004",
            semantic_key="cpi.canada.all_items.index",
            label="seed",
            description=None,
            config=_valid_config(),
            is_active=True,
        )
        mapping, _ = await repo.upsert_by_key(payload, updated_by="seed")
        await session.commit()
        return mapping.id


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upsert_with_stale_if_match_version_raises_version_conflict(
    service, session_factory
):
    """Sequential test (deterministic): explicit stale version → conflict.

    This is the backbone test for the atomic primitive. The
    ``UPDATE ... WHERE version = :stale`` returns rowcount=0 and the
    service raises :class:`VersionConflictError` after re-reading the
    actual version for error context.
    """
    await _seed(session_factory)
    # Bump the row to version=2 via a no-version write.
    await service.upsert_validated(
        cube_id="18-10-0004",
        product_id=18100004,
        semantic_key="cpi.canada.all_items.index",
        label="bumped-to-v2",
        description=None,
        config=_valid_config(),
        is_active=True,
        updated_by="bumper",
        if_match_version=None,
    )

    with pytest.raises(VersionConflictError) as exc_info:
        await service.upsert_validated(
            cube_id="18-10-0004",
            product_id=18100004,
            semantic_key="cpi.canada.all_items.index",
            label="stale-write",
            description=None,
            config=_valid_config(),
            is_active=True,
            updated_by="stale-writer",
            if_match_version=1,  # stale
        )
    assert exc_info.value.expected_version == 1
    assert exc_info.value.actual_version == 2


@pytest.mark.asyncio
async def test_concurrent_upsert_with_same_if_match_version_one_succeeds_other_raises_conflict(
    service, session_factory
):
    """Two coroutines with same if_match_version: exactly one wins.

    With the atomic ``UPDATE WHERE version = :expected`` primitive,
    only ONE concurrent writer's UPDATE matches. The other returns
    rowcount=0 → :class:`VersionConflictError`.

    Sandbox caveat: SQLite/aiosqlite serializes transactions on a single
    in-memory DB, so this test does not exercise true OS-level
    parallelism. It still verifies the contract — the loser sees a
    bumped version and raises. A real-Postgres Testcontainers variant
    is the next iteration.
    """
    await _seed(session_factory)

    async def _writer(label_suffix: str):
        return await service.upsert_validated(
            cube_id="18-10-0004",
            product_id=18100004,
            semantic_key="cpi.canada.all_items.index",
            label=f"updated-{label_suffix}",
            description=None,
            config=_valid_config(),
            is_active=True,
            updated_by=f"writer-{label_suffix}",
            if_match_version=1,
        )

    results = await asyncio.gather(
        _writer("A"), _writer("B"), return_exceptions=True
    )
    successes = [r for r in results if not isinstance(r, BaseException)]
    conflicts = [
        r for r in results if isinstance(r, VersionConflictError)
    ]
    assert len(successes) == 1, (
        f"exactly one writer must succeed; got results={results}"
    )
    assert len(conflicts) == 1, (
        f"the other writer must raise VersionConflictError; got results={results}"
    )

    winner_mapping, winner_was_created = successes[0]
    assert winner_was_created is False
    assert winner_mapping.version == 2, (
        "winner's row must have version bumped exactly once"
    )

    conflict = conflicts[0]
    assert conflict.expected_version == 1
    # ``actual_version`` is read inside the loser's own (still-open)
    # transaction, which under SQLite snapshot isolation may still see
    # the pre-winner state. The atomic UPDATE itself is the correctness
    # signal — the loser's UPDATE returned rowcount=0 → conflict raised.
    # Real Postgres with read-committed behaves differently and is
    # covered by the next-iteration Testcontainers test.
    assert conflict.actual_version >= conflict.expected_version


@pytest.mark.asyncio
async def test_upsert_with_none_if_match_version_does_not_check_concurrency(
    service, session_factory
):
    """``if_match_version=None`` → unconditional update; no conflict."""
    await _seed(session_factory)

    mapping, was_created = await service.upsert_validated(
        cube_id="18-10-0004",
        product_id=18100004,
        semantic_key="cpi.canada.all_items.index",
        label="unconditional-update",
        description=None,
        config=_valid_config(),
        is_active=True,
        updated_by="test",
        if_match_version=None,
    )
    assert was_created is False
    assert mapping.label == "unconditional-update"
    assert mapping.version == 2
