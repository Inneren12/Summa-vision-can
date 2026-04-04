"""StatCan WDS API maintenance window guard.

The Statistics Canada Web Data Service API is offline daily from
00:00 to 08:30 Eastern Time (America/Toronto).  This module provides
a **pure, deterministic** check so that callers can avoid issuing
requests during the maintenance window and risking bans or errors.

Design notes
------------
* Time is always *injected* — ``datetime.now()`` is never called
  internally, keeping the function 100 % testable and side-effect-free.
* We use :mod:`zoneinfo` (stdlib ≥ 3.9) for IANA timezone handling,
  which correctly accounts for EST ↔ EDT (Daylight Saving Time)
  transitions in Toronto.
"""

from __future__ import annotations

from datetime import datetime, time
from zoneinfo import ZoneInfo

# ──────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────
TORONTO_TZ: ZoneInfo = ZoneInfo("America/Toronto")

# Maintenance window boundaries (inclusive start, exclusive end).
# The API is offline from 00:00:00 up to *but not including* 08:30:00.
_MAINTENANCE_START: time = time(0, 0, 0)
_MAINTENANCE_END: time = time(8, 30, 0)


class StatCanMaintenanceGuard:
    """Guard that checks whether the StatCan API is in its maintenance window.

    Usage::

        guard = StatCanMaintenanceGuard()
        if guard.is_maintenance_window(some_datetime):
            # skip the request
            ...

    The guard is intentionally stateless — all state comes in through the
    ``current_time`` parameter so the check remains pure and deterministic.
    """

    # Expose the timezone as a class attribute for callers that need it.
    timezone: ZoneInfo = TORONTO_TZ

    def is_maintenance_window(self, current_time: datetime) -> bool:
        """Return ``True`` if *current_time* falls within the maintenance window.

        Parameters
        ----------
        current_time:
            A :class:`~datetime.datetime` instance.  If it is timezone-aware
            it will be converted to ``America/Toronto``; if it is naive it is
            **assumed** to already represent Toronto local time (a
            :class:`ValueError` is raised to enforce awareness).

        Returns
        -------
        bool
            ``True``  when in window: ``00:00:00 <= local_time < 08:30:00``
            ``False`` otherwise.

        Raises
        ------
        ValueError
            If *current_time* is a naive (timezone-unaware) datetime.
        """
        if current_time.tzinfo is None:
            raise ValueError(
                "current_time must be timezone-aware.  "
                "Attach a tzinfo (e.g. ZoneInfo('America/Toronto')) before calling."
            )

        toronto_time: datetime = current_time.astimezone(TORONTO_TZ)
        local_clock: time = toronto_time.time()

        return _MAINTENANCE_START <= local_clock < _MAINTENANCE_END
