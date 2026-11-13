# ruff: noqa: E501  (long lines are the HTML/CSS page template)
"""Build the D-085 results page from reports/adu-time-trend (fits.csv, test_d_states.csv, tiers.csv, summary.json).

Usage: uv run python scripts/dev/adu_trend_page.py . reports/adu-time-trend/results.html
"""

import json
import math
import sys
from pathlib import Path

import pandas as pd

root, out = Path(sys.argv[1]), Path(sys.argv[2])
rep = root / "reports/adu-time-trend"
fits = pd.read_csv(rep / "fits.csv")
ds = pd.read_csv(rep / "test_d_states.csv")
tiers = pd.read_csv(rep / "tiers.csv")
summ = json.loads((rep / "summary.json").read_text())
tokens = (root / "docs/build/identity/tokens.css").read_text()
W, LW = 640, 170
STATE = {"MN": "Minnesota", "NC": "North Carolina", "TX": "Texas", "OR": "Oregon"}


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def ratio_chart(rows, series, label):
    """Dots of observed ÷ median per row for several forecasts, log scale, ×2 band shaded."""
    lo, hi = math.log(1 / 32), math.log(8)
    top, rh = 18, 34
    h = top + rh * len(rows) + 38

    def sx(v):
        v = min(max(v, math.exp(lo)), math.exp(hi))
        return LW + (math.log(v) - lo) / (hi - lo) * (W - LW - 20)

    g = [f'<svg viewBox="0 0 {W} {h}" class="chart" role="img" aria-label="{esc(label)}">']
    g.append(f'<rect x="{sx(0.5):.1f}" y="{top - 8}" width="{sx(2) - sx(0.5):.1f}" height="{h - 30 - top + 8}" class="band"/>')
    for t, s in ((1 / 32, "÷32"), (1 / 8, "÷8"), (0.5, "÷2"), (1, "×1"), (2, "×2"), (8, "×8")):
        g.append(f'<line x1="{sx(t):.1f}" x2="{sx(t):.1f}" y1="{top - 8}" y2="{h - 30}" class="{"zero" if t == 1 else "grid"}"/>')
        g.append(f'<text x="{sx(t):.1f}" y="{h - 14}" class="tick" text-anchor="middle">{s}</text>')
    for i, (name, vals) in enumerate(rows):
        y = top + rh * i + rh / 2
        g.append(f'<text x="{LW - 10}" y="{y + 4}" class="lab" text-anchor="end">{esc(name)}</text>')
        xs = [sx(v) for v in vals]
        g.append(f'<line x1="{min(xs):.1f}" x2="{max(xs):.1f}" y1="{y}" y2="{y}" class="move"/>')
        for (cls, _), x in zip(series, xs):
            g.append(f'<circle cx="{x:.1f}" cy="{y}" r="5" class="{cls}"/>')
    g.append(f'<text x="{W - 20}" y="{h - 1}" class="tick" text-anchor="end">observed ÷ forecast median, 2021–25 (shaded: within ×2)</text>')
    g.append("</svg>")
    return "".join(g)


def gamma_chart():
    rows = []
    for fold in ["all", "without MN", "without NC", "without OH", "without TX", "without OR"]:
        r = fits[(fits.variant == "central") & (fits.fold == fold) & (fits.form == "A+T")].iloc[0]
        rows.append(("All places" if fold == "all" else fold.replace("without", "Without"), r.gamma, r.gamma_low, r.gamma_high, fold in ("all", "without OR")))
    r = fits[(fits.variant == "early") & (fits.form == "A+T")].iloc[0]
    rows.append(("2016–20 only", r.gamma, r.gamma_low, r.gamma_high, False))
    lo, hi = -0.30, 0.05
    top, rh = 16, 28
    h = top + rh * len(rows) + 36

    def sx(v):
        return LW + (max(min(v, hi), lo) - lo) / (hi - lo) * (W - LW - 20)

    g = [f'<svg viewBox="0 0 {W} {h}" class="chart" role="img" aria-label="gamma by fit">']
    for t in (-0.30, -0.25, -0.20, -0.15, -0.10, -0.05, 0, 0.05):
        g.append(f'<line x1="{sx(t):.1f}" x2="{sx(t):.1f}" y1="{top - 6}" y2="{h - 30}" class="{"zero" if t == 0 else "grid"}"/>')
        g.append(f'<text x="{sx(t):.1f}" y="{h - 14}" class="tick" text-anchor="middle">{t:+.2f}</text>')
    for i, (name, b, bl, bh, main) in enumerate(rows):
        y = top + rh * i + rh / 2
        cls = "cand" if main else ""
        g.append(f'<text x="{LW - 10}" y="{y + 4}" class="lab {cls}" text-anchor="end">{esc(name)}</text>')
        g.append(f'<line x1="{sx(bl):.1f}" x2="{sx(bh):.1f}" y1="{y}" y2="{y}" class="ci {cls}"/>')
        g.append(f'<circle cx="{sx(b):.1f}" cy="{y}" r="5" class="pt {cls}"/>')
    g.append(f'<text x="{W - 20}" y="{h - 1}" class="tick" text-anchor="end">γ, log change in uptake per year (90% interval), Form A + trend</text>')
    g.append("</svg>")
    return "".join(g)


