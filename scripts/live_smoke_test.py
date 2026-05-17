"""Live smoke test against the real Polymarket + Coinbase APIs.

READ-ONLY: does not write to positions.db, does not place orders.
Just shows what the strategy WOULD do right now, with every
intermediate decision logged.

Use this to:
  - Sanity-check that markets are being discovered
  - See which markets get rejected and why
  - Watch the oracle resolve real crypto markets
  - Confirm orderbook depth before going live

Run:
  python scripts/live_smoke_test.py             # 20 markets, all filters
  python scripts/live_smoke_test.py --limit 50  # more
  python scripts/live_smoke_test.py --no-book   # skip book fetches (fast)
  python scripts/live_smoke_test.py --no-color  # plain text output
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from polymarket_arb.config import CONFIG
from polymarket_arb.gamma_client import fetch_resolving_markets
from polymarket_arb.orderbook import fetch_book
from polymarket_arb.price_oracle import verify_crypto_market
from polymarket_arb.safety import book_passes_safety, market_passes_safety
from polymarket_arb.strategy import _fill_within_budget


# ANSI colors (toggled off with --no-color)
class Color:
    GREEN = "\033[32m"
    RED = "\033[31m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    DIM = "\033[2m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


def disable_colors() -> None:
    for attr in ("GREEN", "RED", "YELLOW", "BLUE", "DIM", "BOLD", "RESET"):
        setattr(Color, attr, "")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=20,
                        help="Max markets to evaluate (default 20)")
    parser.add_argument("--no-color", action="store_true",
                        help="Plain text output")
    parser.add_argument("--no-oracle", action="store_true",
                        help="Skip Coinbase oracle calls")
    parser.add_argument("--no-book", action="store_true",
                        help="Skip orderbook fetches (faster, less info)")
    args = parser.parse_args()

    if args.no_color:
        disable_colors()
    C = Color

    print(f"{C.BOLD}Polymarket Arb Bot — Live Smoke Test (read-only){C.RESET}")
    print("=" * 72)
    print(f"  Mode             : DRY (no orders, no DB writes)")
    print(f"  Market age window: {CONFIG.min_market_age_hours:.0f}h .. {CONFIG.max_market_age_days:.0f}d after end_date")
    print(f"  Price band       : ${CONFIG.min_buy_price:.2f}..${CONFIG.max_buy_price:.2f}"
          f" (oracle-verified up to ${CONFIG.oracle_verified_max_buy_price:.2f})")
    print(f"  Subcat filter    : {'ON' if CONFIG.use_subcategory_filter else 'off'}")
    print(f"  Oracle           : {'ON' if CONFIG.use_oracle and not args.no_oracle else 'off'}")
    print(f"  Min market vol   : ${CONFIG.min_market_volume_usd:.0f}")
    print(f"  Min book depth   : ${CONFIG.min_book_depth_usd:.0f}")
    print(f"  Per-position cap : ${CONFIG.max_position_size_usd:.0f}")
    print("-" * 72)

    stats = {
        "scanned": 0,
        "safety_rej": 0,
        "book_rej": 0,
        "oracle_skipped_side": 0,
        "opportunities": 0,
        "oracle_boosted": 0,
        "total_cost": 0.0,
    }
    rejection_reasons: Counter = Counter()
    subcategories: Counter = Counter()
    t0 = time.monotonic()

    try:
        markets = fetch_resolving_markets(
            CONFIG.gamma_base,
            CONFIG.min_market_age_hours,
            CONFIG.max_market_age_days,
            min_volume_usd=CONFIG.min_market_volume_usd,
        )
        for market in markets:
            if stats["scanned"] >= args.limit:
                break
            stats["scanned"] += 1
            n = stats["scanned"]
            q = market.question[:80]

            print()
            print(f"[{n:2d}] {C.BOLD}{q}{C.RESET}")
            print(f"     {C.DIM}category={market.category or '-'}  "
                  f"end={market.end_date.date()} ({market.hours_past_end:.1f}h ago)  "
                  f"vol=${market.volume_usd:,.0f}{C.RESET}")

            ok, reason, classified = market_passes_safety(
                market, use_subcategory_filter=CONFIG.use_subcategory_filter,
            )
            if classified:
                subcategories[classified.subcategory] += 1
                conf_color = (C.GREEN if classified.confidence == "high"
                              else C.YELLOW if classified.confidence == "medium"
                              else C.DIM)
                print(f"     classifier: {conf_color}{classified.subcategory}"
                      f"{C.RESET} ({classified.confidence})", end="")
                if classified.subcategory == "crypto_price":
                    print(f"  → {classified.ticker} {classified.direction} "
                          f"${classified.threshold_usd:,.0f} on {classified.target_date}")
                else:
                    print()

            if not ok:
                stats["safety_rej"] += 1
                bucket = reason.split(":")[0].split("(")[0].strip()
                rejection_reasons[bucket] += 1
                print(f"     {C.RED}✗ SAFETY REJECT{C.RESET}: {reason}")
                continue

            # Oracle check (crypto only)
            oracle_side: str | None = None
            effective_max = CONFIG.max_buy_price
            edge_source = "default"
            if (CONFIG.use_oracle and not args.no_oracle
                    and classified is not None
                    and classified.subcategory == "crypto_price"
                    and classified.confidence == "high"):
                verdict = verify_crypto_market(classified)
                if verdict.winning_side:
                    oracle_side = verdict.winning_side
                    effective_max = CONFIG.oracle_verified_max_buy_price
                    edge_source = "oracle_verified"
                    print(f"     {C.BLUE}oracle{C.RESET}: "
                          f"{classified.ticker} closed ${verdict.actual_price:,.2f} "
                          f"→ {C.BOLD}{oracle_side} wins{C.RESET}, max raised to ${effective_max:.3f}")
                else:
                    print(f"     {C.DIM}oracle: no verdict ({verdict.error}){C.RESET}")

            if args.no_book:
                continue

            sides = [("YES", market.yes_token_id), ("NO", market.no_token_id)]
            for side, token_id in sides:
                if oracle_side is not None and side != oracle_side:
                    stats["oracle_skipped_side"] += 1
                    print(f"     {C.DIM}{side}: skipped (oracle says {oracle_side} wins){C.RESET}")
                    continue

                book = fetch_book(CONFIG.clob_base, token_id)
                if book is None:
                    print(f"     {C.YELLOW}{side}: no book{C.RESET}")
                    continue

                ok_b, reason_b = book_passes_safety(
                    book, effective_max,
                    CONFIG.min_buy_price, CONFIG.min_book_depth_usd,
                )
                ba = book.best_ask if book.best_ask is not None else 0
                bb = book.best_bid if book.best_bid is not None else 0
                if not ok_b:
                    stats["book_rej"] += 1
                    print(f"     {C.DIM}{side}: ask {ba:.3f} bid {bb:.3f} | "
                          f"{reason_b}{C.RESET}")
                    continue

                tokens, cost = _fill_within_budget(
                    book, CONFIG.max_position_size_usd, effective_max,
                )
                avg = cost / tokens if tokens > 0 else 0
                stats["opportunities"] += 1
                stats["total_cost"] += cost
                if edge_source == "oracle_verified":
                    stats["oracle_boosted"] += 1
                tag = f" ({C.BLUE}oracle-verified{C.RESET})" if edge_source == "oracle_verified" else ""
                print(f"     {C.GREEN}✓ {side}: ask {ba:.3f} → WOULD QUEUE "
                      f"${cost:.2f} @ avg {avg:.3f}{C.RESET}{tag}")
    except KeyboardInterrupt:
        print("\n[interrupted]")
    except Exception as e:
        print(f"\n{C.RED}ERROR: {e}{C.RESET}")
        raise

    elapsed = time.monotonic() - t0
    print()
    print("=" * 72)
    print(f"{C.BOLD}Summary{C.RESET} ({elapsed:.1f}s)")
    print("-" * 72)
    print(f"  Markets scanned ............ {stats['scanned']:>4}")
    print(f"  Rejected by safety ......... {stats['safety_rej']:>4}")
    for reason, count in rejection_reasons.most_common():
        print(f"      {reason:<40} {count:>3}")
    print(f"  Rejected by book ........... {stats['book_rej']:>4}")
    print(f"  Sides skipped by oracle .... {stats['oracle_skipped_side']:>4}")
    print()
    color = C.GREEN if stats['opportunities'] > 0 else C.YELLOW
    print(f"  {color}{C.BOLD}WOULD QUEUE: {stats['opportunities']} opportunities, "
          f"${stats['total_cost']:.2f} ideal total{C.RESET}")
    print(f"      oracle-boosted ......... {stats['oracle_boosted']:>4}")
    print()
    if subcategories:
        print(f"  Subcategory distribution (of {sum(subcategories.values())} classified):")
        for sub, n in subcategories.most_common():
            bar = "█" * min(40, n)
            print(f"      {sub:<20} {n:>3}  {bar}")
    print()
    if stats['scanned'] == 0:
        print(f"  {C.YELLOW}No markets returned by Gamma. Either the API moved or there{C.RESET}")
        print(f"  {C.YELLOW}are no markets ending in your time window right now.{C.RESET}")
    elif stats['opportunities'] == 0:
        print(f"  {C.YELLOW}No opportunities right now. Normal — try at a different time{C.RESET}")
        print(f"  {C.YELLOW}of day or loosen MAX_BUY_PRICE / MIN_BOOK_DEPTH_USD in .env.{C.RESET}")
    else:
        print(f"  {C.GREEN}Healthy. Run `python -m polymarket_arb.main` to start collecting.{C.RESET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
