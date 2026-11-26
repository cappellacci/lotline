#!/usr/bin/env python3
# ruff: noqa: E501  (long lines are the HTML/CSS page template)
"""Results page for D-092 run 7 (κ, the baseline's own spread): reports/mm-d092/run7-kappa/results.html.

    uv run python scripts/archive/mm_kappa_page.py

Reads run 7's summary.json and places.csv; borrows the Lotline stylesheet from the run-6 page.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "reports" / "mm-d092" / "run7-kappa"
STYLE_FROM = REPO / "reports" / "mm-d092" / "run6-results" / "d092-results.html"
STATES = {"MN": "Minnesota", "NC": "North Carolina", "OH": "Ohio", "TX": "Texas"}
EXTRA_CSS = """
.hist rect.bar { fill: var(--scenario-baseline); }
.hist rect.bar.near { fill: var(--confidence-inside); }
.chart .grid { stroke: var(--rule); stroke-width: 1; }
"""


def hist(d: pd.DataFrame) -> str:
    """Pseudo-forecasts by observed ÷ baseline (log2 bins of one doubling); the ×½–×2 band highlighted."""
    lr = np.log2((d["observed"] + 0.5) / (d["baseline"] + 0.5)).clip(-8, 8)
    edges = np.arange(-8, 9, 1.0)
    counts, _ = np.histogram(lr, bins=edges)
    W, H, left, right, top, bot = 640, 230, 40, 620, 12, 190
    cmax = int(np.ceil(counts.max() / 50) * 50)
    bw = (right - left) / len(counts)
    g = []
    for v in range(0, cmax + 1, 50):
        y = bot - (bot - top) * v / cmax
        g.append(
            f'<line x1="{left}" x2="{right}" y1="{y:.1f}" y2="{y:.1f}" class="grid"/><text x="{left - 6}" y="{y + 4:.1f}" class="tick" text-anchor="end">{v}</text>'
        )
    for i, c in enumerate(counts):
        x0 = left + i * bw
        h = (bot - top) * c / cmax
        near = " near" if edges[i] in (-1.0, 0.0) else ""
        g.append(
            f'<rect x="{x0 + 1:.1f}" y="{bot - h:.1f}" width="{bw - 2:.1f}" height="{h:.1f}" class="bar{near}"/>'
        )
    for v, lab in (
        (-8, "÷256 or less"),
        (-4, "÷16"),
        (-1, "÷2"),
        (0, "×1"),
        (1, "×2"),
        (4, "×16"),
        (8, "×256+"),
    ):
        x = left + (v + 8) * bw
        g.append(f'<text x="{x:.1f}" y="{bot + 16}" class="tick" text-anchor="middle">{lab}</text>')
    return (
        f'<svg viewBox="0 0 {W} {H}" class="chart hist" role="img" aria-label="Pseudo-forecasts by observed divided by baseline">'
        f'{"".join(g)}<text x="{right}" y="{H - 6}" class="tick" text-anchor="end">observed ÷ baseline, five-year totals (green: within ×2)</text></svg>'
    )


def main() -> None:
    s = json.loads((OUT / "summary.json").read_text())
    d = pd.read_csv(OUT / "places.csv", dtype={"geoid": str})
    style = re.search(r"<style>(.*?)</style>", STYLE_FROM.read_text(), re.S).group(1)
    k = s["kappa"]
    ratio = (d["observed"] + 0.5) / (d["baseline"] + 0.5)
    within = float(((ratio > 0.5) & (ratio < 2)).mean())
    zeros = float((d["observed"] == 0).mean())
    rows = [("Both origins (main)", k["main"]), ("2021 origin only", k["origin_2021_only"])] + [
        (STATES[st], k["by_state"][st]) for st in STATES
    ]
    ktab = "".join(
        f"<tr><td>{n}</td><td class='num'>{r['kappa']:.2f}</td><td class='num'>{r['low']:.2f}–{r['high']:.2f}</td><td class='num'>{r['places']}</td></tr>"
        for n, r in rows
    )
    rng = np.random.default_rng(1)
    w = rng.gamma(1 / k["main"]["kappa"], k["main"]["kappa"], 1_000_000)
    q = np.percentile(w, [10, 50, 90])
    big = d[d["baseline"] >= 85].copy()
    big["lr"] = np.log((big["observed"] + 0.5) / (big["baseline"] + 0.5)).abs()
    big = big.sort_values("lr", ascending=False).head(8)
    btab = "".join(
        f"<tr><td>{r.name.removesuffix(' city').removesuffix(' town')}, {r.state}</td><td class='num'>{r.origin}</td><td class='num'>{r.baseline:,.0f}</td><td class='num'>{r.observed:,.0f}</td></tr>"
        for r in big.itertuples()
    )
    html = f"""<title>Missing-middle baseline spread</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=Public+Sans:wght@400;600;700&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&display=swap">
