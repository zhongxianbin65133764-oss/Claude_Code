"""Minimal Flask dashboard for the arb bot.

Reads positions.db (the same SQLite the bot writes) and renders one
page with summary stats, open positions, closed positions, recent
trades, and a cumulative PnL chart.

Run:
    python -m polymarket_arb.dashboard
Then open http://127.0.0.1:5000
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone

from flask import Flask, jsonify, render_template_string

from .config import CONFIG
from .position_store import PositionStore


def _hours_since(iso: str | None) -> float | None:
    if not iso:
        return None
    try:
        ts = datetime.fromisoformat(iso)
    except ValueError:
        return None
    return (datetime.now(timezone.utc) - ts).total_seconds() / 3600.0


PAGE = """
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>Polymarket Arb Bot</title>
<style>
  :root {
    --bg: #0f1419; --panel: #1a2129; --border: #2a333d;
    --fg: #e6edf3; --muted: #8b949e;
    --good: #3fb950; --bad: #f85149; --warn: #d29922;
    --accent: #58a6ff;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; padding: 24px;
    font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, monospace;
    background: var(--bg); color: var(--fg);
  }
  h1 { margin: 0 0 4px 0; font-size: 22px; }
  .sub { color: var(--muted); font-size: 13px; margin-bottom: 24px; }
  .mode-live { color: var(--bad); font-weight: bold; }
  .mode-dry { color: var(--warn); }
  .grid {
    display: grid; gap: 16px;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    margin-bottom: 24px;
  }
  .card {
    background: var(--panel); border: 1px solid var(--border);
    border-radius: 8px; padding: 16px;
  }
  .card .label { color: var(--muted); font-size: 12px;
                 text-transform: uppercase; letter-spacing: .5px; }
  .card .value { font-size: 24px; font-weight: 600; margin-top: 6px; }
  .pos { color: var(--good); }
  .neg { color: var(--bad); }
  .section { margin-top: 28px; }
  .section h2 { font-size: 16px; margin: 0 0 12px 0; color: var(--muted);
                text-transform: uppercase; letter-spacing: .5px; }
  table { width: 100%; border-collapse: collapse; font-size: 13px;
          background: var(--panel); border: 1px solid var(--border);
          border-radius: 8px; overflow: hidden; }
  th, td { padding: 8px 12px; text-align: left;
           border-bottom: 1px solid var(--border); }
  th { color: var(--muted); font-weight: 500; font-size: 11px;
       text-transform: uppercase; letter-spacing: .5px;
       background: rgba(255,255,255,0.02); }
  tr:last-child td { border-bottom: none; }
  td.num { text-align: right; font-variant-numeric: tabular-nums; }
  .pill { display: inline-block; padding: 2px 8px; border-radius: 10px;
          font-size: 11px; font-weight: 500; }
  .pill-yes { background: rgba(63,185,80,0.15); color: var(--good); }
  .pill-no  { background: rgba(248,81,73,0.15); color: var(--bad); }
  .pill-buy { background: rgba(88,166,255,0.15); color: var(--accent); }
  .pill-settle { background: rgba(210,153,34,0.15); color: var(--warn); }
  .pill-dry { background: rgba(139,148,158,0.2); color: var(--muted); }
  .q { max-width: 480px; white-space: nowrap; overflow: hidden;
       text-overflow: ellipsis; display: inline-block; vertical-align: middle; }
  .empty { color: var(--muted); padding: 24px; text-align: center; }
  #pnl-chart { width: 100%; height: 280px; background: var(--panel);
               border: 1px solid var(--border); border-radius: 8px;
               padding: 12px; }
  .footer { color: var(--muted); font-size: 11px; margin-top: 32px;
            text-align: center; }
</style>
</head>
<body>

<h1>Polymarket Resolution-Time Arb Bot</h1>
<div class="sub">
  mode: <span class="{{ 'mode-live' if not dry_run else 'mode-dry' }}">
    {{ '*** LIVE ***' if not dry_run else 'DRY-RUN' }}
  </span>
  &nbsp;·&nbsp; refreshed {{ refreshed_at }}
  &nbsp;·&nbsp; <a href="javascript:location.reload()" style="color: var(--accent)">reload</a>
</div>

<div class="grid">
  <div class="card">
    <div class="label">Open positions</div>
    <div class="value">{{ s.open_count }}</div>
  </div>
  <div class="card">
    <div class="label">Open exposure</div>
    <div class="value">${{ '%.2f' % s.open_exposure }}</div>
  </div>
  <div class="card">
    <div class="label">Closed trades</div>
    <div class="value">{{ s.closed_count }}</div>
  </div>
  <div class="card">
    <div class="label">Realized PnL</div>
    <div class="value {{ 'pos' if s.realized_pnl >= 0 else 'neg' }}">
      ${{ '%+.2f' % s.realized_pnl }}
    </div>
  </div>
  <div class="card">
    <div class="label">Win rate</div>
    <div class="value">{{ '%.0f' % (s.win_rate * 100) }}%</div>
  </div>
  <div class="card">
    <div class="label">Avg return / trade</div>
    <div class="value {{ 'pos' if s.avg_return_pct >= 0 else 'neg' }}">
      {{ '%+.2f' % s.avg_return_pct }}%
    </div>
  </div>
