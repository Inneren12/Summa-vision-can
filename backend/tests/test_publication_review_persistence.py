"""Tests for Publication.review persistence (Stage 3 PR 4).

Covers:
* :class:`ReviewPayload` schema shape and validator behavior.
* :class:`PublicationCreate` / :class:`PublicationUpdate` accept
  ``review`` and pass-through to the repository.
* :class:`PublicationResponse` parses the stored JSON string into a dict.
* :class:`PublicationRepository._serialize_review` /
  :meth:`_deserialize_review` round-trip.
* Router behavior: workflow → status sync, audit emission,
  publish/unpublish mirror into ``review.workflow``.
* Public gallery endpoint does NOT leak ``review``.

Fixtures mirror ``tests/api/test_admin_publications.py``: per-test
in-memory SQLite engine + overridden DI for router tests, plus
``db_session`` from the root ``conftest.py`` for repository-only tests.
"""
from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from typing import Any

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.api.routers.admin_publications import (
    _get_audit,
    _get_repo,
    router as admin_router,
)
from src.api.routers.public_graphics import (
    _get_repo as _get_public_repo,
    _get_storage as _get_public_storage,
    get_gallery_limiter,
    router as public_graphics_router,
)
from src.core.database import Base
from src.core.security.auth import AuthMiddleware
from src.core.security.ip_rate_limiter import InMemoryRateLimiter
from src.core.storage import StorageInterface
from src.models.audit_event import AuditEvent
from src.models.publication import Publication, PublicationStatus
from src.repositories.publication_repository import PublicationRepository
from src.schemas.events import EventType
from src.schemas.publication import (
    PublicationCreate,
    PublicationResponse,
    PublicationUpdate,
    ReviewPayload,
)
from src.services.audit import AuditWriter


# ---------------------------------------------------------------------------
# Test infrastructure — mirrors test_admin_publications.py patterns
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
async def session_factory(engine: AsyncEngine):
    return async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )


class _NullStorage(StorageInterface):  # pragma: no cover - stub
    async def upload_bytes(self, data: bytes, key: str) -> None:
        return None

    async def download_bytes(self, key: str) -> bytes:
        return b""

    async def upload_dataframe_as_csv(self, df: Any, path: str) -> None:
        return None

    async def upload_raw(
        self, data: bytes, path: str, content_type: str = "application/octet-stream"
    ) -> None:
        return None

    async def download_csv(self, path: str) -> Any:
        return None

    async def list_objects(self, prefix: str) -> list[str]:
        return []

    async def generate_presigned_url(self, path: str, ttl: int = 3600) -> str:
        return "https://cdn.example/stub.png"

    async def delete_object(self, key: str) -> None:
        return None


def _make_admin_app(session_factory) -> FastAPI:
    app = FastAPI()
    app.include_router(admin_router)

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

    app.dependency_overrides[_get_repo] = _override_repo
    app.dependency_overrides[_get_audit] = _override_audit
    app.add_middleware(AuthMiddleware, admin_api_key="test-admin-key")
    return app


def _make_public_app(session_factory) -> FastAPI:
    app = FastAPI()
    app.include_router(public_graphics_router)

    async def _override_public_repo() -> AsyncGenerator[PublicationRepository, None]:
        async with session_factory() as session:
            try:
                yield PublicationRepository(session)
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    def _override_storage() -> StorageInterface:
        return _NullStorage()

    def _override_limiter() -> InMemoryRateLimiter:
        return InMemoryRateLimiter(max_requests=10_000, window_seconds=60)

    app.dependency_overrides[_get_public_repo] = _override_public_repo
    app.dependency_overrides[_get_public_storage] = _override_storage
    app.dependency_overrides[get_gallery_limiter] = _override_limiter
    return app


def _auth_headers() -> dict[str, str]:
    return {"X-API-KEY": "test-admin-key"}


_REVIEW_BASE: dict[str, Any] = {
    "workflow": "draft",
    "history": [
        {
            "ts": "2026-04-19T10:00:00+00:00",
            "action": "created",
            "summary": "Document created",
            "author": "you",
            "fromWorkflow": None,
            "toWorkflow": "draft",
        }
    ],
    "comments": [],
}

