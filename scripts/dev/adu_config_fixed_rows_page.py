# ruff: noqa: E501  (long lines are the HTML/CSS page template)
"""Build the D-096 config page: the ADU engine's statewide results before and after the config change.

Usage: uv run python scripts/dev/adu_config_fixed_rows_page.py . reports/adu-config-fixed-rows/results.html

Three engine runs (`adu_engine_drift_check.py`, own counts with drift on, 1,000 draws, origin 2025): today's
config on the checked rows (`reports/adu-engine-drift/`), today's config on PR #440's fixed rows, and D-096's
config on the fixed rows (`reports/adu-config-fixed-rows/old-params/`, `new-params/`).
"""

import math
import sys
from pathlib import Path

import pandas as pd

root, out = Path(sys.argv[1]), Path(sys.argv[2])
RUNS = {
    "now": root / "reports/adu-engine-drift/totals.csv",
    "rows": root / "reports/adu-config-fixed-rows/old-params/totals.csv",
    "new": root / "reports/adu-config-fixed-rows/new-params/totals.csv",
}
LAB = {"now": "Today's engine", "rows": "Fixed rule rows, old values", "new": "Fixed rows, D-096 values"}
NAME = {"MN": "Minnesota", "NC": "North Carolina", "OH": "Ohio", "TX": "Texas", "OR": "Oregon"}
tokens = (root / "docs/build/identity/tokens.css").read_text()
W = 660

t = pd.concat([pd.read_csv(p).assign(run=k) for k, p in RUNS.items()])
t = t[t.own_rate_drift == 1].set_index(["run", "state", "outcome"])


def esc(x):
    return str(x).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def chart(outcome="additional_homes"):
    states = ["MN", "NC", "OH", "TX", "OR"]
    lw, top, gh = 130, 14, 72
    h = top + gh * len(states) + 34
    lo, hi = math.log(3), math.log(40000)

    def sx(v):
        return lw + (math.log(min(max(v, 3), 40000)) - lo) / (hi - lo) * (W - lw - 60)

    g = [
        f'<svg viewBox="0 0 {W} {h}" class="chart" role="img" aria-label="additional homes by state, three runs">'
    ]
    for v in (10, 100, 1000, 10000):
        g.append(f'<line x1="{sx(v):.1f}" x2="{sx(v):.1f}" y1="{top - 6}" y2="{h - 28}" class="grid"/>')
        g.append(f'<text x="{sx(v):.1f}" y="{h - 14}" class="tick" text-anchor="middle">{v:,}</text>')
    for i, st in enumerate(states):
        y0 = top + gh * i
        g.append(f'<text x="0" y="{y0 + 22}" class="st">{NAME[st]}</text>')
        for j, run in enumerate(("now", "rows", "new")):
            r = t.loc[(run, st, outcome)]
            y = y0 + 8 + 18 * j
            g.append(f'<line x1="{sx(r.p10):.1f}" x2="{sx(r.p90):.1f}" y1="{y}" y2="{y}" class="r{j}"/>')
            g.append(f'<circle cx="{sx(r.p50):.1f}" cy="{y}" r="4" class="d{j}"/>')
            g.append(f'<text x="{sx(r.p90) + 6:.1f}" y="{y + 4}" class="tick">{r.p50:,.0f}</text>')
    g.append(
        f'<text x="{W - 8}" y="{h - 1}" class="tick" text-anchor="end">additional homes from ADUs, 2027–31: P10–P90, dot and label at P50 (log scale)</text>'
    )
    g.append("</svg>")
    return "".join(g)


def table(outcome):
    rows = []
    for st in ("MN", "NC", "OH", "TX", "OR"):
        cells = []
        for run in ("now", "rows", "new"):
            r = t.loc[(run, st, outcome)]
            cells.append(f"<td>{r.p50:,.0f}<small>{r.p10:,.0f}–{r.p90:,.0f}</small></td>")
        rows.append(f"<tr><td class='form'>{NAME[st]}</td>{''.join(cells)}</tr>")
    head = "".join(f"<th>{LAB[k]}</th>" for k in ("now", "rows", "new"))
    return (
        f"<div class='scroll'><table><tr><th class='form'>State</th>{head}</tr>{''.join(rows)}</table></div>"
    )


def ratio(st, outcome="additional_homes"):
    return t.loc[("new", st, outcome)].p50 / t.loc[("now", st, outcome)].p50


