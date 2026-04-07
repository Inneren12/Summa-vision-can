"""Admin endpoints for StatCan cube catalog management.

Protected by AuthMiddleware — requires ``X-API-KEY`` header.

Endpoints:
    GET  /api/v1/admin/cubes/search     — Full-text search with typo tolerance
    POST /api/v1/admin/cubes/sync       — Trigger catalog sync (persistent job)
    GET  /api/v1/admin/cubes/{product_id} — Get full cube metadata
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.repositories.cube_catalog_repository import CubeCatalogRepository
from src.repositories.job_repository import JobRepository
from src.schemas.cube_catalog import CubeCatalogResponse, CubeSearchResult
from src.schemas.job_payloads import CatalogSyncPayload
from src.services.jobs.dedupe import catalog_sync_key

router = APIRouter(
    prefix="/api/v1/admin/cubes",
    tags=["admin-cubes"],
)


# -----------------------------------------------------------------------
# GET /api/v1/admin/cubes/search?q=...&limit=20
# -----------------------------------------------------------------------

@router.get(
    "/search",
    response_model=list[CubeSearchResult],
    summary="Search StatCan cube catalog",
    description=(
        "Full-text search with typo tolerance across English and French "
        "cube titles and subject names. Returns lightweight results "
        "for browsing. Use GET /cubes/{product_id} for full metadata."
    ),
)
async def search_cubes(
    q: str = Query(
        ...,
        min_length=1,
        description="Search query (e.g. 'rental vacancy Alberta')",
    ),
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Maximum results to return",
    ),
    session: AsyncSession = Depends(get_db),
) -> list[CubeSearchResult]:
    """Search the cube catalog.

    Raises:
        422: If ``q`` is empty or missing.
    """
    # Strip whitespace — FastAPI min_length=1 catches empty string,
    # but "   " (whitespace only) would pass. Handle explicitly:
    normalized_q = q.strip()
    if not normalized_q:
        raise HTTPException(
            status_code=422,
            detail="Search query must not be empty or whitespace-only.",
        )

    repo = CubeCatalogRepository(session)
    cubes = await repo.search(normalized_q, limit=limit)

    return [
        CubeSearchResult.model_validate(cube, from_attributes=True)
        for cube in cubes
    ]


# -----------------------------------------------------------------------
# POST /api/v1/admin/cubes/sync
# -----------------------------------------------------------------------

@router.post(
    "/sync",
    status_code=202,
    summary="Trigger catalog sync",
    description=(
        "Creates a persistent job to download and sync the full StatCan "
        "cube catalog (~7000 entries). Returns immediately with job_id. "
        "If a sync for today already exists (queued or running), returns "
        "the existing job instead of creating a duplicate."
    ),
)
async def trigger_catalog_sync(
    session: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    """Trigger a catalog sync as a persistent job.

    Returns:
        202 with ``{"job_id": <int>, "status": "queued", "dedupe": "new"|"existing"}``.
    """
    repo = JobRepository(session)
    dedupe = catalog_sync_key()

    payload = CatalogSyncPayload()

    job, created = await repo.enqueue(
        job_type="catalog_sync",
        payload_json=payload.model_dump_json(),
        dedupe_key=dedupe,
        created_by="admin:api",
    )
    await session.commit()

    return {
        "job_id": job.id,
        "status": job.status.value,
        "dedupe": "new" if created else "existing",
    }


# -----------------------------------------------------------------------
# GET /api/v1/admin/cubes/{product_id}
# -----------------------------------------------------------------------

@router.get(
    "/{product_id}",
    response_model=CubeCatalogResponse,
    summary="Get cube metadata",
    description="Returns full metadata for a single StatCan cube.",
)
async def get_cube(
    product_id: str,
    session: AsyncSession = Depends(get_db),
) -> CubeCatalogResponse:
    """Fetch full cube metadata by product_id.

    Raises:
        404: If cube not found.
    """
    repo = CubeCatalogRepository(session)
    cube = await repo.get_by_product_id(product_id)

    if cube is None:
        raise HTTPException(
            status_code=404,
            detail=f"Cube with product_id '{product_id}' not found.",
        )

    return CubeCatalogResponse.model_validate(cube, from_attributes=True)
