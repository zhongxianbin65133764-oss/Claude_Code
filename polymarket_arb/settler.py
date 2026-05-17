"""Settlement watcher.

For each open position:
  - look up the market on Gamma
  - if outcomePrices indicates a resolved YES or NO winner, book PnL
  - in dry-run, also compute realistic_payout via the friction model
    (which may flip the outcome due to adverse-fill or UMA-dispute draws)
"""
from __future__ import annotations

import json
import logging

import requests

from .config import Config
from .friction import FrictionModel
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
    if not raw.get("closed"):
        return None
    prices_raw = raw.get("outcomePrices")
    if not prices_raw:
        return None
    try:
        prices = json.loads(prices_raw) if isinstance(prices_raw, str) else prices_raw
        yes_p, no_p = float(prices[0]), float(prices[1])
    except (json.JSONDecodeError, ValueError, IndexError):
        return None
    if yes_p > 0.99:
        return "YES"
    if no_p > 0.99:
        return "NO"
    return None


def sweep_settlements(
    config: Config,
    store: PositionStore,
    friction: FrictionModel,
) -> int:
    resolved_count = 0
    for pos in store.open_positions():
        raw = _fetch_market_by_condition(config.gamma_base, pos.condition_id)
        if not raw:
            continue
        outcome = _resolved_outcome(raw)
        if outcome is None:
            continue
        side_won = outcome == pos.side
        payout = pos.tokens if side_won else 0.0

        realistic_payout = None
        realistic_note = ""
        if config.dry_run and pos.realistic_tokens is not None:
            is_adverse = "adverse_fill" in (pos.sim_flags or "")
            will_dispute = "uma_dispute" in (pos.sim_flags or "")
            realistic_payout, reason = friction.realistic_payout(
                nominal_tokens=pos.realistic_tokens,
                side_won=side_won,
                is_adverse=is_adverse,
                will_be_disputed=will_dispute,
            )
            if reason:
                realistic_note = f" [{reason}]"

        pnl = payout - pos.cost_usd
        log.info(
            "SETTLED %s | side=%s, outcome=%s, ideal PnL=$%+.2f%s",
            pos.condition_id, pos.side, outcome, pnl, realistic_note,
        )
        store.mark_resolved(
            condition_id=pos.condition_id,
            payout_usd=payout,
            notes=f"outcome={outcome}{realistic_note}",
            realistic_payout_usd=realistic_payout,
        )
        resolved_count += 1
    return resolved_count
