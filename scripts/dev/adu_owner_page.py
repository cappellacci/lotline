# ruff: noqa: E501  (long lines are the HTML/CSS page template)
"""Build the D-084 results page from reports/adu-owner-share (tiers.csv, test_a.csv, fits.csv, summary.json).

Usage: uv run python scripts/dev/adu_owner_page.py . reports/adu-owner-share/results.html
"""

import json
import math
import sys
from pathlib import Path

import pandas as pd

root, out = Path(sys.argv[1]), Path(sys.argv[2])
rep = root / "reports/adu-owner-share"
tiers = pd.read_csv(rep / "tiers.csv")
ta = pd.read_csv(rep / "test_a.csv")
fits = pd.read_csv(rep / "fits.csv")
summ = json.loads((rep / "summary.json").read_text())
tokens = (root / "docs/build/identity/tokens.css").read_text()
c = summ["central"]
W, LW = 640, 170
STATE = {"MN": "Minnesota", "NC": "North Carolina", "TX": "Texas", "OR": "Oregon"}


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def ratio_chart(rows, label):
    """Dumbbell of observed ÷ median, Form A to A′, on a log scale with the ×2 band shaded."""
    lo, hi = math.log(1 / 16), math.log(16)
    top, rh = 18, 30
    h = top + rh * len(rows) + 38

    def sx(v):
        v = min(max(v, math.exp(lo)), math.exp(hi))
        return LW + (math.log(v) - lo) / (hi - lo) * (W - LW - 20)

    g = [f'<svg viewBox="0 0 {W} {h}" class="chart" role="img" aria-label="{esc(label)}">']
    g.append(f'<rect x="{sx(0.5):.1f}" y="{top - 8}" width="{sx(2) - sx(0.5):.1f}" height="{h - 30 - top + 8}" class="band"/>')
    for t, s in ((1 / 16, "÷16"), (1 / 4, "÷4"), (0.5, "÷2"), (1, "×1"), (2, "×2"), (4, "×4"), (16, "×16")):
        g.append(f'<line x1="{sx(t):.1f}" x2="{sx(t):.1f}" y1="{top - 8}" y2="{h - 30}" class="{"zero" if t == 1 else "grid"}"/>')
        g.append(f'<text x="{sx(t):.1f}" y="{h - 14}" class="tick" text-anchor="middle">{s}</text>')
    for i, (name, a, p) in enumerate(rows):
        y = top + rh * i + rh / 2
        g.append(f'<text x="{LW - 10}" y="{y + 4}" class="lab" text-anchor="end">{esc(name)}</text>')
        g.append(f'<line x1="{sx(a):.1f}" x2="{sx(p):.1f}" y1="{y}" y2="{y}" class="move"/>')
        g.append(f'<circle cx="{sx(a):.1f}" cy="{y}" r="5" class="pt-a"/>')
        g.append(f'<circle cx="{sx(p):.1f}" cy="{y}" r="5" class="pt-p"/>')
    g.append(f'<text x="{W - 20}" y="{h - 1}" class="tick" text-anchor="end">observed ÷ predicted median (shaded: within ×2)</text>')
    g.append("</svg>")
    return "".join(g)


def beta_chart():
    rows = []
    for fold in ["all", "without MN", "without NC", "without OH", "without TX", "without OR"]:
        r = fits[(fits.variant == "central") & (fits.fold == fold) & (fits.form == "A′")].iloc[0]
        rows.append(("All places" if fold == "all" else fold.replace("without", "Without"), r.beta, r.beta_low, r.beta_high, fold == "all"))
    r = fits[(fits.variant == "2016-20 vintage") & (fits.fold == "all")].iloc[0]
    rows.append(("2016–20 owner share", r.beta, r.beta_low, r.beta_high, False))
    w = summ["sensitivity_within_state"]
    rows.append(("Within states only", w["beta"], w["beta_low"], w["beta_high"], False))
    lo, hi = -1.25, 0.25
    top, rh = 16, 28
    h = top + rh * len(rows) + 36

    def sx(v):
        return LW + (max(min(v, hi), lo) - lo) / (hi - lo) * (W - LW - 20)

    g = [f'<svg viewBox="0 0 {W} {h}" class="chart" role="img" aria-label="beta_o by fit">']
    for t in (-1.25, -1, -0.75, -0.5, -0.25, 0, 0.25):
        g.append(f'<line x1="{sx(t):.1f}" x2="{sx(t):.1f}" y1="{top - 6}" y2="{h - 30}" class="{"zero" if t == 0 else "grid"}"/>')
        g.append(f'<text x="{sx(t):.1f}" y="{h - 14}" class="tick" text-anchor="middle">{t:+g}</text>')
    for i, (name, b, bl, bh, main) in enumerate(rows):
        y = top + rh * i + rh / 2
        cls = "cand" if main else ""
        g.append(f'<text x="{LW - 10}" y="{y + 4}" class="lab {cls}" text-anchor="end">{esc(name)}</text>')
        g.append(f'<line x1="{sx(bl):.1f}" x2="{sx(bh):.1f}" y1="{y}" y2="{y}" class="ci {cls}"/>')
        g.append(f'<circle cx="{sx(b):.1f}" cy="{y}" r="5" class="pt {cls}"/>')
    g.append(f'<text x="{W - 20}" y="{h - 1}" class="tick" text-anchor="end">β_o per SD of owner share (90% interval)</text>')
    g.append("</svg>")
    return "".join(g)


