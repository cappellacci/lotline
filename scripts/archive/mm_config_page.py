#!/usr/bin/env python3
# ruff: noqa: E501  (long lines are the HTML/CSS page template)
"""Results page for C4 to config: reports/mm-d092/config-c4/results.html.

    uv run python scripts/archive/mm_config_page.py

Reads compare.json (`mm_config_compare.py`); borrows the Lotline stylesheet from the run-6 page.
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
R = REPO / "reports" / "mm-d092"
OUT = R / "config-c4"
STYLE_FROM = R / "run6-results" / "d092-results.html"
STATES = ("TX", "NC", "OH", "MN", "OR")
EXTRA_CSS = """
.rng .old { stroke: var(--ink-faint); stroke-width: 6; stroke-linecap: round; }
.rng .new { stroke: var(--scenario-missing-middle); stroke-width: 6; stroke-linecap: round; }
.rng .med { fill: var(--ink); }
.key { display: flex; gap: 1.2rem; font-size: .85rem; color: var(--ink-muted); flex-wrap: wrap; }
.key i { display: inline-block; width: 18px; height: 6px; border-radius: 3px; margin-right: .35rem; vertical-align: 2px; }
.key .old { background: var(--ink-faint); } .key .new { background: var(--scenario-missing-middle); }
"""


def ranges(c: dict) -> str:
    """P10-P90 of five-year net homes per state, D-055 (grey) above C4 (green), log scale, median dots."""
    W, left, top, gh = 680, 50, 16, 46
    H = top + gh * len(STATES) + 30
    lo, hi = math.log(10), math.log(100_000)
    sx = lambda v: left + (W - left - 20) * (math.log(max(v, 10)) - lo) / (hi - lo)  # noqa: E731
    g = []
    for v in (10, 100, 1_000, 10_000, 100_000):
        g.append(
            f'<line x1="{sx(v):.1f}" x2="{sx(v):.1f}" y1="{top - 6}" y2="{H - 26}" class="grid"/><text x="{sx(v):.1f}" y="{H - 10}" class="tick" text-anchor="middle">{v:,}</text>'
        )
    for i, st in enumerate(STATES):
        y0 = top + i * gh
        g.append(f'<text x="{left - 8}" y="{y0 + 18}" class="lab" text-anchor="end">{st}</text>')
        for j, (k, cls) in enumerate((("D-055 homes_net", "old"), ("C4 homes_net", "new"))):
            p10, p50, p90, _ = c[st][k]
            y = y0 + 8 + j * 14
            g.append(
                f'<line x1="{sx(p10):.1f}" x2="{sx(p90):.1f}" y1="{y}" y2="{y}" class="{cls}"><title>{st} {k.split()[0]}: {p10:,} to {p90:,}, median {p50:,}</title></line><circle cx="{sx(p50):.1f}" cy="{y}" r="3.5" class="med"/>'
            )
    return f'<div class="scroll"><svg viewBox="0 0 {W} {H}" class="chart rng" role="img" aria-label="Five-year net homes by state, old and new values">{"".join(g)}</svg></div>'


def main() -> None:
    c = json.loads((OUT / "compare.json").read_text())
    rows = "".join(
        f"<tr><td>{st}</td><td>{c[st]['D-055 homes_net'][1]:,}</td><td>{c[st]['D-055 homes_net'][0]:,}–{c[st]['D-055 homes_net'][2]:,}</td>"
        f"<td><b>{c[st]['C4 homes_net'][1]:,}</b></td><td>{c[st]['C4 homes_net'][0]:,}–{c[st]['C4 homes_net'][2]:,}</td>"
        f"<td>{c[st]['C4 homes_net'][1] / c[st]['D-055 homes_net'][1]:.1f}×</td></tr>"
        for st in STATES
    )
    tx = c["TX"]
    html = f"""<title>Missing-middle config C4</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=Public+Sans:wght@400;600;700&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&display=swap">
<style>{style()}{EXTRA_CSS}</style>
<main>
<header>
  <div class="eyebrow">Lotline · Missing middle · C4 to config · 15 Nov 2026</div>
  <h1>The missing-middle effect is now about 2.5× larger, with honest ranges</h1>
  <p class="lede">Ben chose D-092's C4 fit for the tool. The mature rate θ is 1.04 new 2–4 unit buildings per 1,000 eligible lots a year (0.13–19.4); the reform reaches half of that after 4 years; each year is lumpy, because builders put up these buildings in clusters. In the Handbook scenario, statewide five-year net homes roughly double and a half at the median, and the upper ends grow about fourfold.</p>
</header>

<div class="tiles">
  <div class="tile"><b>2.4–2.7×</b><span>median five-year net homes, C4 against D-055, by state</span></div>
  <div class="tile"><b>{tx["C4 homes_net"][1]:,}</b><span>Texas median (P10–P90 {tx["C4 homes_net"][0]:,}–{tx["C4 homes_net"][2]:,})</span></div>
  <div class="tile"><b>57%</b><span>of the five-year total lands in year 5: the effect is still growing</span></div>
  <div class="tile"><b>0.78</b><span>C4's place coverage in the §7 tests (bar 0.60–0.95); D-055's ranges were too narrow</span></div>
</div>

<section>
  <div class="num-tag">Finding 1</div>
  <h2>Every state moves the same way</h2>
  {ranges(c)}
  <div class="key"><span><i class="old"></i>D-055 (before)</span><span><i class="new"></i>C4 (now)</span><span>dot: median; bar: P10–P90; log scale</span></div>
  <div class="scroll"><table><thead><tr><th>State</th><th>D-055 median</th><th>D-055 P10–P90</th><th>C4 median</th><th>C4 P10–P90</th><th>Median ratio</th></tr></thead><tbody>{rows}</tbody></table></div>
  <p class="note">Five-year added 2–4 unit homes net of houses torn down, origin 2025, same places, seed and draws. Oregon is small because its places already allow most of the Handbook rule.</p>
</section>

<section>
  <div class="num-tag">Finding 2</div>
  <h2>Quote medians, not means</h2>
  <p>θ's range spans a factor of about 150, so a few draws with a large θ pull the mean far above the median (Texas: mean {tx["C4 homes_net"][3]:,}, median {tx["C4 homes_net"][1]:,}). The tool's headlines should give the median and the P10–P90 range. And because the reform reaches half its pace only after 4 years, a five-year window catches the start of the effect, not its full size.</p>
</section>

<section class="decision">
  <div class="num-tag">For Ben</div>
  <h2>What else this touches</h2>
  <p>St. Paul's V5 forecast is not frozen yet and reads these values, so it will use C4 if frozen after this merges. V5 Charlotte and V9 Oregon are frozen; their code is unchanged and reproduces at their freeze commits. The app's missing-middle numbers change when the results are regenerated.</p>
</section>

<footer>
  <div>Run: <code>mm_config_compare.py</code> (D-055 against C4, Handbook scenario, origin 2025). No permits read; nothing unblinded.</div>
  <div>Sources: <code>reports/mm-d092/config-c4/</code> on branch <code>ws/mm-baseline-spread</code> (PR #436).</div>
</footer>
</main>
"""
    (OUT / "results.html").write_text(html)
    print(f"wrote {OUT / 'results.html'}")


def style() -> str:
    return re.search(r"<style>(.*?)</style>", STYLE_FROM.read_text(), re.S).group(1)


if __name__ == "__main__":
    main()
