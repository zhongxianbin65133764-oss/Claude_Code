"""Tests for the adaptive scan-interval logic."""
from __future__ import annotations

from datetime import datetime, timezone

from polymarket_arb.config import Config
from polymarket_arb.main import get_scan_interval


def _at_utc(hour: int) -> datetime:
    return datetime(2026, 5, 17, hour, 30, 0, tzinfo=timezone.utc)


def test_disabled_returns_fixed_interval():
    cfg = Config(adaptive_scan_enabled=False, scan_interval_seconds=90.0)
    interval, mode = get_scan_interval(cfg, _at_utc(12))
    assert interval == 90.0
    assert mode == "fixed"


def test_enabled_uses_high_during_listed_hours():
    cfg = Config(
        adaptive_scan_enabled=True,
        high_activity_hours_utc="0,1,2,18,19,20,21,22,23",
        high_activity_interval_seconds=30.0,
        low_activity_interval_seconds=300.0,
    )
    interval, mode = get_scan_interval(cfg, _at_utc(1))
    assert interval == 30.0
    assert mode == "high"


def test_enabled_uses_low_during_off_hours():
    cfg = Config(
        adaptive_scan_enabled=True,
        high_activity_hours_utc="0,1,2,18,19,20,21,22,23",
        high_activity_interval_seconds=30.0,
        low_activity_interval_seconds=300.0,
    )
    interval, mode = get_scan_interval(cfg, _at_utc(12))
    assert interval == 300.0
    assert mode == "low"


def test_us_evening_window_is_high():
    cfg = Config(
        adaptive_scan_enabled=True,
        high_activity_hours_utc="18,19,20,21,22,23",
        high_activity_interval_seconds=30.0,
        low_activity_interval_seconds=300.0,
    )
    # 9pm ET = UTC 01 in summer, but US sports primetime corresponds
    # to UTC 23-04 broadly; we check the documented hours.
    interval, mode = get_scan_interval(cfg, _at_utc(20))
    assert mode == "high"


def test_malformed_hours_string_falls_back_to_low():
    cfg = Config(
        adaptive_scan_enabled=True,
        high_activity_hours_utc="not,a,number",
        high_activity_interval_seconds=30.0,
        low_activity_interval_seconds=300.0,
    )
    interval, mode = get_scan_interval(cfg, _at_utc(1))
    # Nothing parses to a valid hour, so we're never in the high set.
    assert mode == "low"
    assert interval == 300.0
