"""极简中文看板,显示演练 vs 实盘预估的差距。

主要呈现:
  1. 大字"已结算盈亏" - 默认显示实盘预估,旁边对比理想数
  2. 三个小卡片 - 持仓/场上资金/捕获率
  3. "演练 vs 实盘"小节 - 检测/成交率/平均价格漂移
  4. 盈亏走势双线图 - 理想(虚线) vs 实盘预估(实线)
  5. 持仓表 + 结清表(结清表带"实盘盈亏"列)
  6. 折叠帮助 - 解释为什么会有差距

运行:python -m polymarket_arb.dashboard
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
  .hero-sub { color: var(--muted); font-size: 13px; line-height: 1.7; }
  .hero-ideal {
    margin-top: 6px; font-size: 12px; color: var(--muted);
  }
  .hero-ideal .ideal-value { font-variant-numeric: tabular-nums; }
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

  /* 实盘差距小卡片(4 列) */
  .gap-row {
    display: grid; gap: 12px;
    grid-template-columns: repeat(4, 1fr);
    margin-bottom: 8px;
  }
  @media (max-width: 600px) {
    .gap-row { grid-template-columns: repeat(2, 1fr); }
  }
  .gap-card {
    background: var(--panel); border: 1px solid var(--border);
    border-radius: 10px; padding: 12px 14px;
  }
  .gap-label { color: var(--muted); font-size: 11px; }
  .gap-value {
    font-size: 18px; font-weight: 600; margin-top: 2px;
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
  td.muted { color: var(--muted); }

  .pill {
    display: inline-block; padding: 2px 8px; border-radius: 10px;
    font-size: 11px; font-weight: 500;
  }
  .pill-yes { background: #dafbe1; color: var(--good); }
  .pill-no  { background: #ffebe9; color: var(--bad); }

  .q {
    max-width: 300px; white-space: nowrap; overflow: hidden;
    text-overflow: ellipsis; display: inline-block; vertical-align: middle;
  }
  .empty {
    background: var(--panel); border: 1px solid var(--border);
    border-radius: 10px; padding: 32px; text-align: center;
    color: var(--muted); font-size: 13px;
  }

  #pnl-chart {
    width: 100%; height: 260px; background: var(--panel);
    border: 1px solid var(--border); border-radius: 10px;
    padding: 12px;
  }
  .legend {
    font-size: 11px; color: var(--muted); margin-top: 6px;
    display: flex; gap: 16px; padding: 0 12px;
  }
  .legend-dot {
    display: inline-block; width: 18px; height: 2px;
    vertical-align: middle; margin-right: 6px;
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
  details ul { font-size: 13px; line-height: 1.7; padding-left: 20px; }
</style>
</head>
<body>

<h1>Polymarket 套利助手</h1>
<div class="sub">
  <span class="badge {{ 'badge-live' if not dry_run else 'badge-dry' }}">
    {{ '真实交易中' if not dry_run else '演练模式(不花钱,带实盘模拟)' }}
  </span>
  &nbsp;·&nbsp; 更新于 {{ refreshed_at }}
  &nbsp;·&nbsp; <a href="javascript:location.reload()">刷新</a>
</div>

<!-- ============ 主要数字:实盘预估盈亏 ============ -->
<div class="hero">
  {% if dry_run and s.closed_count > 0 %}
    <div class="hero-label">已结算盈亏(实盘预估)</div>
    <div class="hero-value {{ 'pos' if s.realistic_pnl > 0 else ('neg' if s.realistic_pnl < 0 else 'neutral') }}">
      {{ '+' if s.realistic_pnl >= 0 else '' }}${{ '%.2f' % s.realistic_pnl }}
    </div>
    <div class="hero-sub">
      共 {{ s.closed_count }} 笔已结清
      &nbsp;·&nbsp; 单笔平均
      <span class="{{ 'pos' if s.realistic_avg_return_pct >= 0 else 'neg' }}">
        {{ '+' if s.realistic_avg_return_pct >= 0 else '' }}{{ '%.1f' % s.realistic_avg_return_pct }}%
      </span>
    </div>
    <div class="hero-ideal">
      如果完美执行,理想盈亏会是
      <span class="ideal-value {{ 'pos' if s.realized_pnl >= 0 else 'neg' }}">
        {{ '+' if s.realized_pnl >= 0 else '' }}${{ '%.2f' % s.realized_pnl }}
      </span>
      ,实盘缩水了
      <strong>${{ '%.2f' % (s.realized_pnl - s.realistic_pnl) }}</strong>
    </div>
  {% else %}
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
        共 {{ s.closed_count }} 笔已结清
        &nbsp;·&nbsp; 单笔平均
        <span class="{{ 'pos' if s.avg_return_pct >= 0 else 'neg' }}">
          {{ '+' if s.avg_return_pct >= 0 else '' }}{{ '%.1f' % s.avg_return_pct }}%
        </span>
      {% endif %}
    </div>
  {% endif %}
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
    <div class="stat-label">总成本(实盘预估)</div>
    <div class="stat-value">${{ '%.2f' % (s.realistic_cost if dry_run else s.realized_cost) }}</div>
  </div>
</div>

<!-- ============ 演练 vs 实盘的差距 ============ -->
{% if dry_run and verif.detected > 0 %}
<section>
  <h2>演练 vs 实盘的差距</h2>
  <div class="hint">
    每次发现机会后,机器人等 {{ '%.0f' % cfg.verification_delay_seconds }} 秒再回查盘口,看看真的下单时还来不来得及。这是最诚实的实盘模拟。
  </div>
  <div class="gap-row">
    <div class="gap-card">
      <div class="gap-label">发现机会</div>
      <div class="gap-value">{{ verif.detected }} 次</div>
    </div>
    <div class="gap-card">
      <div class="gap-label">实际抢到</div>
      <div class="gap-value">
        {{ verif.filled }} 次
        <span style="font-size: 12px; color: var(--muted)">
          ({{ '%.0f' % (verif.fill_rate * 100) }}%)
        </span>
      </div>
    </div>
    <div class="gap-card">
      <div class="gap-label">资金捕获率</div>
      <div class="gap-value">{{ '%.0f' % (verif.capture_ratio * 100) }}%</div>
    </div>
    <div class="gap-card">
      <div class="gap-label">平均价格漂移</div>
      <div class="gap-value">
        {% if verif.avg_price_drift > 0 %}
          +{{ '%.1f' % (verif.avg_price_drift * 100) }}¢
        {% else %}
          {{ '%.1f' % (verif.avg_price_drift * 100) }}¢
        {% endif %}
      </div>
    </div>
  </div>
  <div class="hint" style="margin-top: 10px">
    💡 看不懂这些数字?展开下方"实盘和演练为什么有差距?"
  </div>
</section>
{% endif %}

<!-- ============ 盈亏走势图 ============ -->
<section>
  <h2>盈亏走势</h2>
  <div class="hint">
    {% if dry_run %}
    每个点是一次结算。实线是实盘预估,虚线是"如果完美执行"的理想结果。两条线分得越开,实盘越难做。
    {% else %}
    每个点是一次结算,曲线往上走代表在赚钱。
    {% endif %}
  </div>
  <canvas id="pnl-chart"></canvas>
  {% if dry_run %}
  <div class="legend">
    <span><span class="legend-dot" style="background: #1f883d"></span>实盘预估</span>
    <span><span class="legend-dot" style="background: #9aa4ad; border-top: 1px dashed; border-bottom: 0; height: 0"></span>理想(完美执行)</span>
  </div>
  {% endif %}
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
  <div class="hint">
    {% if dry_run %}"理想"是完美执行下应得,"实盘"是模拟过摩擦后的真实预估。{% else %}赚的或亏的已经到账。{% endif %}
  </div>
  {% if closed_positions %}
  <table>
    <thead>
      <tr>
        <th>市场题目</th>
        <th>押的方向</th>
        {% if dry_run %}
        <th class="num">理想盈亏</th>
        <th class="num">实盘盈亏</th>
        <th class="num">备注</th>
        {% else %}
        <th class="num">成本</th>
        <th class="num">回收</th>
        <th class="num">盈亏</th>
        {% endif %}
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
        {% if dry_run %}
        <td class="num {{ 'pos' if p.ideal_pnl >= 0 else 'neg' }}">
          {{ '+' if p.ideal_pnl >= 0 else '' }}${{ '%.2f' % p.ideal_pnl }}
        </td>
        <td class="num {{ 'pos' if p.realistic_pnl >= 0 else 'neg' }}">
          {{ '+' if p.realistic_pnl >= 0 else '' }}${{ '%.2f' % p.realistic_pnl }}
        </td>
        <td class="muted" style="font-size: 11px">{{ p.sim_flags or '' }}</td>
        {% else %}
        <td class="num">${{ '%.2f' % p.cost_usd }}</td>
        <td class="num">${{ '%.2f' % (p.payout_usd or 0) }}</td>
        <td class="num {{ 'pos' if p.ideal_pnl >= 0 else 'neg' }}">
          {{ '+' if p.ideal_pnl >= 0 else '' }}${{ '%.2f' % p.ideal_pnl }}
        </td>
        {% endif %}
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
    <strong>机器人在干什么?</strong>
    在 Polymarket 上找一种"已经知道答案但还没正式公布"的市场。
    比赛打完了、币价定格了,但官方仲裁(UMA)还要 1-7 天才会确认。
    这段时间里,赢的那一方"彩票"经常被挂在 95-96 美分卖。
    机器人买进,等 1 美元结算,赚中间差价。
  </p>
  <p>
    <strong>"押的方向"是什么?</strong>
    每个市场是一个是/否题。
    <span class="pill pill-yes">会发生</span> = 押"是",
    <span class="pill pill-no">不会发生</span> = 押"否"。
  </p>
</details>

{% if dry_run %}
<details>
  <summary>实盘和演练为什么有差距?</summary>
  <p>
    <strong>核心问题:演练默认"看到啥都能买到",但实盘不一定。</strong>
    机器人加了一层"实盘模拟",尽量贴近真实结果:
  </p>
  <ul>
    <li><strong>抢单延迟</strong>:发现机会后,机器人等 {{ '%.0f' % cfg.verification_delay_seconds }} 秒再回查盘口。如果别的 bot 已经把便宜货吃掉了,这次就算"miss"。</li>
    <li><strong>部分成交</strong>:订单常常只能成交一部分(平均 {{ '%.0f' % (cfg.expected_fill_ratio * 100) }}%),不是全部。</li>
    <li><strong>gas 成本</strong>:每笔交易扣 ${{ '%.2f' % cfg.estimated_gas_cost_usd }} 的链上手续费。</li>
    <li><strong>逆向选择</strong>:有 {{ '%.1f' % (cfg.adverse_fill_rate * 100) }}% 的概率,愿意 0.96 卖给你的人,其实是因为他知道市场要被改判,这笔就归零。</li>
    <li><strong>UMA 改判</strong>:即便买了正确的一边,有 {{ '%.1f' % (cfg.uma_dispute_rate * 100) }}% 的概率官方仲裁改判,你的"赢"会变成"输"。</li>
  </ul>
  <p>
    <strong>怎么用这个差距?</strong>
    上面的"实盘预估"是把这些摩擦都算进去之后的结果。
    <strong>这个数字比"理想"更接近你真去 Polymarket 实盘后的真实表现。</strong>
    如果实盘预估也是绿的,策略才真有 edge;如果实盘预估是红的而理想是绿的,
    说明只能赚到理论收益、扛不住真实摩擦。
  </p>
  <p>
    <strong>"资金捕获率"是什么?</strong>
    机器人想买 $100,但因为价格漂移和部分成交,实际只买到 ${{ '%.0f' % (verif.capture_ratio * 100 if verif.detected > 0 else 70) }}。
    捕获率越低,实盘越难做。
  </p>
  <p>
    <strong>所有参数在哪改?</strong>
    在 <code>.env</code> 里改 <code>VERIFICATION_DELAY_SECONDS</code>、
    <code>ADVERSE_FILL_RATE</code> 等。默认值是基于公开观察的保守估计,
    跑一周后用真实数据调整。
  </p>
</details>
{% endif %}

<script>
(async function() {
  const [realRes, idealRes] = await Promise.all([
    fetch('/api/pnl-series?realistic=1').then(r => r.json()),
    fetch('/api/pnl-series').then(r => r.json()),
  ]);
  const dryRun = {{ 'true' if dry_run else 'false' }};
  const canvas = document.getElementById('pnl-chart');
  const ctx = canvas.getContext('2d');
  const rect = canvas.getBoundingClientRect();
  canvas.width = rect.width * window.devicePixelRatio;
  canvas.height = rect.height * window.devicePixelRatio;
  ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
  const W = rect.width, H = rect.height;
  ctx.clearRect(0, 0, W, H);

  const primary = dryRun ? realRes : idealRes;
  if (!primary.length) {
    ctx.fillStyle = '#6e7681';
    ctx.font = '13px -apple-system, sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('还没有结清的交易,无数据可画', W/2, H/2);
    return;
  }

  const pad = {l: 56, r: 16, t: 12, b: 28};
  const allY = primary.map(p => p[1]).concat(idealRes.map(p => p[1]));
  const yMin = Math.min(0, ...allY);
  const yMax = Math.max(0, ...allY);
  const yPad = (yMax - yMin) * 0.1 || 1;
  const y0 = yMin - yPad, y1 = yMax + yPad;
  const xMax = Math.max(primary.length, idealRes.length);
  const xScale = i => pad.l + (i / Math.max(1, xMax - 1)) * (W - pad.l - pad.r);
  const yScale = v => H - pad.b - ((v - y0) / (y1 - y0)) * (H - pad.t - pad.b);

  // grid
  ctx.strokeStyle = '#e3e6ea'; ctx.lineWidth = 1;
  ctx.fillStyle = '#6e7681'; ctx.font = '11px -apple-system, sans-serif';
  ctx.textAlign = 'right'; ctx.textBaseline = 'middle';
  for (let i = 0; i <= 4; i++) {
    const v = y0 + (y1 - y0) * (i / 4);
    const y = yScale(v);
    ctx.beginPath(); ctx.moveTo(pad.l, y); ctx.lineTo(W - pad.r, y); ctx.stroke();
    ctx.fillText('$' + v.toFixed(2), pad.l - 6, y);
  }
  // zero line
  const zeroY = yScale(0);
  ctx.strokeStyle = '#9aa4ad'; ctx.lineWidth = 1;
  ctx.beginPath(); ctx.moveTo(pad.l, zeroY); ctx.lineTo(W - pad.r, zeroY); ctx.stroke();

  // ideal (dashed, only in dry-run)
  if (dryRun && idealRes.length) {
    ctx.strokeStyle = '#9aa4ad'; ctx.lineWidth = 1.5;
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    idealRes.forEach((p, i) => {
      const x = xScale(i), y = yScale(p[1]);
      if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    });
    ctx.stroke();
    ctx.setLineDash([]);
  }

  // primary line (realistic in dry-run, ideal in live)
  const lastY = primary[primary.length - 1][1];
  ctx.strokeStyle = lastY >= 0 ? '#1f883d' : '#cf222e';
  ctx.lineWidth = 2.5;
  ctx.beginPath();
  primary.forEach((p, i) => {
    const x = xScale(i), y = yScale(p[1]);
    if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
  });
  ctx.stroke();

  // last value label
  ctx.fillStyle = lastY >= 0 ? '#1f883d' : '#cf222e';
  ctx.textAlign = 'left'; ctx.textBaseline = 'middle';
  ctx.font = 'bold 12px -apple-system, sans-serif';
  ctx.fillText((lastY >= 0 ? '+$' : '-$') + Math.abs(lastY).toFixed(2),
               xScale(primary.length - 1) + 6, yScale(lastY));
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
        verif = store.verification_stats()
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
            ideal_pnl = payout - p.cost_usd
            real_cost = p.realistic_cost_usd if p.realistic_cost_usd is not None else p.cost_usd
            real_payout = p.realistic_payout_usd if p.realistic_payout_usd is not None else payout
            real_pnl = real_payout - real_cost
            held = None
            if p.closed_at and p.opened_at:
                held = (p.closed_at - p.opened_at).total_seconds() / 3600.0
            closes_view.append({
                "question": p.question,
                "side": p.side,
                "cost_usd": p.cost_usd,
                "payout_usd": p.payout_usd,
                "ideal_pnl": ideal_pnl,
                "realistic_pnl": real_pnl,
                "sim_flags": p.sim_flags or "",
                "held_human": _humanize_duration(held),
            })

        return render_template_string(
            PAGE,
            s=s,
            verif=verif,
            open_positions=opens_view,
            closed_positions=closes_view,
            dry_run=config.dry_run,
            cfg=config,
            refreshed_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

    @app.route("/api/pnl-series")
    def api_pnl_series():
        from flask import request
        realistic = request.args.get("realistic") in {"1", "true"}
        return jsonify(store.cumulative_pnl_series(realistic=realistic))

    @app.route("/api/summary")
    def api_summary():
        return jsonify({**store.summary(), "verification": store.verification_stats()})

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
          f"  当前模式:  {'真实交易' if not CONFIG.dry_run else '演练模式(带实盘模拟)'}\n")
    app.run(host=args.host, port=args.port, debug=args.debug)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