</div>

<div class="section">
  <h2>Cumulative realized PnL</h2>
  <canvas id="pnl-chart"></canvas>
</div>

<div class="section">
  <h2>Open positions ({{ open_positions|length }})</h2>
  {% if open_positions %}
  <table>
    <thead>
      <tr>
        <th>Question</th><th>Side</th>
        <th class="num">Tokens</th><th class="num">Avg px</th>
        <th class="num">Cost</th><th class="num">Hours open</th>
      </tr>
    </thead>
    <tbody>
    {% for p in open_positions %}
      <tr>
        <td><span class="q" title="{{ p.question }}">{{ p.question }}</span></td>
        <td><span class="pill pill-{{ 'yes' if p.side == 'YES' else 'no' }}">{{ p.side }}</span></td>
        <td class="num">{{ '%.2f' % p.tokens }}</td>
        <td class="num">{{ '%.3f' % p.avg_price }}</td>
        <td class="num">${{ '%.2f' % p.cost_usd }}</td>
        <td class="num">{{ '%.1f' % p.hours_open if p.hours_open is not none else '-' }}</td>
      </tr>
    {% endfor %}
    </tbody>
  </table>
  {% else %}
  <div class="card empty">No open positions.</div>
  {% endif %}
</div>

<div class="section">
  <h2>Closed positions ({{ s.closed_count }}, last 30)</h2>
  {% if closed_positions %}
  <table>
    <thead>
      <tr>
        <th>Question</th><th>Side</th>
        <th class="num">Cost</th><th class="num">Payout</th>
        <th class="num">PnL</th><th class="num">Return</th>
        <th class="num">Days held</th>
      </tr>
    </thead>
    <tbody>
    {% for p in closed_positions %}
      <tr>
        <td><span class="q" title="{{ p.question }}">{{ p.question }}</span></td>
        <td><span class="pill pill-{{ 'yes' if p.side == 'YES' else 'no' }}">{{ p.side }}</span></td>
        <td class="num">${{ '%.2f' % p.cost_usd }}</td>
        <td class="num">${{ '%.2f' % (p.payout_usd or 0) }}</td>
        <td class="num {{ 'pos' if p.pnl >= 0 else 'neg' }}">${{ '%+.2f' % p.pnl }}</td>
        <td class="num {{ 'pos' if p.ret_pct >= 0 else 'neg' }}">{{ '%+.1f' % p.ret_pct }}%</td>
        <td class="num">{{ '%.1f' % p.days_held if p.days_held is not none else '-' }}</td>
      </tr>
    {% endfor %}
    </tbody>
  </table>
  {% else %}
  <div class="card empty">No closed positions yet.</div>
  {% endif %}
</div>

<div class="section">
  <h2>Recent trades (last 50)</h2>
  {% if trades %}
  <table>
    <thead>
      <tr>
        <th>When</th><th>Action</th><th>Side</th>
        <th class="num">Tokens</th><th class="num">Price</th>
        <th class="num">USD</th><th>Mode</th>
      </tr>
    </thead>
    <tbody>
    {% for t in trades %}
      <tr>
        <td>{{ t.ts[:19].replace('T', ' ') }}</td>
        <td><span class="pill pill-{{ 'buy' if t.action == 'BUY' else 'settle' }}">{{ t.action }}</span></td>
        <td><span class="pill pill-{{ 'yes' if t.side == 'YES' else 'no' }}">{{ t.side }}</span></td>
        <td class="num">{{ '%.2f' % t.tokens }}</td>
        <td class="num">{{ '%.3f' % t.price }}</td>
        <td class="num">${{ '%.2f' % t.usd }}</td>
        <td>
          {% if t.dry_run %}<span class="pill pill-dry">DRY</span>{% else %}<span class="pill pill-buy">LIVE</span>{% endif %}
        </td>
      </tr>
    {% endfor %}
    </tbody>
  </table>
  {% else %}
  <div class="card empty">No trades yet.</div>
  {% endif %}
</div>

<div class="footer">
  positions.db: {{ db_path }} &nbsp;·&nbsp;
  thresholds: buy &lt;= ${{ '%.2f' % cfg.max_buy_price }},
  position &lt;= ${{ '%.0f' % cfg.max_position_size_usd }},
  total &lt;= ${{ '%.0f' % cfg.max_total_exposure_usd }}
</div>

