#!/usr/bin/env python3
# ruff: noqa: E501  (long lines are the HTML/CSS page template)
"""Results page for D-093, the engine wiring of D-091's adopted outcome: reports/adu-engine-drift/.

    uv run python scripts/archive/adu_engine_drift_page.py

Reads `totals.csv` and `by_basis.csv` from `scripts/archive/adu_engine_drift_check.py` (switch off: the A + P
engine of #434; on: own counts × drift); borrows the Lotline stylesheet from the D-089 page. Standard library
and pandas only.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "reports" / "adu-engine-drift"
STYLE_FROM = REPO / "reports" / "adu-state-profiles" / "results.html"
STATES = {"MN": "Minnesota", "NC": "North Carolina", "OH": "Ohio", "TX": "Texas", "OR": "Oregon"}
RUNS = (
    (0, "Before: A + place types, observed rate as a floor", "r-old"),
    (1, "Now: own counts with drift where a place has them", "r-new"),
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


def load() -> dict[int, pd.DataFrame]:
    t = pd.read_csv(OUT / "totals.csv")
    return {f: t[t["own_rate_drift"] == f] for f, _, _ in RUNS}


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


def basis_table() -> str:
    b = pd.read_csv(OUT / "by_basis.csv")
    rows = []
    for st, name in STATES.items():
        g = b[b["state"] == st]
        own0 = g[(g["no_reform_basis"] != "model") & (g["own_rate_drift"] == 0)].iloc[0]
        own1 = g[(g["no_reform_basis"] != "model") & (g["own_rate_drift"] == 1)].iloc[0]
        lots = g[g["own_rate_drift"] == 0]["eligible_parcels"].sum()
        rows.append(
            f"<tr><td>{name}</td><td class='num'>{int(own0.places)}</td>"
            f"<td class='num'>{own0.eligible_parcels / lots:.0%}</td>"
            f"<td class='num'>{fmt(own0.current_rules_adus_mean)} → {fmt(own1.current_rules_adus_mean)}</td>"
            f"<td class='num'>{fmt(own0.adu_permits_added_mean)} → {fmt(own1.adu_permits_added_mean)}</td></tr>"
        )
    return (
        '<div class="scroll"><table><thead><tr><th>State</th><th>Places with own counts</th>'
        "<th>Share of eligible lots</th><th>Current-rules ADUs (mean), before → now</th>"
        "<th>ADU permits added (mean), before → now</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table></div>"
    )


def main() -> None:
    runs = load()
    style = re.search(r"<style>(.*?)</style>", STYLE_FROM.read_text(), re.S).group(1)

    def p(st: str, outcome: str, q: str = "p50") -> list[float]:
        return [float(pick(runs[f], st, outcome)[q]) for f, _, _ in RUNS]

    legend = "".join(f'<span><i class="sw {c}"></i>{t}</span>' for _, t, c in RUNS)
    tx, oh, mn = p("TX", "additional_homes"), p("OH", "additional_homes"), p("MN", "additional_homes")
    tx90 = p("TX", "additional_homes", "p90")
    cur_mn90 = p("MN", "current_rules_adus", "p90")
    html = f"""<title>ADU engine with own counts</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=Public+Sans:wght@400;600;700&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&display=swap">
<style>{style}{EXTRA_CSS}</style>
<main>
<header>
  <div class="eyebrow">Lotline · D-093: the engine reads D-091's adopted outcome · 15 Nov 2026</div>
  <h1>Using each place's own ADU counts barely moves the homes a reform adds, and lowers today's baseline</h1>
  <p class="lede">Where a place has its own ADU counts, the engine now takes its no-reform ADUs from those counts, times a drift of ×2.8 either way at one SD, and scales them by the model's with-reform ÷ no-reform ratio for the Handbook bill. That is the outcome Ben adopted after D-090 and D-091. Elsewhere the A + place-types model runs as before. Additional homes at the median move by 10% or less in every state. The no-reform baseline falls in Minnesota, North Carolina and Ohio, where the model put places with counts above what they actually build, and its top end roughly halves there.</p>
</header>

