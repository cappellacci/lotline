# ruff: noqa: E501  (long lines are the HTML/CSS page template)
"""Build the D-096 results page: A + place types on the coverage-fixed rule rows, against the checked rows.

Usage: uv run python scripts/archive/adu_fixed_rows_page.py . reports/adu-types-fixed-rows/results.html
"""

import json
import math
import sys
from pathlib import Path

import pandas as pd

root, out = Path(sys.argv[1]), Path(sys.argv[2])
OLD, NEW = root / "reports/adu-place-types-checked", root / "reports/adu-types-fixed-rows"
ROLD, RNEW = root / "reports/adu-reform-ratio", root / "reports/adu-reform-ratio-fixed-rows"
tokens = (root / "docs/build/identity/tokens.css").read_text()
NAME = {"MN": "Minnesota", "NC": "North Carolina", "TX": "Texas", "OR": "Oregon"}
W = 660


def esc(x):
    return str(x).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def fit(d, form="A+P"):
    f = pd.read_csv(d / "fits.csv")
    return f[(f.variant == "central") & (f.fold == "all") & (f.form == form)].iloc[0]


def tiers(d):
    t = pd.read_csv(d / "tiers.csv")
    return t[(t.form == "A+P") & (t.tier == 1) & t.observed.notna()].set_index("held_out")


so, sn = json.loads((OLD / "summary.json").read_text()), json.loads((NEW / "summary.json").read_text())
fo, fn = fit(OLD), fit(NEW)
to, tn = tiers(OLD), tiers(NEW)
ro, rn = json.loads((ROLD / "summary.json").read_text()), json.loads((RNEW / "summary.json").read_text())
ev_new = pd.read_csv(RNEW / "events_scored.csv")


def range_chart():
    states = [s for s in ("MN", "NC", "TX", "OR") if s in to.index]
    lw, top, gh = 130, 14, 60
    h = top + gh * len(states) + 34
    lo, hi = math.log(10), math.log(3000)

    def sx(v):
        return lw + (math.log(min(max(v, 10), 3000)) - lo) / (hi - lo) * (W - lw - 20)

    g = [
        f'<svg viewBox="0 0 {W} {h}" class="chart" role="img" aria-label="held-out state ranges before and after the fixes">'
    ]
    for t in (10, 30, 100, 300, 1000, 3000):
        g.append(f'<line x1="{sx(t):.1f}" x2="{sx(t):.1f}" y1="{top - 6}" y2="{h - 28}" class="grid"/>')
        g.append(f'<text x="{sx(t):.1f}" y="{h - 14}" class="tick" text-anchor="middle">{t:,}</text>')
    for i, st in enumerate(states):
        y0 = top + gh * i
        g.append(f'<text x="0" y="{y0 + 18}" class="st">{NAME[st]}</text>')
        for j, (tab, cls, _lab) in enumerate(((to, "old", "checked rows"), (tn, "new", "fixed rows"))):
            r = tab.loc[st]
            y = y0 + 8 + 18 * j
            g.append(f'<line x1="{sx(r.p10):.1f}" x2="{sx(r.p90):.1f}" y1="{y}" y2="{y}" class="{cls}"/>')
            g.append(f'<circle cx="{sx(r.p50):.1f}" cy="{y}" r="4" class="{cls}d"/>')
            g.append(
                f'<text x="{sx(r.p90) + 6:.1f}" y="{y + 4}" class="tick">×{r.p90 / max(r.p10, 1):.0f}</text>'
            )
        x = sx(to.loc[st].observed)
        g.append(
            f'<path d="M{x:.1f} {y0 + 1} L{x + 5:.1f} {y0 + 17} L{x:.1f} {y0 + 33} L{x - 5:.1f} {y0 + 17} Z" class="obs"/>'
        )
    g.append(
        f'<text x="{W - 8}" y="{h - 1}" class="tick" text-anchor="end">ADUs counted in the held-out state\'s target places, tier 1 (log scale); ×: P90 ÷ P10</text>'
    )
    g.append("</svg>")
    return "".join(g)


def row(lab, a, b, fmt="{:.3f}"):
    return f"<tr><td class='form'>{lab}</td><td>{fmt.format(a)}</td><td>{fmt.format(b)}</td></tr>"


params = "".join(
    [
        f"<tr><td class='form'>Fit set</td><td>{so['fit_set']['places']} places, {so['fit_set']['place_years']} place-years</td><td>{sn['fit_set']['places']} places, {sn['fit_set']['place_years']} place-years</td></tr>",
        row("θ, ADUs per 1,000 eligible lots a year (suburb)", fo.theta * 1000, fn.theta * 1000),
        row("α, spread of place luck", fo.alpha, fn.alpha),
        row("Core-city term (log)", fo.b_core, fn.b_core, "{:+.2f}"),
        row("m_x, partial rule share", fo.m_other, fn.m_other, "{:.1f}"),
        row("m_o, owner-occupancy share", fo.m_owner, fn.m_owner, "{:.1f}"),
    ]
)


def dec(s, k):
    d = s["decisions"][k]
    return f"{'replaces' if d['decision']['types'] else 'kept'}: {esc(d['decision']['reason'])}"


