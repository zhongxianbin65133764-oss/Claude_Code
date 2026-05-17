"""Resolution-time arbitrage strategy.

Logic:
  1. List markets whose event time has passed by [min_age_hours,
     max_age_days].
  2. Filter to safe categories, non-blacklisted questions, depth-ok books.
  3. Identify the dominant side (YES or NO) currently trading at
     [min_buy_price, max_buy_price] and buy it.
  4. Track position. UMA settles within 1-7d typically; bot then
     marks resolved and PnL is realised.

Single-leg, no leg risk. Capital is locked until UMA resolution.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from .config import Config
from .executor import Executor
from .gamma_client import Market, fetch_resolving_markets
from .orderbook import OrderBook, fetch_book
from .position_store import PositionStore
from .safety import book_passes_safety, market_passes_safety

log = logging.getLogger(__name__)


@dataclass
class Opportunity:
    market: Market
    side: str           # 'YES' or 'NO'
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

        # Check both sides; resolution-time arb often shows up on whichever
        # side the market consensus has converged on.
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

            fillable_tokens, fillable_cost = book.fillable_cost(
                max_tokens=config.max_position_size_usd / config.min_buy_price,
                max_price=config.max_buy_price,
            )
            # Cap to position size.
            if fillable_cost > config.max_position_size_usd:
                # Re-walk the book with a tighter ceiling so reported cost matches.
                tokens = 0.0
                cost = 0.0
                for ask in book.asks:
                    if ask.price > config.max_buy_price:
                        break
                    affordable = (config.max_position_size_usd - cost) / ask.price
                    take = min(ask.size, affordable)
                    if take <= 0:
                        break
                    tokens += take
                    cost += take * ask.price
                fillable_tokens, fillable_cost = tokens, cost

            if fillable_tokens <= 0 or fillable_cost <= 0:
                continue
            avg_price = fillable_cost / fillable_tokens

            opportunities.append(
                Opportunity(
                    market=market,
                    side=side,
                    token_id=token_id,
                    book=book,
                    fillable_tokens=fillable_tokens,
                    fillable_cost=fillable_cost,
                    avg_price=avg_price,
                )
            )

    log.info(
        "scan: %d markets seen, %d safety-rejected, %d book-rejected, %d opportunities",
        market_count, rejected_safety, rejected_book, len(opportunities),
    )
    return opportunities


def execute_opportunity(
    opp: Opportunity,
    config: Config,
    store: PositionStore,
    executor: Executor,
) -> bool:
    """Place the order and record the position. Returns True on success."""
    # Don't double-position the same market.
    if store.has_position(opp.market.condition_id):
        log.debug("already have position on %s", opp.market.condition_id)
        return False

    # Budget check.
    current_exposure = store.open_exposure_usd()
    headroom = config.max_total_exposure_usd - current_exposure
    if headroom <= 0:
        log.info("at max total exposure ($%.2f), skipping", current_exposure)
        return False

    intended_cost = min(opp.fillable_cost, headroom)
    if intended_cost < 5:  # too small to be worth the gas
        log.debug("opportunity too small: $%.2f", intended_cost)
        return False

    log.info(
        "OPPORTUNITY: %s | %s @ %.3f | fill $%.2f | %s",
        opp.market.question[:80], opp.side, opp.avg_price,
        intended_cost, opp.market.condition_id,
    )

    result = executor.buy(
        token_id=opp.token_id,
        max_price=config.max_buy_price,
        max_usd=intended_cost,
    )
    if not result.success:
        log.warning("execution failed: %s", result.error)
        return False

    store.open_position(
        condition_id=opp.market.condition_id,
        token_id=opp.token_id,
        question=opp.market.question,
        side=opp.side,
        tokens=result.tokens_filled,
        avg_price=result.avg_price,
        cost_usd=result.usd_spent,
        dry_run=config.dry_run,
    )
    return True
