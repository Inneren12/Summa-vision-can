"""Public lead capture endpoint (D-2, A1+A3).

Flow:
1. Rate limit per IP (3 req/min).
2. Validate Turnstile CAPTCHA.
3. Validate asset exists and is PUBLISHED.
4. Check lead deduplication (resend logic R17).
5. Save lead to DB immediately (no data loss on ESP failure).
6. Generate download token (SHA-256 hash only in DB).
7. Build Magic Link to frontend /downloading page.
8. Send email via BackgroundTasks.
9. Write AuditEvents.
10. Return 200 with message.
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas.public_leads import LeadCaptureRequest, LeadCaptureResponse
from src.core.config import Settings, get_settings
from src.core.database import get_db
from src.core.security.ip_rate_limiter import InMemoryRateLimiter
from src.models.publication import PublicationStatus
from src.repositories.download_token_repository import DownloadTokenRepository
from src.repositories.lead_repository import LeadRepository
from src.repositories.publication_repository import PublicationRepository
from src.schemas.events import EventType
from src.services.audit import AuditWriter
from src.services.email.interface import EmailServiceInterface, ConsoleEmailService
from src.services.security.turnstile import TurnstileValidator

logger = structlog.get_logger(module="public_leads")

router = APIRouter(prefix="/api/v1/public/leads", tags=["public-leads"])

# 3 requests per minute per IP — tight to prevent bot abuse
_lead_rate_limiter = InMemoryRateLimiter(max_requests=3, window_seconds=60)

# Resend rate limiter: 1 resend per 2 minutes per IP (A3)
_resend_rate_limiter = InMemoryRateLimiter(max_requests=1, window_seconds=120)

# Email template path
_EMAIL_TEMPLATE_PATH = Path(__file__).resolve().parents[2] / "templates" / "email" / "download_ready.html"


def _get_email_service() -> EmailServiceInterface:
    """Provide an EmailServiceInterface via dependency injection."""
    return ConsoleEmailService()


def _get_turnstile_validator(
    settings: Settings = Depends(get_settings),
) -> TurnstileValidator:
    """Provide a TurnstileValidator via dependency injection."""
    import httpx

    return TurnstileValidator(
        secret_key=settings.turnstile_secret_key,
        http_client=httpx.AsyncClient(),
    )


def _get_client_ip(request: Request) -> str:
    """Extract client IP, respecting X-Forwarded-For if behind a proxy."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _build_email_body(
    magic_link: str,
    headline: str,
    thumbnail_url: str,
    expires_hours: int,
) -> str:
    """Build HTML email body from template."""
    template = _EMAIL_TEMPLATE_PATH.read_text(encoding="utf-8")
    return (
        template
        .replace("{magic_link}", magic_link)
        .replace("{headline}", headline)
        .replace("{thumbnail_url}", thumbnail_url)
        .replace("{expires_hours}", str(expires_hours))
    )