_CREATE_BASE: dict[str, Any] = {
    "headline": "Housing starts hit a record",
    "chart_type": "bar",
    "visual_config": {
        "layout": "single_stat",
        "palette": "housing",
        "background": "gradient_warm",
        "size": "instagram",
    },
}


# ===========================================================================
# Schema tests (ReviewPayload + Create/Update/Response)
# ===========================================================================


class TestReviewPayloadSchema:
    def test_accepts_well_formed_payload_all_workflow_states(self) -> None:
        for state in ("draft", "in_review", "approved", "exported", "published"):
            payload = ReviewPayload(workflow=state)  # type: ignore[arg-type]
            assert payload.workflow == state
            assert payload.history == []
            assert payload.comments == []

    def test_rejects_unknown_workflow_state(self) -> None:
        import pydantic
        with pytest.raises(pydantic.ValidationError):
            ReviewPayload(workflow="bogus")  # type: ignore[arg-type]

    def test_rejects_unknown_top_level_field_extra_forbid(self) -> None:
        import pydantic
        with pytest.raises(pydantic.ValidationError):
            ReviewPayload.model_validate(
                {"workflow": "draft", "bogus": "nope"}
            )

    def test_coerces_none_history_comments_to_empty_lists(self) -> None:
        payload = ReviewPayload.model_validate(
            {"workflow": "draft", "history": None, "comments": None}
        )
        assert payload.history == []
        assert payload.comments == []

    def test_publication_create_accepts_optional_review(self) -> None:
        body = {**_CREATE_BASE, "review": _REVIEW_BASE}
        create = PublicationCreate.model_validate(body)
        assert create.review is not None
        assert create.review.workflow == "draft"

    def test_publication_update_rejects_unknown_top_level_fields(self) -> None:
        import pydantic
        with pytest.raises(pydantic.ValidationError):
            PublicationUpdate.model_validate({"bogus_field": 1})

    def test_publication_response_parses_review_json_string(self) -> None:
        """``review`` stored as JSON string must be parsed back into a dict."""
        review_json = json.dumps(_REVIEW_BASE)

        class _PubLike:
            id = 42
            headline = "h"
            chart_type = "bar"
            eyebrow = None
            description = None
            source_text = None
            footnote = None
            visual_config = None
            review = review_json
            virality_score = None
            status = "DRAFT"
            cdn_url = None
            created_at = __import__("datetime").datetime(2026, 4, 19)
            updated_at = None
            published_at = None

        pub_dict = {
            "id": "42",
            "headline": "h",
            "chart_type": "bar",
            "review": review_json,
            "status": "DRAFT",
            "created_at": "2026-04-19T00:00:00",
        }
        resp = PublicationResponse.model_validate(pub_dict)
        assert resp.review is not None
        assert resp.review.workflow == "draft"
        assert resp.review.history[0]["action"] == "created"


# ===========================================================================
# Repository tests
# ===========================================================================


class TestRepositorySerialization:
    def test_serialize_review_accepts_pydantic_dict_none_string(self) -> None:
        rp = ReviewPayload(**_REVIEW_BASE)
        assert PublicationRepository._serialize_review(None) is None
        assert PublicationRepository._serialize_review(rp) is not None
        assert PublicationRepository._serialize_review(_REVIEW_BASE) is not None
        raw_json = json.dumps(_REVIEW_BASE)
        assert PublicationRepository._serialize_review(raw_json) == raw_json

    def test_serialize_review_rejects_unsupported_types(self) -> None:
        with pytest.raises(TypeError):
            PublicationRepository._serialize_review(123)
        with pytest.raises(TypeError):
            PublicationRepository._serialize_review(["not", "a", "review"])

    def test_deserialize_review_round_trip(self) -> None:
        serialized = PublicationRepository._serialize_review(_REVIEW_BASE)
        assert serialized is not None
        assert PublicationRepository._deserialize_review(serialized) == _REVIEW_BASE
        assert PublicationRepository._deserialize_review(None) is None


