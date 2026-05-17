"""Tests for the crypto price oracle.

We don't hit the real network — `verify_crypto_market` accepts a
`fetch` callable so we inject a fake one.
"""
from __future__ import annotations

from datetime import date, timedelta

from polymarket_arb.price_oracle import PriceVerdict, verify_crypto_market
from polymarket_arb.question_classifier import ClassifiedMarket


def _cm(ticker="BTC", direction="above", threshold=100_000.0,
        target=date(2026, 5, 8)):
    return ClassifiedMarket(
        subcategory="crypto_price",
        confidence="high",
        ticker=ticker, direction=direction,
        threshold_usd=threshold, target_date=target,
    )


def _fake_fetch(price: float | None, err: str | None = None):
    def _f(ticker, target):
        return price, err
    return _f


def test_above_threshold_yes_wins():
    cm = _cm(direction="above", threshold=100_000.0)
    v = verify_crypto_market(cm, fetch=_fake_fetch(105_000.0))
    assert v.winning_side == "YES"
    assert v.actual_price == 105_000.0
    assert v.error is None


def test_above_threshold_no_wins():
    cm = _cm(direction="above", threshold=100_000.0)
    v = verify_crypto_market(cm, fetch=_fake_fetch(95_000.0))
    assert v.winning_side == "NO"
    assert v.actual_price == 95_000.0


def test_below_threshold_yes_wins():
    cm = _cm(direction="below", threshold=200.0)
    v = verify_crypto_market(cm, fetch=_fake_fetch(180.0))
    assert v.winning_side == "YES"


def test_below_threshold_no_wins():
    cm = _cm(direction="below", threshold=200.0)
    v = verify_crypto_market(cm, fetch=_fake_fetch(220.0))
    assert v.winning_side == "NO"


def test_exactly_at_threshold_above_means_no():
    # "above" is strict
    cm = _cm(direction="above", threshold=100_000.0)
    v = verify_crypto_market(cm, fetch=_fake_fetch(100_000.0))
    assert v.winning_side == "NO"


def test_not_yet_past_returns_no_verdict():
    cm = _cm(target=date.today() + timedelta(days=2))
    v = verify_crypto_market(cm, fetch=_fake_fetch(0.0))
    assert v.winning_side is None
    assert "not yet past" in (v.error or "")


def test_fetch_failure_propagates():
    cm = _cm()
    v = verify_crypto_market(cm, fetch=_fake_fetch(None, "network error: timeout"))
    assert v.winning_side is None
    assert "network error" in (v.error or "")


def test_non_crypto_market_rejected():
    cm = ClassifiedMarket(subcategory="team_moneyline", confidence="high")
    v = verify_crypto_market(cm)
    assert v.winning_side is None
    assert "not a crypto market" in (v.error or "")


def test_missing_facts_rejected():
    cm = ClassifiedMarket(subcategory="crypto_price", confidence="high",
                          ticker="BTC")  # no threshold/date
    v = verify_crypto_market(cm)
    assert v.winning_side is None
    assert "missing" in (v.error or "")
