# ruff: noqa: E501  (long lines are the HTML/CSS page template)
"""Build the D-087 results page from reports/adu-age-term (tiers.csv, test_a.csv, fits.csv, summary.json).

Usage: uv run python scripts/archive/adu_age_page.py . reports/adu-age-term/results.html
"""

import json
import math
import sys
from pathlib import Path

import pandas as pd

root, out = Path(sys.argv[1]), Path(sys.argv[2])
rep = root / "reports/adu-age-term"
tiers = pd.read_csv(rep / "tiers.csv")
ta = pd.read_csv(rep / "test_a.csv")
fits = pd.read_csv(rep / "fits.csv")
summ = json.loads((rep / "summary.json").read_text())
tokens = (root / "docs/build/identity/tokens.css").read_text()
c = summ["central"]
W, LW = 640, 170
FORMS = ("A", "A′", "A″")
CLS = {"A": "pt-a", "A′": "pt-p", "A″": "pt-q"}
STATE = {"MN": "Minnesota", "NC": "North Carolina", "OH": "Ohio", "TX": "Texas", "OR": "Oregon"}


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def ratio_chart(rows, label):
    """Observed ÷ median for Forms A, A′, A″ per row, on a log scale with the ×2 band shaded."""
    lo, hi = math.log(1 / 16), math.log(32)
    top, rh = 18, 30
    h = top + rh * len(rows) + 38

    def sx(v):
        v = min(max(v, math.exp(lo)), math.exp(hi))
        return LW + (math.log(v) - lo) / (hi - lo) * (W - LW - 20)

    g = [f'<svg viewBox="0 0 {W} {h}" class="chart" role="img" aria-label="{esc(label)}">']
    g.append(
        f'<rect x="{sx(0.5):.1f}" y="{top - 8}" width="{sx(2) - sx(0.5):.1f}" height="{h - 30 - top + 8}" class="band"/>'
    )
    for t, s in ((1 / 16, "÷16"), (1 / 4, "÷4"), (0.5, "÷2"), (1, "×1"), (2, "×2"), (4, "×4"), (16, "×16")):
        g.append(
            f'<line x1="{sx(t):.1f}" x2="{sx(t):.1f}" y1="{top - 8}" y2="{h - 30}" class="{"zero" if t == 1 else "grid"}"/>'
        )
        g.append(f'<text x="{sx(t):.1f}" y="{h - 14}" class="tick" text-anchor="middle">{s}</text>')
    for i, (name, vals) in enumerate(rows):
        y = top + rh * i + rh / 2
        g.append(f'<text x="{LW - 10}" y="{y + 4}" class="lab" text-anchor="end">{esc(name)}</text>')
        xs = [sx(v) for v in vals]
        g.append(f'<line x1="{min(xs):.1f}" x2="{max(xs):.1f}" y1="{y}" y2="{y}" class="move"/>')
        for f, x in zip(FORMS, xs, strict=True):
            g.append(f'<circle cx="{x:.1f}" cy="{y}" r="5" class="{CLS[f]}"/>')
    g.append(
        f'<text x="{W - 20}" y="{h - 1}" class="tick" text-anchor="end">observed ÷ predicted median (shaded: within ×2)</text>'
    )
    g.append("</svg>")
    return "".join(g)


