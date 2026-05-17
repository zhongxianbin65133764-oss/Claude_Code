"""Realism layer for dry-run mode.

Two mechanisms:

1. VerificationQueue (empirical):
   When an opportunity is detected, we do NOT immediately log it as
   filled. We enqueue it and re-fetch the same book after
   `verification_delay_seconds`. The later book is the truth — if best
   ask has moved above our limit, we missed the trade (another bot
   took it, or the seller cancelled). This emulates real-world
   detection -> submission latency, with zero parameter tuning.

2. FrictionModel (parametric):
   Even verified fills are not free money. We deduct:
     - Gas (every trade)
     - Adverse-fill probability (some fills are toxic)
     - Average fill ratio (rarely get full size)
     - UMA dispute rate (occasionally loses everything)
   For each dry-run fill we store BOTH the ideal cost/payout and the
   friction-adjusted cost/payout, so the dashboard can show the gap.

In LIVE mode neither is used — real fills and real settlements speak
for themselves.
"""
from __future__ import annotations

import hashlib
import logging
import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable

from .orderbook import OrderBook

log = logging.getLogger(__name__)


# --------------------------------------------------------------------------
# VerificationQueue
# --------------------------------------------------------------------------

@dataclass
class PendingVerification:
    token_id: str
    condition_id: str
    question: str
    side: str
    detected_at: datetime
    detected_ask: float
    detected_depth_usd: float
    max_buy_price: float
    intended_usd: float


@dataclass
class VerificationResult:
    pending: PendingVerification
    verified_at: datetime
    verified_ask: float | None       # None if book vanished
    verified_depth_usd: float
    would_have_filled: bool
    realistic_tokens: float          # what we would actually have got
    realistic_cost_usd: float        # what we would actually have paid


class VerificationQueue:
    """In-memory queue of opportunities awaiting re-check.

    Dedupes by token_id so re-detecting the same opportunity every
    scan doesn't spam the verification log.
    """

    def __init__(self, delay_seconds: float):
        self.delay = delay_seconds
        self._pending: dict[str, PendingVerification] = {}

    def __len__(self) -> int:
        return len(self._pending)

    def enqueue(self, pv: PendingVerification) -> bool:
        if pv.token_id in self._pending:
            return False
        self._pending[pv.token_id] = pv
        return True

    def ready(self, now: datetime) -> list[PendingVerification]:
        """Return and remove all entries whose verification time has come."""
        out: list[PendingVerification] = []
        for tid, pv in list(self._pending.items()):
            if (now - pv.detected_at).total_seconds() >= self.delay:
                out.append(pv)
                del self._pending[tid]
        return out


def verify(
    pv: PendingVerification,
    fetch_book: Callable[[str], OrderBook | None],
) -> VerificationResult:
    """Re-fetch the book and decide whether we would have filled."""
    now = datetime.now(timezone.utc)
    book = fetch_book(pv.token_id)
    if book is None or not book.asks:
        return VerificationResult(
            pending=pv,
            verified_at=now,
            verified_ask=None,
            verified_depth_usd=0.0,
            would_have_filled=False,
            realistic_tokens=0.0,
            realistic_cost_usd=0.0,
        )

    best_ask = book.best_ask
    assert best_ask is not None

    if best_ask > pv.max_buy_price:
        # Ask drifted above our limit during the latency window.
        # Another bot won the race, or the seller cancelled.
        _, depth_at_limit = book.fillable_cost(1e9, pv.max_buy_price)
        return VerificationResult(
            pending=pv,
            verified_at=now,
            verified_ask=best_ask,
            verified_depth_usd=depth_at_limit,
            would_have_filled=False,
            realistic_tokens=0.0,
            realistic_cost_usd=0.0,
        )

    # Still fillable. Walk the (possibly thinner) post-latency book.
    intended_tokens = pv.intended_usd / pv.max_buy_price
    tokens = 0.0
    cost = 0.0
    for ask in book.asks:
        if ask.price > pv.max_buy_price:
            break
        affordable = (pv.intended_usd - cost) / ask.price
        take = min(ask.size, affordable, intended_tokens - tokens)
        if take <= 0:
            break
        tokens += take
        cost += take * ask.price

    _, depth_at_limit = book.fillable_cost(1e9, pv.max_buy_price)
    return VerificationResult(
        pending=pv,
        verified_at=now,
        verified_ask=best_ask,
        verified_depth_usd=depth_at_limit,
        would_have_filled=tokens > 0,
        realistic_tokens=tokens,
        realistic_cost_usd=cost,
    )


