"""DownloadToken ORM model (D-0c).

Represents a magic-link download token. Only the SHA-256 hash of the
raw token is stored (R17). Tokens have a max use count and expiry time.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class DownloadToken(Base):
    """A download token for secure magic-link access.

    Attributes:
        id: Auto-incrementing primary key.
        token_hash: SHA-256 hash of the raw token (never store raw).
        lead_id: Foreign key to the lead that requested the download.
        expires_at: UTC timestamp when the token expires.
        max_uses: Maximum number of times this token can be used.
        use_count: Number of times this token has been used.
        revoked: Whether this token has been manually revoked.
        created_at: UTC timestamp of record creation.
    """

    __tablename__ = "download_tokens"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    token_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, index=True
    )
    lead_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("leads.id"), nullable=False, index=True
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    max_uses: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    use_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    revoked: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<DownloadToken(id={self.id}, lead_id={self.lead_id}, "
            f"use_count={self.use_count}/{self.max_uses})>"
        )