def beta_chart():
    """β_o and β_a in Form A″ by fold, plus the within-state sensitivity and the one-term fits."""
    folds = ["all", "without MN", "without NC", "without OH", "without TX", "without OR"]
    rows = []
    for fold in folds:
        r = fits[(fits.variant == "central") & (fits.fold == fold) & (fits.form == "A″")].iloc[0]
        name = "All places" if fold == "all" else fold.replace("without", "Without")
        rows.append(
            (
                name,
                (r.beta_owner, r.beta_owner_low, r.beta_owner_high),
                (r.beta_age, r.beta_age_low, r.beta_age_high),
                fold == "all",
            )
        )
    w = summ["sensitivity_within_state"]
    z = 1.6448536269514722
    rows.append(
        (
            "Within states only",
            *[(b, b - z * s, b + z * s) for b, s in zip(w["betas"], w["beta_se"], strict=True)],
            False,
        )
    )
    lo, hi = -1.4, 1.2
    top, rh = 16, 30
    h = top + rh * len(rows) + 36

    def sx(v):
        return LW + (max(min(v, hi), lo) - lo) / (hi - lo) * (W - LW - 20)

    g = [f'<svg viewBox="0 0 {W} {h}" class="chart" role="img" aria-label="beta_o and beta_a by fit">']
    for t in (-1.2, -0.8, -0.4, 0, 0.4, 0.8, 1.2):
        g.append(
            f'<line x1="{sx(t):.1f}" x2="{sx(t):.1f}" y1="{top - 6}" y2="{h - 30}" class="{"zero" if t == 0 else "grid"}"/>'
        )
        g.append(f'<text x="{sx(t):.1f}" y="{h - 14}" class="tick" text-anchor="middle">{t:+g}</text>')
    for i, (name, bo, ba, main) in enumerate(rows):
        y = top + rh * i + rh / 2
        g.append(
            f'<text x="{LW - 10}" y="{y + 4}" class="lab {"cand" if main else ""}" text-anchor="end">{esc(name)}</text>'
        )
        for (b, bl, bh), cls, dy in ((bo, "own", -4), (ba, "age", 4)):
            g.append(
                f'<line x1="{sx(bl):.1f}" x2="{sx(bh):.1f}" y1="{y + dy}" y2="{y + dy}" class="ci {cls}"/>'
            )
            g.append(f'<circle cx="{sx(b):.1f}" cy="{y + dy}" r="4.5" class="pt {cls}"/>')
    g.append(
        f'<text x="{W - 20}" y="{h - 1}" class="tick" text-anchor="end">β per SD, Form A″ (90% Wald interval)</text>'
    )
    g.append("</svg>")
    return "".join(g)


t1 = tiers[tiers.tier == 1].set_index(["held_out", "form"])
state_rows = [(STATE[s], [t1.loc[(s, f), "obs_over_p50"] for f in FORMS]) for s in ("MN", "NC", "TX", "OR")]
tap = ta.pivot_table(index="name", columns="form", values="obs_over_p50")
place_rows = [
    (n.replace(" city", "").replace(" town", ""), [tap.loc[n, f] for f in FORMS]) for n in tap.index
]

fa = fits[(fits.variant == "central") & (fits.fold == "all")].set_index("form")
A, P, Q = fa.loc["A"], fa.loc["A′"], fa.loc["A″"]
s1, s2 = c["step1"], c["step2"]
lr = summ["lr"]
w = summ["sensitivity_within_state"]
ao = summ["sensitivity_age_only"]
tests = c["tests"]


def mark(v):
    return "—" if v is None else ("pass" if v else "fail")


test_rows = []
for test in ("A", "B"):
    for s in ("MN", "NC", "OH", "TX", "OR"):
        vals = [tests[f][test][s] for f in FORMS]
        if all(v is None for v in vals):
            continue
        cells = "".join(f'<td class="{"useful" if v else ""}">{mark(v)}</td>' for v in vals)
        test_rows.append(f"<tr><td>Test {test}</td><td>{STATE[s]}</td>{cells}</tr>")
test_rows.append(
    "<tr class='sum'><td colspan='2'>Passed</td>"
    + "".join(f"<td>{c['tests_passed'][f]}</td>" for f in FORMS)
    + "</tr>"
)

