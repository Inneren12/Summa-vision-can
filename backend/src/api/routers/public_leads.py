"""Public lead capture endpoint (D-2, A1+A3, D-3 scoring/notifications/ESP).

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
11. Background: Score lead, notify Slack, sync ESP (D-3).
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.api.schemas.public_leads import LeadCaptureRequest, LeadCaptureResponse
from src.core.config import Settings, get_settings
from src.core.database import get_db, get_session_factory
from src.core.exceptions import ESPPermanentError, ESPTransientError
from src.core.security.ip_rate_limiter import InMemoryRateLimiter
from src.models.lead import Lead
from src.models.publication import PublicationStatus
from src.repositories.download_token_repository import DownloadTokenRepository
from src.repositories.lead_repository import LeadRepository
from src.repositories.publication_repository import PublicationRepository
from src.schemas.events import EventType
from src.services.audit import AuditWriter
from src.services.crm.scoring import LeadScoringService
from src.services.email.esp_client import ESPSubscriberInterface, BeehiivClient
from src.services.email.interface import EmailServiceInterface, ConsoleEmailService
from src.services.notifications.slack import SlackNotifierService
from src.services.security.turnstile import TurnstileValidator

logger = structlog.get_logger(module="public_leads")

router = APIRouter(prefix="/api/v1/public/leads", tags=["public-leads"])

# 3 requests per minute per IP — tight to prevent bot abuse
_lead_rate_limiter = InMemoryRateLimiter(max_requests=3, window_seconds=60)

# Resend rate limiter: 1 resend per 2 minutes per IP (A3)
_resend_rate_limiter = InMemoryRateLimiter(max_requests=1, window_seconds=120)

# Email template path
_EMAIL_TEMPLATE_PATH = Path(__file__).resolve().parents[2] / "templates" / "email" / "download_ready.html"


_scoring_service = LeadScoringService()


def _get_email_service() -> EmailServiceInterface:
    """Provide an EmailServiceInterface via dependency injection."""
    return ConsoleEmailService()


def _get_slack_notifier(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> SlackNotifierService:
    """Provide a SlackNotifierService via dependency injection."""
    return SlackNotifierService(
        http_client=request.app.state.http_client,
        settings=settings,
    )


def _get_esp_client(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> ESPSubscriberInterface | None:
    """Provide an ESP client via dependency injection.

    Returns ``None`` when Beehiiv credentials are not configured.
    """
    if not settings.BEEHIIV_API_KEY or not settings.BEEHIIV_PUBLICATION_ID:
        return None
    return BeehiivClient.from_settings(
        http_client=request.app.state.http_client,
        settings=settings,
    )


def _get_turnstile_validator(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> TurnstileValidator:
    """Provide a TurnstileValidator via dependency injection.

    Uses the app-scoped ``httpx.AsyncClient`` stored on ``app.state``
    for connection reuse and proper lifecycle management.
    """
    return TurnstileValidator(
        secret_key=settings.turnstile_secret_key,
        http_client=request.app.state.http_client,
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


async def _score_notify_sync(
    lead_id: int,
    email: str,
    session_factory: async_sessionmaker,
    slack: SlackNotifierService,
    esp_client: ESPSubscriberInterface | None,
) -> None:
    """Background task: score lead, notify Slack, sync ESP (D-3).

    Creates its own database sessions via *session_factory* so that it
    is fully decoupled from the request-scoped session lifecycle.

    Idempotent (R16): dedupe_key prevents duplicate Slack messages,
    and ESP duplicate-subscriber rejection is handled gracefully.
    """
    # 1. Score the lead (pure function — no I/O)
    score = _scoring_service.score_lead(email)

    # 2. Update lead record with scoring data (own session)
    async with session_factory() as session:
        lead = await session.get(Lead, lead_id)
        if lead is None:
            logger.warning("score_notify_sync_lead_not_found", lead_id=lead_id)
            return

        lead.is_b2b = score.is_b2b
        lead.company_domain = score.company_domain
        lead.category = score.category

        # Audit: lead scored
        audit = AuditWriter(session)
        await audit.log_event(
            event_type=EventType.LEAD_SCORED,
            entity_type="lead",
            entity_id=str(lead_id),
            metadata={"category": score.category, "is_b2b": score.is_b2b},
            actor="system",
        )

        await session.commit()

    # 3. Tiered Slack handling (no session needed)
    if score.category in ("b2b", "education"):
        await slack.notify_lead(
            email=email,
            category=score.category,
            company_domain=score.company_domain,
            dedupe_key=f"capture:{email}",
        )
    # isp → no Slack; b2c → no additional action

    # 4. ESP sync (own session for status update)
    if esp_client is not None:
        async with session_factory() as session:
            lead = await session.get(Lead, lead_id)
            if lead is None:
                logger.warning("esp_sync_lead_not_found", lead_id=lead_id)
                return

            audit = AuditWriter(session)
            try:
                await esp_client.add_subscriber(
                    email,
                    metadata={"category": score.category, "company_domain": score.company_domain or ""},
                )
                if score.category == "b2b":
                    await esp_client.add_tag(email, "b2b")
                elif score.category == "education":
                    await esp_client.add_tag(email, "education")
                lead.esp_synced = True

                await audit.log_event(
                    event_type=EventType.LEAD_ESP_SYNCED,
                    entity_type="lead",
                    entity_id=str(lead_id),
                    actor="system",
                )
            except ESPPermanentError as exc:
                lead.esp_sync_failed_permanent = True
                logger.warning("esp_sync_permanent_failure", email=email, lead_id=lead_id)

                await audit.log_event(
                    event_type=EventType.LEAD_ESP_FAILED,
                    entity_type="lead",
                    entity_id=str(lead_id),
                    metadata={"error": str(exc), "permanent": True},
                    actor="system",
                )
            except ESPTransientError:
                lead.esp_synced = False
                logger.warning("esp_sync_transient_failure", email=email, lead_id=lead_id)

            await session.commit()


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
    session_factory: async_sessionmaker = Depends(get_session_factory),
    settings: Settings = Depends(get_settings),
    turnstile: TurnstileValidator = Depends(_get_turnstile_validator),
    email_service: EmailServiceInterface = Depends(_get_email_service),
    slack_notifier: SlackNotifierService = Depends(_get_slack_notifier),
    esp_client: ESPSubscriberInterface | None = Depends(_get_esp_client),
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

    # 4. Race-safe lead get-or-create (handles concurrent requests for same
    #    email+asset without hitting an unhandled IntegrityError).
    is_b2b = not any(
        payload.email.lower().endswith(f"@{d}")
        for d in (
            "gmail.com", "yahoo.com", "outlook.com", "hotmail.com",
            "protonmail.com", "icloud.com",
        )
    )
    company_domain = payload.email.split("@")[1] if "@" in payload.email else None

    lead, is_new = await lead_repo.get_or_create(
        email=payload.email,
        ip_address=client_ip,
        asset_id=str(payload.asset_id),
        is_b2b=is_b2b,
        company_domain=company_domain,
        utm_source=payload.utm_source,
        utm_medium=payload.utm_medium,
        utm_campaign=payload.utm_campaign,
        utm_content=payload.utm_content,
    )

    if not is_new:
        # Resend flow: revoke old token, create fresh token, send new email.
        # Raw token is not recoverable from hash, so we always create a new one.

        # Resend rate limit (A3): 1 resend per 2 min per IP
        if not _resend_rate_limiter.is_allowed(client_ip):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please try again later.",
            )

        existing_token = await token_repo.get_by_lead_and_asset(lead.id)

        if existing_token is not None:
            await token_repo.revoke(existing_token.id)

        raw_token = secrets.token_urlsafe(32)
        token_hash = _hash_token(raw_token)
        new_token = await token_repo.create(
            lead_id=lead.id,
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
            entity_id=str(lead.id),
            actor="system",
        )
        await audit.log_event(
            event_type=EventType.TOKEN_CREATED,
            entity_type="download_token",
            entity_id=str(new_token.id),
            actor="system",
        )

        return LeadCaptureResponse(message="Check your email for the download link")

    # 5. New lead flow — generate download token, send email, audit events.

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

    # 11. Background: score lead, notify Slack, sync ESP (D-3)
    background_tasks.add_task(
        _score_notify_sync,
        lead_id=lead.id,
        email=payload.email,
        session_factory=session_factory,
        slack=slack_notifier,
        esp_client=esp_client,
    )

    # 10. Return success
    return LeadCaptureResponse(message="Check your email for the download link")
