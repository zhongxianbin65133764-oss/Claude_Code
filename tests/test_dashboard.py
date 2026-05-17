"""Dashboard smoke tests: seed the DB with synthetic positions and
verify the page renders + API returns expected data."""
from __future__ import annotations

import os
import tempfile
from datetime import datetime, timedelta, timezone

from polymarket_arb.config import Config
from polymarket_arb.dashboard import create_app
from polymarket_arb.position_store import PositionStore


def _seed(store: PositionStore) -> None:
    # open position (with realistic_*: 70% fill + $0.10 gas)
    store.open_position(
        condition_id="0xopen1", token_id="t1",
        question="Will the Lakers win Game 3?", side="YES",
        tokens=26.18, avg_price=0.955, cost_usd=25.00, dry_run=True,
        realistic_tokens=18.32, realistic_cost_usd=17.60,
        sim_flags="fill_ratio=70%;gas=$0.10",
    )
    # winning closed position
    store.open_position(
        condition_id="0xwin", token_id="t2",
        question="Will BTC close above $100k on 2026-05-10?", side="NO",
        tokens=27.03, avg_price=0.925, cost_usd=25.00, dry_run=True,
        realistic_tokens=18.92, realistic_cost_usd=17.60,
        sim_flags="fill_ratio=70%;gas=$0.10",
    )
    store.mark_resolved(
        "0xwin", payout_usd=27.03,
        realistic_payout_usd=18.92,
        notes="outcome=NO pnl=+2.03",
    )
    # losing closed position (UMA reversed in simulation)
    store.open_position(
        condition_id="0xloss", token_id="t3",
        question="Will the Knicks win Game 2?", side="YES",
        tokens=26.32, avg_price=0.950, cost_usd=25.00, dry_run=True,
        realistic_tokens=18.42, realistic_cost_usd=17.60,
        sim_flags="fill_ratio=70%;gas=$0.10",
    )
    store.mark_resolved(
        "0xloss", payout_usd=0.0,
        realistic_payout_usd=0.0,
        notes="outcome=NO pnl=-25.00",
    )

    # one verification record so the realism stats section renders
    store.record_verification(
        condition_id="0xv1", token_id="vt1", side="YES",
        detected_at="2026-05-17T10:00:00+00:00",
        detected_ask=0.95, detected_depth_usd=200.0, intended_usd=25.0,
        verified_at="2026-05-17T10:01:00+00:00",
        verified_ask=0.95, verified_depth_usd=120.0,
        would_have_filled=True,
        realistic_tokens=18.0, realistic_cost_usd=17.5,
    )
    store.record_verification(
        condition_id="0xv2", token_id="vt2", side="YES",
        detected_at="2026-05-17T10:05:00+00:00",
        detected_ask=0.94, detected_depth_usd=200.0, intended_usd=25.0,
        verified_at="2026-05-17T10:06:00+00:00",
        verified_ask=0.97, verified_depth_usd=30.0,
        would_have_filled=False,
        realistic_tokens=0.0, realistic_cost_usd=0.0,
    )


def test_dashboard_renders_with_seeded_data():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "test.db")
        store = PositionStore(db_path)
        _seed(store)
        cfg = Config(dry_run=True, db_path=db_path)
        app = create_app(store, cfg)
        client = app.test_client()

        # main page
        r = client.get("/")
        assert r.status_code == 200
        body = r.get_data(as_text=True)
        # Chinese labels
        assert "Polymarket 套利助手" in body
        assert "演练模式" in body
        assert "正在持有" in body
        assert "已经结清" in body
        # realism layer should be shown in dry-run with verifications
        assert "演练 vs 实盘的差距" in body
        assert "实盘预估" in body
        assert "理想" in body
        # seeded questions
        assert "Lakers" in body
        assert "BTC close above" in body
        assert "Knicks" in body
        # ideal PnL: +2.03 - 25.00 = -22.97
        assert "-22.97" in body

        # API endpoints
        r = client.get("/api/summary")
        assert r.status_code == 200
        s = r.get_json()
        assert s["open_count"] == 1
        assert s["closed_count"] == 2
        assert abs(s["realized_pnl"] - (-22.97)) < 0.01
        assert abs(s["win_rate"] - 0.5) < 0.001
        # realistic PnL: +1.32 + (0 - 17.60) = -16.28
        assert abs(s["realistic_pnl"] - (-16.28)) < 0.05
        # verification stats
        assert s["verification"]["detected"] == 2
        assert s["verification"]["filled"] == 1
        assert abs(s["verification"]["fill_rate"] - 0.5) < 0.001

        # ideal series
        r = client.get("/api/pnl-series")
        assert r.status_code == 200
        series = r.get_json()
        assert len(series) == 2
        assert abs(series[-1][1] - (-22.97)) < 0.01

        # realistic series
        r = client.get("/api/pnl-series?realistic=1")
        assert r.status_code == 200
        rseries = r.get_json()
        assert len(rseries) == 2
        # last point = -16.28 (within tolerance)
        assert abs(rseries[-1][1] - (-16.28)) < 0.05


def test_dashboard_renders_with_empty_db():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "empty.db")
        store = PositionStore(db_path)
        cfg = Config(dry_run=True, db_path=db_path)
        app = create_app(store, cfg)
        client = app.test_client()
        r = client.get("/")
        assert r.status_code == 200
        body = r.get_data(as_text=True)
        assert "目前没有持仓" in body
        assert "还没有结清的交易" in body
