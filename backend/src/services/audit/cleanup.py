"""Daily cleanup of expired audit events based on AUDIT_RETENTION_DAYS."""

import structlog
from datetime import datetime, timedelta, timezone
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.models.audit_event import AuditEvent

log = structlog.get_logger()


async def cleanup_old_audit_events(
    session_factory: async_sessionmaker,
    retention_days: int = 90,
) -> int:
    """Delete audit events older than retention_days. Returns count deleted."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)

    async with session_factory() as session:
        result = await session.execute(
            delete(AuditEvent).where(AuditEvent.created_at < cutoff)
        )
        await session.commit()
        deleted = result.rowcount

    log.info("audit_cleanup_completed", deleted=deleted, cutoff=cutoff.isoformat())
    return deleted
