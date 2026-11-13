# ruff: noqa: E501  (long lines are the HTML/CSS page template)
"""Build the D-083 results page from reports/adu-covariate-screen (screen.csv, summary.json).

Usage: uv run python scripts/dev/adu_screen_page.py . reports/adu-covariate-screen/results.html
"""

import json
import sys
from pathlib import Path

import pandas as pd

root, out = Path(sys.argv[1]), Path(sys.argv[2])
rep = root / "reports/adu-covariate-screen"
res = pd.read_csv(rep / "screen.csv")
summ = json.loads((rep / "summary.json").read_text())
tokens = (root / "docs/build/identity/tokens.css").read_text()
SHORT = {
    "X1": "Owner-occupied share",
    "X2": "Homes built before 1960",
    "X3": "Detached single-family share",
    "X4": "New houses per 1,000 lots",
    "X5": "Median eligible lot size",
    "R1": "Place size (reference)",
    "R2": "Home value (reference)",
}
W, LW = 640, 200


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def beta_chart(version):
    d = res[res.version == version].reset_index(drop=True)
    lo, hi = -1.5, 1.5
    top, rh = 16, 30
    h = top + rh * len(d) + 36

    def sx(v):
        return LW + (max(min(v, hi), lo) - lo) / (hi - lo) * (W - LW - 20)

    g = [f'<svg viewBox="0 0 {W} {h}" class="chart" role="img" aria-label="beta by factor, {version}">']
    for t in (-1.5, -1, -0.5, 0, 0.5, 1, 1.5):
        g.append(
            f'<line x1="{sx(t):.1f}" x2="{sx(t):.1f}" y1="{top - 6}" y2="{h - 30}" class="{"zero" if t == 0 else "grid"}"/>'
        )
        g.append(f'<text x="{sx(t):.1f}" y="{h - 14}" class="tick" text-anchor="middle">{t:+g}</text>')
    for i, r in d.iterrows():
        y = top + rh * i + rh / 2
        cls = "cand" if r.get("verdict") == "candidate" else ""
        g.append(
            f'<text x="{LW - 10}" y="{y + 4}" class="lab {cls}" text-anchor="end">{esc(SHORT[r.factor])}</text>'
        )
        g.append(
            f'<line x1="{sx(r.beta_low):.1f}" x2="{sx(r.beta_high):.1f}" y1="{y}" y2="{y}" class="ci {cls}"/>'
        )
        g.append(f'<circle cx="{sx(r.beta):.1f}" cy="{y}" r="5" class="pt {cls}"/>')
    g.append(
        f'<text x="{W - 20}" y="{h - 1}" class="tick" text-anchor="end">β: log change in ADUs per eligible lot per SD of the factor (90% interval)</text>'
    )
    g.append("</svg>")
    return "".join(g)


def alpha_chart():
    d = res[res.version == "within"].reset_index(drop=True)
    top, rh = 10, 26
    h = top + rh * len(d) + 30
    mx = 0.30

    def sx(v):
        return LW + max(v, 0) / mx * (W - LW - 20)

    g = [f'<svg viewBox="0 0 {W} {h}" class="chart" role="img" aria-label="fall in alpha by factor">']
    for t in (0, 0.1, 0.2, 0.3):
        g.append(
            f'<line x1="{sx(t):.1f}" x2="{sx(t):.1f}" y1="{top - 4}" y2="{h - 26}" class="{"bar10" if t == 0.1 else "grid"}"/>'
        )
        g.append(f'<text x="{sx(t):.1f}" y="{h - 10}" class="tick" text-anchor="middle">{t:.0%}</text>')
    for i, r in d.iterrows():
        y = top + rh * i
        cls = "cand" if r.verdict == "candidate" else ""
        g.append(
            f'<text x="{LW - 10}" y="{y + 16}" class="lab {cls}" text-anchor="end">{esc(SHORT[r.factor])}</text>'
        )
        g.append(
            f'<rect x="{LW}" y="{y + 5}" width="{sx(r.alpha_drop) - LW:.1f}" height="14" class="bar {cls}"/>'
        )
        g.append(f'<text x="{sx(r.alpha_drop) + 6:.1f}" y="{y + 16}" class="val">{r.alpha_drop:.0%}</text>')
    g.append("</svg>")
    return "".join(g)


rows = []
for r in res[res.version == "within"].itertuples():
    v = {"candidate": "Candidate", "weak": "Weak", "no": "No"}[r.verdict]
    rows.append(
        f"<tr><th>{esc(SHORT[r.factor])}</th><td class='num'>{r.places}</td><td class='num'>{r.beta:+.2f} ({r.beta_low:+.2f}, {r.beta_high:+.2f})</td>"
        f"<td class='num'>{r.p_holm:.3f}</td><td class='num'>{r.alpha_drop:.0%}</td><td>{'yes' if r.sign_stable else 'no'}</td>"
        f"<td class='v {r.verdict}'>{v}</td></tr>"
    )
av = summ["availability"]

