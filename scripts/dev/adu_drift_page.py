# ruff: noqa: E501  (long lines are the HTML/CSS page template)
"""Build the D-091 results page from reports/adu-drift (totals.csv, place_scores.csv, summary.json).

Usage: python scripts/dev/adu_drift_page.py . reports/adu-drift/results.html
"""

import json
import math
import sys
from pathlib import Path

import pandas as pd

root, out = Path(sys.argv[1]), Path(sys.argv[2])
rep = root / "reports/adu-drift"
tot = pd.read_csv(rep / "totals.csv")
ps = pd.read_csv(rep / "place_scores.csv", dtype={"geoid": str})
summ = json.loads((rep / "summary.json").read_text())
tokens = (root / "docs/build/identity/tokens.css").read_text()
ev, vd = summ["evidence"], summ["verdict"]
STATE = {"MN": "Minnesota", "NC": "North Carolina", "TX": "Texas", "OR": "Oregon"}
SCORED = ("MN", "NC", "TX", "OR")
W, LW = 640, 150


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


h = ps[ps["class"] == "history"]
th = tot[tot.line == "history"]


def pv(var, f, col):
    return h[(h.variant == var) & (h.forecaster == f)].set_index("geoid")[col]


def range_chart():
    """P10-P90 bars with the P50 tick and the observed total, per state, without and with drift, log scale."""
    rows = []
    for s in SCORED:
        for f in ("F0", "F1"):
            for var in ("none", "drift"):
                r = th[(th.state == s) & (th.forecaster == f) & (th.variant == var)].iloc[0]
                rows.append((s, f, var, r))
    lo, hi = math.log(30), math.log(20000)
    top, rh, gap = 16, 15, 14
    n_groups = len(SCORED)
    h_ = top + n_groups * (4 * rh + gap) + 34

    def sx(v):
        v = min(max(v, math.exp(lo)), math.exp(hi))
        return LW + (math.log(v) - lo) / (hi - lo) * (W - LW - 16)

    g = [
        f'<svg viewBox="0 0 {W} {h_}" class="chart" role="img" aria-label="State totals: ranges without and with drift">'
    ]
    for t in (30, 100, 300, 1000, 3000, 10000):
        g.append(f'<line x1="{sx(t):.1f}" x2="{sx(t):.1f}" y1="{top - 6}" y2="{h_ - 30}" class="grid"/>')
        g.append(f'<text x="{sx(t):.1f}" y="{h_ - 14}" class="tick" text-anchor="middle">{t:,}</text>')
    y = top
    for s in SCORED:
        obs = rows[[r[0] for r in rows].index(s)][3].observed
        y0 = y
        for _, f, var, r in [q for q in rows if q[0] == s]:
            yy = y + rh / 2
            cls = f"{f.lower()} {'dr' if var == 'drift' else 'nd'}"
            lab = f"{f} {'+ drift' if var == 'drift' else 'no drift'}"
            g.append(f'<text x="{LW - 8}" y="{yy + 4}" class="lab small" text-anchor="end">{lab}</text>')
            g.append(
                f'<line x1="{sx(r.p10):.1f}" x2="{sx(r.p90):.1f}" y1="{yy}" y2="{yy}" class="bar {cls}"><title>{esc(STATE[s])} {lab}: P10 {r.p10:,.0f}, P50 {r.p50:,.0f}, P90 {r.p90:,.0f}</title></line>'
            )
            g.append(
                f'<line x1="{sx(r.p50):.1f}" x2="{sx(r.p50):.1f}" y1="{yy - 5}" y2="{yy + 5}" class="med"/>'
            )
            y += rh
        g.append(
            f'<line x1="{sx(obs):.1f}" x2="{sx(obs):.1f}" y1="{y0 - 2}" y2="{y + 2}" class="obs"><title>observed {obs:,.0f}</title></line>'
        )
        g.append(f'<text x="4" y="{y0 + 2 * rh + 4}" class="lab st">{esc(STATE[s])}</text>')
        y += gap
    g.append(
        f'<text x="{W - 16}" y="{h_ - 1}" class="tick" text-anchor="end">ADUs 2021–2025, places with history (log scale); bar P10–P90, tick median, red line observed</text>'
    )
    g.append("</svg>")
    return "".join(g)


