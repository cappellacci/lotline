#!/usr/bin/env python3
# ruff: noqa: E501  (long lines are the HTML/CSS page template)
"""Results page for D-100 run 1 (missing middle's ramp): reports/mm-d100/run1/results.html.

    uv run python scripts/dev/mm_ramp_page.py

Reads run 1's summary.json; borrows the Lotline stylesheet from the D-092 run-6 page.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from lotline.model.hazard import ramp

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "reports" / "mm-d100" / "run1"
STYLE_FROM = REPO / "reports" / "mm-d092" / "run6-results" / "d092-results.html"
EXTRA_CSS = """
.ramp .st { fill: none; stroke: var(--scenario-missing-middle); stroke-width: 2.5; }
.ramp .lo { fill: none; stroke: var(--brass); stroke-width: 2.5; stroke-dasharray: 6 4; }
.ramp .c4 { fill: none; stroke: var(--ink-faint); stroke-width: 1.5; }
.key { display: flex; gap: 1.2rem; font-size: .85rem; color: var(--ink-muted); flex-wrap: wrap; }
.key i { display: inline-block; width: 22px; height: 0; border-top: 3px solid; margin-right: .35rem; vertical-align: 3px; }
.key .st { border-color: var(--scenario-missing-middle); } .key .lo { border-color: var(--brass); border-top-style: dashed; } .key .c4 { border-color: var(--ink-faint); }
"""


def curves(hs: float, hl: float) -> str:
    W, H, left, top, bot = 640, 230, 46, 14, 34
    sx = lambda a: left + (W - left - 14) * a / 8  # noqa: E731
    sy = lambda v: top + (H - top - bot) * (1 - v)  # noqa: E731
    g = []
    for v in (0, 0.25, 0.5, 0.75, 1):
        g.append(
            f'<line x1="{left}" x2="{W - 14}" y1="{sy(v):.1f}" y2="{sy(v):.1f}" class="grid"/><text x="{left - 6}" y="{sy(v) + 4:.1f}" class="tick" text-anchor="end">{v:.0%}</text>'
        )
    for a in range(0, 9):
        g.append(f'<text x="{sx(a):.1f}" y="{H - 14}" class="tick" text-anchor="middle">{a}</text>')
    ages = [i / 20 for i in range(0, 161)]
    for h, cls in ((hs, "st"), (hl, "lo")):
        pts = " ".join(f"{sx(a):.1f},{sy(float(ramp(a, h, 0.75))):.1f}" for a in ages)
        g.append(f'<polyline points="{pts}" class="{cls}"/>')
    g.append(
        f'<text x="{(left + W) / 2}" y="{H}" class="tick" text-anchor="middle">years since the reform took effect</text>'
    )
    return f'<div class="scroll"><svg viewBox="0 0 {W} {H + 6}" class="chart ramp" role="img" aria-label="Share of the mature rate by years since adoption, by route">{"".join(g)}</svg></div>'


def main() -> None:
    s = json.loads((OUT / "summary.json").read_text())
    f, h, p, r5 = s["full"], s["R2_halves"], s["paired"], s["r5_per_1000"]
    rows = "".join(
        f"<tr><td>{lab}</td><td>{p[k]['delta']:+.2f}</td><td>{p[k]['paired_se']:.2f}</td><td>{'yes' if s['beats_by_2se'][k] else 'no'}</td></tr>"
        for k, lab in (
            ("R1_vs_R0", "R1 (St. Paul added, one ramp) against C4"),
            ("R2_vs_R1", "R2 (a ramp per route) against R1"),
            ("R2_vs_R0", "R2 against C4"),
        )
    )
    html = f"""<title>Missing-middle ramp test</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=Public+Sans:wght@400;600;700&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&display=swap">