class TestRepositoryPersistence:
    @pytest.mark.asyncio
    async def test_create_full_stores_review_as_json(
        self, session_factory
    ) -> None:
        async with session_factory() as session:
            repo = PublicationRepository(session)
            pub = await repo.create_full(
                {**_CREATE_BASE, "review": _REVIEW_BASE}
            )
            await session.commit()
            assert pub.review is not None
            assert json.loads(pub.review) == _REVIEW_BASE

    @pytest.mark.asyncio
    async def test_update_fields_with_review(self, session_factory) -> None:
        async with session_factory() as session:
            repo = PublicationRepository(session)
            pub = await repo.create_full({**_CREATE_BASE})
            await session.commit()
            pub_id = pub.id

        async with session_factory() as session:
            repo = PublicationRepository(session)
            updated = await repo.update_fields(pub_id, {"review": _REVIEW_BASE})
            await session.commit()
            assert updated is not None
            assert json.loads(updated.review) == _REVIEW_BASE

    @pytest.mark.asyncio
    async def test_update_fields_with_review_none_clears_column(
        self, session_factory
    ) -> None:
        async with session_factory() as session:
            repo = PublicationRepository(session)
            pub = await repo.create_full(
                {**_CREATE_BASE, "review": _REVIEW_BASE}
            )
            await session.commit()
            pub_id = pub.id

        async with session_factory() as session:
            repo = PublicationRepository(session)
            updated = await repo.update_fields(pub_id, {"review": None})
            await session.commit()
            assert updated is not None
            assert updated.review is None

    @pytest.mark.asyncio
    async def test_full_round_trip_preserves_payload(
        self, session_factory
    ) -> None:
        rp = ReviewPayload(**_REVIEW_BASE)
        async with session_factory() as session:
            repo = PublicationRepository(session)
            pub = await repo.create_full({**_CREATE_BASE, "review": rp})
            await session.commit()
            pub_id = pub.id

        async with session_factory() as session:
            repo = PublicationRepository(session)
            pub = await repo.get_by_id(pub_id)
            assert pub is not None
            parsed = PublicationRepository._deserialize_review(pub.review)
            assert parsed == _REVIEW_BASE


# ===========================================================================
# Endpoint tests — create / patch / workflow sync
# ===========================================================================


class TestAdminPublicationReviewEndpoints:
    @pytest.mark.asyncio
    async def test_post_with_review_returns_201_and_review(
        self, session_factory
    ) -> None:
        app = _make_admin_app(session_factory)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/admin/publications",
                json={**_CREATE_BASE, "review": _REVIEW_BASE},
                headers=_auth_headers(),
            )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["review"] is not None
        assert data["review"]["workflow"] == "draft"
        assert data["review"]["history"][0]["action"] == "created"

    @pytest.mark.asyncio
    async def test_patch_review_only_preserves_other_fields(
        self, session_factory
    ) -> None:
        app = _make_admin_app(session_factory)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            created = await client.post(
                "/api/v1/admin/publications",
                json={**_CREATE_BASE, "eyebrow": "KICKER"},
                headers=_auth_headers(),
            )
            pub_id = created.json()["id"]

            resp = await client.patch(
                f"/api/v1/admin/publications/{pub_id}",
                json={"review": _REVIEW_BASE},
                headers=_auth_headers(),
            )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["eyebrow"] == "KICKER"
        assert data["review"]["workflow"] == "draft"

    @pytest.mark.asyncio
    async def test_patch_workflow_published_flips_status_to_published(
        self, session_factory
    ) -> None:
        app = _make_admin_app(session_factory)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            created = await client.post(
                "/api/v1/admin/publications",
                json=_CREATE_BASE,
                headers=_auth_headers(),
            )
            pub_id = created.json()["id"]
            assert created.json()["status"] == "DRAFT"

            review_published = {**_REVIEW_BASE, "workflow": "published"}
            resp = await client.patch(
                f"/api/v1/admin/publications/{pub_id}",
                json={"review": review_published},
                headers=_auth_headers(),
            )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["status"] == "PUBLISHED"
        assert data["published_at"] is not None
        assert data["review"]["workflow"] == "published"

    @pytest.mark.asyncio
    async def test_patch_workflow_draft_demotes_published_status(
        self, session_factory
    ) -> None:
        app = _make_admin_app(session_factory)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            created = await client.post(
                "/api/v1/admin/publications",
                json={**_CREATE_BASE, "review": {**_REVIEW_BASE, "workflow": "published"}},
                headers=_auth_headers(),
            )
            pub_id = created.json()["id"]
            # Trigger a published transition
            pub_resp = await client.post(
                f"/api/v1/admin/publications/{pub_id}/publish",
                headers=_auth_headers(),
            )
            published_at = pub_resp.json()["published_at"]
            assert published_at is not None

            resp = await client.patch(
                f"/api/v1/admin/publications/{pub_id}",
                json={"review": {**_REVIEW_BASE, "workflow": "draft"}},
                headers=_auth_headers(),
            )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["status"] == "DRAFT"
        # published_at preserved for audit
        assert data["published_at"] == published_at

    @pytest.mark.asyncio
    async def test_patch_workflow_transition_emits_audit_event(
        self, session_factory
    ) -> None:
        app = _make_admin_app(session_factory)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            created = await client.post(
                "/api/v1/admin/publications",
                json={**_CREATE_BASE, "review": _REVIEW_BASE},
                headers=_auth_headers(),
            )
            pub_id = created.json()["id"]

            resp = await client.patch(
                f"/api/v1/admin/publications/{pub_id}",
                json={"review": {**_REVIEW_BASE, "workflow": "in_review"}},
                headers=_auth_headers(),
            )
            assert resp.status_code == 200

        async with session_factory() as session:
            rows = (await session.execute(select(AuditEvent))).scalars().all()
            event_types = [r.event_type for r in rows]
            assert EventType.PUBLICATION_WORKFLOW_SUBMITTED.value in event_types
            submitted = next(
                r for r in rows
                if r.event_type == EventType.PUBLICATION_WORKFLOW_SUBMITTED.value
            )
            meta = json.loads(submitted.metadata_json or "{}")
            assert meta["from"] == "draft"
            assert meta["to"] == "in_review"


