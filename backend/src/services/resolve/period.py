"""Phase 3.1c — period selection across cached value-cache rows.

Pure helper documented at recon §8: when caller omits ``period`` the
resolve service returns the latest row (last element after the
repository's ASC ordering). When caller pins ``period`` the service
expects a single row; multiple is unexpected and warned upstream
(this helper just returns ``rows[0]`` deterministically).
"""
from __future__ import annotations

import structlog

from src.services.statcan.value_cache_schemas import ValueCacheRow

_logger: structlog.stdlib.BoundLogger = structlog.get_logger(
    module="services.resolve.period"
)


def pick_row(
    rows: list[ValueCacheRow], *, period: str | None
) -> ValueCacheRow:
    """Pick a single :class:`ValueCacheRow` from the repository result.

    Args:
        rows: ASC-ordered rows from
            :meth:`SemanticValueCacheRepository.get_by_lookup`.
        period: Optional caller-pinned ``ref_period``. ``None`` means
            "latest" → ``rows[-1]`` per recon §8.

    Returns:
        The selected row. Caller is responsible for non-emptiness; this
        helper assumes ``rows`` has at least one element (the resolve
        state machine only invokes ``pick_row`` on the rows-found
        branches).

    Logs a structured warning when ``period`` is pinned and the
    repository returned more than one row — that should never happen in
    practice (the unique key includes ``ref_period``) but the warning
    surfaces a cache-integrity bug rather than silently masking it.
    """
    if period is None:
        return rows[-1]
    if len(rows) > 1:
        _logger.warning(
            "resolve.unexpected_multiple_rows_for_explicit_period",
            count=len(rows),
            period=period,
        )
    return rows[0]


__all__ = ["pick_row"]