<style>{style}{EXTRA_CSS}</style>
<main>
<header>
  <div class="eyebrow">Lotline · Missing middle · D-092 run 7, the baseline's own spread · 15 Nov 2026</div>
  <h1>A place's no-reform path is off by more than ×2 most of the time, so one spread number can't describe it</h1>
  <p class="lede">Runs 4–5 failed because each place's no-reform baseline was treated as certain. Run 7 measured how far baselines actually miss, on {s["kept_places"]} places the fit and tests never use. The miss is so large (κ = {k["main"]["kappa"]:.1f}) that a single gamma spread would forecast most places near zero. Two to four unit buildings arrive in projects, and a three-year baseline catches or misses a project by chance. The refit is on hold until the baseline itself is steadier.</p>
</header>

<div class="tiles">
  <div class="tile"><b>{within:.0%}</b><span>of five-year pseudo-forecasts land within ×2 of their baseline</span></div>
  <div class="tile"><b>{zeros:.0%}</b><span>saw no 2–4 unit building at all in five years</span></div>
  <div class="tile"><b>{d["observed"].sum():,.0f} vs {d["baseline"].sum():,.0f}</b><span>observed vs baseline, all places together: right on average</span></div>
  <div class="tile"><b>{q[1]:.2f}</b><span>the median place's multiplier at κ = {k["main"]["kappa"]:.1f} (P10 {q[0]:.0e}, P90 {q[2]:.1f})</span></div>
</div>

<section>
  <div class="num-tag">Finding 1</div>
  <h2>Right in total, far off place by place</h2>
  <p>Each bar counts pseudo-forecasts (a place at the 2016 or 2021 origin) by how its five-year count compared with its baseline. Only the two green bars are within a factor of two. The rest spread over both sides, with a long tail of places that built nothing.</p>
  {hist(d)}
</section>

<section>
  <div class="num-tag">Finding 2</div>
  <h2>κ is large in every state, largest in Texas</h2>
  <div class="scroll"><table><thead><tr><th>Fit</th><th>κ̂</th><th>90% interval</th><th>Pseudo-forecasts</th></tr></thead><tbody>{ktab}</tbody></table></div>
  <p class="note">κ is the variance of a place's rate multiplier, mean 1. κ = 0.5 would mean most places within ×2; at κ = {k["main"]["kappa"]:.1f}, 60% of places get a multiplier under 0.1.</p>
</section>

<section>
  <div class="num-tag">Finding 3</div>
  <h2>Big places miss because one project falls in or out of the baseline years</h2>
  <div class="scroll"><table><thead><tr><th>Place</th><th>Origin</th><th>Baseline</th><th>Observed</th></tr></thead><tbody>{btab}</tbody></table></div>
  <p>A burst in the three pre-years, multiplied by the place's growth index (capped at ×4), sets a baseline the next five years never reach. Places that land a project after the origin swing the other way.</p>
</section>

<section class="decision">
  <div class="num-tag">For Ben</div>
  <h2>Steady the baseline before refitting</h2>
  <p>Using κ = {k["main"]["kappa"]:.1f} would pass test C only because the ranges would cover almost anything. The proposal: pre-register a few baseline constructions (six pre-years, the state's growth index instead of the place's own, no growth index, and a per-year negative binomial for project lumpiness) and score them on these same uncoded places. Then take the best one's κ into the refit. These places are never used by the fit or the §7 tests, so nothing leaks.</p>
</section>

<footer>
  <div>Run: <code>scripts/dev/mm_kappa_d092.py</code>, origins 2016 and 2021, five-year horizon, test C's baseline construction (own growth, 3 pre-years, zero floor), no reform term. Uncoded MN, NC, OH and TX places, minus test C's 11; no fit, test, level or holdout place. Cached tables only; nothing unblinded.</div>
  <div>Sources: <code>reports/mm-d092/run7-kappa/</code> on branch <code>ws/mm-baseline-spread</code> (PR #436).</div>
</footer>
</main>
"""
    (OUT / "results.html").write_text(html)
    print(f"wrote {OUT / 'results.html'}")


if __name__ == "__main__":
    main()
