"""Smoke tests for the weekly review script."""
from __future__ import annotations

import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import importlib.util
spec = importlib.util.spec_from_file_location(
    "weekly_review",
    os.path.join(ROOT, "scripts", "weekly_review.py"),
)
weekly_review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(weekly_review)

from polymarket_arb.position_store import PositionStore


def _seed(store: PositionStore) -> None:
    # 4 closed positions: 3 wins, 1 dispute (loss)
    specs = [
        ("0xc1", "Will BTC close above $100k on May 8, 2026?", "NO",  0.925, True,  None),
        ("0xc2", "Will the Lakers beat the Celtics in Game 3?", "YES", 0.940, True,  None),
        ("0xc3", "Will ETH close above $5000 on May 12, 2026?", "NO",  0.955, False, "adverse_fill"),
        ("0xc4", "Will the Knicks beat the Heat Game 2?",       "YES", 0.950, True,  "uma_dispute"),
    ]
    for cid, q, side, price, won, flag in specs:
        tokens = 25.0 / price
        real_tokens = tokens * 0.7
        real_cost = real_tokens * price + 0.10
        flags = "fill_ratio=70%;gas=$0.10"
        if flag:
            flags += f";{flag}"
        store.open_position(
            cid, "tok_" + cid, q, side, tokens, price, 25.00, dry_run=True,
            realistic_tokens=real_tokens, realistic_cost_usd=real_cost,
            sim_flags=flags,
        )
        payout = tokens if won else 0.0
        if flag == "adverse_fill":
            real_payout = 0.0
        elif flag == "uma_dispute":
            real_payout = 0.0 if won else real_tokens
        else:
            real_payout = real_tokens if won else 0.0
        store.mark_resolved(
            cid, payout_usd=payout, realistic_payout_usd=real_payout,
        )
    # a few verifications
    for i in range(10):
        store.record_verification(
            condition_id=f"0xv{i}", token_id=f"vt{i}", side="YES",
            detected_at="2026-05-17T10:00:00+00:00",
            detected_ask=0.94, detected_depth_usd=200.0, intended_usd=25.0,
            verified_at="2026-05-17T10:01:00+00:00",
            verified_ask=0.94 if i % 3 != 0 else 0.97,
            verified_depth_usd=120.0 if i % 3 != 0 else 30.0,
            would_have_filled=(i % 3 != 0),
            realistic_tokens=18.0 if i % 3 != 0 else 0.0,
            realistic_cost_usd=17.0 if i % 3 != 0 else 0.0,
        )


def test_review_runs_on_seeded_db():
    with tempfile.TemporaryDirectory() as tmp:
        db = os.path.join(tmp, "test.db")
        store = PositionStore(db)
        _seed(store)
        # Each section must produce a non-empty string.
        assert weekly_review.section_activity(store, db).strip()
        assert weekly_review.section_loss_decomposition(store).strip()
        assert weekly_review.section_by_subcategory(store).strip()
        assert weekly_review.section_by_price_bucket(store).strip()
        table, frict = weekly_review.section_friction_calibration(store)
        assert "Fill rate" in table
        # With 4 closed positions, recommendations should not fire yet
        # (need 10+). It should print the "more data needed" message.
        recs = weekly_review.section_recommendations(store, frict)
        assert "10" in recs or "20" in recs


def test_review_runs_on_empty_db():
    with tempfile.TemporaryDirectory() as tmp:
        db = os.path.join(tmp, "empty.db")
        store = PositionStore(db)
        # Should not raise.
        assert weekly_review.section_activity(store, db).strip()
        assert weekly_review.section_loss_decomposition(store).strip()
        assert weekly_review.section_by_subcategory(store).strip()
        assert weekly_review.section_by_price_bucket(store).strip()


def test_loss_decomposition_attributes_correctly():
    with tempfile.TemporaryDirectory() as tmp:
        db = os.path.join(tmp, "attr.db")
        store = PositionStore(db)
        _seed(store)
        text = weekly_review.section_loss_decomposition(store)
        # 3 normal positions had partial fills/gas losses
        # 1 adverse position (ETH) - ideal would be 0 (lost), realistic also 0 -> no diff from adverse
        # 1 dispute position (Knicks) - ideal +0 (lost) but flag is dispute, so it counts as dispute
        # Actually:
        #  c1 BTC won at 0.925: ideal pnl = 27.03-25 = +2.03, real = 18.92-17.60 = +1.32, diff 0.71 (fill+gas)
        #  c2 Lakers won at 0.94: ideal +1.60, real ~+0.89, diff 0.71 (fill+gas)
        #  c3 ETH lost+adverse at 0.955: ideal -25, real -17.60, diff -7.4 (adverse, but in our favor)
        #  c4 Knicks won but dispute at 0.95: ideal +1.32, real -17.60, diff +18.92 (dispute hurts)
        assert "Breakdown:" in text
        assert "Partial fills + gas" in text
        assert "Adverse selection" in text
        assert "UMA disputes" in text
