"""Settlement watcher.

Periodically polls Gamma for the markets we hold positions in, and
when a market is reported as resolved (umaResolutionStatus=resolved
or the market's closed=true with a resolved outcome), updates our
position store with realised PnL.
"""
from __future__ import annotations

import logging

import requests

from .config import Config
from .position_store import PositionStore

log = logging.getLogger(__name__)


def _fetch_market_by_condition(gamma_base: str, condition_id: str) -> dict | None:
    try:
        resp = requests.get(
            f"{gamma_base}/markets",
            params={"condition_ids": condition_id, "limit": 1},
            timeout=10,
        )
        resp.raise_for_status()
        items = resp.json()
        return items[0] if items else None
    except (requests.RequestException, ValueError, IndexError) as e:
        log.warning("settle lookup failed for %s: %s", condition_id, e)
        return None


def _resolved_outcome(raw: dict) -> str | None:
    """Return 'YES' / 'NO' / None depending on UMA resolution state."""
    if not raw.get("closed"):
        return None
    # Polymarket sets 'umaResolutionStatuses' or 'resolutionSource' after
    # UMA returns. The simplest signal is outcomePrices: ['1','0'] or ['0','1'].
    prices_raw = raw.get("outcomePrices")
    if not prices_raw:
        return None
    import json
    try:
        prices = json.loads(prices_raw) if isinstance(prices_raw, str) else prices_raw
        yes_p, no_p = float(prices[0]), float(prices[1])
    except (json.JSONDecodeError, ValueError, IndexError):
        return None
    if yes_p > 0.99:
        return "YES"
    if no_p > 0.99:
        return "NO"
    return None  # ambiguous (50/50 split, dispute, etc.)


def sweep_settlements(config: Config, store: PositionStore) -> int:
    """Look at all open positions; mark resolved ones. Returns count resolved."""
    resolved_count = 0
    for pos in store.open_positions():
        raw = _fetch_market_by_condition(config.gamma_base, pos.condition_id)
        if not raw:
            continue
        outcome = _resolved_outcome(raw)
        if outcome is None:
            continue
        payout = pos.tokens if outcome == pos.side else 0.0
        pnl = payout - pos.cost_usd
        log.info(
            "SETTLED %s: side=%s, outcome=%s, tokens=%.2f, "
            "cost=$%.2f, payout=$%.2f, PnL=$%+.2f",
            pos.condition_id, pos.side, outcome, pos.tokens,
            pos.cost_usd, payout, pnl,
        )
        store.mark_resolved(
            condition_id=pos.condition_id,
            payout_usd=payout,
            notes=f"outcome={outcome} pnl={pnl:+.2f}",
        )
        resolved_count += 1
    return resolved_count
