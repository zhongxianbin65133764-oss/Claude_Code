"""Read-only Gamma API client for market discovery.

Gamma is Polymarket's metadata API. No auth required, no rate limit
enforcement we have hit so far. Used to find markets whose event time
has passed but UMA hasn't resolved yet.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterator

import requests

log = logging.getLogger(__name__)


@dataclass
class Market:
    """A flattened view of a Polymarket market."""
    condition_id: str
    question: str
    description: str
    end_date: datetime
    category: str
    yes_token_id: str
    no_token_id: str
    closed: bool
    active: bool
    accepting_orders: bool
    volume_usd: float

    @property
    def hours_past_end(self) -> float:
        return (datetime.now(timezone.utc) - self.end_date).total_seconds() / 3600.0


def _parse_market(raw: dict) -> Market | None:
    """Parse a Gamma /markets response item. Returns None if malformed."""
    try:
        # Token IDs live in the 'clobTokenIds' field as a JSON-encoded string.
        token_ids_raw = raw.get("clobTokenIds")
        if not token_ids_raw:
            return None
        token_ids = json.loads(token_ids_raw) if isinstance(token_ids_raw, str) else token_ids_raw
        if len(token_ids) != 2:
            return None  # only binary markets for this strategy

        # Outcomes field tells us which token_id maps to YES vs NO.
        outcomes_raw = raw.get("outcomes", '["Yes", "No"]')
        outcomes = json.loads(outcomes_raw) if isinstance(outcomes_raw, str) else outcomes_raw
        # Standard Polymarket convention: index 0 = Yes, index 1 = No.
        if outcomes[0].lower() not in {"yes", "y"}:
            return None

        end_date_raw = raw.get("endDate") or raw.get("end_date_iso")
        if not end_date_raw:
            return None
        end_date = datetime.fromisoformat(end_date_raw.replace("Z", "+00:00"))

        return Market(
            condition_id=raw["conditionId"],
            question=raw.get("question", ""),
            description=raw.get("description", ""),
            end_date=end_date,
            category=raw.get("category", ""),
            yes_token_id=str(token_ids[0]),
            no_token_id=str(token_ids[1]),
            closed=bool(raw.get("closed", False)),
            active=bool(raw.get("active", True)),
            accepting_orders=bool(raw.get("acceptingOrders", False)),
            volume_usd=float(raw.get("volumeNum", 0) or 0),
        )
    except (KeyError, ValueError, json.JSONDecodeError) as e:
        log.debug("skipping malformed market: %s", e)
        return None


def fetch_resolving_markets(
    gamma_base: str,
    min_age_hours: float,
    max_age_days: float,
    page_size: int = 100,
) -> Iterator[Market]:
    """Yield markets whose event ended between (now - max_age_days)
    and (now - min_age_hours), and are still accepting orders.

    These are the candidates for resolution-time arbitrage: the event
    is decided but the market hasn't been settled by UMA yet, so YES
    or NO is often trading at 95-98c instead of $1.00.
    """
    now = datetime.now(timezone.utc)
    end_max = now - timedelta(hours=min_age_hours)
    end_min = now - timedelta(days=max_age_days)

    offset = 0
    while True:
        params = {
            "closed": "false",
            "active": "true",
            "limit": page_size,
            "offset": offset,
            "end_date_min": end_min.isoformat(),
            "end_date_max": end_max.isoformat(),
            "order": "endDate",
            "ascending": "false",
        }
        url = f"{gamma_base}/markets"
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        items = resp.json()
        if not items:
            return

        for raw in items:
            market = _parse_market(raw)
            if market is None:
                continue
            yield market

        if len(items) < page_size:
            return
        offset += page_size
