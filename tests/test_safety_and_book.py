"""Offline tests for safety filters and orderbook math.

Run: python -m pytest tests/ -v
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from polymarket_arb.gamma_client import Market
from polymarket_arb.orderbook import BookSide, OrderBook
from polymarket_arb.safety import book_passes_safety, market_passes_safety


def _make_market(**kw) -> Market:
    defaults = dict(
        condition_id="0xabc",
        question="Will the Lakers win Game 3?",
        description="",
        end_date=datetime.now(timezone.utc) - timedelta(hours=3),
        category="Sports",
        yes_token_id="t_yes",
        no_token_id="t_no",
        closed=False,
        active=True,
        accepting_orders=True,
        volume_usd=10_000.0,
    )
    defaults.update(kw)
    return Market(**defaults)


def test_safe_sports_market_passes():
    ok, _ = market_passes_safety(_make_market())
    assert ok


def test_risky_category_rejected():
    ok, reason = market_passes_safety(_make_market(category="Politics"))
    assert not ok
    assert "risky" in reason


def test_blacklisted_keyword_rejected():
    m = _make_market(question="Will the pope make a statement on AI?")
    ok, reason = market_passes_safety(m)
    assert not ok
    assert "pope" in reason


def test_unknown_category_rejected():
    ok, _ = market_passes_safety(_make_market(category="Memes"))
    assert not ok


def test_not_accepting_orders_rejected():
    ok, _ = market_passes_safety(_make_market(accepting_orders=False))
    assert not ok


def _book(asks, bids=None):
    bids = bids or [BookSide(0.04, 1000)]
    return OrderBook(token_id="t", bids=bids, asks=asks)


def test_book_passes_when_deep_at_good_price():
    asks = [BookSide(0.95, 500), BookSide(0.96, 500)]
    bids = [BookSide(0.93, 500)]
    ok, _ = book_passes_safety(_book(asks, bids), 0.96, 0.88, 50)
    assert ok


def test_book_rejected_when_ask_too_high():
    asks = [BookSide(0.98, 500)]
    bids = [BookSide(0.96, 500)]
    ok, reason = book_passes_safety(_book(asks, bids), 0.96, 0.88, 50)
    assert not ok
    assert "above max" in reason


def test_book_rejected_when_ask_too_low():
    asks = [BookSide(0.70, 500)]
    bids = [BookSide(0.65, 500)]
    ok, reason = book_passes_safety(_book(asks, bids), 0.96, 0.88, 50)
    assert not ok
    assert "below min" in reason


def test_book_rejected_when_too_thin():
    asks = [BookSide(0.95, 30)]  # $28.50 of depth, below $50 min
    bids = [BookSide(0.93, 500)]
    ok, reason = book_passes_safety(_book(asks, bids), 0.96, 0.88, 50)
    assert not ok
    assert "fillable" in reason


def test_book_rejected_when_spread_too_wide():
    asks = [BookSide(0.95, 500)]
    bids = [BookSide(0.50, 500)]
    ok, reason = book_passes_safety(_book(asks, bids), 0.96, 0.88, 50)
    assert not ok
    assert "spread" in reason


def test_fillable_cost_walks_book():
    book = _book(
        asks=[
            BookSide(0.94, 100),
            BookSide(0.95, 100),
            BookSide(0.97, 200),  # above our max
        ]
    )
    tokens, cost = book.fillable_cost(max_tokens=1000, max_price=0.96)
    assert tokens == 200
    assert abs(cost - (100 * 0.94 + 100 * 0.95)) < 1e-9


def test_fillable_cost_respects_max_tokens():
    book = _book(asks=[BookSide(0.94, 100), BookSide(0.95, 100)])
    tokens, cost = book.fillable_cost(max_tokens=50, max_price=0.96)
    assert tokens == 50
    assert abs(cost - 50 * 0.94) < 1e-9
