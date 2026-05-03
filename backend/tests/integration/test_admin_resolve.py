"""Phase 3.1c — admin resolve router HTTP-level integration tests.

Recon §6.3 (6 tests) + impl-addendum 1.1 (``test_resolve_missing_observation_round_trip``)
→ 7 tests. Despite living under ``tests/integration/`` (recon places
the file there), these run against an in-memory SQLite engine via
:class:`httpx.AsyncClient` + :class:`ASGITransport`, mirroring the
3.1b admin-router test pattern in
``tests/api/admin/test_semantic_mappings_endpoints.py``. No Postgres
required — that keeps the suite runnable in CI without Alembic
upgrade. (The recon's "integration" wording predates the move to
the lighter ASGI pattern; tracked informally as a follow-up.)
"""
from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
import structlog
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.api.dependencies.statcan import (
    get_statcan_metadata_cache_service,
    get_statcan_value_cache_service,
)
from src.api.routers.admin_resolve import (
    _get_resolve_service,
    _get_session_factory_dep,
    router as admin_resolve_router,
)
from src.core.database import Base
from src.models.semantic_mapping import SemanticMapping
from src.models.semantic_value_cache import SemanticValueCache
from src.repositories.semantic_mapping_repository import (
    SemanticMappingRepository,
)
from src.services.resolve.service import ResolveService
from src.services.statcan.metadata_cache import StatCanMetadataCacheService
from src.services.statcan.value_cache import StatCanValueCacheService
from src.services.statcan.value_cache_schemas import (
    AutoPrimeResult,
    ValueCacheRow,
)


_FIXED_FETCHED_AT = datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Fixtures (mirror tests/api/admin/test_semantic_mappings_endpoints.py)
# ---------------------------------------------------------------------------


@pytest.fixture()
async def engine() -> AsyncGenerator[AsyncEngine, None]:
    eng = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest.fixture()
async def session_factory(
    engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )


def _row_dto(*, value: Decimal | None, missing: bool) -> ValueCacheRow:
    return ValueCacheRow(
        id=1,
        cube_id="18-10-0004",
        product_id=18100004,
        semantic_key="cpi.canada.all_items.index",
        coord="1.10.0.0.0.0.0.0.0.0",
        ref_period="2025-12",
        period_start=None,
        value=value,
        missing=missing,
        decimals=2,
        scalar_factor_code=0,
        symbol_code=0,
        security_level_code=0,
        status_code=0,
        frequency_code=6,
        vector_id=None,
        response_status_code=None,
        source_hash="hash-abc",
        fetched_at=_FIXED_FETCHED_AT,
        release_time=None,
        is_stale=False,
    )


async def _seed_mapping(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    is_active: bool = True,
) -> None:
    async with session_factory() as session:
        m = SemanticMapping(
            cube_id="18-10-0004",
            product_id=18100004,
            semantic_key="cpi.canada.all_items.index",
            label="CPI",
            description=None,
            config={
                "dimension_filters": {
                    "Geography": "Canada",
                    "Products": "All-items",
                },
                "unit": "index",
                "frequency": "monthly",
            },
            is_active=is_active,
        )
        session.add(m)
        await session.commit()


def _build_app(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    get_cached_returns: list,
    auto_prime_result: AutoPrimeResult = AutoPrimeResult(0, 0, 0),
) -> tuple[FastAPI, MagicMock]:
    app = FastAPI()
    app.include_router(admin_resolve_router)

    value_cache = MagicMock(spec=StatCanValueCacheService)
    value_cache.get_cached = AsyncMock(side_effect=get_cached_returns)
    value_cache.auto_prime = AsyncMock(return_value=auto_prime_result)

    metadata_cache = MagicMock(spec=StatCanMetadataCacheService)
    metadata_cache.get_cached = AsyncMock(return_value=None)

    def _override_factory():
        return session_factory

    def _override_value_cache():
        return value_cache

    def _override_metadata_cache():
        return metadata_cache

    def _override_service():
        return ResolveService(
            session_factory=session_factory,
            mapping_repository_factory=SemanticMappingRepository,
            value_cache_service=value_cache,
            metadata_cache=metadata_cache,
            logger=structlog.get_logger(),
        )

    app.dependency_overrides[_get_session_factory_dep] = _override_factory
    app.dependency_overrides[get_statcan_value_cache_service] = (
        _override_value_cache
    )
    app.dependency_overrides[get_statcan_metadata_cache_service] = (
        _override_metadata_cache
    )
    app.dependency_overrides[_get_resolve_service] = _override_service
    return app, value_cache