# --------------------------------------------------------------------------
# FrictionModel
# --------------------------------------------------------------------------

@dataclass
class FrictionApplied:
    """Result of applying friction to a single verified fill."""
    realistic_tokens: float          # after partial-fill shrinkage
    realistic_cost_usd: float        # tokens * avg_price + gas
    is_adverse: bool                 # was this an adverse-selection fill?
    will_be_disputed: bool           # will UMA reverse this?
    notes: str


class FrictionModel:
    """Stateless friction calculator used during dry-run.

    Random draws are seeded by (token_id, detection_time) so the same
    opportunity always produces the same realistic outcome across runs.
    This keeps the simulation reproducible.
    """

    def __init__(
        self,
        gas_cost_usd: float,
        expected_fill_ratio: float,
        adverse_fill_rate: float,
        uma_dispute_rate: float,
    ):
        self.gas = gas_cost_usd
        self.fill_ratio = expected_fill_ratio
        self.adverse_rate = adverse_fill_rate
        self.dispute_rate = uma_dispute_rate

    def _rng(self, seed: str) -> random.Random:
        h = hashlib.sha256(seed.encode()).digest()
        return random.Random(int.from_bytes(h[:8], "big"))

    def apply_to_fill(
        self,
        token_id: str,
        detected_at: datetime,
        verified_tokens: float,
        verified_cost: float,
    ) -> FrictionApplied:
        """Apply partial-fill ratio + gas + adverse/dispute flags."""
        rng = self._rng(f"{token_id}|{detected_at.isoformat()}")

        # Per-fill realised ratio drawn from a triangular distribution
        # centred on expected_fill_ratio.
        low = max(0.1, self.fill_ratio - 0.3)
        high = min(1.0, self.fill_ratio + 0.2)
        realised_ratio = rng.triangular(low, high, self.fill_ratio)

        realistic_tokens = verified_tokens * realised_ratio
        avg_px = (verified_cost / verified_tokens) if verified_tokens else 0.0
        realistic_cost = realistic_tokens * avg_px + self.gas

        is_adverse = rng.random() < self.adverse_rate
        will_be_disputed = (not is_adverse) and rng.random() < self.dispute_rate

        notes = []
        notes.append(f"fill_ratio={realised_ratio:.0%}")
        notes.append(f"gas=${self.gas:.2f}")
        if is_adverse:
            notes.append("adverse_fill")
        if will_be_disputed:
            notes.append("uma_dispute")

        return FrictionApplied(
            realistic_tokens=realistic_tokens,
            realistic_cost_usd=realistic_cost,
            is_adverse=is_adverse,
            will_be_disputed=will_be_disputed,
            notes=";".join(notes),
        )

    def realistic_payout(
        self,
        nominal_tokens: float,
        side_won: bool,
        is_adverse: bool,
        will_be_disputed: bool,
    ) -> tuple[float, str]:
        """Compute realistic payout for a closed position.

        Returns (payout_usd, reason).
        Nominal payout = tokens if side_won else 0.
        Adverse fills always pay 0 (toxic flow assumption).
        UMA disputes flip the outcome.
        """
        if is_adverse:
            return 0.0, "adverse-fill: paid out to 0"
        if will_be_disputed:
            # Disputed: flip outcome
            if side_won:
                return 0.0, "uma_dispute: outcome reversed -> loss"
            else:
                return nominal_tokens, "uma_dispute: outcome reversed -> win"
        return (nominal_tokens if side_won else 0.0), ""
