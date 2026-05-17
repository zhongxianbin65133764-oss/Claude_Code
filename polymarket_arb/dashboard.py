"""极简中文看板。

设计原则:
  1. 一眼看到最重要的数:目前赚了/亏了多少。
  2. 用大白话标题:"正在持有"、"已经结清"、"押的方向"。
  3. 每一块都附一句"这是什么"的提示。
  4. 不展示给非技术用户看的细节(token id、condition id、trades log)。

运行:
    python -m polymarket_arb.dashboard
浏览器打开 http://127.0.0.1:5000
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone

from flask import Flask, jsonify, render_template_string

from .config import CONFIG
from .position_store import PositionStore


def _humanize_duration(hours: float | None) -> str:
    if hours is None:
        return "-"
    if hours < 1:
        return f"{int(hours * 60)} 分钟"
    if hours < 24:
        return f"{hours:.1f} 小时"
    return f"{hours / 24:.1f} 天"


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
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<title>Polymarket 套利助手</title>
<style>
  :root {
    --bg: #f6f7f9; --panel: #ffffff; --border: #e3e6ea;
    --fg: #1f2328; --muted: #6e7681; --soft: #f0f2f5;
    --good: #1f883d; --bad: #cf222e; --warn: #9a6700;
    --accent: #0969da;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; padding: 24px 16px;
    font-family: -apple-system, BlinkMacSystemFont, "PingFang SC",
                 "Microsoft YaHei", "Segoe UI", sans-serif;
    background: var(--bg); color: var(--fg);
    max-width: 960px; margin-left: auto; margin-right: auto;
  }
  h1 { margin: 0 0 8px 0; font-size: 22px; font-weight: 600; }
  .sub { color: var(--muted); font-size: 13px; margin-bottom: 28px; }
  .sub a { color: var(--accent); text-decoration: none; }
  .sub a:hover { text-decoration: underline; }

  .badge {
    display: inline-block; padding: 2px 10px; border-radius: 12px;
    font-size: 12px; font-weight: 500;
  }
  .badge-dry { background: #fff8c5; color: var(--warn); }
  .badge-live { background: #ffebe9; color: var(--bad); }

  .hero {
    background: var(--panel); border: 1px solid var(--border);
    border-radius: 12px; padding: 24px; margin-bottom: 16px;
    text-align: center;
  }
  .hero-label { color: var(--muted); font-size: 13px; }
  .hero-value {
    font-size: 44px; font-weight: 700; margin: 6px 0 4px;
    font-variant-numeric: tabular-nums;
  }
  .hero-sub { color: var(--muted); font-size: 13px; }
  .pos { color: var(--good); }
  .neg { color: var(--bad); }
  .neutral { color: var(--muted); }

  .stats-row {
    display: grid; gap: 12px;
    grid-template-columns: repeat(3, 1fr);
    margin-bottom: 28px;
  }
  @media (max-width: 600px) {
    .stats-row { grid-template-columns: 1fr; }
  }
  .stat {
    background: var(--panel); border: 1px solid var(--border);
    border-radius: 12px; padding: 14px 16px;
  }
  .stat-label { color: var(--muted); font-size: 12px; }
  .stat-value {
    font-size: 22px; font-weight: 600; margin-top: 4px;
    font-variant-numeric: tabular-nums;
  }

  section { margin-top: 28px; }
  section h2 {
    font-size: 15px; font-weight: 600; margin: 0 0 4px 0;
  }
  .hint {
    color: var(--muted); font-size: 12px; margin-bottom: 10px;
  }

  table {
    width: 100%; border-collapse: collapse; font-size: 13px;
    background: var(--panel); border: 1px solid var(--border);
    border-radius: 10px; overflow: hidden;
  }
  th, td {
    padding: 10px 12px; text-align: left;
    border-bottom: 1px solid var(--border);
  }
  th {
    color: var(--muted); font-weight: 500; font-size: 12px;
    background: var(--soft);
  }
  tr:last-child td { border-bottom: none; }
  td.num { text-align: right; font-variant-numeric: tabular-nums; }

  .pill {
    display: inline-block; padding: 2px 8px; border-radius: 10px;
    font-size: 11px; font-weight: 500;
  }
  .pill-yes { background: #dafbe1; color: var(--good); }
  .pill-no  { background: #ffebe9; color: var(--bad); }

  .q {
    max-width: 360px; white-space: nowrap; overflow: hidden;
    text-overflow: ellipsis; display: inline-block; vertical-align: middle;
  }
  .empty {
    background: var(--panel); border: 1px solid var(--border);
    border-radius: 10px; padding: 32px; text-align: center;
    color: var(--muted); font-size: 13px;
  }

  #pnl-chart {
    width: 100%; height: 240px; background: var(--panel);
    border: 1px solid var(--border); border-radius: 10px;
    padding: 12px;
  }

  details {
    background: var(--panel); border: 1px solid var(--border);
    border-radius: 10px; padding: 14px 16px; margin-top: 28px;
  }
  details summary {
    cursor: pointer; font-weight: 500; font-size: 14px;
    color: var(--accent);
  }
  details p { color: var(--fg); font-size: 13px; line-height: 1.7;
              margin: 10px 0; }
  details strong { color: var(--fg); }
</style>
</head>
<body>

<h1>Polymarket 套利助手</h1>
<div class="sub">
  <span class="badge {{ 'badge-live' if not dry_run else 'badge-dry' }}">
    {{ '真实交易中' if not dry_run else '演练模式(不花钱)' }}
  </span>
  &nbsp;·&nbsp; 更新于 {{ refreshed_at }}
  &nbsp;·&nbsp; <a href="javascript:location.reload()">刷新</a>
</div>

<!-- ============ 主要数字 ============ -->
<div class="hero">
  <div class="hero-label">已结算盈亏</div>
  <div class="hero-value {{ 'pos' if s.realized_pnl > 0 else ('neg' if s.realized_pnl < 0 else 'neutral') }}">
    {% if s.closed_count == 0 %}
      —
    {% else %}
      {{ '+' if s.realized_pnl >= 0 else '' }}${{ '%.2f' % s.realized_pnl }}
    {% endif %}
  </div>
  <div class="hero-sub">
    {% if s.closed_count == 0 %}
      还没有交易结清,继续等
    {% else %}
      共 {{ s.closed_count }} 笔交易已结清
      &nbsp;·&nbsp; 胜率 {{ '%.0f' % (s.win_rate * 100) }}%
      &nbsp;·&nbsp; 单笔平均
      <span class="{{ 'pos' if s.avg_return_pct >= 0 else 'neg' }}">
        {{ '+' if s.avg_return_pct >= 0 else '' }}{{ '%.1f' % s.avg_return_pct }}%
      </span>
    {% endif %}
  </div>
</div>

<!-- ============ 三个小数字 ============ -->
<div class="stats-row">
  <div class="stat">
    <div class="stat-label">正在持有</div>
    <div class="stat-value">{{ s.open_count }} 笔</div>
  </div>
  <div class="stat">
    <div class="stat-label">还在场上的钱</div>
    <div class="stat-value">${{ '%.2f' % s.open_exposure }}</div>
  </div>
  <div class="stat">
    <div class="stat-label">总成本(已结清)</div>
    <div class="stat-value">${{ '%.2f' % s.realized_cost }}</div>
  </div>
</div>

<!-- ============ 盈亏走势图 ============ -->
<section>
  <h2>盈亏走势</h2>
  <div class="hint">每一个点代表一笔交易结算时的累计盈亏。曲线往上走代表在赚钱。</div>
  <canvas id="pnl-chart"></canvas>
</section>

<!-- ============ 正在持有 ============ -->
<section>
  <h2>正在持有({{ open_positions|length }} 笔)</h2>
  <div class="hint">机器人已经下单,等待官方判出结果。一般 1-7 天后会结算。</div>
  {% if open_positions %}
  <table>
    <thead>
      <tr>
        <th>市场题目</th>
        <th>押的方向</th>
        <th class="num">花了多少</th>
        <th class="num">已等</th>
      </tr>
    </thead>
    <tbody>
    {% for p in open_positions %}
      <tr>
        <td><span class="q" title="{{ p.question }}">{{ p.question }}</span></td>
        <td>
          <span class="pill pill-{{ 'yes' if p.side == 'YES' else 'no' }}">
            {{ '会发生' if p.side == 'YES' else '不会发生' }}
          </span>
        </td>
        <td class="num">${{ '%.2f' % p.cost_usd }}</td>
        <td class="num">{{ p.held_human }}</td>
      </tr>
    {% endfor %}
    </tbody>
  </table>
  {% else %}
  <div class="empty">目前没有持仓。机器人还在扫描市场。</div>
  {% endif %}
</section>

<!-- ============ 已结清 ============ -->
<section>
  <h2>已经结清(最近 {{ closed_positions|length }} 笔,共 {{ s.closed_count }} 笔)</h2>
  <div class="hint">官方已经判出结果,赚的或亏的已经到账。</div>
  {% if closed_positions %}
  <table>
    <thead>
      <tr>
        <th>市场题目</th>
        <th>押的方向</th>
        <th class="num">成本</th>
        <th class="num">回收</th>
        <th class="num">盈亏</th>
        <th class="num">持有</th>
      </tr>
    </thead>
    <tbody>
    {% for p in closed_positions %}
      <tr>
        <td><span class="q" title="{{ p.question }}">{{ p.question }}</span></td>
        <td>
          <span class="pill pill-{{ 'yes' if p.side == 'YES' else 'no' }}">
            {{ '会发生' if p.side == 'YES' else '不会发生' }}
          </span>
        </td>
        <td class="num">${{ '%.2f' % p.cost_usd }}</td>
        <td class="num">${{ '%.2f' % (p.payout_usd or 0) }}</td>
        <td class="num {{ 'pos' if p.pnl >= 0 else 'neg' }}">
          {{ '+' if p.pnl >= 0 else '' }}${{ '%.2f' % p.pnl }}
        </td>
        <td class="num">{{ p.held_human }}</td>
      </tr>
    {% endfor %}
    </tbody>
  </table>
  {% else %}
  <div class="empty">还没有结清的交易。第一批结算大约要等 1-7 天。</div>
  {% endif %}
</section>

<!-- ============ 帮助 ============ -->
<details>
  <summary>这个看板是什么意思?</summary>
  <p>
    <strong>机器人在干什么?</strong><br />
    它在 Polymarket 上找一种"已经知道答案但还没正式公布"的市场。比赛打完了、
    币价已经定格了,但官方仲裁(UMA)还要花 1-7 天确认结果。这段时间里,
    赢的那一方的"彩票"经常被挂在 95-96 美分卖,机器人买进来等到 1 美元结算,
    赚中间的差价。
  </p>
  <p>
    <strong>"押的方向"是什么意思?</strong><br />
    每个市场都是一个是/否题(例如"湖人会赢吗?")。
    <span class="pill pill-yes">会发生</span> 代表机器人押"是会发生",
    <span class="pill pill-no">不会发生</span> 代表机器人押"不会发生"。
  </p>
  <p>
    <strong>为什么会亏?</strong><br />
    偶尔 UMA 会改判,那一笔交易就是全亏(亏全部成本)。所以机器人单笔最多
    押 ${{ '%.0f' % cfg.max_position_size_usd }},总仓位最多
    ${{ '%.0f' % cfg.max_total_exposure_usd }},把鸡蛋放在很多篮子里。
  </p>
  <p>
    <strong>怎么判断这套策略到底行不行?</strong><br />
    看上面的"盈亏走势"曲线。**至少跑一周、至少有 20 笔结清后**再看趋势。
    如果曲线整体向上,策略可能真有 edge;如果横盘或向下,
    说明阈值需要调整或这策略目前不适合你。
  </p>
</details>

<script>
(async function() {
  const r = await fetch('/api/pnl-series');
  const series = await r.json();
  const canvas = document.getElementById('pnl-chart');
  const ctx = canvas.getContext('2d');
  const rect = canvas.getBoundingClientRect();
  canvas.width = rect.width * window.devicePixelRatio;
  canvas.height = rect.height * window.devicePixelRatio;
  ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
  const W = rect.width, H = rect.height;
  ctx.clearRect(0, 0, W, H);

  if (!series.length) {
    ctx.fillStyle = '#6e7681';
    ctx.font = '13px -apple-system, sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('还没有结清的交易,无数据可画', W/2, H/2);
    return;
  }

  const pad = {l: 56, r: 16, t: 12, b: 28};
  const ys = series.map(p => p[1]);
  const yMin = Math.min(0, ...ys);
  const yMax = Math.max(0, ...ys);
  const yPad = (yMax - yMin) * 0.1 || 1;
  const y0 = yMin - yPad, y1 = yMax + yPad;
  const xScale = i => pad.l + (i / Math.max(1, series.length - 1)) * (W - pad.l - pad.r);
  const yScale = v => H - pad.b - ((v - y0) / (y1 - y0)) * (H - pad.t - pad.b);

  // 网格 + y 轴标签
  ctx.strokeStyle = '#e3e6ea'; ctx.lineWidth = 1;
  ctx.fillStyle = '#6e7681'; ctx.font = '11px -apple-system, sans-serif';
  ctx.textAlign = 'right'; ctx.textBaseline = 'middle';
  for (let i = 0; i <= 4; i++) {
    const v = y0 + (y1 - y0) * (i / 4);
    const y = yScale(v);
    ctx.beginPath(); ctx.moveTo(pad.l, y); ctx.lineTo(W - pad.r, y); ctx.stroke();
    ctx.fillText('$' + v.toFixed(2), pad.l - 6, y);
  }
  // 零线加粗
  const zeroY = yScale(0);
  ctx.strokeStyle = '#9aa4ad'; ctx.lineWidth = 1;
  ctx.beginPath(); ctx.moveTo(pad.l, zeroY); ctx.lineTo(W - pad.r, zeroY); ctx.stroke();

  // 折线
  const lastY = ys[ys.length - 1];
  ctx.strokeStyle = lastY >= 0 ? '#1f883d' : '#cf222e';
  ctx.lineWidth = 2.5;
  ctx.beginPath();
  series.forEach((p, i) => {
    const x = xScale(i), y = yScale(p[1]);
    if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
  });
  ctx.stroke();

  // 末尾数值标签
  ctx.fillStyle = lastY >= 0 ? '#1f883d' : '#cf222e';
  ctx.textAlign = 'left'; ctx.textBaseline = 'middle';
  ctx.font = 'bold 12px -apple-system, sans-serif';
  ctx.fillText((lastY >= 0 ? '+$' : '-$') + Math.abs(lastY).toFixed(2),
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
        closes = store.closed_positions(limit=20)

        opens_view = []
        for p in opens:
            hours = _hours_since(p.opened_at.isoformat())
            opens_view.append({
                "question": p.question,
                "side": p.side,
                "cost_usd": p.cost_usd,
                "held_human": _humanize_duration(hours),
            })

        closes_view = []
        for p in closes:
            payout = p.payout_usd or 0.0
            pnl = payout - p.cost_usd
            held_hours = None
            if p.closed_at and p.opened_at:
                held_hours = (p.closed_at - p.opened_at).total_seconds() / 3600.0
            closes_view.append({
                "question": p.question,
                "side": p.side,
                "cost_usd": p.cost_usd,
                "payout_usd": p.payout_usd,
                "pnl": pnl,
                "held_human": _humanize_duration(held_hours),
            })

        return render_template_string(
            PAGE,
            s=s,
            open_positions=opens_view,
            closed_positions=closes_view,
            dry_run=config.dry_run,
            cfg=config,
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
    parser = argparse.ArgumentParser(description="Polymarket 套利助手看板")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    store = PositionStore(CONFIG.db_path)
    app = create_app(store, CONFIG)
    print(f"\n  看板地址:  http://{args.host}:{args.port}\n"
          f"  数据文件:  {CONFIG.db_path}\n"
          f"  当前模式:  {'真实交易' if not CONFIG.dry_run else '演练模式(不花钱)'}\n")
    app.run(host=args.host, port=args.port, debug=args.debug)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
