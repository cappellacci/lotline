# ruff: noqa: E501  (long lines are the HTML/CSS page template)
"""Build the results page for D-088 rescored on the checked rule rows: reports/adu-place-types (old rows)
against reports/adu-place-types-checked (#419's rows).

Usage: uv run python scripts/dev/adu_types_checked_page.py . reports/adu-place-types-checked/results.html
"""

import json
import math
import sys
from pathlib import Path

import pandas as pd

root, out = Path(sys.argv[1]), Path(sys.argv[2])
old_dir, new_dir = root / "reports/adu-place-types", root / "reports/adu-place-types-checked"
told, tnew = pd.read_csv(old_dir / "tiers.csv"), pd.read_csv(new_dir / "tiers.csv")
dnew = pd.read_csv(new_dir / "test_d_states.csv")
summ = json.loads((new_dir / "summary.json").read_text())
fits = pd.read_csv(new_dir / "fits.csv")
tokens = (root / "docs/build/identity/tokens.css").read_text()
STATES = ["MN", "NC", "TX", "OR"]
NAME = {"MN": "Minnesota", "NC": "North Carolina", "TX": "Texas", "OR": "Oregon"}
W, LW = 660, 190


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def row(t, form, st, tier):
    r = t[(t.form == form) & (t.held_out == st) & (t.tier == tier)]
    return None if r.empty else r.iloc[0]


def range_chart(tier):
    """Per state: P10-P90 bar and P50 tick for three versions, observed as a diamond. Log scale."""
    versions = [
        ("Form A, checked rows", tnew, "A", "v-a"),
        ("A + types, old rows", told, "A+P", "v-old"),
        ("A + types, checked rows", tnew, "A+P", "v-new"),
    ]
    lo, hi = math.log(5), math.log(3000)
    top, gh, rh = 14, 24 + 18 * len(versions), 18

    def sx(v):
        v = min(max(v, 5), 3000)
        return LW + (math.log(v) - lo) / (hi - lo) * (W - LW - 16)

    h = top + gh * len(STATES) + 34
    g = [f'<svg viewBox="0 0 {W} {h}" class="chart" role="img" aria-label="tier {tier} ranges by state">']
    for t in (10, 30, 100, 300, 1000, 3000):
        g.append(f'<line x1="{sx(t):.1f}" x2="{sx(t):.1f}" y1="{top - 6}" y2="{h - 28}" class="grid"/>')
        g.append(f'<text x="{sx(t):.1f}" y="{h - 12}" class="tick" text-anchor="middle">{t:,}</text>')
    for i, st in enumerate(STATES):
        y0 = top + gh * i
        g.append(f'<text x="8" y="{y0 + 12}" class="st">{NAME[st]}</text>')
        obs = row(tnew, "A+P", st, tier).observed
        for j, (lab, t, form, cls) in enumerate(versions):
            r = row(t, form, st, tier)
            y = y0 + 24 + rh * j
            g.append(f'<text x="{LW - 10}" y="{y + 4}" class="lab" text-anchor="end">{esc(lab)}</text>')
            g.append(
                f'<rect x="{sx(r.p10):.1f}" y="{y - 4}" width="{max(sx(r.p90) - sx(r.p10), 2):.1f}" height="8" rx="4" class="{cls}"/>'
            )
            g.append(
                f'<line x1="{sx(r.p50):.1f}" x2="{sx(r.p50):.1f}" y1="{y - 7}" y2="{y + 7}" class="med"/>'
            )
            ok = "✓" if r.useful else ""
            g.append(f'<text x="{W - 4}" y="{y + 4}" class="ok" text-anchor="end">{ok}</text>')
        x = sx(obs)
        yt, yb = y0 + 16, y0 + 24 + rh * (len(versions) - 1) + 8
        g.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{yt}" y2="{yb}" class="obs-line"/>')
        g.append(f'<path d="M{x:.1f} {yt - 5}l5 5l-5 5l-5-5z" class="obs"/>')
        old_obs = row(told, "A+P", st, tier).observed
        lx, anc = (x - 8, "end") if x > W - 220 else (x + 8, "start")
        if abs(old_obs - obs) > 0.5:
            g.append(
                f'<text x="{lx:.1f}" y="{yt + 3}" class="tick" text-anchor="{anc}">observed {obs:,.0f} (old rows {old_obs:,.0f})</text>'
            )
        else:
            g.append(
                f'<text x="{lx:.1f}" y="{yt + 3}" class="tick" text-anchor="{anc}">observed {obs:,.0f}</text>'
            )
    g.append(
        f'<text x="{W - 16}" y="{h - 1}" class="tick" text-anchor="end">ADUs counted in the held-out state\'s target places (log scale)</text>'
    )
    g.append("</svg>")
    return "".join(g)


