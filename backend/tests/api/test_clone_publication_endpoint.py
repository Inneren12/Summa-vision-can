from __future__ import annotations

import json
from collections.abc import AsyncGenerator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from src.api.routers.admin_publications import _get_audit, _get_repo, router
from src.core.database import Base, get_db
from src.core.error_handler import register_exception_handlers
from src.core.security.auth import AuthMiddleware
from src.models.publication import Publication, PublicationStatus
from src.repositories.publication_repository import PublicationRepository
from src.services.audit import AuditWriter
from tests.conftest import make_publication


@pytest.fixture()
async def engine() -> AsyncGenerator[AsyncEngine, None]:
    eng = create_async_engine('sqlite+aiosqlite:///:memory:', echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest.fixture()
async def session_factory(engine: AsyncEngine):
    return async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


def _make_app(session_factory) -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(router)

    async def _override_db() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def _override_repo() -> AsyncGenerator[PublicationRepository, None]:
        async with session_factory() as session:
            try:
                yield PublicationRepository(session)
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def _override_audit() -> AsyncGenerator[AuditWriter, None]:
        async with session_factory() as session:
            try:
                yield AuditWriter(session)
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[_get_repo] = _override_repo
    app.dependency_overrides[_get_audit] = _override_audit
    app.add_middleware(AuthMiddleware, admin_api_key='test-admin-key')
    return app


def _auth_headers() -> dict[str, str]:
    return {'X-API-KEY': 'test-admin-key'}


async def _seed_publication(session_factory, *, status: PublicationStatus) -> Publication:
    async with session_factory() as session:
        pub = make_publication(
            headline='Seed',
            chart_type='bar',
            visual_config=json.dumps({'size': 'instagram'}),
            review=json.dumps({'workflow': 'published', 'history': [], 'comments': []}),
            source_product_id='P1',
            config_hash='abcabcabcabcabcd',
            version=1,
            status=status,
        )
        session.add(pub)
        await session.commit()
        await session.refresh(pub)
        return pub


@pytest.mark.asyncio
async def test_clone_endpoint_201(session_factory) -> None:
    app = _make_app(session_factory)
    src = await _seed_publication(session_factory, status=PublicationStatus.PUBLISHED)
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        resp = await client.post(f'/api/v1/admin/publications/{src.id}/clone', headers=_auth_headers())
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data['id'] != str(src.id)
    assert data['cloned_from_publication_id'] == src.id


@pytest.mark.asyncio
async def test_clone_endpoint_404_with_error_code(session_factory) -> None:
    app = _make_app(session_factory)
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        resp = await client.post('/api/v1/admin/publications/99999/clone', headers=_auth_headers())
    assert resp.status_code == 404
    assert resp.json()['detail']['error_code'] == 'PUBLICATION_NOT_FOUND'


@pytest.mark.asyncio
async def test_clone_endpoint_409_on_draft_source(session_factory) -> None:
    app = _make_app(session_factory)
    src = await _seed_publication(session_factory, status=PublicationStatus.DRAFT)
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        resp = await client.post(f'/api/v1/admin/publications/{src.id}/clone', headers=_auth_headers())
    assert resp.status_code == 409
    assert resp.json()['detail']['error_code'] == 'PUBLICATION_CLONE_NOT_ALLOWED'


@pytest.mark.asyncio
async def test_clone_endpoint_persists_to_db(session_factory) -> None:
    app = _make_app(session_factory)
    src = await _seed_publication(session_factory, status=PublicationStatus.PUBLISHED)
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        resp = await client.post(f'/api/v1/admin/publications/{src.id}/clone', headers=_auth_headers())
    clone_id = int(resp.json()['id'])
    async with session_factory() as session:
        clone = (await session.execute(select(Publication).where(Publication.id == clone_id))).scalar_one()
    assert clone.cloned_from_publication_id == src.id
    assert clone.status == PublicationStatus.DRAFT


# ---------------------------------------------------------------------------
# Phase 2.2.0 chunk 3c — clone path lineage_key inheritance
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_clone_inherits_source_lineage_key(session_factory) -> None:
    """Clone's lineage_key must equal the source publication's lineage_key."""
    app = _make_app(session_factory)
    src = await _seed_publication(session_factory, status=PublicationStatus.PUBLISHED)
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        resp = await client.post(
            f'/api/v1/admin/publications/{src.id}/clone',
            headers=_auth_headers(),
        )

    assert resp.status_code == 201, resp.text
    clone_payload = resp.json()
    assert clone_payload['lineage_key'] == src.lineage_key, (
        f"clone lineage_key {clone_payload['lineage_key']!r} differs from "
        f"source {src.lineage_key!r}"
    )


@pytest.mark.asyncio
async def test_clone_of_clone_preserves_lineage_chain(session_factory) -> None:
    """A → B → C: every link in the clone chain shares the root's lineage_key."""
    app = _make_app(session_factory)
    src = await _seed_publication(session_factory, status=PublicationStatus.PUBLISHED)
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        # First clone (B from A)
        resp_b = await client.post(
            f'/api/v1/admin/publications/{src.id}/clone',
            headers=_auth_headers(),
        )
        assert resp_b.status_code == 201
        clone_b_id = int(resp_b.json()['id'])

        # Promote B to PUBLISHED so it can itself be cloned
        await client.post(
            f'/api/v1/admin/publications/{clone_b_id}/publish',
            headers=_auth_headers(),
        )

        # Second clone (C from B)
        resp_c = await client.post(
            f'/api/v1/admin/publications/{clone_b_id}/clone',
            headers=_auth_headers(),
        )

    assert resp_c.status_code == 201, resp_c.text
    assert resp_b.json()['lineage_key'] == src.lineage_key
    assert resp_c.json()['lineage_key'] == src.lineage_key


@pytest.mark.asyncio
async def test_clone_of_source_with_null_lineage_key_returns_500_with_diagnostic(
    session_factory, monkeypatch
) -> None:
    """If a source somehow has null lineage_key, derive raises ValueError →
    surfaced as HTTP 500. Defensive: the post-Phase-2.2.0 NOT NULL constraint
    makes this state unreachable in practice, but the helper still guards.
    """
    app = _make_app(session_factory)
    src = await _seed_publication(session_factory, status=PublicationStatus.PUBLISHED)

    # Patch derive_clone_lineage_key to simulate a null-lineage_key source
    # without violating the DB-layer NOT NULL constraint at seed time.
    from src.services.publications import clone as clone_module

    def _raise_value_error(source) -> str:  # type: ignore[no-untyped-def]
        raise ValueError(
            f"Publication id={source.id} has null lineage_key; "
            "data integrity violation post-Phase-2.2.0 migration"
        )

    monkeypatch.setattr(
        clone_module, 'derive_clone_lineage_key', _raise_value_error
    )

    # raise_app_exceptions=False so unhandled ValueError surfaces as a 500
    # response (matching uvicorn behaviour) rather than propagating into the
    # test runtime.
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url='http://test') as client:
        resp = await client.post(
            f'/api/v1/admin/publications/{src.id}/clone',
            headers=_auth_headers(),
        )

    assert resp.status_code == 500, (
        f"expected 500 from null-lineage_key data integrity violation, "
        f"got {resp.status_code}: {resp.text}"
    )