def gain_chart(f):
    """Per-place log-score change with drift, sorted; the sum is dominated by one place."""
    d = (pv("drift", f, "log_score") - pv("none", f, "log_score")).sort_values()
    names = h.drop_duplicates("geoid").set_index("geoid")["name"]
    n = len(d)
    h_, top = 190, 14
    lo, hi = -5, 30
    bw = (W - 60) / n

    def sy(v):
        return top + (hi - max(min(v, hi), lo)) / (hi - lo) * (h_ - top - 34)

    g = [
        f'<svg viewBox="0 0 {W} {h_}" class="chart" role="img" aria-label="Per-place log score change, {f}">'
    ]
    for t in (-5, 0, 10, 20, 30):
        g.append(
            f'<line x1="44" x2="{W - 10}" y1="{sy(t):.1f}" y2="{sy(t):.1f}" class="{"zero" if t == 0 else "grid"}"/>'
        )
        g.append(f'<text x="38" y="{sy(t) + 4:.1f}" class="tick" text-anchor="end">{t:+d}</text>')
    for i, (gid, v) in enumerate(d.items()):
        x = 50 + i * bw
        y0, y1 = sy(0), sy(v)
        cls = "up" if v > 0 else "down"
        g.append(
            f'<rect x="{x:.1f}" y="{min(y0, y1):.1f}" width="{max(bw - 2, 1):.1f}" height="{max(abs(y1 - y0), 0.8):.1f}" class="{cls}"><title>{esc(names[gid])}: {v:+.2f}</title></rect>'
        )
        if v > hi:
            g.append(
                f'<text x="{x + bw / 2:.1f}" y="{top - 2}" class="tick" text-anchor="end">{esc(names[gid].replace(" city", ""))} {v:+.0f} ↑</text>'
            )
    g.append(
        f'<text x="{W - 10}" y="{h_ - 6}" class="tick" text-anchor="end">each bar one place with history, sorted; log score with drift − without</text>'
    )
    g.append("</svg>")
    return "".join(g)


def ev_row(label, fmt, vals, better=None):
    cells = "".join(f"<td class='num'>{fmt(v)}</td>" for v in vals)
    return f"<tr><td>{label}</td>{cells}</tr>"


bv = {f: ev[f]["by_variant"] for f in ("F0", "F1")}
ls = {f: (pv("none", f, "log_score").sum(), pv("drift", f, "log_score").sum()) for f in ("F0", "F1")}
cr = {f: (pv("none", f, "crps").sum(), pv("drift", f, "crps").sum()) for f in ("F0", "F1")}
gain = {f: ev[f]["drift"]["log_score_gain"] for f in ("F0", "F1")}
updown = {}
for f in ("F0", "F1"):
    d = pv("drift", f, "log_score") - pv("none", f, "log_score")
    updown[f] = (int((d > 0.01).sum()), int((d < -0.01).sum()), float(d.sum() - d.max()))
