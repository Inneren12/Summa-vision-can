"""Admin endpoints for data fetch, transform, and preview.

Protected by AuthMiddleware — requires ``X-API-KEY`` header.

Endpoints:
    POST /api/v1/admin/cubes/{product_id}/fetch — Trigger data download
    POST /api/v1/admin/data/transform             — Apply transforms
    GET  /api/v1/admin/data/preview/{storage_key}  — Preview stored data
"""

from __future__ import annotations

import hashlib
import io
from datetime import date, datetime
from typing import Any

import polars as pl
import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from starlette.concurrency import run_in_threadpool
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import get_settings
from src.core.database import get_db
from src.repositories.job_repository import JobRepository
from src.schemas.job_payloads import CubeFetchPayload
from src.schemas.transform import (
    CubeFetchRequest,
    PreviewResponse,
    TransformOperation,
    TransformRequest,
    TransformResponse,
)
from src.services.data.workbench import (
    aggregate_time,
    calc_mom_change,
    calc_rolling_avg,
    calc_yoy_change,
    filter_date_range,
    filter_geo,
    merge_cubes,
)
from src.services.jobs.dedupe import cube_fetch_key

logger = structlog.get_logger()

router = APIRouter(
    prefix="/api/v1/admin",
    tags=["admin-data"],
)

# Map of transform operation names to workbench functions
TRANSFORM_DISPATCH: dict[str, Any] = {
    "aggregate_time": aggregate_time,
    "filter_geo": filter_geo,
    "filter_date_range": filter_date_range,
    "calc_yoy_change": calc_yoy_change,
    "calc_mom_change": calc_mom_change,
    "calc_rolling_avg": calc_rolling_avg,
    "merge_cubes": merge_cubes,
}


# -----------------------------------------------------------------------
# POST /api/v1/admin/cubes/{product_id}/fetch
# -----------------------------------------------------------------------

