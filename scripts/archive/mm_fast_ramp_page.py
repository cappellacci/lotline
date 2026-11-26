#!/usr/bin/env python3
# ruff: noqa: E501  (long lines are the HTML/CSS page template)
"""Results page for D-100's fast-ramp sensitivity: reports/mm-d100/fast-ramp/results.html.

    uv run python scripts/archive/mm_fast_ramp_page.py

Reads compare.json (`mm_fast_ramp_run.py`); borrows the Lotline stylesheet from the D-092 run-6 page.
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path

from lotline.model.scenarios.mm import year_shape

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "reports" / "mm-d100" / "fast-ramp"
STYLE_FROM = REPO / "reports" / "mm-d092" / "run6-results" / "d092-results.html"
STATES = ("TX", "NC", "OH", "MN", "OR")
VARIANTS = (("main", "main", "C4, half-way 4.0 years (main result)"),
            ("fast_high", "mid", "half-way 1.0 year"),
            ("fast", "fast", "half-way 0.5 years (fast ramp)"))  # fmt: skip
EXTRA_CSS = """
.rng .main { stroke: var(--scenario-missing-middle); stroke-width: 6; stroke-linecap: round; }
.rng .mid { stroke: var(--ink-faint); stroke-width: 6; stroke-linecap: round; }
.rng .fast { stroke: var(--ink-muted); stroke-width: 6; stroke-linecap: round; stroke-dasharray: 2 3; }
.rng .med { fill: var(--ink); }
.bars .main { fill: var(--scenario-missing-middle); } .bars .fast { fill: var(--ink-muted); }
.key { display: flex; gap: 1.2rem; font-size: .85rem; color: var(--ink-muted); flex-wrap: wrap; }
.key i { display: inline-block; width: 18px; height: 6px; border-radius: 3px; margin-right: .35rem; vertical-align: 2px; }
.key .main { background: var(--scenario-missing-middle); } .key .mid { background: var(--ink-faint); }
.key .fast { background: repeating-linear-gradient(90deg, var(--ink-muted) 0 2px, transparent 2px 5px); }
"""


def ranges(c: dict) -> str:
    """P10-P90 of five-year net homes per state for the three ramps, log scale, median dots."""
    W, left, top, gh = 680, 50, 16, 58
    H = top + gh * len(STATES) + 30
    lo, hi = math.log(10), math.log(1_000_000)
    sx = lambda v: left + (W - left - 20) * (math.log(max(v, 10)) - lo) / (hi - lo)  # noqa: E731
    g = []
    for v in (10, 100, 1_000, 10_000, 100_000, 1_000_000):
        g.append(
            f'<line x1="{sx(v):.1f}" x2="{sx(v):.1f}" y1="{top - 6}" y2="{H - 26}" class="grid"/><text x="{sx(v):.1f}" y="{H - 10}" class="tick" text-anchor="middle">{v:,}</text>'
        )
    for i, st in enumerate(STATES):
        y0 = top + i * gh
        g.append(f'<text x="{left - 8}" y="{y0 + 22}" class="lab" text-anchor="end">{st}</text>')
        for j, (k, cls, lab) in enumerate(VARIANTS):
            p10, p50, p90, _ = c[st][k]["homes_net"]
            y = y0 + 8 + j * 14
            g.append(
                f'<line x1="{sx(p10):.1f}" x2="{sx(p90):.1f}" y1="{y}" y2="{y}" class="{cls}"><title>{st}, {lab}: {p10:,} to {p90:,}, median {p50:,}</title></line><circle cx="{sx(p50):.1f}" cy="{y}" r="3.5" class="med"/>'
            )
    return f'<div class="scroll"><svg viewBox="0 0 {W} {H}" class="chart rng" role="img" aria-label="Five-year net homes by state for three ramps">{"".join(g)}</svg></div>'


def shape_bars() -> str:
    """Share of the mature rate in each scenario year, half-way 4.0 against 0.5."""
    W, H, left, bottom = 680, 220, 50, 34
    main, fast = year_shape(4.0, 0.75), year_shape(0.5, 0.75)
    bw, gap = 34, 8
    slot = (W - left - 20) / 5
    sy = lambda v: (H - bottom) - (H - bottom - 14) * v  # noqa: E731
    g = []
    for v in (0, 0.25, 0.5, 0.75, 1.0):
        g.append(
            f'<line x1="{left}" x2="{W - 20}" y1="{sy(v):.1f}" y2="{sy(v):.1f}" class="grid"/><text x="{left - 8}" y="{sy(v) + 4:.1f}" class="tick" text-anchor="end">{v:.0%}</text>'
        )
    for t in range(5):
        x = left + slot * t + slot / 2
        for k, (arr, cls) in enumerate(((main, "main"), (fast, "fast"))):
            bx = x - bw - gap / 2 if k == 0 else x + gap / 2
            g.append(
                f'<rect x="{bx:.1f}" y="{sy(arr[t]):.1f}" width="{bw}" height="{sy(0) - sy(arr[t]):.1f}" class="{cls}" rx="2"><title>year {t + 1}: {arr[t]:.0%} of the mature rate</title></rect>'
            )
        g.append(f'<text x="{x:.1f}" y="{H - 12}" class="tick" text-anchor="middle">year {t + 1}</text>')
    return f'<div class="scroll"><svg viewBox="0 0 {W} {H}" class="chart bars" role="img" aria-label="Share of the mature rate by scenario year for the two ramps">{"".join(g)}</svg></div>'


def main() -> None:
    c = json.loads((OUT / "compare.json").read_text())
    rows = "".join(
        f"<tr><td>{st}</td>"
        + "".join(
            f"<td>{'<b>' if k == 'main' else ''}{c[st][k]['homes_net'][1]:,}{'</b>' if k == 'main' else ''}</td><td>{c[st][k]['homes_net'][0]:,}–{c[st][k]['homes_net'][2]:,}</td>"
            for k, _, _ in VARIANTS
        )
        + "</tr>"
        for st in STATES
    )
    tx = c["TX"]
    html = f"""<title>Missing-middle fast ramp</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=Public+Sans:wght@400;600;700&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&display=swap">