html = f"""<title>ADU Config Update</title>
<meta name="claude:viewport-fit-sides" content="cover">
<style>
{tokens}
body {{ background: var(--paper); color: var(--ink); font-family: var(--font-body, Inter, system-ui, sans-serif); font-size: 15px; line-height: 1.55; }}
.wrap {{ max-width: 760px; margin: 0 auto; padding-block: 32px 64px; padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); display: grid; gap: 28px; }}
h1, h2 {{ font-family: var(--font-display, "Space Grotesk", system-ui, sans-serif); text-wrap: balance; margin: 0; }}
h1 {{ font-size: 1.9rem; line-height: 1.15; }} h2 {{ font-size: 1.2rem; }}
.kicker {{ text-transform: uppercase; letter-spacing: .08em; font-size: .75rem; color: var(--ink-muted); }}
p {{ margin: 0; max-width: 65ch; }} section {{ display: grid; gap: 12px; }}
.cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; }}
.card {{ background: var(--paper-raised); border: 1px solid var(--rule); border-radius: 8px; padding: 14px 16px; display: grid; gap: 4px; }}
.card b {{ font-family: var(--font-display, "Space Grotesk", sans-serif); font-size: 1.6rem; }}
.card span {{ color: var(--ink-muted); font-size: .85rem; }}
.chart {{ width: 100%; height: auto; display: block; }}
.chart text {{ fill: var(--ink-muted); font-size: 11px; font-family: inherit; }}
.chart .st {{ fill: var(--ink); font-weight: 600; font-size: 12.5px; }}
.grid {{ stroke: var(--rule); stroke-width: 1; }}
.r0 {{ stroke: var(--tier-none); stroke-width: 6; stroke-linecap: round; }} .d0 {{ fill: var(--ink-muted); }}
.r1 {{ stroke: var(--tier-3); stroke-width: 6; stroke-linecap: round; }} .d1 {{ fill: var(--ink-muted); }}
.r2 {{ stroke: var(--survey); stroke-width: 6; stroke-linecap: round; }} .d2 {{ fill: var(--ink); }}
.legend {{ display: flex; flex-wrap: wrap; gap: 14px; font-size: .85rem; color: var(--ink-muted); }}
.legend i {{ display: inline-block; width: 18px; height: 6px; border-radius: 3px; margin-right: 6px; vertical-align: middle; }}
.scroll {{ overflow-x: auto; }}
table {{ border-collapse: collapse; width: 100%; font-variant-numeric: tabular-nums; font-size: .88rem; }}
th, td {{ padding: 6px 8px; border-bottom: 1px solid var(--rule); text-align: right; vertical-align: top; }}
td small {{ display: block; color: var(--ink-faint); font-size: .75rem; }}
th {{ color: var(--ink-muted); font-weight: 500; font-size: .78rem; text-transform: uppercase; letter-spacing: .05em; }}
td.form, th.form {{ text-align: left; }}
ul {{ margin: 0; padding-left: 20px; display: grid; gap: 6px; max-width: 65ch; }}
.foot {{ color: var(--ink-faint); font-size: .8rem; }}
</style>
<div class="wrap">
<header style="display:grid;gap:8px">
  <div class="kicker">Lotline · ADU engine · D-096 config · 15 Nov 2026</div>
  <h1>New fit, about half the added homes</h1>
  <p>The engine's ADU values now come from the refit on the corrected rule rows. The Handbook bill's added homes fall by about half in every state. Almost all of the change comes from one number: how much a "partial" local rule already allows.</p>
</header>

<div class="cards">
  <div class="card"><span>Partial-rule share (m_x)</span><b>0.4 → 0.7</b><span>A partial rule already gets 70% of full uptake, so lifting it to the Handbook adds 43%, not 150%.</span></div>
  <div class="card"><span>Additional homes, P50</span><b>×{min(ratio(x) for x in NAME):.2f} to ×{max(ratio(x) for x in NAME):.2f}</b><span>New ÷ today, by state. The rule-row fixes alone move little; the new values do it.</span></div>
  <div class="card"><span>ADUs under today's rules</span><b>about flat</b><span>Own counts set the no-reform rate (D-093), so the baseline barely moves.</span></div>
</div>

<section>
  <h2>Additional homes from the Handbook ADU bill, 2027–31</h2>
  <div class="legend"><span><i style="background:var(--tier-none)"></i>{LAB["now"]}</span><span><i style="background:var(--tier-3)"></i>{LAB["rows"]}</span><span><i style="background:var(--survey)"></i>{LAB["new"]}</span></div>
  {chart()}
  {table("additional_homes")}
</section>

<section>
  <h2>ADUs under today's rules (the baseline)</h2>
  {table("current_rules_adus")}
</section>

<section>
  <h2>What changed in config</h2>
  <div class="scroll"><table>
  <tr><th class="form">Parameter</th><th>Was</th><th>Now</th></tr>
  <tr><td class="form">Partial-rule share m_x</td><td>0.4</td><td>0.7 (interval 0.7–0.8)</td></tr>
  <tr><td class="form">Owner-occupancy share m_o</td><td>1.0</td><td>1.0</td></tr>
  <tr><td class="form">Suburb ADU rate θ, per 1,000 lots a year</td><td>0.448 (0.330–0.624)</td><td>0.240 (0.181–0.327)</td></tr>
  <tr><td class="form">Spread of place luck α</td><td>1.55 (1.05–2.30)</td><td>1.44 (0.98–2.12)</td></tr>
  <tr><td class="form">Core-city term</td><td>+1.199 (×3.3)</td><td>+1.670 (×5.3)</td></tr>
  <tr><td class="form">Town prior SD</td><td>0.729</td><td>1.015</td></tr>
  <tr><td class="form">Anchor slopes and information terms</td><td>64 places, 395 place-years</td><td>63 places, 446 place-years</td></tr>
  </table></div>
</section>

<section>
  <h2>What to know</h2>
  <ul>
  <li><b>m_x is fixed in a run.</b> Its leave-one-state-out values run from 0.4 (without Oregon) to 1.0 (without North Carolina), so the result's range does not yet carry that uncertainty. At 1.0 a partial rule already counts in full and the bill adds nothing there; at 0.4 it adds 150%.</li>
  <li><b>The rule fixes depend on PR #440.</b> These runs read its rows; the config is on PR #437's branch and fits them, so #440 should merge first.</li>
  </ul>
</section>

<p class="foot">Engine: scripts/dev/adu_engine_drift_check.py, 1,000 draws, origin 2025, own counts with drift on (D-093), St. Paul left out, offline. The fixed-row runs read PR #440's rule rows from a scratch checkout of that branch with the config shown. Built by scripts/dev/adu_config_fixed_rows_page.py.</p>
</div>
"""
out.write_text(html)
print(f"wrote {out}")
