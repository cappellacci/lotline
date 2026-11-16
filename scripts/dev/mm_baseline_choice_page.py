#!/usr/bin/env python3
# ruff: noqa: E501  (long lines are the HTML/CSS page template)
"""Results page for D-092 run 8 (choosing the no-reform baseline): reports/mm-d092/run8-baseline/results.html.

    uv run python scripts/dev/mm_baseline_choice_page.py

Reads run 8's summary.json and candidates.csv; borrows the Lotline stylesheet from the run-6 page.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "reports" / "mm-d092" / "run8-baseline"
STYLE_FROM = REPO / "reports" / "mm-d092" / "run6-results" / "d092-results.html"
BUILD = {
    "C0": "3 pre-years, own growth (as now)",
    "C1": "6 pre-years, own growth",
    "C2": "6 pre-years, state growth",
    "C3": "6 pre-years, no growth",
}
NOISE = {"w": "one multiplier per place", "year": "lumpy year by year"}
EXTRA_CSS = """
.dots .pt { fill: var(--scenario-baseline); }
.dots .pt.year { fill: var(--scenario-missing); }
.dots .pt.chosen { stroke: var(--ink); stroke-width: 2; }
.dots .se { stroke: var(--ink-faint); stroke-width: 2; }
.chart .grid { stroke: var(--rule); stroke-width: 1; }
tr.chosen td { font-weight: 600; }
"""


def dots(t: pd.DataFrame, chosen: str) -> str:
    """Held-out log score against the best, with ±2 paired SE, one row per candidate."""
    W, left, right, row = 640, 230, 620, 26
    lo = min(-2000.0, float((t["vs_best"] - 2 * t["paired_se_vs_best"]).min()))

    def sx(v):
        return left + (right - left) * (v - lo) / (0 - lo)

    g = []
    for v in range(int(lo // 500) * 500 + 500, 1, 500):
        x = sx(v)
        g.append(
            f'<line x1="{x:.1f}" x2="{x:.1f}" y1="4" y2="{14 + len(t) * row - 8}" class="grid"/><text x="{x:.1f}" y="{14 + len(t) * row + 6}" class="tick" text-anchor="middle">{v:,}</text>'
        )
    for i, r in enumerate(t.itertuples()):
        y = 14 + i * row
        se = 2 * r.paired_se_vs_best
        cls = "pt year" if r.form == "year" else "pt"
        cls += " chosen" if r.candidate == chosen else ""
        g.append(
            f'<text x="{left - 10}" y="{y + 4}" class="lab" text-anchor="end">{r.candidate}: {NOISE[r.form]}</text>'
        )
        if se > 0:
            g.append(
                f'<line x1="{sx(max(lo, r.vs_best - se)):.1f}" x2="{sx(min(0, r.vs_best + se)):.1f}" y1="{y}" y2="{y}" class="se"/>'
            )
        g.append(f'<circle cx="{sx(r.vs_best):.1f}" cy="{y}" r="6" class="{cls}"/>')
    h = 14 + len(t) * row + 24
    return (
        f'<svg viewBox="0 0 {W} {h}" class="chart dots" role="img" aria-label="Held-out log score against the best candidate">{"".join(g)}'
        f'<text x="{right}" y="{h - 2}" class="tick" text-anchor="end">held-out log score minus the best (higher is better); line ±2 paired SE</text></svg>'
    )


def main() -> None:
    s = json.loads((OUT / "summary.json").read_text())
    t = pd.read_csv(OUT / "candidates.csv").sort_values("vs_best", ascending=False)
    chosen = s["choice"]["chosen"]
    c = t.set_index("candidate").loc[chosen]
    style = re.search(r"<style>(.*?)</style>", STYLE_FROM.read_text(), re.S).group(1)
    rows = "".join(
        f"<tr class='{'chosen' if r.candidate == chosen else ''}'><td>{r.candidate}</td><td>{BUILD[r.construction]}</td><td>{NOISE[r.form]}</td>"
        f"<td class='num'>{'φ' if r.form == 'year' else 'κ'} {r.param:.2f}</td><td class='num'>{r.vs_best:,.0f}</td>"
        f"<td class='num'>{r.paired_se_vs_best:,.0f}</td><td class='num'>{r.coverage_2021:.2f}</td></tr>"
        for r in t.itertuples()
    )
    yr_gain = float(t[t.form == "year"]["heldout"].mean() - t[t.form == "w"]["heldout"].mean())
    html = f"""<title>Missing-middle baseline choice</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=Public+Sans:wght@400;600;700&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&display=swap">
