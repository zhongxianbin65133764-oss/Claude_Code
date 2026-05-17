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

### 3.0 macOS one-shot launcher (easiest path)

```bash
./scripts/mac/mac_start.sh
```

Auto-detects Docker; falls back to native Python with virtualenv +
`caffeinate`. Includes a network reachability check so you know
right away if Polymarket is geo-blocking your IP.

After the first launch, you can also register the services as
**LaunchAgents** so they restart at login / auto-restart on crash:

```bash
./scripts/mac/install_launchd.sh    # install
./scripts/mac/uninstall_launchd.sh  # remove
```

The non-Mac paths below also work; this is just sugar.

### 3.0.1 Network reachability check

Before running anything, confirm your machine can actually reach
Polymarket (it geo-blocks several jurisdictions):

```bash
python3 scripts/check_network.py
```

Tests Gamma + CLOB + Coinbase oracle + Polygon RPC and tells you
exactly which paths are blocked. Uses Python stdlib only so you
can run it before `pip install`.

### 3.0.2 Run with Docker (works on any OS)

```bash
cp .env.example .env       # confirm DRY_RUN=true
mkdir -p data
docker-compose up -d        # bot + dashboard, restart-on-failure
open http://localhost:5000
```

The compose file ships two services — `bot` runs the main loop,
`dashboard` exposes the web UI on port 5000. Both share `./data` so
`positions.db` survives container restarts. Memory limits (512MB bot,
256MB dashboard) prevent a runaway process from taking down the host.

To see logs:
```bash
docker-compose logs -f bot
```

To stop:
```bash
docker-compose down
```

### 3.1 Install (no Docker)

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

In **dry-run mode** the bot runs the full realism layer: detect an
opportunity, wait 60s, re-fetch the book, then decide whether the trade
would actually have happened. You'll see something like:

```
2026-05-17 ... | scan: 47 markets seen, 31 safety-rejected, 12 book-rejected, 4 opportunities
2026-05-17 ... | DETECTED Will the Lakers win Game 3? | YES @ 0.955 | depth $200 | queued for verification in 60s
2026-05-17 ... | MISSED   Will Chiefs beat Bengals?  | ask drifted 0.940 -> 0.965, fill rate dropping
2026-05-17 ... | FILLED   Will the Lakers win Game 3? | ideal $25.00 @ 0.960 -> real $17.60 @ 0.955 (fill_ratio=70%;gas=$0.10)
2026-05-17 ... | status: exposure $17.60 / $200.00 | 2 in verification queue
```

Let it run for **at least a week** in dry-run, then look at the dashboard
to evaluate hit rate, realistic PnL, and which markets it would have caught.

### 3.4 Run tests

```bash
python -m pytest tests/ -v
```

### 3.5 Live smoke test (one-shot, read-only)

Before committing to a multi-day run, do a 30-second sanity check
against the real APIs:

```bash
python scripts/live_smoke_test.py --limit 30
```

For each candidate market it shows: classifier verdict, oracle
verdict for crypto, per-side book ask + accept-or-reject reason,
and which sides would queue. Ends with rejection-reason breakdown
and subcategory distribution. **Does not write to DB, does not
place orders.**

Flags: `--no-color`, `--no-oracle`, `--no-book` (faster, less info).

### 3.6 Dashboard

In a separate terminal:

```bash
python -m polymarket_arb.dashboard          # http://127.0.0.1:5000
# or bind to all interfaces / different port:
python -m polymarket_arb.dashboard --host 0.0.0.0 --port 8080
```

The dashboard reads the same `positions.db` the bot writes, so you can
run both side by side. It shows:

- **大字盈亏(实盘预估)** + 对比理想盈亏(完美执行下应得)
- **"演练 vs 实盘的差距"** 小节:发现机会数 / 实际抢到数 / 资金捕获率 / 平均价格漂移
- 盈亏走势图(实线 = 实盘预估,虚线 = 理想)
- 正在持有 + 已经结清两张表(结清表分"理想盈亏" / "实盘盈亏"两列)
- 折叠帮助:"实盘和演练为什么有差距?"

To preview without running the bot, seed synthetic data:

```bash
python scripts/seed_demo_data.py            # writes 3 open + 8 closed
python -m polymarket_arb.dashboard
```

---

## 4. 演练 vs 实盘的差距(必读)

**最容易让自动化策略翻车的事:演练赚钱、实盘亏钱。**
原因是演练默认"看到啥都能买到、买到就 100% 成交、永远不掉单",而实盘:

| 差距来源 | 演练假设 | 实盘真相 | 本 bot 怎么处理 |
|---|---|---|---|
| **抢单延迟** | 即时成交 | 30-90 秒延迟,别的 bot 可能先吃 | 检测后等 `VERIFICATION_DELAY_SECONDS`(默认 60s)再复查盘口 |
| **盘口失效** | 看到的盘口都能吃 | 部分挂单是诱饵 / 已被撤 | 复查时如果 ask 已涨过限价 → 标记 MISSED |
| **部分成交** | 全部按限价成交 | 平均只成交 50-80% | `EXPECTED_FILL_RATIO` (默认 70%) 应用三角分布 |
| **gas + 滑点** | 0 成本 | 每笔 $0.05-0.20 | `ESTIMATED_GAS_COST_USD`(默认 $0.10) 直接扣 |
| **逆向选择** | 卖家都"老实" | 愿意 0.96 卖的可能知道你不知道 | `ADVERSE_FILL_RATE`(默认 3%) 这些成交直接归零 |
| **UMA 改判** | Gamma 说啥就是啥 | 偶尔会被改判 | `UMA_DISPUTE_RATE`(默认 2%) 翻转结算结果 |

