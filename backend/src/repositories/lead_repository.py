"""Lead repository — data access layer for email leads.

Commit semantics:
    Repositories perform ``session.flush()`` and ``session.refresh()``
    on create operations but do **not** call ``session.commit()``.
    Commits are handled by the FastAPI ``get_db`` dependency (auto-commit
    on successful request, rollback on exception).  Callers outside of
    a request context (e.g. background tasks, scripts) must commit
    explicitly.
"""

from __future__ import annotations

from typing import Sequence

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.lead import Lead


class LeadRepository:
    """Encapsulates persistence logic for :class:`Lead`.

    Attributes:
        _session: The injected async database session.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialise with an injected ``AsyncSession``.

        Args:
            session: An active SQLAlchemy async session provided by DI.
        """
        self._session = session

    async def create(
        self,
        *,
        email: str,
        ip_address: str,
        asset_id: str,
        is_b2b: bool = False,
        company_domain: str | None = None,
        utm_source: str | None = None,
        utm_medium: str | None = None,
        utm_campaign: str | None = None,
        utm_content: str | None = None,
    ) -> Lead:
        """Create a new lead record.

        Args:
            email: Lead's email address.
            ip_address: IP address of the request.
            asset_id: Identifier of the downloaded asset.
            is_b2b: Whether this is a B2B lead.
            company_domain: Extracted company domain (optional).
            utm_source: UTM source param at submit time (Phase 2.3).
            utm_medium: UTM medium param (Phase 2.3).
            utm_campaign: UTM campaign param (Phase 2.3).
            utm_content: UTM content param = publication lineage_key
                (Phase 2.3).

        Returns:
            The newly created ``Lead`` instance with its ``id`` populated
            after flush.
        """
        lead = Lead(
            email=email,
            ip_address=ip_address,
            asset_id=asset_id,
            is_b2b=is_b2b,
            company_domain=company_domain,
            utm_source=utm_source,
            utm_medium=utm_medium,
            utm_campaign=utm_campaign,
            utm_content=utm_content,
        )
        self._session.add(lead)
        await self._session.flush()
        await self._session.refresh(lead)
        return lead

    async def get_or_create(
        self,
        *,
        email: str,
        ip_address: str,
        asset_id: str,
        is_b2b: bool = False,
        company_domain: str | None = None,
        utm_source: str | None = None,
        utm_medium: str | None = None,
        utm_campaign: str | None = None,
        utm_content: str | None = None,
    ) -> tuple[Lead, bool]:
        """Create a lead or return the existing one.  Race-safe.

        Uses an optimistic insert guarded by the ``uq_lead_email_asset``
        unique constraint.  If a concurrent request already inserted the
        same (email, asset_id) pair, the :class:`IntegrityError` is caught,
        the session is rolled back, and the existing row is fetched instead.

        Args:
            email: Lead's email address.
            ip_address: IP address of the request.
            asset_id: Identifier of the downloaded asset.
            is_b2b: Whether this is a B2B lead.
            company_domain: Extracted company domain (optional).

        Returns:
            A ``(lead, created)`` tuple where *created* is ``True`` when a
            new row was inserted.
        """
        try:
            lead = Lead(
                email=email,
                ip_address=ip_address,
                asset_id=asset_id,
                is_b2b=is_b2b,
                company_domain=company_domain,
                utm_source=utm_source,
                utm_medium=utm_medium,
                utm_campaign=utm_campaign,
                utm_content=utm_content,
            )
            self._session.add(lead)
            await self._session.flush()
            await self._session.refresh(lead)
            return lead, True
        except IntegrityError:
            await self._session.rollback()
            existing = await self.get_by_email_and_asset(email, asset_id)
            if existing is None:
                raise  # something else went wrong
            return existing, False

    async def exists(self, email: str, asset_id: str) -> bool:
        """Check whether a lead already exists for a given email + asset.

        Used for deduplication: if a user has already submitted their
        email for the same asset, the service should skip insertion.

        Args:
            email: Email address to check.
            asset_id: Asset identifier to check.

        Returns:
            ``True`` if a matching record exists, ``False`` otherwise.
        """
        stmt = (
            select(Lead.id)
            .where(Lead.email == email, Lead.asset_id == asset_id)
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def get_by_id(self, lead_id: int) -> Lead | None:
        """Retrieve a lead by primary key.

        Args:
            lead_id: Primary key of the lead.

        Returns:
            The ``Lead`` instance, or ``None`` if not found.
        """
        stmt = select(Lead).where(Lead.id == lead_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email_and_asset(self, email: str, asset_id: str) -> Lead | None:
        """Retrieve an existing lead for a given email + asset.

        Args:
            email: Email address to look up.
            asset_id: Asset identifier.

        Returns:
            The matching ``Lead`` instance, or ``None``.
        """
        stmt = (
            select(Lead)
            .where(Lead.email == email, Lead.asset_id == asset_id)
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_resend_count(self, email: str, asset_id: str) -> int:
        """Count how many times a lead has been sent for email+asset.

        This is used to enforce the 3-resend limit.

        Args:
            email: Email address.
            asset_id: Asset identifier.

        Returns:
            The number of existing leads (always 0 or 1 due to unique constraint).
        """
        stmt = (
            select(func.count())
            .select_from(Lead)
            .where(Lead.email == email, Lead.asset_id == asset_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def list_by_utm_content(
        self, utm_content: str, *, limit: int = 200
    ) -> Sequence[Lead]:
        """Return leads attributed to a publication via ``utm_content``.

        Phase 2.3: ``utm_content`` carries the source publication's
        ``lineage_key``. Ordered newest-first to match admin dashboard
        consumption.

        Args:
            utm_content: The publication ``lineage_key`` to filter by.
            limit: Maximum number of rows to return.

        Returns:
            A sequence of matching :class:`Lead` rows.
        """
        stmt = (
            select(Lead)
            .where(Lead.utm_content == utm_content)
            .order_by(Lead.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_unsynced(self, limit: int = 100) -> Sequence[Lead]:
        """Retrieve leads that have not yet been successfully synced to the ESP
        and have not permanently failed.

        Args:
            limit: Maximum number of leads to return.

        Returns:
            A sequence of unsynced Lead instances.
        """
        stmt = (
            select(Lead)
            .where(
                Lead.esp_synced.is_(False),
                Lead.esp_sync_failed_permanent.is_(False),
            )
            .order_by(Lead.created_at.asc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def mark_synced(self, lead_id: int) -> None:
        """Mark a lead as successfully synced to the ESP.

        Args:
            lead_id: The ID of the lead to update.
        """
        stmt = (
            update(Lead)
            .where(Lead.id == lead_id)
            .values(esp_synced=True)
        )
        await self._session.execute(stmt)

    async def mark_permanently_failed(self, lead_id: int) -> None:
        """Mark a lead as permanently failed to sync to the ESP.

        Args:
            lead_id: The ID of the lead to update.
        """
        stmt = (
            update(Lead)
            .where(Lead.id == lead_id)
            .values(esp_sync_failed_permanent=True)
        )
        await self._session.execute(stmt)