# ===========================================================================
# Publish / unpublish review sync
# ===========================================================================


class TestPublishUnpublishReviewSync:
    @pytest.mark.asyncio
    async def test_publish_on_row_with_review_sets_workflow_published(
        self, session_factory
    ) -> None:
        app = _make_admin_app(session_factory)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            created = await client.post(
                "/api/v1/admin/publications",
                json={**_CREATE_BASE, "review": _REVIEW_BASE},
                headers=_auth_headers(),
            )
            pub_id = created.json()["id"]

            resp = await client.post(
                f"/api/v1/admin/publications/{pub_id}/publish",
                headers=_auth_headers(),
            )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["status"] == "PUBLISHED"
        assert data["review"]["workflow"] == "published"
        # A system-authored history entry was appended
        actions = [h["action"] for h in data["review"]["history"]]
        assert "published" in actions
        last = data["review"]["history"][-1]
        assert last["author"] == "system"
        # fromWorkflow is captured from the stored review prior to
        # overwrite (Stage 3 PR 4 fix). _REVIEW_BASE ships workflow="draft",
        # so the publish transition reads fromWorkflow="draft".
        assert last["fromWorkflow"] == "draft"
        assert last["toWorkflow"] == "published"

    @pytest.mark.asyncio
    async def test_unpublish_on_row_with_review_sets_workflow_draft(
        self, session_factory
    ) -> None:
        app = _make_admin_app(session_factory)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            created = await client.post(
                "/api/v1/admin/publications",
                json={
                    **_CREATE_BASE,
                    "review": {**_REVIEW_BASE, "workflow": "published"},
                },
                headers=_auth_headers(),
            )
            pub_id = created.json()["id"]
            await client.post(
                f"/api/v1/admin/publications/{pub_id}/publish",
                headers=_auth_headers(),
            )

            resp = await client.post(
                f"/api/v1/admin/publications/{pub_id}/unpublish",
                headers=_auth_headers(),
            )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["status"] == "DRAFT"
        assert data["review"]["workflow"] == "draft"
        last = data["review"]["history"][-1]
        assert last["author"] == "system"
        assert last["toWorkflow"] == "draft"

    @pytest.mark.asyncio
    async def test_publish_on_row_without_review_succeeds_without_sync(
        self, session_factory
    ) -> None:
        app = _make_admin_app(session_factory)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            created = await client.post(
                "/api/v1/admin/publications",
                json=_CREATE_BASE,
                headers=_auth_headers(),
            )
            pub_id = created.json()["id"]

            resp = await client.post(
                f"/api/v1/admin/publications/{pub_id}/publish",
                headers=_auth_headers(),
            )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["status"] == "PUBLISHED"
        # review stayed None (no fabrication by the backend)
        assert data["review"] is None


