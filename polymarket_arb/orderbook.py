"""CLOB orderbook reader.

Read-only book snapshot via the public CLOB REST endpoint. We do not
use the WebSocket here because the strategy polls every ~90s and the
opportunity window for resolution-time arb is hours, not milliseconds.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import requests

log = logging.getLogger(__name__)


@dataclass
class BookSide:
    price: float
    size: float  # in tokens (each token redeems for $1 if YES wins)


@dataclass
class OrderBook:
    token_id: str
    bids: list[BookSide]  # sorted high-to-low
    asks: list[BookSide]  # sorted low-to-high

    def fillable_cost(self, max_tokens: float, max_price: float) -> tuple[float, float]:
        """Walk the ask side and return (tokens_bought, usdc_spent) for
        the largest order we can place that stays within max_price.

        We are a price-taker buying YES near $1, so we eat the ask side.
        """
        tokens = 0.0
        cost = 0.0
        for ask in self.asks:
            if ask.price > max_price:
                break
            take = min(ask.size, max_tokens - tokens)
            if take <= 0:
                break
            tokens += take
            cost += take * ask.price
        return tokens, cost

    @property
    def best_ask(self) -> float | None:
        return self.asks[0].price if self.asks else None

    @property
    def best_bid(self) -> float | None:
        return self.bids[0].price if self.bids else None


def fetch_book(clob_base: str, token_id: str) -> OrderBook | None:
    """Fetch the full orderbook for one CLOB token."""
    try:
        resp = requests.get(
            f"{clob_base}/book",
            params={"token_id": token_id},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError) as e:
        log.warning("failed to fetch book for %s: %s", token_id, e)
        return None

    bids = [
        BookSide(price=float(b["price"]), size=float(b["size"]))
        for b in data.get("bids", [])
    ]
    asks = [
        BookSide(price=float(a["price"]), size=float(a["size"]))
        for a in data.get("asks", [])
    ]
    bids.sort(key=lambda b: b.price, reverse=True)
    asks.sort(key=lambda a: a.price)
    return OrderBook(token_id=token_id, bids=bids, asks=asks)
