# Polymarket Resolution-Time Arbitrage Bot

A small, opinionated automated trading bot that targets **one** specific
inefficiency on Polymarket: markets whose underlying event has already
happened, but whose UMA oracle has not yet resolved, often trade the
winning side at $0.95-0.97 instead of $1.00. Buying at that price and
waiting 1-7 days for resolution yields a small near-risk-free return.

This is **副策略 A (resolution-time arbitrage)** from the strategy design
discussion. Single-leg, no leg risk, simplest possible thing that
might actually work.

> **Honest expectation**: at retail size ($200-$2000 exposure) this
> strategy clears single-digit % per turnover on the trades it finds,
> with perhaps 5-30 fills per month. Annualised returns 15-40% are
> plausible **assuming** no UMA dispute hits you and Polymarket doesn't
> geo-block your wallet. The bot ships in dry-run mode by default.

---

## 1. How the strategy works

```
                +----------------------+
                |  Gamma /markets API  |
                |  (no auth)           |
                +----------+-----------+
                           |
                  end_date in [now-10d, now-2h]
                  closed=false, accepting_orders=true
                           |
                           v
                +----------------------+
                |  Safety filters      |
                |  - safe category     |
                |  - no blacklisted    |
                |    keyword           |
                +----------+-----------+
                           |
                           v
                +----------------------+
                |  CLOB /book per side |
                |  best ask in         |
                |  [0.88, 0.96]?       |
                |  depth >= $50?       |
                |  spread <= 0.20?     |
                +----------+-----------+
                           |
                           v
                +----------------------+
                |  Place limit buy at  |
                |  max_buy_price       |
                |  (DRY_RUN: log only) |
                +----------+-----------+
                           |
                           v
                +----------------------+
                |  Record position     |
                |  in SQLite           |
                +----------+-----------+
                           |
                ... 1-7 days later ...
                           |
                           v
                +----------------------+
                |  Settlement sweep    |
                |  detects resolved    |
                |  market, books PnL   |
                +----------------------+
```

Every loop iteration (default 90s) does:
1. Sweep open positions for newly resolved markets.
2. Scan Gamma for fresh candidates.
3. For each, fetch both YES and NO orderbooks and apply safety filters.
4. Place limit buys on the side whose ask is in the target window.

---

## 2. Files

```
polymarket_arb/
├── config.py         # All thresholds. Read this first.
├── gamma_client.py   # Market discovery (no auth).
├── orderbook.py      # CLOB orderbook reader + fillable cost math.
├── safety.py         # Category/keyword/book sanity filters.
├── strategy.py       # Opportunity detection + sizing.
├── executor.py       # py-clob-client wrapper; DRY_RUN short-circuits.
├── position_store.py # SQLite positions + trade log.
├── settler.py        # Detects UMA-resolved markets, books PnL.
└── main.py           # Loop.

tests/                # Offline unit tests for safety/orderbook math.
```

---

## 3. Setup

### 3.1 Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3.2 Configure

```bash
cp .env.example .env
# Open .env and at minimum confirm DRY_RUN=true for the first run.
```

For **dry-run** (the default) you do **not** need:
- a Polygon wallet
- USDC
- Polymarket API keys

The bot will discover markets, fetch real orderbooks, and log the trades
it *would* place. This is how you validate the strategy is finding real
opportunities before risking money.

### 3.3 Run

```bash
python -m polymarket_arb.main
```

You'll see something like:

```
2026-05-17 ... INFO arb_bot | Polymarket Resolution-Time Arb Bot starting in DRY-RUN
2026-05-17 ... INFO polymarket_arb.strategy | scan: 47 markets seen, 31 safety-rejected, 12 book-rejected, 4 opportunities
2026-05-17 ... INFO polymarket_arb.strategy | OPPORTUNITY: Will the Lakers win Game 3? | YES @ 0.955 | fill $25.00 | 0xabc...
2026-05-17 ... INFO polymarket_arb.executor | [DRY] would BUY 26.18 tokens of 12345... at <=0.960 (max $25.00)
2026-05-17 ... INFO arb_bot | open exposure: $25.00 / $200.00
```