@pytest.fixture()
async def http_client_factory():
    async def _make(app: FastAPI) -> AsyncClient:
        transport = ASGITransport(app=app)
        return AsyncClient(transport=transport, base_url="http://test")

    return _make


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resolve_happy_existing_cache(session_factory, http_client_factory):
    await _seed_mapping(session_factory)
    app, _ = _build_app(
        session_factory,
        get_cached_returns=[[_row_dto(value=Decimal("100.0"), missing=False)]],
    )
    async with await http_client_factory(app) as client:
        resp = await client.get(
            "/api/v1/admin/resolve/18-10-0004/cpi.canada.all_items.index",
            params=[("dim", 1), ("member", 1), ("dim", 2), ("member", 10)],
        )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["cache_status"] == "hit"
    assert body["value"] == "100.0"
    assert body["missing"] is False


@pytest.mark.asyncio
async def test_resolve_missing_observation_round_trip(
    session_factory, http_client_factory
):
    await _seed_mapping(session_factory)
    app, _ = _build_app(
        session_factory,
        get_cached_returns=[[_row_dto(value=None, missing=True)]],
    )
    async with await http_client_factory(app) as client:
        resp = await client.get(
            "/api/v1/admin/resolve/18-10-0004/cpi.canada.all_items.index",
            params=[("dim", 1), ("member", 1), ("dim", 2), ("member", 10)],
        )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["value"] is None
    assert body["missing"] is True
    assert body["cache_status"] == "hit"
    # Regression shield: the literal "None" must NEVER appear in the
    # response text (would indicate ``str(None)`` corruption).
    assert '"None"' not in resp.text


@pytest.mark.asyncio
async def test_resolve_cold_cache_full_pipeline(session_factory, http_client_factory):
    await _seed_mapping(session_factory)
    app, vc = _build_app(
        session_factory,
        get_cached_returns=[[], [_row_dto(value=Decimal("99.9"), missing=False)]],
        auto_prime_result=AutoPrimeResult(1, 0, 0),
    )
    async with await http_client_factory(app) as client:
        resp = await client.get(
            "/api/v1/admin/resolve/18-10-0004/cpi.canada.all_items.index",
            params=[("dim", 1), ("member", 1), ("dim", 2), ("member", 10)],
        )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["cache_status"] == "primed"
    assert body["value"] == "99.9"
    vc.auto_prime.assert_awaited_once()


@pytest.mark.asyncio
async def test_resolve_404_mapping_not_found(session_factory, http_client_factory):
    # NO mapping seeded.
    app, _ = _build_app(session_factory, get_cached_returns=[[]])
    async with await http_client_factory(app) as client:
        resp = await client.get(
            "/api/v1/admin/resolve/18-10-0004/cpi.canada.all_items.index",
            params=[("dim", 1), ("member", 1), ("dim", 2), ("member", 10)],
        )
    assert resp.status_code == 404
    assert resp.json()["detail"]["error_code"] == "MAPPING_NOT_FOUND"


@pytest.mark.asyncio
async def test_resolve_404_cache_miss_after_prime(
    session_factory, http_client_factory
):
    await _seed_mapping(session_factory)
    app, _ = _build_app(
        session_factory,
        get_cached_returns=[[], []],
        auto_prime_result=AutoPrimeResult(0, 0, 0, error="upstream nope"),
    )
    async with await http_client_factory(app) as client:
        resp = await client.get(
            "/api/v1/admin/resolve/18-10-0004/cpi.canada.all_items.index",
            params=[("dim", 1), ("member", 1), ("dim", 2), ("member", 10)],
        )
    assert resp.status_code == 404
    detail = resp.json()["detail"]
    assert detail["error_code"] == "RESOLVE_CACHE_MISS"
    assert detail["details"]["coord"] == "1.10.0.0.0.0.0.0.0.0"
    assert detail["details"]["prime_attempted"] is True
    assert detail["details"]["prime_error_code"] == "upstream"


@pytest.mark.asyncio
async def test_resolve_filters_validation_400(session_factory, http_client_factory):
    await _seed_mapping(session_factory)
    app, _ = _build_app(session_factory, get_cached_returns=[[]])
    async with await http_client_factory(app) as client:
        # Only one dim provided; mapping requires two.
        resp = await client.get(
            "/api/v1/admin/resolve/18-10-0004/cpi.canada.all_items.index",
            params=[("dim", 1), ("member", 1)],
        )
    assert resp.status_code == 400, resp.text
    assert resp.json()["detail"]["error_code"] == "RESOLVE_INVALID_FILTERS"


@pytest.mark.asyncio
async def test_resolve_auth_required(session_factory, http_client_factory):
    """Auth contract — verifies that the route IS registered under the
    ``/api/v1/admin/...`` prefix that ``AuthMiddleware`` guards.

    The module-level ``_build_app`` fixture instantiates a FastAPI app
    WITHOUT mounting :class:`AuthMiddleware`, so 401 cannot be asserted
    here. Instead we assert the URL prefix exists on the registered
    router (the prefix is the auth gate's match key); this gives us a
    static check that future refactors cannot accidentally move the
    endpoint out of the admin namespace.

    A cross-cutting middleware test for X-API-KEY enforcement on the
    full app lives in ``tests/api/test_auth_middleware.py``.
    """
    assert admin_resolve_router.prefix == "/api/v1/admin/resolve"
