"""Main loop: verify -> settle -> scan -> route, repeat."""
from __future__ import annotations

import logging
import signal
import sys
import time
from datetime import datetime, timezone

from .config import CONFIG, Config
from .executor import Executor
from .friction import FrictionModel, VerificationQueue
from .position_store import PositionStore
from .settler import sweep_settlements
from .strategy import (
    find_opportunities,
    handle_opportunity,
    process_verification_queue,
)


def get_scan_interval(config: Config, now_utc: datetime) -> tuple[float, str]:
    """Return (seconds_to_sleep, mode_label)."""
    if not config.adaptive_scan_enabled:
        return config.scan_interval_seconds, "fixed"
    hours = {int(h.strip()) for h in config.high_activity_hours_utc.split(",")
             if h.strip().isdigit()}
    if now_utc.hour in hours:
        return config.high_activity_interval_seconds, "high"
    return config.low_activity_interval_seconds, "low"


def _setup_logging(log_path: str) -> None:
    fmt = "%(asctime)s %(levelname)s %(name)s | %(message)s"
    logging.basicConfig(
        level=logging.INFO,
        format=fmt,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_path),
        ],
    )


_STOP = False


def _handle_signal(signum, _frame):
    global _STOP
    print(f"\nreceived signal {signum}, finishing current loop and exiting...")
    _STOP = True


def main() -> int:
    _setup_logging(CONFIG.log_path)
    log = logging.getLogger("arb_bot")

    mode = "DRY-RUN (realism layer ON)" if CONFIG.dry_run else "*** LIVE TRADING ***"
    log.info("=" * 64)
    log.info("Polymarket Resolution-Time Arb Bot starting in %s", mode)
    log.info("  max buy price       : $%.3f", CONFIG.max_buy_price)
    log.info("  min buy price       : $%.3f", CONFIG.min_buy_price)
    log.info("  min market age      : %.1f hours", CONFIG.min_market_age_hours)
    log.info("  max market age      : %.1f days", CONFIG.max_market_age_days)
    log.info("  max position size   : $%.2f", CONFIG.max_position_size_usd)
    log.info("  max total exposure  : $%.2f", CONFIG.max_total_exposure_usd)
    if CONFIG.adaptive_scan_enabled:
        log.info("  scan interval       : adaptive (hi=%.0fs / lo=%.0fs, hi-hours=%s UTC)",
                 CONFIG.high_activity_interval_seconds,
                 CONFIG.low_activity_interval_seconds,
                 CONFIG.high_activity_hours_utc)
    else:
        log.info("  scan interval       : %.0fs (fixed)", CONFIG.scan_interval_seconds)
    if CONFIG.dry_run:
        log.info("  --- realism layer ---")
        log.info("  verify delay        : %.0fs", CONFIG.verification_delay_seconds)
        log.info("  est gas/trade       : $%.2f", CONFIG.estimated_gas_cost_usd)
        log.info("  expected fill ratio : %.0f%%", CONFIG.expected_fill_ratio * 100)
        log.info("  adverse fill rate   : %.1f%%", CONFIG.adverse_fill_rate * 100)
        log.info("  UMA dispute rate    : %.1f%%", CONFIG.uma_dispute_rate * 100)
    log.info("=" * 64)

    if not CONFIG.dry_run:
        log.warning("LIVE MODE: real USDC will be spent. Ctrl-C in 10s to abort.")
        time.sleep(10)

    store = PositionStore(CONFIG.db_path)
    executor = Executor(CONFIG)
    queue = VerificationQueue(CONFIG.verification_delay_seconds)
    friction = FrictionModel(
        gas_cost_usd=CONFIG.estimated_gas_cost_usd,
        expected_fill_ratio=CONFIG.expected_fill_ratio,
        adverse_fill_rate=CONFIG.adverse_fill_rate,
        uma_dispute_rate=CONFIG.uma_dispute_rate,
    )

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    while not _STOP:
        loop_start = time.monotonic()

        # 1. Process any verifications whose delay has elapsed.
        try:
            opened = process_verification_queue(CONFIG, store, queue, friction)
            if opened:
                log.info("opened %d positions from verification queue", opened)
        except Exception:
            log.exception("verification processing failed")

        # 2. Settle any positions UMA has resolved since last loop.
        try:
            resolved = sweep_settlements(CONFIG, store, friction)
            if resolved:
                log.info("settled %d positions this cycle", resolved)
        except Exception:
            log.exception("settlement sweep failed")

        # 3. Find and route new opportunities.
        try:
            opps = find_opportunities(CONFIG)
            for opp in opps:
                if _STOP:
                    break
                handle_opportunity(opp, CONFIG, store, executor, queue)
        except Exception:
            log.exception("opportunity scan failed")

        # 4. Status snapshot.
        exposure = store.open_exposure_usd()
        interval, mode = get_scan_interval(CONFIG, datetime.now(timezone.utc))
        log.info(
            "status: exposure $%.2f / $%.2f | queue=%d | next scan in %.0fs (%s)",
            exposure, CONFIG.max_total_exposure_usd, len(queue),
            interval, mode,
        )

        if _STOP:
            break
        elapsed = time.monotonic() - loop_start
        sleep_for = max(5.0, interval - elapsed)
        for _ in range(int(sleep_for)):
            if _STOP:
                break
            time.sleep(1)

    log.info("bot stopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