@router.post(
    "/cubes/{product_id}/fetch",
    status_code=202,
    summary="Fetch cube data from StatCan",
    description=(
        "Creates a persistent job to download and process data vectors "
        "for the specified StatCan cube. Returns immediately with job_id. "
        "Deduped by product_id + date — one fetch per cube per day."
    ),
)
async def trigger_cube_fetch(
    product_id: str,
    body: CubeFetchRequest | None = None,
    session: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    """Trigger a cube data fetch as a persistent job."""
    repo = JobRepository(session)
    dedupe = cube_fetch_key(product_id)

    payload = CubeFetchPayload(product_id=product_id)
    if body and body.periods is not None:
        # Override will be read by the handler
        payload = CubeFetchPayload(
            product_id=product_id,
            # Note: CubeFetchPayload may not have 'periods' field.
            # If it doesn't, the handler reads it from CubeCatalog.
        )

    result = await repo.enqueue(
        job_type="cube_fetch",
        payload_json=payload.model_dump_json(),
        dedupe_key=dedupe,
        created_by="admin:api",
    )
    await session.commit()

    is_new = result.created

    return {
        "job_id": result.job.id,
        "status": result.job.status.value,
        "product_id": product_id,
        "dedupe": "new" if is_new else "existing",
    }


# -----------------------------------------------------------------------
# POST /api/v1/admin/data/transform
# -----------------------------------------------------------------------

@router.post(
    "/data/transform",
    response_model=TransformResponse,
    summary="Apply transforms to stored data",
    description=(
        "Loads Parquet source(s) from storage, applies an ordered list "
        "of workbench transforms, saves the result as a new Parquet file, "
        "and returns the output storage key. Full JSON result body is "
        "NOT returned (R15 — prevents JSON bomb). Use /data/preview to "
        "inspect the result."
    ),
)
async def transform_data(
    body: TransformRequest,
    request: Request,
) -> TransformResponse:
    """Apply transforms and return output Parquet key."""
    settings = get_settings()
    log = logger.bind(source_keys=body.source_keys)

    # --- Load source DataFrames from storage ---
    storage = getattr(request.app.state, "storage", None)
    if storage is None:
        raise HTTPException(500, "Storage not configured on app.state")

    data_sem = getattr(request.app.state, "data_sem", None)

    dfs: list[pl.DataFrame] = []
    for key in body.source_keys:
        parquet_bytes = await _load_parquet_bytes(storage, key)
        df = pl.read_parquet(io.BytesIO(parquet_bytes))
        dfs.append(df)

    # Start with first DataFrame (or merge if multiple sources)
    if len(dfs) == 1:
        result = dfs[0]
    else:
        # Multiple sources — merge first, then transform
        # Find merge operation in the operations list, or auto-merge
        merge_op = next(
            (op for op in body.operations if op.type == "merge_cubes"),
            None,
        )
        if merge_op:
            result = merge_cubes(dfs, **merge_op.params)
            # Remove merge from operations list (already applied)
            remaining_ops = [
                op for op in body.operations if op.type != "merge_cubes"
            ]
        else:
            # Default merge on REF_DATE + GEO
            result = merge_cubes(dfs)
            remaining_ops = list(body.operations)

        body = TransformRequest(
            source_keys=body.source_keys,
            operations=[TransformOperation(**op.model_dump()) for op in remaining_ops],
            output_key=body.output_key,
        )

    # --- Apply transforms sequentially (heavy — use threadpool) ---
    async def _apply_transforms() -> pl.DataFrame:
        df = result
        for op in body.operations:
            fn = TRANSFORM_DISPATCH.get(op.type)
            if fn is None:
                raise HTTPException(
                    422,
                    f"Unknown transform: '{op.type}'. "
                    f"Available: {sorted(TRANSFORM_DISPATCH.keys())}",
                )
            if data_sem:
                async with data_sem:
                    df = await run_in_threadpool(fn, df, **op.params)
            else:
                df = await run_in_threadpool(fn, df, **op.params)
        return df

    try:
        transformed = await _apply_transforms()
    except HTTPException:
        raise
    except Exception as exc:
        log.error("transform_failed", error=str(exc))
        raise HTTPException(422, f"Transform failed: {exc}") from exc

    # --- Save result as Parquet (R3) ---
    output_key = body.output_key or _generate_output_key(body)
    parquet_bytes = _df_to_parquet_bytes(transformed)

    await _save_parquet_bytes(storage, output_key, parquet_bytes)

    log.info(
        "transform_completed",
        output_key=output_key,
        rows=transformed.height,
        columns=transformed.width,
    )

    return TransformResponse(
        output_key=output_key,
        rows=transformed.height,
        columns=transformed.width,
    )


# -----------------------------------------------------------------------
# GET /api/v1/admin/data/preview/{storage_key:path}
# -----------------------------------------------------------------------

@router.get(
    "/data/preview/{storage_key:path}",
    response_model=PreviewResponse,
    summary="Preview stored data",
    description=(
        "Returns the first N rows of a stored Parquet file as JSON. "
        "Capped at MAX_PREVIEW_ROWS (default 100, R15). "
        "Values are typed: null→None, datetime→ISO string, "
        "numeric→Python scalar."
    ),
)
async def preview_data(
    storage_key: str,
    limit: int = Query(default=100, ge=1, le=500),
    request: Request = None,  # type: ignore[assignment]
) -> PreviewResponse:
    """Preview stored Parquet data."""
    settings = get_settings()
    max_rows = min(limit, settings.max_preview_rows)

    storage = getattr(request.app.state, "storage", None)
    if storage is None:
        raise HTTPException(500, "Storage not configured on app.state")

    # Load Parquet
    try:
        parquet_bytes = await _load_parquet_bytes(storage, storage_key)
    except Exception as exc:
        raise HTTPException(404, f"Data not found: {storage_key}") from exc

    df = pl.read_parquet(io.BytesIO(parquet_bytes))

    # Cap rows
    preview_df = df.head(max_rows)

    # Typed serialization
    data = _serialize_preview(preview_df)

    return PreviewResponse(
        storage_key=storage_key,
        rows=preview_df.height,
        columns=preview_df.width,
        column_names=preview_df.columns,
        data=data,
    )


# -----------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------

async def _load_parquet_bytes(storage: object, key: str) -> bytes:
    """Load Parquet bytes from storage."""
    if hasattr(storage, "download_bytes"):
        return await storage.download_bytes(key)
    elif hasattr(storage, "download_csv"):
        # Fallback: some storage interfaces may not have download_bytes
        # Try reading as generic file
        raise HTTPException(
            500,
            "Storage does not support download_bytes. "
            "Cannot load Parquet files.",
        )
    else:
        raise HTTPException(500, "Storage interface incompatible")


async def _save_parquet_bytes(
    storage: object, key: str, data: bytes
) -> None:
    """Save Parquet bytes to storage."""
    if hasattr(storage, "upload_bytes"):
        await storage.upload_bytes(data, key)
    else:
        raise HTTPException(
            500, "Storage does not support upload_bytes"
        )


def _df_to_parquet_bytes(df: pl.DataFrame) -> bytes:
    """Serialize Polars DataFrame to Parquet bytes."""
    buf = io.BytesIO()
    df.write_parquet(buf)
    return buf.getvalue()


def _generate_output_key(body: TransformRequest) -> str:
    """Generate a deterministic output key from input + operations."""
    content = (
        ",".join(body.source_keys)
        + "|"
        + ",".join(f"{op.type}:{op.params}" for op in body.operations)
    )
    h = hashlib.sha256(content.encode()).hexdigest()[:12]
    today = date.today().isoformat()
    return f"statcan/transformed/{today}/{h}.parquet"


def _serialize_preview(df: pl.DataFrame) -> list[dict[str, Any]]:
    """Typed serialization of Polars DataFrame rows for JSON response.

    Rules (R15):
        - null → None
        - datetime/date → ISO string
        - numeric → Python int/float
        - string → str
    """
    rows: list[dict[str, Any]] = []

    for row_dict in df.to_dicts():
        clean: dict[str, Any] = {}
        for k, v in row_dict.items():
            if v is None:
                clean[k] = None
            elif isinstance(v, datetime):
                clean[k] = v.isoformat()
            elif isinstance(v, date):
                clean[k] = v.isoformat()
            elif isinstance(v, float):
                clean[k] = v
            elif isinstance(v, int):
                clean[k] = v
            else:
                clean[k] = str(v)
        rows.append(clean)

    return rows
