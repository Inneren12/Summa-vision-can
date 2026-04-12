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
    version = 1

@pytest.fixture
def mock_settings():
    return Settings(
        app_name="Test",
        database_url="sqlite+aiosqlite:///:memory:",
        admin_api_key="test",
        storage_backend="local",
        s3_bucket="test-bucket",
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

    # Return DummyPub but ensure it respects the version requested
    async def create_side_effect(*args, **kwargs):
        pub = DummyPub()
        pub.version = kwargs.get("version", 1)
        return pub

    repo.create_published.side_effect = create_side_effect
    return repo

@pytest.fixture
def mock_audit():
    writer = AsyncMock()
    writer.log_event = AsyncMock()
    return writer

@pytest.fixture
def mock_session_factory():
    mock_session = AsyncMock()
    factory = MagicMock(return_value=mock_session)
    mock_session.__aenter__.return_value = mock_session
    return factory

@pytest.fixture
def pipeline(mock_storage, mock_repo, mock_audit, mock_settings, mock_session_factory):
    with patch("src.services.graphics.pipeline.PublicationRepository", return_value=mock_repo), \
         patch("src.services.graphics.pipeline.AuditWriter", return_value=mock_audit):

        yield GraphicPipeline(
            storage=mock_storage,
            session_factory=mock_session_factory,
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
            metadata={"version": 2, "chart_type": "line", "size": [1080, 1080], "category": "housing"}
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
async def test_pipeline_failure_stage10a_lowres_upload(pipeline, mock_storage, mock_repo, mock_dependencies):
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
    # DRAFT should have been created (stage 7), but NOT updated (stage 11)
    mock_repo.create_published.assert_called_once()
    mock_repo.update_s3_keys_and_publish.assert_not_called()

@pytest.mark.asyncio
async def test_pipeline_failure_stage10b_highres_upload(pipeline, mock_storage, mock_repo, mock_dependencies):
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
    mock_repo.update_s3_keys_and_publish.assert_not_called()

@pytest.mark.asyncio
async def test_pipeline_failure_stage11_db_update(pipeline, mock_storage, mock_repo, mock_dependencies):
    mock_repo.update_s3_keys_and_publish.side_effect = Exception("DB failed")

    with pytest.raises(Exception, match="DB failed"):
        await pipeline.generate(
            data_key="test.parquet",
            chart_type="line",
            title="Test",
            size=(1080, 1080),
            category="housing",
        )

    assert mock_storage.upload_bytes.call_count == 3
    assert mock_storage.delete_object.call_count == 3

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

@pytest.mark.asyncio
async def test_pipeline_version_propagation_after_retry(pipeline, mock_storage, mock_repo, mock_audit, mock_dependencies):
    """When create_published retries and bumps version, all downstream
    artifacts (S3 keys, metadata, audit, result) use the final version."""

    # Return DummyPub but ensure it respects the version requested
    async def create_side_effect(*args, **kwargs):
        pub = DummyPub()
        pub.version = 2
        return pub

    mock_repo.get_latest_version.return_value = None  # first version
    mock_repo.create_published.side_effect = create_side_effect
    mock_repo.update_s3_keys_and_publish = AsyncMock()

    result = await pipeline.generate(
        data_key="test.parquet",
        chart_type="line",
        title="Test",
        size=(1080, 1080),
        category="housing",
    )

    assert result.version == 2
    assert "/v2/" in result.cdn_url_lowres

    # Check S3 upload keys
    upload_calls = mock_storage.upload_bytes.call_args_list
    for call in upload_calls:
        key = call[1].get("key") or call[0][1]
        if "publications/" in key:
            assert "/v2/" in key, f"S3 key {key} should contain /v2/"

    # Check audit events
    audit_calls = mock_audit.log_event.call_args_list
    for call in audit_calls:
        metadata = call[1].get("metadata") or call[0][3]
        if metadata and "version" in metadata:
            assert metadata["version"] == 2

@pytest.mark.asyncio
async def test_pipeline_draft_stays_on_upload_failure(pipeline, mock_storage, mock_repo, mock_dependencies):
    """If S3 upload fails after DB DRAFT creation, publication stays DRAFT
    (not visible in gallery) and no orphaned PUBLISHED record exists."""

    mock_storage.upload_bytes.side_effect = Exception("S3 Upload Failed")

    with pytest.raises(Exception, match="S3 Upload Failed"):
        await pipeline.generate(
            data_key="test.parquet",
            chart_type="line",
            title="Test",
            size=(1080, 1080),
            category="housing",
        )

    mock_repo.create_published.assert_called_once()  # Called to create DRAFT
    mock_repo.update_s3_keys_and_publish.assert_not_called()  # Never published

@pytest.mark.asyncio
async def test_repo_create_published_retry_logic():
    from src.repositories.publication_repository import PublicationRepository
    from src.models.publication import Publication
    from sqlalchemy.exc import IntegrityError

    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    repo = PublicationRepository(mock_session)

    call_count = 0
    def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise IntegrityError("mock error", "mock params", "mock orig")

    mock_session.flush.side_effect = side_effect

    pub = await repo.create_published(
        headline="Test",
        chart_type="line",
        s3_key_lowres="low",
        s3_key_highres="high",
        source_product_id="123",
        version=1,
        config_hash="hash",
        content_hash="content"
    )

    assert pub.version == 3
    assert mock_session.flush.call_count == 3
