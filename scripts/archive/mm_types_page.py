#!/usr/bin/env python3
# ruff: noqa: E501  (long lines are the HTML/CSS page template)
"""Results page for D-092 run 12 (φ by place type): reports/mm-d092/run12-types/results.html.

    uv run python scripts/archive/mm_types_page.py

Reads run 12's summary.json; borrows the Lotline stylesheet from the run-6 page.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
R = REPO / "reports" / "mm-d092"
OUT = R / "run12-types"
STYLE_FROM = R / "run6-results" / "d092-results.html"
TYPES = (("core", "Core city"), ("suburb", "Suburb"), ("town", "Town"))
STATES = ("MN", "NC", "OH", "TX")
EDGE = 20.0
EXTRA_CSS = """
.bars .b { fill: var(--scenario-missing-middle); } .bars .b.edge { fill: var(--brass); }
.bars .one { stroke: var(--ink); stroke-width: 1.5; stroke-dasharray: 4 3; }
"""


def bars(s: dict) -> str:
    """φ by state and type (both origins), one group per state, with one φ as a dashed line."""
    W, left, top, gw, bw, H = 680, 40, 20, 150, 38, 180
    sy = lambda v: top + H - H * min(v, 21.0) / 21.0  # noqa: E731
    g = []
    for v in (0, 5, 10, 15, 20):
        g.append(
            f'<line x1="{left}" x2="{W - 10}" y1="{sy(v):.1f}" y2="{sy(v):.1f}" class="grid"/><text x="{left - 6}" y="{sy(v) + 4:.1f}" class="tick" text-anchor="end">{v}</text>'
        )
    one = s["phi_both_origins_one"]
    for i, st in enumerate(STATES):
        x0 = left + 20 + i * gw
        for j, (t, lab) in enumerate(TYPES):
            v = s["by_state_type"][f"{st}-{t}"]
            x = x0 + j * (bw + 4)
            edge = " edge" if v >= EDGE else ""
            g.append(
                f'<rect x="{x}" y="{sy(v):.1f}" width="{bw}" height="{top + H - sy(v):.1f}" class="b{edge}"><title>{st} {lab}: φ {v:.1f}</title></rect>'
            )
            g.append(
                f'<text x="{x + bw / 2}" y="{top + H + 14}" class="tick" text-anchor="middle">{t[0].upper()}</text>'
            )
            g.append(
                f'<text x="{x + bw / 2}" y="{sy(v) - 4:.1f}" class="tick" text-anchor="middle">{v:.1f}</text>'
            )
        g.append(
            f'<text x="{x0 + 1.5 * (bw + 4) - 2}" y="{top + H + 32}" class="lab" text-anchor="middle">{st}</text>'
        )
    g.append(
        f'<line x1="{left}" x2="{W - 10}" y1="{sy(one):.1f}" y2="{sy(one):.1f}" class="one"/><text x="{W - 12}" y="{sy(one) - 5:.1f}" class="reftxt" text-anchor="end">one φ, {one:.1f}</text>'
    )
    return f'<svg viewBox="0 0 {W} {top + H + 44}" class="chart bars" role="img" aria-label="φ by state and place type">{"".join(g)}</svg>'


def main() -> None:
    s = json.loads((OUT / "summary.json").read_text())
    cov = s["coverage_2021"]
    rows = "".join(
        f"<tr><td>{lab}</td><td>{s['YT_phi_train'][t]:.2f}</td><td>{s['phi_both_origins'][t]['phi']:.1f} ({s['phi_both_origins'][t]['low']:.1f}–{s['phi_both_origins'][t]['high']:.1f})</td><td>{cov[t]['places']}</td><td>{cov[t]['Y1']:.2f}</td><td>{cov[t]['YT']:.2f}</td></tr>"
        for t, lab in TYPES
    )
    rows += f"<tr><td><b>One φ</b></td><td>{s['Y1_phi']:.2f}</td><td>{s['phi_both_origins_one']:.1f}</td><td>{cov['all']['places']}</td><td>{cov['all']['Y1']:.2f}</td><td>{cov['all']['YT']:.2f}</td></tr>"
    html = f"""<title>Missing-middle place types</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=Public+Sans:wght@400;600;700&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&display=swap">
