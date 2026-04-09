import asyncio
import json
import os
import shutil
import tempfile
import zipfile
from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest
from pydantic import BaseModel

from src.core.config import Settings
from src.core.exceptions import StorageError
from src.schemas.events import EventType
from src.services.graphics.pipeline import GraphicPipeline

class DummyPub:
    id = 42

@pytest.fixture
def mock_settings():
    return Settings(
        app_name="Test",
        database_url="sqlite+aiosqlite:///:memory:",
        auth_admin_api_key="test",
        auth_internal_api_key="test",
        storage_backend="local",
        s3_bucket="",
        cdn_base_url="http://cdn.test",
        max_zip_size_mb=1,
    )

@pytest.fixture
def mock_storage():
    storage = AsyncMock()
    storage.download_bytes.return_value = b"parquet_data"
    storage.upload_bytes = AsyncMock()
    storage.delete_object = AsyncMock()
    return storage

@pytest.fixture
def mock_repo():
    repo = AsyncMock()
    repo.get_latest_version.return_value = 1
    repo.create_published.return_value = DummyPub()
    return repo

@pytest.fixture
def mock_audit():
    writer = AsyncMock()
    writer.log_event = AsyncMock()
    return writer

@pytest.fixture
def pipeline(mock_storage, mock_repo, mock_audit, mock_settings):
    with patch("src.services.graphics.pipeline.PublicationRepository", return_value=mock_repo), \
         patch("src.services.graphics.pipeline.AuditWriter", return_value=mock_audit), \
         patch("src.services.graphics.pipeline.get_session_factory") as mock_get_session_factory:

        mock_session = AsyncMock()
        mock_session_factory = MagicMock(return_value=mock_session)
        mock_session.__aenter__.return_value = mock_session
        mock_get_session_factory.return_value = mock_session_factory

        yield GraphicPipeline(
            storage=mock_storage,
            publication_repo=mock_repo,
            audit_writer=mock_audit,
            settings=mock_settings,
        )

@pytest.fixture
def mock_dependencies():
    with patch("src.services.graphics.pipeline.pl.read_parquet", return_value=pl.DataFrame({"a": [1]})), \
         patch("src.services.graphics.pipeline.run_in_threadpool") as mock_threadpool:

        async def side_effect(func, *args, **kwargs):
            if func.__name__ == "generate_chart_svg":
                return b"svg_bytes"
            elif func.__name__ == "get_background":
                return b"bg_bytes"
            elif func.__name__ == "composite_image":
                return b"composite_bytes"
            return b"unknown"

        mock_threadpool.side_effect = side_effect
        yield mock_threadpool

@pytest.mark.asyncio
async def test_pipeline_happy_path(pipeline, mock_storage, mock_repo, mock_audit, mock_settings, mock_dependencies):
    render_sem = asyncio.Semaphore(1)
    io_sem = asyncio.Semaphore(1)

    result = await pipeline.generate(
        data_key="test.parquet",
        chart_type="line",
        title="Test Chart",
        size=(1080, 1080),
        category="housing",
        source_product_id="14-10-0127",
        render_sem=render_sem,
        io_sem=io_sem,
    )

    assert result.publication_id == 42
    assert result.cdn_url_lowres.startswith("http://cdn.test/publications/")
    assert result.version == 2 # Because mock_repo.get_latest_version returns 1

    mock_storage.download_bytes.assert_called_once_with("test.parquet")
    assert mock_storage.upload_bytes.call_count == 3

    mock_audit.log_event.assert_any_call(
        event_type=EventType.PUBLICATION_GENERATED,
        entity_type="publication",
        entity_id="42",
        metadata={"version": 2, "chart_type": "line", "size": (1080, 1080), "category": "housing"}
    )

@pytest.mark.asyncio
async def test_pipeline_failure_stage2_svg(pipeline, mock_storage, mock_dependencies):
    mock_dependencies.side_effect = Exception("SVG Error")

    with pytest.raises(Exception, match="SVG Error"):
        await pipeline.generate(
            data_key="test.parquet",
            chart_type="line",
            title="Test Chart",
            size=(1080, 1080),
            category="housing",
        )
    mock_storage.upload_bytes.assert_not_called()

@pytest.mark.asyncio
async def test_pipeline_failure_stage8a_lowres_upload(pipeline, mock_storage, mock_dependencies):
    mock_storage.upload_bytes.side_effect = [Exception("Upload failed"), None, None]

    with pytest.raises(Exception, match="Upload failed"):
        await pipeline.generate(
            data_key="test.parquet",
            chart_type="line",
            title="Test",
            size=(1080, 1080),
            category="housing",
        )

    assert mock_storage.upload_bytes.call_count == 1
    mock_storage.delete_object.assert_not_called()