<style>{style()}{EXTRA_CSS}</style>
<main>
<header>
  <div class="eyebrow">Lotline · Missing middle · D-100 fast-ramp sensitivity · 17 Nov 2026</div>
  <h1>If builders took up the rule as fast as cities that chose it, five-year homes would be about 3.6 times higher</h1>
  <p class="lede">The main result keeps C4: the Handbook rule reaches half its full pace after 4 years, as Oregon's state-required places did. D-100 found that places which adopted the reform on their own reached half pace in about half a year. This sensitivity runs the same scenario with that fast ramp, changing nothing else: same θ, same draws, same seed.</p>
</header>

<div class="tiles">
  <div class="tile"><b>3.6×</b><span>five-year net homes at half-way 0.5 years against C4, every state (3.3× at 1.0 year)</span></div>
  <div class="tile"><b>{tx["fast"]["homes_net"][1]:,}</b><span>Texas median with the fast ramp, against {tx["main"]["homes_net"][1]:,} with C4</span></div>
  <div class="tile"><b>24%</b><span>of the five years lands in year 5 with the fast ramp (57% with C4)</span></div>
  <div class="tile"><b>3.30 · 3.61</b><span>measured ratios at 1.0 and 0.5 years, exactly the hand calculation written before the run</span></div>
</div>

<section>
  <div class="num-tag">Finding 1</div>
  <h2>The ramp is about timing: the fast ramp books in five years what C4 reaches later</h2>
  {shape_bars()}
  <div class="key"><span><i class="main"></i>C4, half-way 4.0 years</span><span><i class="fast"></i>fast ramp, half-way 0.5 years</span><span>share of the full (mature) rate in each scenario year</span></div>
  <p>Both ramps reach the same mature rate. Over five years C4's ramp averages 23% of it and the fast ramp 84%, so the whole sensitivity is a multiplier of 4.20 ÷ 1.16 = 3.6 on every place. It moves no place relative to another and adds no new uncertainty: it shows how much of the five-year number depends on how quickly builders respond.</p>
</section>

<section>
  <div class="num-tag">Finding 2</div>
  <h2>Every state scales by the same factor</h2>
  {ranges(c)}
  <div class="key"><span><i class="main"></i>C4 (main)</span><span><i class="mid"></i>half-way 1.0 year</span><span><i class="fast"></i>half-way 0.5 years</span><span>dot: median; bar: P10–P90; log scale</span></div>
  <div class="scroll"><table><thead><tr><th>State</th><th>C4 median</th><th>C4 P10–P90</th><th>1.0 yr median</th><th>1.0 yr P10–P90</th><th>0.5 yr median</th><th>0.5 yr P10–P90</th></tr></thead><tbody>{rows}</tbody></table></div>
  <p class="note">Five-year added 2–4 unit homes net of houses torn down, origin 2025, 4,000 draws. Quote medians: θ's wide range pulls means far above them.</p>
</section>

<section>
  <div class="num-tag">How to read it</div>
  <h2>An upper case for timing, not a second forecast</h2>
  <p>C4 stays the headline because the Handbook rule is a state law, and Oregon's state-required places ramped slowly. The fast ramp is fair only if a state law were taken up the way a city's own reform is: by a city that wanted it, often with builders already lined up (St. Paul built 55 buildings in two years). It also holds C4's θ; with R2's own θ (0.94 per 1,000) it would be about 9% lower. The locally adopted ramp rests on 37 places and 64 post-reform years and did not improve held-out forecasts.</p>
</section>

<section class="decision">
  <div class="num-tag">For Ben</div>
  <h2>Getting it into the app</h2>
  <p>The engine can now run it (<code>mm.run(..., ramp="fast")</code>). Showing it in the app means a new part in the results bundle, a shared contract owned by WS-CORE, so it needs a contract-change issue and your OK. Until then it lives on this page and in <code>reports/mm-d100/fast-ramp/</code>.</p>
</section>

<footer>
  <div>Run: <code>mm_fast_ramp_run.py</code>, pre-registered in D-100 on 17 Nov 2026 before the run. No permits read; nothing unblinded; config's main values unchanged.</div>
  <div>Sources: <code>reports/mm-d100/fast-ramp/</code> on branch <code>ws/mm-fast-ramp</code>.</div>
</footer>
</main>
"""
    (OUT / "results.html").write_text(html)
    print(f"wrote {OUT / 'results.html'}")


def style() -> str:
    return re.search(r"<style>(.*?)</style>", STYLE_FROM.read_text(), re.S).group(1)


if __name__ == "__main__":
    main()