def _hash_token(raw_token: str) -> str:
    """Return the SHA-256 hex digest of a raw token string."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


@router.post(
    "/capture",
    response_model=LeadCaptureResponse,
    status_code=status.HTTP_200_OK,
)
async def capture_lead(
    payload: LeadCaptureRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    turnstile: TurnstileValidator = Depends(_get_turnstile_validator),
    email_service: EmailServiceInterface = Depends(_get_email_service),
) -> LeadCaptureResponse:
    """Trade email for a Magic Link download email.

    Rate limited to 3 req/min per IP.
    Lead is saved to DB before any external service calls.
    """
    client_ip = _get_client_ip(request)

    # 1. Rate limit
    if not _lead_rate_limiter.is_allowed(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please try again later.",
        )

    # 2. Validate Turnstile CAPTCHA
    turnstile_valid = await turnstile.validate(payload.turnstile_token, client_ip)
    if not turnstile_valid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CAPTCHA verification failed",
        )

    pub_repo = PublicationRepository(db)
    lead_repo = LeadRepository(db)
    token_repo = DownloadTokenRepository(db)
    audit = AuditWriter(db)

    # 3. Validate asset exists and is published
    publication = await pub_repo.get_by_id(payload.asset_id)
    if publication is None or publication.status != PublicationStatus.PUBLISHED:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found or not yet published",
        )

    s3_key = publication.s3_key_highres or publication.s3_key_lowres
    if not s3_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset file not available yet",
        )

    # 4. Check lead deduplication
    existing_lead = await lead_repo.get_by_email_and_asset(
        payload.email, str(payload.asset_id)
    )

    if existing_lead is not None:
        # Resend rate limit (A3): 1 resend per 2 min per IP
        if not _resend_rate_limiter.is_allowed(client_ip):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please try again later.",
            )

        existing_token = await token_repo.get_by_lead_and_asset(existing_lead.id)

        if existing_token is not None and existing_token.use_count == 0:
            # Reuse existing token (R17 resend logic)
            raw_token = secrets.token_urlsafe(32)
            token_hash = _hash_token(raw_token)

            # We can't recover the raw token from the hash, so we must
            # revoke old and create new for the magic link
            await token_repo.revoke(existing_token.id)
            new_token = await token_repo.create(
                lead_id=existing_lead.id,
                token_hash=token_hash,
                expires_at=datetime.now(timezone.utc) + timedelta(hours=settings.magic_token_ttl_hours),
                max_uses=settings.max_token_uses,
            )
        elif existing_token is not None and existing_token.use_count > 0:
            # Token already used — revoke and create new
            await token_repo.revoke(existing_token.id)
            raw_token = secrets.token_urlsafe(32)
            token_hash = _hash_token(raw_token)
            new_token = await token_repo.create(
                lead_id=existing_lead.id,
                token_hash=token_hash,
                expires_at=datetime.now(timezone.utc) + timedelta(hours=settings.magic_token_ttl_hours),
                max_uses=settings.max_token_uses,
            )
        else:
            # No existing token — create new
            raw_token = secrets.token_urlsafe(32)
            token_hash = _hash_token(raw_token)
            new_token = await token_repo.create(
                lead_id=existing_lead.id,
                token_hash=token_hash,
                expires_at=datetime.now(timezone.utc) + timedelta(hours=settings.magic_token_ttl_hours),
                max_uses=settings.max_token_uses,
            )

        # Build and send Magic Link email
        magic_link = f"{settings.public_site_url}/downloading?token={raw_token}"
        cdn_url = f"{settings.cdn_base_url}/{publication.s3_key_lowres}" if publication.s3_key_lowres else ""
        html_body = _build_email_body(
            magic_link=magic_link,
            headline=publication.headline,
            thumbnail_url=cdn_url,
            expires_hours=settings.magic_token_ttl_hours,
        )

        background_tasks.add_task(
            email_service.send_email,
            to=payload.email,
            subject="Your Summa Vision Download",
            html_body=html_body,
        )

        await audit.log_event(
            event_type=EventType.LEAD_EMAIL_SENT,
            entity_type="lead",
            entity_id=str(existing_lead.id),
            actor="system",
        )
        await audit.log_event(
            event_type=EventType.TOKEN_CREATED,
            entity_type="download_token",
            entity_id=str(new_token.id),
            actor="system",
        )

        return LeadCaptureResponse(message="Check your email for the download link")

    # 5. Save lead to DB IMMEDIATELY
    is_b2b = not any(
        payload.email.lower().endswith(f"@{d}")
        for d in (
            "gmail.com", "yahoo.com", "outlook.com", "hotmail.com",
            "protonmail.com", "icloud.com",
        )
    )
    company_domain = payload.email.split("@")[1] if "@" in payload.email else None

    lead = await lead_repo.create(
        email=payload.email,
        ip_address=client_ip,
        asset_id=str(payload.asset_id),
        is_b2b=is_b2b,
        company_domain=company_domain,
    )

    # 6. Generate download token
    raw_token = secrets.token_urlsafe(32)
    token_hash = _hash_token(raw_token)
    download_token = await token_repo.create(
        lead_id=lead.id,
        token_hash=token_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=settings.magic_token_ttl_hours),
        max_uses=settings.max_token_uses,
    )

    # 7. Build Magic Link
    magic_link = f"{settings.public_site_url}/downloading?token={raw_token}"

    # 8. Send email via BackgroundTasks
    cdn_url = f"{settings.cdn_base_url}/{publication.s3_key_lowres}" if publication.s3_key_lowres else ""
    html_body = _build_email_body(
        magic_link=magic_link,
        headline=publication.headline,
        thumbnail_url=cdn_url,
        expires_hours=settings.magic_token_ttl_hours,
    )

    background_tasks.add_task(
        email_service.send_email,
        to=payload.email,
        subject="Your Summa Vision Download",
        html_body=html_body,
    )

    logger.info(
        "lead.captured",
        email=payload.email,
        asset_id=payload.asset_id,
        is_b2b=is_b2b,
    )

    # 9. Write AuditEvents
    await audit.log_event(
        event_type=EventType.LEAD_CAPTURED,
        entity_type="lead",
        entity_id=str(lead.id),
        metadata={"email_domain": company_domain, "asset_id": payload.asset_id},
        actor="system",
    )
    await audit.log_event(
        event_type=EventType.LEAD_EMAIL_SENT,
        entity_type="lead",
        entity_id=str(lead.id),
        actor="system",
    )
    await audit.log_event(
        event_type=EventType.TOKEN_CREATED,
        entity_type="download_token",
        entity_id=str(download_token.id),
        actor="system",
    )

    # 10. Return success
    return LeadCaptureResponse(message="Check your email for the download link")
