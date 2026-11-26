#!/usr/bin/env python3
# ruff: noqa: E501  (long lines are the HTML/CSS page template)
"""Results page for the engine switch to Form A + place types (D-088, D-089): reports/adu-types-engine/.

    uv run python scripts/archive/adu_types_engine_page.py

Reads the totals written by `scripts/archive/adu_types_engine_check.py` (D-053 engine, types with m_x held at 1.0,
types as adopted) and the by-type means; borrows the Lotline stylesheet from the D-089 page. Standard
library and pandas only.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "reports" / "adu-types-engine"
STYLE_FROM = REPO / "reports" / "adu-state-profiles" / "results.html"
STATES = {"MN": "Minnesota", "NC": "North Carolina", "OH": "Ohio", "TX": "Texas", "OR": "Oregon"}
RUNS = (
    ("totals_d053.csv", "Before: D-053 (no types, m_x 1.0)", "r-old"),
    ("totals_types_mx1.csv", "Types, m_x held at 1.0 (decomposition only)", "r-mid"),
    ("totals_types.csv", "Now: Form A + place types (m_x 0.4)", "r-new"),
)
EXTRA_CSS = """
.r-old, .sw.r-old { fill: var(--scenario-baseline); background: var(--scenario-baseline); stroke: var(--scenario-baseline); }
.r-mid, .sw.r-mid { fill: var(--brass); background: var(--brass); stroke: var(--brass); }
.r-new, .sw.r-new { fill: var(--scenario-adu); background: var(--scenario-adu); stroke: var(--scenario-adu); }
.chart line.rng { stroke-width: 3; stroke-linecap: round; }
.chart .grid { stroke: var(--rule); stroke-width: 1; }
.chart .val { fill: var(--ink-muted); font-size: 11px; font-family: var(--font-mono); }
"""


def fmt(x: float) -> str:
    return f"{x:,.0f}"


def load() -> dict[str, pd.DataFrame]:
    return {f: pd.read_csv(OUT / f) for f, _, _ in RUNS}


def pick(df: pd.DataFrame, st: str, outcome: str) -> pd.Series:
    return df[(df["state"] == st) & (df["outcome"] == outcome)].iloc[0]


def range_chart(runs: dict[str, pd.DataFrame], outcome: str, label: str) -> str:
    """Per state, three P10-P90 lines with a P50 dot; log-free linear axis scaled to the largest P90."""
    W, left, right, row, gap = 640, 130, 600, 14, 16
    top = max(float(pick(runs[f], st, outcome)["p90"]) for f, _, _ in RUNS for st in STATES)
    step = 10 ** (len(str(int(top))) - 1)
    top = (int(top / step) + 1) * step

    def sx(v: float) -> float:
        return left + (right - left) * v / top

    g, y = [], 10
    for st, name in STATES.items():
        g.append(f'<text x="{left - 10}" y="{y + 2 * row - 2}" class="lab" text-anchor="end">{name}</text>')
        for f, _, cls in RUNS:
            r = pick(runs[f], st, outcome)
            yy = y + row // 2
            g.append(
                f'<line x1="{sx(r.p10):.1f}" x2="{sx(r.p90):.1f}" y1="{yy}" y2="{yy}" class="rng {cls}"/>'
                f'<circle cx="{sx(r.p50):.1f}" cy="{yy}" r="4.5" class="{cls}"/>'
                f'<text x="{sx(r.p90) + 6:.1f}" y="{yy + 4}" class="val">{fmt(r.p50)}</text>'
            )
            y += row
        y += gap
    ticks = []
    for i in range(6):
        v = top * i / 5
        ticks.append(
            f'<line x1="{sx(v):.1f}" x2="{sx(v):.1f}" y1="4" y2="{y - gap + 4}" class="grid"/>'
            f'<text x="{sx(v):.1f}" y="{y + 8}" class="tick" text-anchor="middle">{fmt(v)}</text>'
        )
    h = y + 26
    return (
        f'<svg viewBox="0 0 {W} {h}" class="chart" role="img" aria-label="{label}">{"".join(ticks)}{"".join(g)}'
        f'<text x="{right}" y="{y + 22}" class="tick" text-anchor="end">{label}; line P10–P90, dot and number '
        "P50</text></svg>"
    )


def state_table(runs: dict[str, pd.DataFrame]) -> str:
    rows = []
    for st, name in STATES.items():
        for outcome, lab in (
            ("current_rules_adus", "ADUs under current rules"),
            ("adu_permits_added", "ADU permits added"),
            ("additional_homes", "Additional homes"),
        ):
            cells = []
            for f, _, _ in RUNS:
                r = pick(runs[f], st, outcome)
                cells.append(f"<td class='num'>{fmt(r.p50)}<br><small>{fmt(r.p10)}–{fmt(r.p90)}</small></td>")
            first = name if outcome == "current_rules_adus" else ""
            rows.append(f"<tr><td>{first}</td><td>{lab}</td>{''.join(cells)}</tr>")
    head = "".join(f"<th>{t}</th>" for _, t, _ in RUNS)
    return (
        '<div class="scroll"><table><thead><tr><th>State</th><th>2027–2031</th>'
        f"{head}</tr></thead><tbody>{''.join(rows)}</tbody></table></div>"
    )


def type_table() -> str:
    t = pd.read_csv(OUT / "by_type.csv")
    names = {"core": "Core cities", "suburb": "Suburbs", "town": "Towns"}
    rows = []
    for st, name in STATES.items():
        g = t[t["state"] == st].set_index("place_type")
        tot_c, tot_a = g["current_rules_adus_mean"].sum(), g["adu_permits_added_mean"].sum()
        for i, ty in enumerate(("core", "suburb", "town")):
            r = g.loc[ty]
            rows.append(
                f"<tr><td>{name if i == 0 else ''}</td><td>{names[ty]}</td>"
                f"<td class='num'>{r.eligible_parcels / 1000:,.0f}k</td>"
                f"<td class='num'>{fmt(r.current_rules_adus_mean)} ({r.current_rules_adus_mean / tot_c:.0%})</td>"
                f"<td class='num'>{fmt(r.adu_permits_added_mean)} ({r.adu_permits_added_mean / tot_a:.0%})</td></tr>"
            )
    return (
        '<div class="scroll"><table><thead><tr><th>State</th><th>Type</th><th>Eligible lots</th>'
        "<th>Current-rules ADUs (mean)</th><th>ADU permits added (mean)</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table></div>"
    )


def main() -> None:
    runs = load()
    style = re.search(r"<style>(.*?)</style>", STYLE_FROM.read_text(), re.S).group(1)
    homes = {st: [float(pick(runs[f], st, "additional_homes")["p50"]) for f, _, _ in RUNS] for st in STATES}
    legend = "".join(f'<span><i class="sw {c}"></i>{t}</span>' for _, t, c in RUNS)
    tx = homes["TX"]
    html = f"""<title>ADU engine with place types</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=Public+Sans:wght@400;600;700&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&display=swap">