# ===========================================================================
# Leak prevention — public endpoint must never expose review
# ===========================================================================


class TestReviewLeakPrevention:
    @pytest.mark.asyncio
    async def test_public_graphics_endpoint_never_exposes_review(
        self, session_factory
    ) -> None:
        # Seed a published row carrying a review payload directly.
        async with session_factory() as session:
            repo = PublicationRepository(session)
            pub = await repo.create_full(
                {
                    **_CREATE_BASE,
                    "review": {**_REVIEW_BASE, "workflow": "published"},
                    "s3_key_lowres": "low/key.png",
                    "s3_key_highres": "high/key.png",
                }
            )
            pub.status = PublicationStatus.PUBLISHED
            await session.commit()

        app = _make_public_app(session_factory)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/public/graphics")

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["items"], "expected at least one item"
        for item in body["items"]:
            assert "review" not in item, (
                "review must never leak through the public gallery endpoint"
            )

    @pytest.mark.asyncio
    async def test_admin_get_includes_review_for_admin_consumers(
        self, session_factory
    ) -> None:
        app = _make_admin_app(session_factory)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            created = await client.post(
                "/api/v1/admin/publications",
                json={**_CREATE_BASE, "review": _REVIEW_BASE},
                headers=_auth_headers(),
            )
            pub_id = created.json()["id"]
            resp = await client.get(
                f"/api/v1/admin/publications/{pub_id}",
                headers=_auth_headers(),
            )
        assert resp.status_code == 200
        assert resp.json()["review"]["workflow"] == "draft"


# ===========================================================================
# Auth smoke — PATCH with review requires X-API-KEY
# ===========================================================================


class TestAuth:
    @pytest.mark.asyncio
    async def test_patch_without_api_key_returns_401(
        self, session_factory
    ) -> None:
        app = _make_admin_app(session_factory)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.patch(
                "/api/v1/admin/publications/1",
                json={"review": _REVIEW_BASE},
            )
        assert resp.status_code == 401


# ===========================================================================
# Post-review fixes (Stage 3 PR 4 fix) — fromWorkflow preservation,
# semantic CHANGES_REQUESTED vs RETURNED_TO_DRAFT, unchanged-workflow PATCH,
# malformed review during publish/unpublish.
# ===========================================================================


async def _fetch_audit_events_for(
    session: AsyncSession, entity_id: str
) -> list[AuditEvent]:
    """Return every :class:`AuditEvent` for a publication entity id."""
    stmt = select(AuditEvent).where(AuditEvent.entity_id == entity_id)
    result = await session.execute(stmt)
    return list(result.scalars())


class TestPublishUnpublishSyncPreservesFromWorkflow:
    @pytest.mark.asyncio
    async def test_publish_sync_preserves_previous_workflow_in_history(
        self, session_factory
    ) -> None:
        """Publishing a row with ``review.workflow=approved`` writes a
        system history entry with ``fromWorkflow = "approved"`` (not
        ``None``) — the prior state is captured before overwrite."""
        app = _make_admin_app(session_factory)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            created = await client.post(
                "/api/v1/admin/publications",
                json={
                    **_CREATE_BASE,
                    "review": {
                        "workflow": "approved",
                        "history": [],
                        "comments": [],
                    },
                },
                headers=_auth_headers(),
            )
            assert created.status_code == 201
            pub_id = created.json()["id"]

            pub_resp = await client.post(
                f"/api/v1/admin/publications/{pub_id}/publish",
                headers=_auth_headers(),
            )
            assert pub_resp.status_code == 200

            get_resp = await client.get(
                f"/api/v1/admin/publications/{pub_id}",
                headers=_auth_headers(),
            )

        review = get_resp.json()["review"]
        assert review["workflow"] == "published"
        system_entry = review["history"][-1]
        assert system_entry["author"] == "system"
        assert system_entry["fromWorkflow"] == "approved"
        assert system_entry["toWorkflow"] == "published"

    @pytest.mark.asyncio
    async def test_unpublish_sync_preserves_previous_workflow_in_history(
        self, session_factory
    ) -> None:
        """Unpublishing writes ``fromWorkflow = "published"`` in the
        appended history entry (not ``None``)."""
        app = _make_admin_app(session_factory)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            created = await client.post(
                "/api/v1/admin/publications",
                json={
                    **_CREATE_BASE,
                    "review": {
                        "workflow": "published",
                        "history": [],
                        "comments": [],
                    },
                },
                headers=_auth_headers(),
            )
            pub_id = created.json()["id"]

            await client.post(
                f"/api/v1/admin/publications/{pub_id}/publish",
                headers=_auth_headers(),
            )

            unpub = await client.post(
                f"/api/v1/admin/publications/{pub_id}/unpublish",
                headers=_auth_headers(),
            )
            assert unpub.status_code == 200

            get_resp = await client.get(
                f"/api/v1/admin/publications/{pub_id}",
                headers=_auth_headers(),
            )

        review = get_resp.json()["review"]
        # Find the unpublish (toWorkflow != "published") system entry.
        system_entries = [h for h in review["history"] if h["author"] == "system"]
        last_unpublish = next(
            (e for e in reversed(system_entries) if e["toWorkflow"] != "published"),
            None,
        )
        assert last_unpublish is not None, "expected a system unpublish entry"
        assert last_unpublish["fromWorkflow"] == "published"
        assert last_unpublish["toWorkflow"] == "draft"


