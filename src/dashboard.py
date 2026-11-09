"""Writes the self-contained HTML dashboard (docs/index.html) from results.json."""
from __future__ import annotations

import json
from pathlib import Path

TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ResearchPulse Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.js"></script>
<style>
:root{color-scheme:light;
  --page:#f9f9f7;--surface:#fcfcfb;--ink:#0b0b0b;--ink2:#52514e;--muted:#898781;--grid:#e1e0d9;--axis:#c3c2b7;
  --border:rgba(11,11,11,.10);--s1:#2a78d6;--s2:#eb6834;--s3:#1baf7a;--s4:#eda100;--s5:#e87ba4;--s6:#008300;
  --seq1:#cde2fb;--seq4:#86b6ef;--seq7:#3987e5;--seq10:#1c5cab;--seq13:#0d366b;--neg:#e34948;--mid:#f0efec;--up:#006300}
@media (prefers-color-scheme:dark){:root:where(:not([data-theme="light"])){color-scheme:dark;
  --page:#0d0d0d;--surface:#1a1a19;--ink:#f0efec;--ink2:#c3c2b7;--muted:#898781;--grid:#2c2c2a;--axis:#383835;
  --border:rgba(255,255,255,.10);--s1:#3987e5;--s2:#d95926;--s3:#199e70;--s4:#c98500;--s5:#d55181;--s6:#008300;
  --seq1:#104281;--seq4:#1c5cab;--seq7:#2a78d6;--seq10:#6da7ec;--seq13:#b7d3f6;--neg:#e66767;--mid:#383835;--up:#0ca30c}}
:root[data-theme="dark"]{color-scheme:dark;
  --page:#0d0d0d;--surface:#1a1a19;--ink:#f0efec;--ink2:#c3c2b7;--muted:#898781;--grid:#2c2c2a;--axis:#383835;
  --border:rgba(255,255,255,.10);--s1:#3987e5;--s2:#d95926;--s3:#199e70;--s4:#c98500;--s5:#d55181;--s6:#008300;
  --seq1:#104281;--seq4:#1c5cab;--seq7:#2a78d6;--seq10:#6da7ec;--seq13:#b7d3f6;--neg:#e66767;--mid:#383835;--up:#0ca30c}
*{box-sizing:border-box}
body{margin:0;background:var(--page);color:var(--ink);font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}
.wrap{max-width:1200px;margin:0 auto;padding:28px 16px 64px}
h1{font-size:26px;line-height:1.25;margin:0 0 6px;letter-spacing:-.01em}
.sub{color:var(--ink2);margin:0 0 6px}
.meta{color:var(--muted);font-size:13px;margin:0 0 22px}
h2{font-size:17px;margin:0 0 2px}
h3{font-size:13px;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);margin:30px 0 12px}
.note{color:var(--ink2);font-size:13px;margin:0 0 14px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,250px),1fr));gap:12px;margin-bottom:8px}
.kpi{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:14px 16px}
.kpi .v{font-size:24px;font-weight:700;line-height:1.25}
.kpi .l{color:var(--ink2);font-size:13px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,540px),1fr));gap:16px}
.card{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:18px;min-width:0}
.full{grid-column:1/-1}
.chart{position:relative;height:340px}.tall{height:460px}
.row{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:0 0 12px;font-size:13px;color:var(--ink2)}
select{font:inherit;font-size:13px;padding:5px 8px;border-radius:8px;border:1px solid var(--border);background:var(--surface);color:var(--ink)}
.tw{overflow-x:auto}
table{width:100%;border-collapse:collapse;font-size:13.5px}
th,td{text-align:left;padding:7px 6px;border-bottom:1px solid var(--grid)}
th{color:var(--muted);font-weight:600;font-size:11.5px;text-transform:uppercase;letter-spacing:.04em;white-space:nowrap}
td.n,th.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.up{color:var(--up);font-weight:600}.down{color:var(--neg);font-weight:600}
.pill{display:inline-block;padding:1px 8px;border-radius:999px;font-size:12px;border:1px solid var(--border);color:var(--ink2)}
.heat td{text-align:center;font-variant-numeric:tabular-nums;font-size:12px;padding:6px 4px;min-width:44px}
.heat th.rowh{text-align:left;text-transform:none;letter-spacing:0;font-size:12.5px;color:var(--ink2);white-space:nowrap}
.heat th.colh{writing-mode:vertical-rl;transform:rotate(180deg);text-transform:none;letter-spacing:0;font-size:12px;height:130px;vertical-align:bottom;padding:4px}
.method{font-size:13px;color:var(--ink2)}.method li{margin:4px 0}
footer{color:var(--muted);font-size:12px;margin-top:26px}
</style>
</head>
<body>
<div class="wrap">
  <h1>ResearchPulse: Emerging &amp; Interdisciplinary Research Trend Analytics</h1>
  <p class="sub" id="sub"></p>
  <p class="meta" id="meta"></p>

  <div class="kpis" id="kpis"></div>

  <h3>1 · Fields</h3>
  <div class="grid">
    <div class="card">
      <h2>Field output over time</h2>
      <p class="note">Papers per year, indexed so the first year = 100.</p>
      <div class="row">Show <select id="fieldSet">
        <option value="gain">Fields gaining the most share</option>
        <option value="lose">Fields losing the most share</option>
        <option value="large">Largest fields</option></select></div>
      <div class="chart"><canvas id="fieldLines"></canvas></div>
    </div>
    <div class="card">
      <h2>Change in share of all research</h2>
      <p class="note" id="shareNote"></p>
      <div class="chart tall"><canvas id="fieldShare"></canvas></div>
    </div>
  </div>

  <h3>2 · Subfields: what is rising and falling</h3>
  <div class="grid">
    <div class="card">
      <h2>Fastest-rising and fastest-falling subfields</h2>
      <p class="note">Trend in each subfield's <b>share</b> of all research, % per year (log-linear fit over all years).</p>
      <div class="chart tall"><canvas id="riseFall"></canvas></div>
    </div>
    <div class="card">
      <h2>Size vs. momentum</h2>
      <p class="note">Each dot is a subfield. Up = gaining share; right = larger. Steady trends (R² ≥ 0.6) are classed Rising/Declining.</p>
      <div class="chart tall"><canvas id="scatter"></canvas></div>
    </div>
    <div class="card full">
      <h2>Top rising subfields</h2>
      <p class="note" id="risingNote"></p>
      <div class="tw"><table id="risingTable"></table></div>
    </div>
    <div class="card full">
      <h2>Fastest-rising research topics inside the top subfields</h2>
      <p class="note">Papers in a 2-year window early vs. late in the period. Ranked by papers added.</p>
      <div class="tw"><table id="topicTable"></table></div>
    </div>
  </div>

  <h3>3 · Interdisciplinarity</h3>
  <div class="grid">
    <div class="card" id="focusCard">
      <h2 id="focusTitle"></h2>
      <p class="note" id="focusNote"></p>
      <div class="chart tall"><canvas id="focusSpread"></canvas></div>
    </div>
    <div class="card">
      <h2>Fastest-growing field overlaps</h2>
      <p class="note">Share of a field's papers that also carry a topic from another field: first vs. last year.</p>
      <div class="tw"><table id="crossGrowth"></table></div>
    </div>
    <div class="card full">
      <h2>Field overlap map</h2>
      <p class="note" id="heatNote"></p>
      <div class="tw"><table class="heat" id="heat"></table></div>
    </div>
  </div>

  <h3>4 · Who is driving it</h3>
  <div class="grid">
    <div class="card" id="countryCard">
      <h2>Country participation in rising subfields</h2>
      <p class="note">% of the subfield's papers with at least one author from each country.</p>
      <div class="row">Subfield <select id="countryPick"></select></div>
      <div class="chart"><canvas id="countries"></canvas></div>
    </div>
    <div class="card" id="instCard">
      <h2 id="instTitle"></h2>
      <p class="note">Papers by primary field (institution and its sub-units).</p>
      <div class="chart"><canvas id="inst"></canvas></div>
    </div>
  </div>

  <h3>5 · Data quality &amp; method</h3>
  <div class="grid">
    <div class="card">
      <h2>Data quality checks</h2>
      <div class="tw"><table id="dq"></table></div>
    </div>
    <div class="card">
      <h2>Method &amp; limitations</h2>
      <ul class="method" id="method"></ul>
    </div>
  </div>
  <footer>Data: OpenAlex (CC0), openalex.org. Built with Python, SQL (SQLite) and Chart.js.</footer>
