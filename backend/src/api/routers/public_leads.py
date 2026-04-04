"""Public lead capture endpoint.

Flow:
1. Rate limit per IP (3 req/min).
2. Validate asset exists and is PUBLISHED.
3. Save lead to DB immediately (no data loss on ESP failure).
4. Generate presigned URL (TTL 15 min).
5. Return download URL.
"""
from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas.public_leads import LeadCaptureRequest, LeadCaptureResponse
from src.core.database import get_db
from src.core.security.ip_rate_limiter import InMemoryRateLimiter
from src.core.storage import StorageInterface, get_storage_manager
from src.models.publication import PublicationStatus
from src.repositories.lead_repository import LeadRepository
from src.repositories.publication_repository import PublicationRepository

logger = structlog.get_logger(module="public_leads")

router = APIRouter(prefix="/api/v1/public/leads", tags=["public-leads"])

# 3 requests per minute per IP — tight to prevent bot abuse
_lead_rate_limiter = InMemoryRateLimiter(max_requests=3, window_seconds=60)


def _get_storage() -> StorageInterface:
    """Provide a StorageInterface via dependency injection.

    Wraps :func:`get_storage_manager` in a zero-arg function so that
    FastAPI does not attempt to resolve the optional ``settings`` parameter
    as a request body field.
    """
    return get_storage_manager()


def _get_client_ip(request: Request) -> str:
    """Extract client IP, respecting X-Forwarded-For if behind a proxy."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post(
    "/capture",
    response_model=LeadCaptureResponse,
    status_code=status.HTTP_200_OK,
)
async def capture_lead(
    payload: LeadCaptureRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    storage: StorageInterface = Depends(_get_storage),
) -> LeadCaptureResponse:
    """Trade email for a presigned download URL.

    Rate limited to 3 req/min per IP.
    Lead is saved to DB before any external service calls.
    """
    # 1. Rate limit
    client_ip = _get_client_ip(request)
    if not _lead_rate_limiter.is_allowed(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please try again later.",
        )

    pub_repo = PublicationRepository(db)
    lead_repo = LeadRepository(db)

    # 2. Validate asset exists and is published
    publication = await pub_repo.get_by_id(payload.asset_id)
    if publication is None or publication.status != PublicationStatus.PUBLISHED:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found or not yet published",
        )

    # 3. Save lead immediately — before any external call
    is_b2b = not any(
        payload.email.lower().endswith(f"@{d}")
        for d in (
            "gmail.com", "yahoo.com", "outlook.com", "hotmail.com",
            "protonmail.com", "icloud.com",
        )
    )
    company_domain = payload.email.split("@")[1] if "@" in payload.email else None

    await lead_repo.create(
        email=payload.email,
        ip_address=client_ip,
        asset_id=str(payload.asset_id),
        is_b2b=is_b2b,
        company_domain=company_domain,
    )

    logger.info(
        "lead.captured",
        email=payload.email,
        asset_id=payload.asset_id,
        is_b2b=is_b2b,
    )

    # 4. Generate presigned URL (TTL 15 min = 900 seconds)
    s3_key = publication.s3_key_highres or publication.s3_key_lowres
    if not s3_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset file not available yet",
        )

    download_url = await storage.generate_presigned_url(s3_key, ttl=900)

    return LeadCaptureResponse(download_url=download_url)