实战意义:
- 看板上**"实盘预估"**列就是把这些都算进去后的预估,**比"理想"更接近你真去实盘的结果**
- 如果实盘预估也是绿的,策略真有 edge;如果实盘预估是红的而理想是绿的,只是理论收益,不能扛真实摩擦
- **跑一周后用真实数据校准参数**:看 verifications 表里的 `fill_rate` 是不是真的 70%,如果实际只有 50%,就改 `EXPECTED_FILL_RATIO=0.5`

```sql
-- 看实际抢单成功率
SELECT
  COUNT(*) AS detected,
  SUM(would_have_filled) AS filled,
  CAST(SUM(would_have_filled) AS FLOAT) / COUNT(*) AS fill_rate,
  AVG(CASE WHEN would_have_filled
           THEN verified_ask - detected_ask END) AS avg_drift_cents
FROM verifications;
```

---

## 5. Going live (don't rush this)

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

## 6. Known failure modes (read before going live)

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

## 7. Optimization tools

Two tools to help you iterate on the strategy without losing money:

### 7.1 Weekly review (diagnostic)

```bash
python scripts/weekly_review.py
```

Reads `positions.db` and prints a structured report:
- Activity summary (detections, fills, settlements)
- Loss decomposition — splits the ideal-vs-realistic gap into
  *partial fills + gas*, *adverse selection*, and *UMA disputes*
- Performance by subcategory (which market types win/lose)
- Performance by entry-price bucket (find your sweet spot)
- Empirical vs configured friction (auto-calibrates the model)
- Top 3 prioritized recommendations

Run this **weekly** to find out what to optimize next. The script
refuses to give recommendations until you have ≥10 closed positions,
because anything less is noise.

### 7.2 S-tier optimizations (enabled by default)

Two changes proven to reduce dispute and adverse-fill rates the most:

**A. Sub-category whitelist** (`USE_SUBCATEGORY_FILTER=true`)
Beyond the broad category check, market questions must match a
high-confidence safe pattern: `crypto_price` (e.g., "Will BTC close
above $X on Y?") or `team_moneyline` (e.g., "Will the Lakers beat
the Celtics?"). Excludes player props, sports event existence, and
anything with subjective resolution language. Implementation in
`polymarket_arb/question_classifier.py`.

**B. Independent crypto oracle** (`USE_ORACLE=true`)
For `crypto_price` markets we don't need to trust UMA — we can look
up the close price on Coinbase ourselves. If the oracle confirms the
winning side, we:
- Trade only that side (skip the losing one even if it looks
  underpriced)
- Pay up to `ORACLE_VERIFIED_MAX_BUY_PRICE` (default $0.985 instead
  of $0.96)

This essentially eliminates UMA dispute risk on crypto markets.
Implementation in `polymarket_arb/price_oracle.py`.

### 7.3 Fine-grained classifier (`polymarket_arb/question_classifier.py`)

Beyond the two whitelisted subcategories, the classifier also tags:
- `weather` — temperature / rainfall / earthquake markets (rejected)
- `politics` — primaries / nominations / elections (rejected)
- `speech_event` — "Will X say Y" / "Will X tweet Z" (rejected,
  highly subjective)
- `event_moneyline` — generic "Will X win Y" pattern, covers
  non-US-league sports and esports tournaments. **NOT in default
  whitelist** because dispute rates are unknown. Opt in by editing
  `DEFAULT_SAFE_SUBCATEGORIES` in `question_classifier.py` once you've
  verified the dispute rate on a sample of these markets in your
  dry-run data.

### 7.4 Adaptive scan interval

When `ADAPTIVE_SCAN_ENABLED=true`, the bot scans every
`HIGH_ACTIVITY_INTERVAL_SECONDS` (default 30s) during the UTC hours
in `HIGH_ACTIVITY_HOURS_UTC` (default `0,1,2,18,19,20,21,22,23` —
crypto daily-close + US sports primetime) and every
`LOW_ACTIVITY_INTERVAL_SECONDS` (default 300s) otherwise. This is a
~70% reduction in API + network cost during dead hours while keeping
detection latency low when the action happens.

### 7.5 Tuning thresholds

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

## 8. What this bot is NOT

- **Not a prediction strategy.** It does not try to be smarter than the market. It rides the market's own consensus during the oracle delay window.
- **Not high-frequency.** 90-second poll loop. If you need ms-latency, this is the wrong architecture.
- **Not a money printer.** Realistic expectation is 1-4% per trade, 5-30 trades/month, with occasional 100% losses on UMA disputes. Net expected value is positive if filters are honest; the variance is real.
- **Not audited.** Use small size. Read every file before going live.

---

## 9. License

Choose your own. Provided as-is, no warranty, do your own due diligence.
