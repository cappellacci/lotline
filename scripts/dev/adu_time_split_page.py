# ruff: noqa: E501  (long lines are the HTML/CSS page template)
"""Build the D-090 results page from reports/adu-time-split (totals.csv, place_scores.csv, fits.csv, summary.json).

Usage: python scripts/dev/adu_time_split_page.py . reports/adu-time-split/results.html
"""

import json
import math
import sys
from pathlib import Path

import pandas as pd

root, out = Path(sys.argv[1]), Path(sys.argv[2])
rep = root / "reports/adu-time-split"
tot = pd.read_csv(rep / "totals.csv")
ps = pd.read_csv(rep / "place_scores.csv")
fits = pd.read_csv(rep / "fits.csv")
summ = json.loads((rep / "summary.json").read_text())
tokens = (root / "docs/build/identity/tokens.css").read_text()
c = summ["central"]
v = c["verdict"]
W, LW = 640, 170
FC = ("F0", "F1", "F2", "F1 + trend")
CLS = {"F0": "f0", "F1": "f1", "F2": "f2", "F1 + trend": "ft"}
LABEL = {
    "F0": "Persistence (F0)",
    "F1": "Form A, own history (F1)",
    "F2": "F1 + housing age (F2)",
    "F1 + trend": "F1 + trend (sensitivity)",
}
STATE = {"MN": "Minnesota", "NC": "North Carolina", "TX": "Texas", "OR": "Oregon"}
SCORED = ("MN", "NC", "TX", "OR")


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def ratio_chart(rows, label, forecasters=FC):
    """Observed ÷ predicted median per row and forecaster, log scale, the ×2 band shaded."""
    lo, hi = math.log(1 / 16), math.log(16)
    top, rh = 18, 30
    h = top + rh * len(rows) + 38

    def sx(x):
        x = min(max(x, math.exp(lo)), math.exp(hi))
        return LW + (math.log(x) - lo) / (hi - lo) * (W - LW - 20)

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
        xs = [sx(vals[f]) for f in forecasters if f in vals and pd.notna(vals[f])]
        if xs:
            g.append(f'<line x1="{min(xs):.1f}" x2="{max(xs):.1f}" y1="{y}" y2="{y}" class="move"/>')
        for f in forecasters:
            if f in vals and pd.notna(vals[f]):
                g.append(
                    f'<circle cx="{sx(vals[f]):.1f}" cy="{y}" r="5" class="{CLS[f]}"><title>{esc(LABEL[f])}: {vals[f]:.2f}</title></circle>'
                )
    g.append(
        f'<text x="{W - 20}" y="{h - 1}" class="tick" text-anchor="end">observed ÷ predicted median (shaded: within ×2)</text>'
    )
    g.append("</svg>")
    return "".join(g)


def legend(forecasters=FC):
    return (
        '<div class="legend">'
        + "".join(f'<span><i class="dot {CLS[f]}"></i>{esc(LABEL[f])}</span>' for f in forecasters)
        + "</div>"
    )


hist = tot[tot.line == "history"].set_index(["state", "forecaster"])
state_rows = [(STATE[s], {f: hist.loc[(s, f), "obs_over_p50"] for f in FC}) for s in SCORED]

band_rows = []
for s in SCORED:
    obs = hist.loc[(s, "F0"), "observed"]
    for i, f in enumerate(FC):
        r = hist.loc[(s, f)]
        cls_in = "useful" if r.inside else ""
        cls_2 = "useful" if r.within_2x else ""
        band_rows.append(
            f"<tr><td>{STATE[s] if i == 0 else ''}</td><td class='num'>{f'{obs:,.0f}' if i == 0 else ''}</td><td>{esc(LABEL[f])}</td>"
            f"<td class='num'>{r.p10:,.0f}–{r.p50:,.0f}–{r.p90:,.0f}</td><td class='num {cls_2}'>{r.obs_over_p50:.2f}</td>"
            f"<td class='{cls_in}'>{'yes' if r.inside else 'no'}</td></tr>"
        )

