# ruff: noqa: E501  (long lines are the HTML/CSS page template)
"""Build the ADU range-coverage results page from reports/adu-range-coverage.

Usage: uv run python scripts/dev/adu_range_coverage_page.py . reports/adu-range-coverage/results.html
"""

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

root, out = Path(sys.argv[1]), Path(sys.argv[2])
rep = root / "reports/adu-range-coverage"
pl = pd.read_csv(rep / "heldout_places.csv", dtype={"geoid": str})
cov = pd.read_csv(rep / "heldout_coverage.csv")
parts = pd.read_csv(rep / "state_width_parts.csv")
tdc = pd.read_csv(rep / "test_d_coverage.csv")
drc = pd.read_csv(rep / "drift_coverage.csv")
tokens = (root / "docs/build/identity/tokens.css").read_text()
NAME = {"MN": "Minnesota", "NC": "North Carolina", "TX": "Texas", "OR": "Oregon", "OH": "Ohio"}
W = 660


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def pit_hist(frame, label):
    """Ten bins of the randomized percentile; a calibrated forecast fills each to 10%."""
    p = frame["pit"].to_numpy()
    counts = np.histogram(p, bins=10, range=(0, 1))[0] / max(len(p), 1)
    w, h, top, bot, lw = 300, 150, 12, 26, 30
    bw = (w - lw - 8) / 10
    ymax = max(0.35, counts.max() * 1.1)

    def sy(v):
        return top + (1 - v / ymax) * (h - top - bot)

    g = [f'<svg viewBox="0 0 {w} {h}" class="chart" role="img" aria-label="{esc(label)}">']
    for t in (0, 0.1, 0.2, 0.3):
        g.append(f'<line x1="{lw}" x2="{w - 8}" y1="{sy(t):.1f}" y2="{sy(t):.1f}" class="grid"/>')
        g.append(f'<text x="{lw - 4}" y="{sy(t) + 4:.1f}" class="tick" text-anchor="end">{t:.0%}</text>')
    for i, c in enumerate(counts):
        cls = "tail" if i in (0, 9) else "mid"
        g.append(
            f'<rect x="{lw + i * bw + 1:.1f}" y="{sy(c):.1f}" width="{bw - 2:.1f}" height="{sy(0) - sy(c):.1f}" class="{cls}" rx="2"/>'
        )
    g.append(f'<line x1="{lw}" x2="{w - 8}" y1="{sy(0.1):.1f}" y2="{sy(0.1):.1f}" class="ideal"/>')
    g.append(f'<text x="{lw}" y="{h - 8}" class="tick">0 · below the range</text>')
    g.append(f'<text x="{w - 8}" y="{h - 8}" class="tick" text-anchor="end">above · 1</text>')
    g.append("</svg>")
    return "".join(g)


def parts_chart():
    rows = parts[(parts.form == "A+P") & (parts.state != "OH")]
    series = [
        ("full_ratio", "Everything", "s0"),
        ("no_state_multiplier_ratio", "Without the state level", "s1"),
        ("no_place_luck_ratio", "Without place luck", "s2"),
        ("shared_parameters_only_ratio", "Shared parameters only", "s3"),
    ]
    lw, top, gh, rh = 130, 12, 84, 17
    h = top + gh * len(rows) + 30
    lo, hi = 0, math.log(40)

    def sx(v):
        return lw + (math.log(max(v, 1)) - lo) / (hi - lo) * (W - lw - 50)

    g = [f'<svg viewBox="0 0 {W} {h}" class="chart" role="img" aria-label="range width by source">']
    for t in (1, 2, 5, 10, 20, 40):
        g.append(f'<line x1="{sx(t):.1f}" x2="{sx(t):.1f}" y1="{top - 4}" y2="{h - 26}" class="grid"/>')
        g.append(f'<text x="{sx(t):.1f}" y="{h - 10}" class="tick" text-anchor="middle">×{t}</text>')
    for i, (_, r) in enumerate(rows.iterrows()):
        y0 = top + gh * i
        g.append(f'<text x="0" y="{y0 + 14}" class="st">{NAME[r.state]}</text>')
        g.append(f'<text x="0" y="{y0 + 30}" class="tick">{int(r.places)} counted places</text>')
        for j, (col, _lab, cls) in enumerate(series):
            y = y0 + 4 + rh * j
            v = r[col]
            g.append(
                f'<rect x="{lw}" y="{y}" width="{sx(v) - lw:.1f}" height="{rh - 5}" rx="2" class="{cls}"/>'
            )
            g.append(f'<text x="{sx(v) + 5:.1f}" y="{y + rh - 7}" class="val">×{v:.1f}</text>')
    g.append(
        f'<text x="{W - 8}" y="{h - 1}" class="tick" text-anchor="end">top of range ÷ bottom (P90 ÷ P10) of the state total, log scale</text>'
    )
    g.append("</svg>")
    return "".join(g)


