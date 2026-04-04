"""Admin endpoints for publication queue and graphic generation.

Provides two endpoints:

* ``GET  /api/v1/admin/queue``               — list DRAFT publications
* ``POST /api/v1/admin/graphics/generate``   — trigger async generation pipeline

Architecture:
    Follows ARCH-DPEN-001 — all services arrive via ``Depends``.
    Route handlers perform only request/response mapping.
    Business logic lives in :func:`_run_generation_pipeline`.
"""

from __future__ import annotations

import asyncio

import pandas as pd
import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas.admin_graphics import (
    GenerateRequest,
    GenerateResponse,
    PublicationResponse,
)
from src.core.database import get_db
from src.core.logging import get_logger
from src.core.storage import StorageInterface, get_storage_manager
from src.core.task_manager import TaskManager, get_task_manager
from src.models.publication import Publication, PublicationStatus
from src.repositories.publication_repository import PublicationRepository
from src.services.ai.schemas import ChartType
from src.services.graphics.ai_image_client import AIImageClient
from src.services.graphics.compositor import composite_image
from src.services.graphics.svg_generator import (
    SIZE_INSTAGRAM,
    SIZE_REDDIT,
    SIZE_TWITTER,
    generate_chart_svg,
)

logger: structlog.stdlib.BoundLogger = get_logger(module="admin_graphics")

# ---------------------------------------------------------------------------
# Size preset mapping
# ---------------------------------------------------------------------------

SIZE_PRESETS: dict[str, tuple[int, int]] = {
    "instagram": SIZE_INSTAGRAM,  # (1080, 1080)
    "twitter": SIZE_TWITTER,  # (1200, 628)
    "reddit": SIZE_REDDIT,  # (1200, 900)
}

# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


# ---------------------------------------------------------------------------
# Dependency helpers
# ---------------------------------------------------------------------------


def _get_repo(session: AsyncSession = Depends(get_db)) -> PublicationRepository:
    """Provide a PublicationRepository via dependency injection."""
    return PublicationRepository(session)


def _get_storage() -> StorageInterface:
    """Provide a StorageInterface via dependency injection."""
    return get_storage_manager()


# ---------------------------------------------------------------------------
# GET /api/v1/admin/queue
# ---------------------------------------------------------------------------


@router.get(
    "/queue",
    response_model=list[PublicationResponse],
    status_code=status.HTTP_200_OK,
    summary="List draft publications",
    responses={
        200: {"description": "List of DRAFT publications (may be empty)."},
    },
)
async def get_queue(
    limit: int = Query(default=20, ge=1, le=100),
    pub_repo: PublicationRepository = Depends(_get_repo),
) -> list[PublicationResponse]:
    """Return draft publications ordered by virality score (highest first).

    If no drafts exist, an empty list is returned (never 404).

    Parameters
    ----------
    limit:
        Maximum number of results (1–100, default 20).
    pub_repo:
        Injected :class:`PublicationRepository`.

    Returns
    -------
    list[PublicationResponse]
        Draft publications formatted for the admin panel queue.
    """
    publications = await pub_repo.get_drafts(limit=limit)
    return [
        PublicationResponse(
            id=pub.id,
            headline=pub.headline,
            chart_type=pub.chart_type,
            virality_score=pub.virality_score,
            status=pub.status.value,
            created_at=pub.created_at,
        )
        for pub in publications
    ]


# ---------------------------------------------------------------------------
# POST /api/v1/admin/graphics/generate
# ---------------------------------------------------------------------------


@router.post(
    "/graphics/generate",
    response_model=GenerateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger graphic generation",
    responses={
        202: {"description": "Generation submitted — poll /api/v1/admin/tasks/{task_id}."},
        404: {"description": "Publication not found."},
        409: {"description": "Publication is not in DRAFT status."},
    },
)
async def generate_graphic(
    body: GenerateRequest,
    pub_repo: PublicationRepository = Depends(_get_repo),
    storage: StorageInterface = Depends(_get_storage),
    tm: TaskManager = Depends(get_task_manager),
    db: AsyncSession = Depends(get_db),
) -> GenerateResponse:
    """Submit a graphic generation job for the given publication.

    The pipeline runs in the background via :class:`TaskManager`.
    The HTTP response is returned **immediately** with status ``202 Accepted``.

    Parameters
    ----------
    body:
        JSON body with ``brief_id``, ``size_preset``, ``dpi``, ``watermark``.
    pub_repo:
        Injected publication repository.
    storage:
        Injected storage backend.
    tm:
        Injected task manager.
    db:
        Injected async database session.

    Returns
    -------
    GenerateResponse
        Contains the ``task_id`` for polling.

    Raises
    ------
    HTTPException (404)
        If no publication with ``brief_id`` exists.
    HTTPException (409)
        If the publication is not in ``DRAFT`` status.
    """
    publication = await pub_repo.get_by_id(body.brief_id)
    if publication is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Publication not found",
        )
    if publication.status != PublicationStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Publication is not in DRAFT status",
        )

    size = SIZE_PRESETS[body.size_preset]

    coro = _run_generation_pipeline(
        publication=publication,
        size=size,
        dpi=body.dpi,
        watermark=body.watermark,
        pub_repo=pub_repo,
        storage=storage,
        session=db,
    )
    task_id: str = tm.submit_task(coro)

    return GenerateResponse(task_id=task_id)


