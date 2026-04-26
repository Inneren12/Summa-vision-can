"""Focused tests for AuthMiddleware structured error codes."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.core.security.auth import AuthMiddleware


@pytest.fixture()
def app() -> FastAPI:
    api = FastAPI()

    @api.patch("/api/v1/admin/publications/{publication_id}")
    async def protected(publication_id: int):
        return {"ok": True, "id": publication_id}

    api.add_middleware(AuthMiddleware, admin_api_key="test-admin-key")
    return api


@pytest.mark.asyncio
async def test_missing_api_key_returns_structured_error_code(app: FastAPI) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.patch("/api/v1/admin/publications/1", json={})

    assert response.status_code == 401
    body = response.json()
    assert body["error_code"] == "AUTH_API_KEY_MISSING"


@pytest.mark.asyncio
async def test_invalid_api_key_returns_structured_error_code(app: FastAPI) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.patch(
            "/api/v1/admin/publications/1",
            json={},
            headers={"X-API-KEY": "wrong-key"},
        )

    assert response.status_code == 401
    body = response.json()
    assert body["error_code"] == "AUTH_API_KEY_INVALID"


@pytest.mark.asyncio
async def test_rate_limited_returns_structured_error_code(app: FastAPI) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        last = None
        for _ in range(11):
            last = await client.patch(
                "/api/v1/admin/publications/1",
                json={},
                headers={"X-API-KEY": "test-admin-key"},
            )

    assert last is not None
    assert last.status_code == 429
    body = last.json()
    assert body["error_code"] == "AUTH_ADMIN_RATE_LIMITED"
