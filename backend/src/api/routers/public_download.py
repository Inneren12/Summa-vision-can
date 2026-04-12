"""Public download / token exchange endpoint (D-2, A2).

GET /api/v1/public/download?token=<raw_token>

Exchanges a magic-link token for a presigned S3 URL via 307 redirect.
The token is validated atomically (R17) — no TOCTOU races.
"""
from __future__ import annotations

import hashlib

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import Settings, get_settings
from src.core.database import get_db
from src.core.storage import StorageInterface, get_storage_manager
from src.repositories.download_token_repository import DownloadTokenRepository
from src.repositories.lead_repository import LeadRepository
from src.repositories.publication_repository import PublicationRepository
from src.schemas.events import EventType
from src.services.audit import AuditWriter

logger = structlog.get_logger(module="public_download")

router = APIRouter(prefix="/api/v1/public", tags=["public-download"])


def _get_storage() -> StorageInterface:
    """Provide a StorageInterface via dependency injection."""
    return get_storage_manager()


def _hash_token(raw_token: str) -> str:
    """Return the SHA-256 hex digest of a raw token string."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


@router.get("/download")
async def download_file(
    token: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db),
    storage: StorageInterface = Depends(_get_storage),
    settings: Settings = Depends(get_settings),
) -> RedirectResponse:
    """Exchange a magic-link token for a presigned S3 URL.

    Returns 307 Temporary Redirect to the presigned URL.
    The browser follows the redirect and starts the download.
    """
    token_repo = DownloadTokenRepository(db)
    audit = AuditWriter(db)

    # 1. Hash the incoming token
    token_hash = _hash_token(token)

    # 2. Atomic token usage (R17)
    download_token = await token_repo.activate_atomic(token_hash)

    if download_token is None:
        # 3. Determine error reason for user-friendly messaging
        error_reason = await token_repo.get_error_reason(token_hash)

        if error_reason == "expired":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Download link has expired. Request a new one.",
            )
        elif error_reason == "exhausted":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Download link has been used too many times. Request a new one.",
            )
        elif error_reason == "revoked":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Download link has been revoked.",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid download link",
            )

    # 4. Look up the Lead and Publication
    lead_repo = LeadRepository(db)
    pub_repo = PublicationRepository(db)

    lead = await lead_repo.get_by_id(download_token.lead_id)
    if lead is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid download link",
        )

    publication = await pub_repo.get_by_id(int(lead.asset_id))
    if publication is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found",
        )

    s3_key = publication.s3_key_highres or publication.s3_key_lowres
    if not s3_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset file not available",
        )

    # 5. Generate presigned URL
    presigned_url = await storage.generate_presigned_url(
        s3_key, ttl=settings.signed_url_ttl_minutes * 60
    )

    # 7. Write AuditEvent: token.activated
    await audit.log_event(
        event_type=EventType.TOKEN_ACTIVATED,
        entity_type="download_token",
        entity_id=str(download_token.id),
        metadata={
            "use_count": download_token.use_count,
            "lead_id": download_token.lead_id,
            "asset_id": lead.asset_id,
        },
        actor="system",
    )

    # 8. If this was the last allowed use, also write token.exhausted
    if download_token.use_count >= download_token.max_uses:
        await audit.log_event(
            event_type=EventType.TOKEN_EXHAUSTED,
            entity_type="download_token",
            entity_id=str(download_token.id),
            metadata={
                "use_count": download_token.use_count,
                "max_uses": download_token.max_uses,
            },
            actor="system",
        )

    # 6. Return 307 Temporary Redirect to the presigned URL
    return RedirectResponse(
        url=presigned_url,
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    )
