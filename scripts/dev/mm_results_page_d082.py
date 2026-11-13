# ruff: noqa: E501  (long lines are the HTML/CSS page template)
"""Build the D-082 run-6 results page from the run-4 and run-5 report files (to scale, log axes).

Usage: uv run python scripts/dev/mm_results_page_d082.py . reports/mm-d082/run6-results/d082-results.html
"""

import json
import math
import sys
from pathlib import Path

import pandas as pd

root = Path(sys.argv[1])
out = Path(sys.argv[2])
r4, r5 = root / "reports/mm-d082/run4-refit", root / "reports/mm-d082/run5-tests"
fits = pd.read_csv(r4 / "fits.csv").set_index("fit")
s4 = json.loads((r4 / "summary.json").read_text())
s5 = json.loads((r5 / "summary.json").read_text())
loso = pd.read_csv(r5 / "loso_states.csv")
tc = pd.read_csv(r5 / "test_c_places.csv", dtype={"geoid": str})
tcs = pd.read_csv(r5 / "test_c_states.csv")
tb = pd.read_csv(r5 / "test_b_areas.csv")
ta = pd.read_csv(r5 / "test_a_places.csv")
tokens = (root / "docs/build/identity/tokens.css").read_text()

W = 640


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def logx(lo, hi, x0, x1):
    a, b = math.log10(lo), math.log10(hi)
    return lambda v: x0 + (math.log10(max(v, lo)) - a) / (b - a) * (x1 - x0)


def axis(sx, ticks, y, fmt=lambda t: f"{t:g}", top=20):
    g = []
    for t in ticks:
        x = sx(t)
        g.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{top}" y2="{y}" class="grid"/>')
        g.append(f'<text x="{x:.1f}" y="{y + 16}" class="tick" text-anchor="middle">{fmt(t)}</text>')
    return "".join(g)


def interval_rows(rows, lo, hi, ticks, unit, label_w=170, ref=None, fmt=lambda t: f"{t:g}"):
    """rows: list of dict(label, lo, mid, hi, obs=None, cls). Horizontal interval chart on a log scale."""
    rh, top = 30, 24
    h = top + rh * len(rows) + 34
    sx = logx(lo, hi, label_w, W - 20)
    g = [f'<svg viewBox="0 0 {W} {h}" role="img" class="chart">']
    g.append(axis(sx, ticks, h - 30, fmt, top=top - 8))
    if ref:
        for v, txt in ref:
            x = sx(v)
            g.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{top - 8}" y2="{h - 30}" class="ref"/>')
            g.append(f'<text x="{x + 4:.1f}" y="{top - 10}" class="reftxt">{esc(txt)}</text>')
    for i, r in enumerate(rows):
        y = top + rh * i + rh / 2
        g.append(
            f'<text x="{label_w - 10}" y="{y + 4}" class="lab" text-anchor="end">{esc(r["label"])}</text>'
        )
        x0, x1 = sx(r["lo"]), sx(r["hi"])
        g.append(
            f'<rect x="{x0:.1f}" y="{y - 6}" width="{max(x1 - x0, 2):.1f}" height="12" class="band {r.get("cls", "")}"/>'
        )
        if r.get("mid") is not None:
            xm = sx(r["mid"])
            g.append(f'<line x1="{xm:.1f}" x2="{xm:.1f}" y1="{y - 8}" y2="{y + 8}" class="mid"/>')
        if r.get("obs") is not None:
            xo = sx(r["obs"])
            inside = r["lo"] <= r["obs"] <= r["hi"]
            g.append(f'<circle cx="{xo:.1f}" cy="{y}" r="5" class="obs {"in" if inside else "out"}"/>')
    g.append(f'<text x="{W - 20}" y="{h - 2}" class="tick" text-anchor="end">{esc(unit)}</text>')
    g.append("</svg>")
    return "".join(g)


