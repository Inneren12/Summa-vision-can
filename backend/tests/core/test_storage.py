"""Unit tests for the storage abstraction layer.

Tests cover the full lifecycle using ``LocalStorageManager`` (upload → list →
download → generate_presigned_url) as well as the ``get_storage_manager``
factory.  S3 tests are included using mocked ``aiobotocore`` sessions.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import AsyncIterator
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from src.core.config import Settings
from src.core.storage import (
    LocalStorageManager,
    S3StorageManager,
    StorageInterface,
    get_storage_manager,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sample_df() -> pd.DataFrame:
    """Return a small deterministic DataFrame for testing."""
    return pd.DataFrame(
        {"city": ["Toronto", "Vancouver", "Calgary"], "value": [100, 200, 300]}
    )


# ---------------------------------------------------------------------------
# LocalStorageManager – full cycle tests
# ---------------------------------------------------------------------------


class TestLocalStorageManagerUpload:
    """Tests for ``LocalStorageManager.upload_dataframe_as_csv``."""

    @pytest.fixture()
    def storage(self, tmp_path: Path) -> LocalStorageManager:
        """Create a ``LocalStorageManager`` rooted in a tmp directory."""
        return LocalStorageManager(base_dir=str(tmp_path))

    @pytest.mark.asyncio
    async def test_upload_creates_file(
        self, storage: LocalStorageManager, tmp_path: Path
    ) -> None:
        """Uploading a DataFrame should persist a CSV file on disk."""
        df = _sample_df()
        await storage.upload_dataframe_as_csv(df, "reports/q1.csv")
        target = tmp_path / "reports" / "q1.csv"
        assert target.is_file()

    @pytest.mark.asyncio
    async def test_upload_csv_content_matches(
        self, storage: LocalStorageManager, tmp_path: Path
    ) -> None:
        """The persisted CSV content should parse back to the same data."""
        df = _sample_df()
        await storage.upload_dataframe_as_csv(df, "data.csv")
        loaded = pd.read_csv(tmp_path / "data.csv")
        pd.testing.assert_frame_equal(df, loaded)

    @pytest.mark.asyncio
    async def test_upload_creates_nested_directories(
        self, storage: LocalStorageManager, tmp_path: Path
    ) -> None:
        """Deeply nested paths should be created automatically."""
        df = _sample_df()
        await storage.upload_dataframe_as_csv(df, "a/b/c/d.csv")
        assert (tmp_path / "a" / "b" / "c" / "d.csv").is_file()


class TestLocalStorageManagerDownload:
    """Tests for ``LocalStorageManager.download_csv``."""

    @pytest.fixture()
    def storage(self, tmp_path: Path) -> LocalStorageManager:
        return LocalStorageManager(base_dir=str(tmp_path))

    @pytest.mark.asyncio
    async def test_download_roundtrip(
        self, storage: LocalStorageManager
    ) -> None:
        """Upload then download should return equal data."""
        original = _sample_df()
        await storage.upload_dataframe_as_csv(original, "round.csv")
        result = await storage.download_csv("round.csv")
        pd.testing.assert_frame_equal(original, result)

    @pytest.mark.asyncio
    async def test_download_missing_file_raises(
        self, storage: LocalStorageManager
    ) -> None:
        """Downloading a non-existent file must raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            await storage.download_csv("nonexistent.csv")


class TestLocalStorageManagerListObjects:
    """Tests for ``LocalStorageManager.list_objects``."""

    @pytest.fixture()
    def storage(self, tmp_path: Path) -> LocalStorageManager:
        return LocalStorageManager(base_dir=str(tmp_path))

    @pytest.mark.asyncio
    async def test_list_objects_empty_prefix(
        self, storage: LocalStorageManager
    ) -> None:
        """Listing a non-existent prefix returns an empty list."""
        result = await storage.list_objects("no_such_prefix/")
        assert result == []

    @pytest.mark.asyncio
    async def test_list_objects_finds_uploaded_files(
        self, storage: LocalStorageManager
    ) -> None:
        """Uploaded files should appear in the listing."""
        df = _sample_df()
        await storage.upload_dataframe_as_csv(df, "reports/a.csv")
        await storage.upload_dataframe_as_csv(df, "reports/b.csv")
        await storage.upload_dataframe_as_csv(df, "other/c.csv")

        result = await storage.list_objects("reports")
        assert sorted(result) == ["reports/a.csv", "reports/b.csv"]

    @pytest.mark.asyncio
    async def test_list_objects_single_file_prefix(
        self, storage: LocalStorageManager
    ) -> None:
        """Listing an exact file path should return that file."""
        df = _sample_df()
        await storage.upload_dataframe_as_csv(df, "only.csv")
        result = await storage.list_objects("only.csv")
        assert result == ["only.csv"]