class TestPatchWorkflowEventClassification:
    @pytest.mark.asyncio
    async def test_patch_in_review_to_draft_emits_changes_requested(
        self, session_factory
    ) -> None:
        """``in_review → draft`` emits ``CHANGES_REQUESTED`` — distinct
        from other ``* → draft`` transitions."""
        app = _make_admin_app(session_factory)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            created = await client.post(
                "/api/v1/admin/publications",
                json={
                    **_CREATE_BASE,
                    "review": {
                        "workflow": "in_review",
                        "history": [],
                        "comments": [],
                    },
                },
                headers=_auth_headers(),
            )
            pub_id = created.json()["id"]

            resp = await client.patch(
                f"/api/v1/admin/publications/{pub_id}",
                json={
                    "review": {
                        "workflow": "draft",
                        "history": [],
                        "comments": [],
                    }
                },
                headers=_auth_headers(),
            )
            assert resp.status_code == 200

        async with session_factory() as session:
            events = await _fetch_audit_events_for(session, entity_id=str(pub_id))
        workflow_events = [
            e for e in events if e.event_type.startswith("publication.workflow.")
        ]
        assert len(workflow_events) == 1
        assert workflow_events[0].event_type == (
            "publication.workflow.changes_requested"
        )

    @pytest.mark.asyncio
    async def test_patch_approved_to_draft_emits_returned_to_draft(
        self, session_factory
    ) -> None:
        """``approved → draft`` emits ``RETURNED_TO_DRAFT`` — revocation
        of approval, not a reviewer pushback."""
        app = _make_admin_app(session_factory)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            created = await client.post(
                "/api/v1/admin/publications",
                json={
                    **_CREATE_BASE,
                    "review": {
                        "workflow": "approved",
                        "history": [],
                        "comments": [],
                    },
                },
                headers=_auth_headers(),
            )
            pub_id = created.json()["id"]

            resp = await client.patch(
                f"/api/v1/admin/publications/{pub_id}",
                json={
                    "review": {
                        "workflow": "draft",
                        "history": [],
                        "comments": [],
                    }
                },
                headers=_auth_headers(),
            )
            assert resp.status_code == 200

        async with session_factory() as session:
            events = await _fetch_audit_events_for(session, entity_id=str(pub_id))
        workflow_events = [
            e for e in events if e.event_type.startswith("publication.workflow.")
        ]
        assert len(workflow_events) == 1
        assert workflow_events[0].event_type == (
            "publication.workflow.returned_to_draft"
        )

    @pytest.mark.asyncio
    async def test_patch_first_review_assignment_emits_no_workflow_audit(
        self, session_factory
    ) -> None:
        """PATCH that sets ``review`` for the first time
        (``previous_workflow is None``) must NOT emit a workflow-transition
        audit event, regardless of the target state. Initial assignment
        is not a transition — the creation signal is already on
        ``PUBLICATION_GENERATED`` at POST time.
        """
        app = _make_admin_app(session_factory)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Create publication WITHOUT review
            created = await client.post(
                "/api/v1/admin/publications",
                json={**_CREATE_BASE},  # no "review" key
                headers=_auth_headers(),
            )
            assert created.status_code == 201
            pub_id = int(created.json()["id"])

        # Confirm review is NULL in DB
        async with session_factory() as session:
            pub = await session.get(Publication, pub_id)
            assert pub is not None
            assert pub.review is None

        # First write: PATCH review.workflow="draft"
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            patch_resp = await client.patch(
                f"/api/v1/admin/publications/{pub_id}",
                json={
                    "review": {
                        "workflow": "draft",
                        "history": [],
                        "comments": [],
                    }
                },
                headers=_auth_headers(),
            )
            assert patch_resp.status_code == 200

        async with session_factory() as session:
            events = await _fetch_audit_events_for(session, entity_id=str(pub_id))
        workflow_events = [
            e for e in events if e.event_type.startswith("publication.workflow.")
        ]
        assert workflow_events == [], (
            "Expected no workflow transition events on first review write, "
            f"got: {[e.event_type for e in workflow_events]}"
        )

    @pytest.mark.asyncio
    async def test_patch_first_review_to_in_review_emits_no_workflow_audit(
        self, session_factory
    ) -> None:
        """Same first-write guard applies for a non-``draft`` target
        (e.g. PATCH directly into ``in_review`` without a prior draft
        row). Unusual, but must not produce a phantom ``SUBMITTED`` event.
        """
        app = _make_admin_app(session_factory)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            created = await client.post(
                "/api/v1/admin/publications",
                json={**_CREATE_BASE},
                headers=_auth_headers(),
            )
            pub_id = int(created.json()["id"])

            resp = await client.patch(
                f"/api/v1/admin/publications/{pub_id}",
                json={
                    "review": {
                        "workflow": "in_review",
                        "history": [],
                        "comments": [],
                    }
                },
                headers=_auth_headers(),
            )
            assert resp.status_code == 200

        async with session_factory() as session:
            events = await _fetch_audit_events_for(session, entity_id=str(pub_id))
        workflow_events = [
            e for e in events if e.event_type.startswith("publication.workflow.")
        ]
        assert workflow_events == []

    @pytest.mark.asyncio
    async def test_patch_real_transition_still_emits_after_initial_write(
        self, session_factory
    ) -> None:
        """Regression guard: the first-write gate must not silence
        legitimate transitions. After a create-with-review (so
        ``previous_workflow = "draft"`` on the next PATCH), a real
        ``draft → in_review`` transition must emit
        ``PUBLICATION_WORKFLOW_SUBMITTED``.
        """
        app = _make_admin_app(session_factory)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Step 1: create WITH review (no workflow transition audit)
            created = await client.post(
                "/api/v1/admin/publications",
                json={
                    **_CREATE_BASE,
                    "review": {
                        "workflow": "draft",
                        "history": [],
                        "comments": [],
                    },
                },
                headers=_auth_headers(),
            )
            pub_id = int(created.json()["id"])

            # Step 2: legitimate transition draft → in_review
            resp = await client.patch(
                f"/api/v1/admin/publications/{pub_id}",
                json={
                    "review": {
                        "workflow": "in_review",
                        "history": [],
                        "comments": [],
                    }
                },
                headers=_auth_headers(),
            )
            assert resp.status_code == 200

        async with session_factory() as session:
            events = await _fetch_audit_events_for(session, entity_id=str(pub_id))
        workflow_events = [
            e for e in events if e.event_type.startswith("publication.workflow.")
        ]
        assert len(workflow_events) == 1
        assert workflow_events[0].event_type == "publication.workflow.submitted"