</div>
<script>
const D = __DATA__;
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const C = {}; ['--ink','--ink2','--muted','--grid','--axis','--surface','--s1','--s2','--s3','--s4','--s5','--s6',
  '--seq1','--seq4','--seq7','--seq10','--seq13','--neg','--mid'].forEach(k => C[k.slice(2)] = css(k));
const SERIES = [C.s1, C.s2, C.s3, C.s4, C.s5, C.s6];
Chart.defaults.color = C.ink2; Chart.defaults.borderColor = C.grid;
Chart.defaults.font.family = getComputedStyle(document.body).fontFamily; Chart.defaults.font.size = 12;
Chart.defaults.maintainAspectRatio = false;
Chart.defaults.plugins.tooltip.mode = 'nearest';
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt = n => n == null ? '–' : Number(n).toLocaleString();
const pct = (n, d=1) => n == null ? '–' : Number(n).toFixed(d) + '%';
const sgn = (n, d=1, u='%') => n == null ? '–' : (n > 0 ? '+' : n < 0 ? '−' : '') + Math.abs(n).toFixed(d) + u;
const cls = n => n > 0 ? 'up' : n < 0 ? 'down' : '';
const short = (s, n=34) => s && s.length > n ? s.slice(0, n - 1) + '…' : s;
const axis = extra => Object.assign({grid:{color:C.grid}, border:{color:C.axis}, ticks:{color:C.muted}}, extra || {});
const P = D.params, A = D.analysis;
const first = P.first_year, last = P.last_year;

