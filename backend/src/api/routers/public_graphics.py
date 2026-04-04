"""Public gallery endpoint — ``GET /api/v1/public/graphics``.

Returns a paginated list of published infographics with presigned S3 URLs
for low-resolution previews.  This is a **public** endpoint — no API key
is required.  Rate limiting is enforced per client IP using
:class:`InMemoryRateLimiter` (30 req/min).

Architecture: follows ARCH-DPEN-001 — ``PublicationRepository`` and
``StorageInterface`` are injected via FastAPI ``Depends``.  No direct
SQLAlchemy imports appear in this module.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.security.ip_rate_limiter import InMemoryRateLimiter
from src.core.storage import StorageInterface, get_storage_manager
from src.repositories.publication_repository import PublicationRepository

router = APIRouter(prefix="/api/v1/public", tags=["public"])


# ---------------------------------------------------------------------------
# Rate limiter — one instance per process, 30 requests per minute per IP
# ---------------------------------------------------------------------------

_gallery_limiter = InMemoryRateLimiter(max_requests=30, window_seconds=60)


def get_gallery_limiter() -> InMemoryRateLimiter:
    """Provide the gallery rate limiter via dependency injection.

    Tests can override this dependency with a custom limiter.
    """
    return _gallery_limiter


# ---------------------------------------------------------------------------
# Dependency helpers
# ---------------------------------------------------------------------------


def _get_storage() -> StorageInterface:
    """Provide a StorageInterface via dependency injection.

    In production this reads the ``STORAGE_BACKEND`` setting; tests can
    override this dependency with a mock.
    """
    return get_storage_manager()


def _get_repo(session: AsyncSession = Depends(get_db)) -> PublicationRepository:
    """Provide a PublicationRepository via dependency injection.

    The ``AsyncSession`` is injected by the ``get_db`` dependency.
    Tests can override this dependency with a mock repository.
    """
    return PublicationRepository(session)


# ---------------------------------------------------------------------------
# Response schema
# ---------------------------------------------------------------------------


class PublicationResponse(BaseModel):
    """Public-facing publication representation.

    Deliberately omits ``s3_key_lowres`` and ``s3_key_highres`` to
    prevent exposing internal object keys to the public internet.

    Attributes:
        id: Publication primary key.
        headline: Short title of the graphic.
        chart_type: Type of chart (e.g. ``"bar"``, ``"infographic"``).
        virality_score: AI-estimated virality score (0.0 – 1.0).
        preview_url: Time-limited presigned URL for the low-res preview.
        created_at: UTC timestamp of record creation.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    headline: str
    chart_type: str
    virality_score: float
    preview_url: str
    created_at: datetime


class PaginatedGraphicsResponse(BaseModel):
    """Paginated wrapper for the gallery endpoint response.

    Attributes:
        items: List of publication response objects for this page.
        limit: The limit that was applied.
        offset: The offset that was applied.
    """

    items: list[PublicationResponse]
    limit: int
    offset: int


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.get(
    "/graphics",
    response_model=PaginatedGraphicsResponse,
    status_code=status.HTTP_200_OK,
    summary="List published infographics",
    responses={
        200: {"description": "Paginated list of published graphics."},
        429: {"description": "Rate limit exceeded."},
    },
)
async def list_public_graphics(
    request: Request,
    limit: int = Query(default=12, ge=1, le=50, description="Items per page (max 50)."),
    offset: int = Query(default=0, ge=0, description="Number of items to skip."),
    sort: Literal["newest", "oldest", "score"] = Query(
        default="newest",
        description="Sort order: newest, oldest, or score.",
    ),
    repo: PublicationRepository = Depends(_get_repo),
    storage: StorageInterface = Depends(_get_storage),
    limiter: InMemoryRateLimiter = Depends(get_gallery_limiter),
) -> JSONResponse:
    """Return a paginated list of published infographics.

    This is a **public** endpoint — no authentication required.
    Rate-limited to 30 requests per minute per client IP.

    Query Parameters
    ----------------
    limit:
        Number of items to return (1–50, default 12).
    offset:
        Number of items to skip (default 0).
    sort:
        Sort order (``newest``, ``oldest``, ``score``). Default: ``newest``.

    Returns
    -------
    PaginatedGraphicsResponse
        A JSON object with ``items``, ``limit``, and ``offset``.
    """
    # --- Rate limiting ---
    client_ip: str = request.client.host if request.client else "unknown"
    if not limiter.is_allowed(client_ip):
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"detail": "Rate limit exceeded. Try again later."},
        )

    # --- Fetch published publications ---
    publications = await repo.get_published_sorted(
        limit=limit, offset=offset, sort=sort
    )

    # --- Build response with presigned URLs ---
    items: list[dict] = []
    for pub in publications:
        preview_url = ""
        if pub.s3_key_lowres:
            preview_url = await storage.generate_presigned_url(
                pub.s3_key_lowres, ttl=3600
            )

        items.append(
            PublicationResponse(
                id=pub.id,
                headline=pub.headline,
                chart_type=pub.chart_type,
                virality_score=pub.virality_score or 0.0,
                preview_url=preview_url,
                created_at=pub.created_at,
            ).model_dump(mode="json")
        )

    body = PaginatedGraphicsResponse(
        items=items,  # type: ignore[arg-type]
        limit=limit,
        offset=offset,
    )

    return JSONResponse(
        content=body.model_dump(mode="json"),
        status_code=status.HTTP_200_OK,
        headers={"Cache-Control": "public, max-age=3600"},
    )
