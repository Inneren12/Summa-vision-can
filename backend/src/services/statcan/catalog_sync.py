"""CatalogSyncService — downloads and syncs the full StatCan cube catalog.

Architecture decisions:
    R7  — Sync runs as a persistent DB-backed job.
    R16 — Idempotent: re-running sync for same day updates existing records.

StatCan API endpoint:
    GET https://www150.statcan.gc.ca/t1/tbl1/en/dtl!getAllCubesList
    Returns: JSON array of ~7000 cube metadata objects.
"""

from __future__ import annotations

from dataclasses import dataclass

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.cube_catalog_repository import CubeCatalogRepository
from src.schemas.cube_catalog import CubeCatalogCreate
from src.schemas.statcan_catalog import StatCanCubeListItem, FREQUENCY_MAP

logger = structlog.get_logger()

STATCAN_ALL_CUBES_URL = (
    "https://www150.statcan.gc.ca/t1/tbl1/en/dtl!getAllCubesList"
)


@dataclass
class SyncReport:
    """Result of a catalog sync operation."""

    total: int
    new: int
    updated: int
    errors: int


class CatalogSyncService:
    """Downloads the full StatCan cube catalog and syncs to DB.

    Args:
        http_client: Any async HTTP client with a ``.get(url)`` method
            that returns a response with ``.json()`` and ``.raise_for_status()``.
            Typically StatCanClient or httpx.AsyncClient.
        repo: CubeCatalogRepository for database operations.
    """

    def __init__(
        self,
        http_client: object,
        repo: CubeCatalogRepository,
    ) -> None:
        self._http_client = http_client
        self._repo = repo

    async def sync_full_catalog(self) -> SyncReport:
        """Download all cubes from StatCan and upsert into DB.

        Returns:
            SyncReport with counts of total, new, updated, errors.
        """
        logger.info("catalog_sync_started")

        # Step 1: Fetch from StatCan API
        raw_cubes = await self._fetch_cube_list()
        total_fetched = len(raw_cubes)
        logger.info("catalog_sync_fetched", count=total_fetched)

        # Step 2: Parse into internal schema
        parsed_cubes: list[CubeCatalogCreate] = []
        errors = 0

        for i, raw in enumerate(raw_cubes):
            try:
                item = StatCanCubeListItem.model_validate(raw)
                parsed_cubes.append(self._to_catalog_create(item))
            except Exception as exc:
                errors += 1
                if errors <= 10:
                    logger.warning(
                        "catalog_sync_parse_error",
                        index=i,
                        error=str(exc),
                    )

            # Progress logging every 1000 cubes
            if (i + 1) % 1000 == 0:
                logger.info(
                    "catalog_sync_progress",
                    processed=i + 1,
                    total=total_fetched,
                )

        logger.info(
            "catalog_sync_parsed",
            parsed=len(parsed_cubes),
            errors=errors,
        )

        # Step 3: Count before upsert (for new vs updated calculation)
        count_before = await self._repo.count()

        # Step 4: Batch upsert
        upserted = await self._repo.upsert_batch(parsed_cubes)

        count_after = await self._repo.count()
        new_count = max(0, count_after - count_before)
        updated_count = max(0, upserted - new_count)

        report = SyncReport(
            total=total_fetched,
            new=new_count,
            updated=updated_count,
            errors=errors,
        )

        logger.info(
            "catalog_sync_completed",
            total=report.total,
            new=report.new,
            updated=report.updated,
            errors=report.errors,
        )

        return report

    async def _fetch_cube_list(self) -> list[dict]:
        """Fetch raw cube list JSON from StatCan API."""
        if hasattr(self._http_client, "request"):
            response = await self._http_client.request(
                "GET", STATCAN_ALL_CUBES_URL
            )
        elif hasattr(self._http_client, "get"):
            response = await self._http_client.get(STATCAN_ALL_CUBES_URL)
        else:
            raise TypeError(
                f"HTTP client must have .get() or .request() method, "
                f"got {type(self._http_client)}"
            )

        response.raise_for_status()
        data = response.json()

        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            # StatCan might wrap in container
            for key in ("cubes", "data", "results"):
                if key in data and isinstance(data[key], list):
                    return data[key]

        logger.warning(
            "catalog_sync_unexpected_format",
            type=type(data).__name__,
        )
        return data if isinstance(data, list) else []

    @staticmethod
    def _to_catalog_create(item: StatCanCubeListItem) -> CubeCatalogCreate:
        """Convert StatCan API item to internal schema."""
        frequency = FREQUENCY_MAP.get(item.frequency_code)
        if frequency is None:
            frequency = str(item.frequency_code)

        return CubeCatalogCreate(
            product_id=str(item.product_id),
            cube_id_statcan=item.cansim_id,
            title_en=item.cube_title_en,
            title_fr=item.cube_title_fr,
            subject_code=str(item.subject_code),
            subject_en=item.subject_en,
            survey_en=item.survey_en,
            frequency=frequency,
            start_date=item.start_date,
            end_date=item.end_date,
            archive_status=item.archived,
        )