document.getElementById('sub').textContent =
  `Which research fields are growing, which are shrinking, and where fields are converging, ${first}–${last}.`;
document.getElementById('meta').textContent =
  `Source: OpenAlex · peer-reviewed ${P.work_types.replace('|', ' + ')} · generated ${D.generated} · ${fmt(D.api_calls)} API calls`;

// KPIs
const totalWorks = A.totals.reduce((s, r) => s + r.works, 0);
const lastTot = A.totals.find(r => r.year === last) || {}, firstTot = A.totals.find(r => r.year === first) || {};
const topR = A.rising[0] || {};
const cc = A.class_counts;
const fw = (A.focus && A.focus.works_by_year) || [];
const fFirst = fw.find(r => r.year === first), fLast = fw.find(r => r.year === last);
const kpis = [
  [fmt(totalWorks), `papers analyzed (${first}–${last})`],
  [sgn(100 * (Math.pow(lastTot.works / firstTot.works, 1 / (last - first)) - 1)), 'annual growth of all research output (CAGR)'],
  [`${fmt(cc['Rising'] || 0)} ↑ · ${fmt(cc['Declining'] || 0)} ↓`, `subfields with a steady rising / declining share (of ${fmt(D.quality.subfields_in_taxonomy)})`],
  [esc(short(topR.subfield, 30)), `fastest-rising subfield: ${sgn(topR.share_trend_pct)} share per year`],
];
if (fFirst && fLast) kpis.push([`${pct(fFirst.share_pct, 1)} → ${pct(fLast.share_pct, 1)}`, `share of all papers touching ${esc(A.focus.name)}`]);
kpis.push([pct(100 - D.quality.pct_works_without_topic, 1), 'of papers carry a topic classification']);
document.getElementById('kpis').innerHTML = kpis.map(([v, l]) =>
  `<div class="kpi"><div class="v">${v}</div><div class="l">${l}</div></div>`).join('');

