"""Resolution-time arbitrage strategy.

Two execution paths:

  LIVE   : detect -> place order immediately -> record position.
           Real fills are the realistic truth.

  DRY-RUN: detect -> enqueue for verification (NO immediate "fill").
           After `verification_delay_seconds`, re-fetch the same book
           and decide what would *actually* have happened given the
           detection-to-submission latency. Then apply parametric
           friction (gas, partial fill, adverse selection, UMA dispute)
           to produce a "realistic" cost/payout alongside the "ideal"
           one. Both are stored, the dashboard shows the gap.

Single-leg, no leg risk. Capital is locked until UMA resolution.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from .config import Config
from .executor import Executor
from .friction import (
    FrictionModel,
    PendingVerification,
    VerificationQueue,
    verify,
)
from .gamma_client import Market, fetch_resolving_markets
from .orderbook import OrderBook, fetch_book
from .position_store import PositionStore
from .safety import book_passes_safety, market_passes_safety

log = logging.getLogger(__name__)


@dataclass
class Opportunity:
    market: Market
    side: str
    token_id: str
    book: OrderBook
    fillable_tokens: float
    fillable_cost: float
    avg_price: float


def find_opportunities(config: Config) -> list[Opportunity]:
    """Scan Gamma + CLOB for tradable resolution-time arb opportunities."""
    opportunities: list[Opportunity] = []
    market_count = 0
    rejected_safety = 0
    rejected_book = 0

    for market in fetch_resolving_markets(
        config.gamma_base,
        config.min_market_age_hours,
        config.max_market_age_days,
    ):
        market_count += 1
        ok, reason = market_passes_safety(market)
        if not ok:
            rejected_safety += 1
            log.debug("skip %s: %s", market.question[:60], reason)
            continue

        for side, token_id in (("YES", market.yes_token_id),
                               ("NO", market.no_token_id)):
            book = fetch_book(config.clob_base, token_id)
            if book is None:
                continue
            ok, reason = book_passes_safety(
                book,
                max_price=config.max_buy_price,
                min_price=config.min_buy_price,
                min_depth_usd=config.min_book_depth_usd,
            )
            if not ok:
                rejected_book += 1
                log.debug("skip %s %s: %s", market.question[:60], side, reason)
                continue

            tokens, cost = _fill_within_budget(
                book, config.max_position_size_usd, config.max_buy_price,
            )
            if tokens <= 0 or cost <= 0:
                continue
            opportunities.append(Opportunity(
                market=market,
                side=side,
                token_id=token_id,
                book=book,
                fillable_tokens=tokens,
                fillable_cost=cost,
                avg_price=cost / tokens,
            ))

    log.info(
        "scan: %d markets seen, %d safety-rejected, %d book-rejected, %d opportunities",
        market_count, rejected_safety, rejected_book, len(opportunities),
    )
    return opportunities


def _fill_within_budget(
    book: OrderBook, max_usd: float, max_price: float,
) -> tuple[float, float]:
    """Walk the asks, capped by total USD and per-level max_price."""
    tokens = 0.0
    cost = 0.0
    for ask in book.asks:
        if ask.price > max_price:
            break
        affordable = (max_usd - cost) / ask.price
        take = min(ask.size, affordable)
        if take <= 0:
            break
        tokens += take
        cost += take * ask.price
    return tokens, cost


# --------------------------------------------------------------------------
# Per-opportunity routing
# --------------------------------------------------------------------------

def handle_opportunity(
    opp: Opportunity,
    config: Config,
    store: PositionStore,
    executor: Executor,
    queue: VerificationQueue,
) -> str:
    """Route an opportunity according to mode.

    Returns one of: 'dup', 'budget', 'queued', 'placed', 'failed'.
    """
    if store.has_position(opp.market.condition_id):
        return "dup"

    current_exposure = store.open_exposure_usd()
    headroom = config.max_total_exposure_usd - current_exposure
    if headroom <= 0:
        log.info("at max total exposure ($%.2f), skipping", current_exposure)
        return "budget"
    intended_cost = min(opp.fillable_cost, headroom)
    if intended_cost < 5:
        return "budget"

    if config.dry_run:
        # Don't execute now — enqueue for delayed verification.
        _, depth_at_limit = opp.book.fillable_cost(1e9, config.max_buy_price)
        added = queue.enqueue(PendingVerification(
            token_id=opp.token_id,
            condition_id=opp.market.condition_id,
            question=opp.market.question,
            side=opp.side,
            detected_at=datetime.now(timezone.utc),
            detected_ask=opp.book.best_ask or opp.avg_price,
            detected_depth_usd=depth_at_limit,
            max_buy_price=config.max_buy_price,
            intended_usd=intended_cost,
        ))
        if added:
            log.info(
                "DETECTED %s | %s @ %.3f | depth $%.0f | queued for verification in %.0fs",
                opp.market.question[:70], opp.side, opp.avg_price,
                depth_at_limit, config.verification_delay_seconds,
            )
        return "queued"

    # LIVE path
    log.info(
        "PLACING %s | %s @ %.3f | $%.2f",
        opp.market.question[:70], opp.side, opp.avg_price, intended_cost,
    )
    result = executor.buy(
        token_id=opp.token_id,
        max_price=config.max_buy_price,
        max_usd=intended_cost,
    )
    if not result.success:
        log.warning("execution failed: %s", result.error)
        return "failed"
    store.open_position(
        condition_id=opp.market.condition_id,
        token_id=opp.token_id,
        question=opp.market.question,
        side=opp.side,
        tokens=result.tokens_filled,
        avg_price=result.avg_price,
        cost_usd=result.usd_spent,
        dry_run=False,
    )
    return "placed"


def process_verification_queue(
    config: Config,
    store: PositionStore,
    queue: VerificationQueue,
    friction: FrictionModel,
) -> int:
    """Run any ready verifications. For each fill, open a dry-run
    position with BOTH ideal (what scan saw) and realistic (post-
    latency + friction) cost numbers. Returns count of positions opened.
    """
    if not config.dry_run:
        return 0

    now = datetime.now(timezone.utc)
    opened = 0

    for pv in queue.ready(now):
        if store.has_position(pv.condition_id):
            continue

        result = verify(pv, lambda tid: fetch_book(config.clob_base, tid))

        # Ideal numbers: what dry-run *thought* it could get at detection time.
        ideal_tokens = pv.intended_usd / pv.max_buy_price
        ideal_cost = pv.intended_usd
        ideal_avg_px = pv.max_buy_price

        store.record_verification(
            condition_id=pv.condition_id,
            token_id=pv.token_id,
            side=pv.side,
            detected_at=pv.detected_at.isoformat(),
            detected_ask=pv.detected_ask,
            detected_depth_usd=pv.detected_depth_usd,
            intended_usd=pv.intended_usd,
            verified_at=result.verified_at.isoformat(),
            verified_ask=result.verified_ask,
            verified_depth_usd=result.verified_depth_usd,
            would_have_filled=result.would_have_filled,
            realistic_tokens=result.realistic_tokens,
            realistic_cost_usd=result.realistic_cost_usd,
        )

        if not result.would_have_filled:
            log.info(
                "MISSED %s | ask drifted %.3f -> %.3f, fill rate dropping",
                pv.question[:70], pv.detected_ask,
                result.verified_ask if result.verified_ask else 0.0,
            )
            continue

        # We would have filled. Apply parametric friction.
        applied = friction.apply_to_fill(
            token_id=pv.token_id,
            detected_at=pv.detected_at,
            verified_tokens=result.realistic_tokens,
            verified_cost=result.realistic_cost_usd,
        )

        log.info(
            "FILLED  %s | ideal $%.2f @ %.3f -> real $%.2f @ %.3f (%s)",
            pv.question[:70], ideal_cost, ideal_avg_px,
            applied.realistic_cost_usd,
            (applied.realistic_cost_usd / applied.realistic_tokens)
                if applied.realistic_tokens else 0.0,
            applied.notes,
        )

        store.open_position(
            condition_id=pv.condition_id,
            token_id=pv.token_id,
            question=pv.question,
            side=pv.side,
            tokens=ideal_tokens,
            avg_price=ideal_avg_px,
            cost_usd=ideal_cost,
            dry_run=True,
            realistic_tokens=applied.realistic_tokens,
            realistic_cost_usd=applied.realistic_cost_usd,
            sim_flags=applied.notes,
        )
        opened += 1

    return opened