# 1. theta by model
F = s4["full"]
rows = []
for k, lab in [
    ("M", "M (main)"),
    ("C1", "C1 not-yet-treated"),
    ("C3", "C3 conditional z"),
    ("C4", "C4 level prior"),
    ("L", "L always-allowed level"),
]:
    f = F[k]
    rows.append(
        {
            "label": lab,
            "lo": f["low_per_1000"],
            "mid": f["per_1000"],
            "hi": f["high_per_1000"],
            "cls": "m" if k == "M" else "",
        }
    )
mo = fits.loc["M_without_OR"]
rows.append(
    {
        "label": "M without Oregon",
        "lo": mo.low_per_1000,
        "mid": mo.per_1000,
        "hi": mo.high_per_1000,
        "cls": "warn",
    }
)
chart_theta = interval_rows(
    rows,
    0.003,
    200,
    [0.01, 0.1, 1, 10, 100],
    "new 2–4 unit buildings per 1,000 eligible parcels per year (log)",
    ref=[(0.12, "D-059 adopted 0.12")],
)

# 2. LOSO (model M)
lm = loso[loso.model == "M"]
rows = [
    {
        "label": f"{r.state} ({r.fit_places} fit places)",
        "lo": max(r.p10, 0.5),
        "mid": max(r.p50, 0.5),
        "hi": max(r.p90, 0.5),
        "obs": max(r.observed, 0.5),
    }
    for r in lm.itertuples()
]
chart_loso = interval_rows(
    rows,
    0.5,
    3000,
    [1, 10, 100, 1000],
    "2–4 unit buildings, 5 years after the event, state total (log; 0 drawn at 0.5)",
)

# 3. Test C: per-place, sorted by P50
t = tc.sort_values("p50", ascending=False)
t = t[(t.p90 > 0) | (t.observed > 0)].head(18)
rows = [
    {
        "label": f"{r.name.replace(' city', '').replace(' town', '')} {r.state}",
        "lo": max(r.p10, 0.5),
        "mid": max(r.p50, 0.5),
        "hi": max(r.p90, 0.5),
        "obs": max(r.observed, 0.5),
    }
    for r in t.itertuples()
]
chart_c = interval_rows(
    rows, 0.5, 3000, [1, 10, 100, 1000], "2–4 unit buildings 2021–25, no reform (log; 0 drawn at 0.5)"
)
rows = [
    {
        "label": f"{r.state} total ({r.places} places)",
        "lo": r.p10,
        "mid": r.p50,
        "hi": r.p90,
        "obs": r.observed,
    }
    for r in tcs.itertuples()
]
chart_cs = interval_rows(rows, 2, 10000, [10, 100, 1000, 10000], "2–4 unit buildings 2021–25 (log)")

# 4. Test B
b = tb[tb.model == "M"]
rows = [
    {"label": f"{r.area} {r.permit_years}", "lo": r.p10, "mid": r.p50, "hi": r.p90, "obs": r.observed}
    for r in b.itertuples()
]
chart_b = interval_rows(
    rows,
    10,
    2000,
    [10, 100, 1000],
    "predicted 2–4 buildings (bar) vs lots that gained one in the rolls (dot), log",
)

# 5. Placebo
pl = s5["placebo"]
r5m = s4["r5_M"]
rows = [
    {
        "label": "Main event year",
        "lo": r5m["low"] * 1e3,
        "mid": r5m["r5"] * 1e3,
        "hi": r5m["high"] * 1e3,
        "cls": "m",
    },
    {
        "label": "Event moved 3 yrs early",
        "lo": pl["placebo_low"] * 1e3,
        "mid": pl["placebo_r5"] * 1e3,
        "hi": pl["placebo_high"] * 1e3,
        "cls": "warn",
    },
]
chart_pl = interval_rows(
    rows, 0.1, 2, [0.1, 0.2, 0.5, 1, 2], "five-year rate r5, per 1,000 eligible parcels (log)"
)

# scorecard
M = s5["models"]