class TestLocalStorageManagerPresignedUrl:
    """Tests for ``LocalStorageManager.generate_presigned_url``."""

    @pytest.fixture()
    def storage(self, tmp_path: Path) -> LocalStorageManager:
        return LocalStorageManager(base_dir=str(tmp_path))

    @pytest.mark.asyncio
    async def test_presigned_url_starts_with_file_scheme(
        self, storage: LocalStorageManager
    ) -> None:
        """Local presigned URLs should use the ``file://`` scheme."""
        df = _sample_df()
        await storage.upload_dataframe_as_csv(df, "url_test.csv")
        url = await storage.generate_presigned_url("url_test.csv")
        assert url.startswith("file:///")

    @pytest.mark.asyncio
    async def test_presigned_url_contains_filename(
        self, storage: LocalStorageManager
    ) -> None:
        """The generated URL should contain the target filename."""
        df = _sample_df()
        await storage.upload_dataframe_as_csv(df, "url_test.csv")
        url = await storage.generate_presigned_url("url_test.csv")
        assert "url_test.csv" in url


class TestLocalStorageManagerFullCycle:
    """End-to-end test: upload → list → download → presigned URL."""

    @pytest.mark.asyncio
    async def test_full_cycle(self, tmp_path: Path) -> None:
        """Exercise the entire local-storage lifecycle in one test."""
        storage = LocalStorageManager(base_dir=str(tmp_path))
        original = _sample_df()

        # 1. Upload
        await storage.upload_dataframe_as_csv(original, "cycle/test.csv")

        # 2. List
        keys = await storage.list_objects("cycle")
        assert keys == ["cycle/test.csv"]

        # 3. Download
        downloaded = await storage.download_csv("cycle/test.csv")
        pd.testing.assert_frame_equal(original, downloaded)

        # 4. Presigned URL
        url = await storage.generate_presigned_url("cycle/test.csv")
        assert url.startswith("file:///")
        assert "cycle" in url


class TestLocalStorageManagerBaseDir:
    """Test the ``base_dir`` property and constructor behaviour."""

    def test_base_dir_property(self, tmp_path: Path) -> None:
        """``base_dir`` should expose the internal base path."""
        storage = LocalStorageManager(base_dir=str(tmp_path / "custom"))
        assert storage.base_dir == tmp_path / "custom"

    def test_constructor_creates_directory(self, tmp_path: Path) -> None:
        """Constructor should create the base directory if missing."""
        target = tmp_path / "auto_create"
        assert not target.exists()
        LocalStorageManager(base_dir=str(target))
        assert target.is_dir()


# ---------------------------------------------------------------------------
# get_storage_manager factory tests
# ---------------------------------------------------------------------------


