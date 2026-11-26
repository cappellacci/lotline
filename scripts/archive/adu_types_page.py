# ruff: noqa: E501  (long lines are the HTML/CSS page template)
"""Build the D-088 results page from reports/adu-place-types (fits.csv, tiers.csv, summary.json, ...).

Usage: uv run python scripts/archive/adu_types_page.py . reports/adu-place-types/results.html
"""

import json
import math
import sys
from pathlib import Path

import pandas as pd

root, out = Path(sys.argv[1]), Path(sys.argv[2])
rep = root / "reports/adu-place-types"
fits = pd.read_csv(rep / "fits.csv")
tiers = pd.read_csv(rep / "tiers.csv")
ds = pd.read_csv(rep / "test_d_states.csv")
pt = pd.read_csv(rep / "place_types.csv", dtype={"geoid": str})
summ = json.loads((rep / "summary.json").read_text())
tokens = (root / "docs/build/identity/tokens.css").read_text()
W, LW = 640, 170
STATE = {"MN": "Minnesota", "NC": "North Carolina", "TX": "Texas", "OR": "Oregon", "OH": "Ohio"}


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def ratio_chart(rows, series, label, axis):
    lo, hi = math.log(1 / 8), math.log(16)
    top, rh = 18, 34
    h = top + rh * len(rows) + 38

    def sx(v):
        v = min(max(v, math.exp(lo)), math.exp(hi))
        return LW + (math.log(v) - lo) / (hi - lo) * (W - LW - 20)

    g = [f'<svg viewBox="0 0 {W} {h}" class="chart" role="img" aria-label="{esc(label)}">']
    g.append(
        f'<rect x="{sx(0.5):.1f}" y="{top - 8}" width="{sx(2) - sx(0.5):.1f}" height="{h - 30 - top + 8}" class="band"/>'
    )
    for t, s in ((1 / 8, "÷8"), (0.5, "÷2"), (1, "×1"), (2, "×2"), (4, "×4"), (16, "×16")):
        g.append(
            f'<line x1="{sx(t):.1f}" x2="{sx(t):.1f}" y1="{top - 8}" y2="{h - 30}" class="{"zero" if t == 1 else "grid"}"/>'
        )
        g.append(f'<text x="{sx(t):.1f}" y="{h - 14}" class="tick" text-anchor="middle">{s}</text>')
    for i, (name, vals) in enumerate(rows):
        y = top + rh * i + rh / 2
        g.append(f'<text x="{LW - 10}" y="{y + 4}" class="lab" text-anchor="end">{esc(name)}</text>')
        xs = [sx(v) for v in vals]
        g.append(f'<line x1="{min(xs):.1f}" x2="{max(xs):.1f}" y1="{y}" y2="{y}" class="move"/>')
        for (cls, _), x in zip(series, xs, strict=True):
            g.append(f'<circle cx="{x:.1f}" cy="{y}" r="5" class="{cls}"/>')
    g.append(f'<text x="{W - 20}" y="{h - 1}" class="tick" text-anchor="end">{esc(axis)}</text>')
    g.append("</svg>")
    return "".join(g)


def share_chart():
    """Horizontal bars: share of the place-effect variance each grouping explains, Form A and Form A′."""
    groups = [
        ("State", "state"),
        ("Place type", "type"),
        ("Counting source", "source"),
        ("All three together", "all three"),
    ]
    top, rh = 16, 44
    h = top + rh * len(groups) + 34
    x0, x1 = LW, W - 20

    def sx(v):
        return x0 + v * (x1 - x0)

    g = [f'<svg viewBox="0 0 {W} {h}" class="chart" role="img" aria-label="variance shares">']
    for t in (0, 0.25, 0.5, 0.75, 1.0):
        g.append(
            f'<line x1="{sx(t):.1f}" x2="{sx(t):.1f}" y1="{top - 6}" y2="{h - 30}" class="{"zero" if t == 0 else "grid"}"/>'
        )
        g.append(f'<text x="{sx(t):.1f}" y="{h - 14}" class="tick" text-anchor="middle">{t:.0%}</text>')
    for i, (name, key) in enumerate(groups):
        y = top + rh * i
        g.append(f'<text x="{LW - 10}" y="{y + 18}" class="lab" text-anchor="end">{esc(name)}</text>')
        for j, (form, cls) in enumerate((("A", "bar-a"), ("A′", "bar-p"))):
            v = summ["part1"][form]["shares"][key]
            yy = y + 4 + j * 16
            g.append(f'<rect x="{x0}" y="{yy}" width="{sx(v) - x0:.1f}" height="13" class="{cls}" rx="2"/>')
            g.append(f'<text x="{sx(v) + 6:.1f}" y="{yy + 11}" class="val">{v:.0%}</text>')
    g.append(
        f'<text x="{W - 20}" y="{h - 1}" class="tick" text-anchor="end">share of the spread between places explained (weighted by fit years)</text>'
    )
    g.append("</svg>")
    return "".join(g)