tests = "".join(
    f"<tr><td class='form'>{lab}</td><td>{a}</td><td>{b}</td></tr>"
    for lab, a, b in [
        ("A + P claim tier", so["claim_tier"]["A+P"], sn["claim_tier"]["A+P"]),
        (
            "A + P useful states, tiers 0 · 1 · 2",
            " · ".join(str(v) for v in so["useful"]["A+P"].values()),
            " · ".join(str(v) for v in sn["useful"]["A+P"].values()),
        ),
        ("A vs A + P (D-088 rule)", dec(so, "A vs A+P"), dec(sn, "A vs A+P")),
        ("A′ vs A′ + P", dec(so, "A′ vs A′+P"), dec(sn, "A′ vs A′+P")),
        ("Reform check (D-095): events", ro["events"], rn["events"]),
        ("Reform check: reading", ro["reading"], rn["reading"]),
        (
            "Reform check: exponent b",
            f"{ro['drift']['M']['b']:.2f} ({ro['drift']['M']['b_low']:.2f}–{ro['drift']['M']['b_high']:.2f})",
            f"{rn['drift']['M']['b']:.2f} ({rn['drift']['M']['b_low']:.2f}–{rn['drift']['M']['b_high']:.2f})",
        ),
    ]
)

html = f"""<title>ADU Refit on Fixed Rules</title>
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
.old {{ stroke: var(--tier-none); stroke-width: 6; stroke-linecap: round; }} .oldd {{ fill: var(--ink-muted); }}
.new {{ stroke: var(--survey); stroke-width: 6; stroke-linecap: round; }} .newd {{ fill: var(--ink); }}
.obs {{ fill: var(--brass); }}
.legend {{ display: flex; flex-wrap: wrap; gap: 14px; font-size: .85rem; color: var(--ink-muted); }}
.legend i {{ display: inline-block; width: 18px; height: 6px; border-radius: 3px; margin-right: 6px; vertical-align: middle; }}
.scroll {{ overflow-x: auto; }}
table {{ border-collapse: collapse; width: 100%; font-variant-numeric: tabular-nums; font-size: .88rem; }}
th, td {{ padding: 6px 8px; border-bottom: 1px solid var(--rule); text-align: right; vertical-align: top; }}
th {{ color: var(--ink-muted); font-weight: 500; font-size: .78rem; text-transform: uppercase; letter-spacing: .05em; }}
td.form, th.form {{ text-align: left; }}
ul {{ margin: 0; padding-left: 20px; display: grid; gap: 6px; max-width: 65ch; }}
.foot {{ color: var(--ink-faint); font-size: .8rem; }}
</style>
<div class="wrap">
<header style="display:grid;gap:8px">
  <div class="kicker">Lotline · ADU model · D-096 · 15 Nov 2026</div>
  <h1>Fixing how rules were coded makes places look less random</h1>
  <p>The coverage audit found rule rows that called "no ADUs" an allowed rule, read lists of every single-family district as three-quarters of a city, and read rural-only rules as citywide. PR #440 corrected 33 rows. This page refits A + place types on them and reruns the tests.</p>
</header>

<div class="cards">
  <div class="card"><span>Spread of place luck (α)</span><b>{fo.alpha:.2f} → {fn.alpha:.2f}</b><span>Some of what looked like places being randomly different was the coding.</span></div>
  <div class="card"><span>Partial-rule share (m_x)</span><b>{fo.m_other:.1f} → {fn.m_other:.1f}</b><span>The engine still runs 0.4 from the old rows.</span></div>
  <div class="card"><span>Reform events in the data</span><b>{ro["events"]} → {rn["events"]}</b><span>Four were placeholders turning into real coding, not reforms.</span></div>
</div>

<section>
  <h2>Held-out state ranges, before and after the fixes</h2>
  <div class="legend"><span><i style="background:var(--tier-none)"></i>checked rows</span><span><i style="background:var(--survey)"></i>fixed rows</span><span>◆ observed</span></div>
  {range_chart()}
  <p>Each state left out and predicted from the others with its 20 largest places' rules (tier 1). Ranges narrow in North Carolina, Texas and Oregon and the medians move toward what was built; every state stays useful.</p>
</section>

<section>
  <h2>Fitted values</h2>
  <div class="scroll"><table><tr><th class="form">A + place types</th><th>Checked rows</th><th>Fixed rows</th></tr>{params}</table></div>
</section>

<section>
  <h2>The same tests, rerun</h2>
  <div class="scroll"><table><tr><th class="form">Test</th><th>Checked rows</th><th>Fixed rows</th></tr>{tests}</table></div>
  <p class="foot">D-088's rule still keeps Form A over A + P only because A passes Texas's test A (College Station) and A + P doesn't; the held-out score gain of A + P stays large ({sn["decisions"]["A vs A+P"]["tier1_log_score_gain"]["gain"]:+.1f}, 2 SE {2 * sn["decisions"]["A vs A+P"]["tier1_log_score_gain"]["se"]:.1f}). Reform check: {rn["events"]} events left ({", ".join(ev_new["name"].str.replace(" city", "").str.replace(" town", ""))}); Raleigh still carries it.</p>
</section>

<section>
  <h2>What this means</h2>
  <ul>
  <li><b>The fixes are improvements</b>, not just changes: less unexplained place-to-place spread, narrower held-out ranges, and the same verdicts.</li>
  <li><b>The engine's config is now two fits behind.</b> It runs m_x 0.4 and core +1.20 from rows before the checks; the fixed rows give m_x {fn.m_other:.1f}, core {fn.b_core:+.2f}, θ {fn.theta * 1000:.3f} per 1,000 and α {fn.alpha:.2f}. Moving config is your call.</li>
  <li><b>The reform ratio stays unproven</b> with six events.</li>
  </ul>
</section>

<p class="foot">Sources: reports/adu-types-fixed-rows/ and reports/adu-reform-ratio-fixed-rows/ (D-088's and D-095's scripts run through scripts/archive/adu_refit_fixed_rows.py on PR #440's rule rows; offline; St. Paul excluded; Cottage Grove 2016–22 and Maplewood 2016–23 left out as unknown). Compared with reports/adu-place-types-checked/ and reports/adu-reform-ratio/. Built by scripts/dev/adu_fixed_rows_page.py.</p>
</div>
"""
out.write_text(html)
print(f"wrote {out}")