class TestGetStorageManager:
    """Tests for the ``get_storage_manager`` factory function."""

    def test_returns_local_by_default(self, tmp_path: Path) -> None:
        """Default ``storage_backend='local'`` should give LocalStorageManager."""
        settings = Settings(
            storage_backend="local",
            local_storage_dir=str(tmp_path),
        )
        mgr = get_storage_manager(settings=settings)
        assert isinstance(mgr, LocalStorageManager)

    def test_returns_s3_when_configured(self) -> None:
        """``storage_backend='s3'`` should give S3StorageManager."""
        settings = Settings(
            storage_backend="s3",
            s3_bucket_name="my-bucket",
            s3_region="us-east-1",
        )
        mgr = get_storage_manager(settings=settings)
        assert isinstance(mgr, S3StorageManager)

    def test_is_storage_interface(self, tmp_path: Path) -> None:
        """Returned object must satisfy the StorageInterface contract."""
        settings = Settings(
            storage_backend="local",
            local_storage_dir=str(tmp_path),
        )
        mgr = get_storage_manager(settings=settings)
        assert isinstance(mgr, StorageInterface)

    def test_uses_get_settings_when_none(self, tmp_path: Path) -> None:
        """When no settings are passed, ``get_settings()`` should be used."""
        mock_settings = Settings(
            storage_backend="local",
            local_storage_dir=str(tmp_path),
        )
        with patch(
            "src.core.storage.get_settings", return_value=mock_settings
        ):
            mgr = get_storage_manager()
        assert isinstance(mgr, LocalStorageManager)


# ---------------------------------------------------------------------------
# S3StorageManager – mocked tests
# ---------------------------------------------------------------------------


class _FakeAsyncContextManager:
    """Minimal async-context-manager that yields a mock S3 client."""

    def __init__(self, client: MagicMock) -> None:
        self._client = client

    async def __aenter__(self) -> MagicMock:
        return self._client

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        pass


class _FakeAsyncPaginator:
    """Async iterator over a single page of S3 list results."""

    def __init__(self, pages: list[dict[str, list[dict[str, str]]]]) -> None:
        self._pages = pages

    def paginate(self, **kwargs: str) -> _FakeAsyncPaginator:  # noqa: ARG002
        return self

    def __aiter__(self) -> _FakeAsyncPaginator:
        self._iter = iter(self._pages)
        return self

    async def __anext__(self) -> dict[str, list[dict[str, str]]]:
        try:
            return next(self._iter)
        except StopIteration:
            raise StopAsyncIteration


def _make_s3_manager(
    mock_client: MagicMock,
) -> S3StorageManager:
    """Build an ``S3StorageManager`` with a mocked aiobotocore session."""
    settings = Settings(
        storage_backend="s3",
        s3_bucket_name="test-bucket",
        s3_region="us-east-1",
    )
    mock_session = MagicMock()
    mock_session.create_client.return_value = _FakeAsyncContextManager(
        mock_client
    )
    return S3StorageManager(settings=settings, session=mock_session)


class TestS3StorageManagerUpload:
    """Tests for ``S3StorageManager.upload_dataframe_as_csv``."""

    @pytest.mark.asyncio
    async def test_upload_calls_put_object(self) -> None:
        """Uploading a DataFrame should call ``put_object`` on S3."""
        mock_client = MagicMock()
        mock_client.put_object = AsyncMock()

        mgr = _make_s3_manager(mock_client)
        df = _sample_df()
        await mgr.upload_dataframe_as_csv(df, "reports/q1.csv")

        mock_client.put_object.assert_awaited_once()
        call_kwargs = mock_client.put_object.call_args.kwargs
        assert call_kwargs["Bucket"] == "test-bucket"
        assert call_kwargs["Key"] == "reports/q1.csv"
        assert call_kwargs["ContentType"] == "text/csv"
        # Verify body is valid CSV
        body_str = call_kwargs["Body"].decode("utf-8")
        assert "Toronto" in body_str


class TestS3StorageManagerDownload:
    """Tests for ``S3StorageManager.download_csv``."""

    @pytest.mark.asyncio
    async def test_download_returns_dataframe(self) -> None:
        """Downloading a CSV from S3 should return a valid DataFrame."""
        csv_content = b"city,value\nToronto,100\nVancouver,200\n"

        mock_body = AsyncMock()
        mock_body.read = AsyncMock(return_value=csv_content)

        mock_client = MagicMock()
        mock_client.get_object = AsyncMock(
            return_value={"Body": mock_body}
        )

        mgr = _make_s3_manager(mock_client)
        result = await mgr.download_csv("data.csv")

        assert isinstance(result, pd.DataFrame)
        assert list(result.columns) == ["city", "value"]
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_download_missing_raises_file_not_found(self) -> None:
        """Downloading a non-existent S3 key should raise FileNotFoundError."""
        mock_client = MagicMock()

        # Simulate NoSuchKey exception
        no_such_key = type("NoSuchKey", (Exception,), {})
        mock_client.exceptions = MagicMock()
        mock_client.exceptions.NoSuchKey = no_such_key
        mock_client.get_object = AsyncMock(side_effect=no_such_key())

        mgr = _make_s3_manager(mock_client)
        with pytest.raises(FileNotFoundError, match="S3 object not found"):
            await mgr.download_csv("missing.csv")