def ratio_cell(r):
    if r is None or pd.isna(r.obs_over_p50):
        return "<td>—</td>"
    v = r.obs_over_p50
    cls = "good" if r.useful else ("edge" if r.inside else "bad")
    return f'<td class="{cls}">{v:.2f}</td>'


def tier_table():
    lines = []
    for lab, t, form in [
        ("Form A", tnew, "A"),
        ("A′ (owner share)", tnew, "A′"),
        ("A + types, old rows (D-088)", told, "A+P"),
        ("A + types, checked rows", tnew, "A+P"),
        ("A′ + types, checked rows", tnew, "A′+P"),
    ]:
        for tier in (0, 1, 2):
            rs = [row(t, form, s, tier) for s in STATES]
            n = sum(bool(r.useful) for r in rs if r is not None)
            first = f'<td rowspan="3" class="form">{esc(lab)}</td>' if tier == 0 else ""
            lines.append(
                f"<tr>{first}<td>{tier}</td>{''.join(ratio_cell(r) for r in rs)}<td class='num'><b>{n}</b> of 4</td></tr>"
            )
    return "".join(lines)


def test_d_table():
    lines = []
    for f, lab in [
        ("A", "Form A"),
        ("A+P", "A + types"),
        ("A′+P", "A′ + types"),
        ("persistence", "Own past rate"),
    ]:
        cells = []
        for s in STATES:
            r = dnew[(dnew.forecast == f) & (dnew.state == s)].iloc[0]
            cls = "good" if r.useful else ("edge" if r.within_2x else "bad")
            cells.append(f'<td class="{cls}">{r.obs_over_p50:.2f}</td>')
        lines.append(f"<tr><td class='form'>{lab}</td>{''.join(cells)}</tr>")
    return "".join(lines)


dec = summ["decisions"]["A vs A+P"]
fa = fits[(fits.variant == "central") & (fits.fold == "all")].set_index("form")
ap = fa.loc["A+P"]