// 1a Field lines
const FC = A.field_change;
const sets = {gain: FC.slice(0, 6).map(r => r.field), lose: FC.slice(-6).reverse().map(r => r.field),
              large: FC.slice().sort((a, b) => b.works_last - a.works_last).slice(0, 6).map(r => r.field)};
let lineChart;
function drawLines() {
  const names = sets[document.getElementById('fieldSet').value];
  const years = [...new Set(A.field_index.map(r => r.year))].sort();
  if (lineChart) lineChart.destroy();
  lineChart = new Chart(document.getElementById('fieldLines'), {type: 'line',
    data: {labels: years, datasets: names.map((n, i) => ({label: n, borderColor: SERIES[i], backgroundColor: SERIES[i],
      borderWidth: 2, pointRadius: 0, pointHoverRadius: 5, tension: .25,
      data: years.map(y => (A.field_index.find(r => r.field === n && r.year === y) || {}).index_first_year)}))},
    options: {interaction: {mode: 'index', intersect: false},
      plugins: {legend: {position: 'bottom', labels: {boxWidth: 10, boxHeight: 10, usePointStyle: true}},
        tooltip: {callbacks: {label: c => `${c.dataset.label}: ${c.parsed.y}`}}},
      scales: {x: axis(), y: axis({title: {display: true, text: `index (${first} = 100)`, color: C.muted}})}}});
}
document.getElementById('fieldSet').addEventListener('change', drawLines); drawLines();

// 1b Field share change (diverging)
document.getElementById('shareNote').textContent = `Percentage-point change in each field's share of all papers, ${first} → ${last}.`;
new Chart(document.getElementById('fieldShare'), {type: 'bar',
  data: {labels: FC.map(r => short(r.field, 30)), datasets: [{data: FC.map(r => r.share_change_pts),
    backgroundColor: FC.map(r => r.share_change_pts >= 0 ? C.s1 : C.neg), borderRadius: 4, barPercentage: .8}]},
  options: {indexAxis: 'y', plugins: {legend: {display: false}, tooltip: {callbacks: {
      title: c => FC[c[0].dataIndex].field,
      label: c => `${sgn(c.parsed.x, 2, ' pts')} (${pct(FC[c.dataIndex].share_first, 2)} → ${pct(FC[c.dataIndex].share_last, 2)})`}}},
    scales: {x: axis({ticks: {color: C.muted, callback: v => v + ' pts'}}), y: axis({grid: {display: false}, ticks: {autoSkip: false, color: C.ink2, font: {size: 11}}})}}});

// 2a Rising / falling
const RF = A.rising.slice(0, 12).concat(A.declining.slice(0, 8).reverse());
new Chart(document.getElementById('riseFall'), {type: 'bar',
  data: {labels: RF.map(r => short(r.subfield, 32)), datasets: [{data: RF.map(r => r.share_trend_pct),
    backgroundColor: RF.map(r => r.share_trend_pct >= 0 ? C.s1 : C.neg), borderRadius: 4, barPercentage: .8}]},
  options: {indexAxis: 'y', plugins: {legend: {display: false}, tooltip: {callbacks: {
      title: c => `${RF[c[0].dataIndex].subfield} (${RF[c[0].dataIndex].field})`,
      label: c => [`share trend ${sgn(c.parsed.x)} / yr (R² ${RF[c.dataIndex].share_r2})`,
                   `raw papers ${sgn(RF[c.dataIndex].raw_trend_pct)} / yr · ${fmt(RF[c.dataIndex].works_last)} in ${last}`]}}},
    scales: {x: axis({ticks: {color: C.muted, callback: v => v + '%'}}), y: axis({grid: {display: false}, ticks: {autoSkip: false, color: C.ink2, font: {size: 11}}})}}});

