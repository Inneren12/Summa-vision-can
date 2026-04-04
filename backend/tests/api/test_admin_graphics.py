"""Tests for admin graphics endpoints and generation pipeline.

Covers:
* ``GET  /api/v1/admin/queue``
* ``POST /api/v1/admin/graphics/generate``
* ``_run_generation_pipeline`` (integration-style, all externals mocked)
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.api.routers.admin_graphics import (
    SIZE_PRESETS,
    _get_repo,
    _get_storage,
    _run_generation_pipeline,
    router,
)
from src.core.task_manager import TaskManager, get_task_manager
from src.models.publication import Publication, PublicationStatus


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_app(
    repo_override: object | None = None,
    storage_override: object | None = None,
    tm_override: object | None = None,
) -> FastAPI:
    """Create a minimal test FastAPI app with dependency overrides."""
    app = FastAPI()
    app.include_router(router)

    if repo_override is not None:
        app.dependency_overrides[_get_repo] = lambda: repo_override
    if storage_override is not None:
        app.dependency_overrides[_get_storage] = lambda: storage_override
    if tm_override is not None:
        app.dependency_overrides[get_task_manager] = lambda: tm_override

    return app


def _make_publication(
    *,
    pub_id: int = 1,
    headline: str = "Test Headline",
    chart_type: str = "BAR",
    virality_score: float = 7.5,
    status: PublicationStatus = PublicationStatus.DRAFT,
) -> Publication:
    """Create a mock Publication instance."""
    pub = MagicMock(spec=Publication)
    pub.id = pub_id
    pub.headline = headline
    pub.chart_type = chart_type
    pub.virality_score = virality_score
    pub.status = status
    pub.created_at = datetime(2026, 3, 15, 12, 0, 0, tzinfo=timezone.utc)
    pub.s3_key_lowres = None
    pub.s3_key_highres = None
    return pub


@pytest.fixture()
def mock_repo() -> AsyncMock:
    """Return a mocked PublicationRepository."""
    repo = AsyncMock()
    return repo


@pytest.fixture()
def mock_storage() -> AsyncMock:
    """Return a mocked StorageInterface."""
    storage = AsyncMock()
    return storage


@pytest.fixture()
def mock_task_manager() -> MagicMock:
    """Return a mocked TaskManager.

    The ``submit_task`` mock uses a *side_effect* that closes the received
    coroutine so that no ``RuntimeWarning: coroutine was never awaited``
    is emitted during garbage collection.
    """
    tm = MagicMock(spec=TaskManager)

    def _close_and_return(coro: object) -> str:  # noqa: ANN001
        import asyncio

        if asyncio.iscoroutine(coro):
            coro.close()
        return "test-task-uuid"

    tm.submit_task.side_effect = _close_and_return
    return tm


# ---------------------------------------------------------------------------
# GET /api/v1/admin/queue
# ---------------------------------------------------------------------------


class TestGetQueue:
    """Tests for the GET /api/v1/admin/queue endpoint."""

    @pytest.mark.asyncio()
    async def test_get_queue_returns_draft_publications(
        self, mock_repo: AsyncMock
    ) -> None:
        """Two DRAFT publications should be returned as a list of 2 items."""
        pub1 = _make_publication(pub_id=1, virality_score=8.0)
        pub2 = _make_publication(pub_id=2, virality_score=6.0)
        mock_repo.get_drafts.return_value = [pub1, pub2]

        app = _make_app(repo_override=mock_repo)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/admin/queue")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["id"] == 1
        assert data[1]["id"] == 2

    @pytest.mark.asyncio()
    async def test_get_queue_empty_returns_empty_list(
        self, mock_repo: AsyncMock
    ) -> None:
        """An empty draft list should return HTTP 200 with ``[]``."""
        mock_repo.get_drafts.return_value = []

        app = _make_app(repo_override=mock_repo)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/admin/queue")

        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio()
    async def test_get_queue_respects_limit_param(
        self, mock_repo: AsyncMock
    ) -> None:
        """The ``limit`` query param should be forwarded to ``get_drafts``."""
        mock_repo.get_drafts.return_value = []

        app = _make_app(repo_override=mock_repo)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.get("/api/v1/admin/queue?limit=5")

        mock_repo.get_drafts.assert_called_once_with(limit=5)

    @pytest.mark.asyncio()
    async def test_get_queue_response_schema(
        self, mock_repo: AsyncMock
    ) -> None:
        """Response items must contain the expected keys."""
        pub = _make_publication()
        mock_repo.get_drafts.return_value = [pub]

        app = _make_app(repo_override=mock_repo)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/admin/queue")

        item = resp.json()[0]
        expected_keys = {"id", "headline", "chart_type", "virality_score", "status", "created_at"}
        assert expected_keys == set(item.keys())

    @pytest.mark.asyncio()
    async def test_get_queue_default_limit(
        self, mock_repo: AsyncMock
    ) -> None:
        """Without an explicit limit, the default (20) should be used."""
        mock_repo.get_drafts.return_value = []

        app = _make_app(repo_override=mock_repo)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.get("/api/v1/admin/queue")

        mock_repo.get_drafts.assert_called_once_with(limit=20)


# ---------------------------------------------------------------------------
# POST /api/v1/admin/graphics/generate
# ---------------------------------------------------------------------------


class TestGenerateGraphic:
    """Tests for the POST /api/v1/admin/graphics/generate endpoint."""

    @pytest.mark.asyncio()
    async def test_generate_returns_202_with_task_id(
        self,
        mock_repo: AsyncMock,
        mock_storage: AsyncMock,
        mock_task_manager: MagicMock,
    ) -> None:
        """A valid DRAFT publication should return 202 with a task_id."""
        mock_repo.get_by_id.return_value = _make_publication()

        app = _make_app(
            repo_override=mock_repo,
            storage_override=mock_storage,
            tm_override=mock_task_manager,
        )
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/admin/graphics/generate",
                json={"brief_id": 1},
            )

        assert resp.status_code == 202
        data = resp.json()
        assert "task_id" in data
        assert isinstance(data["task_id"], str)
        assert data["task_id"] == "test-task-uuid"
        assert data["message"] == "Generation started"

    @pytest.mark.asyncio()
    async def test_generate_404_if_publication_not_found(
        self,
        mock_repo: AsyncMock,
        mock_storage: AsyncMock,
        mock_task_manager: MagicMock,
    ) -> None:
        """When ``get_by_id`` returns None, the response should be 404."""
        mock_repo.get_by_id.return_value = None

        app = _make_app(
            repo_override=mock_repo,
            storage_override=mock_storage,
            tm_override=mock_task_manager,
        )
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/admin/graphics/generate",
                json={"brief_id": 999},
            )

        assert resp.status_code == 404

    @pytest.mark.asyncio()
    async def test_generate_409_if_not_draft(
        self,
        mock_repo: AsyncMock,
        mock_storage: AsyncMock,
        mock_task_manager: MagicMock,
    ) -> None:
        """A PUBLISHED publication should result in 409 Conflict."""
        mock_repo.get_by_id.return_value = _make_publication(
            status=PublicationStatus.PUBLISHED,
        )

        app = _make_app(
            repo_override=mock_repo,
            storage_override=mock_storage,
            tm_override=mock_task_manager,
        )
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/admin/graphics/generate",
                json={"brief_id": 1},
            )

        assert resp.status_code == 409
        assert "not in DRAFT status" in resp.json()["detail"]

    @pytest.mark.asyncio()
    async def test_generate_does_not_block_response(
        self,
        mock_repo: AsyncMock,
        mock_storage: AsyncMock,
        mock_task_manager: MagicMock,
    ) -> None:
        """``submit_task`` should be called (not awaited), and return immediately."""
        mock_repo.get_by_id.return_value = _make_publication()

        app = _make_app(
            repo_override=mock_repo,
            storage_override=mock_storage,
            tm_override=mock_task_manager,
        )
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/admin/graphics/generate",
                json={"brief_id": 1},
            )

        assert resp.status_code == 202
        # submit_task was called exactly once with a coroutine
        mock_task_manager.submit_task.assert_called_once()
        coro_arg = mock_task_manager.submit_task.call_args[0][0]
        # The argument should be a coroutine (fixture closes it automatically)
        import asyncio

        assert asyncio.iscoroutine(coro_arg)

    @pytest.mark.asyncio()
    async def test_generate_size_preset_mapping(
        self,
        mock_repo: AsyncMock,
        mock_storage: AsyncMock,
        mock_task_manager: MagicMock,
    ) -> None:
        """Requesting ``size_preset=twitter`` should pass SIZE_TWITTER to the pipeline."""
        mock_repo.get_by_id.return_value = _make_publication()

        app = _make_app(
            repo_override=mock_repo,
            storage_override=mock_storage,
            tm_override=mock_task_manager,
        )
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/admin/graphics/generate",
                json={"brief_id": 1, "size_preset": "twitter"},
            )

        assert resp.status_code == 202
        # The coroutine was submitted; spot-check that SIZE_PRESETS maps correctly
        assert SIZE_PRESETS["twitter"] == (1200, 628)

    @pytest.mark.asyncio()
    async def test_generate_default_values(
        self,
        mock_repo: AsyncMock,
        mock_storage: AsyncMock,
        mock_task_manager: MagicMock,
    ) -> None:
        """Defaults: size_preset=instagram, dpi=150, watermark=True."""
        mock_repo.get_by_id.return_value = _make_publication()

        app = _make_app(
            repo_override=mock_repo,
            storage_override=mock_storage,
            tm_override=mock_task_manager,
        )
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/admin/graphics/generate",
                json={"brief_id": 1},
            )

        assert resp.status_code == 202


# ---------------------------------------------------------------------------
# _run_generation_pipeline (integration test)
# ---------------------------------------------------------------------------


class TestGenerationPipeline:
    """Tests for the private ``_run_generation_pipeline`` function."""

    @pytest.mark.asyncio()
    async def test_pipeline_updates_publication_to_published(self) -> None:
        """After successful execution, the publication should be PUBLISHED with S3 keys."""
        pub = _make_publication(pub_id=42)

        mock_repo = AsyncMock()
        mock_storage = AsyncMock()
        mock_session = AsyncMock()

        # Fake PNG bytes (1x1 transparent pixel)
        fake_png = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
            b"\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
            b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01"
            b"\r\n\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
        )

        with (
            patch(
                "src.api.routers.admin_graphics.generate_chart_svg",
                return_value=b"<svg></svg>",
            ),
            patch(
                "src.api.routers.admin_graphics.AIImageClient"
            ) as mock_ai_cls,
            patch(
                "src.api.routers.admin_graphics.composite_image",
                return_value=fake_png,
            ),
        ):
            mock_ai_instance = AsyncMock()
            mock_ai_instance.generate_background.return_value = fake_png
            mock_ai_cls.return_value = mock_ai_instance

            result = await _run_generation_pipeline(
                publication=pub,
                size=(1080, 1080),
                dpi=150,
                watermark=True,
                pub_repo=mock_repo,
                storage=mock_storage,
                session=mock_session,
            )

        # Assert status updated to PUBLISHED
        mock_repo.update_status.assert_called_once_with(
            42, PublicationStatus.PUBLISHED
        )

        # Assert S3 keys saved
        mock_repo.update_s3_keys.assert_called_once_with(
            42,
            s3_key_lowres="graphics/42/lowres.png",
            s3_key_highres="graphics/42/highres.png",
        )

        # Assert upload called for both keys
        assert mock_storage.upload_raw.call_count == 2

        # Assert session committed
        mock_session.commit.assert_called_once()

        # Assert return value
        assert result == {
            "s3_key_lowres": "graphics/42/lowres.png",
            "s3_key_highres": "graphics/42/highres.png",
        }

    @pytest.mark.asyncio()
    async def test_pipeline_logs_and_reraises_on_failure(self) -> None:
        """If any step fails, the exception should be logged and re-raised."""
        pub = _make_publication(pub_id=7)

        mock_repo = AsyncMock()
        mock_storage = AsyncMock()
        mock_session = AsyncMock()

        with patch(
            "src.api.routers.admin_graphics.generate_chart_svg",
            side_effect=RuntimeError("SVG generation exploded"),
        ):
            with pytest.raises(RuntimeError, match="SVG generation exploded"):
                await _run_generation_pipeline(
                    publication=pub,
                    size=(1080, 1080),
                    dpi=150,
                    watermark=True,
                    pub_repo=mock_repo,
                    storage=mock_storage,
                    session=mock_session,
                )

        # Status should NOT have been updated (pipeline failed before that step)
        mock_repo.update_status.assert_not_called()

    @pytest.mark.asyncio()
    async def test_pipeline_calls_composite_in_thread(self) -> None:
        """``composite_image`` (sync) should be called via ``asyncio.to_thread``."""
        pub = _make_publication(pub_id=1)

        mock_repo = AsyncMock()
        mock_storage = AsyncMock()
        mock_session = AsyncMock()

        fake_png = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
            b"\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
            b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01"
            b"\r\n\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
        )

        with (
            patch(
                "src.api.routers.admin_graphics.generate_chart_svg",
                return_value=b"<svg></svg>",
            ),
            patch(
                "src.api.routers.admin_graphics.AIImageClient"
            ) as mock_ai_cls,
            patch(
                "src.api.routers.admin_graphics.composite_image",
                return_value=fake_png,
            ) as mock_composite,
            patch(
                "src.api.routers.admin_graphics.asyncio.to_thread",
                new_callable=AsyncMock,
                return_value=fake_png,
            ) as mock_to_thread,
        ):
            mock_ai_instance = AsyncMock()
            mock_ai_instance.generate_background.return_value = fake_png
            mock_ai_cls.return_value = mock_ai_instance

            await _run_generation_pipeline(
                publication=pub,
                size=(1080, 1080),
                dpi=150,
                watermark=True,
                pub_repo=mock_repo,
                storage=mock_storage,
                session=mock_session,
            )

        # composite_image should have been called via asyncio.to_thread
        mock_to_thread.assert_called_once_with(
            mock_composite,
            fake_png,
            b"<svg></svg>",
            dpi=150,
            watermark=True,
        )

    @pytest.mark.asyncio()
    async def test_pipeline_uses_correct_chart_type(self) -> None:
        """The pipeline should parse ``publication.chart_type`` into ``ChartType``."""
        pub = _make_publication(chart_type="LINE")

        mock_repo = AsyncMock()
        mock_storage = AsyncMock()
        mock_session = AsyncMock()

        fake_png = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
            b"\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
            b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01"
            b"\r\n\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
        )

        from src.services.ai.schemas import ChartType

        with (
            patch(
                "src.api.routers.admin_graphics.generate_chart_svg",
                return_value=b"<svg></svg>",
            ) as mock_gen_svg,
            patch(
                "src.api.routers.admin_graphics.AIImageClient"
            ) as mock_ai_cls,
            patch(
                "src.api.routers.admin_graphics.composite_image",
                return_value=fake_png,
            ),
        ):
            mock_ai_instance = AsyncMock()
            mock_ai_instance.generate_background.return_value = fake_png
            mock_ai_cls.return_value = mock_ai_instance

            await _run_generation_pipeline(
                publication=pub,
                size=(1200, 628),
                dpi=150,
                watermark=True,
                pub_repo=mock_repo,
                storage=mock_storage,
                session=mock_session,
            )

        # Should have called generate_chart_svg with ChartType.LINE
        call_args = mock_gen_svg.call_args
        assert call_args[0][1] == ChartType.LINE
        assert call_args[1]["size"] == (1200, 628)


# ---------------------------------------------------------------------------
# Size presets mapping
# ---------------------------------------------------------------------------


class TestSizePresets:
    """Ensure SIZE_PRESETS map to the correct constants."""

    def test_instagram_size(self) -> None:
        assert SIZE_PRESETS["instagram"] == (1080, 1080)

    def test_twitter_size(self) -> None:
        assert SIZE_PRESETS["twitter"] == (1200, 628)

    def test_reddit_size(self) -> None:
        assert SIZE_PRESETS["reddit"] == (1200, 900)