def cov_row(lab, r, base=0.8):
    c = r["pit_central_80"]
    cls = "good" if abs(c - base) <= 0.08 else ("wide" if c > base else "narrow")
    return (
        f"<tr><td class='form'>{esc(lab)}</td><td>{int(r['places'])}</td><td>{r['inside_p10_p90']:.0%}</td>"
        f"<td class='{cls}'>{c:.0%}</td><td>{r['pit_below_10']:.0%}</td><td>{r['pit_above_90']:.0%}</td></tr>"
    )


def cov_table():
    rows = []
    a = cov[cov.form == "A+P"].set_index("group")
    rows.append(cov_row("All 64 places, A + types", a.loc["all"]))
    rows.append(cov_row("Core cities", a.loc["core"]))
    rows.append(cov_row("Suburbs", a.loc["suburb"]))
    rows.append(cov_row("Form A, all places", cov[(cov.form == "A") & (cov.group == "all")].iloc[0]))
    for lab, frame, key in [
        ("Test D, A + types, no drift", tdc, ("form", "A+P")),
        ("D-091 own counts, no drift", drc, ("variant", "none")),
        ("D-091 own counts, with drift (the engine)", drc, ("variant", "drift")),
    ]:
        f = frame[frame[key[0]] == key[1]]
        if "forecaster" in f:
            f = f[f.forecaster == "F0"]
        rows.append(cov_row(lab, f.iloc[0]))
    return "".join(rows)


ap = pl[pl.form == "A+P"]
core_share = ap.loc[ap.type == "core", "observed"].sum() / ap["observed"].sum()