html = f"""<title>ADU place-factor screen</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=Public+Sans:wght@400;600;700&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&display=swap">
<style>
/* Layout: one reading column; headline, a decision panel, numbered findings each with a chart, then the table. */
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
.decision {{ background: var(--paper-raised); border: 1px solid var(--brass); border-radius: var(--radius-sm); padding: var(--space-5); display: flex; flex-direction: column; gap: var(--space-3); }}
.decision ol {{ margin: 0; padding-left: 1.3em; display: flex; flex-direction: column; gap: var(--space-2); }}
.tag {{ font-family: var(--font-mono); font-size: 11px; letter-spacing: .06em; text-transform: uppercase; background: var(--brass); color: var(--on-brass); padding: 2px 6px; border-radius: var(--radius-sm); align-self: flex-start; }}
.chart {{ width: 100%; height: auto; display: block; }}
.chart text {{ font-family: var(--font-sans); }}
.chart .grid {{ stroke: var(--rule); stroke-width: 1; }}
.chart .zero {{ stroke: var(--ink-faint); stroke-width: 1.5; }}
.chart .bar10 {{ stroke: var(--brass); stroke-width: 1.5; stroke-dasharray: 4 3; }}
.chart .tick, .chart .val {{ fill: var(--ink-faint); font-size: 11px; font-family: var(--font-mono); }}
.chart .lab {{ fill: var(--ink-muted); font-size: 12.5px; }}
.chart .lab.cand {{ fill: var(--ink); font-weight: 600; }}
.chart .ci {{ stroke: var(--ink-faint); stroke-width: 3; }}
.chart .ci.cand {{ stroke: var(--scenario-adu); }}
.chart .pt {{ fill: var(--ink-faint); }}
.chart .pt.cand {{ fill: var(--scenario-adu); }}
.chart .bar {{ fill: var(--rule); }}
.chart .bar.cand {{ fill: var(--scenario-adu); }}
.scroll {{ overflow-x: auto; }}
table {{ border-collapse: collapse; width: 100%; font-size: 13px; min-width: 560px; }}
th, td {{ text-align: left; padding: 6px 8px; border-bottom: 1px solid var(--rule); }}
thead th {{ font-weight: 600; color: var(--ink-muted); font-size: 12px; }}
td.num {{ font-family: var(--font-mono); font-variant-numeric: tabular-nums; }}
td.v.candidate {{ color: var(--confidence-inside); font-weight: 600; }}
.note {{ font-size: 13px; color: var(--ink-muted); }}
code {{ font-family: var(--font-mono); font-size: 12.5px; }}
footer {{ border-top: 1px solid var(--rule); padding-top: var(--space-4); font-size: 13px; color: var(--ink-muted); display: flex; flex-direction: column; gap: var(--space-2); }}
</style>
<main>
<header>
  <div class="eyebrow">Lotline · D-083 ADU screen · 13 Nov 2026</div>
  <h1>Renters and older homes: two factors that help explain where ADUs get built</h1>
  <p class="lede">We refitted the ADU model once for each place factor it doesn't use, and asked whether the factor explains why places with the same rules build so differently. Two factors pass the bar set before the run, both narrowly. Nothing in the model has changed.</p>
</header>

<div class="decision">
  <span class="tag">Needs Ben's call</span>
  <h2>Take owner share into the model?</h2>
  <ol>
    <li><b>Recommended:</b> first run a leave-one-place-out check, so we know no single city carries the owner-share effect. Then write a method entry that adds owner share, and maybe housing age, and score it on D-075's tests before any fit.</li>
    <li>Write the method entry now and skip the influence check.</li>
    <li>Leave the model as it is and report the screen as a finding.</li>
  </ol>
</div>

<section>
  <div class="num-tag">Finding 1</div>
  <h2>Places with more renters build more ADUs per eligible lot</h2>
  <p>A place about 15 points more owner-occupied builds roughly half as many ADUs per eligible lot, with the same rules and market. Owner share most likely stands in for how urban a place is and how much rental demand an extra unit meets. It is the only factor that also works across states: Minnesota's places are the most owner-occupied, the same direction as the model's Minnesota over-prediction.</p>
  {beta_chart("within")}
  <p class="note">Within-state version: one rate per state, so each factor is compared only between places in the same state. Blue marks the two candidates.</p>
</section>

<section>
  <div class="num-tag">Finding 2</div>
  <h2>Older housing helps within a state, but not between states</h2>
  <p>A place with about 17 points more homes built before 1960 builds about 1.8 times as many ADUs per eligible lot. That fits the garages, alleys and lot layouts of older neighbourhoods. In the pooled version, which can also compare states, its effect fades. Owner share grows stronger there instead.</p>
  {beta_chart("pooled")}
  <p class="note">Pooled version: one rate for all places.</p>
</section>

<section>
  <div class="num-tag">Finding 3</div>
  <h2>Each candidate explains a modest slice of the gap between places</h2>
  <p>The place-effect variance α measures how much places differ that the model can't explain. Owner share cuts it by 16% and housing age by 11%. The bar was 10%, marked by the dashed line. New-house building, lot size, place size and home value each move it by 4% or less.</p>
  {alpha_chart()}
</section>

<section>
  <div class="num-tag">Scorecard</div>
  <h2>Every factor screened</h2>
  <div class="scroll"><table>
    <thead><tr><th>Factor</th><th>Places</th><th>β per SD (90%)</th><th>Holm p</th><th>α falls</th><th>Sign holds without each state</th><th>Verdict</th></tr></thead>
    <tbody>{"".join(rows)}</tbody>
  </table></div>
  <p class="note">Not screened: HOA share ({av["X6"]["places"]} places; no roll has the field) and homestead share ({av["X7"]["places"]} of 64; Minnesota only). Seven places have no ACS place rows: six Minnesota townships and unincorporated Durham County. A candidate must clear all three bars: Holm p &lt; 0.10, α falls ≥ 10%, and the sign holds when each state is left out.</p>
</section>

<footer>
  <div>Sources: <code>reports/adu-covariate-screen/</code> (screen.csv, factors.csv, summary.json) and <code>src/lotline/model/adu_screen.py</code>, on branch <code>ws/adu-covariate-screen</code>. Method: D-083 in <code>docs/analysis_plan.md</code>.</div>
  <div>Run offline from cached data. St. Paul stays out. ACS, BPS and parcel rows went through the holdout filters, and nothing was unblinded.</div>
</footer>
</main>
"""
out.write_text(html)
print(out, len(html))