// 2b Scatter by class (3 categorical slots + neutral)
const CLS = [['Rising', C.s1], ['Declining', C.s2], ['Volatile', C.s3], ['Stable', C.muted]];
new Chart(document.getElementById('scatter'), {type: 'scatter',
  data: {datasets: CLS.map(([k, col]) => ({label: k, backgroundColor: col, borderColor: C.surface, borderWidth: 1,
    pointRadius: 4.5, pointHoverRadius: 7,
    data: A.scatter.filter(r => r.trend_class === k).map(r => ({x: r.works_last, y: r.share_trend_pct, r}))}))},
  options: {plugins: {legend: {position: 'bottom', labels: {usePointStyle: true, boxWidth: 8}},
      tooltip: {callbacks: {label: c => [`${c.raw.r.subfield} (${c.raw.r.field})`,
        `${fmt(c.raw.r.works_last)} papers in ${last} · share ${sgn(c.raw.r.share_trend_pct)}/yr · R² ${c.raw.r.share_r2}`]}}},
    scales: {x: axis({type: 'logarithmic', title: {display: true, text: `papers in ${last} (log scale)`, color: C.muted},
               ticks: {color: C.muted, maxRotation: 0, callback: v => [1e3, 1e4, 1e5, 1e6].includes(v) ? fmt(v) : ''}}),
             y: axis({title: {display: true, text: 'share trend, % per year', color: C.muted}, ticks: {color: C.muted, callback: v => v + '%'}})}}});

// 2c Rising table
document.getElementById('risingNote').textContent =
  `Share trend = growth of the subfield's share of all research. CAGR columns use raw paper counts. Acceleration = recent CAGR (${last - 5}–${last}) minus prior CAGR (${first}–${last - 5}).`;
document.getElementById('risingTable').innerHTML =
  `<tr><th>Subfield</th><th>Field</th><th class="n">Papers ${last}</th><th class="n">Share trend / yr</th><th class="n">R²</th><th class="n">CAGR ${first}–${last - 5}</th><th class="n">CAGR ${last - 5}–${last}</th><th>Class</th></tr>` +
  A.rising.slice(0, 12).map(r => `<tr><td>${esc(r.subfield)}</td><td>${esc(r.field)}</td><td class="n">${fmt(r.works_last)}</td>
    <td class="n ${cls(r.share_trend_pct)}">${sgn(r.share_trend_pct)}</td><td class="n">${r.share_r2 ?? '–'}</td>
    <td class="n">${sgn(r.cagr_prior)}</td><td class="n">${sgn(r.cagr_recent)}</td><td><span class="pill">${esc(r.trend_class)}</span></td></tr>`).join('');

// 2d Topics
document.getElementById('topicTable').innerHTML = A.topics.length ?
  `<tr><th>Topic</th><th>Subfield</th><th class="n">Papers ${P.early_window}</th><th class="n">Papers ${P.late_window}</th><th class="n">Added</th><th class="n">Growth</th></tr>` +
  A.topics.slice(0, 15).map(r => `<tr><td>${esc(r.topic)}</td><td>${esc(r.subfield)}</td><td class="n">${fmt(r.early)}</td>
    <td class="n">${fmt(r.late)}</td><td class="n up">+${fmt(r.abs_growth)}</td><td class="n">${r.growth_pct == null ? 'new' : sgn(r.growth_pct, 0)}</td></tr>`).join('')
  : '<tr><td>No topic data.</td></tr>';