evidence = "".join(
    [
        "<tr><th></th><th>F0 no drift</th><th>F0 + drift</th><th>F1 no drift</th><th>F1 + drift</th></tr>",
        "<tr><td>Places inside their own P10–P90 (honest: ~80%)</td>"
        + "".join(
            f"<td class='num {'useful' if v == 'drift' else ''}'>{bv[f][v]['place_coverage'] * 100:.0f}%</td>"
            for f in ("F0", "F1")
            for v in ("none", "drift")
        )
        + "</tr>",
        "<tr><td>States whose total is inside P10–P90 (of 4)</td>"
        + "".join(
            f"<td class='num'>{sum(bv[f][v]['inside_states'].values())}</td>"
            for f in ("F0", "F1")
            for v in ("none", "drift")
        )
        + "</tr>",
        "<tr><td>Useful states (inside and within ×2; bar 3)</td>"
        + "".join(
            f"<td class='num {'useful' if sum(bv[f][v]['useful_states'].values()) >= 3 else ''}'>{sum(bv[f][v]['useful_states'].values())}</td>"
            for f in ("F0", "F1")
            for v in ("none", "drift")
        )
        + "</tr>",
        "<tr><td>Summed per-place log score (higher is better)</td>"
        + "".join(f"<td class='num'>{ls[f][i]:,.0f}</td>" for f in ("F0", "F1") for i in (0, 1))
        + "</tr>",
        "<tr><td>Gain with drift, and the 2-SE bar</td>"
        + "".join(
            f"<td></td><td class='num'>{gain[f][0]:+.0f} vs {2 * gain[f][1]:.0f}</td>" for f in ("F0", "F1")
        )
        + "</tr>",
        "<tr><td>Places better / worse with drift</td>"
        + "".join(f"<td></td><td class='num'>{updown[f][0]} / {updown[f][1]}</td>" for f in ("F0", "F1"))
        + "</tr>",
        "<tr><td>Gain without Portland</td>"
        + "".join(f"<td></td><td class='num'>{updown[f][2]:+.0f}</td>" for f in ("F0", "F1"))
        + "</tr>",
        "<tr><td>Summed per-place CRPS (lower is better)</td>"
        + "".join(f"<td class='num'>{cr[f][i]:,.0f}</td>" for f in ("F0", "F1") for i in (0, 1))
        + "</tr>",
        "<tr><td>Summed state-total CRPS (lower is better)</td>"
        + "".join(
            f"<td class='num'>{bv[f][v]['state_total_crps_sum']:,.0f}</td>"
            for f in ("F0", "F1")
            for v in ("none", "drift")
        )
        + "</tr>",
    ]
)

sig_rows = "".join(
    f"<tr><td>Without {STATE[s]}</td><td class='num'>{summ['sigma_loso'][f'F0 without {s}']:.3f} (×{math.exp(summ['sigma_loso'][f'F0 without {s}']):.1f})</td>"
    f"<td class='num'>{summ['sigma_loso'][f'F1 without {s}']:.3f} (×{math.exp(summ['sigma_loso'][f'F1 without {s}']):.1f})</td></tr>"
    for s in SCORED
)
sens_rows = []
for var in ("drift", "drift, shared by state", "drift, log-mean learned"):
    cells = "".join(
        f"<td class='num'>{bv[f][var]['place_coverage'] * 100:.0f}%</td><td class='num'>{sum(bv[f][var]['useful_states'].values())}</td><td class='num'>{bv[f][var]['state_total_crps_sum']:,.0f}</td>"
        for f in ("F0", "F1")
    )
    sens_rows.append(f"<tr><td>{esc(var)}</td>{cells}</tr>")
nc1 = th[(th.state == "NC") & (th.forecaster == "F1")].set_index("variant")