<div class="stats">
  <div class="stat"><b>{fmt(tx[0])} → {fmt(tx[1])}</b><span>Texas additional homes, 2027–31, P50 (P90 {fmt(tx90[0])} → {fmt(tx90[1])})</span></div>
  <div class="stat"><b>{fmt(oh[0])} → {fmt(oh[1])}</b><span>Ohio additional homes, P50</span></div>
  <div class="stat"><b>{fmt(mn[0])} → {fmt(mn[1])}</b><span>Minnesota additional homes, P50</span></div>
  <div class="stat"><b>{fmt(cur_mn90[0])} → {fmt(cur_mn90[1])}</b><span>Minnesota ADUs under today's rules, P90: the baseline's top end falls by half</span></div>
</div>

<section>
  <div class="num-tag">Finding 1</div>
  <h2>Additional homes from the Handbook ADU reform barely change</h2>
  <p>The reform's effect still comes from the model's ratio, so the added homes stay close to before. Texas and Ohio rise most, by about 9–10% at the median. Texas's P90 rises more, because its six places with counts (Austin among them) hold a sixth of its lots and their drift is wide.</p>
  <div class="legend">{legend}</div>
  {range_chart(runs, "additional_homes", "additional homes, 2027–2031")}
</section>

<section>
  <div class="num-tag">Finding 2</div>
  <h2>ADUs under today's rules fall, and their range narrows</h2>
  <p>Before, a place with counts got the larger of the model's rate and its observed rate. On the whole the model ran higher than those places build, so its spread set the top of the range. Now the place's own rate sets it. Texas barely moves at the median, and Oregon rises a little: their places with counts build about as many as, or more than, the model says.</p>
  <div class="legend">{legend}</div>
  {range_chart(runs, "current_rules_adus", "ADU permits under current rules, 2027–2031")}
</section>

<section>
  <div class="num-tag">Finding 3</div>
  <h2>Which places changed</h2>
  <p>Only places with observed ADU counts change; the rest give identical numbers both ways (same seeds). They are few in Ohio and Texas but hold 16–48% of eligible lots, because they include the big cities.</p>
  {basis_table()}
  <p class="note">Means over 1,000 draws, summed over places. St. Paul (V5, still blind) is left out.</p>
</section>

<section>
  <div class="num-tag">What it cannot say</div>
  <h2>Three limits</h2>
  <ul>
    <li><b>The bill's ratio is unchecked.</b> D-090 found the model within ×2 in 1 of 4 states. The ratio may be better than the level, but no held-out test shows it. The app should label a bill's effect "not checked within ×2".</li>
    <li><b>Independent drift averages out in state totals.</b> Each place draws its own drift, median 1, mean 1.69. Summed over many places, the state total drifts toward the mean, and its range narrows. D-091 found one drift shared by a state covered state totals better; that is a sensitivity, not what runs here.</li>
    <li><b>The drift was learned on a different gap.</b> σ 1.025 comes from forecasting 2021–25 from four years, 2016–19. The engine reads three years, 2023–25, and forecasts 2027–31.</li>
  </ul>
</section>

<section>
  <div class="num-tag">State table</div>
  <h2>P50 and P10–P90, before and now</h2>
  {state_table(runs)}
</section>

<footer>
  <div>Engine: <code>scenarios.adu.run</code>, origin 2025, window 2027–2031, 1,000 draws, seed 20261020, on #434's A + place-types anchor slopes and the 65 fit places' checked rule rows (stack rebased 15 Nov); inputs <code>places_from_store</code> from holdout-filtered tables, offline. New: <code>adu_own_rate_drift</code> 1, <code>adu_drift_sigma</code> 1.025 (config/params/adu.yaml). Set the switch to 0 for the before run.</div>
  <div>Sources: <code>reports/adu-engine-drift/</code>, <code>scripts/archive/adu_engine_drift_check.py</code>, branch <code>ws/adu-engine-drift</code>. Nothing was unblinded.</div>
</footer>
</main>
"""
    (OUT / "results.html").write_text(html)
    print(f"wrote {OUT / 'results.html'}")


if __name__ == "__main__":
    main()
