"""Regression test for DEBT-030 PR1 hotfix: ValueError serialization.

Bot review identified that exc.errors() may carry ctx.error as a raw
ValueError, which JSONResponse cannot serialize. Default FastAPI handler
uses jsonable_encoder; our custom one must too.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel, field_validator

from src.core.error_handler import register_exception_handlers


class _SchemaWithValueErrorValidator(BaseModel):
    """Mirrors the admin_graphics.py pattern that triggered the bot finding."""

    headline: str

    @field_validator("headline")
    @classmethod
    def _reject_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("headline must not be empty")
        return v


@pytest.fixture()
def app() -> FastAPI:
    """Generic, non-publication app to exercise the FALLBACK branch."""
    api = FastAPI()
    register_exception_handlers(api)

    @api.post("/api/v1/test/schema")
    async def post_schema(body: _SchemaWithValueErrorValidator):
        return {"ok": True, "headline": body.headline}

    return api


@pytest.fixture()
def publications_app() -> FastAPI:
    """App with PATCH /api/v1/admin/publications/{id} to exercise NESTED branch."""
    api = FastAPI()
    register_exception_handlers(api)

    @api.patch("/api/v1/admin/publications/{publication_id}")
    async def patch_publication(
        publication_id: int, body: _SchemaWithValueErrorValidator
    ):
        return {"ok": True, "id": publication_id}

    return api


@pytest.mark.asyncio
async def test_fallback_branch_serializes_value_error(app: FastAPI) -> None:
    """Validator raising ValueError must yield 422, not unhandled 500."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/test/schema", json={"headline": "   "})

    assert response.status_code == 422, response.text
    body = response.json()
    assert "detail" in body
    # detail is the FastAPI default list shape after jsonable_encoder
    assert isinstance(body["detail"], list)


@pytest.mark.asyncio
async def test_nested_branch_serializes_value_error(publications_app: FastAPI) -> None:
    """Same regression for PATCH /admin/publications/{id} nested envelope."""
    transport = ASGITransport(app=publications_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.patch(
            "/api/v1/admin/publications/1", json={"headline": "   "}
        )

    assert response.status_code == 422, response.text
    body = response.json()
    detail = body["detail"]
    assert detail["error_code"] == "PUBLICATION_UPDATE_PAYLOAD_INVALID"
    assert "validation_errors" in detail["details"]
    # Each entry must be JSON-serializable (e.g., ctx.error coerced to string).
    for err in detail["details"]["validation_errors"]:
        assert isinstance(err, dict)
        if "ctx" in err and "error" in err["ctx"]:
            assert isinstance(err["ctx"]["error"], str), err["ctx"]
