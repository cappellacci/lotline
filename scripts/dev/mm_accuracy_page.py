#!/usr/bin/env python3
# ruff: noqa: E501  (long lines are the HTML/CSS page template)
"""Missing-middle accuracy report: reports/mm-d092/accuracy/results.html.

    uv run python scripts/dev/mm_accuracy_page.py

Gathers results already on file; runs nothing and reads no permits:
- run 11's §7 tests for C4 (reports/mm-d092/run11-tests-phi/: test B rolls, test A, test C, leave one state out,
  place coverage, M against no effect, placebo);
- run 12's held-out coverage of the no-reform baseline on 468 unused places (reports/mm-d092/run12-types/);
- V5 Charlotte, blind, scored with D-055's values (reports/v5-charlotte/score.json);
- V5 St. Paul, blind, frozen and scored with C4 (reports/v5-stpaul/score.json);
- V9 Oregon, the frozen D-038 forecast (reports/v9-oregon-d055/mm_totals.csv).
Borrows the Lotline stylesheet from the run-6 page.
"""

from __future__ import annotations

import csv
import json
import math
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
R = REPO / "reports" / "mm-d092"
R11 = R / "run11-tests-phi"
OUT = R / "accuracy"
STYLE_FROM = R / "run6-results" / "d092-results.html"
MODEL = "C4"
EXTRA_CSS = """
.acc .rg { stroke: var(--scenario-missing-middle); stroke-width: 7; stroke-linecap: round; opacity: .45; }
.acc .rg.old { stroke: var(--ink-faint); }
.acc .med { stroke: var(--ink); stroke-width: 2; }
.acc .in { fill: var(--scenario-missing-middle); stroke: var(--bg, #fff); stroke-width: 1.5; }
.acc .out { fill: #c2410c; stroke: var(--bg, #fff); stroke-width: 1.5; }
.acc .grp { font-size: 11px; letter-spacing: .06em; text-transform: uppercase; fill: var(--ink-muted); }
.key { display: flex; gap: 1.2rem; font-size: .85rem; color: var(--ink-muted); flex-wrap: wrap; margin-top: .4rem; }
.key i { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: .35rem; vertical-align: -1px; }
.key .in { background: var(--scenario-missing-middle); } .key .out { background: #c2410c; }
.key .rg { width: 20px; height: 7px; border-radius: 4px; background: var(--scenario-missing-middle); opacity: .45; }
.verdict { display: inline-block; font: 600 .75rem/1 var(--font-mono, monospace); padding: .3rem .5rem; border-radius: 4px; border: 1px solid currentColor; margin-left: .4rem; vertical-align: 3px; }
.good { color: var(--scenario-missing-middle); } .mixed { color: var(--brass); } .weak { color: #c2410c; }
"""


def rows_of(name: str, model: str | None = MODEL) -> list[dict]:
    with open(R11 / name) as f:
        return [r for r in csv.DictReader(f) if model is None or r.get("model") == model]