<style>{style()}{EXTRA_CSS}</style>
<main>
<header>
  <div class="eyebrow">Lotline · Missing middle · D-100 run 1, the ramp after St. Paul · 16 Nov 2026</div>
  <h1>Cities that choose the reform build fast; it doesn't forecast better</h1>
  <p class="lede">After St. Paul built faster than C4 predicted, we tested a separate ramp for cities that adopt missing middle themselves and for places a state law requires to. In the fit the split is clear: local adopters reach half speed in about half a year, places under Oregon's HB 2001 in four. But scored on states the fit didn't see, neither a refit with St. Paul nor the split ramp beats C4 by the pre-registered two standard errors. C4 stays, and the scenario's ramp, for a state law, is the same either way.</p>
</header>

<div class="tiles">
  <div class="tile"><b>{h["local"]:.1f} vs {h["state"]:.1f}</b><span>years to half speed: locally adopted vs state-required (in the fit)</span></div>
  <div class="tile"><b>{p["R2_vs_R1"]["delta"]:+.1f}</b><span>held-out gain from a ramp per route (SE {p["R2_vs_R1"]["paired_se"]:.1f}); bar is 2 SE</span></div>
  <div class="tile"><b>{p["R1_vs_R0"]["delta"]:+.1f}</b><span>adding St. Paul with one ramp: worse held out (SE {p["R1_vs_R0"]["paired_se"]:.1f})</span></div>
  <div class="tile"><b>C4 stays</b><span>nothing goes to config; §7 is not rerun</span></div>
</div>

<section>
  <div class="num-tag">Finding 1</div>
  <h2>In the fit, the two routes ramp very differently</h2>
  {curves(h["state"], h["local"])}
  <div class="key"><span><i class="st"></i>state-required (HB 2001 Oregon places), half-way {h["state"]:.1f} years</span><span><i class="lo"></i>locally adopted, half-way {h["local"]:.1f} years (range {h["local_low"]:.1f}–{h["local_high"]:.1f})</span></div>
  <p>Every leave-one-state-out fold with both groups finds the same split. In five-year rates: {r5["R2_local"]:.2f} new 2–4 unit buildings per 1,000 lots a year for local adopters against {r5["R2"]:.2f} for state-required places (C4: {r5["R0"]:.2f}).</p>
</section>

<section>
  <div class="num-tag">Finding 2</div>
  <h2>But it doesn't carry to a state the fit didn't see</h2>
  <div class="scroll"><table><thead><tr><th>Comparison (94 held-out places)</th><th>Δ log score</th><th>Paired SE</th><th>Beats by 2 SE?</th></tr></thead><tbody>{rows}</tbody></table></div>
  <p>The local ramp rests on 37 places with 64 post-reform years, most of them small Oregon towns with one or two years of data. Adding St. Paul to a single shared ramp makes held-out scores worse: one fast city pulls the ramp and the rate for the slow Oregon majority. R2's θ interval ({f["R2"]["low_per_1000"]:.2f}–{f["R2"]["high_per_1000"]:.2f} per 1,000) is narrower than C4's because it holds the pair of ramps fixed.</p>
</section>

<section class="decision">
  <div class="num-tag">For Ben</div>
  <h2>What changes, and what doesn't</h2>
  <p>Config stays at C4. For the Handbook scenario, a state law, the state-required ramp (4 years) is the same as C4's, so the statewide numbers don't move. What's new is an explanation for St. Paul's miss: cities that choose the reform build within a year. That fits as a stated finding and a "fast ramp" sensitivity for places that adopt on their own, if you want it shown.</p>
</section>

<footer>
  <div>Run: <code>mm_ramp_d100.py</code> (49 min, cached tables only); the summary was rebuilt from the saved fits and scores by <code>mm_ramp_d100_summary.py</code> after a JSON key bug at the last step (fixed). Pre-registered as D-100. St. Paul in the fit after its release (D-098).</div>
  <div>Sources: <code>reports/mm-d100/run1/</code> on branch <code>ws/mm-ramp-entry</code> (PR #445).</div>
</footer>
</main>
"""
    (OUT / "results.html").write_text(html)
    print(f"wrote {OUT / 'results.html'}")


def style() -> str:
    return re.search(r"<style>(.*?)</style>", STYLE_FROM.read_text(), re.S).group(1)


if __name__ == "__main__":
    main()
