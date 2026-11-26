# ruff: noqa: E501  (long lines are the HTML/CSS page template)
"""Build the D-089 results page from reports/adu-state-profiles (profiles.csv, evidence.csv, summary.json).

Usage: uv run python scripts/archive/adu_profiles_page.py . reports/adu-state-profiles/results.html
"""

import json
import sys
from pathlib import Path

import pandas as pd

root, out = Path(sys.argv[1]), Path(sys.argv[2])
rep = root / "reports/adu-state-profiles"
prof = pd.read_csv(rep / "profiles.csv")
summ = json.loads((rep / "summary.json").read_text())
tokens = (root / "docs/build/identity/tokens.css").read_text()
W, LW = 640, 150
STATES = ("MN", "NC", "OH", "TX", "OR")
NAME = {
    "MN": "Minnesota",
    "NC": "North Carolina",
    "OH": "Ohio",
    "TX": "Texas",
    "OR": "Oregon",
    "fit set": "Fit set (64)",
}
TYPES = (("core", "Core cities", "seg-core"), ("suburb", "Suburbs", "seg-sub"), ("town", "Towns", "seg-town"))


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def stacked(rows, label, axis):
    """Horizontal 100% bars: each row a list of (share, css class, text)."""
    top, rh = 10, 30
    h = top + rh * len(rows) + 30
    x0, x1 = LW, W - 10
    g = [f'<svg viewBox="0 0 {W} {h}" class="chart" role="img" aria-label="{esc(label)}">']
    for i, (name, segs) in enumerate(rows):
        y = top + rh * i
        g.append(f'<text x="{LW - 10}" y="{y + 15}" class="lab" text-anchor="end">{esc(name)}</text>')
        x = x0
        for share, cls, txt in segs:
            w = share * (x1 - x0)
            g.append(f'<rect x="{x:.1f}" y="{y + 2}" width="{max(w - 1, 0):.1f}" height="18" class="{cls}"/>')
            if w > 34:
                g.append(f'<text x="{x + 5:.1f}" y="{y + 15}" class="seg">{esc(txt)}</text>')
            x += w
    for t in (0, 0.25, 0.5, 0.75, 1):
        xx = x0 + t * (x1 - x0)
        g.append(f'<text x="{xx:.1f}" y="{h - 8}" class="tick" text-anchor="middle">{t:.0%}</text>')
    g.append(f'<text x="{x1}" y="{h + 6}" class="tick" text-anchor="end">{esc(axis)}</text>')
    g.append("</svg>")
    return "".join(g)


mix_rows = []
for st in (*STATES, "fit set"):
    p = prof[prof.state == st].set_index("type")
    segs = [
        (
            float(p.loc[t, "lot_share"]) if t in p.index else 0.0,
            cls,
            f"{lab.split()[0]} {p.loc[t, 'lot_share']:.0%}" if t in p.index else "",
        )
        for t, lab, cls in TYPES
    ]
    mix_rows.append((NAME[st], segs))

ev = summ["evidence"]
tot = summ["totals"]
ev_rows = []
for st in STATES:
    e = ev[st]
    ev_rows.append(
        (
            NAME[st],
            [
                (e["is_town"], "seg-town", f"towns {e['is_town']:.0%}"),
                (e["beyond_range"], "seg-out", f"beyond {e['beyond_range']:.0%}"),
                (1 - e["outside"], "seg-in", f"inside {1 - e['outside']:.0%}"),
            ],
        )
    )
adu_rows = []
for st in STATES:
    a = tot[st]["towns as suburbs"]
    o = a["share_from_outside"]
    adu_rows.append(
        (NAME[st], [(o, "seg-out", f"outside {o:.0%}"), (1 - o, "seg-in", f"inside {1 - o:.0%}")])
    )