# ---------------------------------------------------------------------------
# Generation pipeline (private, executed by TaskManager in background)
# ---------------------------------------------------------------------------


async def _run_generation_pipeline(
    *,
    publication: Publication,
    size: tuple[int, int],
    dpi: int,
    watermark: bool,
    pub_repo: PublicationRepository,
    storage: StorageInterface,
    session: AsyncSession,
) -> dict[str, str]:
    """Execute the full graphic generation pipeline for a publication.

    This function is **not** a route handler — it receives plain Python
    objects and can be tested in isolation (ARCH-DPEN-001).

    Steps
    -----
    1. Build a placeholder DataFrame for chart rendering.
    2. Call ``generate_chart_svg`` to produce SVG bytes.
    3. Call ``AIImageClient.generate_background`` for a BG image.
    4. Call ``composite_image`` to merge BG + SVG into final PNG.
    5. Upload PNG to storage (lowres + highres keys).
    6. Update the ``Publication`` status to ``PUBLISHED`` and save S3 keys.

    Parameters
    ----------
    publication:
        The ``Publication`` ORM instance to generate for.
    size:
        ``(width, height)`` in pixels.
    dpi:
        Rendering DPI for SVG rasterisation.
    watermark:
        Whether to apply a watermark.
    pub_repo:
        Repository for publication updates.
    storage:
        Storage backend for uploading PNG files.
    session:
        Database session for committing changes.

    Returns
    -------
    dict[str, str]
        A dict with ``s3_key_lowres`` and ``s3_key_highres``.

    Raises
    ------
    Exception
        Any failure is re-raised after logging so ``TaskManager`` marks
        the task as ``FAILED``.
    """
    try:
        # 1. Build placeholder DataFrame
        # TODO: fetch real StatCan data from storage using publication.cube_id when available
        df = pd.DataFrame(
            {
                "Category": ["Q1", "Q2", "Q3", "Q4", "Q5"],
                "Value": [120, 340, 280, 410, 190],
            }
        )

        # 2. Generate SVG chart
        chart_type = ChartType(publication.chart_type)
        svg_bytes: bytes = generate_chart_svg(df, chart_type, size=size)

        # 3. Generate AI background
        client = AIImageClient()
        bg_prompt = "Canadian data visualization"
        bg_bytes: bytes = await client.generate_background(
            prompt=bg_prompt,
            size=size,
        )

        # 4. Composite final PNG (sync function → run in thread)
        png_bytes: bytes = await asyncio.to_thread(
            composite_image,
            bg_bytes,
            svg_bytes,
            dpi=dpi,
            watermark=watermark,
        )

        # 5. Upload to storage
        s3_key_lowres = f"graphics/{publication.id}/lowres.png"
        s3_key_highres = f"graphics/{publication.id}/highres.png"

        await storage.upload_raw(
            png_bytes, s3_key_lowres, content_type="image/png"
        )
        # TODO: generate actual high-res variant; for now upload the same file
        await storage.upload_raw(
            png_bytes, s3_key_highres, content_type="image/png"
        )

        # 6. Update publication in DB
        await pub_repo.update_status(
            publication.id, PublicationStatus.PUBLISHED
        )
        await pub_repo.update_s3_keys(
            publication.id,
            s3_key_lowres=s3_key_lowres,
            s3_key_highres=s3_key_highres,
        )
        await session.commit()

        logger.info(
            "generation.pipeline_completed",
            publication_id=publication.id,
            s3_key_lowres=s3_key_lowres,
            s3_key_highres=s3_key_highres,
        )

        return {
            "s3_key_lowres": s3_key_lowres,
            "s3_key_highres": s3_key_highres,
        }

    except Exception:
        logger.error(
            "generation.pipeline_failed",
            publication_id=publication.id,
            exc_info=True,
        )
        raise
