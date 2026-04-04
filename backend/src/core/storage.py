"""Storage abstraction layer for Summa Vision.

Provides a uniform interface for persisting Pandas DataFrames as CSV files
and generating download links.  Two concrete implementations are provided:

* **S3StorageManager** – uses ``aiobotocore`` for async Amazon S3 operations.
* **LocalStorageManager** – saves files to a local directory for development.

A factory function :func:`get_storage_manager` reads the ``STORAGE_BACKEND``
setting to determine which implementation to instantiate.
"""

from __future__ import annotations

import abc
import io
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import quote

import pandas as pd
from aiobotocore.session import AioSession

from src.core.config import Settings, get_settings

if TYPE_CHECKING:
    from types_aiobotocore_s3.client import S3Client


# ---------------------------------------------------------------------------
# Abstract interface
# ---------------------------------------------------------------------------


class StorageInterface(abc.ABC):
    """Abstract base class defining the storage contract.

    Every concrete storage backend must implement these four operations so
    that higher-level services can remain storage-agnostic.
    """

    @abc.abstractmethod
    async def upload_dataframe_as_csv(
        self, df: pd.DataFrame, path: str
    ) -> None:
        """Serialise *df* to CSV and persist it at *path*.

        Args:
            df: The DataFrame to serialise.
            path: Logical storage path (e.g. ``"reports/2026/q1.csv"``).
        """

    @abc.abstractmethod
    async def upload_raw(
        self, data: str | bytes, path: str, content_type: str = "text/html"
    ) -> None:
        """Persist arbitrary raw content at *path*.

        This is useful for saving HTML snapshots, JSON blobs, or other
        non-CSV payloads that should not go through DataFrame serialisation.

        Args:
            data: The raw content to persist (string or bytes).
            path: Logical storage path.
            content_type: MIME type hint for the backend (default ``text/html``).
        """

    @abc.abstractmethod
    async def download_csv(self, path: str) -> pd.DataFrame:
        """Download a CSV object at *path* and return it as a DataFrame.

        Args:
            path: Logical storage path.

        Returns:
            A :class:`pandas.DataFrame` parsed from the CSV content.

        Raises:
            FileNotFoundError: If *path* does not exist in the backend.
        """

    @abc.abstractmethod
    async def list_objects(self, prefix: str) -> list[str]:
        """List object keys whose path starts with *prefix*.

        Args:
            prefix: Key prefix to filter by (e.g. ``"reports/"``).

        Returns:
            A list of matching object keys.
        """

    @abc.abstractmethod
    async def generate_presigned_url(
        self, path: str, ttl: int = 3600
    ) -> str:
        """Generate a time-limited download URL for the object at *path*.

        Args:
            path: Logical storage path.
            ttl: URL validity in seconds (default 3600 = 1 hour).

        Returns:
            A URL string that can be used to download the object.
        """


# ---------------------------------------------------------------------------
# S3 implementation
# ---------------------------------------------------------------------------


class S3StorageManager(StorageInterface):
    """AWS S3 storage backend using ``aiobotocore``.

    Parameters:
        settings: Application settings containing S3 configuration.
        session: Optional ``AioSession`` instance; one will be created if
            not provided.
    """

    def __init__(
        self,
        settings: Settings,
        session: AioSession | None = None,
    ) -> None:
        self._bucket: str = settings.s3_bucket_name
        self._region: str = settings.s3_region
        self._endpoint_url: str = settings.s3_endpoint_url
        self._access_key_id: str = settings.s3_access_key_id
        self._secret_access_key: str = settings.s3_secret_access_key
        self._session: AioSession = session or AioSession()

    def _client_kwargs(self) -> dict[str, str]:
        """Build keyword arguments for ``create_client``.

        Returns:
            A dict of keyword arguments suitable for
            ``AioSession.create_client("s3", ...)``.
        """
        kwargs: dict[str, str] = {"region_name": self._region}
        if self._endpoint_url:
            kwargs["endpoint_url"] = self._endpoint_url
        if self._access_key_id:
            kwargs["aws_access_key_id"] = self._access_key_id
        if self._secret_access_key:
            kwargs["aws_secret_access_key"] = self._secret_access_key
        return kwargs

    async def upload_dataframe_as_csv(
        self, df: pd.DataFrame, path: str
    ) -> None:
        """Upload *df* as a CSV object to S3 at *path*."""
        csv_bytes: bytes = df.to_csv(index=False).encode("utf-8")
        async with self._session.create_client(
            "s3", **self._client_kwargs()
        ) as client:
            client: S3Client  # type: ignore[no-redef]
            await client.put_object(
                Bucket=self._bucket,
                Key=path,
                Body=csv_bytes,
                ContentType="text/csv",
            )

    async def upload_raw(
        self, data: str | bytes, path: str, content_type: str = "text/html"
    ) -> None:
        """Upload raw content to S3 at *path*."""
        body: bytes = data.encode("utf-8") if isinstance(data, str) else data
        async with self._session.create_client(
            "s3", **self._client_kwargs()
        ) as client:
            client: S3Client  # type: ignore[no-redef]
            await client.put_object(
                Bucket=self._bucket,
                Key=path,
                Body=body,
                ContentType=content_type,
            )

    async def download_csv(self, path: str) -> pd.DataFrame:
        """Download a CSV from S3 at *path* and return a DataFrame.

        Raises:
            FileNotFoundError: If the key does not exist.
        """
        async with self._session.create_client(
            "s3", **self._client_kwargs()
        ) as client:
            client: S3Client  # type: ignore[no-redef]
            try:
                response = await client.get_object(
                    Bucket=self._bucket, Key=path
                )
            except client.exceptions.NoSuchKey:
                raise FileNotFoundError(
                    f"S3 object not found: s3://{self._bucket}/{path}"
                )
            body = await response["Body"].read()
        return pd.read_csv(io.BytesIO(body))

    async def list_objects(self, prefix: str) -> list[str]:
        """List S3 object keys matching *prefix*."""
        keys: list[str] = []
        async with self._session.create_client(
            "s3", **self._client_kwargs()
        ) as client:
            client: S3Client  # type: ignore[no-redef]
            paginator = client.get_paginator("list_objects_v2")
            async for page in paginator.paginate(
                Bucket=self._bucket, Prefix=prefix
            ):
                for obj in page.get("Contents", []):
                    keys.append(obj["Key"])
        return keys

    async def generate_presigned_url(
        self, path: str, ttl: int = 3600
    ) -> str:
        """Generate a presigned S3 URL for *path*."""
        async with self._session.create_client(
            "s3", **self._client_kwargs()
        ) as client:
            client: S3Client  # type: ignore[no-redef]
            url: str = await client.generate_presigned_url(
                ClientMethod="get_object",
                Params={"Bucket": self._bucket, "Key": path},
                ExpiresIn=ttl,
            )
        return url