dec = summ["decisions"]
da, dp = dec["A vs A+T"], dec["A′ vs A′+T"]
full = fits[(fits.variant == "central") & (fits.fold == "all")].set_index("form")
lr = 2 * (full.loc["A+T"].loglik - full.loc["A"].loglik)
SERIES = [("pt-a", "A"), ("pt-p", "A+T flat"), ("pt-c", "A+T continued"), ("pt-k", "persistence")]
piv = ds.pivot_table(index="state", columns="forecast", values="obs_over_p50")
d_rows = [(f"{STATE[s]} ({int(ds[(ds.state == s)].places.iloc[0])})", [piv.loc[s, f] for _, f in SERIES]) for s in ("MN", "NC", "TX", "OR")]
ps = pd.read_csv(rep / "test_d_places_scores.csv")
mpls = ps[(ps.name == "Minneapolis city")].set_index("forecast")

trows = []
for s in ("MN", "NC", "TX", "OR"):
    for f in ("A", "A+T flat", "A+T continued", "A′", "A′+T flat", "persistence"):
        r = ds[(ds.state == s) & (ds.forecast == f)].iloc[0]
        u = "useful" if (r.inside and 0.5 <= r.obs_over_p50 <= 2) else ""
        trows.append(f"<tr><td>{STATE[s] if f == 'A' else ''}</td><td>{esc(f)}</td><td class='num'>{r.observed:,.0f}</td><td class='num'>{r.p10:,.0f}–{r.p50:,.0f}–{r.p90:,.0f}</td><td class='num {u}'>{r.obs_over_p50:.2f}</td></tr>")
ls = ps.pivot_table(index="geoid", columns="forecast", values="log_score").sum()
age = summ["outlook_rule_age"]

