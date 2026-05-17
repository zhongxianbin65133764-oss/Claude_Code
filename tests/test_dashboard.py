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
    # one open position
    store.open_position(
        condition_id="0xopen1", token_id="t1",
        question="Will the Lakers win Game 3?", side="YES",
        tokens=26.18, avg_price=0.955, cost_usd=25.00, dry_run=True,
    )
    # one winning closed position
    store.open_position(
        condition_id="0xwin", token_id="t2",
        question="Will BTC close above $100k on 2026-05-10?", side="NO",
        tokens=27.03, avg_price=0.925, cost_usd=25.00, dry_run=True,
    )
    store.mark_resolved("0xwin", payout_usd=27.03, notes="outcome=NO pnl=+2.03")
    # one losing closed position (UMA dispute reversed)
    store.open_position(
        condition_id="0xloss", token_id="t3",
        question="Will the Knicks win Game 2?", side="YES",
        tokens=26.32, avg_price=0.950, cost_usd=25.00, dry_run=True,
    )
    store.mark_resolved("0xloss", payout_usd=0.0, notes="outcome=NO pnl=-25.00")


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
        # Chinese labels should appear
        assert "Polymarket 套利助手" in body
        assert "演练模式" in body
        assert "已结算盈亏" in body
        assert "正在持有" in body
        assert "已经结清" in body
        # seeded questions should appear
        assert "Lakers" in body
        assert "BTC close above" in body
        assert "Knicks" in body
        # PnL: +2.03 - 25.00 = -22.97
        assert "-22.97" in body

        # API endpoints
        r = client.get("/api/summary")
        assert r.status_code == 200
        s = r.get_json()
        assert s["open_count"] == 1
        assert s["closed_count"] == 2
        assert abs(s["realized_pnl"] - (-22.97)) < 0.01
        assert abs(s["win_rate"] - 0.5) < 0.001

        r = client.get("/api/pnl-series")
        assert r.status_code == 200
        series = r.get_json()
        assert len(series) == 2
        # cumulative: first +2.03, then +2.03 - 25 = -22.97
        assert abs(series[-1][1] - (-22.97)) < 0.01


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