t1 = tiers[tiers.tier == 1].set_index(["held_out", "form"])
state_rows = [(STATE[s], t1.loc[(s, "A"), "obs_over_p50"], t1.loc[(s, "A′"), "obs_over_p50"]) for s in ("MN", "NC", "TX", "OR")]
tap = ta.pivot_table(index="name", columns="form", values="obs_over_p50")
place_rows = [(n.replace(" city", "").replace(" town", ""), tap.loc[n, "A"], tap.loc[n, "A′"]) for n in tap.index]

fa = fits[(fits.variant == "central") & (fits.fold == "all")].set_index("form")
A, P = fa.loc["A"], fa.loc["A′"]
gain, se = c["log_gain_a_prime_over_a"], c["log_gain_se"]

tier_rows = []
for s in ("MN", "NC", "TX", "OR"):
    for tier in (0, 1, 2):
        cells = []
        for f in ("A", "A′"):
            r = tiers[(tiers.held_out == s) & (tiers.tier == tier) & (tiers.form == f)].iloc[0]
            u = "useful" if r.useful else ""
            cells.append(f'<td class="num">{r.p10:,.0f}–{r.p50:,.0f}–{r.p90:,.0f}</td><td class="num {u}">{r.obs_over_p50:.2f}</td>')
        obs = tiers[(tiers.held_out == s) & (tiers.tier == tier)].observed.iloc[0]
        tier_rows.append(f"<tr><td>{STATE[s] if tier == 0 else ''}</td><td>{tier}</td><td class='num'>{obs:,.0f}</td>{''.join(cells)}</tr>")

vc = summ["vintage_check"]
ol = summ["outlook_pre1960"]