class TestS3StorageManagerListObjects:
    """Tests for ``S3StorageManager.list_objects``."""

    @pytest.mark.asyncio
    async def test_list_objects_returns_keys(self) -> None:
        """Listing objects should return all keys from paginated results."""
        mock_client = MagicMock()
        pages = [
            {"Contents": [{"Key": "reports/a.csv"}, {"Key": "reports/b.csv"}]},
            {"Contents": [{"Key": "reports/c.csv"}]},
        ]
        mock_client.get_paginator = MagicMock(
            return_value=_FakeAsyncPaginator(pages)
        )

        mgr = _make_s3_manager(mock_client)
        result = await mgr.list_objects("reports/")

        assert result == ["reports/a.csv", "reports/b.csv", "reports/c.csv"]

    @pytest.mark.asyncio
    async def test_list_objects_empty_bucket(self) -> None:
        """Listing an empty prefix should return an empty list."""
        mock_client = MagicMock()
        pages: list[dict[str, list[dict[str, str]]]] = [{}]
        mock_client.get_paginator = MagicMock(
            return_value=_FakeAsyncPaginator(pages)
        )

        mgr = _make_s3_manager(mock_client)
        result = await mgr.list_objects("empty/")
        assert result == []


class TestS3StorageManagerPresignedUrl:
    """Tests for ``S3StorageManager.generate_presigned_url``."""

    @pytest.mark.asyncio
    async def test_presigned_url_returns_string(self) -> None:
        """Generating a presigned URL should return a string URL."""
        mock_client = MagicMock()
        expected_url = "https://s3.amazonaws.com/test-bucket/data.csv?X-Amz-Signature=abc"
        mock_client.generate_presigned_url = AsyncMock(
            return_value=expected_url
        )

        mgr = _make_s3_manager(mock_client)
        url = await mgr.generate_presigned_url("data.csv", ttl=600)

        assert url == expected_url
        mock_client.generate_presigned_url.assert_awaited_once_with(
            ClientMethod="get_object",
            Params={"Bucket": "test-bucket", "Key": "data.csv"},
            ExpiresIn=600,
        )


class TestS3StorageManagerClientKwargs:
    """Tests for internal ``_client_kwargs`` builder."""

    def test_includes_endpoint_when_set(self) -> None:
        """Custom endpoint URL should appear in client kwargs."""
        settings = Settings(
            storage_backend="s3",
            s3_bucket_name="b",
            s3_region="us-east-1",
            s3_endpoint_url="http://localhost:4566",
            s3_access_key_id="AKID",
            s3_secret_access_key="SECRET",
        )
        mgr = S3StorageManager(settings=settings)
        kwargs = mgr._client_kwargs()
        assert kwargs["endpoint_url"] == "http://localhost:4566"
        assert kwargs["aws_access_key_id"] == "AKID"
        assert kwargs["aws_secret_access_key"] == "SECRET"

    def test_omits_optional_fields_when_empty(self) -> None:
        """Empty optional fields should be omitted from client kwargs."""
        settings = Settings(
            storage_backend="s3",
            s3_bucket_name="b",
            s3_region="us-east-1",
        )
        mgr = S3StorageManager(settings=settings)
        kwargs = mgr._client_kwargs()
        assert "endpoint_url" not in kwargs
        assert "aws_access_key_id" not in kwargs
        assert "aws_secret_access_key" not in kwargs
        assert kwargs["region_name"] == "us-east-1"