<style>{style}{EXTRA_CSS}</style>
<main>
<header>
  <div class="eyebrow">Lotline · Missing middle · D-092 run 8, choosing the baseline · 15 Nov 2026</div>
  <h1>Treating each year as lumpy fixes the baseline's ranges; the three-year baseline stays</h1>
  <p class="lede">Eight pre-registered baselines were fitted on 2016–20 and scored on 2021–25, on {s["score_places"]} places the fit and tests never use. Letting each year's count be lumpy (projects arrive in bursts) beats one multiplier per place under every construction. The rule keeps today's three-year baseline, now with a per-year spread of φ = {c["param"]:.1f}. Its ranges hold {c["coverage_2021"]:.0%} of outcomes, where 80% is the target and runs 4–5 managed 37%.</p>
</header>

<div class="tiles">
  <div class="tile"><b>{chosen}</b><span>chosen: 3 pre-years, own growth, lumpy year by year</span></div>
  <div class="tile"><b>{c["coverage_2021"]:.0%}</b><span>of 2021–25 outcomes inside P10–P90 (target 80%)</span></div>
  <div class="tile"><b>+{yr_gain:,.0f}</b><span>log score, lumpy years over a place multiplier (mean over constructions)</span></div>
  <div class="tile"><b>1.9 SE</b><span>the best scorer (C2-year) leads the chosen one by this much: close</span></div>
</div>

<section>
  <div class="num-tag">Finding 1</div>
  <h2>Lumpy years beat a place multiplier, whatever the window</h2>
  <p>Each dot is a candidate's held-out score against the best. The four per-year candidates sit together near the top, and the four place-multiplier candidates sit about 1,500 points lower. The ringed dot is the one the rule chose.</p>
  {dots(t, chosen)}
</section>

<section>
  <div class="num-tag">Finding 2</div>
  <h2>A longer window doesn't help; the state's growth index helps a little</h2>
  <div class="scroll"><table><thead><tr><th>Candidate</th><th>Baseline</th><th>Noise</th><th>Spread</th><th>vs best</th><th>Paired SE</th><th>Coverage</th></tr></thead><tbody>{rows}</tbody></table></div>
  <p class="note">The rule picks the simplest candidate within 2 paired SE of the best. C2-year leads C0-year by 197 against 2 × 103, so C0-year is kept, narrowly.</p>
</section>

<section class="decision">
  <div class="num-tag">For Ben</div>
  <h2>Next: put the lumpy-year form into the fit, then refit</h2>
  <p>Single-place ranges stay wide: half of all place-forecasts have a median under {c["median_pred_over_baseline"]:.0%} of the baseline, with the mean at the baseline. That is how 2–4 unit building behaves place by place, and state totals add up hundreds of places. The pre-registered next steps are to code the per-year negative binomial into the main likelihood, estimate φ on both origins, then refit M and C4 and rerun the §7 tests.</p>
</section>

<footer>
  <div>Run: <code>scripts/dev/mm_baseline_choice_d092.py</code>, pre-registered in commit 5890ce71 before any scoring code. Fit on the 2016 origin ({s["train_places"]} places), scored on 2021 ({s["score_places"]}); the same places for every candidate; coverage from 20,000 draws, seed 20261115. Cached tables only; nothing unblinded.</div>
  <div>Sources: <code>reports/mm-d092/run8-baseline/</code> on branch <code>ws/mm-baseline-spread</code> (PR #436).</div>
</footer>
</main>
"""
    (OUT / "results.html").write_text(html)
    print(f"wrote {OUT / 'results.html'}")


if __name__ == "__main__":
    main()