// 3a Focus subfield spread
if (A.focus && A.focus.spread && A.focus.spread.length) {
  const F = A.focus.spread;
  document.getElementById('focusTitle').textContent = `Where ${A.focus.name} research is spreading`;
  document.getElementById('focusNote').textContent =
    `Of all papers with a topic in ${A.focus.name}, the % that also carry a topic from each other field (outside ${A.focus.own_field}).`;
  new Chart(document.getElementById('focusSpread'), {type: 'bar',
    data: {labels: F.map(r => short(r.field, 28)), datasets: [
      {label: String(first), data: F.map(r => r.pct_first), backgroundColor: C.seq4, borderRadius: 4, barPercentage: .9, categoryPercentage: .75},
      {label: String(last), data: F.map(r => r.pct_last), backgroundColor: C.seq10, borderRadius: 4, barPercentage: .9, categoryPercentage: .75}]},
    options: {indexAxis: 'y', plugins: {legend: {position: 'bottom', labels: {boxWidth: 10, boxHeight: 10}},
        tooltip: {callbacks: {label: c => `${c.dataset.label}: ${pct(c.parsed.x)}`}}},
      scales: {x: axis({ticks: {color: C.muted, callback: v => v + '%'}}), y: axis({grid: {display: false}, ticks: {autoSkip: false, color: C.ink2, font: {size: 11}}})}}});
} else document.getElementById('focusCard').style.display = 'none';

// 3b Cross growth table
document.getElementById('crossGrowth').innerHTML =
  `<tr><th>Field</th><th>Also touches</th><th class="n">${first}</th><th class="n">${last}</th><th class="n">Change</th></tr>` +
  A.cross_growth.slice(0, 12).map(r => `<tr><td>${esc(r.primary_field)}</td><td>${esc(r.other_field)}</td>
    <td class="n">${pct(r.pct_first)}</td><td class="n">${pct(r.pct_last)}</td><td class="n ${cls(r.change_pts)}">${sgn(r.change_pts, 1, ' pts')}</td></tr>`).join('');

// 3c Heatmap (sequential, one hue) for the 12 largest fields
const big = FC.slice().sort((a, b) => b.works_last - a.works_last).slice(0, 12).map(r => r.field);
document.getElementById('heatNote').textContent =
  `${last}, 12 largest fields. Row = a paper's primary field; column = another field it also touches. Stronger color = larger share.`;
const cell = (a, b) => (A.cross_last.find(r => r.primary_field === a && r.other_field === b) || {}).pct_of_primary;
const vals = big.flatMap(a => big.map(b => a === b ? null : cell(a, b))).filter(v => v != null);
const vmax = Math.max(1, ...vals);
const ramp = [C.seq1, C.seq4, C.seq7, C.seq10, C.seq13];
const isDark = document.documentElement.dataset.theme === 'dark' ||
  (document.documentElement.dataset.theme !== 'light' && matchMedia('(prefers-color-scheme: dark)').matches);
function heatCell(v) {
  if (v == null) return `<td style="background:${C.mid};color:${C.muted}">–</td>`;
  const i = Math.min(4, Math.floor(Math.sqrt(v / vmax) * 5));
  const light = isDark ? i >= 3 : i <= 1;           // which ramp steps are pale
  return `<td style="background:${ramp[i]};color:${light ? '#0b0b0b' : '#ffffff'}" title="${pct(v)}">${v.toFixed(1)}</td>`;
}
document.getElementById('heat').innerHTML =
  `<tr><th></th>${big.map(b => `<th class="colh">${esc(short(b, 26))}</th>`).join('')}</tr>` +
  big.map(a => `<tr><th class="rowh">${esc(short(a, 30))}</th>${big.map(b => heatCell(a === b ? null : cell(a, b))).join('')}</tr>`).join('');

// 4a Countries
if (A.countries.length) {
  const sel = document.getElementById('countryPick');
  sel.innerHTML = A.countries.map((c, i) => `<option value="${i}">${esc(c.subfield)}</option>`).join('');
  let cChart;
  const draw = () => {
    const c = A.countries[+sel.value].countries;
    if (cChart) cChart.destroy();
    cChart = new Chart(document.getElementById('countries'), {type: 'bar',
      data: {labels: c.map(r => r.country), datasets: [
        {label: P.country_years[0] + '', data: c.map(r => r.pct_first), backgroundColor: C.seq4, borderRadius: 4, categoryPercentage: .7},
        {label: P.country_years[1] + '', data: c.map(r => r.pct_last), backgroundColor: C.seq10, borderRadius: 4, categoryPercentage: .7}]},
      options: {plugins: {legend: {position: 'bottom', labels: {boxWidth: 10, boxHeight: 10}},
          tooltip: {callbacks: {label: x => `${x.dataset.label}: ${pct(x.parsed.y)} of papers`}}},
        scales: {x: axis({grid: {display: false}, ticks: {color: C.muted, maxRotation: 0, autoSkip: false, font: {size: 11}}}), y: axis({ticks: {color: C.muted, callback: v => v + '%'}})}}});
  };
  sel.addEventListener('change', draw); draw();
} else document.getElementById('countryCard').style.display = 'none';