h = ps[(ps["class"] == "history") & (ps.observed >= 50)].copy()
h["F0"] = h.observed / h["p50_F0"]
h["F1"] = h.observed / h["p50_F1"]
h["F1 + trend"] = h.observed / h["p50_F1 + trend"]
pr = pd.read_csv(rep / "places.csv").set_index("geoid")
h["rc"] = [pr.loc[g, "rule_change_years"] if g in pr.index else "" for g in h.geoid]
h = h.sort_values(["state", "observed"], ascending=[True, False])
big_rows = [
    (
        f"{n.replace(' city', '').replace(' town', '')}{' ·' if isinstance(rc, str) and rc else ''}",
        {"F0": a, "F1": b, "F1 + trend": t},
    )
    for n, a, b, t, rc in zip(h.name, h.F0, h.F1, h["F1 + trend"], h.rc, strict=True)
]

hh = ps[ps["class"] == "history"].copy()
hh["d"] = hh.ls_F1 - hh.ls_F0
top_d = pd.concat([hh.nsmallest(4, "d"), hh.nlargest(4, "d")]).sort_values("d")
d_rows = "".join(
    f"<tr><td>{esc(r['name'])}</td><td>{r.state}</td><td class='num'>{r.observed:,.0f}</td><td class='num'>{r.p50_F0:,.0f}</td>"
    f"<td class='num'>{r.p50_F1:,.0f}</td><td class='num'>{r.d:+.1f}</td><td>{esc(pr.loc[r.geoid, 'rule_change_years']) if isinstance(pr.loc[r.geoid, 'rule_change_years'], str) else '—'}</td></tr>"
    for _, r in top_d.iterrows()
)

other_rows = []
for line in (
    "history, rule change in window",
    "history, no rule change",
    "new places in a known state",
    "thin history (1 fit year)",
):
    t = tot[(tot.line == line) & tot.forecaster.isin(["F0", "F1"])]
    for s in SCORED:
        r = t[t.state == s]
        if r.empty:
            continue
        cells = []
        for f in ("F0", "F1"):
            q = r[r.forecaster == f]
            if q.empty:
                cells.append("<td class='num'>—</td><td></td>")
            else:
                q = q.iloc[0]
                cells.append(
                    f"<td class='num'>{q.p10:,.0f}–{q.p50:,.0f}–{q.p90:,.0f}</td><td class='num {'useful' if q.useful else ''}'>{q.obs_over_p50:.2f}</td>"
                )
        other_rows.append(
            f"<tr><td>{esc(line)}</td><td>{s}</td><td class='num'>{int(r.places.iloc[0])}</td><td class='num'>{r.observed.iloc[0]:,.0f}</td>{''.join(cells)}</tr>"
        )

f1 = fits[fits.forecaster == "F1"].set_index("state")
f2 = fits[fits.forecaster == "F2"].set_index("state")
tr = fits[fits.forecaster == "F1 + trend"].set_index("state")
fit_rows = "".join(
    f"<tr><td>{STATE[s]}</td><td class='num'>{f1.loc[s, 'theta'] * 1000:.2f} ({f1.loc[s, 'theta_low'] * 1000:.2f}–{f1.loc[s, 'theta_high'] * 1000:.2f})</td>"
    f"<td class='num'>{f2.loc[s, 'theta'] * 1000:.2f}</td><td class='num'>×{math.exp(tr.loc[s, 'trend_per_year']):.2f}</td></tr>"
    for s in SCORED
)
A1, A2 = f1.iloc[0], f2.iloc[0]
w2 = {f: sum(bool(hist.loc[(s, f), "within_2x"]) for s in SCORED) for f in FC}
ins = {f: sum(bool(hist.loc[(s, f), "inside"]) for s in SCORED) for f in FC}
g10, s10 = c["log_gain_F1_over_F0"]
g21, s21 = c["log_gain_F2_over_F1"]

