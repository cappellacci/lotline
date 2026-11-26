#!/usr/bin/env python3
# ruff: noqa: E501  (long lines are the HTML/CSS page template)
"""Results page for the anchor draw terms recomputed for Form A + place types: reports/adu-types-slopes/.

    uv run python scripts/archive/adu_types_slopes_page.py

Reads slopes.csv (this run), D-053's slopes from git (`adu_anchor.yaml` at the engine switch, eaa0a15a), and the
statewide totals before (reports/adu-types-engine/totals_types.csv) and after (totals.csv). Borrows the Lotline
stylesheet from the D-089 page.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pandas as pd

from lotline.model.scenarios import adu

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "reports" / "adu-types-slopes"
STYLE_FROM = REPO / "reports" / "adu-state-profiles" / "results.html"
BEFORE_REF = "eaa0a15a"
STATES = {"MN": "Minnesota", "NC": "North Carolina", "OH": "Ohio", "TX": "Texas", "OR": "Oregon"}
LABEL = {
    "adu_rate_semi_elasticity": "Mortgage-rate semi-elasticity",
    "adu_equity_elasticity": "Home-equity elasticity",
    "adu_feasibility_dispersion": "Feasibility spread",
    "cap_rate": "Cap rate",
    "operating_expense_share": "Operating expense share",
    "rental_vacancy_rate": "Rental vacancy",
    "adu_hard_cost_premium": "ADU hard-cost premium",
    "soft_cost_share": "Soft-cost share",
    "adu_margin": "ADU margin",
    "adu_rent_to_median_ratio": "ADU rent ÷ median rent",
    "construction_loan_rate": "Construction loan rate",
    "hard_cost_per_sqft_usd": "Hard cost per sq ft",
    "adu_sqft": "ADU size",
    "average_draw_share": "Average loan draw",
    "construction_years_irc": "Build time",
}
EXTRA_CSS = """
.d-old, .sw.d-old { fill: var(--scenario-baseline); background: var(--scenario-baseline); }
.d-new, .sw.d-new { fill: var(--scenario-adu); background: var(--scenario-adu); }
.chart .grid { stroke: var(--rule); stroke-width: 1; }
.chart .zero { stroke: var(--ink-faint); stroke-width: 1; }
td.up { color: var(--confidence-outside); } td.down { color: var(--confidence-inside); }
"""


def old_slopes() -> dict[str, float]:
    txt = subprocess.run(
        ["git", "show", f"{BEFORE_REF}:config/params/adu_anchor.yaml"],
        capture_output=True,
        text=True,
        check=True,
        cwd=REPO,
    ).stdout
    return {k: float(v) for k, v in re.findall(r"^(anchor_slope_\w+):\n  value: (\S+)", txt, re.M)}


def effects(which: str) -> pd.DataFrame:
    """Change in log θ (or log α) across each parameter's whole low-high range: slope × (high − low)."""
    s = pd.read_csv(OUT / "slopes.csv")
    s = s[s["in_fit"]]
    old = old_slopes()
    spec = adu.specs()
    rows = []
    for r in s.itertuples():
        rng = spec[r.key].high - spec[r.key].low
        rows.append(
            {
                "key": r.key,
                "old": old.get(f"anchor_slope_{which}__{r.key}", 0.0) * rng,
                "new": getattr(r, which) * rng,
                "core": r.core * rng,
            }
        )
    return pd.DataFrame(rows).sort_values("new", key=abs, ascending=False)


def dot_chart(e: pd.DataFrame, label: str) -> str:
    W, left, right, row = 640, 210, 620, 22
    lim = max(e[["old", "new"]].abs().max().max(), 0.05) * 1.1

    def sx(v):
        return left + (right - left) * (v + lim) / (2 * lim)

    g = []
    for i, r in enumerate(e.itertuples()):
        y = 14 + i * row
        g.append(
            f'<text x="{left - 10}" y="{y + 4}" class="lab" text-anchor="end">{LABEL.get(r.key, r.key)}</text>'
        )
        g.append(
            f'<circle cx="{sx(r.old):.1f}" cy="{y}" r="5" class="d-old"/><circle cx="{sx(r.new):.1f}" cy="{y}" r="5" class="d-new"/>'
        )
    h = 14 + len(e) * row
    ticks = "".join(
        f'<line x1="{sx(v):.1f}" x2="{sx(v):.1f}" y1="2" y2="{h - 8}" class="{"zero" if v == 0 else "grid"}"/>'
        f'<text x="{sx(v):.1f}" y="{h + 6}" class="tick" text-anchor="middle">{v:+.2f}</text>'
        for v in (-lim / 1.1, -lim / 2.2, 0.0, lim / 2.2, lim / 1.1)
    )
    return (
        f'<svg viewBox="0 0 {W} {h + 24}" class="chart" role="img" aria-label="{label}">{ticks}{"".join(g)}'
        f'<text x="{right}" y="{h + 20}" class="tick" text-anchor="end">{label}</text></svg>'
    )


