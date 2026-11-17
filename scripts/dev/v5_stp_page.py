#!/usr/bin/env python3
# ruff: noqa: E501  (long lines are the HTML/CSS page template)
"""Results page for V5 St. Paul (D-098): reports/v5-stpaul/results.html.

    uv run python scripts/dev/v5_stp_page.py

Reads reports/v5-stpaul/score.json and posthoc_ramp.json; borrows the Lotline stylesheet from the run-6 page.
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "reports" / "v5-stpaul"
STYLE_FROM = REPO / "reports" / "mm-d092" / "run6-results" / "d092-results.html"
EXTRA_CSS = """
.rng .rg { stroke: var(--scenario-missing-middle); stroke-width: 8; stroke-linecap: round; opacity: .45; }
.rng .rg.frozen { opacity: .9; }
.rng .med { stroke: var(--ink); stroke-width: 2; }
.rng .obs { stroke: #c2410c; stroke-width: 2; stroke-dasharray: 5 3; }
.rng .obstxt { fill: #c2410c; font-size: 12px; }
"""


def chart(rows: list, obs: float) -> str:
    W, left, top, rh = 700, 300, 18, 34
    H = top + rh * len(rows) + 30
    lo, hi = math.log(5), math.log(500)
    sx = lambda v: left + (W - left - 16) * (math.log(max(v, 5)) - lo) / (hi - lo)  # noqa: E731
    g = []
    for v in (5, 10, 20, 50, 100, 200, 500):
        g.append(
            f'<line x1="{sx(v):.1f}" x2="{sx(v):.1f}" y1="{top - 8}" y2="{H - 26}" class="grid"/><text x="{sx(v):.1f}" y="{H - 10}" class="tick" text-anchor="middle">{v}</text>'
        )
    g.append(
        f'<line x1="{sx(obs):.1f}" x2="{sx(obs):.1f}" y1="{top - 12}" y2="{H - 26}" class="obs"/><text x="{sx(obs) + 4:.1f}" y="{top - 2}" class="obstxt">built: {obs:.0f}</text>'
    )
    for i, r in enumerate(rows):
        y = top + i * rh + rh / 2
        g.append(f'<text x="{left - 10}" y="{y + 4:.1f}" class="lab" text-anchor="end">{r["label"]}</text>')
        g.append(
            f'<line x1="{sx(r["p10"]):.1f}" x2="{sx(r["p90"]):.1f}" y1="{y:.1f}" y2="{y:.1f}" class="rg{" frozen" if i == 0 else ""}"><title>{r["label"]}: {r["p10"]:.0f}–{r["p90"]:.0f}, median {r["p50"]:.0f}</title></line>'
        )
        g.append(
            f'<line x1="{sx(r["p50"]):.1f}" x2="{sx(r["p50"]):.1f}" y1="{y - 7:.1f}" y2="{y + 7:.1f}" class="med"/>'
        )
    return f'<div class="scroll"><svg viewBox="0 0 {W} {H}" class="chart rng" role="img" aria-label="St. Paul 2024-2025: built against the frozen forecast and post-hoc variants">{"".join(g)}</svg></div>'


def main() -> None:
    s = json.loads((OUT / "score.json").read_text())
    ph = json.loads((OUT / "posthoc_ramp.json").read_text())
    p = s["primary"]["2024-2025"]
    rows = ph["rows"]
    names = {
        "D-055 values": "Old D-055 values (post-hoc)",
        "C4 as frozen": "Frozen: C4, half-way 4.0 years",
        "half 0.5": "C4's θ, half-way 0.5 year (post-hoc)",
        "half 1.0": "C4's θ, half-way 1.0 year (post-hoc)",
    }  # fmt: skip  (D-055 first: its label has "half 0.5")
    for r in rows:
        r["label"] = next(v for k, v in names.items() if k in r["label"])
    yr = "".join(
        f"<tr><td>{k}</td><td>{v['observed']:.0f}</td><td>{v['p10']:.0f}</td><td>{v['p50']:.0f}</td><td>{v['p90']:.0f}</td><td>{v['percentile']:.0f}</td><td>{v['crps_model']:.1f} vs {v['crps_no_reform']:.1f}</td></tr>"
        for k, v in s["primary"].items()
    )
    html = f"""<title>St. Paul blind test</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=Public+Sans:wght@400;600;700&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&display=swap">
<style>{style()}{EXTRA_CSS}</style>
<main>
<header>
  <div class="eyebrow">Lotline · Missing middle · V5 St. Paul blind test (D-098) · scored 16 Nov 2026</div>
  <h1>St. Paul built faster than the model said</h1>
  <p class="lede">After its 2023 reform allowed up to four homes on 55,269 single-family lots, St. Paul got {p["observed"]:.0f} new 2–4 unit buildings in 2024–25. The forecast frozen before we looked was {p["p10"]:.0f} to {p["p90"]:.0f}, median {p["p50"]:.0f}: a miss, at the {p["percentile"]:.0f}th percentile. The model's mature rate looks right; its timing doesn't. It assumed the reform takes four years to reach half speed, and St. Paul got there in about one.</p>
</header>

<div class="tiles">
  <div class="tile"><b>{p["observed"]:.0f}</b><span>2–4 unit buildings built in 2024–25 (about 6 a year before the reform)</span></div>
  <div class="tile"><b>{p["p10"]:.0f}–{p["p90"]:.0f}</b><span>the frozen forecast's range (median {p["p50"]:.0f}): missed</span></div>
  <div class="tile"><b>{p["crps_model"]:.1f} vs {p["crps_no_reform"]:.1f}</b><span>score against "no reform" (CRPS, lower is better): right direction, too small</span></div>
  <div class="tile"><b>0.85–1.09</b><span>mature rate per 1,000 lots St. Paul implies with a fast ramp; C4's is 1.04</span></div>
</div>

<section>
  <div class="num-tag">Finding 1</div>
  <h2>The frozen forecast missed high building in year one</h2>
  <div class="scroll"><table><thead><tr><th>Period</th><th>Built</th><th>P10</th><th>P50</th><th>P90</th><th>Percentile</th><th>CRPS: model vs no reform</th></tr></thead><tbody>{yr}</tbody></table></div>
  <p>St. Paul got 33 in 2024, the first full year, against about 6 a year in 2021–23. C4 puts only 1% of its mature rate into year one and 3% into year two, so it could not produce that jump. Homes in these buildings (123) were above their range too.</p>
</section>

<section>
  <div class="num-tag">Finding 2 · post-hoc</div>
  <h2>A fast ramp at C4's level would have caught it</h2>
  {chart(rows, p["observed"])}
  <p>Same frozen inputs, draws and seed; only the ramp or the values changed. These are checks made after the score was read, so they are reported, not a re-score. With C4's mature rate and a half-way point of one year (the low end of C4's own range), the median is 55. The old D-055 values missed too, for the opposite reason: a fast ramp but a level eight times lower.</p>
</section>

<section class="decision">
  <div class="num-tag">For Ben</div>
  <h2>Keep the slow ramp, or move to a fast one?</h2>
  <p>Charlotte (passed) and St. Paul (missed) are two blind cases. The fit pins the ramp poorly (1.0–6.0 years), and St. Paul points to the fast end. Changing the ramp would use St. Paul, so it needs a new dated entry, and St. Paul would no longer be a blind test for the changed model. Nothing in config has changed.</p>
</section>

<footer>
  <div>Frozen in #436 (<code>results/frozen/V5-MN-STPAUL.json</code>, code 9ee70aa, 4,000 draws, seed 20261108) before any outcome was read; scored by <code>v5_stp_score.py</code>, which regenerates the freeze first. Exposure D-013 disclosed. Sources: <code>reports/v5-stpaul/</code>.</div>
</footer>
</main>
"""
    (OUT / "results.html").write_text(html)
    print(f"wrote {OUT / 'results.html'}")


def style() -> str:
    return re.search(r"<style>(.*?)</style>", STYLE_FROM.read_text(), re.S).group(1)


if __name__ == "__main__":
    main()
