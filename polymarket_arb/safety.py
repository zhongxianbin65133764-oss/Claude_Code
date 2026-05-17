"""Pre-trade safety filters.

These filters exist to keep us out of markets where UMA is likely
to dispute the result, where the question is subjective, or where
the orderbook is a trap (thin, manipulated, stale).
"""
from __future__ import annotations

import logging

from .config import BLACKLIST_KEYWORDS, RISKY_CATEGORIES, SAFE_CATEGORIES
from .gamma_client import Market
from .orderbook import OrderBook
from .question_classifier import (
    DEFAULT_SAFE_SUBCATEGORIES,
    ClassifiedMarket,
    classify,
    is_safe,
)

log = logging.getLogger(__name__)


def market_passes_safety(
    market: Market,
    use_subcategory_filter: bool = True,
) -> tuple[bool, str, ClassifiedMarket | None]:
    """Return (ok, reason, classified_market_or_none).

    When use_subcategory_filter is True (S-tier optimization),
    a market must additionally classify into the safe-subcategory
    whitelist (crypto_price / team_moneyline) with high confidence.
    This is much stricter than the broad category whitelist.
    """
    if not market.accepting_orders:
        return False, "not accepting orders", None
    if market.closed:
        return False, "already closed", None

    q_lower = market.question.lower()
    for kw in BLACKLIST_KEYWORDS:
        if kw in q_lower:
            return False, f"blacklisted keyword: {kw}", None

    cat = market.category
    if cat in RISKY_CATEGORIES:
        return False, f"risky category: {cat}", None
    if SAFE_CATEGORIES and cat and cat not in SAFE_CATEGORIES:
        return False, f"unknown category: {cat}", None

    classified = classify(market.question)

    if use_subcategory_filter:
        if not is_safe(classified, DEFAULT_SAFE_SUBCATEGORIES, min_confidence="high"):
            return False, (
                f"subcategory '{classified.subcategory}' "
                f"(conf={classified.confidence}) not in safe whitelist"
            ), classified

    return True, "ok", classified


def book_passes_safety(
    book: OrderBook,
    max_price: float,
    min_price: float,
    min_depth_usd: float,
) -> tuple[bool, str]:
    """Return (ok, reason).

    Requires the ask side to have meaningful depth in the price band
    we care about, and the book not to be one-sided (one-sided books
    are often manipulation / stale liquidity).
    """
    if not book.asks or not book.bids:
        return False, "empty book on one side"
    best_ask = book.best_ask
    best_bid = book.best_bid
    assert best_ask is not None and best_bid is not None

    if best_ask > max_price:
        return False, f"ask {best_ask:.3f} above max {max_price:.3f}"
    if best_ask < min_price:
        return False, f"ask {best_ask:.3f} below min {min_price:.3f} (market unsure)"

    # Tokens we could buy <= max_price at theoretical_value of 1 USDC.
    fillable_tokens, fillable_cost = book.fillable_cost(
        max_tokens=1e9,
        max_price=max_price,
    )
    if fillable_cost < min_depth_usd:
        return False, f"only ${fillable_cost:.0f} fillable below max price"

    # Sanity: spread must be sane. A 30c spread on a near-resolved
    # market means thin/dishonest book.
    if best_ask - best_bid > 0.20:
        return False, f"spread {best_ask - best_bid:.2f} too wide"

    return True, "ok"