html = f"""<title>ADU forecast drift</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=Public+Sans:wght@400;600;700&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&display=swap">
<style>
/* Layout: one reading column; headline, stat row, decision panel, the evidence table Ben asked for, then findings with charts. */
{tokens}
body {{ background: var(--paper); color: var(--ink); font-family: var(--font-sans); font-size: 15px; line-height: 1.55;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); padding-block: var(--space-7); }}
main {{ max-width: 720px; margin: 0 auto; display: flex; flex-direction: column; gap: var(--space-7); }}
header, section {{ display: flex; flex-direction: column; gap: var(--space-3); min-width: 0; }}
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
.chart {{ width: 100%; height: auto; display: block; }}
.chart text {{ font-family: var(--font-sans); }}
.chart .grid {{ stroke: var(--rule); stroke-width: 1; }}
.chart .zero {{ stroke: var(--ink-faint); stroke-width: 1.5; }}
.chart .tick {{ fill: var(--ink-faint); font-size: 11px; font-family: var(--font-mono); }}
.chart .lab {{ fill: var(--ink-muted); font-size: 12px; }}
.chart .lab.small {{ font-size: 11px; }}
.chart .lab.st {{ fill: var(--ink); font-weight: 600; font-size: 12.5px; }}
.chart .bar {{ stroke-width: 7; stroke-linecap: butt; }}
.chart .bar.f0.nd {{ stroke: var(--ink-faint); opacity: .55; }} .chart .bar.f0.dr {{ stroke: var(--ink-faint); }}
.chart .bar.f1.nd {{ stroke: var(--scenario-adu); opacity: .45; }} .chart .bar.f1.dr {{ stroke: var(--scenario-adu); }}
.chart .med {{ stroke: var(--ink); stroke-width: 2; }}
.chart .obs {{ stroke: var(--confidence-outside); stroke-width: 2.5; }}
.chart .up {{ fill: var(--confidence-inside); }} .chart .down {{ fill: var(--confidence-outside); }}
.scroll {{ overflow-x: auto; }}
table {{ border-collapse: collapse; width: 100%; font-size: 13px; }}
table.wide {{ min-width: 600px; }}
th, td {{ text-align: left; padding: 6px 8px; border-bottom: 1px solid var(--rule); }}
th {{ font-weight: 600; color: var(--ink-muted); font-size: 12px; }}
td.num {{ font-family: var(--font-mono); font-variant-numeric: tabular-nums; }}
td.useful {{ color: var(--confidence-inside); font-weight: 600; }}
.note {{ font-size: 13px; color: var(--ink-muted); }}
code {{ font-family: var(--font-mono); font-size: 12.5px; }}
footer {{ border-top: 1px solid var(--rule); padding-top: var(--space-4); font-size: 13px; color: var(--ink-muted); display: flex; flex-direction: column; gap: var(--space-2); }}
</style>
<main>
<header>
  <div class="eyebrow">Lotline · D-091 ADU forecast drift · 14 Nov 2026</div>
  <h1>The drift makes the ranges honest; a gain in predictive power is not proven at the pre-set bar</h1>
  <p class="lede">D-090's forecasts were given one random multiplier per place for 2021–2025, its spread learned for each state from the other three. The bands now hold about 80% of places, as an honest 80% band should, and persistence with drift is useful in 3 of 4 states. The log score improves by a lot in total, but almost all of it is Portland; place by place, about as many get slightly worse as better.</p>
</header>

<div class="stats">
  <div class="stat"><b>58% → {bv["F0"]["drift"]["place_coverage"] * 100:.0f}%</b><span>places inside their own P10–P90, persistence (F1: → {bv["F1"]["drift"]["place_coverage"] * 100:.0f}%)</span></div>
  <div class="stat"><b>0 → {sum(bv["F0"]["drift"]["useful_states"].values())} of 4</b><span>states where persistence is useful, without → with drift (bar 3)</span></div>
  <div class="stat"><b>{gain["F0"][0]:+.0f}</b><span>log-score gain, persistence; the bar was 2 SE = {2 * gain["F0"][1]:.0f}. Without Portland {updown["F0"][2]:+.0f}</span></div>
  <div class="stat"><b>×{math.exp(summ["sigma_all_states_reported_only"]["F0"]):.1f}</b><span>one SD of drift, learned leaving each state out (folds ×{min(math.exp(summ["sigma_loso"][f"F0 without {s}"]) for s in SCORED):.1f}–×{max(math.exp(summ["sigma_loso"][f"F0 without {s}"]) for s in SCORED):.1f})</span></div>
</div>

<div class="decision">
  <span class="tag">Needs Ben's call</span>
  <p><b>D-091's rules, fixed before the run:</b></p>
  <ol>
    <li><b>Rule 1:</b> F1 with drift is useful in {vd["rule1_F1d_useful_states"]} of 4 (fails); <b>persistence with drift in {vd["rule1_F0d_useful_states"]} of 4 (passes).</b></li>
    <li><b>Rule 2:</b> F1 with drift beats persistence with drift by {vd["rule2_F1d_minus_F0d"][0]:+.1f}, bar {2 * vd["rule2_F1d_minus_F0d"][1]:.0f}: no.</li>
    <li><b>Rule 3, calibration:</b> {vd["rule3_coverage"]["F0"] * 100:.0f}% (persistence) and {vd["rule3_coverage"]["F1"] * 100:.0f}% (F1) of places inside their band, inside 65–95%: pass.</li>
    <li><b>Your condition, "does it improve predictive power":</b> the pre-set test (log-score gain over 2 paired SE) is <b>not met</b> for either forecaster. Calibration and per-place CRPS improve clearly; the log-score total does not clear its bar because one city carries it.</li>
  </ol>
  <p><b>The outcome D-091 fixed for this case</b> ("only persistence with drift passes"): the tool's no-reform range for a state with history is persistence with the drift band; a bill's effect is F1's ratio (with ÷ without the bill) applied to it, labelled as unchecked within ×2. Nothing is in the tool or config yet. To roll back, close PR #430.</p>
</div>

<section>
  <div class="num-tag">The evidence you asked for</div>
  <h2>With and without drift, side by side</h2>
  <div class="scroll"><table class="wide">{evidence}</table></div>
  <p class="note">σ is learned leaving each state out, so no state's own window sets its own band. With drift off, every place's draws and scores equal D-090's exactly (largest gap {summ["rollback_check_max_gap"]:.1e}). The median of d is 1, so each place's median is unchanged and the ×2 test cannot improve place by place.</p>
</section>

<section>
  <div class="num-tag">Finding 1</div>
  <h2>The ranges now reach the observed totals</h2>
  <p>Without drift every bar is a sliver and misses. With drift persistence's range holds the total in all four states; its median is within ×2 in three (Oregon is 0.47).</p>
  {range_chart()}
  <p class="note">Faint bars: no drift. Solid: with drift. Grey: persistence (F0). Blue: F1.</p>
</section>

<section>
  <div class="num-tag">Finding 2</div>
  <h2>Most of the log-score gain is one city</h2>
  <p>Persistence: {updown["F0"][0]} places better, {updown["F0"][1]} slightly worse. The losses are small (the largest is Bend, −2.5): where the old band already held what happened, a wider band spreads probability away from it. Portland's score alone rises by about 270, because without drift the observed total was far outside a very tight band. Remove Portland and the gain is {updown["F0"][2]:+.0f}, still large, but the paired SE is built from these same uneven gains, so the 2-SE bar is not met.</p>
  {gain_chart("F0")}
</section>

<section>
  <div class="num-tag">Finding 3</div>
  <h2>Independent drift lifts a state's median when one place dominates its errors</h2>
  <p>Each place keeps its median, but a state's total is a sum of skewed draws, so its median rises. For F1 in North Carolina, the total's median moved from {nc1.loc["none", "p50"]:,.0f} to {nc1.loc["drift", "p50"]:,.0f} (observed 790), because F1's σ learned without NC is the widest fold ({summ["sigma_loso"]["F1 without NC"]:.2f}). This is why F1's state-total CRPS gets worse while its per-place CRPS improves.</p>
  <div class="scroll"><table class="wide"><tr><th>Fold</th><th>σ, persistence</th><th>σ, F1</th></tr>{sig_rows}</table></div>
  <p class="note">F1's folds range more widely than persistence's, because F1's errors include how it priced rule changes in each state. On all four states together: persistence {summ["sigma_all_states_reported_only"]["F0"]:.3f}, F1 {summ["sigma_all_states_reported_only"]["F1"]:.3f} (reported only, never used).</p>
</section>

<section>
  <div class="num-tag">Finding 4</div>
  <h2>Sensitivities</h2>
  <div class="scroll"><table class="wide"><tr><th>Variant</th><th>F0 coverage</th><th>F0 useful</th><th>F0 total CRPS</th><th>F1 coverage</th><th>F1 useful</th><th>F1 total CRPS</th></tr>{"".join(sens_rows)}</table></div>
  <p class="note">One drift shared by every place in a state, the correlated bound, does as well or better on totals: persistence useful in 4 of 4. Learning a log-mean as well shifts every median up and makes things worse; the median-1 choice holds.</p>
</section>

<footer>
  <p>Built by <code>scripts/dev/adu_drift_page.py</code> from <code>reports/adu-drift/</code>. Method: D-091 in <code>docs/analysis_plan.md</code>, accepted 14 Nov 2026 with Ben's two conditions; code committed at d8429d88 before the run. D-090's fits and draws reused unchanged.</p>
  <p>A smoke run (500 draws) came first; only its status lines were seen. St. Paul is out; no <code>--unblind</code>. Nothing written to config.</p>
</footer>
</main>
"""
out.write_text(html)
print(f"wrote {out}")