html = f"""<title>ADU Range Coverage</title>
<meta name="claude:viewport-fit-sides" content="cover">
<style>
{tokens}
:root {{ --s0: var(--survey); --s1: var(--tier-3); --s2: var(--tier-1); --s3: var(--tier-none); }}
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
.pair {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 16px; }}
.pair figure {{ margin: 0; display: grid; gap: 6px; min-width: 0; }} figcaption {{ font-size: .85rem; color: var(--ink-muted); }}
.chart {{ width: 100%; height: auto; display: block; }}
.chart text {{ fill: var(--ink-muted); font-size: 11px; font-family: inherit; }}
.chart .st {{ fill: var(--ink); font-weight: 600; font-size: 12.5px; }} .chart .val {{ fill: var(--ink); }}
.grid {{ stroke: var(--rule); stroke-width: 1; }} .ideal {{ stroke: var(--brass); stroke-dasharray: 4 3; stroke-width: 1.5; }}
.mid {{ fill: var(--survey); }} .tail {{ fill: var(--confidence-outside); }}
.s0 {{ fill: var(--s0); }} .s1 {{ fill: var(--s1); }} .s2 {{ fill: var(--s2); }} .s3 {{ fill: var(--s3); }}
.legend {{ display: flex; flex-wrap: wrap; gap: 14px; font-size: .85rem; color: var(--ink-muted); }}
.legend i {{ display: inline-block; width: 14px; height: 10px; border-radius: 2px; margin-right: 6px; vertical-align: middle; }}
.scroll {{ overflow-x: auto; }}
table {{ border-collapse: collapse; width: 100%; font-variant-numeric: tabular-nums; font-size: .9rem; }}
th, td {{ padding: 6px 8px; border-bottom: 1px solid var(--rule); text-align: right; }}
th {{ color: var(--ink-muted); font-weight: 500; font-size: .8rem; text-transform: uppercase; letter-spacing: .05em; }}
td.form, th.form {{ text-align: left; }}
td.good {{ color: var(--confidence-inside); font-weight: 600; }} td.wide {{ color: var(--confidence-edge); font-weight: 600; }} td.narrow {{ color: var(--confidence-outside); font-weight: 600; }}
ul {{ margin: 0; padding-left: 20px; display: grid; gap: 6px; max-width: 65ch; }}
.foot {{ color: var(--ink-faint); font-size: .8rem; }}
</style>
<div class="wrap">
<header style="display:grid;gap:8px">
  <div class="kicker">Lotline · ADU model · range check · 15 Nov 2026</div>
  <h1>Are the ADU ranges the right width?</h1>
  <p>Each state was left out in turn and every one of its 64 counted places predicted from the other states (A + place types, checked rule rows).
  We then asked where each place's actual count fell in its predicted range. If the ranges are honest, 80% of places land inside the middle 80%.</p>
</header>

<div class="cards">
  <div class="card"><span>Inside the middle 80%, all places</span><b>{cov[(cov.form == "A+P") & (cov.group == "all")].pit_central_80.iloc[0]:.0%}</b><span>About right, slightly narrow. The ranges are not oversized overall.</span></div>
  <div class="card"><span>Core cities inside the middle 80%</span><b>{cov[(cov.form == "A+P") & (cov.group == "core")].pit_central_80.iloc[0]:.0%}</b><span>Too wide; and they hold {core_share:.0%} of observed ADUs. Suburbs: {cov[(cov.form == "A+P") & (cov.group == "suburb")].pit_central_80.iloc[0]:.0%}, too narrow.</span></div>
  <div class="card"><span>Biggest source of a state's range</span><b>Place luck</b><span>In states with few counted places, one city's unexplained rate swings the total.</span></div>
</div>

<section>
  <h2>Where each place's actual count fell in its range</h2>
  <div class="pair">
    <figure>{pit_hist(ap[ap.type == "core"], "core cities")}<figcaption><b>16 core cities.</b> Piled in the middle: actual counts land near the median far more often than an honest range allows, so these ranges are too wide.</figcaption></figure>
    <figure>{pit_hist(ap[ap.type == "suburb"], "suburbs")}<figcaption><b>48 suburbs</b> (41 in Minnesota). Too many at the ends, purple: these ranges are a little too narrow.</figcaption></figure>
  </div>
  <p class="foot">Randomized percentile of the observed total over each place's fit years; a calibrated forecast fills each bar to the dashed 10% line. With 16 core cities the pattern is suggestive, not conclusive (about 1.5 standard errors).</p>
</section>

<section>
  <h2>What makes a state's range wide</h2>
  <div class="legend"><span><i style="background:var(--s0)"></i>Everything</span><span><i style="background:var(--s1)"></i>Without the unknown state level</span><span><i style="background:var(--s2)"></i>Without place-to-place luck</span><span><i style="background:var(--s3)"></i>Shared parameters only (θ, core term, rule multipliers)</span></div>
  {parts_chart()}
  <p>Removing each place's own unexplained rate shrinks a state's range the most: from about ×25 to ×5–9 in North Carolina, Texas and Oregon. Removing the unknown state level helps less (to ×15–20). The fitted parameters alone give only ×3–5. Minnesota's range is narrow because 43 places average their luck out.</p>
</section>

<section>
  <h2>Coverage across the checks we have</h2>
  <div class="scroll"><table>
  <tr><th class="form">Prediction</th><th>Places</th><th>Inside P10–P90</th><th>Middle 80% (randomized)</th><th>Below</th><th>Above</th></tr>
  {cov_table()}
  </table></div>
  <p class="foot">Target: 80% in the middle, 10% below, 10% above. Green within 8 points; amber too wide; purple too narrow. "Inside P10–P90" flatters small counts, since a place with 0 built is inside any range that starts at 0; the randomized column corrects for that. The test D and D-091 rows use the plain percentile.</p>
</section>

<section>
  <h2>What this suggests</h2>
  <ul>
  <li><b>Don't narrow the ranges across the board.</b> Over all places they are about right, a little narrow if anything.</li>
  <li><b>Test a separate place-luck spread for core cities and suburbs.</b> Core cities carry almost all ADUs and look too wide; suburbs look too narrow. Fitting one spread for each type would narrow the state totals honestly, if it holds up held out. It would need its own entry (D-094) before any fit.</li>
  <li><b>The cheapest narrowing is data: counts for the biggest core cities.</b> Where a city has its own counts, the engine already uses them (D-093), replacing that city's luck with what it actually built.</li>
  <li><b>Over time, drift was the fix.</b> Without it, forecasts of 2021–25 held about half the places in the middle 80%; with D-091's drift, which the engine now uses, about 80%.</li>
  </ul>
</section>

<p class="foot">Source: reports/adu-range-coverage/ (scripts/dev/adu_range_coverage.py, offline, St. Paul excluded; tier-1 held-out inputs as D-088's held-out log score). Built by scripts/dev/adu_range_coverage_page.py.</p>
</div>
"""
out.write_text(html)
print(f"wrote {out}")