html = f"""<title>ADU Place Types, Checked Rows</title>
<meta name="claude:viewport-fit-sides" content="cover">
<style>
{tokens}
:root {{ --v-a: var(--tier-none); --v-old: var(--tier-1); --v-new: var(--survey); }}
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
.chart .lab {{ fill: var(--ink-muted); }} .chart .ok {{ fill: var(--confidence-inside); font-size: 13px; }}
.grid {{ stroke: var(--rule); stroke-width: 1; }}
.v-a {{ fill: var(--v-a); }} .v-old {{ fill: var(--v-old); }} .v-new {{ fill: var(--v-new); }}
.med {{ stroke: var(--ink); stroke-width: 2; }}
.obs {{ fill: var(--brass); }} .obs-line {{ stroke: var(--brass); stroke-dasharray: 3 3; }}
.scroll {{ overflow-x: auto; }}
table {{ border-collapse: collapse; width: 100%; font-variant-numeric: tabular-nums; font-size: .9rem; }}
th, td {{ padding: 6px 8px; border-bottom: 1px solid var(--rule); text-align: right; }}
th {{ color: var(--ink-muted); font-weight: 500; font-size: .8rem; text-transform: uppercase; letter-spacing: .05em; }}
td.form, th.form {{ text-align: left; }} td.form {{ color: var(--ink); }}
td.good {{ color: var(--confidence-inside); font-weight: 600; }} td.edge {{ color: var(--confidence-edge); }} td.bad {{ color: var(--confidence-outside); }}
.legend {{ display: flex; flex-wrap: wrap; gap: 14px; font-size: .85rem; color: var(--ink-muted); }}
.legend i {{ display: inline-block; width: 18px; height: 8px; border-radius: 4px; margin-right: 6px; vertical-align: middle; }}
.call {{ background: var(--paper-sunken); border-left: 3px solid var(--brass); padding: 14px 16px; border-radius: 4px; display: grid; gap: 8px; }}
ul {{ margin: 0; padding-left: 20px; display: grid; gap: 4px; max-width: 65ch; }}
.foot {{ color: var(--ink-faint); font-size: .8rem; }}
</style>
<div class="wrap">
<header style="display:grid;gap:8px">
  <div class="kicker">Lotline · ADU model · D-088 rescored · 15 Nov 2026</div>
  <h1>Place types on the checked rule rows: the first form to pass the transfer test</h1>
  <p>D-088's run, repeated unchanged on the source-checked local ADU rules (#419). With each state left out in turn,
  A + place types lands inside its range and within ×2 in all four states that have counts, at tiers 1 and 2.
  D-088's own decision rule still keeps Form A, on one place.</p>
</header>

<div class="cards">
  <div class="card"><span>Useful states, tier 1</span><b>4 of 4</b><span>A + types; was 3 of 4 on the old rows. Form A: 0 of 4.</span></div>
  <div class="card"><span>Held-out log score over Form A</span><b>+{dec["tier1_log_score_gain"]["gain"]:.1f}</b><span>2 SE = {2 * dec["tier1_log_score_gain"]["se"]:.1f}; 64 places</span></div>
  <div class="card"><span>Core city vs suburb</span><b>×{math.exp(ap.b_core):.1f}</b><span>β {ap.b_core:+.2f} ({ap.b_core_low:+.2f} to {ap.b_core_high:+.2f}); was ×3.3</span></div>
</div>

<section>
  <h2>Tier 1: each state predicted from the other states plus its 20 largest places' rules</h2>
  <div class="legend"><span><i style="background:var(--v-a)"></i>Form A</span><span><i style="background:var(--v-old)"></i>A + types, old rows</span><span><i style="background:var(--v-new)"></i>A + types, checked rows</span><span>Bar P10–P90, tick median, <span style="color:var(--brass)">◆ observed</span>, ✓ useful</span></div>
  {range_chart(1)}
  <p>Every state's range on the checked rows contains what was built, and every median is within ×2. The ranges are wide: P90 is ×4 the P10 in Minnesota and ×22–71 elsewhere.</p>
</section>

<section>
  <h2>Observed ÷ median, every form and tier</h2>
  <div class="scroll"><table>
  <tr><th class="form">Form</th><th>Tier</th>{"".join(f"<th>{s}</th>" for s in STATES)}<th>Useful</th></tr>
  {tier_table()}
  </table></div>
  <p class="foot">Green: useful (inside P10–P90 and within ×2). Amber: inside the range, outside ×2. Purple: outside the range. Ohio has no target places with counts, so it can't be scored; "4 of 4" is all the states that can be.</p>
</section>

<section>
  <h2>The decision rule keeps Form A, on College Station</h2>
  <div class="call">
  <p>D-088's rule needs all three: a lower passing tier <b>(met: tier 1 against none)</b>; at least as many of tests A–B
  <b>(missed: 1 against 2)</b>; test D not worse by more than 2 SE <b>(met: {dec["test_d_gain"]["gain"]:+.1f}, 2 SE {2 * dec["test_d_gain"]["se"]:.1f})</b>.</p>
  <p>Form A's extra pass is test A in Texas, which is one city: College Station built about 5 ADUs; Form A's median is 6,
  A + types' 25 (inside its range, outside ×2). It is the same single place that decided D-087's step 1.</p>
  </div>
</section>

<section>
  <h2>Test D: forecasting 2021–2025 from 2016–2020 inside each state</h2>
  <div class="scroll"><table>
  <tr><th class="form">Forecast</th>{"".join(f"<th>{s}</th>" for s in STATES)}</tr>
  {test_d_table()}
  </table></div>
  <p>Observed ÷ median. No form is useful in any state over time: every form forecasts Minnesota about ×2.6 too high and North Carolina ×1.6 too low. Types help Minnesota (0.23 → 0.38) and change nothing elsewhere. This is what D-091's drift term and the D-093 engine path address.</p>
</section>

<section>
  <h2>What it means, and what it doesn't</h2>
  <ul>
  <li>With coded rules for a state's 20 largest places (tier 1), A + types transfers to every state we can test. National data alone (tier 0) works only in Minnesota.</li>
  <li>The four states also informed the rule coding and the choice of types, so this is not a blind test. St. Paul (V5) and the V9 Oregon holdout are the clean checks and were not touched.</li>
  <li>The fit moved: θ {ap.theta * 1000:.3f} per 1,000 lots (was 0.448), α {ap.alpha:.2f}, m_x 0.8 (was 0.4). The engine still runs on the old-row values; nothing was written to config.</li>
  </ul>
</section>

<p class="foot">Source: reports/adu-place-types-checked/ (run at a40c09cf, offline, St. Paul excluded). Method: D-088 in docs/analysis_plan.md, with the 2026-11-15 rescoring note. Built by scripts/dev/adu_types_checked_page.py.</p>
</div>
"""
out.write_text(html)
print(f"wrote {out}")
