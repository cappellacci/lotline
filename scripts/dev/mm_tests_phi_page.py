#!/usr/bin/env python3
# ruff: noqa: E501  (long lines are the HTML/CSS page template)
"""Results page for D-092 runs 9-11 (lumpy years, refit and §7): reports/mm-d092/run11-tests-phi/results.html.

    uv run python scripts/dev/mm_tests_phi_page.py

Reads run 5's and run 11's test files and runs 4 and 10's summaries; borrows the Lotline stylesheet from the
run-6 page.
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[2]
R = REPO / "reports" / "mm-d092"
OUT = R / "run11-tests-phi"
STYLE_FROM = R / "run6-results" / "d092-results.html"
EXTRA_CSS = """
.rng .old { stroke: var(--scenario-baseline); stroke-width: 4; stroke-linecap: round; }
.rng .new { stroke: var(--scenario-missing); stroke-width: 4; stroke-linecap: round; }
.rng .obs { fill: var(--ink); }
.rng .sw.old { background: var(--scenario-baseline); } .rng .sw.new { background: var(--scenario-missing); }
.chart .grid { stroke: var(--rule); stroke-width: 1; }
td.ok { color: var(--confidence-inside); font-weight: 600; } td.no { color: var(--confidence-outside); }
"""


def rows() -> list[dict]:
    """Totals scored in both runs: test C by state, and leave one state out for Oregon and Texas."""
    out = []
    for run, d in (("old", R / "run5-tests"), ("new", OUT)):
        c = pd.read_csv(d / "test_c_states.csv")
        for r in c.itertuples():
            out.append({"run": run, "label": f"{r.state}: no-reform places (test C)", **r._asdict()})
        lo = pd.read_csv(d / "loso_states.csv")
        lo = lo[(lo["model"] == "M") & lo["state"].isin(["OR", "TX", "NC"])]
        for r in lo.itertuples():
            out.append({"run": run, "label": f"{r.state}: fit places, state left out", **r._asdict()})
    return out


def range_chart(rs: list[dict]) -> str:
    """Log axis: each row's P10-P90 in both runs, with the observed total as a dot."""
    labels = list(dict.fromkeys(r["label"] for r in rs))
    W, left, right, row = 680, 250, 650, 30
    vals = [max(v, 1.0) for r in rs for v in (r["p10"], r["p90"], r["observed"])]
    lo, hi = math.floor(math.log10(min(vals))), math.ceil(math.log10(max(vals)))

    def sx(v):
        return left + (right - left) * (math.log10(max(v, 1.0)) - lo) / (hi - lo)

    g = []
    for e in range(lo, hi + 1):
        x = sx(10**e)
        g.append(
            f'<line x1="{x:.1f}" x2="{x:.1f}" y1="4" y2="{10 + len(labels) * row}" class="grid"/><text x="{x:.1f}" y="{24 + len(labels) * row}" class="tick" text-anchor="middle">{10**e:,}</text>'
        )
    for i, lab in enumerate(labels):
        y = 16 + i * row
        g.append(f'<text x="{left - 10}" y="{y + 4}" class="lab" text-anchor="end">{lab}</text>')
        obs = None
        for r in rs:
            if r["label"] != lab:
                continue
            yy = y - 5 if r["run"] == "old" else y + 5
            g.append(
                f'<line x1="{sx(r["p10"]):.1f}" x2="{sx(r["p90"]):.1f}" y1="{yy}" y2="{yy}" class="{r["run"]}"/>'
            )
            obs = r["observed"]
        g.append(f'<circle cx="{sx(obs):.1f}" cy="{y}" r="4.5" class="obs"/>')
    h = 34 + len(labels) * row
    return (
        f'<svg viewBox="0 0 {W} {h}" class="chart rng" role="img" aria-label="P10 to P90 ranges in runs 5 and 11 against observed totals">{"".join(g)}'
        f'<text x="{right}" y="{h - 2}" class="tick" text-anchor="end">2–4 unit buildings, log scale; dot = observed</text></svg>'
    )