def core_chart():
    rows = []
    for fold in ["all", "without MN", "without NC", "without OH", "without TX", "without OR"]:
        for form in ("A+P", "A′+P"):
            r = fits[(fits.variant == "central") & (fits.fold == fold) & (fits.form == form)].iloc[0]
            name = (
                ("All places" if fold == "all" else fold.replace("without", "Without"))
                if form == "A+P"
                else ""
            )
            rows.append((name, form, r.b_core, r.b_core_low, r.b_core_high))
    lo, hi = -1.0, 2.6
    top, rh = 16, 20
    h = top + rh * len(rows) + 36

    def sx(v):
        return LW + (max(min(v, hi), lo) - lo) / (hi - lo) * (W - LW - 20)

    g = [f'<svg viewBox="0 0 {W} {h}" class="chart" role="img" aria-label="core city term by fit">']
    for t in (-1, -0.5, 0, 0.5, 1, 1.5, 2, 2.5):
        g.append(
            f'<line x1="{sx(t):.1f}" x2="{sx(t):.1f}" y1="{top - 6}" y2="{h - 30}" class="{"zero" if t == 0 else "grid"}"/>'
        )
        g.append(f'<text x="{sx(t):.1f}" y="{h - 14}" class="tick" text-anchor="middle">{t:+.1f}</text>')
    for i, (name, form, b, bl, bh) in enumerate(rows):
        y = top + rh * i + rh / 2
        cls = "ca" if form == "A+P" else "cp"
        if name:
            g.append(f'<text x="{LW - 10}" y="{y + 12}" class="lab" text-anchor="end">{esc(name)}</text>')
        g.append(f'<line x1="{sx(bl):.1f}" x2="{sx(bh):.1f}" y1="{y}" y2="{y}" class="ci {cls}"/>')
        g.append(f'<circle cx="{sx(b):.1f}" cy="{y}" r="4.5" class="pt {cls}"/>')
    g.append(
        f'<text x="{W - 20}" y="{h - 1}" class="tick" text-anchor="end">core-city term, log multiple of a suburb (90% interval)</text>'
    )
    g.append("</svg>")
    return "".join(g)


dec = summ["decisions"]
da, dp = dec["A vs A+P"], dec["A′ vs A′+P"]
p1a, p1p = summ["part1"]["A"], summ["part1"]["A′"]
full = fits[(fits.variant == "central") & (fits.fold == "all")].set_index("form")
FORMS = [("pt-a", "A"), ("pt-p", "A+P"), ("pt-c", "A′"), ("pt-k", "A′+P")]
t1 = tiers[tiers.tier == 1].pivot_table(index="held_out", columns="form", values="obs_over_p50")
t_rows = [(STATE[s], [t1.loc[s, f] for _, f in FORMS]) for s in ("MN", "NC", "TX", "OR")]
useful = summ["useful"]
mean_a = p1a["group_means"]

trows = []
for s in ("MN", "NC", "TX", "OR"):
    for tier in (0, 1, 2):
        cells = []
        for _, f in FORMS:
            r = tiers[(tiers.held_out == s) & (tiers.tier == tier) & (tiers.form == f)].iloc[0]
            cells.append(f"<td class='num {'useful' if r.useful else ''}'>{r.obs_over_p50:.2f}</td>")
        trows.append(f"<tr><td>{STATE[s] if tier == 0 else ''}</td><td>{tier}</td>{''.join(cells)}</tr>")
