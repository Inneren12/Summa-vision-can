"""DownloadToken repository — data access layer for download tokens (D-2, A4).

All methods accept ``AsyncSession`` via constructor injection (ARCH-DPEN-001).

Commit semantics:
    Repositories perform ``session.flush()`` and ``session.refresh()``
    on create operations but do **not** call ``session.commit()``.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.download_token import DownloadToken


class DownloadTokenRepository:
    """Encapsulates persistence logic for :class:`DownloadToken`.

    Attributes:
        _session: The injected async database session.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        lead_id: int,
        token_hash: str,
        expires_at: datetime,
        max_uses: int,
    ) -> DownloadToken:
        """Create a new download token record.

        Args:
            lead_id: ID of the lead this token belongs to.
            token_hash: SHA-256 hash of the raw token.
            expires_at: When this token expires.
            max_uses: Maximum number of uses for this token.

        Returns:
            The newly created ``DownloadToken`` instance.
        """
        token = DownloadToken(
            lead_id=lead_id,
            token_hash=token_hash,
            expires_at=expires_at,
            max_uses=max_uses,
        )
        self._session.add(token)
        await self._session.flush()
        await self._session.refresh(token)
        return token

    async def activate_atomic(self, token_hash: str) -> DownloadToken | None:
        """Atomically increment use_count and return the token (R17).

        Uses UPDATE with WHERE guards to prevent TOCTOU races.
        Returns None if the token is invalid, expired, exhausted, or revoked.

        Args:
            token_hash: SHA-256 hash of the raw token.

        Returns:
            The updated DownloadToken if valid, None otherwise.
        """
        now = datetime.now(timezone.utc)

        # Atomic UPDATE with guards — only succeeds if token is valid.
        # synchronize_session=False avoids Python-side evaluation which
        # has timezone comparison issues with SQLite (tests use tz-naive).
        stmt = (
            update(DownloadToken)
            .where(
                DownloadToken.token_hash == token_hash,
                DownloadToken.use_count < DownloadToken.max_uses,
                DownloadToken.expires_at > now,
                DownloadToken.revoked.is_(False),
            )
            .values(use_count=DownloadToken.use_count + 1)
            .execution_options(synchronize_session=False)
        )
        result = await self._session.execute(stmt)

        if result.rowcount == 0:
            return None

        # Expire cached state and re-fetch the updated token
        self._session.expire_all()
        select_stmt = select(DownloadToken).where(
            DownloadToken.token_hash == token_hash
        )
        select_result = await self._session.execute(select_stmt)
        return select_result.scalar_one_or_none()

    async def get_by_lead_and_asset(self, lead_id: int) -> DownloadToken | None:
        """Get the latest non-revoked token for a lead.

        Used for the resend flow — find existing token to reuse or revoke.

        Args:
            lead_id: ID of the lead.

        Returns:
            The latest non-revoked DownloadToken, or None.
        """
        stmt = (
            select(DownloadToken)
            .where(
                DownloadToken.lead_id == lead_id,
                DownloadToken.revoked.is_(False),
            )
            .order_by(DownloadToken.created_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def revoke(self, token_id: int) -> None:
        """Revoke a token by setting revoked=True.

        Args:
            token_id: ID of the token to revoke.
        """
        stmt = (
            update(DownloadToken)
            .where(DownloadToken.id == token_id)
            .values(revoked=True)
        )
        await self._session.execute(stmt)

    async def get_error_reason(self, token_hash: str) -> str | None:
        """Look up a token and determine why it cannot be used.

        Returns:
            A specific error reason string, or None if token not found.
            Possible values: "expired", "exhausted", "revoked".
        """
        stmt = select(DownloadToken).where(
            DownloadToken.token_hash == token_hash
        )
        result = await self._session.execute(stmt)
        token = result.scalar_one_or_none()

        if token is None:
            return None

        if token.revoked:
            return "revoked"

        now = datetime.now(timezone.utc)
        # Handle timezone-naive datetimes from SQLite
        expires_at = token.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if expires_at <= now:
            return "expired"
        if token.use_count >= token.max_uses:
            return "exhausted"

        return None
