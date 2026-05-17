"""Tests for the realism layer:
  - VerificationQueue dedupes and respects delay
  - verify() correctly classifies fills vs misses
  - FrictionModel is deterministic and applies expected adjustments
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from polymarket_arb.friction import (
    FrictionModel,
    PendingVerification,
    VerificationQueue,
    verify,
)
from polymarket_arb.orderbook import BookSide, OrderBook


# ---- VerificationQueue ----

def _pv(token_id: str, detected_at: datetime) -> PendingVerification:
    return PendingVerification(
        token_id=token_id,
        condition_id="0xabc",
        question="Will X happen?",
        side="YES",
        detected_at=detected_at,
        detected_ask=0.955,
        detected_depth_usd=200.0,
        max_buy_price=0.96,
        intended_usd=25.0,
    )


def test_queue_dedupes_same_token():
    q = VerificationQueue(delay_seconds=60.0)
    now = datetime.now(timezone.utc)
    assert q.enqueue(_pv("t1", now)) is True
    assert q.enqueue(_pv("t1", now)) is False  # dedup
    assert q.enqueue(_pv("t2", now)) is True
    assert len(q) == 2


def test_queue_only_returns_ready_items():
    q = VerificationQueue(delay_seconds=60.0)
    now = datetime.now(timezone.utc)
    q.enqueue(_pv("t1", now - timedelta(seconds=10)))   # not ready
    q.enqueue(_pv("t2", now - timedelta(seconds=120)))  # ready
    ready = q.ready(now)
    assert {r.token_id for r in ready} == {"t2"}
    assert len(q) == 1  # only t1 remains


# ---- verify() ----

def test_verify_marks_filled_when_book_still_good():
    pv = _pv("t1", datetime.now(timezone.utc) - timedelta(seconds=60))
    book = OrderBook(
        token_id="t1",
        bids=[BookSide(0.93, 500)],
        asks=[BookSide(0.95, 100), BookSide(0.96, 200)],
    )
    result = verify(pv, lambda tid: book)
    assert result.would_have_filled
    assert result.realistic_tokens > 0
    # Should fill within $25 budget
    assert 24.0 < result.realistic_cost_usd <= 25.0


def test_verify_marks_missed_when_ask_drifted_up():
    pv = _pv("t1", datetime.now(timezone.utc) - timedelta(seconds=60))
    book = OrderBook(
        token_id="t1",
        bids=[BookSide(0.95, 100)],
        asks=[BookSide(0.97, 100)],  # drifted above max 0.96
    )
    result = verify(pv, lambda tid: book)
    assert not result.would_have_filled
    assert result.realistic_tokens == 0.0


def test_verify_handles_empty_book():
    pv = _pv("t1", datetime.now(timezone.utc) - timedelta(seconds=60))
    result = verify(pv, lambda tid: None)
    assert not result.would_have_filled
    assert result.verified_ask is None


# ---- FrictionModel ----

def test_friction_is_deterministic():
    m = FrictionModel(
        gas_cost_usd=0.10,
        expected_fill_ratio=0.7,
        adverse_fill_rate=0.05,
        uma_dispute_rate=0.02,
    )
    detected = datetime(2026, 5, 17, 10, 0, 0, tzinfo=timezone.utc)
    a = m.apply_to_fill("t1", detected, verified_tokens=26.0, verified_cost=25.0)
    b = m.apply_to_fill("t1", detected, verified_tokens=26.0, verified_cost=25.0)
    assert a.realistic_tokens == b.realistic_tokens
    assert a.realistic_cost_usd == b.realistic_cost_usd
    assert a.is_adverse == b.is_adverse


def test_friction_applies_partial_fill_and_gas():
    m = FrictionModel(
        gas_cost_usd=0.10,
        expected_fill_ratio=0.7,
        adverse_fill_rate=0.0,
        uma_dispute_rate=0.0,
    )
    detected = datetime(2026, 5, 17, 10, 0, 0, tzinfo=timezone.utc)
    a = m.apply_to_fill("t1", detected, verified_tokens=26.0, verified_cost=25.0)
    # Should be a haircut from 26 tokens (0.4 < ratio < 1.0)
    assert 10 < a.realistic_tokens < 26
    # Cost should include gas
    avg = 25.0 / 26.0
    expected_cost = a.realistic_tokens * avg + 0.10
    assert abs(a.realistic_cost_usd - expected_cost) < 1e-6


def test_friction_payout_normal_win():
    m = FrictionModel(0.10, 0.7, 0.0, 0.0)
    payout, reason = m.realistic_payout(
        nominal_tokens=20.0, side_won=True,
        is_adverse=False, will_be_disputed=False,
    )
    assert payout == 20.0
    assert reason == ""


def test_friction_payout_normal_loss():
    m = FrictionModel(0.10, 0.7, 0.0, 0.0)
    payout, _ = m.realistic_payout(
        nominal_tokens=20.0, side_won=False,
        is_adverse=False, will_be_disputed=False,
    )
    assert payout == 0.0


def test_friction_payout_adverse_zeros_out():
    m = FrictionModel(0.10, 0.7, 0.0, 0.0)
    payout, reason = m.realistic_payout(
        nominal_tokens=20.0, side_won=True,
        is_adverse=True, will_be_disputed=False,
    )
    assert payout == 0.0
    assert "adverse" in reason


def test_friction_payout_uma_dispute_flips_win_to_loss():
    m = FrictionModel(0.10, 0.7, 0.0, 0.0)
    payout, reason = m.realistic_payout(
        nominal_tokens=20.0, side_won=True,
        is_adverse=False, will_be_disputed=True,
    )
    assert payout == 0.0
    assert "uma" in reason.lower()


def test_friction_payout_uma_dispute_flips_loss_to_win():
    """If we bet wrong and UMA disputes, we win? Edge case but
    mechanically consistent with the model."""
    m = FrictionModel(0.10, 0.7, 0.0, 0.0)
    payout, _ = m.realistic_payout(
        nominal_tokens=20.0, side_won=False,
        is_adverse=False, will_be_disputed=True,
    )
    assert payout == 20.0
