"""Seed positions.db with synthetic data to preview the dashboard."""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from polymarket_arb.config import CONFIG
from polymarket_arb.position_store import PositionStore


def main(db_path: str = CONFIG.db_path) -> None:
    if os.path.exists(db_path):
        os.remove(db_path)
    store = PositionStore(db_path)

    open_positions = [
        ("0xopen1", "t1", "Will the Lakers win Game 3 of the playoffs?", "YES", 26.18, 0.955, 25.00),
        ("0xopen2", "t2", "Will ETH close above $5000 on May 16?", "NO", 27.78, 0.900, 25.00),
        ("0xopen3", "t3", "Will Chiefs beat Bengals on May 11?", "YES", 26.60, 0.940, 25.00),
    ]
    for cid, tid, q, side, tokens, px, cost in open_positions:
        store.open_position(cid, tid, q, side, tokens, px, cost, dry_run=True)

    closed_positions = [
        ("0xc1", "t10", "Will BTC close above $100k on May 8?",      "NO", 27.03, 0.925, 25.00, 27.03),  # +2.03
        ("0xc2", "t11", "Will the Warriors beat the Suns May 6?",   "YES", 26.04, 0.960, 25.00, 26.04),  # +1.04
        ("0xc3", "t12", "Will SOL close above $200 on May 4?",      "NO",  26.32, 0.950, 25.00, 26.32),  # +1.32
        ("0xc4", "t13", "Will the Knicks beat the Heat Game 2?",    "YES", 26.32, 0.950, 25.00, 0.00),   # -25.00 dispute
        ("0xc5", "t14", "Will Mavericks win game May 2?",           "YES", 26.60, 0.940, 25.00, 26.60),  # +1.60
        ("0xc6", "t15", "Will BTC close above $95k on Apr 28?",     "YES", 27.17, 0.920, 25.00, 27.17),  # +2.17
        ("0xc7", "t16", "Will Celtics beat 76ers Game 4?",          "YES", 26.46, 0.945, 25.00, 26.46),  # +1.46
        ("0xc8", "t17", "Will ETH close above $4500 on Apr 24?",    "NO",  26.18, 0.955, 25.00, 26.18),  # +1.18
    ]
    for cid, tid, q, side, tokens, px, cost, payout in closed_positions:
        store.open_position(cid, tid, q, side, tokens, px, cost, dry_run=True)
        store.mark_resolved(cid, payout_usd=payout, notes=f"pnl={payout-cost:+.2f}")

    s = store.summary()
    print(f"seeded {db_path}")
    print(f"  open : {s['open_count']} positions, ${s['open_exposure']:.2f}")
    print(f"  closed: {s['closed_count']} positions, PnL ${s['realized_pnl']:+.2f}, "
          f"win rate {s['win_rate']*100:.0f}%")


if __name__ == "__main__":
    main()