class TestPatchSameWorkflowEmitsNoAudit:
    @pytest.mark.asyncio
    async def test_patch_same_workflow_emits_no_workflow_audit(
        self, session_factory
    ) -> None:
        """A PATCH that carries ``review`` but does not change
        ``review.workflow`` must NOT emit a workflow audit event.
        Non-workflow field updates ride through unaffected."""
        app = _make_admin_app(session_factory)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            created = await client.post(
                "/api/v1/admin/publications",
                json={
                    **_CREATE_BASE,
                    "headline": "original",
                    "review": _REVIEW_BASE,
                },
                headers=_auth_headers(),
            )
            pub_id = created.json()["id"]

            resp = await client.patch(
                f"/api/v1/admin/publications/{pub_id}",
                json={
                    "headline": "updated",
                    "review": _REVIEW_BASE,  # workflow == "draft" (unchanged)
                },
                headers=_auth_headers(),
            )
            assert resp.status_code == 200
            assert resp.json()["headline"] == "updated"

        async with session_factory() as session:
            events = await _fetch_audit_events_for(session, entity_id=str(pub_id))
        workflow_events = [
            e for e in events if e.event_type.startswith("publication.workflow.")
        ]
        assert workflow_events == []


class TestMalformedReviewDuringPublishUnpublish:
    @pytest.mark.asyncio
    async def test_publish_with_malformed_review_does_not_crash(
        self, session_factory
    ) -> None:
        """If ``Publication.review`` contains malformed JSON, ``/publish``
        still flips ``status = PUBLISHED``; the review sync is skipped
        with a warning. Corrupt row stays corrupt (no silent rewrite)."""
        app = _make_admin_app(session_factory)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            created = await client.post(
                "/api/v1/admin/publications",
                json={**_CREATE_BASE, "review": _REVIEW_BASE},
                headers=_auth_headers(),
            )
            pub_id = int(created.json()["id"])

        # Corrupt the column directly via the session factory.
        async with session_factory() as session:
            pub = await session.get(Publication, pub_id)
            assert pub is not None
            pub.review = "{not valid json"
            await session.commit()

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            pub_resp = await client.post(
                f"/api/v1/admin/publications/{pub_id}/publish",
                headers=_auth_headers(),
            )
        assert pub_resp.status_code == 200
        assert pub_resp.json()["status"] == "PUBLISHED"

        async with session_factory() as session:
            pub = await session.get(Publication, pub_id)
            assert pub is not None
            assert pub.status == PublicationStatus.PUBLISHED
            # Corrupt content left as-is — sync skipped, not silently repaired.
            assert pub.review == "{not valid json"

    @pytest.mark.asyncio
    async def test_unpublish_with_malformed_review_does_not_crash(
        self, session_factory
    ) -> None:
        """Symmetric to publish: ``/unpublish`` with malformed review
        still flips ``status = DRAFT``; sync is skipped."""
        app = _make_admin_app(session_factory)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            created = await client.post(
                "/api/v1/admin/publications",
                json={
                    **_CREATE_BASE,
                    "review": {**_REVIEW_BASE, "workflow": "published"},
                },
                headers=_auth_headers(),
            )
            pub_id = int(created.json()["id"])

            # Publish first so there's something to unpublish.
            await client.post(
                f"/api/v1/admin/publications/{pub_id}/publish",
                headers=_auth_headers(),
            )

        # Corrupt the column directly.
        async with session_factory() as session:
            pub = await session.get(Publication, pub_id)
            assert pub is not None
            pub.review = "not json either"
            await session.commit()

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            unpub_resp = await client.post(
                f"/api/v1/admin/publications/{pub_id}/unpublish",
                headers=_auth_headers(),
            )
        assert unpub_resp.status_code == 200
        assert unpub_resp.json()["status"] == "DRAFT"

        async with session_factory() as session:
            pub = await session.get(Publication, pub_id)
            assert pub is not None
            assert pub.status == PublicationStatus.DRAFT
            assert pub.review == "not json either"


# ===========================================================================
# Malformed stored review — behavior is defined (parse failure → None)
# ===========================================================================


class TestMalformedReviewOnRead:
    @pytest.mark.asyncio
    async def test_malformed_review_json_surfaces_as_null_review(
        self, session_factory
    ) -> None:
        """Injecting invalid JSON into the column should not 500 the GET.

        The router's ``_serialize`` helper catches parse errors and
        falls through to ``review=None`` (matches the ``visual_config``
        behavior). This test pins that contract.
        """
        async with session_factory() as session:
            repo = PublicationRepository(session)
            pub = await repo.create_full(_CREATE_BASE)
            pub.review = "{not: valid: json"
            session.add(pub)
            await session.commit()
            pub_id = pub.id

        app = _make_admin_app(session_factory)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                f"/api/v1/admin/publications/{pub_id}",
                headers=_auth_headers(),
            )
        assert resp.status_code == 200
        assert resp.json()["review"] is None
