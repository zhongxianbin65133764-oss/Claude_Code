"""Strategy configuration.

All thresholds are intentionally conservative for a first run.
Tighten or loosen after you have at least 30 paper-trade observations.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    return float(raw) if raw else default


@dataclass(frozen=True)
class Config:
    # Runtime
    dry_run: bool = _env_bool("DRY_RUN", True)

    # Polymarket API
    gamma_base: str = "https://gamma-api.polymarket.com"
    clob_base: str = "https://clob.polymarket.com"
    api_key: str = os.getenv("POLYMARKET_API_KEY", "")
    api_secret: str = os.getenv("POLYMARKET_API_SECRET", "")
    api_passphrase: str = os.getenv("POLYMARKET_API_PASSPHRASE", "")

    # Wallet
    wallet_private_key: str = os.getenv("WALLET_PRIVATE_KEY", "")
    polygon_rpc: str = os.getenv("POLYGON_RPC_URL", "https://polygon-rpc.com")

    # ---- Entry thresholds ----
    # Max ask price we are willing to pay. 96c leaves 4c per dollar for
    # UMA dispute risk, gas, and time value of money.
    max_buy_price: float = _env_float("MAX_BUY_PRICE", 0.96)
    # Below this price the market is signalling uncertainty -> skip.
    min_buy_price: float = _env_float("MIN_BUY_PRICE", 0.88)

    # ---- Market eligibility ----
    # Market end_date must be at least this old (lets the dust settle).
    min_market_age_hours: float = _env_float("MIN_MARKET_AGE_HOURS", 2.0)
    # If a market is stuck past this without resolving, something is wrong
    # (UMA dispute or oracle issue) -> avoid.
    max_market_age_days: float = _env_float("MAX_MARKET_AGE_DAYS", 10.0)
    # Need at least this much depth at or below max_buy_price to bother.
    min_book_depth_usd: float = _env_float("MIN_BOOK_DEPTH_USD", 50.0)

    # ---- Sizing ----
    max_position_size_usd: float = _env_float("MAX_POSITION_SIZE_USD", 25.0)
    max_total_exposure_usd: float = _env_float("MAX_TOTAL_EXPOSURE_USD", 200.0)

    # ---- Loop ----
    scan_interval_seconds: float = _env_float("SCAN_INTERVAL_SECONDS", 90.0)

    # ---- Storage ----
    db_path: str = os.getenv("DB_PATH", "positions.db")
    log_path: str = os.getenv("LOG_PATH", "arb_bot.log")

    # ---- Paper/live realism layer ----
    # In dry-run we don't just "assume" the book we saw is fillable.
    # Instead we re-fetch the same book after this many seconds and
    # treat the *later* book as the truth, simulating latency from
    # detection -> submission and competition from other arb bots.
    verification_delay_seconds: float = _env_float("VERIFICATION_DELAY_SECONDS", 60.0)

    # Per-trade gas + signing overhead, paid even if the order partially
    # fills or gets cancelled. Polygon is cheap but it adds up.
    estimated_gas_cost_usd: float = _env_float("ESTIMATED_GAS_COST_USD", 0.10)

    # Of orders that DO find liquidity at our limit price, what fraction
    # of intended size fills on average? Real fills are usually partial
    # because the visible book has hidden cancellations and competing
    # takers.
    expected_fill_ratio: float = _env_float("EXPECTED_FILL_RATIO", 0.70)

    # Probability that a fill we got was an "adverse" fill — i.e. the
    # only reason someone sold to us at 96c was that they knew the
    # market was about to be voided / disputed / re-resolved. These
    # fills go to zero. Set conservatively based on observed dispute
    # base rate; tighten with empirical data.
    adverse_fill_rate: float = _env_float("ADVERSE_FILL_RATE", 0.03)

    # Probability that a position we hold gets UMA-disputed and reversed
    # despite passing all safety filters. Applies on top of adverse fill.
    uma_dispute_rate: float = _env_float("UMA_DISPUTE_RATE", 0.02)


# Categories where outcomes are mechanically verifiable (price feeds,
# game scores, on-chain data). UMA is least likely to dispute these.
SAFE_CATEGORIES = {
    "Sports",
    "Crypto",
    "Crypto Prices",
}

# Categories with subjective resolution criteria -> UMA dispute risk.
RISKY_CATEGORIES = {
    "Politics",
    "Elections",
    "Geopolitics",
    "Pop Culture",
    "Awards",
}

# Keywords in question text that flag dispute risk regardless of category.
BLACKLIST_KEYWORDS = {
    "war",
    "ceasefire",
    "indicted",
    "indictment",
    "arrested",
    "scandal",
    "pope",
    "leak",
    "rumor",
    "tweet",
    "post",  # "Will X post Y" -> deletion ambiguity
}


CONFIG = Config()