<style>{style}{EXTRA_CSS}</style>
<main>
<header>
  <div class="eyebrow">Lotline · ADU engine switch to Form A + place types (D-088, D-089) · 14 Nov 2026</div>
  <h1>With place types, the Handbook ADU scenario adds two to four times as many homes in four states</h1>
  <p class="lede">The scenario engine now runs the model Ben chose in D-088: a suburb's ADU rate, a core-city multiplier (×3.3), the town prior from D-089, and partial local rules counting at 40% of the Handbook (m_x 0.4) instead of 100%. Oregon barely moves. In Minnesota, North Carolina, Ohio and Texas, the homes the reform adds rise by 1.8–4.1 times at the median, and the ranges widen. The split varies: the types and the new anchor make most of the rise in Ohio and Texas, and partial rules no longer counting in full make most of it in Minnesota and North Carolina.</p>
</header>

<div class="stats">
  <div class="stat"><b>{fmt(tx[0])} → {fmt(tx[2])}</b><span>Texas additional homes, 2027–31, P50</span></div>
  <div class="stat"><b>{fmt(homes["NC"][0])} → {fmt(homes["NC"][2])}</b><span>North Carolina, the biggest relative rise (×{homes["NC"][2] / homes["NC"][0]:.1f})</span></div>
  <div class="stat"><b>{fmt(homes["OR"][0])} → {fmt(homes["OR"][2])}</b><span>Oregon: its rules are already near the Handbook, so little is added</span></div>
  <div class="stat"><b>×3.3</b><span>core-city multiplier on a suburb's rate (×1.7 to ×6.7), drawn each run</span></div>