def gather() -> tuple[list, dict]:
    s = json.loads((R11 / "summary.json").read_text())
    rows = []  # (group, label, observed, p10, p50, p90, note, old)
    for r in rows_of("test_b_areas.csv"):
        label = {"Wake": "Wake County towns", "Franklin": "Franklin County, OH", "Minneapolis": "Minneapolis",
                 "Met Council": "Twin Cities suburbs"}[r["area"]]  # fmt: skip
        rows.append(("Places that reformed", f"{label}, {r['permit_years']}", float(r["observed"]),
                     float(r["p10"]), float(r["p50"]), float(r["p90"]), f"{r['places']} places", False))  # fmt: skip
    for r in rows_of("test_a_places.csv"):
        rows.append(("Places that reformed", f"Houston, from {r['T']} (new to the fit)", float(r["observed"]),
                     float(r["p10"]), float(r["p50"]), float(r["p90"]), "test A", False))  # fmt: skip
    v5 = json.loads((REPO / "reports" / "v5-charlotte" / "score.json").read_text())["primary"]["2023-2025"]
    rows.append(("Places that reformed", "Charlotte area, 2023–25 (blind)", v5["observed"], v5["p10"], v5["p50"], v5["p90"],
                 "older D-055 values", True))  # fmt: skip
    sp = json.loads((REPO / "reports" / "v5-stpaul" / "score.json").read_text())["primary"]["2024-2025"]
    rows.append(("Places that reformed", "St. Paul, 2024–25 (blind, C4)", sp["observed"], sp["p10"], sp["p50"], sp["p90"],
                 "C4, frozen 15 Nov", False))  # fmt: skip
    for r in rows_of("test_c_states.csv", model=None):
        rows.append(("Statewide, no reform (test C)", f"{r['state']}: {r['places']} places with no reform", float(r["observed"]),
                     float(r["p10"]), float(r["p50"]), float(r["p90"]), "", False))  # fmt: skip
    for r in rows_of("loso_states.csv"):
        if r["state"] == "OR":
            rows.append(("A new state (left out of the fit)", "Oregon, from the other states' 7 places", float(r["observed"]),
                         float(r["p10"]), float(r["p50"]), float(r["p90"]), f"{r['fit_places']} places", False))  # fmt: skip
    with open(REPO / "reports" / "v9-oregon-d055" / "mm_totals.csv") as f:
        for r in csv.DictReader(f):
            if r["params"] == "D-038 (frozen)" and r["target"].startswith("headline (62 places), 2018-2025"):
                rows.append(("A new state (left out of the fit)", "Oregon 2018–25, blind (V9)", float(r["observed"]),
                             float(r["p10"]), float(r["p50"]), float(r["p90"]), "older D-038 values", True))  # fmt: skip
    return rows, s


def chart(rows: list) -> str:
    W, left, top, rh = 720, 250, 14, 24
    groups = list(dict.fromkeys(r[0] for r in rows))
    H = top + rh * (len(rows) + len(groups)) + 34
    lo, hi = math.log(1), math.log(20_000)
    sx = lambda v: left + (W - left - 16) * (math.log(max(v, 1.0)) - lo) / (hi - lo)  # noqa: E731
    g = []
    for v in (1, 10, 100, 1_000, 10_000):
        g.append(
            f'<line x1="{sx(v):.1f}" x2="{sx(v):.1f}" y1="{top - 4}" y2="{H - 28}" class="grid"/><text x="{sx(v):.1f}" y="{H - 12}" class="tick" text-anchor="middle">{"0–1" if v == 1 else f"{v:,}"}</text>'
        )
    y = top
    for grp in groups:
        y += rh
        g.append(f'<text x="8" y="{y - 6}" class="grp">{grp}</text>')
        for r in [r for r in rows if r[0] == grp]:
            _, label, obs, p10, p50, p90, note, old = r
            cy = y + rh / 2 - 4
            inside = p10 <= obs <= p90
            tip = f"{label}: observed {obs:,.0f}; range {p10:,.0f}–{p90:,.0f}, median {p50:,.0f}" + (
                f" ({note})" if note else ""
            )
            g.append(f'<text x="{left - 10}" y="{cy + 4:.1f}" class="lab" text-anchor="end">{label}</text>')
            g.append(
                f'<line x1="{sx(p10):.1f}" x2="{sx(p90):.1f}" y1="{cy:.1f}" y2="{cy:.1f}" class="rg{" old" if old else ""}"><title>{tip}</title></line>'
            )
            g.append(
                f'<line x1="{sx(p50):.1f}" x2="{sx(p50):.1f}" y1="{cy - 6:.1f}" y2="{cy + 6:.1f}" class="med"/>'
            )
            g.append(
                f'<circle cx="{sx(obs):.1f}" cy="{cy:.1f}" r="5" class="{"in" if inside else "out"}"><title>{tip}</title></circle>'
            )
            y += rh
    return f'<div class="scroll"><svg viewBox="0 0 {W} {H}" class="chart acc" role="img" aria-label="Observed missing-middle buildings against the model\'s ranges">{"".join(g)}</svg></div>'