ptab = []
for st in (*STATES, "fit set"):
    for t, lab, _ in TYPES:
        r = prof[(prof.state == st) & (prof.type == t)]
        if r.empty:
            continue
        r = r.iloc[0]
        ptab.append(
            f"<tr><td>{NAME[st] if t == 'core' else ''}</td><td>{lab}</td><td class='num'>{int(r.jurisdictions):,}</td>"
            f"<td class='num'>{r['pop'] / 1e6:.2f}M</td><td class='num'>{r.lots / 1e3:,.0f}k</td><td class='num'>{r.lot_share:.0%}</td>"
            f"<td class='num'>${r.home_value / 1e3:,.0f}k</td><td class='num'>${r.rent:,.0f}</td><td class='num'>{r.owner:.0%}</td></tr>"
        )
ttab = []
for st in STATES:
    a, b = tot[st]["towns as suburbs"], tot[st]["town prior"]
    ttab.append(
        f"<tr><td>{NAME[st]}</td><td class='num'>{a['p10']:,.0f}–{a['p50']:,.0f}–{a['p90']:,.0f}</td>"
        f"<td class='num'>{b['p10']:,.0f}–{b['p50']:,.0f}–{b['p90']:,.0f}</td><td class='num'>{b['share_from_towns']:.0%}</td>"
        f"<td class='num'>{a['share_from_outside']:.0%}</td></tr>"
    )
dr = summ["beyond_range_by_measure_non_town_lot_share"]
dtab = "".join(
    f"<tr><td>{NAME[st]}</td>"
    + "".join(f"<td class='num'>{dr[st][m]:.0%}</td>" for m in ("home_value", "rent", "owner", "lots"))
    + "</tr>"
    for st in STATES
)
fr = summ["fit_ranges"]
win = tot["MN"]["window"]