Let it run for **at least a week** in dry-run, then look at `positions.db`
to evaluate hit rate and which markets it would have caught.

### 3.4 Run tests

```bash
python -m pytest tests/ -v
```

### 3.5 Dashboard

In a separate terminal:

```bash
python -m polymarket_arb.dashboard          # http://127.0.0.1:5000
# or bind to all interfaces / different port:
python -m polymarket_arb.dashboard --host 0.0.0.0 --port 8080
```

The dashboard reads the same `positions.db` the bot writes, so you can
run both side by side. It shows:

- summary cards (open count, exposure, closed count, realized PnL, win rate, avg return)
- cumulative realized PnL line chart
- open positions table (with hours-since-opened)
- closed positions table (last 30, with PnL, return %, days held)
- recent trades log (last 50, BUY + SETTLE actions)

To preview without running the bot, seed synthetic data:

```bash
python scripts/seed_demo_data.py            # writes 3 open + 8 closed
python -m polymarket_arb.dashboard
```

---

## 4. Going live (don't rush this)

Only after a week of dry-run output looks sane:

1. Create a dedicated Polygon wallet (Metamask, hardware wallet). **Not your main wallet.**
2. Fund it with USDC on Polygon **only what you can afford to lose** (start with $100-200).
3. Sign up at polymarket.com and create an API key.
4. Fill all `POLYMARKET_*` and `WALLET_PRIVATE_KEY` fields in `.env`.
5. Set `DRY_RUN=false`.
6. Run. The bot will print a 10-second warning before starting.

> **Geographic restriction**: Polymarket geo-blocks several jurisdictions
> (US, UK, France, Singapore, etc.). Trading from a blocked region is
> against ToS and your wallet may be banned. The author of this bot does
> not condone ToS violation; check eligibility before going live.

---

## 5. Known failure modes (read before going live)

| Failure | Probability | Mitigation in code |
|---|---|---|
| UMA disputes the resolution and reverses outcome | Low (~1% of trades) but tail-heavy | Risky categories blacklisted; safe categories require mechanically-verifiable outcomes |
| Market is past end_date but UMA hasn't even started | Medium | `max_market_age_days` filter |
| Thin book: ask shows 0.95 but only $5 of depth | High | `min_book_depth_usd` filter + walk-the-book cost calc |
| You buy YES at 0.95, then 5 minutes later news reveals NO won | Low for sports/crypto, high for politics | Category whitelist excludes politics by default |
| Polymarket geo-blocks your IP/wallet | Depends on jurisdiction | Out of scope - your problem |
| Wallet private key leaks | User error | Dedicated bot wallet, small balance, never commit `.env` |
| API key suspended for ToS violation | Low if you follow rules | Out of scope |

---

## 6. Tuning

Once you have 30+ dry-run observations, look at `positions.db`:

```sql
-- which markets would have been hit, at what price
SELECT question, side, avg_price, cost_usd, opened_at
FROM positions ORDER BY opened_at DESC LIMIT 30;
```

Things to consider tightening or loosening:
- `max_buy_price`: higher catches more opportunities but lower per-trade edge.
- `min_market_age_hours`: lower catches more, but more risk of false reads.
- `min_book_depth_usd`: lower catches more, but more slippage on real fills.
- `SAFE_CATEGORIES` in `config.py`: add categories once you're confident they're mechanical.

---

## 7. What this bot is NOT

- **Not a prediction strategy.** It does not try to be smarter than the market. It rides the market's own consensus during the oracle delay window.
- **Not high-frequency.** 90-second poll loop. If you need ms-latency, this is the wrong architecture.
- **Not a money printer.** Realistic expectation is 1-4% per trade, 5-30 trades/month, with occasional 100% losses on UMA disputes. Net expected value is positive if filters are honest; the variance is real.
- **Not audited.** Use small size. Read every file before going live.

---

## 8. License

Choose your own. Provided as-is, no warranty, do your own due diligence.
