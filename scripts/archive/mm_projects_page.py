#!/usr/bin/env python3
# ruff: noqa: E501  (long lines are the HTML/CSS page template)
"""Results page for D-092 run 13 (buildings per project): reports/mm-d092/run13-projects/results.html.

    uv run python scripts/archive/mm_projects_page.py [--dir reports/mm-d092/run13-projects-mpls-fix]

Reads run 13's summary.json; borrows the Lotline stylesheet from the run-6 page.
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
R = REPO / "reports" / "mm-d092"
OUT = R / "run13-projects"
STYLE_FROM = R / "run6-results" / "d092-results.html"
BAR = 1.5
NAMES = {
    "mpls_ccs_permits": "Minneapolis", "rochester_permits": "Rochester MN", "durham_permits": "Durham",
    "raleigh_permits": "Raleigh", "wilmington_permits": "Wilmington", "cincy_permits": "Cincinnati",
    "cle_permits": "Cleveland", "columbus_permits": "Columbus", "bend_permits": "Bend",
    "medford_permits": "Medford", "portland_permits": "Portland", "austin_permits": "Austin",
    "cstx_permits": "College Station", "cary_permits": "Cary", "chapel_hill_permits": "Chapel Hill",
    "greensboro_permits": "Greensboro", "dallas_permits": "Dallas", "sa_permits": "San Antonio",
}  # fmt: skip
EXTRA_CSS = """
.dots .lot { fill: var(--scenario-missing-middle); } .dots .day { fill: none; stroke: var(--brass); stroke-width: 2; }
.dots .bar { stroke: var(--ink); stroke-width: 1.5; stroke-dasharray: 4 3; }
.key { display: flex; gap: 1.2rem; font-size: .85rem; color: var(--ink-muted); flex-wrap: wrap; }
.key i { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: .35rem; vertical-align: -1px; }
.key .lot { background: var(--scenario-missing-middle); } .key .day { border: 2px solid var(--brass); }
"""


def dots(s: dict) -> str:
    """Inflation by source on a log scale, same lot (filled) and same day (ring), with the 1.5 bar."""
    rows = [(k, v) for k, v in s["by_source"].items() if v.get("same_day", {}).get("projects", 0) >= 10]
    rows.sort(key=lambda kv: -max(x["inflation"] for x in kv[1].values() if x["projects"]))
    W, left, top, rh = 680, 130, 24, 22
    H = top + rh * len(rows) + 30
    lo, hi = math.log(1.0), math.log(30.0)
    sx = lambda v: left + (W - left - 20) * (math.log(max(v, 1.0)) - lo) / (hi - lo)  # noqa: E731
    g = []
    for v in (1, 1.5, 2, 5, 10, 20):
        cls = "bar" if v == BAR else "grid"
        g.append(
            f'<line x1="{sx(v):.1f}" x2="{sx(v):.1f}" y1="{top - 8}" y2="{H - 26}" class="{cls}"/><text x="{sx(v):.1f}" y="{H - 10}" class="tick" text-anchor="middle">{v:g}</text>'
        )
    for i, (k, v) in enumerate(rows):
        y = top + i * rh + rh / 2
        g.append(
            f'<text x="{left - 8}" y="{y + 4:.1f}" class="lab" text-anchor="end">{NAMES.get(k, k)}</text>'
        )
        for how, cls in (("same_lot", "lot"), ("same_day", "day")):
            x = v.get(how)
            if x and x["projects"]:
                g.append(
                    f'<circle cx="{sx(x["inflation"]):.1f}" cy="{y:.1f}" r="5" class="{cls}"><title>{NAMES.get(k, k)}, {how.replace("_", " ")}: {x["inflation"]:.2f} ({x["projects"]} projects, {x["buildings"]:.0f} buildings)</title></circle>'
                )
    return f'<div class="scroll"><svg viewBox="0 0 {W} {H}" class="chart dots" role="img" aria-label="Inflation by city">{"".join(g)}</svg></div>'


def main(out: Path = OUT) -> None:
    s = json.loads((out / "summary.json").read_text())
    fixed = out.name.endswith("mpls-fix")
    mp = s["by_source"]["mpls_ccs_permits"]
    mpls_tile = f"{mp['same_lot']['inflation']:.2f}–{mp['same_day']['inflation']:.2f}"
    banner = (
        '<section class="decision"><div class="num-tag">Corrected 17 Nov 2026</div><h2>Minneapolis rerun after a permit-file fix</h2>'
        "<p>Minneapolis's file had typed roof, remodel and addition permits on existing duplexes and fourplexes as new 2–4 unit buildings (#450, fixed in #451). "
        "Rerun with the fix, Minneapolis drops from 1,042 to 179 buildings (by lot); its 2017–2025 count is now 175 against Census's 165. "
        "Every other city is unchanged. Pooled clustering goes up slightly: by lot 12.8 → 14.3 with 34% → 39% in projects of 3+; by day 5.3 → 5.6 with 42% → 44%. "
        "The verdict is the same. The building-equivalent check (below) was not rerun; Minneapolis was not one of its large clusters.</p></section>"
        if fixed
        else ""
    )
    lot, day = s["pooled"]["same_lot"], s["pooled"]["same_day"]
    rows = "".join(
        f"<tr><td>{NAMES.get(k, k)}</td>"
        + "".join(
            f"<td>{v[h]['projects']}</td><td>{v[h]['inflation']:.2f}</td><td>{v[h]['share_in_3plus']:.0%}</td>"
            if h in v and v[h]["projects"] else "<td>–</td><td>–</td><td>–</td>"
            for h in ("same_lot", "same_day")
        ) + "</tr>"
        for k, v in s["by_source"].items() if any(x["projects"] for x in v.values())
    )  # fmt: skip
    html = f"""<title>Missing-middle project size</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=Public+Sans:wght@400;600;700&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&display=swap">
