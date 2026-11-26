# ruff: noqa: E501  (long lines are the HTML/CSS page template)
"""Build the D-095 results page from reports/adu-reform-ratio.

Usage: uv run python scripts/archive/adu_reform_ratio_page.py . reports/adu-reform-ratio/results.html
"""

import json
import math
import sys
from pathlib import Path

import pandas as pd

root, out = Path(sys.argv[1]), Path(sys.argv[2])
rep = root / "reports/adu-reform-ratio"
s = json.loads((rep / "summary.json").read_text())
ev = pd.read_csv(rep / "events_scored.csv", dtype={"geoid": str})
prof = pd.read_csv(rep / "b_profile.csv")
tokens = (root / "docs/build/identity/tokens.css").read_text()
W = 660


def esc(x):
    return str(x).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def ratio_chart():
    """Per event: the engine's ratio (dot) and the observed after ÷ before rate (diamond), log scale."""
    rows = ev[(ev.y_before + ev.y_after) > 0].sort_values("ratio_engine")
    lw, top, rh = 170, 14, 30
    h = top + rh * len(rows) + 36
    lo, hi = math.log(0.05), math.log(50)

    def sx(v):
        return lw + (math.log(min(max(v, 0.05), 50)) - lo) / (hi - lo) * (W - lw - 20)

    g = [
        f'<svg viewBox="0 0 {W} {h}" class="chart" role="img" aria-label="engine ratio vs observed change, by event">'
    ]
    for t in (0.1, 0.3, 1, 3, 10, 30):
        g.append(
            f'<line x1="{sx(t):.1f}" x2="{sx(t):.1f}" y1="{top - 6}" y2="{h - 30}" class="{"zero" if t == 1 else "grid"}"/>'
        )
        g.append(f'<text x="{sx(t):.1f}" y="{h - 16}" class="tick" text-anchor="middle">×{t:g}</text>')
    for i, (_, r) in enumerate(rows.iterrows()):
        y = top + rh * i + 10
        g.append(
            f'<text x="0" y="{y + 4}" class="lab">{esc(r["name"].replace(" city", "").replace(" town", ""))} {int(r.year)}</text>'
        )
        g.append(
            f'<text x="{lw - 8}" y="{y + 4}" class="tick" text-anchor="end">{r.y_before:.0f} → {r.y_after:.0f}</text>'
        )
        g.append(
            f'<line x1="{sx(r.ratio_engine):.1f}" x2="{sx(r.observed_ratio):.1f}" y1="{y}" y2="{y}" class="link"/>'
        )
        g.append(f'<circle cx="{sx(r.ratio_engine):.1f}" cy="{y}" r="5" class="eng"/>')
        x = sx(r.observed_ratio)
        g.append(
            f'<path d="M{x:.1f} {y - 6} L{x + 6:.1f} {y} L{x:.1f} {y + 6} L{x - 6:.1f} {y} Z" class="obs"/>'
        )
    g.append(
        f'<text x="{W - 8}" y="{h - 1}" class="tick" text-anchor="end">after ÷ before, ADUs per eligible lot a year (log scale); counts before → after at left</text>'
    )
    g.append("</svg>")
    return "".join(g)


def b_chart():
    w, h, lw, top, bot = W, 190, 44, 12, 34
    b = prof["b"].to_numpy()
    y = prof["M"].to_numpy()
    y = y - y.max()
    ymin = -12

    def sx(v):
        return lw + (v - b.min()) / (b.max() - b.min()) * (w - lw - 12)

    def sy(v):
        return top + (max(v, ymin) / ymin) * (h - top - bot)

    g = [f'<svg viewBox="0 0 {w} {h}" class="chart" role="img" aria-label="profile of the ratio exponent b">']
    for t in (-2, -1, 0, 1, 2, 3):
        g.append(
            f'<line x1="{sx(t):.1f}" x2="{sx(t):.1f}" y1="{top}" y2="{h - bot}" class="{"zero" if t in (0, 1) else "grid"}"/>'
        )
        g.append(f'<text x="{sx(t):.1f}" y="{h - bot + 16}" class="tick" text-anchor="middle">{t}</text>')
    cut = -0.5 * 2.705543454095404
    g.append(f'<line x1="{lw}" x2="{w - 12}" y1="{sy(cut):.1f}" y2="{sy(cut):.1f}" class="cut"/>')
    pts = " ".join(f"{sx(bi):.1f},{sy(yi):.1f}" for bi, yi in zip(b, y, strict=True))
    g.append(f'<polyline points="{pts}" class="curve"/>')
    g.append(
        f'<text x="{sx(0):.1f}" y="{top + 10}" class="tick" text-anchor="middle">rules don\'t matter</text>'
    )
    g.append(f'<text x="{sx(1):.1f}" y="{top + 24}" class="tick" text-anchor="middle">engine\'s ratio</text>')
    g.append(
        f'<text x="{w - 12}" y="{h - 2}" class="tick" text-anchor="end">exponent b on the engine\'s ratio · dashed: 90% cut</text>'
    )
    g.append("</svg>")
    return "".join(g)


