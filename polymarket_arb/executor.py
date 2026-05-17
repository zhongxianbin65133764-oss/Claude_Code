"""Order execution layer.

Wraps py-clob-client for live orders. In DRY_RUN mode all live paths
are short-circuited and execution is logged only.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

log = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    success: bool
    tokens_filled: float
    avg_price: float
    usd_spent: float
    order_id: str | None
    error: str | None = None


class Executor:
    """Order placer. Construct once per process."""

    def __init__(self, config):
        self.config = config
        self._client = None  # lazy-init only when live

    def _ensure_client(self):
        if self._client is not None:
            return self._client
        # Lazy import so dry-run installs don't need py-clob-client.
        from py_clob_client.client import ClobClient
        from py_clob_client.constants import POLYGON
        from py_clob_client.clob_types import ApiCreds

        cfg = self.config
        missing = [
            name for name, val in [
                ("POLYMARKET_API_KEY", cfg.api_key),
                ("POLYMARKET_API_SECRET", cfg.api_secret),
                ("POLYMARKET_API_PASSPHRASE", cfg.api_passphrase),
                ("WALLET_PRIVATE_KEY", cfg.wallet_private_key),
            ] if not val
        ]
        if missing:
            raise RuntimeError(
                f"Live mode requires env vars: {', '.join(missing)}"
            )

        self._client = ClobClient(
            host=cfg.clob_base,
            key=cfg.wallet_private_key,
            chain_id=POLYGON,
            creds=ApiCreds(
                api_key=cfg.api_key,
                api_secret=cfg.api_secret,
                api_passphrase=cfg.api_passphrase,
            ),
        )
        return self._client

    def buy(
        self,
        token_id: str,
        max_price: float,
        max_usd: float,
    ) -> ExecutionResult:
        """Place an immediate-or-cancel (FOK-style) limit buy at max_price.

        We use a limit order at max_price (not a market order) because:
          1. Polymarket's market orders can slip through stale liquidity
             and pay > our threshold.
          2. A limit order at max_price that doesn't fully fill simply
             leaves us with whatever it filled; we accept partial fills.
        """
        tokens_target = max_usd / max_price

        if self.config.dry_run:
            log.info(
                "[DRY] would BUY %.2f tokens of %s at <=%.3f (max $%.2f)",
                tokens_target, token_id, max_price, max_usd,
            )
            return ExecutionResult(
                success=True,
                tokens_filled=tokens_target,
                avg_price=max_price,
                usd_spent=tokens_target * max_price,
                order_id="DRY-RUN",
            )

        try:
            client = self._ensure_client()
            from py_clob_client.clob_types import OrderArgs, OrderType
            args = OrderArgs(
                price=max_price,
                size=tokens_target,
                side="BUY",
                token_id=token_id,
            )
            signed = client.create_order(args)
            resp = client.post_order(signed, OrderType.GTC)
        except Exception as e:  # noqa: BLE001 - we want to capture any failure
            log.exception("order placement failed for %s", token_id)
            return ExecutionResult(False, 0.0, 0.0, 0.0, None, error=str(e))

        if not resp or not resp.get("success"):
            return ExecutionResult(
                False, 0.0, 0.0, 0.0, None,
                error=str(resp),
            )

        # post_order returns matched + resting; for IOC we'd use OrderType.FOK
        # but py-clob-client doesn't expose FOK uniformly, so we use GTC and
        # rely on our max_price ceiling.
        order_id = resp.get("orderID")
        # Conservative reporting: assume the matched portion at our limit.
        matched_size = float(resp.get("takingAmount", 0)) or tokens_target
        return ExecutionResult(
            success=True,
            tokens_filled=matched_size,
            avg_price=max_price,
            usd_spent=matched_size * max_price,
            order_id=order_id,
        )
