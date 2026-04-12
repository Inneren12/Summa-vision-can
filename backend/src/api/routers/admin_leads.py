"""Admin lead management endpoints (D-3).

Provides the resync endpoint for retrying failed ESP subscriber pushes
with exponential backoff.

Protected by AuthMiddleware (``/api/v1/admin/*``).
"""

from __future__ import annotations

import asyncio

import structlog
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.exceptions import ESPPermanentError, ESPTransientError
from src.repositories.lead_repository import LeadRepository
from src.services.email.esp_client import ESPSubscriberInterface, BeehiivClient
from src.core.config import Settings, get_settings
from fastapi import Request

logger = structlog.get_logger(module="admin_leads")

router = APIRouter(prefix="/api/v1/admin/leads", tags=["admin-leads"])

_MAX_ATTEMPTS = 3


class ResyncResult(BaseModel):
    """Summary of an ESP resync operation."""

    total: int
    synced: int
    failed_transient: int
    failed_permanent: int


def _get_esp_client(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> ESPSubscriberInterface | None:
    """Provide an ESP client via dependency injection."""
    if not settings.BEEHIIV_API_KEY or not settings.BEEHIIV_PUBLICATION_ID:
        return None
    return BeehiivClient.from_settings(
        http_client=request.app.state.http_client,
        settings=settings,
    )


@router.post("/resync", response_model=ResyncResult)
async def resync_leads(
    db: AsyncSession = Depends(get_db),
    esp_client: ESPSubscriberInterface | None = Depends(_get_esp_client),
) -> ResyncResult:
    """Retry ESP sync for unsynced leads with exponential backoff.

    Fetches up to 100 leads where ``esp_synced=False`` and
    ``esp_sync_failed_permanent=False``, then attempts up to 3 syncs
    per lead with 1s, 2s backoff between retries.
    """
    lead_repo = LeadRepository(db)
    leads = await lead_repo.get_unsynced(limit=100)

    result = ResyncResult(
        total=len(leads),
        synced=0,
        failed_transient=0,
        failed_permanent=0,
    )

    if esp_client is None:
        logger.warning("resync_esp_not_configured")
        result.failed_transient = result.total
        return result

    for lead in leads:
        synced = False

        for attempt in range(_MAX_ATTEMPTS):
            try:
                await esp_client.add_subscriber(
                    lead.email,
                    metadata={"category": "b2b" if lead.is_b2b else "other"},
                )
                await lead_repo.mark_synced(lead.id)
                result.synced += 1
                synced = True
                break
            except ESPPermanentError:
                await lead_repo.mark_permanently_failed(lead.id)
                result.failed_permanent += 1
                synced = True  # handled — don't count as transient
                logger.warning(
                    "resync_permanent_failure",
                    lead_id=lead.id,
                    email=lead.email,
                )
                break
            except ESPTransientError:
                if attempt < _MAX_ATTEMPTS - 1:
                    delay = 2**attempt  # 1s, 2s
                    await asyncio.sleep(delay)
                    logger.info(
                        "resync_retry",
                        lead_id=lead.id,
                        attempt=attempt + 1,
                        delay=delay,
                    )

        if not synced:
            result.failed_transient += 1
            logger.warning(
                "resync_transient_exhausted",
                lead_id=lead.id,
                email=lead.email,
            )

    await db.commit()

    logger.info(
        "resync_complete",
        total=result.total,
        synced=result.synced,
        failed_transient=result.failed_transient,
        failed_permanent=result.failed_permanent,
    )

    return result