def table(rows: list) -> str:
    body = "".join(
        f"<tr><td>{label}</td><td>{obs:,.0f}</td><td>{p50:,.0f}</td><td>{p10:,.0f}–{p90:,.0f}</td>"
        f"<td>{'inside' if p10 <= obs <= p90 else ('above' if obs > p90 else 'below')}</td>"
        f"<td>{'–' if obs == 0 or p50 == 0 else f'{p50 / obs:.1f}×'}</td><td>{note or MODEL}</td></tr>"
        for _, label, obs, p10, p50, p90, note, _ in rows
    )
    return f'<div class="scroll"><table><thead><tr><th>Test</th><th>Built</th><th>Model median</th><th>Model range (P10–P90)</th><th>Result</th><th>Median ÷ built</th><th>Notes</th></tr></thead><tbody>{body}</tbody></table></div>'


def main() -> None:
    rows, s = gather()
    c4 = s["models"][MODEL]
    cov = c4["place_coverage"]
    r12 = json.loads((R / "run12-types" / "summary.json").read_text())["coverage_2021"]["all"]
    pl = s["placebo"]
    oregon = next(r for r in rows if r[1].startswith("Oregon, from"))
    html = f"""<title>Missing-middle accuracy</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=Public+Sans:wght@400;600;700&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&display=swap">
<style>{style()}{EXTRA_CSS}</style>
<main>
<header>
  <div class="eyebrow">Lotline · Missing middle · Accuracy of the C4 model · 15 Nov 2026</div>
  <h1>How accurate is the missing-middle model?</h1>
  <p class="lede">Honest, but not sharp. When we check the model against what was actually built, the real count lands inside its range about 8 times in 10, which is what a P10–P90 range should do. But the ranges are wide (often 10-fold), single-place medians can miss by 3–6×, and the data can't yet cleanly separate the reform's own effect from ordinary ups and downs in building. For a new state, our one real test, Oregon, came in inside the range with the median 1.3× too high. C4's first blind test, St. Paul, missed: 55 built against 9–28, because the reform worked much faster than C4's ramp assumes.</p>
</header>

<div class="tiles">
  <div class="tile"><b>{cov["coverage"]:.0%}</b><span>of {cov["places"]} places land inside their P10–P90 range (target 60–95%)</span></div>
  <div class="tile"><b>{r12["Y1"]:.0%}</b><span>of {r12["places"]} places with no reform land inside, scored on 2021–25 held out</span></div>
  <div class="tile"><b>{oregon[2]:,.0f} vs {oregon[4]:,.0f}</b><span>Oregon, built vs predicted median, from the other states only (range {oregon[3]:,.0f}–{oregon[5]:,.0f})</span></div>
  <div class="tile"><b>Not clear</b><span>the reform's own effect: +5.0 against "no effect" (SE 3.4); the placebo test fails</span></div>
</div>

<section>
  <div class="num-tag">The evidence</div>
  <h2>Every test, built against predicted</h2>
  {chart(rows)}
  <div class="key"><span><i class="rg"></i>model's P10–P90 range (grey: older values)</span><span>| median</span><span><i class="in"></i>actually built, inside</span><span><i class="out"></i>actually built, outside</span><span>2–4 unit buildings, log scale</span></div>
  {table(rows)}
  <p class="note">Ranges are C4's (run 11, 20,000 draws), except Charlotte (frozen and scored blind with D-055's values) and Oregon's V9 row (frozen with D-038's). Counts are 2–4 unit buildings in Census permit data, or in county parcel rolls for the roll check.</p>
</section>

<section>
  <div class="num-tag">Goal 1</div>
  <h2>Estimating missing-middle buildings in a place <span class="verdict mixed">calibrated, wide</span></h2>
  <ul>
    <li><b>The ranges are honest.</b> Across every test, {cov["coverage"]:.0%} of {cov["places"]} places land inside their P10–P90 range. The no-reform baseline alone, scored held out on {r12["places"]} places it never saw, lands inside {r12["Y1"]:.0%} of the time.</li>
    <li><b>Single places are hard.</b> The parcel-roll check passes (Wake, Franklin, Minneapolis all inside), but Franklin County built 142 against a median of 483 (3.4× too high) and Minneapolis built 275 against a median of 42 (6.5× too low), each just inside its range.</li>
    <li><b>Why:</b> 34–44% of 2–4 unit buildings come in projects of 3 or more (run 13). Whether one big project lands in a place in five years decides its count, and nothing in our data can foresee that.</li>
    <li><b>Blind tests:</b> Charlotte passed with the older D-055 values (119 built against 89–172). St. Paul, frozen with C4 before we looked, <b>missed</b>: 55 built in 2024–25 against 9–28 (median 15). C4 assumes the reform takes 4 years to reach half speed; St. Paul got there in about one. Post-hoc, C4's mature rate with a one-year ramp gives a median of 55 (<code>reports/v5-stpaul/</code>).</li>
  </ul>
</section>

<section>
  <div class="num-tag">Goal 2</div>
  <h2>Projecting to a statewide total <span class="verdict mixed">totals inside, except Minnesota</span></h2>
  <ul>
    <li><b>Adding places up tightens the range</b> relative to the total, because one place's big project is offset by another's quiet year.</li>
    <li><b>No-reform state totals:</b> Texas built 4,515 (range 1,701–7,183) and Ohio 391 (45–1,266), both inside. Minnesota's three places built 32 against a top of 13: a miss, on small numbers (Rochester alone built 20).</li>
    <li><b>Not yet tested directly:</b> the statewide reform effect on its own. Every statewide number mixes the baseline (well tested) with the reform effect (weakly identified, below).</li>
  </ul>
</section>

<section>
  <div class="num-tag">Goal 3</div>
  <h2>Predicting what a new state would build <span class="verdict mixed">one real test, passed</span></h2>
  <ul>
    <li><b>Oregon held out.</b> Fitted on the other states' 7 reforming places only, the model predicts Oregon's 86 places: median {oregon[4]:,.0f} (range {oregon[3]:,.0f}–{oregon[5]:,.0f}) against {oregon[2]:,.0f} built. Inside, 1.3× high.</li>
    <li><b>The other states can't serve as tests:</b> each has 1–3 reforming places, and Minnesota's and Ohio's built none in the window.</li>
    <li><b>The earlier blind Oregon forecast (V9)</b>, frozen with D-038's values, was inside its range (1,753 built, 1,738–6,469) but 1.5× high and beat by "no reform". That was an older model; C4 hasn't had a blind new-state test, because Oregon is now in its fit.</li>
  </ul>
</section>

<section>
  <div class="num-tag">The weak spot</div>
  <h2>The reform's own effect isn't clearly detected <span class="verdict weak">weak</span></h2>
  <ul>
    <li>Held out, the model with a reform effect beats the same model with none by only 5.0 log points (SE 3.4), about 1.5 standard errors.</li>
    <li>The placebo fails: moving each reform three years early gives a <i>larger</i> five-year rate ({pl["placebo_r5"] * 1000:.2f} per 1,000 lots a year) than the real dates ({pl["main_r5"] * 1000:.2f}).</li>
    <li>So the scenario's added homes rest on an effect the counts are consistent with but can't pin down. That is why θ's range spans about 150-fold, and why the tool shows wide ranges, not single numbers.</li>
  </ul>
</section>

<section class="decision">
  <div class="num-tag">What would sharpen this</div>
  <h2>The ramp is the open question</h2>
  <p>St. Paul says the effect arrives fast: C4's level with a ramp near one year fits it, and C4's own fit allows 1.0–6.0 years. Whether to move the ramp is Ben's call, and a new dated entry, because it would use St. Paul. Beyond that, the honest limits stay: the outcome counts 2–4 unit buildings only (a floor for the Handbook's 2–6), and clustering means single-place forecasts will stay wide.</p>
</section>

<footer>
  <div>Built from results already on file; nothing was rerun and no permits were read. Sources: <code>reports/mm-d092/run11-tests-phi/</code>, <code>run12-types/</code>, <code>run13-projects/</code>, <code>reports/v5-charlotte/</code>, <code>reports/v9-oregon-d055/</code>. Page: <code>scripts/dev/mm_accuracy_page.py</code>.</div>
</footer>
</main>
"""
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "results.html").write_text(html)
    print(f"wrote {OUT / 'results.html'}")


def style() -> str:
    return re.search(r"<style>(.*?)</style>", STYLE_FROM.read_text(), re.S).group(1)


if __name__ == "__main__":
    main()