def main() -> None:
    s5 = json.loads((R / "run5-tests" / "summary.json").read_text())
    s11 = json.loads((OUT / "summary.json").read_text())
    f4 = json.loads((R / "run4-refit" / "summary.json").read_text())
    f10 = json.loads((R / "run10-refit-phi" / "summary.json").read_text())
    m5, m11 = s5["models"]["M"], s11["models"]["M"]

    def cell(v):
        return "<td class='ok'>pass</td>" if v else "<td class='no'>fail</td>"

    tests = [
        ("A: new places (Houston only)", m5["test_a"]["pass"], m11["test_a"]["pass"]),
        ("B: parcel-roll check", m5["test_b"]["pass"], m11["test_b"]["pass"]),
        ("C: places with no reform", m5["test_c"]["pass"], m11["test_c"]["pass"]),
        ("Leave one state out", m5["loso"]["pass"], m11["loso"]["pass"]),
        ("Placebo (events 3 years early)", s5["placebo"]["pass"], s11["placebo"]["pass"]),
    ]
    trows = "".join(f"<tr><td>{n}</td>{cell(a)}{cell(b)}</tr>" for n, a, b in tests)
    cov5, cov11 = m5["place_coverage"]["coverage"], m11["place_coverage"]["coverage"]
    trows += f"<tr><td>Place coverage (target 0.60–0.95)</td><td class='no'>{cov5:.2f}</td><td class='ok'>{cov11:.2f}</td></tr>"
    c11 = m11["test_c"]
    vs_none = f10["paired_M_vs_none"]
    th4, th10 = f4["full"]["M"], f10["full"]["M"]
    html = f"""<title>Missing-middle lumpy-year refit</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=Public+Sans:wght@400;600;700&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&display=swap">
<style>{style()}{EXTRA_CSS}</style>
<main>
<header>
  <div class="eyebrow">Lotline · Missing middle · D-092 runs 9–11, refit with lumpy years · 15 Nov 2026</div>
  <h1>Honest ranges now hold up, and they are too wide to show the reform's effect</h1>
  <p class="lede">With each year's count allowed to be lumpy (φ = {f10["phi"]:.1f}, fitted on places the model never uses), the missing-middle model's ranges are calibrated: {cov11:.0%} of places land inside P10–P90, against 44% before. Leave one state out and the parcel-roll check now pass. Test C misses on one rule, Minnesota's three-place total. But the same honesty swamps the reform signal: the model beats "no effect" by only {vs_none["delta"]:.1f} (SE {vs_none["paired_se"]:.1f}), and the placebo still fails.</p>
</header>

<div class="tiles">
  <div class="tile"><b>{cov5:.2f} → {cov11:.2f}</b><span>place coverage, target 0.60–0.95</span></div>
  <div class="tile"><b>{c11["share_inside"]:.0%}</b><span>of no-reform places inside their range (bar 70%); MN total missed</span></div>
  <div class="tile"><b>{th4["per_1000"]:.2f} → {th10["per_1000"]:.2f}</b><span>θ per 1,000 lots a year; 90% range now {th10["low_per_1000"]:.2f}–{th10["high_per_1000"]:.1f}</span></div>
  <div class="tile"><b>+{vs_none["delta"]:.1f}</b><span>held-out gain over "no reform effect" (SE {vs_none["paired_se"]:.1f}); was +186 (SE 63)</span></div>
</div>

<section>
  <div class="num-tag">Finding 1</div>
  <h2>Two more tests pass, and coverage is on target</h2>
  <div class="scroll"><table><thead><tr><th>§7 test (model M)</th><th>Run 5: certain baseline</th><th>Run 11: lumpy years</th></tr></thead><tbody>{trows}</tbody></table></div>
  <p class="note">Test A has one place, Houston: 21 built, a range of 0–31, and a median of 0, so the within-×2 rule can't be met. Test C fails only on Minnesota's total: 32 built by three places against a P90 of 13.</p>
</section>

<section>
  <div class="num-tag">Finding 2</div>
  <h2>The ranges now reach the observed totals, because they are much wider</h2>
  <div class="legend"><span><i class="sw old" style="background:var(--scenario-baseline)"></i>Run 5, Poisson baseline</span><span><i class="sw new" style="background:var(--scenario-missing)"></i>Run 11, lumpy years</span></div>
  {range_chart(rows())}
  <p>Before, Ohio's and Texas's no-reform totals fell outside narrow ranges. Now they fall inside, as does Oregon left out. Oregon's range runs to nearly 10,000 against 703 built, which is too wide to guide a bill.</p>
</section>

<section>
  <div class="num-tag">Finding 3</div>
  <h2>The reform effect is no longer clear</h2>
  <p>Once a place's no-reform path can swing the way real places do, the cap rises in this data add little that the model can tell apart from noise. Moving every event three years early gives a five-year rate of {s11["placebo"]["placebo_r5"]:.5f}, more than the real dates' {f10["r5_M"]["r5"]:.5f}. Oregon and the other four states agree much more closely (θ {f10["full"]["M"]["per_1000"]:.2f} with Oregon, 1.08 without), so the 20× gap in run 4 was mostly the over-sure baseline.</p>
</section>

<section class="decision">
  <div class="num-tag">For Ben</div>
  <h2>Next: place types, then count projects instead of buildings</h2>
  <p>Place types (core city, suburb, town, as in ADU D-088) are already planned. They can explain part of the year-to-year spread and narrow every place's range without new data. The deeper fix is the unit: buildings arrive in projects, and run 1 found about 11 permit sources with parcel IDs. Counting projects would make the noise model match the mechanism. Nothing goes to config until you choose; the tool still runs D-059's θ = 0.12.</p>
</section>

<footer>
  <div>Runs: <code>mm_kappa_d092.py --form year</code> (φ = {f10["phi"]:.3f}, 941 pseudo-forecasts on unused places), <code>calibrate_mm_d092.py --phi</code> (M and C4, 93 fit places, 44 min), <code>mm_tests_d092.py --phi</code> (20,000 draws, seed 20261112). Pre-registered in D-092's deviations of 2026-11-15. Cached tables only; St. Paul and Ramsey not in the panel; nothing unblinded.</div>
  <div>Sources: <code>reports/mm-d092/run9-phi/</code>, <code>run10-refit-phi/</code> and <code>run11-tests-phi/</code> on branch <code>ws/mm-baseline-spread</code> (PR #436).</div>
</footer>
</main>
"""
    (OUT / "results.html").write_text(html)
    print(f"wrote {OUT / 'results.html'}")


def style() -> str:
    return re.search(r"<style>(.*?)</style>", STYLE_FROM.read_text(), re.S).group(1)


if __name__ == "__main__":
    main()
