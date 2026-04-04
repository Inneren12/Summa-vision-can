"""Tests for :mod:`src.services.statcan.maintenance`.

All datetime objects are **timezone-aware** and injected directly into the
guard — no monkeypatching of ``datetime.now()`` is needed because the
implementation is a pure function of its input.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from zoneinfo import ZoneInfo

from src.services.statcan.maintenance import (
    StatCanMaintenanceGuard,
    TORONTO_TZ,
    _MAINTENANCE_END,
    _MAINTENANCE_START,
)

# ──────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────
TORONTO: ZoneInfo = ZoneInfo("America/Toronto")
UTC: timezone = timezone.utc


@pytest.fixture
def guard() -> StatCanMaintenanceGuard:
    """Return a fresh guard instance for each test."""
    return StatCanMaintenanceGuard()


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────
def _toronto_dt(
    year: int,
    month: int,
    day: int,
    hour: int = 0,
    minute: int = 0,
    second: int = 0,
) -> datetime:
    """Shorthand to build a Toronto-aware datetime."""
    return datetime(year, month, day, hour, minute, second, tzinfo=TORONTO)


# ══════════════════════════════════════════════
# 1.  Core window detection
# ══════════════════════════════════════════════
class TestMaintenanceWindowCore:
    """Basic in-window / out-of-window assertions."""

    def test_deep_in_window_01_00(self, guard: StatCanMaintenanceGuard) -> None:
        """01:00 EST is clearly inside the maintenance window."""
        dt = _toronto_dt(2026, 1, 15, 1, 0, 0)
        assert guard.is_maintenance_window(dt) is True

    def test_deep_in_window_04_00(self, guard: StatCanMaintenanceGuard) -> None:
        """04:00 EST — middle of the window."""
        dt = _toronto_dt(2026, 1, 15, 4, 0, 0)
        assert guard.is_maintenance_window(dt) is True

    def test_midnight_exact(self, guard: StatCanMaintenanceGuard) -> None:
        """00:00:00 is the very start of the window — must be True."""
        dt = _toronto_dt(2026, 1, 15, 0, 0, 0)
        assert guard.is_maintenance_window(dt) is True

    def test_after_window_09_00(self, guard: StatCanMaintenanceGuard) -> None:
        """09:00 EST is well outside the window."""
        dt = _toronto_dt(2026, 1, 15, 9, 0, 0)
        assert guard.is_maintenance_window(dt) is False

    def test_late_evening_23_00(self, guard: StatCanMaintenanceGuard) -> None:
        """23:00 EST is outside the window (before midnight next cycle)."""
        dt = _toronto_dt(2026, 1, 15, 23, 0, 0)
        assert guard.is_maintenance_window(dt) is False

    def test_noon(self, guard: StatCanMaintenanceGuard) -> None:
        """12:00 EST — firmly outside."""
        dt = _toronto_dt(2026, 1, 15, 12, 0, 0)
        assert guard.is_maintenance_window(dt) is False


# ══════════════════════════════════════════════
# 2.  Edge-case boundaries
# ══════════════════════════════════════════════
class TestEdgeCases:
    """Boundary tests around 08:30:00."""

    def test_edge_08_29_59_in_window(self, guard: StatCanMaintenanceGuard) -> None:
        """08:29:59 EST — one second before window closes → True."""
        dt = _toronto_dt(2026, 1, 15, 8, 29, 59)
        assert guard.is_maintenance_window(dt) is True

    def test_edge_08_30_00_out_of_window(self, guard: StatCanMaintenanceGuard) -> None:
        """08:30:00 EST — window closes at this exact moment → False."""
        dt = _toronto_dt(2026, 1, 15, 8, 30, 0)
        assert guard.is_maintenance_window(dt) is False

    def test_edge_08_30_01_out_of_window(self, guard: StatCanMaintenanceGuard) -> None:
        """08:30:01 EST — just past the window → False."""
        dt = _toronto_dt(2026, 1, 15, 8, 30, 1)
        assert guard.is_maintenance_window(dt) is False

    def test_edge_23_59_59_out_of_window(self, guard: StatCanMaintenanceGuard) -> None:
        """23:59:59 EST — one second before midnight, outside window."""
        dt = _toronto_dt(2026, 1, 15, 23, 59, 59)
        assert guard.is_maintenance_window(dt) is False


# ══════════════════════════════════════════════
# 3.  Timezone conversion correctness
# ══════════════════════════════════════════════
class TestTimezoneConversion:
    """Ensure that non-Toronto datetimes are correctly converted."""

    def test_utc_time_during_est_window(self, guard: StatCanMaintenanceGuard) -> None:
        """05:00 UTC in winter (EST = UTC-5) → 00:00 Toronto → in window."""
        dt = datetime(2026, 1, 15, 5, 0, 0, tzinfo=UTC)
        assert guard.is_maintenance_window(dt) is True

    def test_utc_time_outside_est_window(self, guard: StatCanMaintenanceGuard) -> None:
        """14:00 UTC in winter (EST = UTC-5) → 09:00 Toronto → out of window."""
        dt = datetime(2026, 1, 15, 14, 0, 0, tzinfo=UTC)
        assert guard.is_maintenance_window(dt) is False

    def test_utc_time_during_edt_window(self, guard: StatCanMaintenanceGuard) -> None:
        """04:00 UTC in summer (EDT = UTC-4) → 00:00 Toronto → in window."""
        dt = datetime(2026, 7, 15, 4, 0, 0, tzinfo=UTC)
        assert guard.is_maintenance_window(dt) is True

    def test_utc_time_outside_edt_window(self, guard: StatCanMaintenanceGuard) -> None:
        """13:00 UTC in summer (EDT = UTC-4) → 09:00 Toronto → out of window."""
        dt = datetime(2026, 7, 15, 13, 0, 0, tzinfo=UTC)
        assert guard.is_maintenance_window(dt) is False

    def test_pacific_time_in_window(self, guard: StatCanMaintenanceGuard) -> None:
        """21:00 PST (UTC-8) on Jan 14 → 00:00 EST Jan 15 → in window."""
        pacific = ZoneInfo("America/Vancouver")
        dt = datetime(2026, 1, 14, 21, 0, 0, tzinfo=pacific)
        assert guard.is_maintenance_window(dt) is True


# ══════════════════════════════════════════════
# 4.  Daylight Saving Time transitions (Toronto)
# ══════════════════════════════════════════════
class TestDaylightSavingTransitions:
    """DST transitions in the America/Toronto zone.

    In 2026:
      - Spring forward: Sun 2026-03-08 02:00 EST → 03:00 EDT
      - Fall back:      Sun 2026-11-01 02:00 EDT → 01:00 EST
    """

    def test_spring_forward_before_transition(
        self, guard: StatCanMaintenanceGuard
    ) -> None:
        """01:30 EST on the night of spring-forward → in window."""
        # 2026-03-08 01:30 EST  (clocks haven't jumped yet)
        dt = datetime(2026, 3, 8, 6, 30, 0, tzinfo=UTC)  # 06:30 UTC = 01:30 EST
        assert guard.is_maintenance_window(dt) is True

    def test_spring_forward_after_transition(
        self, guard: StatCanMaintenanceGuard
    ) -> None:
        """Right after the spring-forward jump, 03:00 EDT → in window (03:00 < 08:30)."""
        # 03:00 EDT = 07:00 UTC on 2026-03-08
        dt = datetime(2026, 3, 8, 7, 0, 0, tzinfo=UTC)
        assert guard.is_maintenance_window(dt) is True

    def test_spring_forward_window_end_edt(
        self, guard: StatCanMaintenanceGuard
    ) -> None:
        """08:30 EDT on spring-forward day → window has closed."""
        # 08:30 EDT = 12:30 UTC on 2026-03-08
        dt = datetime(2026, 3, 8, 12, 30, 0, tzinfo=UTC)
        assert guard.is_maintenance_window(dt) is False

    def test_fall_back_first_01_00(self, guard: StatCanMaintenanceGuard) -> None:
        """01:00 EDT on fall-back day (before clocks move back) → in window."""
        # 01:00 EDT = 05:00 UTC on 2026-11-01
        dt = datetime(2026, 11, 1, 5, 0, 0, tzinfo=UTC)
        assert guard.is_maintenance_window(dt) is True

    def test_fall_back_second_01_00(self, guard: StatCanMaintenanceGuard) -> None:
        """01:00 EST on fall-back day (after clocks moved back) → in window."""
        # 01:00 EST = 06:00 UTC on 2026-11-01
        dt = datetime(2026, 11, 1, 6, 0, 0, tzinfo=UTC)
        assert guard.is_maintenance_window(dt) is True


# ══════════════════════════════════════════════
# 5.  Naive datetime rejection
# ══════════════════════════════════════════════
class TestNaiveDatetimeRejection:
    """The guard must reject timezone-unaware datetimes."""

    def test_naive_datetime_raises_value_error(
        self, guard: StatCanMaintenanceGuard
    ) -> None:
        """Passing a naive datetime must raise ValueError."""
        naive = datetime(2026, 1, 15, 3, 0, 0)
        with pytest.raises(ValueError, match="timezone-aware"):
            guard.is_maintenance_window(naive)


# ══════════════════════════════════════════════
# 6.  Class / module attributes
# ══════════════════════════════════════════════
class TestModuleAttributes:
    """Smoke-tests for exported constants and class attributes."""

    def test_timezone_attribute(self) -> None:
        guard = StatCanMaintenanceGuard()
        assert guard.timezone == ZoneInfo("America/Toronto")

    def test_toronto_tz_constant(self) -> None:
        assert TORONTO_TZ == ZoneInfo("America/Toronto")

    def test_maintenance_start(self) -> None:
        from datetime import time as t

        assert _MAINTENANCE_START == t(0, 0, 0)

    def test_maintenance_end(self) -> None:
        from datetime import time as t

        assert _MAINTENANCE_END == t(8, 30, 0)