def table():
    out_rows = []
    for _, r in ev.iterrows():
        out_rows.append(
            f"<tr><td class='form'>{esc(r['name'])}</td><td>{int(r.year)}</td><td>{r.dose_before:.2f} → {r.dose_after:.2f}</td>"
            f"<td>{r.y_before:.0f} → {r.y_after:.0f}</td><td>×{r.ratio_engine:.2f}</td><td>×{r.ratio_refit:.2f}</td>"
            f"<td>×{r.observed_ratio:.2f}</td><td>{r.M_p10:.0f}–{r.M_p90:.0f}</td><td>{r.ls_M - r.ls_P:+.2f}</td></tr>"
        )
    return "".join(out_rows)


m = s["drift"]["M"]
mr = s["drift"]["Mr"]
nd = s["no_drift"]["M"]
r = ev.set_index("name")
zeros = int(((ev.y_before == 0) & (ev.y_after == 0)).sum())
contra = int(((ev.dose_after > ev.dose_before) & (ev.ratio_engine < 1)).sum())

html = f"""<title>ADU Reform Ratio Check</title>
<meta name="claude:viewport-fit-sides" content="cover">
<style>
{tokens}
body {{ background: var(--paper); color: var(--ink); font-family: var(--font-body, Inter, system-ui, sans-serif); font-size: 15px; line-height: 1.55; }}
.wrap {{ max-width: 760px; margin: 0 auto; padding-block: 32px 64px; padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); display: grid; gap: 28px; }}
h1, h2 {{ font-family: var(--font-display, "Space Grotesk", system-ui, sans-serif); text-wrap: balance; margin: 0; }}
h1 {{ font-size: 1.9rem; line-height: 1.15; }} h2 {{ font-size: 1.2rem; }}
.kicker {{ text-transform: uppercase; letter-spacing: .08em; font-size: .75rem; color: var(--ink-muted); }}
p {{ margin: 0; max-width: 65ch; }} section {{ display: grid; gap: 12px; }}
.cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; }}
.card {{ background: var(--paper-raised); border: 1px solid var(--rule); border-radius: 8px; padding: 14px 16px; display: grid; gap: 4px; }}
.card b {{ font-family: var(--font-display, "Space Grotesk", sans-serif); font-size: 1.6rem; }}
.card span {{ color: var(--ink-muted); font-size: .85rem; }}
.chart {{ width: 100%; height: auto; display: block; }}
.chart text {{ fill: var(--ink-muted); font-size: 11px; font-family: inherit; }}
.chart .lab {{ fill: var(--ink); font-size: 12px; }}
.grid {{ stroke: var(--rule); stroke-width: 1; }} .zero {{ stroke: var(--brass); stroke-dasharray: 4 3; stroke-width: 1.5; }}
.cut {{ stroke: var(--ink-faint); stroke-dasharray: 3 3; }} .curve {{ fill: none; stroke: var(--survey); stroke-width: 2.5; }}
.link {{ stroke: var(--rule); stroke-width: 3; }} .eng {{ fill: var(--survey); }} .obs {{ fill: var(--brass); }}
.legend {{ display: flex; flex-wrap: wrap; gap: 14px; font-size: .85rem; color: var(--ink-muted); }}
.scroll {{ overflow-x: auto; }}
table {{ border-collapse: collapse; width: 100%; font-variant-numeric: tabular-nums; font-size: .85rem; }}
th, td {{ padding: 6px 8px; border-bottom: 1px solid var(--rule); text-align: right; white-space: nowrap; }}
th {{ color: var(--ink-muted); font-weight: 500; font-size: .75rem; text-transform: uppercase; letter-spacing: .05em; }}
td.form, th.form {{ text-align: left; }}
ul {{ margin: 0; padding-left: 20px; display: grid; gap: 6px; max-width: 65ch; }}
.verdict {{ border-left: 4px solid var(--brass); padding: 10px 14px; background: var(--paper-raised); border-radius: 0 8px 8px 0; }}
.foot {{ color: var(--ink-faint); font-size: .8rem; }}
</style>
<div class="wrap">
<header style="display:grid;gap:8px">
  <div class="kicker">Lotline · ADU model · D-095 · 15 Nov 2026</div>
  <h1>When a city changed its ADU rules, did permits move the way the engine says?</h1>
  <p>The engine turns a place's own ADU rate into a reform rate by multiplying it by a ratio from the rules. We checked that ratio against the {s["events"]} places in {s["states"]} states whose coded rules changed while we were counting their ADUs: forecast the years after the change from the years before, with and without the ratio.</p>
</header>

<div class="verdict"><b>Reading: {esc(s["reading"])}.</b> The ratio helps a little (log score {m["gain_over_P"]["gain"]:+.1f}, 2 SE {2 * m["gain_over_P"]["se"]:.1f}), and the best scaling of it is ×{m["b"]:.1f} ({m["b_low"]:.2f}–{m["b_high"]:.2f}): consistent with the engine's ratio and not with "rules don't matter", but ten events, half with no ADUs at all, can't show it. Nothing changes in the engine.</div>

<div class="cards">
  <div class="card"><span>Raleigh 2021, by right</span><b>×{r.loc["Raleigh city", "observed_ratio"]:.0f}</b><span>{r.loc["Raleigh city", "y_before"]:.0f} → {r.loc["Raleigh city", "y_after"]:.0f} ADUs. The engine's ratio was ×{r.loc["Raleigh city", "ratio_engine"]:.1f}: right direction, too small. This one event carries most of the evidence.</span></div>
  <div class="card"><span>Greensboro 2024</span><b>×{r.loc["Greensboro city", "observed_ratio"]:.1f}</b><span>Engine ×{r.loc["Greensboro city", "ratio_engine"]:.1f}, close.</span></div>
  <div class="card"><span>Events with no ADUs before or after</span><b>{zeros} of {s["events"]}</b><span>Minnesota suburbs that built nothing either side: they can't tell the ratios apart.</span></div>
</div>

<section>
  <h2>Engine ratio vs what happened</h2>
  <div class="legend"><span><svg width="12" height="12"><circle cx="6" cy="6" r="5" class="eng"/></svg> engine's ratio (config rule shares)</span><span><svg width="12" height="12"><path d="M6 0 L12 6 L6 12 L0 6 Z" class="obs"/></svg> observed after ÷ before</span></div>
  {ratio_chart()}
  <p>Only events with at least one ADU are shown. Raleigh and Greensboro moved up about as the engine says or more; Minneapolis fell by half when the engine expected almost no change; College Station and Burnsville barely moved. Small counts (Cornelius 2 → 4) are noise.</p>
</section>

<section>
  <h2>How much should the ratio count?</h2>
  {b_chart()}
  <p>Each forecast's mean is the no-effect forecast × ratio^b. b = 1 is the engine as built; b = 0 means rule changes make no difference. The data put b at {m["b"]:.1f}, with an interval from {m["b_low"]:.2f} to {m["b_high"]:.2f}. With the refitted rule shares (each event's own place left out) it is {mr["b"]:.1f} ({mr["b_low"]:.2f}–{mr["b_high"]:.2f}).</p>
</section>

<section>
  <h2>A coding mismatch the check turned up</h2>
  <p>In {contra} of the 10 events, D-079's dose says the rules got looser while the engine's rule share says they got tighter. The clearest cases come from zoned coverage: Forest Lake's new rule is coded as covering about 6% of the city, Cottage Grove's 75%, while the rules before count as covering all of it. So "a newer, more specific rule" reads as a cut. This doesn't change the verdict, since those places built almost nothing, but the engine's ratio is only as good as the coding of before and after.</p>
</section>

<section>
  <h2>Every event</h2>
  <div class="scroll"><table>
  <tr><th class="form">Place</th><th>Year</th><th>Dose</th><th>ADUs before → after</th><th>Engine ratio</th><th>Refit ratio</th><th>Observed</th><th>Engine P10–P90</th><th>Log score vs no effect</th></tr>
  {table()}
  </table></div>
  <p class="foot">Forecasts from the before years only: rate ~ Gamma(Y + 0.5, lot-years) × drift (σ {s["inputs"]["sigma"]}, D-091), × the ratio for the engine and refit versions. Observed ratio uses the same + 0.5. Inside P10–P90: no effect {s["coverage"]["P"]["inside_p10_p90"]}/10, engine {s["coverage"]["M"]["inside_p10_p90"]}/10, refit {s["coverage"]["Mr"]["inside_p10_p90"]}/10. Without drift (sensitivity) the reading is "{esc(nd["reading"])}", but its paired SE ({nd["gain_over_P"]["se"]:.0f}) is dominated by Raleigh and Minneapolis, so it says little.</p>
</section>

<section>
  <h2>What this means</h2>
  <ul>
  <li><b>Keep the engine's ratio.</b> Nothing contradicts it, and the one big reform (Raleigh) went further than it predicts, not less.</li>
  <li><b>It is not proven either.</b> Ten events, five with no ADUs, and short after windows. The ×2 claim in D-093 stays unchecked.</li>
  <li><b>Worth fixing:</b> rules coded with a zoned coverage after a change but none before read as a tightening. Checking how coverage is coded for old rules would make the ratio more trustworthy wherever it is used.</li>
  </ul>
</section>

<p class="foot">Source: reports/adu-reform-ratio/ (scripts/archive/adu_reform_ratio.py, offline, St. Paul excluded, checked rule rows; engine rule shares m_o {s["inputs"]["m_owner"]}, m_x {s["inputs"]["m_other"]} from config). Method fixed in D-095 before scoring. Built by scripts/dev/adu_reform_ratio_page.py.</p>
</div>
"""
out.write_text(html)
print(f"wrote {out}")