html = f"""<title>ADU owner-share refit</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=Public+Sans:wght@400;600;700&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&display=swap">
<style>
/* Layout: one reading column; headline, a decision panel, numbered findings each with a chart, then the tier table. */
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
.legend {{ display: flex; gap: var(--space-4); font-size: 13px; color: var(--ink-muted); align-items: center; }}
.dot {{ display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 6px; vertical-align: -1px; }}
.dot.a {{ background: var(--ink-faint); }} .dot.p {{ background: var(--scenario-adu); }}
.chart {{ width: 100%; height: auto; display: block; }}
.chart text {{ font-family: var(--font-sans); }}
.chart .grid {{ stroke: var(--rule); stroke-width: 1; }}
.chart .zero {{ stroke: var(--ink-faint); stroke-width: 1.5; }}
.chart .band {{ fill: var(--confidence-inside); fill-opacity: .10; }}
.chart .tick {{ fill: var(--ink-faint); font-size: 11px; font-family: var(--font-mono); }}
.chart .lab {{ fill: var(--ink-muted); font-size: 12.5px; }}
.chart .lab.cand {{ fill: var(--ink); font-weight: 600; }}
.chart .move {{ stroke: var(--rule); stroke-width: 3; }}
.chart .pt-a {{ fill: var(--ink-faint); }}
.chart .pt-p {{ fill: var(--scenario-adu); }}
.chart .ci {{ stroke: var(--ink-faint); stroke-width: 3; }}
.chart .ci.cand {{ stroke: var(--scenario-adu); }}
.chart .pt {{ fill: var(--ink-faint); }}
.chart .pt.cand {{ fill: var(--scenario-adu); }}
.scroll {{ overflow-x: auto; }}
table {{ border-collapse: collapse; width: 100%; font-size: 13px; min-width: 560px; }}
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
  <div class="eyebrow">Lotline · D-084 ADU owner share · 13 Nov 2026</div>
  <h1>Adding owner share moves every state's ADU prediction the right way, and wins the pre-set test by a narrow margin</h1>
  <p class="lede">Form A′ is today's ADU model plus one term: places with more renters build more ADUs per eligible lot. We scored it against Form A on D-079's tests, under the rule fixed before the run. A′ wins on the held-out score, but still passes no data tier, and three states remain under-predicted by about ×2 to ×2.6.</p>
</header>

<div class="stats">
  <div class="stat"><b>{P.beta:+.2f}</b><span>β_o per SD of owner share (90%: {P.beta_low:+.2f} to {P.beta_high:+.2f})</span></div>
  <div class="stat"><b>{(1 - P.alpha / A.alpha) * 100:.0f}%</b><span>less unexplained place variance (α {A.alpha:.2f} → {P.alpha:.2f})</span></div>
  <div class="stat"><b>+{gain:.1f}</b><span>held-out log score over 52 places (bar: 2 SE = {2 * se:.1f})</span></div>
  <div class="stat"><b>0 / 0</b><span>data tiers passed, Form A / A′ (claim needs 4 states)</span></div>
</div>

<div class="decision">
  <span class="tag">Needs Ben's call</span>
  <h2>D-084's rule picks Form A′. Adopt it?</h2>
  <ol>
    <li><b>Recommended:</b> adopt A′ as the working ADU form. Write θ {P.theta * 1000:.3f} per 1,000, α {P.alpha:.2f}, β_o {P.beta:+.2f} and the owner-share inputs to config in their own PR. Then give the scenario engine the place term, so that test C can run on A′.</li>
    <li>Keep Form A until A′ also clears a data tier. The win is narrow (+{gain:.1f} against a bar of {2 * se:.1f}), and no state but Minnesota and North Carolina gets inside ×2 at any tier.</li>
    <li>Adopt A′, and also write the next entry now: an ADU time trend with a time-split forecast test. That is the other lead for the under-predicted states.</li>
  </ol>
</div>

<section>
  <div class="num-tag">Finding 1</div>
  <h2>Every held-out state moves toward its observed count</h2>
  <p>We left each state out, refitted on the other four, and predicted the state's 2021–2024 ADUs from its 20 largest places' own rules (tier 1). Minnesota's over-prediction shrinks from ×{1 / state_rows[0][1]:.1f} to ×{1 / state_rows[0][2]:.1f}. North Carolina, Texas and Oregon's under-predictions shrink by roughly a third to a half. North Carolina gets inside ×2 at tier 1. Texas and Oregon do not.</p>
  <div class="legend"><span><i class="dot a"></i>Form A</span><span><i class="dot p"></i>Form A′</span></div>
  {ratio_chart(state_rows, "observed over median by held-out state, tier 1")}
  <p class="note">Ohio cannot be scored: its one fit place, Columbus, is its tier-2 city. Every range still holds the observed total. D-075 counts a state as useful when the range holds the total and the median is within ×2.</p>
</section>

<section>
  <div class="num-tag">Finding 2</div>
  <h2>New places: renter-heavy cities get closer, but College Station overshoots</h2>
  <p>Test A predicts each place added since D-053 from a fit without it. The renter-heavy North Carolina and Oregon cities move closer: Durham from ×4.7 to ×2.5, Wilmington from ×5.0 to ×2.2, Charlotte to ×1.0. North Carolina now passes test A. College Station, the most renter-heavy place in the fit (z −2.1), swings from right on to a 4× over-prediction, so Texas no longer passes. The count of tests passed is unchanged: 1 each.</p>
  <div class="legend"><span><i class="dot a"></i>Form A</span><span><i class="dot p"></i>Form A′</span></div>
  {ratio_chart(place_rows, "test A observed over median by new place")}
  <p class="note">Test B (the Wake and Franklin County towns' roll counts) still fails for both forms. A′ narrows the over-prediction (Wake: median 69 against 5 counted, down from 83), but not enough.</p>
</section>

<section>
  <div class="num-tag">Finding 3</div>
  <h2>The effect is steady, though weaker than the screen suggested</h2>
  <p>β_o keeps its sign whichever state is left out, and with the 2016–20 vintage. Its interval crosses zero only without Minnesota, and in the within-state version (−0.37, −0.77 to +0.03). It is smaller than D-083's −0.81. Most of the difference is the six Minnesota townships, which the screen lacked and which are about 95% owner-occupied. Adding pre-1960 housing on top changes nothing (p {ol["p"]:.2f}).</p>
  {beta_chart()}
</section>

<section>
  <div class="num-tag">Data-tier table</div>
  <h2>Ranges by held-out state and tier</h2>
  <div class="scroll"><table>
    <thead><tr><th>State</th><th>Tier</th><th>Observed</th><th>Form A P10–P50–P90</th><th>Obs ÷ P50</th><th>Form A′ P10–P50–P90</th><th>Obs ÷ P50</th></tr></thead>
    <tbody>{"".join(tier_rows)}</tbody>
  </table></div>
  <p class="note">Green ratios are useful (range holds the total, median within ×2). A′: 1 useful state at each tier; A: 0. The claim rule needs 4.</p>
</section>

<footer>
  <div>Form A from the same fitter matches D-079 to four figures (θ 0.7563 per 1,000, α 1.918, log-lik −1,347.71). Owner share: ACS 2011–15 B25003. The 57 places use their place rows, the 6 Minnesota townships their county subdivision, and Durham County unincorporated its county less its places. 2011–15 against 2020–24: r = {vc["pearson"]:.3f}.</div>
  <div>Sources: <code>reports/adu-owner-share/</code>, <code>src/lotline/model/adu_owner.py</code>, on branch <code>ws/adu-owner-share</code>. Method: D-084 in <code>docs/analysis_plan.md</code>. Run offline from cached data. St. Paul stays out. Nothing was unblinded and nothing was written to config.</div>
</footer>
</main>
"""
out.write_text(html)
print(out, len(html))