<style>{style()}{EXTRA_CSS}</style>
<main>
<header>
  <div class="eyebrow">Lotline · Missing middle · D-092 run 13, buildings per project · 15 Nov 2026{" (Minneapolis corrected 17 Nov)" if fixed else ""}</div>
  <h1>Duplexes and fourplexes come in clusters</h1>
  <p class="lede">In the city permit files, a third or more of 2–4 unit buildings come in projects of 3 or more: {lot["share_in_3plus"]:.0%} grouped by lot, {day["share_in_3plus"]:.0%} grouped by day. Clustering multiplies a place's year-to-year variance by {lot["inflation"]:.1f} (by lot) or {day["inflation"]:.1f} (by day), far over the pre-registered bar of 1.5. By the rule, the project-based model goes back to Ben. The pre-run guess, that most projects are one building, was wrong.</p>
</header>
{banner}
<div class="tiles">
  <div class="tile"><b>{lot["inflation"]:.1f} / {day["inflation"]:.1f}</b><span>variance inflation, by lot / by day (bar 1.5)</span></div>
  <div class="tile"><b>{lot["share_in_3plus"]:.0%}</b><span>of buildings in projects of 3+ (by lot)</span></div>
  <div class="tile"><b>~100–130</b><span>duplexes on one Austin parcel in three months (202 permits, some per side): the largest project</span></div>
  <div class="tile"><b>{mpls_tile}</b><span>Minneapolis, by lot / by day: the one big city where nearly every project is one building</span></div>
</div>

<section>
  <div class="num-tag">Finding 1</div>
  <h2>Most cities are over the bar, and they differ a lot</h2>
  {dots(s)}
  <div class="key"><span><i class="lot"></i>same lot (parcel ID, within a year)</span><span><i class="day"></i>same day (issue date)</span><span>dashed line: the 1.5 bar</span></div>
  <p>Cities with at least 10 same-day projects, on a log scale. Minneapolis, Cincinnati, Cleveland, Medford and Portland sit near the bar ({"1.0" if fixed else "1.1"} to 2.4): their 2–4 unit buildings mostly come one or two at a time. Austin, College Station, Wilmington and Columbus build them in large groups, which fits Texas's lumpiness from run 12.</p>
</section>

<section>
  <div class="num-tag">Finding 2</div>
  <h2>"Same lot" wasn't a lower bound</h2>
  <p>The plan called same lot the low estimate and same day the high one. It came out the other way round in the pooled numbers ({lot["inflation"]:.1f} against {day["inflation"]:.1f}). That's because one parcel can hold a whole build-to-rent community permitted over a year, while a same-day group catches only one day of it. Both are far over 1.5, so the verdict doesn't depend on which is right.</p>
  <div class="scroll"><table><thead><tr><th rowspan="2">Source</th><th colspan="3">Same lot</th><th colspan="3">Same day</th></tr><tr><th>Projects</th><th>Inflation</th><th>In 3+</th><th>Projects</th><th>Inflation</th><th>In 3+</th></tr></thead><tbody>{rows}</tbody></table></div>
  <p class="note">2–4 unit building permits from 2010, through the holdout filter; St. Paul and Mecklenburg left out. Franklin and Montgomery counties' files hold no typed 2–4 unit permits. Inflation is E[S²]/E[S], where S is buildings per project. A check after the run, reported only: some files record one permit per home or duplex side (Austin's 202 permits are about 100–130 duplexes). Counted as homes ÷ homes per building instead, inflation is 11.8 by lot and 5.6 by day, with 39–44% in projects of 3+, so the finding holds.</p>
</section>

<section class="decision">
  <div class="num-tag">For Ben</div>
  <h2>Decided: record it, don't build it</h2>
  <p>Clustering is real and large, so it's the honest explanation for missing middle's wide ranges. A model of projects × buildings per project would match how building happens, but it adds no new information. Ben chose to record it as the reason for the ranges and a stated limitation (15 Nov 2026). Run 11 stands; the config choice is next.</p>
</section>

<footer>
  <div>Run: <code>mm_project_size_d092.py</code> (same lot and same day groupings; stop rule 1.5). Pre-registered in D-092's deviation (d) of 2026-11-15. Cached tables only; nothing unblinded.</div>
  <div>Sources: <code>{out.relative_to(REPO)}/</code>{" (rerun after #451; the original run is in <code>reports/mm-d092/run13-projects/</code>)" if fixed else " on branch <code>ws/mm-baseline-spread</code> (PR #436)"}.</div>
</footer>
</main>
"""
    (out / "results.html").write_text(html)
    print(f"wrote {out / 'results.html'}")


def style() -> str:
    return re.search(r"<style>(.*?)</style>", STYLE_FROM.read_text(), re.S).group(1)


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", type=Path, default=OUT, help="run folder holding summary.json")
    main(ap.parse_args().dir.resolve())
