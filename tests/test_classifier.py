"""Tests for the question classifier.

Focus on correctness on real-world Polymarket question phrasings.
"""
from __future__ import annotations

from datetime import date

from polymarket_arb.question_classifier import (
    DEFAULT_SAFE_SUBCATEGORIES,
    classify,
    is_safe,
)


# ---- crypto_price ----

def test_crypto_btc_above_dollar_threshold():
    cm = classify("Will BTC close above $100,000 on May 8, 2026?", fallback_year=2026)
    assert cm.subcategory == "crypto_price"
    assert cm.confidence == "high"
    assert cm.ticker == "BTC"
    assert cm.direction == "above"
    assert cm.threshold_usd == 100000
    assert cm.target_date == date(2026, 5, 8)


def test_crypto_ethereum_k_suffix():
    cm = classify("Will Ethereum reach $5k by May 16, 2026?", fallback_year=2026)
    assert cm.subcategory == "crypto_price"
    assert cm.ticker == "ETH"
    assert cm.threshold_usd == 5000


def test_crypto_solana_below():
    cm = classify("Will Solana close below $200 on May 4, 2026?", fallback_year=2026)
    assert cm.subcategory == "crypto_price"
    assert cm.ticker == "SOL"
    assert cm.direction == "below"


def test_crypto_iso_date():
    cm = classify("Will BTC be above $95000 on 2026-04-28?", fallback_year=2026)
    assert cm.subcategory == "crypto_price"
    assert cm.target_date == date(2026, 4, 28)


def test_crypto_without_date_is_low_confidence():
    cm = classify("Will BTC ever reach $200,000?", fallback_year=2026)
    assert cm.subcategory == "crypto_price"
    assert cm.confidence == "low"
    assert cm.target_date is None


# ---- team_moneyline ----

def test_two_teams_with_verb_high_confidence():
    cm = classify("Will the Lakers beat the Celtics on May 12?")
    assert cm.subcategory == "team_moneyline"
    assert cm.confidence == "high"


def test_one_team_with_verb_medium_confidence():
    # "Bengals" is in keyword list, "their opponent" isn't
    cm = classify("Will the Chiefs win their game on Sunday?")
    assert cm.subcategory == "team_moneyline"
    assert cm.confidence == "medium"


# ---- player_prop (rejected) ----

def test_player_prop_detected():
    cm = classify("Will LeBron score 30+ points in Game 3?")
    assert cm.subcategory == "player_prop"


def test_mvp_question_is_player_prop():
    cm = classify("Will Jokic win MVP this season?")
    assert cm.subcategory == "player_prop"


def test_player_prop_not_safe():
    cm = classify("Will Steph Curry have 8+ assists?")
    assert not is_safe(cm)


# ---- sports_event (event existence) ----

def test_single_team_no_verb_marked_event():
    cm = classify("Will the Lakers play their game this week?")
    assert cm.subcategory == "sports_event"


def test_sports_event_not_in_default_whitelist():
    cm = classify("Will the Lakers play their game this week?")
    assert not is_safe(cm)


# ---- subjective phrasings rejected ----

def test_official_decision_rejected():
    cm = classify("Will the Lakers officially be declared the winner?")
    assert cm.subcategory == "other"


def test_controversy_rejected():
    cm = classify("Will there be controversy over the BTC close above $100k?")
    assert cm.subcategory == "other"


# ---- other / fallback ----

def test_unknown_question_is_other():
    cm = classify("Will it rain in Tokyo this weekend?")
    assert cm.subcategory == "other"


def test_empty_question_is_other():
    cm = classify("")
    assert cm.subcategory == "other"


# ---- is_safe gate ----

def test_default_safe_subcategories_are_strict():
    assert "crypto_price" in DEFAULT_SAFE_SUBCATEGORIES
    assert "team_moneyline" in DEFAULT_SAFE_SUBCATEGORIES
    assert "player_prop" not in DEFAULT_SAFE_SUBCATEGORIES
    assert "sports_event" not in DEFAULT_SAFE_SUBCATEGORIES


def test_low_confidence_crypto_not_safe_by_default():
    cm = classify("Will BTC ever reach $200,000?", fallback_year=2026)
    assert not is_safe(cm)