</div>

<section>
  <div class="num-tag">Finding 1</div>
  <h2>Additional homes from the Handbook ADU reform, by state</h2>
  <p>Each state has three runs: the old engine, the new one with partial rules still counted in full, and the new one as adopted. The middle run is only there to split the change into its two causes; nobody fitted m_x 1.0 with types.</p>
  <div class="legend">{legend}</div>
  {range_chart(runs, "additional_homes", "additional homes, 2027–2031")}
</section>

<section>
  <div class="num-tag">Finding 2</div>
  <h2>ADUs under today's rules rise too, so the baseline is higher</h2>
  <p>The no-reform path rises in every state, most in Texas and North Carolina (about 45%), where core cities hold most of today's ADUs. With m_x at 0.4, partial rules make fewer ADUs today, which pulls this path back down and leaves more for the reform to add.</p>
  <div class="legend">{legend}</div>
  {range_chart(runs, "current_rules_adus", "ADU permits under current rules, 2027–2031")}
</section>

<section>
  <div class="num-tag">Finding 3</div>
  <h2>Where the ADUs come from, by place type</h2>
  <p>Core cities hold most of today's ADUs in North Carolina, Texas and Oregon. The reform's added ADUs come mostly from suburbs, where partial rules are common, except in Texas, where core cities add about as many as suburbs. Towns add from 2% (Texas) to 27% (Oregon) of what the reform adds: few ADUs today, but often no rule yet.</p>
  {type_table()}
  <p class="note">Means over 1,000 draws, summed over places of each type. St. Paul (V5, still blind) is left out.</p>
</section>

<section>
  <div class="num-tag">What it means</div>
  <h2>Every state's number changes; two pieces still need a look</h2>
  <p>These are the engine's own runs: judgment parameters, the anchor's lognormal draw, each place's own effect, extrapolation noise, the observed floor with its undercount draw, and now the core-city and town terms. Two things are approximations until they are redone for this fit. First, the anchor's judgment slopes (adu_anchor.yaml) are still D-053's. Second, the anchor's lognormal width comes from the profile interval, and only its correlation comes from the new fit's observed information. The D-089 label still applies: every state's range rests mostly on places unlike the ones fitted.</p>
</section>

<section>
  <div class="num-tag">State table</div>
  <h2>P50 and P10–P90 for each run</h2>
  {state_table(runs)}
</section>

<footer>
  <div>Engine: <code>scenarios.adu.run</code>, origin 2025, window 2027–2031, 1,000 draws, seed 20261020; inputs <code>places_from_store</code> from holdout-filtered tables, offline. Parameters: θ 0.448 per 1,000 (suburb), α 1.55, core +1.199 (se 0.411), town prior sd 0.729, m_o 1.0, m_x 0.4. Before: θ 0.308 per 1,000, α 2.317, m_x 1.0 (D-053).</div>
  <div>Sources: <code>reports/adu-types-engine/</code>, <code>scripts/archive/adu_types_engine_check.py</code>, on branch <code>ws/adu-types-engine</code>. Nothing was unblinded.</div>
</footer>
</main>
"""
    (OUT / "results.html").write_text(html)
    print(f"wrote {OUT / 'results.html'}")


if __name__ == "__main__":
    main()
