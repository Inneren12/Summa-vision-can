import asyncio
import hashlib
import io
import json
import os
import shutil
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import polars as pl
import structlog
from fastapi.concurrency import run_in_threadpool

from typing import Callable
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from src.core.config import Settings
from src.core.exceptions import StorageError
from src.core.storage import StorageInterface
from src.models.publication import PublicationStatus
from src.repositories.publication_repository import PublicationRepository
from src.schemas.events import EventType
from src.schemas.graphics import GenerationResult
from src.services.audit import AuditWriter
from src.services.graphics.backgrounds import BackgroundCategory, get_background
from src.services.graphics.compositor import composite_image
from src.services.graphics.svg_generator import generate_chart_svg

logger = structlog.get_logger(__name__)

async def _with_sem(sem: asyncio.Semaphore | None, coro):
    if sem:
        async with sem:
            return await coro
    return await coro

class GraphicPipeline:
    """End-to-End Graphic Generation Pipeline.

    Wires together SVG chart generation, template backgrounds, and image
    compositing into a resilient pipeline that produces versioned graphics.
    """

    def __init__(
        self,
        storage: StorageInterface,
        session_factory: async_sessionmaker[AsyncSession] | Callable[[], AsyncSession],
        settings: Settings,
    ):
        self._storage = storage
        self._session_factory = session_factory
        self._settings = settings


    async def generate(
        self,
        data_key: str,
        chart_type: str,
        title: str,
        size: tuple[int, int],
        category: str,
        source_product_id: str | None = None,
        render_sem: asyncio.Semaphore | None = None,
        io_sem: asyncio.Semaphore | None = None,
    ) -> GenerationResult:
        """Execute the end-to-end graphic generation pipeline."""

        # Stage 1: Load data
        df = await self._load_data(data_key, io_sem)

        # Stage 2-3: Render assets
        svg_bytes = await self._render_svg(df, chart_type, size, render_sem)
        bg_bytes = await self._render_background(category, size, render_sem)

        # Stage 4: Composite
        lowres_bytes, highres_bytes = await self._composite(svg_bytes, bg_bytes, render_sem)

        # Stage 5: Compute hashes
        config_hash, content_hash = self._compute_hashes(chart_type, size, title, lowres_bytes)

        # Stage 6: Resolve version
        version = await self._resolve_version(source_product_id, config_hash)

        # Stage 7: Create DRAFT publication
        pub_id, final_version = await self._create_draft_publication(
            title, chart_type, source_product_id, version, config_hash, content_hash, data_key,
        )

        # Stage 8: Build S3 keys
        s3_keys = self._build_s3_keys(pub_id, final_version, content_hash)

        # Stage 9: Create ZIP
        temp_dir, zip_bytes = await self._create_zip_package(
            lowres_bytes, highres_bytes, pub_id, final_version,
            title, chart_type, source_product_id,
        )

        # Stage 10: Upload to S3
        try:
            await self._upload_to_s3(lowres_bytes, highres_bytes, zip_bytes, s3_keys, io_sem, data_key)
        except Exception:
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
            raise
        finally:
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)

        # Stage 11: Publish (update DB)
        await self._publish(pub_id, s3_keys, io_sem, data_key)

        # Stage 12: Audit events
        await self._write_audit_events(pub_id, final_version, chart_type, size, category)

        # Stage 13: Return result
        return self._build_result(pub_id, s3_keys, final_version)

    # -- Private stage methods ------------------------------------------------

    async def _load_data(self, data_key: str, io_sem: asyncio.Semaphore | None) -> "pl.DataFrame":
        """Stage 1: Download Parquet from storage and read into DataFrame."""
        async def load_data():
            parquet_bytes = await self._storage.download_bytes(data_key)
            return pl.read_parquet(io.BytesIO(parquet_bytes))

        try:
            return await _with_sem(io_sem, load_data())
        except StorageError as e:
            logger.error("Pipeline failed at Stage 1 (data load): StorageError", error=str(e), data_key=data_key)
            raise

    async def _render_svg(self, df: "pl.DataFrame", chart_type: str, size: tuple[int, int], render_sem: asyncio.Semaphore | None) -> bytes:
        """Stage 2: Generate SVG chart from data."""
        try:
            async def render_svg():
                return await run_in_threadpool(
                    generate_chart_svg,
                    df=df,
                    chart_type=chart_type,
                    size=size,
                    # pass config if needed
                )
            return await _with_sem(render_sem, render_svg())
        except Exception as e:
            logger.error("Pipeline failed at Stage 2 (SVG gen)", error=str(e))
            raise

    async def _render_background(self, category: str, size: tuple[int, int], render_sem: asyncio.Semaphore | None) -> bytes:
        """Stage 3: Generate template background."""
        try:
            bg_category = BackgroundCategory(category.upper())
            async def render_bg():
                return await run_in_threadpool(get_background, bg_category, size)
            return await _with_sem(render_sem, render_bg())
        except Exception as e:
            logger.error("Pipeline failed at Stage 3 (background)", error=str(e))
            raise

    async def _composite(self, svg_bytes: bytes, bg_bytes: bytes, render_sem: asyncio.Semaphore | None) -> tuple[bytes, bytes]:
        """Stage 4: Composite SVG over background -> (lowres, highres)."""
        try:
            async def composite(dpi: int):
                return await run_in_threadpool(
                    composite_image,
                    bg_bytes=bg_bytes,
                    svg_bytes=svg_bytes,
                    dpi=dpi
                )
            # Lowres 150 DPI, Highres 300 DPI
            async def composite_both():
                low = await composite(150)
                high = await composite(300)
                return low, high

            return await _with_sem(render_sem, composite_both())
        except Exception as e:
            logger.error("Pipeline failed at Stage 4 (composite)", error=str(e))
            raise

    def _compute_hashes(self, chart_type: str, size: tuple[int, int], title: str, lowres_bytes: bytes) -> tuple[str, str]:
        """Stage 5: Compute config_hash and content_hash."""
        config_dict = {"chart_type": chart_type, "size": size, "title": title}
        config_json = json.dumps(config_dict, sort_keys=True).encode("utf-8")
        config_hash = hashlib.sha256(config_json).hexdigest()
        content_hash = hashlib.sha256(lowres_bytes).hexdigest()
        return config_hash, content_hash

    async def _resolve_version(self, source_product_id: str | None, config_hash: str) -> int:
        """Stage 6: Query DB for latest version of this lineage."""
        version = 1
        if source_product_id:
            async with self._session_factory() as session:
                repo = PublicationRepository(session)
                latest_version = await repo.get_latest_version(source_product_id, config_hash)
                if latest_version:
                    version = latest_version + 1
        return version

    async def _create_draft_publication(
        self,
        title: str,
        chart_type: str,
        source_product_id: str | None,
        version: int,
        config_hash: str,
        content_hash: str,
        data_key: str,
    ) -> tuple[int, int]:
        """Stage 7: Create Publication record with DRAFT status. Returns (pub_id, final_version)."""
        try:
            async with self._session_factory() as session:
                repo = PublicationRepository(session)
                pub = await repo.create_published(
                    headline=title,
                    chart_type=chart_type,
                    s3_key_lowres="",       # placeholder -- updated after upload
                    s3_key_highres="",      # placeholder -- updated after upload
                    source_product_id=source_product_id,
                    version=version,
                    config_hash=config_hash,
                    content_hash=content_hash,
                    status=PublicationStatus.DRAFT,  # NOT published yet
                )
                await session.commit()
                return pub.id, pub.version  # pub.version is the authoritative version
        except Exception as e:
            logger.error("Pipeline failed at Stage 7 (DB DRAFT create)", error=str(e), data_key=data_key)
            raise

    def _build_s3_keys(self, pub_id: int, version: int, content_hash: str) -> dict[str, str]:
        """Stage 8: Construct S3 key paths for lowres, highres, zip."""
        return {
            "lowres": f"publications/{pub_id}/v{version}/{content_hash[:8]}_lowres.png",
            "highres": f"publications/{pub_id}/v{version}/{content_hash[:8]}_highres.png",
            "zip": f"publications/{pub_id}/v{version}/archive.zip",
        }

    async def _create_zip_package(
        self,
        lowres_bytes: bytes,
        highres_bytes: bytes,
        pub_id: int,
        final_version: int,
        title: str,
        chart_type: str,
        source_product_id: str | None,
    ) -> tuple[str, bytes]:
        """Stage 9: Create temp dir with ZIP. Returns (temp_dir_path, zip_bytes)."""
        temp_dir = ""
        try:
            temp_dir = tempfile.mkdtemp()
            lowres_path = os.path.join(temp_dir, "lowres.png")
            highres_path = os.path.join(temp_dir, "highres.png")
            metadata_path = os.path.join(temp_dir, "metadata.json")
            zip_path = os.path.join(temp_dir, "archive.zip")

            with open(lowres_path, "wb") as f:
                f.write(lowres_bytes)
            with open(highres_path, "wb") as f:
                f.write(highres_bytes)

            metadata = {
                "publication_id": pub_id,
                "version": final_version,
                "title": title,
                "chart_type": chart_type,
                "source_product_id": source_product_id,
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
            with open(metadata_path, "w") as meta_f:
                json.dump(metadata, meta_f)

            with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                zf.write(lowres_path, arcname="lowres.png")
                zf.write(highres_path, arcname="highres.png")
                zf.write(metadata_path, arcname="metadata.json")

            zip_size_mb = os.path.getsize(zip_path) / (1024 * 1024)
            if zip_size_mb > self._settings.max_zip_size_mb:
                raise ValueError(f"Generated ZIP exceeds limit of {self._settings.max_zip_size_mb} MB")

            with open(zip_path, "rb") as zip_f:
                zip_bytes = zip_f.read()

            return temp_dir, zip_bytes
        except Exception as e:
            logger.error("Pipeline failed at Stage 9 (ZIP creation)", error=str(e))
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
            raise

    async def _upload_to_s3(
        self,
        lowres_bytes: bytes,
        highres_bytes: bytes,
        zip_bytes: bytes,
        s3_keys: dict[str, str],
        io_sem: asyncio.Semaphore | None,
        data_key: str,
    ) -> None:
        """Stage 10: Upload all files to S3 under io_sem."""
        async def upload_files():
            try:
                await self._storage.upload_bytes(lowres_bytes, s3_keys["lowres"])
            except Exception as e:
                logger.error("Pipeline failed at Stage 10a (lowres upload)", error=str(e), data_key=data_key)
                raise

            try:
                await self._storage.upload_bytes(highres_bytes, s3_keys["highres"])
                await self._storage.upload_bytes(zip_bytes, s3_keys["zip"])
            except Exception as e:
                logger.error("Pipeline failed at Stage 10b (highres/ZIP upload)", error=str(e), data_key=data_key)
                await self._storage.delete_object(s3_keys["lowres"])
                raise

        await _with_sem(io_sem, upload_files())

    async def _publish(self, pub_id: int, s3_keys: dict[str, str], io_sem: asyncio.Semaphore | None, data_key: str) -> None:
        """Stage 11: Update Publication status to PUBLISHED with S3 keys."""
        try:
            async with self._session_factory() as session:
                repo = PublicationRepository(session)
                await repo.update_s3_keys_and_publish(
                    publication_id=pub_id,
                    s3_key_lowres=s3_keys["lowres"],
                    s3_key_highres=s3_keys["highres"],
                    status=PublicationStatus.PUBLISHED,
                )
                await session.commit()
        except Exception as e:
            logger.warning("Pipeline failed at Stage 11 (DB update to PUBLISHED). Cleaning up S3 objects.", error=str(e), data_key=data_key)

            async def cleanup_s3_keys():
                for key in s3_keys.values():
                    try:
                        await self._storage.delete_object(key)
                    except Exception as exc:
                        logger.error("Failed to clean up S3 object", key=key, error=str(exc))

            # Use io_sem to delete the objects
            await _with_sem(io_sem, cleanup_s3_keys())
            raise

    async def _write_audit_events(self, pub_id: int, version: int, chart_type: str, size: tuple[int, int], category: str) -> None:
        """Stage 12: Write publication.generated and publication.published audit events."""
        async with self._session_factory() as session:
            writer = AuditWriter(session)
            await writer.log_event(
                event_type=EventType.PUBLICATION_GENERATED,
                entity_type="publication",
                entity_id=str(pub_id),
                metadata={"version": version, "chart_type": chart_type, "size": list(size), "category": category}
            )
            await writer.log_event(
                event_type=EventType.PUBLICATION_PUBLISHED,
                entity_type="publication",
                entity_id=str(pub_id),
                metadata={"version": version}
            )
            await session.commit()

    def _build_result(self, pub_id: int, s3_keys: dict[str, str], version: int) -> GenerationResult:
        """Stage 13: Construct the GenerationResult return value."""
        cdn_url_lowres = f"{self._settings.cdn_base_url}/{s3_keys['lowres']}"
        return GenerationResult(
            publication_id=pub_id,
            cdn_url_lowres=cdn_url_lowres,
            s3_key_highres=s3_keys["highres"],
            version=version
        )
