"""Public sponsorship inquiry endpoint (D-3, PR-37/38).

Allows potential sponsors to submit inquiries. Leads are classified
by email domain:
- B2B → accepted, Slack notified with full details.
- Education → accepted, Slack notified with [EDUCATION] tag.
- ISP → accepted, saved to DB only (low priority).
- B2C → rejected with 422 (must use corporate email).
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import Settings, get_settings
from src.core.database import get_db
from src.core.security.ip_rate_limiter import InMemoryRateLimiter
from src.repositories.lead_repository import LeadRepository
from src.schemas.events import EventType
from src.services.audit import AuditWriter
from src.services.crm.scoring import LeadScoringService
from src.services.notifications.slack import SlackNotifierService

logger = structlog.get_logger(module="public_sponsorship")

router = APIRouter(prefix="/api/v1/public/sponsorship", tags=["public-sponsorship"])

# 1 request per 5 minutes per IP
_sponsorship_rate_limiter = InMemoryRateLimiter(max_requests=1, window_seconds=300)

_scoring_service = LeadScoringService()


class SponsorshipInquiryRequest(BaseModel):
    """Request body for sponsorship inquiries."""

    name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    budget: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=10, max_length=2000)


class SponsorshipInquiryResponse(BaseModel):
    """Response for accepted sponsorship inquiries."""

    message: str = "Thank you for your inquiry. Our team will be in touch."


def _get_client_ip(request: Request) -> str:
    """Extract client IP, respecting X-Forwarded-For if behind a proxy."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _get_slack_notifier(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> SlackNotifierService:
    """Provide a SlackNotifierService via dependency injection."""
    return SlackNotifierService(
        http_client=request.app.state.http_client,
        settings=settings,
    )


@router.post(
    "/inquire",
    response_model=SponsorshipInquiryResponse,
    status_code=status.HTTP_200_OK,
)
async def sponsorship_inquire(
    payload: SponsorshipInquiryRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    slack: SlackNotifierService = Depends(_get_slack_notifier),
) -> SponsorshipInquiryResponse:
    """Submit a sponsorship inquiry.

    Rate limited to 1 request per 5 minutes per IP.
    B2C emails are rejected with 422.
    """
    client_ip = _get_client_ip(request)

    # Rate limit
    if not _sponsorship_rate_limiter.is_allowed(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please try again later.",
        )

    # Score email
    score = _scoring_service.score_lead(payload.email)

    # B2C → reject
    if score.category == "b2c":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Please use your corporate email address for sponsorship inquiries.",
        )

    # Save inquiry to DB as a lead
    lead_repo = LeadRepository(db)
    lead, _ = await lead_repo.get_or_create(
        email=payload.email,
        ip_address=client_ip,
        asset_id="sponsorship_inquiry",
        is_b2b=score.is_b2b,
        company_domain=score.company_domain,
    )

    # Audit
    audit = AuditWriter(db)
    await audit.log_event(
        event_type=EventType.SPONSORSHIP_INQUIRY,
        entity_type="lead",
        entity_id=str(lead.id),
        metadata={
            "name": payload.name,
            "budget": payload.budget,
            "category": score.category,
        },
        actor="system",
    )

    # Tiered Slack handling
    if score.category in ("b2b", "education"):
        await slack.notify_lead(
            email=payload.email,
            category=score.category,
            company_domain=score.company_domain,
            context={
                "name": payload.name,
                "budget": payload.budget,
                "message": payload.message,
            },
            dedupe_key=f"inquiry:{payload.email}",
        )
    # isp → no Slack notification (saved to DB above)

    logger.info(
        "sponsorship_inquiry_received",
        email=payload.email,
        category=score.category,
    )

    return SponsorshipInquiryResponse()
