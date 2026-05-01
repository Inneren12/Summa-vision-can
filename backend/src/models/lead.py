"""Lead ORM model.

Represents an email lead captured when a user downloads a free asset.
The ``asset_id`` field links the lead to the publication (as a string
reference, not a foreign key) so that lead-capture analytics can be
decoupled from the publications table lifecycle.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, String, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class Lead(Base):
    """An email lead collected via asset download.

    Attributes:
        id: Auto-incrementing primary key.
        email: Lead's email address (max 320 chars – RFC 5321 limit).
        ip_address: IP address from which the lead was captured.
        asset_id: Identifier of the asset that triggered the capture.
        is_b2b: Whether this lead is classified as business-to-business.
        company_domain: Extracted domain of the lead's company (nullable).
        category: Lead category from scoring: "b2b", "education", "isp", or "b2c".
        esp_synced: Whether this lead has been synced to the ESP (Beehiiv).
        esp_sync_failed_permanent: Whether ESP returned 4xx (never retry).
        created_at: UTC timestamp of record creation.
    """

    __tablename__ = "leads"
    __table_args__ = (
        UniqueConstraint("email", "asset_id", name="uq_lead_email_asset"),
        Index(
            "ix_lead_unsynced_lookup",
            "esp_synced",
            "esp_sync_failed_permanent",
            "created_at",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=False)
    asset_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    is_b2b: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    company_domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    category: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    esp_synced: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    esp_sync_failed_permanent: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    utm_source: Mapped[str | None] = mapped_column(
        String(length=100),
        nullable=True,
        doc="UTM source param at submit time, e.g. 'reddit'. Phase 2.3.",
    )
    utm_medium: Mapped[str | None] = mapped_column(
        String(length=100),
        nullable=True,
        doc="UTM medium param, typically 'social'. Phase 2.3.",
    )
    utm_campaign: Mapped[str | None] = mapped_column(
        String(length=200),
        nullable=True,
        doc="UTM campaign param, typically 'publish_kit'. Phase 2.3.",
    )
    utm_content: Mapped[str | None] = mapped_column(
        String(length=200),
        nullable=True,
        index=True,
        doc="UTM content param = source publication lineage_key. Phase 2.3.",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<Lead(id={self.id}, email={self.email!r}, "
            f"asset_id={self.asset_id!r})>"
        )