html = f"""<title>ADU own-history forecast</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=Public+Sans:wght@400;600;700&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&display=swap">
<style>
/* Layout: one reading column; headline, stat row, decision panel, numbered findings each with a chart or table. */
{tokens}
body {{ background: var(--paper); color: var(--ink); font-family: var(--font-sans); font-size: 15px; line-height: 1.55;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); padding-block: var(--space-7); }}
main {{ max-width: 720px; margin: 0 auto; display: flex; flex-direction: column; gap: var(--space-7); }}
header, section {{ display: flex; flex-direction: column; gap: var(--space-3); min-width: 0; }}
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
.dot.f0 {{ background: var(--ink-faint); }} .dot.f1 {{ background: var(--scenario-adu); }} .dot.f2 {{ background: var(--brass); }} .dot.ft {{ background: var(--scenario-fees); }}
.chart {{ width: 100%; height: auto; display: block; }}
.chart text {{ font-family: var(--font-sans); }}
.chart .grid {{ stroke: var(--rule); stroke-width: 1; }}
.chart .zero {{ stroke: var(--ink-faint); stroke-width: 1.5; }}
.chart .band {{ fill: var(--confidence-inside); fill-opacity: .10; }}
.chart .tick {{ fill: var(--ink-faint); font-size: 11px; font-family: var(--font-mono); }}
.chart .lab {{ fill: var(--ink-muted); font-size: 12.5px; }}
.chart .move {{ stroke: var(--rule); stroke-width: 3; }}
.chart .f0 {{ fill: var(--ink-faint); }} .chart .f1 {{ fill: var(--scenario-adu); }} .chart .f2 {{ fill: var(--brass); }} .chart .ft {{ fill: var(--scenario-fees); }}
.scroll {{ overflow-x: auto; }}
table {{ border-collapse: collapse; width: 100%; font-size: 13px; }}
table.wide {{ min-width: 600px; }}
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
  <div class="eyebrow">Lotline · D-090 ADU within-state forecast · 14 Nov 2026</div>
  <h1>A state's own ADU history does not forecast its next five years inside the range</h1>
  <p class="lede">We fitted each state on its own 2016–2019 permits and forecast 2021–2025 under the rules actually in force. Form A with each place's own history (F1) was useful in 1 of 4 states; the pre-set bar was 3. It did no better than carrying each place's old rate forward, and housing age did not help. Every forecaster's range was far too narrow.</p>
</header>

<div class="stats">
  <div class="stat"><b>{v["useful_states_f1"]} of 4</b><span>states where F1 was useful (inside P10–P90 and within ×2); bar 3</span></div>
  <div class="stat"><b>{g10:+.1f}</b><span>F1 − persistence, summed log score over {c["places_scored"]} places; bar 2 SE = {2 * s10:.0f}</span></div>
  <div class="stat"><b>{w2["F0"]} of 4</b><span>states where persistence's median was within ×2; its range held the total in {ins["F0"]}</span></div>
  <div class="stat"><b>{A2.beta_age:+.2f}</b><span>β per SD of housing age within states (SE {A2.beta_age_se:.2f}); F2 − F1 log score {g21:+.1f}</span></div>
</div>

<div class="decision">
  <span class="tag">Needs Ben's call</span>
  <p><b>What the pre-set rule says.</b> All three rules read against the model:</p>
  <ol>
    <li><b>Own history is not enough.</b> F1 is useful only in North Carolina. So, as D-090 fixed before the run, the tool shows the ranges and says plainly that ADU uptake cannot yet be forecast within ×2, even with local history.</li>
    <li><b>The mechanism does not beat persistence.</b> F1 − F0 is {g10:+.1f} against a bar of {2 * s10:.0f}. The spread is huge because a few cities swing it both ways (finding 3).</li>
    <li><b>Housing age does not replace F1.</b> F2 − F1 is {g21:+.1f} (bar {2 * s21:.0f}), useful in 0 states.</li>
  </ol>
  <p><b>Accept this outcome?</b> If yes, the next question is the range, not the median (finding 2).</p>
</div>

<section>
  <div class="num-tag">Finding 1</div>
  <h2>Medians land within ×2 more often than the verdict suggests</h2>
  <p>Observed 2021–2025 total over the places with history, divided by each forecaster's median. Persistence is within ×2 in all four states; F1 in two (NC, TX); the trend sensitivity in three. F1 over-predicts Minnesota and Oregon about 2.5- to 3-fold.</p>
  {legend()}
  {ratio_chart(state_rows, "Observed over median by state and forecaster")}
</section>

<section>
  <div class="num-tag">Finding 2</div>
  <h2>Every range is far too narrow</h2>
  <p>With four years of each place's own counts, the forecasters pin each place's rate tightly, and nothing in the model lets a place's rate drift from one period to the next. The P10–P90 ranges span about ±10%, so even a median off by 15% falls outside. Of 16 state-forecaster pairs, {sum(ins.values())} hold the observed total.</p>
  <div class="scroll"><table class="wide"><thead><tr><th>State</th><th>Observed</th><th>Forecaster</th><th>P10–P50–P90</th><th>Obs ÷ P50</th><th>Inside</th></tr></thead><tbody>{"".join(band_rows)}</tbody></table></div>
</section>

<section>
  <div class="num-tag">Finding 3</div>
  <h2>Where rules changed, the mechanism was right in North Carolina and wrong in Minneapolis and Bend</h2>
  <p>Places with at least 50 ADUs in the window (· = a coded rule change in 2021–2025). In Wilmington and Charlotte, F1 priced the rule change and persistence missed by ×3 to ×6. In Minneapolis, F1 expected the 2021 change to raise output; output fell. Bend had no change in the window, but its stronger rule took effect partway through the fit years, so F1 projected the full-rule rate, about 3 times what came.</p>
  {legend(("F0", "F1", "F1 + trend"))}
  {ratio_chart(big_rows, "Observed over median, large places", ("F0", "F1", "F1 + trend"))}
  <div class="scroll"><table class="wide"><thead><tr><th>Place</th><th>State</th><th>Observed</th><th>F0 P50</th><th>F1 P50</th><th>F1 − F0 log score</th><th>Rule changes</th></tr></thead><tbody>{d_rows}</tbody></table></div>
  <p class="note">The four places where F1 loses most to persistence, and the four where it gains most. These eight make up about 90% of the absolute per-place differences, and they nearly cancel: that is why the paired SE is so large.</p>
</section>

<section>
  <div class="num-tag">Finding 4</div>
  <h2>The other lines: rule changes, new places, thin history</h2>
  <div class="scroll"><table class="wide"><thead><tr><th>Line</th><th>State</th><th>Places</th><th>Observed</th><th>F0 P10–P50–P90</th><th>÷</th><th>F1 P10–P50–P90</th><th>÷</th></tr></thead><tbody>{"".join(other_rows)}</tbody></table></div>
  <p class="note">New places draw u from the prior, so their ranges are wide and they land inside more often. Raleigh and Cary (thin history: only 2019 before the window) came in about 5 times above F1's median.</p>
</section>

<section>
  <div class="num-tag">Finding 5</div>
  <h2>The fit-year trends all pointed down, and NC then rose</h2>
  <p>A log-linear trend fitted per state on 2016–2019 falls in every state. It helps Oregon and Minnesota, where counts kept falling, and doubles the miss in North Carolina, where counts surged after 2020. D-090 kept it as a sensitivity for this reason.</p>
  <div class="scroll"><table><thead><tr><th>State</th><th>F1 θ per 1,000 lots (90%)</th><th>F2 θ</th><th>Trend a year</th></tr></thead><tbody>{fit_rows}</tbody></table></div>
  <p class="note">F1: α {A1.alpha:.2f}, m_o {A1.m_owner}, m_x {A1.m_other} ({"estimated" if A1.other_estimated else "judgment"}); F2: α {A2.alpha:.2f}, m_o {A2.m_owner}, m_x {A2.m_other}. Fitted on 46 places, 168 place-years.</p>
</section>

<footer>
  <p>Built by <code>scripts/dev/adu_time_split_page.py</code> from <code>reports/adu-time-split/</code>. Method: D-090 in <code>docs/analysis_plan.md</code>, accepted 14 Nov 2026 before any run; code committed at 62669bd5 before the fit.</p>
  <p>A smoke run on a 2 × 2 grid came first; its per-state lines were seen before the full run. St. Paul is out of every fit and score; no <code>--unblind</code>. Nothing written to config.</p>
</footer>
</main>
"""
out.write_text(html)
print(f"wrote {out}")