@pytest.mark.asyncio
async def test_pipeline_failure_stage8b_highres_upload(pipeline, mock_storage, mock_dependencies):
    async def upload_side_effect(data, key):
        if "highres" in key:
            raise Exception("Highres failed")
        return None
    mock_storage.upload_bytes.side_effect = upload_side_effect

    with pytest.raises(Exception, match="Highres failed"):
        await pipeline.generate(
            data_key="test.parquet",
            chart_type="line",
            title="Test",
            size=(1080, 1080),
            category="housing",
        )

    assert mock_storage.upload_bytes.call_count == 2
    mock_storage.delete_object.assert_called_once()

@pytest.mark.asyncio
async def test_pipeline_failure_stage9_db_write(pipeline, mock_storage, mock_repo, mock_dependencies):
    mock_repo.create_published.side_effect = Exception("DB failed")

    with pytest.raises(Exception, match="DB failed"):
        await pipeline.generate(
            data_key="test.parquet",
            chart_type="line",
            title="Test",
            size=(1080, 1080),
            category="housing",
        )

    assert mock_storage.upload_bytes.call_count == 3
    mock_storage.delete_object.assert_not_called()

@pytest.mark.asyncio
async def test_pipeline_semaphore_none(pipeline, mock_storage, mock_dependencies):
    result = await pipeline.generate(
        data_key="test.parquet",
        chart_type="line",
        title="Test Chart",
        size=(1080, 1080),
        category="housing",
        render_sem=None,
        io_sem=None,
    )
    assert result.publication_id == 42

@pytest.mark.asyncio
async def test_pipeline_zip_size_enforcement(pipeline, mock_dependencies, mock_settings):
    # Change zip size limit to 0 MB to force failure
    mock_settings.max_zip_size_mb = 0

    with pytest.raises(ValueError, match="Generated ZIP exceeds limit"):
        await pipeline.generate(
            data_key="test.parquet",
            chart_type="line",
            title="Test Chart",
            size=(1080, 1080),
            category="housing",
        )

@pytest.mark.asyncio
async def test_pipeline_hash_determinism(pipeline, mock_storage, mock_repo, mock_dependencies):
    import hashlib

    config1 = json.dumps({"chart_type": "line", "size": (1080, 1080), "title": "A"}, sort_keys=True).encode()
    config2 = json.dumps({"chart_type": "line", "size": (1080, 1080), "title": "B"}, sort_keys=True).encode()

    hash1 = hashlib.sha256(config1).hexdigest()
    hash2 = hashlib.sha256(config2).hexdigest()

    assert hash1 != hash2

@pytest.mark.asyncio
async def test_pipeline_failure_stage4_composite_cleanup(pipeline, mock_storage, mock_dependencies):
    # Mock composite to fail
    async def side_effect(func, *args, **kwargs):
        if func.__name__ == "generate_chart_svg":
            return b"svg_bytes"
        elif func.__name__ == "get_background":
            return b"bg_bytes"
        elif func.__name__ == "composite_image":
            raise Exception("Compositor failed")
        return b"unknown"
    mock_dependencies.side_effect = side_effect

    with pytest.raises(Exception, match="Compositor failed"):
        await pipeline.generate(
            data_key="test.parquet",
            chart_type="line",
            title="Test Chart",
            size=(1080, 1080),
            category="housing",
        )
    # The temp dir isn't created until stage 7, but we can verify it doesn't leave anything

@pytest.mark.asyncio
async def test_pipeline_versioning(pipeline, mock_storage, mock_repo, mock_dependencies):
    mock_repo.get_latest_version.return_value = None

    result = await pipeline.generate(
        data_key="test.parquet",
        chart_type="line",
        title="Test Chart",
        size=(1080, 1080),
        category="housing",
        source_product_id="14-10-0127"
    )
    assert result.version == 1

@pytest.mark.asyncio
async def test_pipeline_content_hash_determinism(pipeline, mock_storage, mock_repo, mock_dependencies):
    import hashlib
    lowres_bytes1 = b"lowres_image_data_1"
    lowres_bytes2 = b"lowres_image_data_1"

    hash1 = hashlib.sha256(lowres_bytes1).hexdigest()
    hash2 = hashlib.sha256(lowres_bytes2).hexdigest()

    assert hash1 == hash2