html = f"""<title>ADU time-trend test</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=Public+Sans:wght@400;600;700&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&display=swap">
<style>
/* Layout: one reading column; headline, a decision panel, numbered findings each with a chart, then the tier table. */
{tokens}
body {{ background: var(--paper); color: var(--ink); font-family: var(--font-sans); font-size: 15px; line-height: 1.55;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); padding-block: var(--space-7); }}
main {{ max-width: 720px; margin: 0 auto; display: flex; flex-direction: column; gap: var(--space-7); }}
header, section {{ display: flex; flex-direction: column; gap: var(--space-3); }}
.eyebrow, .num-tag {{ font-family: var(--font-mono); font-size: 12px; letter-spacing: .06em; text-transform: uppercase; color: var(--ink-muted); }}
.num-tag {{ color: var(--survey); }}
h1 {{ font-family: var(--font-serif); font-weight: 600; font-size: 32px; line-height: 1.15; margin: 0; text-wrap: balance; }}
h2 {{ font-family: var(--font-serif); font-weight: 600; font-size: 21px; line-height: 1.25; margin: 0; text-wrap: balance; }}
p {{ margin: 0; max-width: 65ch; }}
.lede {{ font-size: 17px; color: var(--ink-muted); }}
.stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: var(--space-3); }}
.stat {{ border-top: 2px solid var(--rule); padding-top: var(--space-2); }}
.stat b {{ display: block; font-family: var(--font-mono); font-size: 22px; font-weight: 500; }}
.stat span {{ font-size: 13px; color: var(--ink-muted); }}
.decision {{ background: var(--paper-raised); border: 1px solid var(--brass); border-radius: var(--radius-sm); padding: var(--space-5); display: flex; flex-direction: column; gap: var(--space-3); }}
.decision ol {{ margin: 0; padding-left: 1.3em; display: flex; flex-direction: column; gap: var(--space-2); }}
.tag {{ font-family: var(--font-mono); font-size: 11px; letter-spacing: .06em; text-transform: uppercase; background: var(--brass); color: var(--on-brass); padding: 2px 6px; border-radius: var(--radius-sm); align-self: flex-start; }}
.legend {{ display: flex; gap: var(--space-4); font-size: 13px; color: var(--ink-muted); align-items: center; }}
.dot {{ display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 6px; vertical-align: -1px; }}
.dot.a {{ background: var(--ink-faint); }} .dot.f {{ background: var(--scenario-adu); }} .dot.c {{ background: var(--brass); }} .dot.k {{ background: var(--survey); }}
.chart {{ width: 100%; height: auto; display: block; }}
.chart text {{ font-family: var(--font-sans); }}
.chart .grid {{ stroke: var(--rule); stroke-width: 1; }}
.chart .zero {{ stroke: var(--ink-faint); stroke-width: 1.5; }}
.chart .band {{ fill: var(--confidence-inside); fill-opacity: .10; }}
.chart .tick {{ fill: var(--ink-faint); font-size: 11px; font-family: var(--font-mono); }}
.chart .lab {{ fill: var(--ink-muted); font-size: 12.5px; }}
.chart .lab.cand {{ fill: var(--ink); font-weight: 600; }}
.chart .move {{ stroke: var(--rule); stroke-width: 3; }}
.chart .pt-a {{ fill: var(--ink-faint); }}
.chart .pt-p {{ fill: var(--scenario-adu); }}
.chart .pt-c {{ fill: var(--brass); }}
.chart .pt-k {{ fill: var(--survey); }}
.chart .ci {{ stroke: var(--ink-faint); stroke-width: 3; }}
.chart .ci.cand {{ stroke: var(--scenario-adu); }}
.chart .pt {{ fill: var(--ink-faint); }}
.chart .pt.cand {{ fill: var(--scenario-adu); }}
.scroll {{ overflow-x: auto; }}
table {{ border-collapse: collapse; width: 100%; font-size: 13px; min-width: 560px; }}
th, td {{ text-align: left; padding: 6px 8px; border-bottom: 1px solid var(--rule); }}
thead th {{ font-weight: 600; color: var(--ink-muted); font-size: 12px; }}
td.num {{ font-family: var(--font-mono); font-variant-numeric: tabular-nums; }}
td.useful {{ color: var(--confidence-inside); font-weight: 600; }}
.note {{ font-size: 13px; color: var(--ink-muted); }}
code {{ font-family: var(--font-mono); font-size: 12.5px; }}
footer {{ border-top: 1px solid var(--rule); padding-top: var(--space-4); font-size: 13px; color: var(--ink-muted); display: flex; flex-direction: column; gap: var(--space-2); }}
</style>
<main>
<header>
  <div class="eyebrow">Lotline · D-085 ADU time trend · 13 Nov 2026</div>
  <h1>A yearly trend fits the past ADU counts far better, but forecasts 2021–25 no better, so the model keeps no trend</h1>
  <p class="lede">D-085 asked two things: does uptake drift by calendar year, and can the model forecast the places it has seen? We added one shared yearly trend, and ran a new test: fit on 2016–20, forecast 2021–25. The trend explains a lot in sample, mostly Oregon's boom and fall, but it does not forecast better. A plain carry-forward of each place's own early rate does as well as any model form.</p>
</header>

<div class="stats">
  <div class="stat"><b>{full.loc["A+T"].gamma:+.3f}</b><span>γ a year, all places (90%: {full.loc["A+T"].gamma_low:+.3f} to {full.loc["A+T"].gamma_high:+.3f})</span></div>
  <div class="stat"><b>{lr:,.0f}</b><span>in-sample likelihood ratio for the trend (one number)</span></div>
  <div class="stat"><b>+{da["test_d_gain_t_over_base"]["gain"]:.1f}</b><span>test D log score, trend held flat over Form A (bar: 2 SE = {2 * da["test_d_gain_t_over_base"]["se"]:.1f})</span></div>
  <div class="stat"><b>{-da["base_over_persistence"]["gain"]:+.1f}</b><span>carry-forward over Form A on test D (SE {da["base_over_persistence"]["se"]:.1f})</span></div>
</div>

<div class="decision">
  <span class="tag">Decided by the pre-set rule</span>
  <h2>No trend, for either base form</h2>
  <ol>
    <li><b>Form A + trend:</b> {esc(da["decision"]["reason"])}.</li>
    <li><b>Form A′ + trend:</b> {esc(dp["decision"]["reason"])}.</li>
    <li>Continuing the trend past 2020 forecasts much worse than holding it flat ({da["continue_over_flat"]["gain"]:+.1f}, SE {da["continue_over_flat"]["se"]:.1f}), so "flat" was the version scored, as the rule says.</li>
  </ol>
  <p class="note">Nothing goes to config. The open call is still D-084 (adopt Form A′ or keep Form A); this result does not change it.</p>
</div>

<section>
  <div class="num-tag">Finding 1</div>
  <h2>The trend is mostly Oregon's boom and fall</h2>
  <p>Fitted on every place, uptake relative to the model falls about 12% a year. It stays near that when Minnesota, North Carolina, Ohio or Texas is left out. Without Oregon it shrinks to about 4% a year, and the likelihood gain drops from {lr:,.0f} to {2 * (fits[(fits.variant == "central") & (fits.fold == "without OR") & (fits.form == "A+T")].iloc[0].loglik - fits[(fits.variant == "central") & (fits.fold == "without OR") & (fits.form == "A")].iloc[0].loglik):.0f}. Oregon's large cities issued ADU permits at a peak in the late 2010s and fewer since. A shared trend mostly encodes that one boom.</p>
  {gamma_chart()}
  <p class="note">A rule-age term in place of the calendar trend (outlook only) is weaker: δ {age["delta"]:+.3f} a year of rule age, likelihood ratio {age["lr_vs_a_prime"]:.0f} against Form A′.</p>
</section>

<section>
  <div class="num-tag">Finding 2</div>
  <h2>Forecasting 2021–25 from 2016–20: no form is reliable, and the simplest forecast does as well</h2>
  <p>This is the scenario's own job: forecast places the model has already seen. Every form misses Minnesota badly, and only North Carolina lands within ×2 and inside the range. Holding the trend flat helps Texas and Oregon but not enough to clear the bar. Carrying each place's own 2016–20 rate forward scores {ls["persistence"]:.1f}, against Form A's {ls["A"]:.1f}.</p>
  <div class="legend"><span><i class="dot a"></i>Form A</span><span><i class="dot f"></i>+ trend, held flat</span><span><i class="dot c"></i>+ trend, continued</span><span><i class="dot k"></i>carry-forward</span></div>
  {ratio_chart(d_rows, SERIES, "test D observed over median by state")}
</section>

<section>
  <div class="num-tag">Finding 3</div>
  <h2>Minneapolis: the model predicts a huge jump at the 2021 reform, and none came</h2>
  <p>Fitted on 2016–20 alone, the share an owner-occupancy rule allows comes out at 0.1 (it is 1.0 on all years). So when Minneapolis dropped its owner-occupancy rule in 2021, the model expected uptake to rise about tenfold. It forecast {mpls.loc["A"].p50:,.0f} ADU permits for 2021–25; {mpls.loc["A"].observed:,.0f} were counted, fewer than the carry-forward's {mpls.loc["persistence"].p50:,.0f}. This is most of Minnesota's miss. It is also the question D-086 asks: how much a rule change moves uptake. Here the model's step is far too big, the opposite of Raleigh's case.</p>
</section>

<section>
  <div class="num-tag">Test D table</div>
  <h2>2021–25 totals by state</h2>
  <div class="scroll"><table>
    <thead><tr><th>State</th><th>Forecast</th><th>Observed</th><th>P10–P50–P90</th><th>Obs ÷ P50</th></tr></thead>
    <tbody>{"".join(trows)}</tbody>
  </table></div>
  <p class="note">Green ratios are inside the range and within ×2. Ohio has no fit year before 2024 and is not in test D. On the data-tier test, adding the trend changes no state's useful count; no form passes any tier.</p>
</section>

<footer>
  <div>The base forms match D-084 to the digit (Form A θ 0.7563 per 1,000, log-lik −1,347.71). Test D: 38 places in the 2016–20 fit, 37 forecast (MN 21, NC 10, OR 4, TX 2), 178 place-years. Each place's effect is updated from its own early counts. 20,000 draws, seed 20261111.</div>
  <div>Sources: <code>reports/adu-time-trend/</code>, <code>src/lotline/model/adu_trend.py</code>, on branch <code>ws/adu-time-trend</code>. Method: D-085 in <code>docs/analysis_plan.md</code>. Run offline from cached data. St. Paul stays out. Nothing was unblinded and nothing was written to config.</div>
</footer>
</main>
"""
out.write_text(html)
print(out, len(html))
