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

        # Stage 1 — Load Data (io_sem)
        async def load_data():
            parquet_bytes = await self._storage.download_bytes(data_key)
            return pl.read_parquet(io.BytesIO(parquet_bytes))

        try:
            df = await _with_sem(io_sem, load_data())
        except StorageError as e:
            logger.error("Pipeline failed at Stage 1 (data load): StorageError", error=str(e), data_key=data_key)
            raise

        # Stage 2 — Generate SVG Chart (render_sem, run_in_threadpool)
        try:
            async def render_svg():
                return await run_in_threadpool(
                    generate_chart_svg,
                    df=df,
                    chart_type=chart_type,
                    size=size,
                    # pass config if needed
                )
            svg_bytes = await _with_sem(render_sem, render_svg())
        except Exception as e:
            logger.error("Pipeline failed at Stage 2 (SVG gen)", error=str(e), data_key=data_key)
            raise

        # Stage 3 — Generate Background (render_sem, run_in_threadpool)
        try:
            bg_category = BackgroundCategory(category.upper())
            async def render_bg():
                return await run_in_threadpool(get_background, bg_category, size)
            bg_bytes = await _with_sem(render_sem, render_bg())
        except Exception as e:
            logger.error("Pipeline failed at Stage 3 (background)", error=str(e), data_key=data_key)
            raise

        # Stage 4 — Composite (render_sem, run_in_threadpool)
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

            lowres_bytes, highres_bytes = await _with_sem(render_sem, composite_both())
        except Exception as e:
            logger.error("Pipeline failed at Stage 4 (composite)", error=str(e), data_key=data_key)
            raise



        temp_dir = ""
        try:
            # Stage 5 — Compute Hashes & Version (no semaphore, no DB yet)
            config_dict = {"chart_type": chart_type, "size": size, "title": title}
            config_json = json.dumps(config_dict, sort_keys=True).encode("utf-8")
            config_hash = hashlib.sha256(config_json).hexdigest()
            content_hash = hashlib.sha256(lowres_bytes).hexdigest()

            # Stage 6 — Resolve Version (short DB session, R6)
            version = 1
            if source_product_id:
                async with self._session_factory() as session:
                    repo = PublicationRepository(session)
                    latest_version = await repo.get_latest_version(source_product_id, config_hash)
                    if latest_version:
                        version = latest_version + 1

            # Stage 7 — Create ZIP (temp files, strict cleanup)
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
                "title": title,
                "chart_type": chart_type,
                "source_product_id": source_product_id,
                "version": version,
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

        except Exception as e:
            logger.error("Pipeline failed at Stage 5, 6, or 7", error=str(e), data_key=data_key)
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
            raise

        # Stage 8 — Upload to S3 (io_sem)
        import uuid
        pub_id = str(uuid.uuid4())
        s3_key_lowres  = f"publications/{pub_id}/v{version}/{content_hash[:8]}_lowres.png"
        s3_key_highres = f"publications/{pub_id}/v{version}/{content_hash[:8]}_highres.png"
        s3_key_zip     = f"publications/{pub_id}/v{version}/archive.zip"

        async def upload_files():
            try:
                await self._storage.upload_bytes(lowres_bytes, s3_key_lowres)
            except Exception as e:
                logger.error("Pipeline failed at Stage 8a (lowres upload)", error=str(e), data_key=data_key)
                raise

            try:
                await self._storage.upload_bytes(highres_bytes, s3_key_highres)
                await self._storage.upload_bytes(zip_bytes, s3_key_zip)
            except Exception as e:
                logger.error("Pipeline failed at Stage 8b (highres/ZIP upload)", error=str(e), data_key=data_key)
                await self._storage.delete_object(s3_key_lowres)
                raise

        try:
            await _with_sem(io_sem, upload_files())
        except Exception as e:
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
            raise
        finally:
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)

        # Stage 9 — Persist to DB (short session, R6)
        try:
            async with self._session_factory() as session:
                repo = PublicationRepository(session)
                pub = await repo.create_published(
                    headline=title,
                    chart_type=chart_type,
                    s3_key_lowres=s3_key_lowres,
                    s3_key_highres=s3_key_highres,
                    source_product_id=source_product_id,
                    version=version,
                    config_hash=config_hash,
                    content_hash=content_hash,
                )
                db_pub_id = pub.id
                await session.commit()
        except Exception as e:
            logger.warning("Pipeline failed at Stage 9 (DB persist). Cleaning up S3 objects.", error=str(e), data_key=data_key)

            async def cleanup_s3_keys():
                for key in [s3_key_lowres, s3_key_highres, s3_key_zip]:
                    try:
                        await self._storage.delete_object(key)
                    except Exception as exc:
                        logger.error("Failed to clean up S3 object", key=key, error=str(exc))

            # Use io_sem to delete the objects
            await _with_sem(io_sem, cleanup_s3_keys())
            raise

        # Stage 10 — Audit Events
        async with self._session_factory() as session:
            writer = AuditWriter(session)
            await writer.log_event(
                event_type=EventType.PUBLICATION_GENERATED,
                entity_type="publication",
                entity_id=str(db_pub_id),
                metadata={"version": version, "chart_type": chart_type, "size": size, "category": category}
            )
            await writer.log_event(
                event_type=EventType.PUBLICATION_PUBLISHED,
                entity_type="publication",
                entity_id=str(db_pub_id),
                metadata={"version": version}
            )
            await session.commit()

        # Stage 11 — Return Result
        cdn_url_lowres = f"{self._settings.cdn_base_url}/{s3_key_lowres}"
        return GenerationResult(
            publication_id=db_pub_id,
            cdn_url_lowres=cdn_url_lowres,
            s3_key_highres=s3_key_highres,
            version=version
        )
