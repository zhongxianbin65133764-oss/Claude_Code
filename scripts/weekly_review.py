"""Weekly review tool.

Reads positions.db and prints a structured report telling the user
WHAT happened this week and WHERE to focus optimization effort.

Output sections:
  1. Activity summary
  2. Loss decomposition (where realistic-vs-ideal money went)
  3. Performance by subcategory (which market types win/lose)
  4. Performance by entry-price bucket (find the sweet spot)
  5. Empirical vs configured friction (calibrate the model)
  6. Top recommendations (prioritized next changes)

Run:  python scripts/weekly_review.py [--db positions.db]
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from polymarket_arb.config import CONFIG
from polymarket_arb.position_store import PositionStore
from polymarket_arb.question_classifier import classify


# -------------------- helpers --------------------

def _ascii_table(headers: list[str], rows: list[list[str]], aligns: list[str]) -> str:
    """Render a simple monospace table. `aligns` is per-col 'l' or 'r'."""
    if not rows:
        return "  (no data)"
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    def fmt_row(cells: list[str]) -> str:
        parts = []
        for cell, w, a in zip(cells, widths, aligns):
            parts.append(cell.rjust(w) if a == "r" else cell.ljust(w))
        return "  " + " │ ".join(parts)

    sep = "  " + "─┼─".join("─" * w for w in widths)
    out = [fmt_row(headers), sep]
    for row in rows:
        out.append(fmt_row(row))
    return "\n".join(out)


def _pct(x: float) -> str:
    return f"{x * 100:.0f}%"


def _money(x: float, sign: bool = True) -> str:
    return (f"{x:+.2f}" if sign else f"{x:.2f}").replace("+-", "-")


# -------------------- sections --------------------

def section_activity(store: PositionStore, db_path: str) -> str:
    s = store.summary()
    v = store.verification_stats()
    opens = store.open_positions()
    closes = store.closed_positions()
    all_pos = opens + closes
    if all_pos:
        first = min(p.opened_at for p in all_pos)
        last = max((p.closed_at or p.opened_at) for p in all_pos)
        window = f"{first.date()} → {last.date()}  ({(last - first).total_seconds()/86400:.1f} days)"
    else:
        window = "no positions yet"

    db_size = os.path.getsize(db_path) if os.path.exists(db_path) else 0
    realistic_pnl = s["realistic_pnl"] if s["realistic_pnl"] != s["realized_pnl"] else s["realized_pnl"]
    ideal_pnl = s["realized_pnl"]
    ideal_roi = s["avg_return_pct"]
    real_roi = s["realistic_avg_return_pct"]

    lines = [
        f"Data window  : {window}",
        f"DB           : {db_path} ({db_size/1024:.1f} KB)",
        "",
        f"Opportunities detected ...  {v['detected']}",
        f"Verified as fillable .....  {v['filled']}  ({_pct(v['fill_rate'])})",
        f"Positions opened .........  {s['open_count'] + s['closed_count']}",
        f"  - currently open .......  {s['open_count']}  (${s['open_exposure']:.2f} on the line)",
        f"  - resolved .............  {s['closed_count']}",
        "",
        f"Realistic PnL ............  ${_money(realistic_pnl)}  ({_money(real_roi, sign=True)}% ROI)",
        f"Ideal PnL (no friction) ..  ${_money(ideal_pnl)}  ({_money(ideal_roi, sign=True)}% ROI)",
        f"Capture ratio ............  {_pct(v['capture_ratio'])}  (real$ / intended$)",
    ]
    return "\n".join(lines)


def section_loss_decomposition(store: PositionStore) -> str:
    """Break down where realistic-vs-ideal money went on closed positions."""
    closes = store.closed_positions()
    if not closes:
        return "(no closed positions yet)"

    ideal_pnl = sum((p.payout_usd or 0) - p.cost_usd for p in closes)
    real_pnl = sum(
        (p.realistic_payout_usd if p.realistic_payout_usd is not None else (p.payout_usd or 0))
        - (p.realistic_cost_usd if p.realistic_cost_usd is not None else p.cost_usd)
        for p in closes
    )
    destroyed = ideal_pnl - real_pnl  # how much friction cost us

    # Categorize each closed position
    adverse_loss = 0.0
    dispute_loss = 0.0
    fill_gas_loss = 0.0
    for p in closes:
        flags = p.sim_flags or ""
        ideal = (p.payout_usd or 0) - p.cost_usd
        real_payout = p.realistic_payout_usd if p.realistic_payout_usd is not None else (p.payout_usd or 0)
        real_cost = p.realistic_cost_usd if p.realistic_cost_usd is not None else p.cost_usd
        real = real_payout - real_cost
        diff = ideal - real
        if "adverse_fill" in flags:
            adverse_loss += diff
        elif "uma_dispute" in flags:
            dispute_loss += diff
        else:
            fill_gas_loss += diff

    def share(x: float) -> str:
        return f"({_pct(x / destroyed)})" if destroyed > 1e-6 else ""

    lines = [
        f"Ideal PnL          : ${_money(ideal_pnl)}",
        f"Realistic PnL      : ${_money(real_pnl)}",
        f"Destroyed by friction : ${_money(-destroyed, sign=True)}",
        "",
        f"Breakdown:",
        f"  Partial fills + gas .....  ${_money(-fill_gas_loss, sign=True)}  {share(fill_gas_loss)}",
        f"  Adverse selection .......  ${_money(-adverse_loss, sign=True)}  {share(adverse_loss)}",
        f"  UMA disputes ............  ${_money(-dispute_loss, sign=True)}  {share(dispute_loss)}",
    ]
    return "\n".join(lines)


def section_by_subcategory(store: PositionStore) -> str:
    closes = store.closed_positions()
    if not closes:
        return "(no closed positions yet)"

    buckets: dict[str, dict] = defaultdict(
        lambda: {"n": 0, "wins": 0, "real_pnl": 0.0, "disputes": 0}
    )
    for p in closes:
        cm = classify(p.question)
        sub = cm.subcategory
        buckets[sub]["n"] += 1
        real_payout = p.realistic_payout_usd if p.realistic_payout_usd is not None else (p.payout_usd or 0)
        real_cost = p.realistic_cost_usd if p.realistic_cost_usd is not None else p.cost_usd
        pnl = real_payout - real_cost
        buckets[sub]["real_pnl"] += pnl
        if (p.payout_usd or 0) > p.cost_usd:
            buckets[sub]["wins"] += 1
        if "uma_dispute" in (p.sim_flags or ""):
            buckets[sub]["disputes"] += 1

    rows = []
    for sub, b in sorted(buckets.items(), key=lambda kv: -kv[1]["real_pnl"]):
        rows.append([
            sub,
            str(b["n"]),
            _pct(b["wins"] / b["n"]) if b["n"] else "-",
            f"${_money(b['real_pnl'])}",
            _pct(b["disputes"] / b["n"]) if b["n"] else "-",
        ])
    return _ascii_table(
        ["Subcategory", "N", "Win %", "Realistic PnL", "Dispute %"],
        rows,
        ["l", "r", "r", "r", "r"],
    )


def section_by_price_bucket(store: PositionStore) -> str:
    closes = store.closed_positions()
    if not closes:
        return "(no closed positions yet)"
    boundaries = [0.88, 0.91, 0.93, 0.95, 0.97, 1.00]
    bucket_keys = [f"{lo:.2f}–{hi:.2f}" for lo, hi in zip(boundaries, boundaries[1:])]
    buckets: dict[str, dict] = {k: {"n": 0, "wins": 0, "real_pnl": 0.0} for k in bucket_keys}
    for p in closes:
        for lo, hi, key in zip(boundaries, boundaries[1:], bucket_keys):
            if lo <= p.avg_price < hi:
                buckets[key]["n"] += 1
                if (p.payout_usd or 0) > p.cost_usd:
                    buckets[key]["wins"] += 1
                real_payout = p.realistic_payout_usd if p.realistic_payout_usd is not None else (p.payout_usd or 0)
                real_cost = p.realistic_cost_usd if p.realistic_cost_usd is not None else p.cost_usd
                buckets[key]["real_pnl"] += real_payout - real_cost
                break
    rows = []
    for key in bucket_keys:
        b = buckets[key]
        if b["n"] == 0:
            continue
        rows.append([
            key, str(b["n"]),
            _pct(b["wins"] / b["n"]),
            f"${_money(b['real_pnl'])}",
            f"${_money(b['real_pnl'] / b['n'])}",
        ])
    return _ascii_table(
        ["Price bucket", "N", "Win %", "Total real PnL", "Avg per trade"],
        rows,
        ["l", "r", "r", "r", "r"],
    )


def section_friction_calibration(store: PositionStore) -> tuple[str, dict]:
    v = store.verification_stats()
    closes = store.closed_positions()
    measured_adverse = 0
    measured_dispute = 0
    n_closed = len(closes)
    for p in closes:
        flags = p.sim_flags or ""
        if "adverse_fill" in flags:
            measured_adverse += 1
        if "uma_dispute" in flags:
            measured_dispute += 1

    measured = {
        "fill_rate": v["fill_rate"],
        "adverse_rate": (measured_adverse / n_closed) if n_closed else 0.0,
        "dispute_rate": (measured_dispute / n_closed) if n_closed else 0.0,
    }
    configured = {
        "fill_rate": CONFIG.expected_fill_ratio,
        "adverse_rate": CONFIG.adverse_fill_rate,
        "dispute_rate": CONFIG.uma_dispute_rate,
    }

    def hint(meas: float, cfg: float, lower_is_worse: bool) -> str:
        if not n_closed:
            return ""
        ratio = meas / cfg if cfg > 0 else 0
        if lower_is_worse and meas < cfg * 0.9:
            return "⚠ measured worse than configured — lower"
        if not lower_is_worse and meas > cfg * 1.5:
            return "⚠ measured worse than configured — raise"
        return "✓ within tolerance"

    rows = [
        ["Fill rate", _pct(configured["fill_rate"]), _pct(measured["fill_rate"]),
         hint(measured["fill_rate"], configured["fill_rate"], lower_is_worse=True)],
        ["Adverse rate", _pct(configured["adverse_rate"]), _pct(measured["adverse_rate"]),
         hint(measured["adverse_rate"], configured["adverse_rate"], lower_is_worse=False)],
        ["UMA dispute rate", _pct(configured["dispute_rate"]), _pct(measured["dispute_rate"]),
         hint(measured["dispute_rate"], configured["dispute_rate"], lower_is_worse=False)],
    ]
    table = _ascii_table(
        ["Parameter", "Configured", "Measured", "Hint"],
        rows, ["l", "r", "r", "l"],
    )
    return table, {"measured": measured, "configured": configured, "n_closed": n_closed}


def section_recommendations(
    store: PositionStore,
    friction: dict,
) -> str:
    """Prioritized list of suggested next actions."""
    closes = store.closed_positions()
    n = friction["n_closed"]
    if n < 10:
        return (f"  Only {n} closed positions so far. Recommendations need at least\n"
                f"  10-20 settled trades for signal. Keep the dry-run going.")

    measured = friction["measured"]
    cfg = friction["configured"]
    recs: list[str] = []

    # 1. Recalibrate any friction parameter that's significantly off.
    if measured["adverse_rate"] > cfg["adverse_rate"] * 1.5:
        recs.append(
            f"Adverse rate measured {_pct(measured['adverse_rate'])} vs configured "
            f"{_pct(cfg['adverse_rate'])}.\n"
            f"     → In .env set ADVERSE_FILL_RATE={measured['adverse_rate']:.3f}\n"
            f"     → Also consider raising MIN_BOOK_DEPTH_USD from "
            f"${CONFIG.min_book_depth_usd:.0f} to ${CONFIG.min_book_depth_usd * 2:.0f} "
            f"to filter the thin trades that are usually adverse."
        )
    if measured["dispute_rate"] > cfg["dispute_rate"] * 1.5:
        recs.append(
            f"UMA dispute rate measured {_pct(measured['dispute_rate'])} vs configured "
            f"{_pct(cfg['dispute_rate'])}.\n"
            f"     → In .env set UMA_DISPUTE_RATE={measured['dispute_rate']:.3f}\n"
            f"     → Check section 'Performance by subcategory' above. If disputes\n"
            f"       cluster in one subcategory, remove it from\n"
            f"       DEFAULT_SAFE_SUBCATEGORIES in question_classifier.py."
        )
    if measured["fill_rate"] < cfg["fill_rate"] * 0.85:
        recs.append(
            f"Fill rate measured {_pct(measured['fill_rate'])} vs configured "
            f"{_pct(cfg['fill_rate'])}.\n"
            f"     → In .env set EXPECTED_FILL_RATIO={measured['fill_rate']:.2f}\n"
            f"     → Other bots are outracing us. Next architectural step is the\n"
            f"       WebSocket-based detector (drops 90s polling to <5s)."
        )

    # 2. If a price bucket is consistently negative, suggest tightening MAX_BUY_PRICE.
    buckets: dict[tuple[float, float], list[float]] = defaultdict(list)
    boundaries = [0.88, 0.91, 0.93, 0.95, 0.97]
    for p in closes:
        for lo, hi in zip(boundaries, boundaries[1:]):
            if lo <= p.avg_price < hi:
                real_payout = p.realistic_payout_usd if p.realistic_payout_usd is not None else (p.payout_usd or 0)
                real_cost = p.realistic_cost_usd if p.realistic_cost_usd is not None else p.cost_usd
                buckets[(lo, hi)].append(real_payout - real_cost)
                break
    for (lo, hi), pnls in buckets.items():
        if len(pnls) >= 3 and sum(pnls) < 0:
            recs.append(
                f"Price bucket {lo:.2f}–{hi:.2f} has {len(pnls)} trades with negative\n"
                f"     realistic PnL ${sum(pnls):+.2f}. Consider lowering\n"
                f"     MAX_BUY_PRICE to {lo:.2f} in .env."
            )
            break

    if not recs:
        recs.append("No urgent issues. Friction parameters and price thresholds look\n"
                    "     reasonable. Consider the WebSocket detector to push fill\n"
                    "     rate further, or increase max_total_exposure_usd modestly.")

    return "\n".join(f"  {i+1}. {r}" for i, r in enumerate(recs[:4]))


# -------------------- main --------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Weekly review of the arb bot")
    parser.add_argument("--db", default=CONFIG.db_path)
    args = parser.parse_args()

    if not os.path.exists(args.db):
        print(f"No DB at {args.db}. Run the bot first or seed demo data.")
        return 1

    store = PositionStore(args.db)
    print("═" * 64)
    print("  Polymarket Arb Bot — Weekly Review")
    print(f"  Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("═" * 64)
    print()
    print("📊 Activity")
    print("─" * 64)
    print(section_activity(store, args.db))
    print()
    print("🩸 Loss decomposition")
    print("─" * 64)
    print(section_loss_decomposition(store))
    print()
    print("🎯 Performance by subcategory")
    print("─" * 64)
    print(section_by_subcategory(store))
    print()
    print("💰 Performance by entry-price bucket")
    print("─" * 64)
    print(section_by_price_bucket(store))
    print()
    print("⚙️  Empirical vs configured friction")
    print("─" * 64)
    table, friction = section_friction_calibration(store)
    print(table)
    print()
    print("💡 Top recommendations")
    print("─" * 64)
    print(section_recommendations(store, friction))
    print()
    print("═" * 64)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