# ---------------------------------------------------------------------------
# Local filesystem implementation
# ---------------------------------------------------------------------------


class LocalStorageManager(StorageInterface):
    """Filesystem-backed storage for local development & testing.

    Parameters:
        base_dir: Root directory under which all objects are stored.
            Defaults to ``./data/local_storage``.
    """

    def __init__(self, base_dir: str = "./data/local_storage") -> None:
        self._base: Path = Path(base_dir)
        self._base.mkdir(parents=True, exist_ok=True)

    @property
    def base_dir(self) -> Path:
        """Return the resolved base directory path."""
        return self._base

    def _resolve(self, path: str) -> Path:
        """Resolve a logical path to an absolute filesystem path.

        Args:
            path: Logical object key.

        Returns:
            Full filesystem ``Path``.
        """
        return self._base / path

    async def upload_dataframe_as_csv(
        self, df: pd.DataFrame, path: str
    ) -> None:
        """Write *df* to a CSV file on disk at *path*."""
        target = self._resolve(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(target, index=False)

    async def upload_raw(
        self, data: str | bytes, path: str, content_type: str = "text/html"
    ) -> None:
        """Write raw content to a file on disk at *path*."""
        target = self._resolve(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(data, str):
            target.write_text(data, encoding="utf-8")
        else:
            target.write_bytes(data)

    async def download_csv(self, path: str) -> pd.DataFrame:
        """Read a CSV file from disk and return a DataFrame.

        Raises:
            FileNotFoundError: If the file does not exist.
        """
        target = self._resolve(path)
        if not target.is_file():
            raise FileNotFoundError(f"Local file not found: {target}")
        return pd.read_csv(target)

    async def list_objects(self, prefix: str) -> list[str]:
        """List files under *prefix* relative to the base directory."""
        search_root = self._base / prefix
        if not search_root.exists():
            return []

        results: list[str] = []
        if search_root.is_file():
            results.append(
                str(search_root.relative_to(self._base)).replace("\\", "/")
            )
        else:
            for item in search_root.rglob("*"):
                if item.is_file():
                    results.append(
                        str(item.relative_to(self._base)).replace("\\", "/")
                    )
        return sorted(results)

    async def generate_presigned_url(
        self, path: str, ttl: int = 3600
    ) -> str:
        """Return a ``file://`` URL for local debugging.

        The *ttl* parameter is accepted for interface compatibility but
        is ignored since local files do not expire.

        Args:
            path: Logical storage path.
            ttl: Ignored for local storage.

        Returns:
            A ``file://`` URI pointing to the local file.
        """
        target = self._resolve(path).resolve()
        # Produce a proper file URI with percent-encoded path components.
        return "file:///" + quote(
            str(target).replace("\\", "/"), safe="/:@"
        )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def get_storage_manager(
    settings: Settings | None = None,
) -> StorageInterface:
    """Create the appropriate storage backend based on application settings.

    This is the **only** entry-point that higher-level code should use to
    obtain a :class:`StorageInterface` instance.

    Args:
        settings: Optional explicit settings.  When ``None`` the cached
            singleton from :func:`get_settings` is used.

    Returns:
        A concrete :class:`StorageInterface` implementation.

    Raises:
        ValueError: If ``settings.storage_backend`` contains an
            unrecognised value.
    """
    if settings is None:
        settings = get_settings()

    backend = settings.storage_backend

    if backend == "local":
        return LocalStorageManager(base_dir=settings.local_storage_dir)
    if backend == "s3":
        return S3StorageManager(settings=settings)

    # Literal type should prevent this at static-analysis time, but guard
    # at runtime just in case.
    raise ValueError(f"Unknown storage backend: {backend!r}")
