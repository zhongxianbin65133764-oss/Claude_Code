"""Independent price oracle for crypto-price markets.

When a market says "Will BTC close above $100k on May 8?", we don't
need UMA to tell us the answer — we can look up the actual closing
price from Coinbase ourselves. If we know the answer independently:

  - We're not betting on UMA's fairness; we're betting on UMA being
    accurate, which is much more likely.
  - We can be more aggressive on price (e.g., buy up to 0.98 instead
    of 0.96), since we've eliminated the dispute tail risk.
  - We can SKIP markets where the "winning" side per market price
    disagrees with the actual outcome (sometimes the market is
    mispriced because it's the losing side that's at 95c).

Uses Coinbase Exchange's public candle endpoint (no auth, no key).
Falls back gracefully on network errors — caller must handle
PriceVerdict(winning_side=None).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone

import requests

from .question_classifier import ClassifiedMarket

log = logging.getLogger(__name__)


# Polymarket crypto-close markets typically settle on UTC midnight of
# the named date. We grab the daily candle for that day and use its close.
# Coinbase product naming: {TICKER}-USD.
_COINBASE_BASE = "https://api.exchange.coinbase.com"
_TIMEOUT_SECONDS = 8.0


@dataclass
class PriceVerdict:
    """Verdict on which side of a crypto-price market should pay out."""
    winning_side: str | None        # 'YES' | 'NO' | None (can't determine)
    actual_price: float | None      # close price on target_date
    source: str                     # e.g. "coinbase:BTC-USD"
    error: str | None = None


def _fetch_close_price(
    ticker: str,
    target_date: date,
) -> tuple[float | None, str | None]:
    """Return (close_price, error). Uses Coinbase daily candles."""
    # Coinbase wants ISO timestamps and granularity in seconds.
    start_dt = datetime.combine(target_date, time(0, 0), tzinfo=timezone.utc)
    end_dt = start_dt + timedelta(days=1)

    url = f"{_COINBASE_BASE}/products/{ticker}-USD/candles"
    params = {
        "start": start_dt.isoformat(),
        "end": end_dt.isoformat(),
        "granularity": 86400,
    }
    try:
        resp = requests.get(url, params=params, timeout=_TIMEOUT_SECONDS)
        resp.raise_for_status()
        candles = resp.json()
    except requests.RequestException as e:
        return None, f"network error: {e}"
    except ValueError as e:
        return None, f"bad JSON: {e}"

    # Coinbase returns [[timestamp, low, high, open, close, volume], ...].
    # When asking for a single day we expect 1 candle.
    if not isinstance(candles, list) or not candles:
        return None, "no candle returned"
    try:
        close = float(candles[0][4])
    except (IndexError, TypeError, ValueError):
        return None, f"unexpected candle shape: {candles[0]}"
    return close, None


def verify_crypto_market(
    cm: ClassifiedMarket,
    fetch: callable = _fetch_close_price,
) -> PriceVerdict:
    """Decide which side of a crypto-price market wins.

    Caller should already have checked that cm.subcategory == 'crypto_price'
    and cm.confidence == 'high'.
    """
    if cm.subcategory != "crypto_price":
        return PriceVerdict(None, None, "n/a", error="not a crypto market")
    if not cm.ticker or cm.threshold_usd is None or cm.target_date is None:
        return PriceVerdict(None, None, "n/a", error="missing crypto facts")

    # Only verify after the target date has passed.
    if cm.target_date >= date.today():
        return PriceVerdict(
            None, None, f"coinbase:{cm.ticker}-USD",
            error=f"target date {cm.target_date} not yet past",
        )

    actual, err = fetch(cm.ticker, cm.target_date)
    if actual is None:
        return PriceVerdict(
            None, None, f"coinbase:{cm.ticker}-USD",
            error=err or "fetch returned None",
        )

    # Determine which side wins.
    if cm.direction == "above":
        side = "YES" if actual > cm.threshold_usd else "NO"
    elif cm.direction == "below":
        side = "YES" if actual < cm.threshold_usd else "NO"
    else:
        return PriceVerdict(
            None, actual, f"coinbase:{cm.ticker}-USD",
            error=f"unknown direction: {cm.direction}",
        )

    return PriceVerdict(
        winning_side=side,
        actual_price=actual,
        source=f"coinbase:{cm.ticker}-USD",
    )
