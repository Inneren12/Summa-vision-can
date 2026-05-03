"""Phase 3.1ab: end-to-end integration test for ``SemanticMappingService``.

Mirrors :mod:`tests.integration.test_metadata_cache_integration` Postgres
pattern: relies on the ``pg_session`` fixture which boots Alembic against
``TEST_DATABASE_URL``. Skips when no Postgres URL is set.

The StatCan client is mocked so cube metadata is primed deterministically
without a network call. Everything else (cache repository, semantic mapping
repository, table schema) is real.
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.repositories.semantic_mapping_repository import (
    SemanticMappingRepository,
)
from src.services.semantic_mappings.exceptions import DimensionMismatchError
from src.services.semantic_mappings.service import SemanticMappingService
from src.services.statcan.client import StatCanClient
from src.services.statcan.metadata_cache import StatCanMetadataCacheService
from src.services.statcan.schemas import CubeMetadataResponse


_FIXED_NOW = datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc)


def _payload() -> CubeMetadataResponse:
    return CubeMetadataResponse.model_validate(
        {
            "productId": 18100004,
            "cubeTitleEn": "CPI",
            "cubeTitleFr": "IPC",
            "frequencyCode": 6,
            "scalarFactorCode": 0,
            "dimension": [
                {
                    "dimensionNameEn": "Geography",
                    "dimensionNameFr": "Géographie",
                    "dimensionPositionId": 1,
                    "hasUom": False,
                    "member": [
                        {
                            "memberId": 1,
                            "memberNameEn": "Canada",
                            "memberNameFr": "Canada",
                        },
                    ],
                },
                {
                    "dimensionNameEn": "Products",
                    "dimensionNameFr": "Produits",
                    "dimensionPositionId": 2,
                    "hasUom": False,
                    "member": [
                        {
                            "memberId": 10,
                            "memberNameEn": "All-items",
                            "memberNameFr": "Ensemble",
                        },
                    ],
                },
            ],
        }
    )


def _valid_config() -> dict:
    return {
        "dimension_filters": {"Geography": "Canada", "Products": "All-items"},
        "measure": "Value",
        "unit": "index",
        "frequency": "monthly",
        "supported_metrics": [
            "current_value",
            "year_over_year_change",
            "previous_period_change",
        ],
    }


def _build_service(pg_session) -> tuple[SemanticMappingService, async_sessionmaker]:
    bind = pg_session.bind
    factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
        bind=bind, class_=AsyncSession, expire_on_commit=False
    )

    client = AsyncMock(spec=StatCanClient)
    client.get_cube_metadata.return_value = _payload()

    cache = StatCanMetadataCacheService(
        session_factory=factory,
        client=client,
        clock=lambda: _FIXED_NOW,
        logger=structlog.get_logger(),
    )

    service = SemanticMappingService(
        session_factory=factory,
        repository_factory=SemanticMappingRepository,
        metadata_cache=cache,
        logger=structlog.get_logger(),
    )
    return service, factory


@pytest.mark.asyncio
async def test_upsert_validated_persists_row_when_validation_passes(pg_session):
    service, factory = _build_service(pg_session)

    mapping, _was_created = await service.upsert_validated(
        cube_id="18-10-0004",
        product_id=18100004,
        semantic_key="cpi.canada.all_items.index",
        label="CPI — Canada, all-items",
        description="headline",
        config=_valid_config(),
        is_active=True,
        updated_by="seed",
    )

    assert mapping.id is not None
    assert mapping.cube_id == "18-10-0004"
    assert mapping.semantic_key == "cpi.canada.all_items.index"

    async with factory() as session:
        repo = SemanticMappingRepository(session)
        fetched = await repo.get_by_key(
            "18-10-0004", "cpi.canada.all_items.index"
        )
    assert fetched is not None
    assert fetched.label == "CPI — Canada, all-items"
    assert fetched.config["dimension_filters"] == {
        "Geography": "Canada",
        "Products": "All-items",
    }


@pytest.mark.asyncio
async def test_upsert_validated_does_not_persist_row_when_validation_fails(
    pg_session,
):
    service, factory = _build_service(pg_session)

    bad_config = _valid_config()
    bad_config["dimension_filters"] = {"Province": "Ontario"}  # not in cube

    with pytest.raises(DimensionMismatchError):
        await service.upsert_validated(
            cube_id="18-10-0004",
            product_id=18100004,
            semantic_key="cpi.canada.bad",
            label="bad",
            description=None,
            config=bad_config,
            is_active=True,
            updated_by="seed",
        )

    async with factory() as session:
        repo = SemanticMappingRepository(session)
        fetched = await repo.get_by_key("18-10-0004", "cpi.canada.bad")
    assert fetched is None