// 4b Institution
if (A.institution) {
  const I = A.institution, bf = I.by_field;
  document.getElementById('instTitle').textContent = `${I.name}: research mix, ${last - 5} vs. ${last}`;
  new Chart(document.getElementById('inst'), {type: 'bar',
    data: {labels: bf.map(r => short(r.field, 26)), datasets: [
      {label: String(last - 5), data: bf.map(r => r.works_mid), backgroundColor: C.seq4, borderRadius: 4, categoryPercentage: .75},
      {label: String(last), data: bf.map(r => r.works_last), backgroundColor: C.seq10, borderRadius: 4, categoryPercentage: .75}]},
    options: {indexAxis: 'y', plugins: {legend: {position: 'bottom', labels: {boxWidth: 10, boxHeight: 10}}},
      scales: {x: axis(), y: axis({grid: {display: false}, ticks: {autoSkip: false, color: C.ink2, font: {size: 11}}})}}});
} else document.getElementById('instCard').style.display = 'none';

// 5 Data quality + method
const Q = D.quality;
document.getElementById('dq').innerHTML = [
  ['Papers without a topic classification', pct(Q.pct_works_without_topic, 2), 'excluded from field/subfield counts'],
  ['Subfields in the taxonomy', fmt(Q.subfields_in_taxonomy), ''],
  ['Subfields with data', fmt(Q.subfields_with_data), ''],
  ['Subfields with a zero year', fmt(Q.subfields_with_zero_year), 'trend fit skips zero years'],
  ['Subfields too small to rank', fmt(cc['Too small'] || 0), `fewer than ${fmt(P.min_works)} papers in ${last - 5}`],
  ['Subfield totals vs. field totals', Q.subfield_vs_field_total_gap === 0 ? 'match' : fmt(Q.subfield_vs_field_total_gap) + ' gap',
   'same papers counted two ways; should match'],
].map(([a, b, c]) => `<tr><td>${a}</td><td class="n">${b}</td><td style="color:${C.muted}">${c}</td></tr>`).join('');
document.getElementById('method').innerHTML = [
  `Counts come from OpenAlex <code>group_by</code> aggregates (no bulk download). Each paper is assigned to one primary topic → subfield → field.`,
  `Trends use each subfield's <b>share</b> of all papers, not raw counts: total output grows every year (and database coverage improves), so raw growth makes nearly every field look "rising".`,
  `Share trend = log-linear regression of share on year (${first}–${last}); R² measures how steady the trend is. Rising / Declining need |trend| > 3%/yr and R² ≥ 0.6.`,
  `Only ${P.work_types.replace('|', ' and ')}s are counted; preprints are excluded to avoid counting the same paper twice. Fields that publish mostly on arXiv (e.g. parts of AI) are therefore undercounted.`,
  `Topics are assigned by OpenAlex's classifier, which can mislabel papers. ${last} counts can still rise slightly as late records are indexed.`,
  `Country % counts a paper once for every country among its authors, so shares can add up to more than 100%.`,
].map(t => `<li>${t}</li>`).join('');
</script>
</body>
</html>
"""


def write_dashboard(results: dict, path: Path) -> None:
    data = json.dumps(results, default=str).replace("</", "<\\/")
    path.write_text(TEMPLATE.replace("__DATA__", data), encoding="utf-8")