def totals_table() -> str:
    a = pd.read_csv(REPO / "reports" / "adu-types-engine" / "totals_types.csv")
    b = pd.read_csv(OUT / "totals.csv")
    m = a.merge(b, on=["state", "period", "outcome"], suffixes=("_old", "_new"))
    rows = []
    for st, name in STATES.items():
        for outcome, lab in (
            ("additional_homes", "Additional homes"),
            ("current_rules_adus", "Current-rules ADUs"),
        ):
            r = m[(m["state"] == st) & (m["outcome"] == outcome)].iloc[0]
            cells = ""
            for q in ("p10", "p50", "p90"):
                ch = r[f"{q}_new"] / r[f"{q}_old"] - 1
                cls = "up" if ch > 0.005 else "down" if ch < -0.005 else ""
                cells += f"<td class='num'>{r[f'{q}_old']:,.0f} → {r[f'{q}_new']:,.0f}</td><td class='num {cls}'>{ch:+.1%}</td>"
            rows.append(
                f"<tr><td>{name if outcome == 'additional_homes' else ''}</td><td>{lab}</td>{cells}</tr>"
            )
    return (
        '<div class="scroll"><table><thead><tr><th>State</th><th>2027–2031</th><th>P10</th><th></th><th>P50</th><th></th>'
        f"<th>P90</th><th></th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>"
    )


def main() -> None:
    style = re.search(r"<style>(.*?)</style>", STYLE_FROM.read_text(), re.S).group(1)
    th, al = effects("theta"), effects("alpha")
    core_max = th["core"].abs().max()
    legend = '<span><i class="sw d-old"></i>D-053 fit (used until now)</span><span><i class="sw d-new"></i>Form A + place types fit (now)</span>'
    html = f"""<title>ADU anchor slopes</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=Public+Sans:wght@400;600;700&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&display=swap">
<style>{style}{EXTRA_CSS}</style>
<main>
<header>
  <div class="eyebrow">Lotline · ADU anchor draw terms for Form A + place types · 14 Nov 2026</div>
  <h1>Recomputing the anchor's slopes for the new fit moves state totals by a few percent</h1>
  <p class="lede">Each simulation draw shifts the ADU anchor θ and the place-effect variance α with the cost and market assumptions they were fitted at. Those shifts were still the ones measured for the old D-053 fit. Refit on D-088's 64 places with each assumption nudged, θ's shifts are nearly unchanged and α's are smaller. Statewide additional homes move by under 3.5% at the median and under 6% at P90.</p>
</header>

<div class="stats">
  <div class="stat"><b>15 of 24</b><span>judgment parameters the fit depends on; the other 9 leave it unchanged</span></div>
  <div class="stat"><b>±3.4%</b><span>largest change in a state's median additional homes (Texas, down)</span></div>
  <div class="stat"><b>≤ {core_max:.2f}</b><span>largest shift in the core-city term across any parameter's whole range (its SE is 0.41), so it gets no slope</span></div>
</div>

<section>
  <div class="num-tag">Finding 1</div>
  <h2>How much θ moves across each assumption's whole range</h2>
  <p>Change in log θ from the low to the high end of each parameter's range. The mortgage-rate and home-equity elasticities matter most, as before; the new fit leans on them slightly more.</p>
  <div class="legend">{legend}</div>
  {dot_chart(th, "change in log θ, low to high end of the parameter's range")}
</section>

<section>
  <div class="num-tag">Finding 2</div>
  <h2>α moves less than it did</h2>
  <p>With the core-city term in the fit, cost and market assumptions shift α about half as much as before: part of what α used to absorb (big cities building more) now sits in the core term.</p>
  <div class="legend">{legend}</div>
  {dot_chart(al, "change in log α, low to high end of the parameter's range")}
</section>

<section>
  <div class="num-tag">Finding 3</div>
  <h2>Statewide totals, before and after the new slopes</h2>
  {totals_table()}
  <p class="note">Same engine, inputs, draws (1,000) and seed; only adu_anchor.yaml differs. St. Paul (V5, still blind) is left out.</p>
</section>

<footer>
  <div>Slopes: <code>scripts/archive/adu_types_slopes.py</code>, central ± 10% of each range, θ, α and the core term refit at m_o 1.0, m_x 0.4; central refit reproduces D-088 (θ 0.4476 per 1,000, α 1.550, core +1.199). Observed information: log-SE θ 0.191, α 0.239, correlation 0.115.</div>
  <div>Sources: <code>reports/adu-types-slopes/</code>, on branch <code>ws/adu-types-slopes</code>. Run offline; nothing unblinded.</div>
</footer>
</main>
"""
    (OUT / "results.html").write_text(html)
    print(f"wrote {OUT / 'results.html'}")


if __name__ == "__main__":
    main()
