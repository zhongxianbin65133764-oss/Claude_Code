"""SQLite store for open positions and trade log.

Kept deliberately simple. Two tables: positions (one row per open buy)
and trades (immutable append-only log).
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
    side TEXT NOT NULL,            -- 'YES' or 'NO'
    tokens REAL NOT NULL,
    avg_price REAL NOT NULL,
    cost_usd REAL NOT NULL,
    opened_at TEXT NOT NULL,
    resolved INTEGER NOT NULL DEFAULT 0,
    payout_usd REAL,
    closed_at TEXT
);

CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    condition_id TEXT NOT NULL,
    token_id TEXT NOT NULL,
    side TEXT NOT NULL,
    action TEXT NOT NULL,          -- 'BUY' | 'SETTLE'
    tokens REAL NOT NULL,
    price REAL NOT NULL,
    usd REAL NOT NULL,
    dry_run INTEGER NOT NULL,
    notes TEXT
);
"""


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


class PositionStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        with self._conn() as c:
            c.executescript(SCHEMA)

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

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
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._conn() as c:
            c.execute(
                """INSERT OR IGNORE INTO positions
                   (condition_id, token_id, question, side, tokens,
                    avg_price, cost_usd, opened_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (condition_id, token_id, question, side, tokens,
                 avg_price, cost_usd, now),
            )
            c.execute(
                """INSERT INTO trades
                   (ts, condition_id, token_id, side, action,
                    tokens, price, usd, dry_run, notes)
                   VALUES (?, ?, ?, ?, 'BUY', ?, ?, ?, ?, ?)""",
                (now, condition_id, token_id, side, tokens, avg_price,
                 cost_usd, int(dry_run), None),
            )

    def mark_resolved(
        self,
        condition_id: str,
        payout_usd: float,
        notes: str | None = None,
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
                """UPDATE positions SET resolved=1, payout_usd=?, closed_at=?
                   WHERE condition_id=?""",
                (payout_usd, now, condition_id),
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

    @staticmethod
    def _row_to_position(r: sqlite3.Row) -> Position:
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
        )
