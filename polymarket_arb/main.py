"""Main loop: scan -> execute -> settle, repeat."""
from __future__ import annotations

import logging
import signal
import sys
import time

from .config import CONFIG
from .executor import Executor
from .position_store import PositionStore
from .settler import sweep_settlements
from .strategy import execute_opportunity, find_opportunities


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

    mode = "DRY-RUN" if CONFIG.dry_run else "*** LIVE TRADING ***"
    log.info("=" * 60)
    log.info("Polymarket Resolution-Time Arb Bot starting in %s", mode)
    log.info("  max buy price       : $%.3f", CONFIG.max_buy_price)
    log.info("  min buy price       : $%.3f", CONFIG.min_buy_price)
    log.info("  min market age      : %.1f hours", CONFIG.min_market_age_hours)
    log.info("  max market age      : %.1f days", CONFIG.max_market_age_days)
    log.info("  max position size   : $%.2f", CONFIG.max_position_size_usd)
    log.info("  max total exposure  : $%.2f", CONFIG.max_total_exposure_usd)
    log.info("  scan interval       : %.0fs", CONFIG.scan_interval_seconds)
    log.info("=" * 60)

    if not CONFIG.dry_run:
        log.warning("LIVE MODE: real USDC will be spent. Ctrl-C in 10s to abort.")
        time.sleep(10)

    store = PositionStore(CONFIG.db_path)
    executor = Executor(CONFIG)

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    while not _STOP:
        loop_start = time.monotonic()

        # 1. Settle any positions UMA has resolved since last loop.
        try:
            resolved = sweep_settlements(CONFIG, store)
            if resolved:
                log.info("settled %d positions this cycle", resolved)
        except Exception:
            log.exception("settlement sweep failed")

        # 2. Find and act on new opportunities.
        try:
            opps = find_opportunities(CONFIG)
            for opp in opps:
                if _STOP:
                    break
                execute_opportunity(opp, CONFIG, store, executor)
        except Exception:
            log.exception("opportunity scan failed")

        # 3. Status snapshot.
        exposure = store.open_exposure_usd()
        log.info("open exposure: $%.2f / $%.2f", exposure, CONFIG.max_total_exposure_usd)

        if _STOP:
            break
        elapsed = time.monotonic() - loop_start
        sleep_for = max(5.0, CONFIG.scan_interval_seconds - elapsed)
        log.debug("sleeping %.1fs", sleep_for)
        for _ in range(int(sleep_for)):
            if _STOP:
                break
            time.sleep(1)

    log.info("bot stopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