urow = "".join(
    f"<td class='num'>{useful[f]['0']} / {useful[f]['1']} / {useful[f]['2']}</td>" for _, f in FORMS
)
xt = pd.crosstab(pt.state, pt.type)
xs = pd.crosstab(pt.state, pt.source_kind)
mix = "".join(
    f"<tr><td>{STATE[s]}</td><td class='num'>{xt.loc[s].get('core', 0)}</td><td class='num'>{xt.loc[s].get('suburb', 0)}</td>"
    f"<td class='num'>{xs.loc[s].get('survey', 0)}</td><td class='num'>{xs.loc[s].get('parser', 0)}</td><td class='num'>{xs.loc[s].get('field', 0)}</td></tr>"
    for s in ("MN", "NC", "OH", "TX", "OR")
)
dsp = ds.pivot_table(index="state", columns="forecast", values="obs_over_p50")
hl = pd.read_csv(rep / "heldout_log_scores.csv").groupby("form")["log_score"].sum()

html = f"""<title>ADU place types</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=Public+Sans:wght@400;600;700&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&display=swap">
<style>
/* Layout: one reading column; headline, a decision panel, numbered findings each with a chart, then tables. */
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
.decision {{ background: var(--paper-raised); border: 1px solid var(--brass); border-radius: var(--radius-sm); padding: var(--space-5); display: flex; flex-direction: column; gap: var(--space-3); }}
.decision ol {{ margin: 0; padding-left: 1.3em; display: flex; flex-direction: column; gap: var(--space-2); }}
.tag {{ font-family: var(--font-mono); font-size: 11px; letter-spacing: .06em; text-transform: uppercase; background: var(--brass); color: var(--on-brass); padding: 2px 6px; border-radius: var(--radius-sm); align-self: flex-start; }}
.legend {{ display: flex; flex-wrap: wrap; gap: var(--space-4); font-size: 13px; color: var(--ink-muted); align-items: center; }}
.dot {{ display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 6px; vertical-align: -1px; }}
.dot.a {{ background: var(--ink-faint); }} .dot.f {{ background: var(--scenario-adu); }} .dot.c {{ background: var(--brass); }} .dot.k {{ background: var(--survey); }}
.chart {{ width: 100%; height: auto; display: block; }}
.chart text {{ font-family: var(--font-sans); }}
.chart .grid {{ stroke: var(--rule); stroke-width: 1; }}
.chart .zero {{ stroke: var(--ink-faint); stroke-width: 1.5; }}
.chart .band {{ fill: var(--confidence-inside); fill-opacity: .10; }}
.chart .tick {{ fill: var(--ink-faint); font-size: 11px; font-family: var(--font-mono); }}
.chart .lab {{ fill: var(--ink-muted); font-size: 12.5px; }}
.chart .val {{ fill: var(--ink-muted); font-size: 11.5px; font-family: var(--font-mono); }}
.chart .move {{ stroke: var(--rule); stroke-width: 3; }}
.chart .pt-a {{ fill: var(--ink-faint); }}
.chart .pt-p {{ fill: var(--scenario-adu); }}
.chart .pt-c {{ fill: var(--brass); }}
.chart .pt-k {{ fill: var(--survey); }}
.chart .bar-a {{ fill: var(--scenario-adu); }}
.chart .bar-p {{ fill: var(--brass); }}
.chart .ci {{ stroke-width: 3; }}
.chart .ci.ca {{ stroke: var(--scenario-adu); }} .chart .pt.ca {{ fill: var(--scenario-adu); }}
.chart .ci.cp {{ stroke: var(--brass); }} .chart .pt.cp {{ fill: var(--brass); }}
.scroll {{ overflow-x: auto; }}
table {{ border-collapse: collapse; width: 100%; font-size: 13px; min-width: 520px; }}
th, td {{ text-align: left; padding: 6px 8px; border-bottom: 1px solid var(--rule); }}
thead th {{ font-weight: 600; color: var(--ink-muted); font-size: 12px; }}
td.num {{ font-family: var(--font-mono); font-variant-numeric: tabular-nums; }}
td.useful {{ color: var(--confidence-inside); font-weight: 600; }}
.note {{ font-size: 13px; color: var(--ink-muted); }}
code {{ font-family: var(--font-mono); font-size: 12.5px; }}
footer {{ border-top: 1px solid var(--rule); padding-top: var(--space-4); font-size: 13px; color: var(--ink-muted); display: flex; flex-direction: column; gap: var(--space-2); }}
</style>
<main>
<header>
  <div class="eyebrow">Lotline · D-088 ADU place types · 14 Nov 2026</div>
  <h1>Core cities build about three times as many ADUs per lot as suburbs, and that moves every held-out state toward its real count</h1>
  <p class="lede">D-088 asked where the differences between places sit (by state, by kind of place, or by how ADUs were counted) and whether a place type shared across states helps the model carry over to a state it has not seen. Typing places as core cities or suburbs gives the best leave-one-state-out result yet, and the pre-set rule adopts it over Form A. It adds nothing once owner share (Form A′) is in. And about 70% of the spread is between places of the same state, type and counting method, which no grouping reaches.</p>
</header>

<div class="stats">
  <div class="stat"><b>×{math.exp(full.loc["A+P"].b_core):.1f}</b><span>core city over suburb, Form A + types (90%: ×{math.exp(full.loc["A+P"].b_core_low):.1f} to ×{math.exp(full.loc["A+P"].b_core_high):.1f})</span></div>
  <div class="stat"><b>{useful["A+P"]["1"]} of 4</b><span>held-out states useful at tier 1 with types (Form A: {useful["A"]["1"]}; A′: {useful["A′"]["1"]})</span></div>
  <div class="stat"><b>+{da["tier1_log_score_gain"]["gain"]:.1f}</b><span>tier-1 held-out log score, A + types over A (bar: 2 SE = {2 * da["tier1_log_score_gain"]["se"]:.1f})</span></div>
  <div class="stat"><b>{1 - p1a["shares"]["all three"]:.0%}</b><span>of the spread between places that state, type and counting source leave unexplained (Form A)</span></div>
</div>

<div class="decision">
  <span class="tag">Decided by the pre-set rule</span>
  <h2>Types replace Form A; they do not improve Form A′</h2>
  <ol>
    <li><b>Form A + types:</b> adopted over Form A. {esc(da["decision"]["reason"])}.</li>
    <li><b>Form A′ + types:</b> not adopted. {esc(dp["decision"]["reason"])}.</li>
    <li>No form passes D-075's claim rule at any tier: that needs every scorable state useful, and Minnesota stays outside ×2 for every form.</li>
  </ol>
  <p class="note">Which pair counts depends on D-084, still open: keep Form A (then A + types is the form), or adopt A′ (then A′ stays as is). The two finalists, A + types and A′, are a near tie on the tier-1 log score ({hl["A+P"] - hl["A"]:+.1f} and {hl["A′"] - hl["A"]:+.1f} over A); A + types has more useful states (3 against 1). That comparison is descriptive, not part of the rule. Nothing goes to config.</p>
</div>

<section>
  <div class="num-tag">Finding 1</div>
  <h2>In this data, state, kind of place and counting method are almost the same thing</h2>
  <p>Before any fit, the 64 fit places split into 16 core cities, spread over all five states, and 48 suburbs, all in Minnesota and North Carolina. There are no towns. Texas, Oregon and Ohio contribute only core cities. Minnesota's 41 suburbs are all counted from the Met Council survey; the other states use city permit records or parsers. So "Minnesota is over-predicted" and "suburbs are over-predicted" and "survey places are over-predicted" are largely one statement, and Part 1 cannot pull them apart cleanly.</p>
  <div class="scroll"><table>
    <thead><tr><th>State</th><th>Core cities</th><th>Suburbs</th><th>Survey</th><th>Parser</th><th>Permit field</th></tr></thead>
    <tbody>{mix}</tbody>
  </table></div>
</section>

<section>
  <div class="num-tag">Finding 2</div>
  <h2>Each grouping explains about a quarter of the spread, and together not much more</h2>
  <p>Under Form A, kind of place explains {p1a["shares"]["type"]:.0%} of the spread in place effects, state {p1a["shares"]["state"]:.0%} and counting source {p1a["shares"]["source"]:.0%}; all three together {p1a["shares"]["all three"]:.0%}. The pre-set reading is "types matter": type explains a little more than state, and core cities sit above suburbs with every state left out. A typical core city's effect is ×{mean_a["type"]["core"]["x_mean"]:.1f}, a suburb's ×{mean_a["type"]["suburb"]["x_mean"]:.1f}. Under Form A′, owner share has already absorbed most of it: the three explain {p1p["shares"]["state"]:.0%}, {p1p["shares"]["type"]:.0%} and {p1p["shares"]["source"]:.0%} (reading: "mixed").</p>
  <div class="legend"><span><i class="dot f"></i>Form A</span><span><i class="dot c"></i>Form A′ (owner share)</span></div>
  {share_chart()}
  <p class="note">The rest, about {1 - p1a["shares"]["all three"]:.0%} under A, is between places of the same state, type and counting method: Edina against Richfield, Cary against Durham. That is what no form so far can predict for a state it has not seen.</p>
</section>

<section>
  <div class="num-tag">Finding 3</div>
  <h2>With types, every held-out state moves toward its observed count</h2>
  <p>Leave one state out, forecast it from the other four. Form A misses Texas ×{t1.loc["TX", "A"]:.1f}, Oregon ×{t1.loc["OR", "A"]:.1f} and North Carolina ×{t1.loc["NC", "A"]:.1f} low, and Minnesota ÷{1 / t1.loc["MN", "A"]:.1f} high. With the core-city term these become ×{t1.loc["TX", "A+P"]:.1f}, ×{t1.loc["OR", "A+P"]:.1f}, ×{t1.loc["NC", "A+P"]:.1f} and ÷{1 / t1.loc["MN", "A+P"]:.1f}: three of four states inside ×2 and their ranges. Owner share (A′) does about as well on Texas and less well elsewhere, and adding types to it changes little at tier 1.</p>
  <div class="legend"><span><i class="dot a"></i>A</span><span><i class="dot f"></i>A + types</span><span><i class="dot c"></i>A′</span><span><i class="dot k"></i>A′ + types</span></div>
  {ratio_chart(t_rows, FORMS, "tier 1 observed over median by held-out state", "observed ÷ forecast median, held-out state, tier 1 (shaded: within ×2)")}
</section>

<section>
  <div class="num-tag">Finding 4</div>
  <h2>The core-city effect is steady on its own, and mostly the same thing as owner share</h2>
  <p>On its own the core-city term holds at ×2.5 to ×3.5 with any state left out. Next to owner share it shrinks to about ×{math.exp(full.loc["A′+P"].b_core):.1f}, its interval includes no effect, and without Oregon it nearly vanishes. Core cities are where renters are (correlation with owner share {summ["owner_vs_core_correlation"]:+.2f}). The two terms measure much the same urban-versus-suburban difference; types are simpler to explain and need only a metro map and a housing count.</p>
  <div class="legend"><span><i class="dot f"></i>A + types</span><span><i class="dot c"></i>A′ + types</span></div>
  {core_chart()}
</section>

<section>
  <div class="num-tag">Finding 5</div>
  <h2>Types don't help forecast the places the model has already seen</h2>
  <p>On D-085's test D (fit 2016–20, forecast 2021–25), types change nothing that matters: Minnesota is still forecast {1 / dsp.loc["MN", "A+P"]:.0f}× too high, mostly Minneapolis's 2021 reform step. Carrying each place's own rate forward still scores best. Types answer "what will a new state look like", not "what will this city do next".</p>
</section>

<section>
  <div class="num-tag">Data-tier table</div>
  <h2>Observed ÷ forecast median, by held-out state and tier</h2>
  <div class="scroll"><table>
    <thead><tr><th>Held out</th><th>Tier</th><th>A</th><th>A + types</th><th>A′</th><th>A′ + types</th></tr></thead>
    <tbody>{"".join(trows)}<tr><td><b>Useful states</b></td><td>0 / 1 / 2</td>{urow}</tr></tbody>
  </table></div>
  <p class="note">Green: inside P10–P90 and within ×2. Ohio has no scorable place outside its tier-2 city, so four states are scored. A four-type sensitivity (suburbs split by pre-1960 housing) does worse: {useful["A+P4"]["1"]} useful at tier 1.</p>
</section>

<footer>
  <div>The base forms match D-084 to the digit (Form A θ {full.loc["A"].theta * 1000:.4f} per 1,000, log-lik {full.loc["A"].loglik:,.2f}; A′ β_o {full.loc["A′"].beta:+.3f}). Types: core city is the largest place in its metro area by 2011–15 housing units, or any place with a third of its units; other places in a metro are suburbs; the rest towns (none in the fit set). 20,000 draws, seed 20261111.</div>
  <div>Sources: <code>reports/adu-place-types/</code>, <code>src/lotline/model/adu_types.py</code>, on branch <code>ws/adu-segments</code>. Method: D-088 in <code>docs/analysis_plan.md</code>. Run offline from cached data. St. Paul stays out. Nothing was unblinded and nothing was written to config.</div>
</footer>
</main>
"""
out.write_text(html)
print(out, len(html))
