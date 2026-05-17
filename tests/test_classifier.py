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
    cm = classify("Will the conference happen in Q3?")
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


# ---- weather ----

def test_temperature_market_classified_as_weather():
    cm = classify("Will the highest temperature in Hong Kong be 27°C on May 15?")
    assert cm.subcategory == "weather"
    assert not is_safe(cm)


def test_rainfall_classified_as_weather():
    cm = classify("Will it rain in Tokyo on May 20?")
    # 'rain' alone is in keyword but this should still classify
    # as weather (the rainfall pattern matches "rain")
    assert cm.subcategory == "weather"


def test_earthquake_classified_as_weather():
    cm = classify("Will there be 3 or fewer earthquakes of magnitude 5.5+ this week?")
    assert cm.subcategory == "weather"


# ---- politics ----

def test_president_question_classified_as_politics():
    cm = classify("Will Antonio Maíllo be the next President of Andalusia?")
    assert cm.subcategory == "politics"
    assert not is_safe(cm)


def test_senate_primary_classified_as_politics():
    cm = classify("Will John Fleming be the republican nominee for Senate in Louisiana?")
    assert cm.subcategory == "politics"


def test_party_winning_election_classified_as_politics():
    cm = classify("Will Partido Popular (PP) win the Andalusia regional election?")
    assert cm.subcategory == "politics"


# ---- speech_event ----

def test_will_x_say_y_classified_as_speech():
    cm = classify('Will Trump say "Iran" during events with Xi Jinping?')
    assert cm.subcategory == "speech_event"
    assert not is_safe(cm)


def test_will_x_tweet_classified_as_speech():
    cm = classify("Will Elon Musk tweet about Tesla earnings tonight?")
    assert cm.subcategory == "speech_event"


# ---- event_moneyline (generic, opt-in) ----

def test_non_us_soccer_classified_as_event_moneyline():
    cm = classify("Will FC Anyang win on 2026-05-17?")
    assert cm.subcategory == "event_moneyline"
    assert cm.confidence == "medium"


def test_esports_tournament_classified_as_event_moneyline():
    cm = classify("Will Spirit win PGL Astana 2026?")
    assert cm.subcategory == "event_moneyline"


def test_event_moneyline_not_in_default_whitelist():
    cm = classify("Will FC Anyang win on 2026-05-17?")
    assert not is_safe(cm)  # not in DEFAULT_SAFE_SUBCATEGORIES


def test_event_moneyline_can_be_opted_in():
    cm = classify("Will FC Anyang win on 2026-05-17?")
    allowed = DEFAULT_SAFE_SUBCATEGORIES | {"event_moneyline"}
    assert is_safe(cm, allowed=allowed, min_confidence="medium")


# ---- priority / ordering ----

def test_weather_takes_priority_over_event_moneyline():
    # "Will it rain by May 17?" — has 'will' + 'by date' but also weather word
    cm = classify("Will it rain in Tokyo by May 20, 2026?")
    assert cm.subcategory == "weather"


def test_politics_takes_priority_over_event_moneyline():
    # "Will Trump win on Nov 5?" — has moneyline shape but contains nothing
    # in politics list. Try a clearer politics one:
    cm = classify("Will Biden win the Democratic primary in Nevada?")
    assert cm.subcategory == "politics"
