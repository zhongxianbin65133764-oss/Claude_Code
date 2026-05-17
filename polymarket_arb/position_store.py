"""SQLite store for positions, trades, and dry-run realism measurements.

Schema:
  positions       - one row per opened buy (live or dry-run)
                    dual cost/payout columns: ideal_* (what dry-run thought)
                    vs realistic_* (after friction). For live trades the
                    realistic_* columns are NULL because real fills are
                    the realistic truth.
  trades          - immutable append-only log
  verifications   - dry-run only: each opportunity detection + the
                    post-latency book re-check, so we can measure
                    real-world fill rate without parameter guessing
"""
from __future__ import annotations

import logging
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterator

log = logging.getLogger(__name__)


SCHEMA = """
CREATE TABLE IF NOT EXISTS positions (
    condition_id TEXT PRIMARY KEY,
    token_id TEXT NOT NULL,
    question TEXT NOT NULL,
    side TEXT NOT NULL,
    tokens REAL NOT NULL,
    avg_price REAL NOT NULL,
    cost_usd REAL NOT NULL,
    opened_at TEXT NOT NULL,
    resolved INTEGER NOT NULL DEFAULT 0,
    payout_usd REAL,
    closed_at TEXT,
    -- Realism layer (NULL for live trades):
    realistic_tokens REAL,
    realistic_cost_usd REAL,
    realistic_payout_usd REAL,
    sim_flags TEXT
);

CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    condition_id TEXT NOT NULL,
    token_id TEXT NOT NULL,
    side TEXT NOT NULL,
    action TEXT NOT NULL,
    tokens REAL NOT NULL,
    price REAL NOT NULL,
    usd REAL NOT NULL,
    dry_run INTEGER NOT NULL,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS verifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    condition_id TEXT NOT NULL,
    token_id TEXT NOT NULL,
    side TEXT NOT NULL,
    detected_at TEXT NOT NULL,
    detected_ask REAL NOT NULL,
    detected_depth_usd REAL NOT NULL,
    intended_usd REAL NOT NULL,
    verified_at TEXT NOT NULL,
    verified_ask REAL,
    verified_depth_usd REAL NOT NULL,
    would_have_filled INTEGER NOT NULL,
    realistic_tokens REAL NOT NULL,
    realistic_cost_usd REAL NOT NULL
);
"""

# Columns added after v0.1; tolerate older DBs.
_OPTIONAL_COLUMNS_POSITIONS = [
    ("realistic_tokens", "REAL"),
    ("realistic_cost_usd", "REAL"),
    ("realistic_payout_usd", "REAL"),
    ("sim_flags", "TEXT"),
]


@dataclass
class Position:
    condition_id: str
    token_id: str
    question: str
    side: str
    tokens: float
    avg_price: float
    cost_usd: float
    opened_at: datetime
    resolved: bool
    payout_usd: float | None
    closed_at: datetime | None
    realistic_tokens: float | None
    realistic_cost_usd: float | None
    realistic_payout_usd: float | None
    sim_flags: str | None


class PositionStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        with self._conn() as c:
            c.executescript(SCHEMA)
            self._migrate_positions(c)

    def _migrate_positions(self, c: sqlite3.Connection) -> None:
        existing = {r["name"] for r in c.execute("PRAGMA table_info(positions)")}
        for col, typ in _OPTIONAL_COLUMNS_POSITIONS:
            if col not in existing:
                c.execute(f"ALTER TABLE positions ADD COLUMN {col} {typ}")

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    # ---- positions ----

    def open_position(
        self,
        condition_id: str,
        token_id: str,
        question: str,
        side: str,
        tokens: float,
        avg_price: float,
        cost_usd: float,
        dry_run: bool,
        realistic_tokens: float | None = None,
        realistic_cost_usd: float | None = None,
        sim_flags: str | None = None,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._conn() as c:
            c.execute(
                """INSERT OR IGNORE INTO positions
                   (condition_id, token_id, question, side, tokens,
                    avg_price, cost_usd, opened_at,
                    realistic_tokens, realistic_cost_usd, sim_flags)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (condition_id, token_id, question, side, tokens,
                 avg_price, cost_usd, now,
                 realistic_tokens, realistic_cost_usd, sim_flags),
            )
            c.execute(
                """INSERT INTO trades
                   (ts, condition_id, token_id, side, action,
                    tokens, price, usd, dry_run, notes)
                   VALUES (?, ?, ?, ?, 'BUY', ?, ?, ?, ?, ?)""",
                (now, condition_id, token_id, side, tokens, avg_price,
                 cost_usd, int(dry_run), sim_flags),
            )

    def mark_resolved(
        self,
        condition_id: str,
        payout_usd: float,
        notes: str | None = None,
        realistic_payout_usd: float | None = None,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._conn() as c:
            row = c.execute(
                "SELECT token_id, side, tokens FROM positions WHERE condition_id=?",
                (condition_id,),
            ).fetchone()
            if not row:
                return
            c.execute(
                """UPDATE positions
                   SET resolved=1, payout_usd=?, closed_at=?,
                       realistic_payout_usd=COALESCE(?, realistic_payout_usd)
                   WHERE condition_id=?""",
                (payout_usd, now, realistic_payout_usd, condition_id),
            )
            c.execute(
                """INSERT INTO trades
                   (ts, condition_id, token_id, side, action,
                    tokens, price, usd, dry_run, notes)
                   VALUES (?, ?, ?, ?, 'SETTLE', ?, ?, ?, 0, ?)""",
                (now, condition_id, row["token_id"], row["side"],
                 row["tokens"], 1.0, payout_usd, notes),
            )

    def open_exposure_usd(self) -> float:
        with self._conn() as c:
            row = c.execute(
                "SELECT COALESCE(SUM(cost_usd), 0) AS s FROM positions WHERE resolved=0"
            ).fetchone()
        return float(row["s"])

    def has_position(self, condition_id: str) -> bool:
        with self._conn() as c:
            row = c.execute(
                "SELECT 1 FROM positions WHERE condition_id=?",
                (condition_id,),
            ).fetchone()
        return row is not None

    def open_positions(self) -> list[Position]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT * FROM positions WHERE resolved=0 ORDER BY opened_at"
            ).fetchall()
        return [self._row_to_position(r) for r in rows]

    def closed_positions(self, limit: int | None = None) -> list[Position]:
        sql = "SELECT * FROM positions WHERE resolved=1 ORDER BY closed_at DESC"
        if limit is not None:
            sql += f" LIMIT {int(limit)}"
        with self._conn() as c:
            rows = c.execute(sql).fetchall()
        return [self._row_to_position(r) for r in rows]

    def cumulative_pnl_series(self, realistic: bool = False) -> list[tuple[str, float]]:
        """Return [(closed_at_iso, cumulative_pnl_usd), ...] chronologically.

        When realistic=True uses realistic_* columns (with fall-back to ideal
        if missing, e.g. live trades).
        """
        if realistic:
            sql = """SELECT closed_at,
                            (COALESCE(realistic_payout_usd, payout_usd) -
                             COALESCE(realistic_cost_usd, cost_usd)) AS pnl
                     FROM positions
                     WHERE resolved=1 AND closed_at IS NOT NULL
                     ORDER BY closed_at"""
        else:
            sql = """SELECT closed_at, (payout_usd - cost_usd) AS pnl
                     FROM positions
                     WHERE resolved=1 AND closed_at IS NOT NULL
                     ORDER BY closed_at"""
        with self._conn() as c:
            rows = c.execute(sql).fetchall()
        series: list[tuple[str, float]] = []
        running = 0.0
        for r in rows:
            running += float(r["pnl"])
            series.append((r["closed_at"], running))
        return series

    def recent_trades(self, limit: int = 50) -> list[dict]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT * FROM trades ORDER BY id DESC LIMIT ?",
                (int(limit),),
            ).fetchall()
        return [dict(r) for r in rows]

    def summary(self) -> dict:
        with self._conn() as c:
            open_row = c.execute(
                """SELECT COUNT(*) AS n, COALESCE(SUM(cost_usd), 0) AS exposure
                   FROM positions WHERE resolved=0"""
            ).fetchone()
            closed_row = c.execute(
                """SELECT COUNT(*) AS n,
                          COALESCE(SUM(cost_usd), 0) AS cost,
                          COALESCE(SUM(payout_usd), 0) AS payout,
                          SUM(CASE WHEN payout_usd > cost_usd THEN 1 ELSE 0 END) AS wins,
                          COALESCE(SUM(COALESCE(realistic_cost_usd, cost_usd)), 0) AS r_cost,
                          COALESCE(SUM(COALESCE(realistic_payout_usd, payout_usd)), 0) AS r_payout
                   FROM positions WHERE resolved=1"""
            ).fetchone()
        cost = float(closed_row["cost"])
        payout = float(closed_row["payout"])
        pnl = payout - cost
        r_cost = float(closed_row["r_cost"])
        r_payout = float(closed_row["r_payout"])
        r_pnl = r_payout - r_cost
        n_closed = int(closed_row["n"])
        wins = int(closed_row["wins"] or 0)
        return {
            "open_count": int(open_row["n"]),
            "open_exposure": float(open_row["exposure"]),
            "closed_count": n_closed,
            "realized_cost": cost,
            "realized_payout": payout,
            "realized_pnl": pnl,
            "win_rate": (wins / n_closed) if n_closed else 0.0,
            "avg_return_pct": ((pnl / cost) * 100) if cost else 0.0,
            # Realism layer
            "realistic_cost": r_cost,
            "realistic_payout": r_payout,
            "realistic_pnl": r_pnl,
            "realistic_avg_return_pct": ((r_pnl / r_cost) * 100) if r_cost else 0.0,
        }

    # ---- verifications ----

    def record_verification(
        self,
        condition_id: str,
        token_id: str,
        side: str,
        detected_at: str,
        detected_ask: float,
        detected_depth_usd: float,
        intended_usd: float,
        verified_at: str,
        verified_ask: float | None,
        verified_depth_usd: float,
        would_have_filled: bool,
        realistic_tokens: float,
        realistic_cost_usd: float,
    ) -> None:
        with self._conn() as c:
            c.execute(
                """INSERT INTO verifications
                   (condition_id, token_id, side, detected_at, detected_ask,
                    detected_depth_usd, intended_usd, verified_at,
                    verified_ask, verified_depth_usd, would_have_filled,
                    realistic_tokens, realistic_cost_usd)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (condition_id, token_id, side, detected_at, detected_ask,
                 detected_depth_usd, intended_usd, verified_at,
                 verified_ask, verified_depth_usd, int(would_have_filled),
                 realistic_tokens, realistic_cost_usd),
            )

    def verification_stats(self) -> dict:
        """Aggregate the gap between detection and post-latency reality."""
        with self._conn() as c:
            row = c.execute(
                """SELECT COUNT(*) AS n,
                          SUM(would_have_filled) AS filled,
                          COALESCE(SUM(intended_usd), 0) AS intended,
                          COALESCE(SUM(realistic_cost_usd), 0) AS realistic,
                          COALESCE(AVG(CASE WHEN would_have_filled
                                            THEN verified_ask - detected_ask
                                            ELSE NULL END), 0) AS avg_drift
                   FROM verifications"""
            ).fetchone()
        n = int(row["n"])
        filled = int(row["filled"] or 0)
        intended = float(row["intended"])
        realistic = float(row["realistic"])
        return {
            "detected": n,
            "filled": filled,
            "fill_rate": (filled / n) if n else 0.0,
            "intended_usd": intended,
            "realistic_usd": realistic,
            "capture_ratio": (realistic / intended) if intended else 0.0,
            "avg_price_drift": float(row["avg_drift"] or 0.0),
        }

    @staticmethod
    def _row_to_position(r: sqlite3.Row) -> Position:
        # Tolerate older rows missing the realism columns.
        keys = r.keys()
        return Position(
            condition_id=r["condition_id"],
            token_id=r["token_id"],
            question=r["question"],
            side=r["side"],
            tokens=r["tokens"],
            avg_price=r["avg_price"],
            cost_usd=r["cost_usd"],
            opened_at=datetime.fromisoformat(r["opened_at"]),
            resolved=bool(r["resolved"]),
            payout_usd=r["payout_usd"],
            closed_at=datetime.fromisoformat(r["closed_at"]) if r["closed_at"] else None,
            realistic_tokens=r["realistic_tokens"] if "realistic_tokens" in keys else None,
            realistic_cost_usd=r["realistic_cost_usd"] if "realistic_cost_usd" in keys else None,
            realistic_payout_usd=r["realistic_payout_usd"] if "realistic_payout_usd" in keys else None,
            sim_flags=r["sim_flags"] if "sim_flags" in keys else None,
        )