def cell(v):
    return (
        '<td class="f">fail</td>'
        if v is False
        else ('<td class="p">pass</td>' if v is True else "<td>—</td>")
    )


sc = []
for k in ["M", "C1", "C3", "C4"]:
    m = M[k]
    pv = pl["pass"] if k == "M" else None
    sel = s5["selection"]["table"]
    d = next((x for x in sel if x["model"] == k), None)
    score = f"{d['delta']:+.1f} ({d['paired_se']:.1f})" if d else "—"
    sc.append(
        f"<tr><th>{k}</th>{cell(m['test_a']['pass'])}{cell(m['test_b']['pass'])}{cell(m['test_c']['pass'])}"
        f"<td class='num'>{m['tests_a_c_passed']}</td>{cell(m['loso']['pass'])}{cell(pv)}"
        f"<td class='num'>{m['place_coverage']['coverage']:.2f}</td><td class='num'>{score}</td></tr>"
    )
scorecard = "".join(sc)

h = ta[ta.model == "M"].iloc[0]
c_share = M["M"]["test_c"]["share_inside"]

html = f"""<title>Missing-middle model check</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=Public+Sans:wght@400;600;700&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&display=swap">
<style>
/* Layout: one reading column of numbered findings, each a headline + its chart; a decision panel up top. */
{tokens}
body {{ background: var(--paper); color: var(--ink); font-family: var(--font-sans); font-size: 15px; line-height: 1.55;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); padding-block: var(--space-7); }}
main {{ max-width: 720px; margin: 0 auto; display: flex; flex-direction: column; gap: var(--space-7); }}
header {{ display: flex; flex-direction: column; gap: var(--space-3); }}
.eyebrow {{ font-family: var(--font-mono); font-size: 12px; letter-spacing: .06em; text-transform: uppercase; color: var(--ink-muted); }}
h1 {{ font-family: var(--font-serif); font-weight: 600; font-size: 34px; line-height: 1.15; margin: 0; text-wrap: balance; }}
h2 {{ font-family: var(--font-serif); font-weight: 600; font-size: 22px; line-height: 1.25; margin: 0; text-wrap: balance; }}
p {{ margin: 0; max-width: 65ch; }}
.lede {{ font-size: 17px; color: var(--ink-muted); }}
section {{ display: flex; flex-direction: column; gap: var(--space-4); }}
.num-tag {{ font-family: var(--font-mono); color: var(--survey); font-size: 13px; }}
.decision {{ background: var(--paper-raised); border: 1px solid var(--brass); border-radius: var(--radius-sm); padding: var(--space-5); display: flex; flex-direction: column; gap: var(--space-3); }}
.decision h2 {{ font-size: 19px; }}
.decision ol {{ margin: 0; padding-left: 1.3em; display: flex; flex-direction: column; gap: var(--space-2); }}
.tag {{ font-family: var(--font-mono); font-size: 11px; letter-spacing: .06em; text-transform: uppercase; background: var(--brass); color: var(--on-brass); padding: 2px 6px; border-radius: var(--radius-sm); align-self: flex-start; }}
.tiles {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: var(--space-4); }}
.tile {{ border-top: 2px solid var(--ink); padding-top: var(--space-2); display: flex; flex-direction: column; gap: 2px; }}
.tile b {{ font-family: var(--font-mono); font-weight: 500; font-size: 24px; font-variant-numeric: tabular-nums; }}
.tile span {{ font-size: 13px; color: var(--ink-muted); }}
.chart {{ width: 100%; height: auto; display: block; }}
.chart text {{ font-family: var(--font-sans); }}
.chart .grid {{ stroke: var(--rule); stroke-width: 1; }}
.chart .tick {{ fill: var(--ink-faint); font-size: 11px; font-family: var(--font-mono); }}
.chart .lab {{ fill: var(--ink); font-size: 12px; }}
.chart .band {{ fill: var(--survey-band); stroke: var(--survey); stroke-width: 1; }}
.chart .band.m {{ fill: var(--survey); fill-opacity: .35; }}
.chart .band.warn {{ fill: var(--brass); fill-opacity: .25; stroke: var(--brass); }}
.chart .mid {{ stroke: var(--ink); stroke-width: 2; }}
.chart .obs {{ stroke: var(--paper); stroke-width: 1.5; }}
.chart .obs.in {{ fill: var(--confidence-inside); }}
.chart .obs.out {{ fill: var(--confidence-outside); }}
.chart .ref {{ stroke: var(--brass); stroke-width: 1.5; stroke-dasharray: 4 3; }}
.chart .reftxt {{ fill: var(--brass); font-size: 11px; font-family: var(--font-mono); }}
.legend {{ display: flex; flex-wrap: wrap; gap: var(--space-4); font-size: 13px; color: var(--ink-muted); }}
.legend i {{ display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 6px; vertical-align: -1px; }}
.legend .sw {{ border-radius: 0; width: 18px; background: var(--survey-band); border: 1px solid var(--survey); }}
.scroll {{ overflow-x: auto; }}
table {{ border-collapse: collapse; width: 100%; font-size: 13px; min-width: 560px; }}
th, td {{ text-align: left; padding: 6px 8px; border-bottom: 1px solid var(--rule); }}
thead th {{ font-weight: 600; color: var(--ink-muted); font-size: 12px; }}
td.num {{ font-family: var(--font-mono); font-variant-numeric: tabular-nums; }}
td.f {{ color: var(--confidence-outside); font-weight: 600; }}
td.p {{ color: var(--confidence-inside); font-weight: 600; }}
.note {{ font-size: 13px; color: var(--ink-muted); }}
code {{ font-family: var(--font-mono); font-size: 12.5px; }}
footer {{ border-top: 1px solid var(--rule); padding-top: var(--space-4); font-size: 13px; color: var(--ink-muted); display: flex; flex-direction: column; gap: var(--space-2); }}
</style>
<main>
<header>
  <div class="eyebrow">Lotline · D-082 runs 4–5 · 12 Nov 2026</div>
  <h1>The missing-middle model fails its own accuracy tests</h1>
  <p class="lede">We refit the missing-middle uptake model and three challengers, then held each one to the six checks set out before any number was seen. None of the four passes any of the three selection tests (A–C). The cause is mostly one thing: the model treats the no-reform baseline as known.</p>
</header>

<div class="tiles">
  <div class="tile"><b>0.63</b><span>θ for M, per 1,000 parcels a year (0.36–1.32)</span></div>
  <div class="tile"><b>0.034</b><span>θ without Oregon, about 1/20 as large</span></div>
  <div class="tile"><b>0 / 3</b><span>tests A–C passed, every model</span></div>
  <div class="tile"><b>{c_share:.0%}</b><span>of no-reform places inside their P10–P90 (bar: 70%)</span></div>
</div>

<div class="decision">
  <span class="tag">Needs Ben's call</span>
  <h2>Which way to take the model</h2>
  <p>The rule in D-082 §5 picks C4, because every model ties at zero tests passed and C4 scores 2.9 paired SE better than M. C4's θ is the same as M's (0.633 against 0.632). With every model failing, that pick carries no weight. Options:</p>
  <ol>
    <li><b>Recommended: give the baseline its own uncertainty.</b> Fit a place-level spread on the no-reform level from the no-reform places, then rerun runs 4–5. This is a method change to D-059 (b′), so it needs a dated deviation entry.</li>
    <li><b>Use the four-state θ (0.034) as the main value</b>, with Oregon as an outside check, in line with D-037's route one.</li>
    <li><b>Adopt M (or C4) as it stands</b> and disclose the test failures.</li>
  </ol>
  <p class="note">No value has been written to config. Any adopted value goes in its own PR.</p>
</div>

<section>
  <div class="num-tag">Finding 1</div>
  <h2>Oregon sets the rate. Without it, the rate drops about twentyfold.</h2>
  <p>86 of the 93 fit places are Oregon cities with an HB 2001 event. The challengers land close to M, except the always-allowed level L, which is too thin to pin down. With Oregon left out, θ is 0.034, below the 0.12 adopted for D-059.</p>
  {chart_theta}
  <div class="legend"><span><i class="sw"></i>90% range</span><span>black tick: fitted θ</span></div>
</section>

<section>
  <div class="num-tag">Finding 2</div>
  <h2>The baseline is too narrow, so places with no reform land outside their ranges.</h2>
  <p>Test C predicts 2021–25 for places that never changed their rules. The prediction is the place's own pre-period level and trend, with only Poisson noise around it. Real places move far more than that, in both directions. Reynoldsburg is predicted 144–176 and saw 5. Abilene is predicted 100–127 and saw 307.</p>
  {chart_c}
  <p class="note">The 18 no-reform places with the largest predictions are shown. All 43 are in <code>test_c_places.csv</code>.</p>
  {chart_cs}
  <div class="legend"><span><i style="background:var(--confidence-inside)"></i>observed, inside P10–P90</span><span><i style="background:var(--confidence-outside)"></i>observed, outside</span><span><i class="sw"></i>P10–P90</span></div>
</section>

<section>
  <div class="num-tag">Finding 3</div>
  <h2>Leaving out one state, the model misses Oregon and North Carolina.</h2>
  <p>Each state is predicted from a fit to the other four. Oregon is over-predicted: the P10 is 803 against 703 observed, and with θ from four states that prediction is almost all baseline. North Carolina, 2 observed against 7–36, is also missed, but has only 2 fit places, so the test does not count it.</p>
  {chart_loso}
</section>

<section>
  <div class="num-tag">Finding 4</div>
  <h2>A fake reform three years early still shows two thirds of the effect.</h2>
  <p>Part of what M calls a reform effect was already under way before the reform. This fits Finding 2: when the baseline misses a place's upward drift, the reform term picks it up.</p>
  {chart_pl}
</section>

<section>
  <div class="num-tag">Finding 5</div>
  <h2>The roll check compares two different counts.</h2>
  <p>Test B sets predicted new 2–4 unit buildings (BPS) against lots that gained a 2–4 unit building between two tax rolls. Franklin's 785 predicted buildings against 142 lots says most BPS buildings in Columbus are not lots changing class in the roll. Minneapolis goes the other way: conversions show in the roll, not in BPS. Until the two counts are lined up, this test cannot separate model error from the mismatch.</p>
  {chart_b}
  <p class="note">Test A had a single new place, Houston, now class S: 21 observed against P10–P90 of {h.p10:.0f}–{h.p90:.0f}. That is inside, but 3× the P50 of {h.p50:.0f}. One place cannot carry the test.</p>
</section>

<section>
  <div class="num-tag">Scorecard</div>
  <h2>Every test, every model</h2>
  <div class="scroll"><table>
    <thead><tr><th>Model</th><th>A new places</th><th>B roll check</th><th>C no-reform</th><th>A–C passed</th><th>Leave one state out</th><th>Placebo</th><th>Place coverage (0.60–0.95)</th><th>Score vs M (SE)</th></tr></thead>
    <tbody>{scorecard}</tbody>
  </table></div>
  <p class="note">Not run: the data-tier test (too few strong permit sources with post-event years) and challenger C2 (needs addresses, which the adapters drop). The 30-building hand check from run 1 is still open.</p>
</section>

<footer>
  <div>Sources: <code>reports/mm-d082/run4-refit/</code> and <code>reports/mm-d082/run5-tests/</code> on branch <code>ws/mm-run5</code> (PR #415, stacked on #414 → #410 → #392). Pass rules: <code>src/lotline/model/mm_tests.py</code>.</div>
  <div>Holdouts: St. Paul and Ramsey County stay blind, with no unblinding. Everything was run from cached data, with nothing downloaded.</div>
</footer>
</main>
"""
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(html)
print(out, len(html))