html = f"""<title>ADU state profiles</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=Public+Sans:wght@400;600;700&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&display=swap">
<style>
/* Layout: one reading column; headline, stats, numbered findings with charts, then tables. */
{tokens}
body {{ background: var(--paper); color: var(--ink); font-family: var(--font-sans); font-size: 15px; line-height: 1.55;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); padding-block: var(--space-7); }}
main {{ max-width: 720px; margin: 0 auto; display: flex; flex-direction: column; gap: var(--space-7); }}
header, section {{ display: flex; flex-direction: column; gap: var(--space-3); }}
.eyebrow, .num-tag {{ font-family: var(--font-mono); font-size: 12px; letter-spacing: .06em; text-transform: uppercase; color: var(--ink-muted); }}
.num-tag {{ color: var(--survey); }}
h1 {{ font-family: var(--font-serif); font-weight: 600; font-size: 32px; line-height: 1.15; margin: 0; text-wrap: balance; }}
h2 {{ font-family: var(--font-serif); font-weight: 600; font-size: 21px; line-height: 1.25; margin: 0; text-wrap: balance; }}
p {{ margin: 0; max-width: 65ch; }}
.lede {{ font-size: 17px; color: var(--ink-muted); }}
.stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: var(--space-3); }}
.stat {{ border-top: 2px solid var(--rule); padding-top: var(--space-2); }}
.stat b {{ display: block; font-family: var(--font-mono); font-size: 22px; font-weight: 500; }}
.stat span {{ font-size: 13px; color: var(--ink-muted); }}
.legend {{ display: flex; flex-wrap: wrap; gap: var(--space-4); font-size: 13px; color: var(--ink-muted); align-items: center; }}
.sw {{ display: inline-block; width: 12px; height: 12px; border-radius: 2px; margin-right: 6px; vertical-align: -1px; }}
.chart {{ width: 100%; height: auto; display: block; overflow: visible; }}
.chart text {{ font-family: var(--font-sans); }}
.chart .tick {{ fill: var(--ink-faint); font-size: 11px; font-family: var(--font-mono); }}
.chart .lab {{ fill: var(--ink-muted); font-size: 12.5px; }}
.chart .seg {{ fill: var(--paper); font-size: 11px; font-family: var(--font-mono); }}
.seg-core, .sw.core {{ fill: var(--scenario-adu); background: var(--scenario-adu); }}
.seg-sub, .sw.sub {{ fill: var(--brass); background: var(--brass); }}
.seg-town, .sw.town {{ fill: var(--survey); background: var(--survey); }}
.seg-out, .sw.out {{ fill: var(--ink-muted); background: var(--ink-muted); }}
.seg-in, .sw.in {{ fill: var(--confidence-inside); background: var(--confidence-inside); }}
.scroll {{ overflow-x: auto; }}
table {{ border-collapse: collapse; width: 100%; font-size: 13px; min-width: 560px; }}
th, td {{ text-align: left; padding: 6px 8px; border-bottom: 1px solid var(--rule); }}
thead th {{ font-weight: 600; color: var(--ink-muted); font-size: 12px; }}
td.num {{ font-family: var(--font-mono); font-variant-numeric: tabular-nums; }}
.note {{ font-size: 13px; color: var(--ink-muted); }}
code {{ font-family: var(--font-mono); font-size: 12.5px; }}
footer {{ border-top: 1px solid var(--rule); padding-top: var(--space-4); font-size: 13px; color: var(--ink-muted); display: flex; flex-direction: column; gap: var(--space-2); }}
</style>
<main>
<header>
  <div class="eyebrow">Lotline · D-089 ADU state profiles · 14 Nov 2026</div>
  <h1>Every state's ADU forecast leans on places unlike the ones the model learned from, and towns are not the reason</h1>
  <p class="lede">D-089 profiled every jurisdiction in the five states by type (core city, suburb, town), size, price and owner share, and set each state against the 64 places the ADU model was fitted on. Towns, the one type with no data, hold 9–30% of each state's lots but yield only 1–5% of its expected ADUs, so the town prior barely moves any range. The bigger gap is price and size: the fitted suburbs are the pricey Twin Cities and Triangle ones, and most of Ohio's and Texas's places are cheaper or bigger than anything fitted.</p>
</header>

<div class="stats">
  <div class="stat"><b>5 of 5</b><span>states labeled "mostly outside the places the model was fitted on" (over 25% of lots)</span></div>
  <div class="stat"><b>1–5%</b><span>of each state's expected ADUs come from towns, against 9–30% of its lots</span></div>
  <div class="stat"><b>25–96%</b><span>of each state's expected ADUs come from places outside the evidence (NC lowest, TX highest)</span></div>
  <div class="stat"><b>×0.30–×3.3</b><span>the town prior's 90% range over a suburb, set from the measured core-city gap</span></div>
</div>

<section>
  <div class="num-tag">Finding 1</div>
  <h2>The states' mixes differ, and the fit set is mostly core cities</h2>
  <p>Share of each state's eligible lots (ACS one-unit detached homes, 2011–15) by type. Suburbs hold half or more of every state's lots. The 64 fitted places are a different mix: their lots are mostly in core cities, because the cities with permit records are the big ones.</p>
  <div class="legend"><span><i class="sw core"></i>Core cities</span><span><i class="sw sub"></i>Suburbs</span><span><i class="sw town"></i>Towns</span></div>
  {stacked(mix_rows, "lot share by type", "share of eligible lots")}
</section>

<section>
  <div class="num-tag">Finding 2</div>
  <h2>Most lots in every state are outside the fit's evidence, mainly on price and size</h2>
  <p>A place is outside the evidence if it is a town, or if its home value, rent, owner share or lot count lies outside the 5th–95th percentile of the fitted places of its type. The fitted suburbs all have median home values of ${fr["suburb"]["home_value"][0] / 1e3:,.0f}k or more and rents of ${fr["suburb"]["rent"][0]:,.0f} or more (2025 dollars); many Ohio and Texas suburbs are cheaper. Texas's biggest cities and suburbs are also bigger than any fitted place.</p>
  <div class="legend"><span><i class="sw town"></i>Towns</span><span><i class="sw out"></i>Beyond the fit's range</span><span><i class="sw in"></i>Inside the evidence</span></div>
  {stacked(ev_rows, "share of lots outside the evidence", "share of eligible lots")}
  <div class="scroll"><table>
    <thead><tr><th>State (non-town lots)</th><th>Value out of range</th><th>Rent</th><th>Owner share</th><th>Lot count</th></tr></thead>
    <tbody>{dtab}</tbody>
  </table></div>
  <p class="note">A place can be out of range on several measures, so the columns overlap.</p>
</section>

<section>
  <div class="num-tag">Finding 3</div>
  <h2>Towns hardly matter to the totals; extrapolation does</h2>
  <p>Each state's ADU permits under its current rules, {win}, from the scenario's own inputs (eligible lots, rules, rent and value, the observed floor) with Form A + place types. Towns add few ADUs because their rents are low and fewer of them allow ADUs, so treating them as suburbs or giving them the wide prior changes P90 by under 3%. What does matter is the share of each total that comes from places outside the evidence: from a quarter in North Carolina to nearly all of Texas.</p>
  <div class="legend"><span><i class="sw out"></i>From places outside the evidence</span><span><i class="sw in"></i>Inside</span></div>
  {stacked(adu_rows, "share of expected ADUs outside the evidence", "share of expected ADU permits, " + win)}
  <div class="scroll"><table>
    <thead><tr><th>State</th><th>Towns as suburbs, P10–P50–P90</th><th>With the town prior</th><th>From towns</th><th>From outside the evidence</th></tr></thead>
    <tbody>{"".join(ttab)}</tbody>
  </table></div>
  <p class="note">These totals are a sensitivity, not the scenario output: they carry θ, the core-city term and each place's own effect, but no state effect (every state is in the fit) and no market-path draws. St. Paul is left out.</p>
</section>

<section>
  <div class="num-tag">What it means</div>
  <h2>Label the ranges, and look for cheaper suburbs before towns</h2>
  <p>By the rule set in advance, every state's ADU range gets the label "mostly outside the places the model was fitted on". The town prior can go to config as written; it costs nothing and closes the one unmeasured type. The more useful next data would be ADU counts for a few lower-priced suburbs (Ohio or Texas), the places the forecasts lean on most and the model has never seen.</p>
</section>

<section>
  <div class="num-tag">Profile table</div>
  <h2>Each state by type</h2>
  <div class="scroll"><table>
    <thead><tr><th>State</th><th>Type</th><th>Places</th><th>Population</th><th>Eligible lots</th><th>Share</th><th>Home value</th><th>Rent</th><th>Owners</th></tr></thead>
    <tbody>{"".join(ptab)}</tbody>
  </table></div>
  <p class="note">Value, rent and owner share are lot-weighted medians, 2011–15 ACS, in 2025 dollars. Unincorporated county areas read their county's value and rent ({summ["value_from_county"]} of {summ["jurisdictions"]:,}).</p>
</section>

<footer>
  <div>Types by D-088's rule (core: the largest place in its metro by housing units, or a third of it; other metro places suburbs; the rest towns). Fit: Form A + P, θ {summ["a_p_fit"]["theta"] * 1000:.3f} per 1,000, core term {summ["a_p_fit"]["b_core"]:+.3f}, α {summ["a_p_fit"]["alpha"]:.2f}. Town prior sd {summ["town_prior_sd"]:.3f}. 20,000 draws, seed 20261111.</div>
  <div>Sources: <code>reports/adu-state-profiles/</code>, <code>src/lotline/model/adu_profiles.py</code>, on branch <code>ws/adu-state-profiles</code>. Method: D-089 in <code>docs/analysis_plan.md</code>. Run offline from cached data; no ADU count read for the profiles. Nothing was unblinded and nothing was written to config.</div>
</footer>
</main>
"""
out.write_text(html)
print(out, len(html))