tier_rows = []
for s in ("MN", "NC", "TX", "OR"):
    for tier in (0, 1, 2):
        cells = []
        for f in FORMS:
            r = tiers[(tiers.held_out == s) & (tiers.tier == tier) & (tiers.form == f)].iloc[0]
            u = "useful" if r.useful else ""
            cells.append(
                f'<td class="num">{r.p10:,.0f}–{r.p50:,.0f}–{r.p90:,.0f}</td><td class="num {u}">{r.obs_over_p50:.2f}</td>'
            )
        obs = tiers[(tiers.held_out == s) & (tiers.tier == tier)].observed.iloc[0]
        tier_rows.append(
            f"<tr><td>{STATE[s] if tier == 0 else ''}</td><td>{tier}</td><td class='num'>{obs:,.0f}</td>{''.join(cells)}</tr>"
        )

nc_med = {f: ta[(ta.form == f) & (ta.state == "NC")].obs_over_p50.median() for f in FORMS}
u = c["useful_states_by_tier"]

html = f"""<title>ADU housing-age refit</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=Public+Sans:wght@400;600;700&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&display=swap">
<style>
/* Layout: one reading column; headline, stat row, decision panel, numbered findings each with a chart or table, then the tier table. */
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
.dot.a {{ background: var(--ink-faint); }} .dot.p {{ background: var(--scenario-adu); }} .dot.q {{ background: var(--brass); }}
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
.chart .pt-q {{ fill: var(--brass); }}
.chart .ci {{ stroke-width: 3; }}
.chart .ci.own {{ stroke: var(--scenario-adu); }} .chart .pt.own {{ fill: var(--scenario-adu); }}
.chart .ci.age {{ stroke: var(--brass); }} .chart .pt.age {{ fill: var(--brass); }}
.scroll {{ overflow-x: auto; }}
table {{ border-collapse: collapse; width: 100%; font-size: 13px; }}
table.wide {{ min-width: 640px; }}
th, td {{ text-align: left; padding: 6px 8px; border-bottom: 1px solid var(--rule); }}
thead th {{ font-weight: 600; color: var(--ink-muted); font-size: 12px; }}
td.num {{ font-family: var(--font-mono); font-variant-numeric: tabular-nums; }}
td.useful {{ color: var(--confidence-inside); font-weight: 600; }}
tr.sum td {{ font-weight: 600; border-top: 2px solid var(--rule); }}
.note {{ font-size: 13px; color: var(--ink-muted); }}
code {{ font-family: var(--font-mono); font-size: 12.5px; }}
footer {{ border-top: 1px solid var(--rule); padding-top: var(--space-4); font-size: 13px; color: var(--ink-muted); display: flex; flex-direction: column; gap: var(--space-2); }}
</style>
<main>
<header>
  <div class="eyebrow">Lotline · D-087 ADU housing age · 14 Nov 2026</div>
  <h1>Owner share and housing age both improve the held-out ADU score, but the pre-set rule keeps Form A</h1>
  <p class="lede">We refitted three forms on the checked rule rows: today's Form A, A′ (plus owner-occupied share) and A″ (plus owner share and housing age). Both challengers beat A on held-out places by more than the bar. Each passes one fewer of tests A–B than A, so under D-084's rule, fixed before the run, A stays. Housing age adds nothing held-out on top of owner share.</p>
</header>

<div class="stats">
  <div class="stat"><b>{Q.beta_owner:+.2f}</b><span>β_o per SD of owner share in A″ (90%: {Q.beta_owner_low:+.2f} to {Q.beta_owner_high:+.2f})</span></div>
  <div class="stat"><b>{Q.beta_age:+.2f}</b><span>β_a per SD of housing age in A″ (90%: {Q.beta_age_low:+.2f} to {Q.beta_age_high:+.2f})</span></div>
  <div class="stat"><b>{A.alpha:.2f} → {Q.alpha:.2f}</b><span>place-effect variance α, A → A″ ({(1 - Q.alpha / A.alpha) * 100:.0f}% less; A′ {P.alpha:.2f})</span></div>
  <div class="stat"><b>2 · 1 · 1</b><span>tests A–B passed by A, A′, A″ (the rule needs ≥ A's)</span></div>
</div>

<div class="decision">
  <span class="tag">Needs Ben's call</span>
  <h2>The rule keeps Form A in both steps. Accept that?</h2>
  <ol>
    <li><b>Recommended:</b> accept it. Keep Form A as the working ADU form, and don't adopt A′ (#418) or A″. Record that both terms carry held-out signal, and that the tests-count gate turned on one place each (College Station in Texas; North Carolina's median of {nc_med["A′"]:.2f} against a bar of 2). Re-read once test D runs after #420 merges, without changing the rule.</li>
    <li>Adopt A′ anyway, on its held-out score (+{s1["log_gain"]:.1f} against a bar of {2 * s1["log_gain_se"]:.1f}). That overrides a rule written before the run, after seeing which way it fell, so it would need its own dated deviation.</li>
    <li>Keep A, and write a new entry for housing age as a <em>within-state</em> term only, since that is where its signal sits (β_a {w["betas"][1]:+.2f} within states, with owner share near zero). That is a fresh, pre-registered test, not a rescue of this one.</li>
  </ol>
</div>

<section>
  <div class="num-tag">Finding 1</div>
  <h2>Both challengers clear the score bar; both lose on the tests count</h2>
  <p>No form passes D-075's claim rule at any tier (it needs 4 useful states). So the rule falls to the held-out score, gated by tests A–B. Step 1, A′ against A: +{s1["log_gain"]:.1f} over {c["places_scored"]} places, bar {2 * s1["log_gain_se"]:.1f}. Step 2, A″ against A (step 1's winner): +{s2["log_gain"]:.1f}, bar {2 * s2["log_gain_se"]:.1f}. Both clear it. But A passes test A in Texas and test B in Ohio, while A′ and A″ pass only Ohio's test B.</p>
  <div class="scroll"><table>
    <thead><tr><th>Test</th><th>State</th><th>Form A</th><th>Form A′</th><th>Form A″</th></tr></thead>
    <tbody>{"".join(test_rows)}</tbody>
  </table></div>
  <p class="note">Texas's test A is one place, College Station, a college town and the most renter-heavy place in the fit. Owner share lifts its median from 6 to 37 against 5 observed. Without it, the counts tie at 1 and step 1 would pick A′ (gain +8.1, bar 7.3). That check was run after the result and does not change the decision. Test C runs for Form A only (the scenario engine has no place terms); it passes in all five states.</p>
</section>

<section>
  <div class="num-tag">Finding 2</div>
  <h2>Housing age adds nothing held-out on top of owner share</h2>
  <p>A″ against A′ directly: +{c["log_gain_a2_over_a"][0] - s1["log_gain"]:.2f} in held-out log score, against 2 SE of about 3.6. In-sample, age's likelihood-ratio statistic over A′ is {lr["A″ vs A′"]:.1f} on one degree of freedom. The two terms are correlated (r {summ["z"]["corr_owner_age_fit_places"]:.2f} across places), and owner share takes most of what age offers. Alone, age does about a third as well (LR {ao["lr_vs_a"]:.1f} against A, compared with {lr["A′ vs A"]:.1f} for owner share).</p>
  <p>At tier 1, Minnesota's over-prediction shrinks most under A′. A″ gives back part of that gain, likely because Minnesota's suburbs are both owner-heavy and newer.</p>
  <div class="legend"><span><i class="dot a"></i>Form A</span><span><i class="dot p"></i>A′ (owner share)</span><span><i class="dot q"></i>A″ (owner share + age)</span></div>
  {ratio_chart(state_rows, "observed over median by held-out state, tier 1")}
  <p class="note">Useful states (range holds the total, median within ×2), tiers 0–1–2: A {u["A"]["0"]}–{u["A"]["1"]}–{u["A"]["2"]}, A′ {u["A′"]["0"]}–{u["A′"]["1"]}–{u["A′"]["2"]}, A″ {u["A″"]["0"]}–{u["A″"]["1"]}–{u["A″"]["2"]}. Ohio cannot be scored: its one fit place is its tier-2 city.</p>
</section>

<section>
  <div class="num-tag">Finding 3</div>
  <h2>New places: renter-heavy cities get closer; College Station overshoots</h2>
  <p>Test A predicts each place added since D-053 from a fit without it. Asheville, Durham, Wilmington, Medford and Salem all move toward their observed counts. North Carolina still fails, narrowly: its median ratio is {nc_med["A′"]:.2f} under A′ and {nc_med["A″"]:.2f} under A″, against a bar of 2. Cary's predicted median is 4 here, against 22 in D-084's run. I have not traced which input change moved it.</p>
  <div class="legend"><span><i class="dot a"></i>Form A</span><span><i class="dot p"></i>A′</span><span><i class="dot q"></i>A″</span></div>
  {ratio_chart(place_rows, "test A observed over median by new place")}
</section>

<section>
  <div class="num-tag">Finding 4</div>
  <h2>Between states it is owner share; within states it is housing age</h2>
  <p>In the pooled A″, both β's keep their sign whichever state is left out. Owner share's interval stays clear of zero every time. Age's crosses zero without North Carolina. With one θ per state, the picture flips: owner share falls to {w["betas"][0]:+.2f} (SE {w["beta_se"][0]:.2f}), and age rises to {w["betas"][1]:+.2f} (SE {w["beta_se"][1]:.2f}). Much of owner share's pooled pull is the difference between states. Age's is the difference between places inside a state. The joint draws carry their correlation (r {Q.beta_corr:.2f}).</p>
  <div class="legend"><span><i class="dot p"></i>β_o, owner share</span><span><i class="dot q"></i>β_a, housing age (share built before 1960)</span></div>
  {beta_chart()}
</section>

<section>
  <div class="num-tag">Data-tier table</div>
  <h2>Ranges by held-out state and tier</h2>
  <div class="scroll"><table class="wide">
    <thead><tr><th>State</th><th>Tier</th><th>Observed</th><th>A P10–P50–P90</th><th>÷ P50</th><th>A′ P10–P50–P90</th><th>÷ P50</th><th>A″ P10–P50–P90</th><th>÷ P50</th></tr></thead>
    <tbody>{"".join(tier_rows)}</tbody>
  </table></div>
  <p class="note">Green ratios are useful. Fits on all 64 places (491 place-years): A θ {A.theta * 1000:.3f} per 1,000 eligible lots, α {A.alpha:.2f}; A′ θ {P.theta * 1000:.3f}, α {P.alpha:.2f}; A″ θ {Q.theta * 1000:.3f}, α {Q.alpha:.2f}. All three are at m_o 1.0 and m_x 0.8. D-079 had m_x 0.4. With m_x held at 0.4, A″'s β's barely move (β_o {summ["sensitivity_mx_0_4"]["A″ at m_x 0.4"]["beta_owner"]:+.2f}, β_a {summ["sensitivity_mx_0_4"]["A″ at m_x 0.4"]["beta_age"]:+.2f}).</p>
</section>

<footer>
  <div>Housing age: ACS 2011–15 B25034, share of units built before 1960, standardized on D-083's 57 places (center 0.2045, scale 0.1669). Owner share as in D-084. Six Minnesota townships use their county subdivision's rows, and Durham County unincorporated uses its county less its places. The rule rows are #419's head (ef37063f), merged into this branch, not yet <code>main</code>. Test D waits for #420.</div>
  <div>Sources: <code>reports/adu-age-term/</code>, <code>src/lotline/model/adu_terms.py</code>, on branch <code>ws/adu-age-term</code> (PR #426). Method: D-087 in <code>docs/analysis_plan.md</code>. Run offline from cached data, 20,000 draws. St. Paul stays out. Nothing was unblinded, and nothing was written to config.</div>
</footer>
</main>
"""
out.write_text(html)
print(out, len(html))
