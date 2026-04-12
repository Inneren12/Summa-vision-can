"""Tests for the graphics_generate job handler.

Covers:
* Handler calls GraphicPipeline.generate with correct arguments
* Handler returns GenerationResult.model_dump()
* Handler uses DI for dependencies (ARCH-DPEN-001)
* Handler passes semaphores from app_state
* Handler works when app_state has no storage attribute
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

import pytest

from src.schemas.graphics import GenerationResult
from src.schemas.job_payloads import GraphicsGeneratePayload
from src.services.jobs.handlers import handle_graphics_generate


def _make_generation_result(
    publication_id: int = 42,
    cdn_url_lowres: str = "http://cdn.test/pub/42/v1/abc_lowres.png",
    s3_key_highres: str = "publications/42/v1/abc_highres.png",
    version: int = 1,
) -> GenerationResult:
    return GenerationResult(
        publication_id=publication_id,
        cdn_url_lowres=cdn_url_lowres,
        s3_key_highres=s3_key_highres,
        version=version,
    )


def _make_app_state(
    *,
    storage: object | None = None,
    render_sem: asyncio.Semaphore | None = None,
    io_sem: asyncio.Semaphore | None = None,
) -> SimpleNamespace:
    ns = SimpleNamespace()
    if storage is not None:
        ns.storage = storage
    ns.render_sem = render_sem or asyncio.Semaphore(2)
    ns.io_sem = io_sem or asyncio.Semaphore(10)
    return ns


@pytest.mark.asyncio()
async def test_handler_calls_pipeline_generate_with_correct_args() -> None:
    """Handler must instantiate GraphicPipeline and call generate()."""
    payload = GraphicsGeneratePayload(
        data_key="data/test.parquet",
        chart_type="bar",
        title="Test Chart",
        size=(1080, 1080),
        category="housing",
        source_product_id="14-10-0127",
    )
    app_state = _make_app_state()

    mock_result = _make_generation_result()
    mock_pipeline_instance = AsyncMock()
    mock_pipeline_instance.generate.return_value = mock_result

    with (
        patch("src.core.database.get_session_factory", return_value=MagicMock()),
        patch("src.core.storage.get_storage_manager", return_value=MagicMock()),
        patch("src.core.config.get_settings", return_value=MagicMock()),
        patch(
            "src.services.graphics.pipeline.GraphicPipeline",
            return_value=mock_pipeline_instance,
        ),
    ):
        result = await handle_graphics_generate(payload, app_state=app_state)

    mock_pipeline_instance.generate.assert_called_once_with(
        data_key="data/test.parquet",
        chart_type="bar",
        title="Test Chart",
        size=(1080, 1080),
        category="housing",
        source_product_id="14-10-0127",
        render_sem=app_state.render_sem,
        io_sem=app_state.io_sem,
    )

    assert result == mock_result.model_dump()


@pytest.mark.asyncio()
async def test_handler_returns_model_dump() -> None:
    """Handler should return GenerationResult.model_dump() as dict."""
    payload = GraphicsGeneratePayload(
        data_key="data/test.parquet",
        chart_type="line",
        title="Test",
        category="housing",
    )
    app_state = _make_app_state()

    mock_result = _make_generation_result(publication_id=99, version=3)
    mock_pipeline = AsyncMock()
    mock_pipeline.generate.return_value = mock_result

    with (
        patch("src.core.database.get_session_factory", return_value=MagicMock()),
        patch("src.core.storage.get_storage_manager", return_value=MagicMock()),
        patch("src.core.config.get_settings", return_value=MagicMock()),
        patch("src.services.graphics.pipeline.GraphicPipeline", return_value=mock_pipeline),
    ):
        result = await handle_graphics_generate(payload, app_state=app_state)

    assert isinstance(result, dict)
    assert result["publication_id"] == 99
    assert result["version"] == 3
    assert "cdn_url_lowres" in result
    assert "s3_key_highres" in result


@pytest.mark.asyncio()
async def test_handler_uses_storage_from_app_state_when_available() -> None:
    """When app_state.storage exists, use it instead of get_storage_manager()."""
    payload = GraphicsGeneratePayload(
        data_key="data/test.parquet",
        chart_type="bar",
        title="Test",
        category="housing",
    )
    mock_storage = MagicMock()
    app_state = _make_app_state(storage=mock_storage)

    mock_result = _make_generation_result()
    mock_pipeline_cls = MagicMock()
    mock_pipeline_instance = AsyncMock()
    mock_pipeline_instance.generate.return_value = mock_result
    mock_pipeline_cls.return_value = mock_pipeline_instance

    with (
        patch("src.core.database.get_session_factory", return_value=MagicMock()),
        patch("src.core.storage.get_storage_manager") as mock_get_storage,
        patch("src.core.config.get_settings", return_value=MagicMock()),
        patch("src.services.graphics.pipeline.GraphicPipeline", mock_pipeline_cls),
    ):
        await handle_graphics_generate(payload, app_state=app_state)

    # get_storage_manager should NOT have been called
    mock_get_storage.assert_not_called()

    # Pipeline should have been constructed with app_state.storage
    call_kwargs = mock_pipeline_cls.call_args[1]
    assert call_kwargs["storage"] is mock_storage


@pytest.mark.asyncio()
async def test_handler_falls_back_to_get_storage_manager() -> None:
    """When app_state has no storage, fall back to get_storage_manager()."""
    payload = GraphicsGeneratePayload(
        data_key="data/test.parquet",
        chart_type="bar",
        title="Test",
        category="housing",
    )
    app_state = SimpleNamespace(render_sem=asyncio.Semaphore(2), io_sem=asyncio.Semaphore(10))

    fallback_storage = MagicMock()
    mock_result = _make_generation_result()
    mock_pipeline_cls = MagicMock()
    mock_pipeline_instance = AsyncMock()
    mock_pipeline_instance.generate.return_value = mock_result
    mock_pipeline_cls.return_value = mock_pipeline_instance

    with (
        patch("src.core.database.get_session_factory", return_value=MagicMock()),
        patch("src.core.storage.get_storage_manager", return_value=fallback_storage),
        patch("src.core.config.get_settings", return_value=MagicMock()),
        patch("src.services.graphics.pipeline.GraphicPipeline", mock_pipeline_cls),
    ):
        await handle_graphics_generate(payload, app_state=app_state)

    call_kwargs = mock_pipeline_cls.call_args[1]
    assert call_kwargs["storage"] is fallback_storage


@pytest.mark.asyncio()
async def test_handler_passes_none_semaphores_when_missing() -> None:
    """When app_state has no semaphores, None is passed to pipeline."""
    payload = GraphicsGeneratePayload(
        data_key="data/test.parquet",
        chart_type="bar",
        title="Test",
        category="housing",
    )
    app_state = SimpleNamespace()  # no render_sem, no io_sem

    mock_result = _make_generation_result()
    mock_pipeline = AsyncMock()
    mock_pipeline.generate.return_value = mock_result

    with (
        patch("src.core.database.get_session_factory", return_value=MagicMock()),
        patch("src.core.storage.get_storage_manager", return_value=MagicMock()),
        patch("src.core.config.get_settings", return_value=MagicMock()),
        patch("src.services.graphics.pipeline.GraphicPipeline", return_value=mock_pipeline),
    ):
        await handle_graphics_generate(payload, app_state=app_state)

    call_kwargs = mock_pipeline.generate.call_args[1]
    assert call_kwargs["render_sem"] is None
    assert call_kwargs["io_sem"] is None


@pytest.mark.asyncio()
async def test_handler_propagates_pipeline_exception() -> None:
    """If pipeline.generate() raises, the handler must not swallow it."""
    payload = GraphicsGeneratePayload(
        data_key="data/test.parquet",
        chart_type="bar",
        title="Test",
        category="housing",
    )
    app_state = _make_app_state()

    mock_pipeline = AsyncMock()
    mock_pipeline.generate.side_effect = RuntimeError("Storage unavailable")

    with (
        patch("src.core.database.get_session_factory", return_value=MagicMock()),
        patch("src.core.storage.get_storage_manager", return_value=MagicMock()),
        patch("src.core.config.get_settings", return_value=MagicMock()),
        patch("src.services.graphics.pipeline.GraphicPipeline", return_value=mock_pipeline),
    ):
        with pytest.raises(RuntimeError, match="Storage unavailable"):
            await handle_graphics_generate(payload, app_state=app_state)


@pytest.mark.asyncio()
async def test_handler_registered_in_handler_registry() -> None:
    """graphics_generate must be present in HANDLER_REGISTRY."""
    from src.services.jobs.handlers import HANDLER_REGISTRY

    assert "graphics_generate" in HANDLER_REGISTRY
    assert HANDLER_REGISTRY["graphics_generate"] is handle_graphics_generate
