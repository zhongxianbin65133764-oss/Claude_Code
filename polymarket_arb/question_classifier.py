"""Fine-grained market sub-classification.

The top-level Polymarket category ('Sports', 'Crypto') is too coarse
for risk management — a "Will the Lakers win?" market behaves very
differently from a "Will LeBron score 30+?" market even though both
are tagged 'Sports'.

This module classifies a market by parsing the question text with
regex, returning:
  - subcategory: one of a small enumeration
  - confidence : how sure we are about the classification
  - facts     : for crypto_price markets, the (ticker, direction,
                threshold, date) so we can independently verify the
                outcome via an external price feed

Subcategories and their typical UMA dispute rates (rough estimates):
  crypto_price      ~0.1%    mechanically resolvable from price feed
  team_moneyline    ~0.3%    'A beat B' is unambiguous in major leagues
  team_score        ~1-2%    spreads can have edge-case rounding
  player_prop       ~5-10%   stat definitions, time-on-court rules
  sports_event      ~3-5%    cancellations, weather, injury rules
  other             unknown  -> reject by default
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Iterable

# Symbols we will accept for crypto-price classification. Extend as needed.
CRYPTO_TICKERS: dict[str, str] = {
    # name-or-alias  -> canonical ticker
    "btc": "BTC", "bitcoin": "BTC",
    "eth": "ETH", "ethereum": "ETH", "ether": "ETH",
    "sol": "SOL", "solana": "SOL",
    "xrp": "XRP", "ripple": "XRP",
    "doge": "DOGE", "dogecoin": "DOGE",
    "ada": "ADA", "cardano": "ADA",
    "avax": "AVAX", "avalanche": "AVAX",
    "matic": "MATIC", "polygon": "MATIC",
    "dot": "DOT", "polkadot": "DOT",
    "link": "LINK", "chainlink": "LINK",
    "bnb": "BNB",
    "ltc": "LTC", "litecoin": "LTC",
}

# Major US sports leagues whose moneyline markets are mechanical.
# We match on team-name-style words; if both teams parse, it's a moneyline.
MAJOR_TEAM_KEYWORDS = {
    "lakers", "celtics", "warriors", "heat", "knicks", "76ers", "bucks",
    "nuggets", "suns", "mavericks", "mavs", "clippers", "nets", "raptors",
    "bulls", "cavaliers", "cavs", "pacers", "rockets", "spurs", "thunder",
    "timberwolves", "wolves", "jazz", "trail blazers", "blazers", "kings",
    "grizzlies", "pistons", "hornets", "magic", "wizards", "hawks",
    "chiefs", "bengals", "eagles", "cowboys", "patriots", "49ers", "ravens",
    "bills", "dolphins", "jets", "steelers", "browns", "broncos", "raiders",
    "chargers", "rams", "seahawks", "cardinals", "packers", "vikings",
    "lions", "bears", "saints", "falcons", "buccaneers", "panthers",
    "titans", "jaguars", "texans", "colts", "commanders", "giants",
    "yankees", "red sox", "dodgers", "giants", "cubs", "mets", "phillies",
    "braves", "astros", "rangers", "blue jays", "orioles", "rays",
    "marlins", "nationals", "cardinals", "brewers", "reds", "pirates",
    "white sox", "guardians", "twins", "tigers", "royals", "athletics",
    "mariners", "angels", "padres", "diamondbacks", "rockies",
}

# Phrases that signal a player-prop market — these have notoriously
# fiddly resolution rules.
PLAYER_PROP_PATTERNS = [
    re.compile(r"\b(score|points|assists|rebounds|goals|yards|"
               r"touchdowns|home runs|hits|strikeouts|saves|blocks|"
               r"steals|tackles|interceptions)\b", re.I),
    re.compile(r"\b(first|most|leading) (scorer|rusher|passer)\b", re.I),
    re.compile(r"\bMVP\b", re.I),
]

# Words suggesting subjective / disputable resolution.
SUBJECTIVE_PATTERNS = [
    re.compile(r"\b(official|officially|deemed|determined|considered|"
               r"declared|judged|ruled)\b", re.I),
    re.compile(r"\b(controversy|controversial|disputed|"
               r"investigation|investigated)\b", re.I),
]


@dataclass
class ClassifiedMarket:
    subcategory: str           # 'crypto_price' | 'team_moneyline' | ...
    confidence: str            # 'high' | 'medium' | 'low'
    # Filled in only for crypto_price:
    ticker: str | None = None
    direction: str | None = None       # 'above' or 'below'
    threshold_usd: float | None = None
    target_date: date | None = None
    notes: str = ""


# ---------------------------------------------------------------------------
# Crypto price classifier
# ---------------------------------------------------------------------------

# Examples we want to parse:
#   "Will BTC close above $100,000 on May 8?"
#   "Will Bitcoin reach $100k on 2026-05-08?"
#   "Will ETH be above $5000 by end of May?"
#   "Will Solana close below $200 on May 4, 2026?"
_CRYPTO_PRICE_RE = re.compile(
    r"\b(?P<ticker>" + "|".join(re.escape(k) for k in CRYPTO_TICKERS) + r")\b"
    r".{0,40}?"
    r"\b(?P<direction>above|below|over|under|reach|hit|break)\b"
    r".{0,20}?"
    r"\$?\s*(?P<threshold>[\d,]+(?:\.\d+)?)\s*(?P<unit>k|m|thousand|million)?\b",
    re.I | re.S,
)

# Date forms: "on May 8", "by May 8", "on 2026-05-08", "on May 8 2026"
_DATE_PATTERNS = [
    re.compile(r"\b(?P<y>\d{4})-(?P<m>\d{1,2})-(?P<d>\d{1,2})\b"),
    re.compile(r"\bon\s+(?P<month>jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+(?P<d>\d{1,2})(?:,?\s+(?P<y>\d{4}))?\b", re.I),
    re.compile(r"\bby\s+(?P<month>jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+(?P<d>\d{1,2})(?:,?\s+(?P<y>\d{4}))?\b", re.I),
]
_MONTH_NUM = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def _parse_date(text: str, fallback_year: int) -> date | None:
    for pat in _DATE_PATTERNS:
        m = pat.search(text)
        if not m:
            continue
        try:
            if "month" in m.groupdict():
                month = _MONTH_NUM[m.group("month")[:3].lower()]
                day = int(m.group("d"))
                year = int(m.group("y")) if m.group("y") else fallback_year
            else:
                year = int(m.group("y"))
                month = int(m.group("m"))
                day = int(m.group("d"))
            return date(year, month, day)
        except (ValueError, KeyError):
            continue
    return None


def _parse_threshold(raw: str, unit: str | None) -> float:
    val = float(raw.replace(",", ""))
    if not unit:
        return val
    u = unit.lower()
    if u in {"k", "thousand"}:
        return val * 1_000
    if u in {"m", "million"}:
        return val * 1_000_000
    return val


def _classify_crypto(question: str, fallback_year: int) -> ClassifiedMarket | None:
    m = _CRYPTO_PRICE_RE.search(question)
    if not m:
        return None
    ticker = CRYPTO_TICKERS[m.group("ticker").lower()]
    raw_direction = m.group("direction").lower()
    direction = "above" if raw_direction in {"above", "over", "reach", "hit", "break"} else "below"
    threshold = _parse_threshold(m.group("threshold"), m.group("unit"))
    target = _parse_date(question, fallback_year)
    if target is None:
        return ClassifiedMarket(
            subcategory="crypto_price",
            confidence="low",
            ticker=ticker, direction=direction, threshold_usd=threshold,
            notes="no date parsed",
        )
    # Sanity checks: threshold must be plausible
    if not (0.01 <= threshold <= 10_000_000):
        return None
    return ClassifiedMarket(
        subcategory="crypto_price",
        confidence="high",
        ticker=ticker,
        direction=direction,
        threshold_usd=threshold,
        target_date=target,
    )


# ---------------------------------------------------------------------------
# Sports classifier
# ---------------------------------------------------------------------------

_TEAM_VS_RE = re.compile(
    r"\b(?:will|do|does|can|the)\b.*?\b(?P<verb>beat|defeat|win|lose|"
    r"sweep|knock out|cover|advance)\b",
    re.I,
)


def _matches_player_prop(question: str) -> bool:
    return any(p.search(question) for p in PLAYER_PROP_PATTERNS)


def _count_team_mentions(question: str) -> int:
    q = question.lower()
    return sum(1 for kw in MAJOR_TEAM_KEYWORDS if re.search(rf"\b{re.escape(kw)}\b", q))


def _classify_sports(question: str) -> ClassifiedMarket | None:
    if _matches_player_prop(question):
        return ClassifiedMarket(subcategory="player_prop", confidence="high",
                                notes="player-stat language detected")
    teams = _count_team_mentions(question)
    has_vs_verb = bool(_TEAM_VS_RE.search(question))
    if teams >= 2 and has_vs_verb:
        return ClassifiedMarket(subcategory="team_moneyline", confidence="high")
    if teams >= 1 and has_vs_verb:
        return ClassifiedMarket(subcategory="team_moneyline", confidence="medium")
    if teams >= 1:
        return ClassifiedMarket(subcategory="sports_event", confidence="medium",
                                notes="single team referenced, no clear matchup verb")
    return None


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def classify(
    question: str,
    fallback_year: int | None = None,
) -> ClassifiedMarket:
    """Classify a market question. Always returns a ClassifiedMarket;
    falls back to subcategory='other' if no pattern matches."""
    if fallback_year is None:
        fallback_year = datetime.utcnow().year
    if not question:
        return ClassifiedMarket(subcategory="other", confidence="low",
                                notes="empty question")

    # Subjective-language guard
    for p in SUBJECTIVE_PATTERNS:
        if p.search(question):
            return ClassifiedMarket(
                subcategory="other", confidence="low",
                notes="subjective resolution language",
            )

    cp = _classify_crypto(question, fallback_year)
    if cp:
        return cp

    sp = _classify_sports(question)
    if sp:
        return sp

    return ClassifiedMarket(subcategory="other", confidence="low")


# ---------------------------------------------------------------------------
# Whitelist helpers
# ---------------------------------------------------------------------------

DEFAULT_SAFE_SUBCATEGORIES: set[str] = {
    "crypto_price",
    "team_moneyline",
}


def is_safe(
    cm: ClassifiedMarket,
    allowed: Iterable[str] = DEFAULT_SAFE_SUBCATEGORIES,
    min_confidence: str = "high",
) -> bool:
    confidence_rank = {"low": 0, "medium": 1, "high": 2}
    if cm.subcategory not in set(allowed):
        return False
    return confidence_rank.get(cm.confidence, 0) >= confidence_rank[min_confidence]
