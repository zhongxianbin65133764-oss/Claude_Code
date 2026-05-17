"""Seed positions.db with synthetic data to preview the dashboard.

Populates BOTH ideal and realistic numbers so the realism-layer UI
shows the ideal-vs-realistic gap.
"""
from __future__ import annotations

import os
import random
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from polymarket_arb.config import CONFIG
from polymarket_arb.position_store import PositionStore


def main(db_path: str = CONFIG.db_path) -> None:
    if os.path.exists(db_path):
        os.remove(db_path)
    store = PositionStore(db_path)

    # ---- Open positions: 3 in flight ----
    open_specs = [
        ("0xopen1", "t1", "Will the Lakers win Game 3 of the playoffs?",   "YES", 0.955),
        ("0xopen2", "t2", "Will ETH close above $5000 on May 16?",          "NO",  0.900),
        ("0xopen3", "t3", "Will Chiefs beat Bengals on May 11?",            "YES", 0.940),
    ]
    for cid, tid, q, side, price in open_specs:
        ideal_tokens = 25.0 / price
        # realistic: 70% fill ratio + $0.10 gas
        real_tokens = ideal_tokens * 0.72
        real_cost = real_tokens * price + 0.10
        store.open_position(
            cid, tid, q, side, ideal_tokens, price, 25.00, dry_run=True,
            realistic_tokens=real_tokens,
            realistic_cost_usd=real_cost,
            sim_flags="fill_ratio=72%;gas=$0.10",
        )

    # ---- Closed positions: 8 settlements ----
    # ideal_payout, realistic_outcome ('won', 'adverse', 'disputed', 'lost')
    closed_specs = [
        # (cid, tid, q, side, price, side_won, sim_outcome)
        ("0xc1", "t10", "Will BTC close above $100k on May 8?",    "NO",  0.925, True,  "won"),
        ("0xc2", "t11", "Will the Warriors beat the Suns May 6?",  "YES", 0.960, True,  "won"),
        ("0xc3", "t12", "Will SOL close above $200 on May 4?",     "NO",  0.950, True,  "won"),
        ("0xc4", "t13", "Will the Knicks beat the Heat Game 2?",   "YES", 0.950, True,  "disputed"),  # UMA flipped -> lost
        ("0xc5", "t14", "Will Mavericks win game May 2?",          "YES", 0.940, True,  "won"),
        ("0xc6", "t15", "Will BTC close above $95k on Apr 28?",    "YES", 0.920, True,  "adverse"),   # seller knew
        ("0xc7", "t16", "Will Celtics beat 76ers Game 4?",         "YES", 0.945, True,  "won"),
        ("0xc8", "t17", "Will ETH close above $4500 on Apr 24?",   "NO",  0.955, True,  "won"),
    ]
    rng = random.Random(42)
    for cid, tid, q, side, price, side_won, sim in closed_specs:
        ideal_tokens = 25.0 / price
        ideal_payout = ideal_tokens if side_won else 0.0
        fill_ratio = rng.triangular(0.5, 0.9, 0.72)
        real_tokens = ideal_tokens * fill_ratio
        real_cost = real_tokens * price + 0.10
        flags = [f"fill_ratio={fill_ratio:.0%}", "gas=$0.10"]
        if sim == "adverse":
            real_payout = 0.0
            flags.append("adverse_fill")
        elif sim == "disputed":
            real_payout = 0.0 if side_won else real_tokens
            flags.append("uma_dispute")
        else:
            real_payout = real_tokens if side_won else 0.0
        sim_flags = ";".join(flags)

        store.open_position(
            cid, tid, q, side, ideal_tokens, price, 25.00, dry_run=True,
            realistic_tokens=real_tokens,
            realistic_cost_usd=real_cost,
            sim_flags=sim_flags,
        )
        store.mark_resolved(
            cid, payout_usd=ideal_payout,
            notes=f"sim={sim} pnl=${ideal_payout - 25.00:+.2f}",
            realistic_payout_usd=real_payout,
        )

    # ---- Verifications: simulate scan-then-recheck observations ----
    # Make it look like ~70% fill rate, with some misses
    now = datetime.now(timezone.utc)
    verif_specs = [
        # (would_fill, detected_ask, verified_ask)
        (True,  0.955, 0.955), (True,  0.940, 0.945), (False, 0.950, 0.965),
        (True,  0.945, 0.948), (True,  0.930, 0.930), (False, 0.955, 0.975),
        (True,  0.948, 0.952), (False, 0.940, 0.970), (True,  0.935, 0.935),
        (True,  0.952, 0.955), (True,  0.945, 0.948), (False, 0.955, 0.962),
        (True,  0.940, 0.942), (True,  0.948, 0.950), (True,  0.930, 0.935),
    ]
    for i, (would_fill, det_ask, ver_ask) in enumerate(verif_specs):
        detected = now - timedelta(minutes=(len(verif_specs) - i) * 10)
        verified = detected + timedelta(seconds=60)
        intended = 25.0
        if would_fill:
            real_tokens = (intended / det_ask) * rng.triangular(0.55, 0.85, 0.72)
            real_cost = real_tokens * ver_ask
        else:
            real_tokens = 0.0
            real_cost = 0.0
        store.record_verification(
            condition_id=f"0xv{i}", token_id=f"vt{i}", side="YES",
            detected_at=detected.isoformat(),
            detected_ask=det_ask,
            detected_depth_usd=200.0,
            intended_usd=intended,
            verified_at=verified.isoformat(),
            verified_ask=ver_ask,
            verified_depth_usd=100.0 if would_fill else 30.0,
            would_have_filled=would_fill,
            realistic_tokens=real_tokens,
            realistic_cost_usd=real_cost,
        )

    s = store.summary()
    v = store.verification_stats()
    print(f"seeded {db_path}")
    print(f"  open    : {s['open_count']} positions, ${s['open_exposure']:.2f}")
    print(f"  closed  : {s['closed_count']} positions")
    print(f"  ideal PnL    : ${s['realized_pnl']:+.2f}")
    print(f"  realistic PnL: ${s['realistic_pnl']:+.2f}")
    print(f"  verifications: {v['detected']} detected, "
          f"{v['filled']} filled ({v['fill_rate']*100:.0f}%), "
          f"capture {v['capture_ratio']*100:.0f}%")


if __name__ == "__main__":
    main()