<script>
(async function() {
  const r = await fetch('/api/pnl-series');
  const series = await r.json();
  const canvas = document.getElementById('pnl-chart');
  const ctx = canvas.getContext('2d');
  // size canvas to its displayed pixel size
  const rect = canvas.getBoundingClientRect();
  canvas.width = rect.width * window.devicePixelRatio;
  canvas.height = rect.height * window.devicePixelRatio;
  ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
  const W = rect.width, H = rect.height;
  ctx.clearRect(0, 0, W, H);

  if (!series.length) {
    ctx.fillStyle = '#8b949e';
    ctx.font = '13px monospace';
    ctx.textAlign = 'center';
    ctx.fillText('No closed positions yet.', W/2, H/2);
    return;
  }

  const pad = {l: 50, r: 16, t: 12, b: 28};
  const xs = series.map((_, i) => i);
  const ys = series.map(p => p[1]);
  const yMin = Math.min(0, ...ys);
  const yMax = Math.max(0, ...ys);
  const yPad = (yMax - yMin) * 0.1 || 1;
  const y0 = yMin - yPad, y1 = yMax + yPad;
  const xScale = i => pad.l + (i / Math.max(1, xs.length - 1)) * (W - pad.l - pad.r);
  const yScale = v => H - pad.b - ((v - y0) / (y1 - y0)) * (H - pad.t - pad.b);

  // grid + axis
  ctx.strokeStyle = '#2a333d'; ctx.lineWidth = 1;
  ctx.fillStyle = '#8b949e'; ctx.font = '11px monospace';
  ctx.textAlign = 'right'; ctx.textBaseline = 'middle';
  for (let i = 0; i <= 4; i++) {
    const v = y0 + (y1 - y0) * (i / 4);
    const y = yScale(v);
    ctx.beginPath(); ctx.moveTo(pad.l, y); ctx.lineTo(W - pad.r, y); ctx.stroke();
    ctx.fillText('$' + v.toFixed(2), pad.l - 6, y);
  }
  // zero line emphasized
  const zeroY = yScale(0);
  ctx.strokeStyle = '#3a4754'; ctx.lineWidth = 1;
  ctx.beginPath(); ctx.moveTo(pad.l, zeroY); ctx.lineTo(W - pad.r, zeroY); ctx.stroke();

  // line
  const lastY = ys[ys.length - 1];
  ctx.strokeStyle = lastY >= 0 ? '#3fb950' : '#f85149';
  ctx.lineWidth = 2;
  ctx.beginPath();
  series.forEach((p, i) => {
    const x = xScale(i), y = yScale(p[1]);
    if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
  });
  ctx.stroke();

  // last value label
  ctx.fillStyle = lastY >= 0 ? '#3fb950' : '#f85149';
  ctx.textAlign = 'left'; ctx.textBaseline = 'middle';
  ctx.fillText('$' + lastY.toFixed(2),
               xScale(series.length - 1) + 6, yScale(lastY));
})();
</script>

</body>
</html>
"""


def create_app(store: PositionStore, config) -> Flask:
    app = Flask(__name__)

    @app.route("/")
    def index():
        s = store.summary()
        opens = store.open_positions()
        closes = store.closed_positions(limit=30)
        trades = store.recent_trades(limit=50)

        opens_view = [
            {
                "question": p.question,
                "side": p.side,
                "tokens": p.tokens,
                "avg_price": p.avg_price,
                "cost_usd": p.cost_usd,
                "hours_open": _hours_since(p.opened_at.isoformat()),
            }
            for p in opens
        ]
        closes_view = []
        for p in closes:
            payout = p.payout_usd or 0.0
            pnl = payout - p.cost_usd
            ret = (pnl / p.cost_usd * 100) if p.cost_usd else 0.0
            days = None
            if p.closed_at and p.opened_at:
                days = (p.closed_at - p.opened_at).total_seconds() / 86400.0
            closes_view.append({
                "question": p.question,
                "side": p.side,
                "cost_usd": p.cost_usd,
                "payout_usd": p.payout_usd,
                "pnl": pnl,
                "ret_pct": ret,
                "days_held": days,
            })

        return render_template_string(
            PAGE,
            s=s,
            open_positions=opens_view,
            closed_positions=closes_view,
            trades=trades,
            dry_run=config.dry_run,
            cfg=config,
            db_path=config.db_path,
            refreshed_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

    @app.route("/api/pnl-series")
    def api_pnl_series():
        return jsonify(store.cumulative_pnl_series())

    @app.route("/api/summary")
    def api_summary():
        return jsonify(store.summary())

    return app


def main() -> int:
    parser = argparse.ArgumentParser(description="Polymarket arb bot dashboard")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    store = PositionStore(CONFIG.db_path)
    app = create_app(store, CONFIG)
    print(f"\n  Dashboard:  http://{args.host}:{args.port}\n"
          f"  DB path:    {CONFIG.db_path}\n"
          f"  Mode:       {'LIVE' if not CONFIG.dry_run else 'DRY-RUN'}\n")
    app.run(host=args.host, port=args.port, debug=args.debug)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