<style>{style()}{EXTRA_CSS}</style>
<main>
<header>
  <div class="eyebrow">Lotline · Missing middle · D-092 run 12, place types · 15 Nov 2026</div>
  <h1>Place types don't narrow missing middle's ranges</h1>
  <p class="lede">Giving core cities, suburbs and towns their own year-to-year lumpiness improved the held-out score by {s["delta"]:.1f} log points, with a standard error of {s["paired_se"]:.1f}. The pre-registered bar was 2 standard errors, so one φ is kept and the refit isn't run. Coverage doesn't move ({cov["all"]["Y1"]:.2f} against {cov["all"]["YT"]:.2f}). The size of the difference depends more on the state than on the type of place.</p>
</header>

<div class="tiles">
  <div class="tile"><b>+{s["delta"]:.1f}</b><span>held-out gain from φ by type (SE {s["paired_se"]:.1f}); bar is 2 SE</span></div>
  <div class="tile"><b>Not adopted</b><span>one φ ({s["phi_both_origins_one"]:.1f}) stays; run 11 stands</span></div>
  <div class="tile"><b>{s["phi_both_origins"]["town"]["phi"]:.1f}</b><span>towns' φ: the least lumpy type, not the most as guessed</span></div>
  <div class="tile"><b>0 of 93</b><span>fit places can carry a type term on the reform rate (size rule merges both)</span></div>
</div>

<section>
  <div class="num-tag">Finding 1</div>
  <h2>The type difference doesn't hold up out of sample</h2>
  <div class="scroll"><table><thead><tr><th>Type</th><th>φ, fitted 2016</th><th>φ, both origins (90%)</th><th>Places scored 2021</th><th>Coverage, one φ</th><th>Coverage, φ by type</th></tr></thead><tbody>{rows}</tbody></table></div>
  <p class="note">Coverage is the share of 2021–2025 totals inside P10–P90 (20,000 draws, seed 20261115). The places are the 483 unused ones (MN, NC, OH, TX), which no fit or test uses.</p>
</section>

<section>
  <div class="num-tag">Finding 2</div>
  <h2>The state matters more than the type</h2>
  {bars(s)}
  <p>φ by state and type (C core city, S suburb, T town). Within each state, suburbs are lumpier than towns. But Texas's core cities and suburbs both hit the search's upper limit (shown in brass), while the other states' sit at 3–12. A state term isn't a candidate, because it wouldn't carry to a state with no permit data.</p>
</section>

<section class="decision">
  <div class="num-tag">For Ben</div>
  <h2>Next lever: count projects, not buildings</h2>
  <p>For missing middle, place types are coded and recorded but not used: they don't narrow the noise, and the fit places (86 of 93 in Oregon) can't support a type term on the reform rate. Texas's lumpiness at the limit points to large multi-building projects, so the noise sits in what is counted. Nothing goes to config; the tool still runs D-059's θ = 0.12.</p>
</section>

<footer>
  <div>Run: <code>mm_types_d092.py</code> (one φ against φ by type; trained 2016, scored 2021; 2-SE rule). Pre-registered in D-092's deviation (c) of 2026-11-15. Cached tables only; St. Paul and Ramsey not in the panel; nothing unblinded.</div>
  <div>Sources: <code>reports/mm-d092/run12-types/</code> on branch <code>ws/mm-baseline-spread</code> (PR #436).</div>
</footer>
</main>
"""
    (OUT / "results.html").write_text(html)
    print(f"wrote {OUT / 'results.html'}")


def style() -> str:
    return re.search(r"<style>(.*?)</style>", STYLE_FROM.read_text(), re.S).group(1)


if __name__ == "__main__":
    main()
