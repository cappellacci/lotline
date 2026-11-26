# ruff: noqa: E501  (long lines are the HTML/CSS page template)
"""Build the D-094 results page from reports/adu-type-spread.

Usage: uv run python scripts/archive/adu_type_spread_page.py . reports/adu-type-spread/results.html
"""

import json
import math
import sys
from pathlib import Path

import pandas as pd

root, out = Path(sys.argv[1]), Path(sys.argv[2])
rep = root / "reports/adu-type-spread"
s = json.loads((rep / "summary.json").read_text())
sp = pd.read_csv(rep / "spreads.csv")
cov = pd.read_csv(rep / "heldout_coverage.csv")
parts = pd.read_csv(rep / "state_width_parts.csv")
tokens = (root / "docs/build/identity/tokens.css").read_text()
NAME = {"MN": "Minnesota", "NC": "North Carolina", "TX": "Texas", "OR": "Oregon", "OH": "Ohio"}
LAB = {
    "A+P": "A + types (today)",
    "A+P+S": "A + types + spread by type",
    "A+S": "Spread by type, no type terms",
}
W = 660


def esc(x):
    return str(x).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def lam_chart():
    """λ = log(α_core ÷ α_sub) with its 90% interval: all states, and each state left out (A + P + S)."""
    rows = sp[(sp.form == "A+P+S") & ~sp.fold.str.startswith("without place") & (sp.fold != "early")]
    order = ["all"] + [f"without {st}" for st in ("MN", "NC", "TX", "OR", "OH")]
    rows = rows.set_index("fold").loc[[o for o in order if o in set(rows.fold)]]
    lw, top, rh = 150, 14, 30
    h = top + rh * len(rows) + 34
    lo, hi = -2.5, 2.0

    def sx(v):
        return lw + (v - lo) / (hi - lo) * (W - lw - 20)

    g = [
        f'<svg viewBox="0 0 {W} {h}" class="chart" role="img" aria-label="core-city spread relative to suburbs, by fold">'
    ]
    for t in (-2, -1, 0, 1, 2):
        g.append(
            f'<line x1="{sx(t):.1f}" x2="{sx(t):.1f}" y1="{top - 6}" y2="{h - 28}" class="{"zero" if t == 0 else "grid"}"/>'
        )
        g.append(
            f'<text x="{sx(t):.1f}" y="{h - 14}" class="tick" text-anchor="middle">×{math.exp(t):.2g}</text>'
        )
    for i, (fold, r) in enumerate(rows.iterrows()):
        y = top + rh * i + 10
        lab = "All states" if fold == "all" else f"Without {NAME[fold.removeprefix('without ')]}"
        g.append(f'<text x="0" y="{y + 4}" class="{"st" if fold == "all" else "lab"}">{esc(lab)}</text>')
        g.append(
            f'<line x1="{sx(max(r.lam_low, lo)):.1f}" x2="{sx(min(r.lam_high, hi)):.1f}" y1="{y}" y2="{y}" class="ci"/>'
        )
        g.append(f'<circle cx="{sx(r.lam):.1f}" cy="{y}" r="5" class="{"pt" if r.lam_high < 0 else "pt0"}"/>')
    g.append(
        f'<text x="{W - 8}" y="{h - 1}" class="tick" text-anchor="end">core cities\' luck spread ÷ suburbs\' (α_core ÷ α_sub), 90% interval</text>'
    )
    g.append("</svg>")
    return "".join(g)


def width_chart():
    rows = parts[parts.state != "OH"]
    states = [st for st in ("MN", "NC", "TX", "OR") if st in set(rows.state)]
    forms = [("A+P", "s0"), ("A+P+S", "s2")]
    lw, top, gh, rh = 130, 12, 52, 20
    h = top + gh * len(states) + 30
    lo, hi = 0, math.log(40)

    def sx(v):
        return lw + (math.log(max(v, 1)) - lo) / (hi - lo) * (W - lw - 50)

    g = [
        f'<svg viewBox="0 0 {W} {h}" class="chart" role="img" aria-label="state total range width, today vs spread by type">'
    ]
    for t in (1, 2, 5, 10, 20, 40):
        g.append(f'<line x1="{sx(t):.1f}" x2="{sx(t):.1f}" y1="{top - 4}" y2="{h - 26}" class="grid"/>')
        g.append(f'<text x="{sx(t):.1f}" y="{h - 10}" class="tick" text-anchor="middle">×{t}</text>')
    for i, st in enumerate(states):
        y0 = top + gh * i
        g.append(f'<text x="0" y="{y0 + 16}" class="st">{NAME[st]}</text>')
        for j, (f, cls) in enumerate(forms):
            v = float(rows[(rows.state == st) & (rows.form == f)].full_ratio.iloc[0])
            y = y0 + 2 + rh * j
            g.append(
                f'<rect x="{lw}" y="{y}" width="{sx(v) - lw:.1f}" height="{rh - 6}" rx="2" class="{cls}"/>'
            )
            g.append(f'<text x="{sx(v) + 5:.1f}" y="{y + rh - 9}" class="val">×{v:.1f}</text>')
    g.append(
        f'<text x="{W - 8}" y="{h - 1}" class="tick" text-anchor="end">top of range ÷ bottom (P90 ÷ P10) of the held-out state total, log scale</text>'
    )
    g.append("</svg>")
    return "".join(g)


def cov_table():
    out_rows = []
    for f in ("A+P", "A+P+S", "A+S"):
        c = cov[cov.form == f].set_index("group")
        cells = []
        for grp in ("all", "core", "suburb"):
            v = c.loc[grp, "pit_central_80"]
            cls = "good" if abs(v - 0.8) <= 0.08 else ("wide" if v > 0.8 else "narrow")
            cells.append(f"<td class='{cls}'>{v:.0%}</td>")
        out_rows.append(f"<tr><td class='form'>{esc(LAB[f])}</td>{''.join(cells)}</tr>")
    return "".join(out_rows)


def tests_table():
    cmp = s["comparisons"]
    rows = []
    for f in ("A+P", "A+P+S", "A+S"):
        u = s["useful"][f]
        tier = s["claim_tier"][f]
        if f == "A+P":
            gl = gd = "—"
        else:
            c = cmp[f"A+P vs {f}"]
            gl = f"{c['tier1_log_score_gain']['gain']:+.1f} (2 SE {2 * c['tier1_log_score_gain']['se']:.1f})"
            gd = f"{c['test_d_gain']['gain']:+.1f} (2 SE {2 * c['test_d_gain']['se']:.1f})"
        rows.append(
            f"<tr><td class='form'>{esc(LAB[f])}</td><td>{'tier ' + str(tier) if tier is not None else 'none'}</td>"
            f"<td>{u['0']} · {u['1']} · {u['2']}</td><td>{s['tests_passed'][f]}</td><td>{gl}</td><td>{gd}</td></tr>"
        )
    return "".join(rows)


full = sp[(sp.fold == "all")].set_index("form")
c = full.loc["A+P+S"]
gain = s["comparisons"]["A+P vs A+P+S"]["tier1_log_score_gain"]
wmn = sp[(sp.form == "A+P+S") & (sp.fold == "without MN")].iloc[0]
pw = parts.set_index(["form", "state"])["full_ratio"]

html = f"""<title>ADU Spread by Type</title>
<meta name="claude:viewport-fit-sides" content="cover">
<style>
{tokens}
:root {{ --s0: var(--survey); --s2: var(--tier-1); }}
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
.chart .st {{ fill: var(--ink); font-weight: 600; font-size: 12.5px; }} .chart .lab {{ fill: var(--ink); font-size: 12px; }} .chart .val {{ fill: var(--ink); }}
.grid {{ stroke: var(--rule); stroke-width: 1; }} .zero {{ stroke: var(--brass); stroke-dasharray: 4 3; stroke-width: 1.5; }}
.ci {{ stroke: var(--ink-muted); stroke-width: 2; }} .pt {{ fill: var(--tier-1); }} .pt0 {{ fill: var(--paper); stroke: var(--ink-muted); stroke-width: 2; }}
.s0 {{ fill: var(--s0); }} .s2 {{ fill: var(--s2); }}
.legend {{ display: flex; flex-wrap: wrap; gap: 14px; font-size: .85rem; color: var(--ink-muted); }}
.legend i {{ display: inline-block; width: 14px; height: 10px; border-radius: 2px; margin-right: 6px; vertical-align: middle; }}
.scroll {{ overflow-x: auto; }}
table {{ border-collapse: collapse; width: 100%; font-variant-numeric: tabular-nums; font-size: .9rem; }}
th, td {{ padding: 6px 8px; border-bottom: 1px solid var(--rule); text-align: right; }}
th {{ color: var(--ink-muted); font-weight: 500; font-size: .8rem; text-transform: uppercase; letter-spacing: .05em; }}
td.form, th.form {{ text-align: left; }}
td.good {{ color: var(--confidence-inside); font-weight: 600; }} td.wide {{ color: var(--confidence-edge); font-weight: 600; }} td.narrow {{ color: var(--confidence-outside); font-weight: 600; }}
ul {{ margin: 0; padding-left: 20px; display: grid; gap: 6px; max-width: 65ch; }}
.verdict {{ border-left: 4px solid var(--brass); padding: 10px 14px; background: var(--paper-raised); border-radius: 0 8px 8px 0; }}
.foot {{ color: var(--ink-faint); font-size: .8rem; }}
</style>
<div class="wrap">
<header style="display:grid;gap:8px">
  <div class="kicker">Lotline · ADU model · D-094 · 15 Nov 2026</div>
  <h1>Do core cities need their own spread of luck?</h1>
  <p>Today one number sets how far any place can stray from its fitted rate. D-094 gave core cities and suburbs one each, refitted on the checked rule rows (64 places), and scored it the way D-088 scored place types: each state left out, then predicted.</p>
</header>

<div class="verdict"><b>Verdict: keep A + types.</b> {esc(s["decision"]["reason"][0].upper() + s["decision"]["reason"][1:])}. Nothing goes to config or the engine.</div>

<div class="cards">
  <div class="card"><span>Core cities' spread vs suburbs', all states</span><b>×{math.exp(c.lam):.2f}</b><span>α {c.alpha_core:.2f} vs {c.alpha_sub:.2f}; 90% interval ×{math.exp(c.lam_low):.2f}–×{math.exp(c.lam_high):.2f}. Core cities do vary less in the fit.</span></div>
  <div class="card"><span>Held-out score gain</span><b>{gain["gain"]:+.1f}</b><span>log score over 64 places, 2 SE {2 * gain["se"]:.1f}. Predicting a state it hasn't seen, it is no better.</span></div>
  <div class="card"><span>Without Minnesota</span><b>×{math.exp(wmn.lam):.2f}</b><span>Leave Minnesota out and core cities look no steadier (interval ×{math.exp(wmn.lam_low):.2f}–×{math.exp(wmn.lam_high):.2f}): the evidence comes from Minnesota's uneven suburbs.</span></div>
</div>

<section>
  <h2>Where the difference comes from</h2>
  {lam_chart()}
  <p>Filled dots: the interval stays below ×1 (core cities vary less). Hollow: it crosses ×1. Leaving Minnesota out, where 41 of the 48 suburbs are, the estimate moves above ×1 and its interval spans ×1; leaving Oregon out, the interval also crosses ×1.</p>
</section>

<section>
  <h2>State ranges would be narrower</h2>
  <div class="legend"><span><i style="background:var(--s0)"></i>{LAB["A+P"]}</span><span><i style="background:var(--s2)"></i>{LAB["A+P+S"]}</span></div>
  {width_chart()}
  <p>Because core cities carry most ADUs, a smaller core-city spread narrows each held-out state's total: North Carolina ×{pw["A+P", "NC"]:.0f} → ×{pw["A+P+S", "NC"]:.0f}, Texas ×{pw["A+P", "TX"]:.0f} → ×{pw["A+P+S", "TX"]:.0f}, Oregon ×{pw["A+P", "OR"]:.0f} → ×{pw["A+P+S", "OR"]:.0f}. Narrower is only better if it is still honest, and the place-level score says the narrower ranges are no more accurate. The state-level test (D-075) is unchanged: useful in 4 of 4 states at tier 1 either way.</p>
</section>

<section>
  <h2>The tests D-094 fixed in advance</h2>
  <div class="scroll"><table>
  <tr><th class="form">Form</th><th>Claim tier</th><th>Useful states, tiers 0 · 1 · 2</th><th>Tests A–B passed</th><th>Held-out log score vs today</th><th>Test D vs today</th></tr>
  {tests_table()}
  </table></div>
  <p class="foot">D-088's rule: the new form replaces A + types only with a lower claim tier, or the same tier and a held-out gain above 2 SE; at least as many of tests A–B; and test D not worse by more than 2 SE.</p>
</section>

<section>
  <h2>Coverage by type</h2>
  <div class="scroll"><table>
  <tr><th class="form">Form</th><th>All places</th><th>Core cities</th><th>Suburbs</th></tr>
  {cov_table()}
  </table></div>
  <p class="foot">Share of held-out places inside the middle 80% of their range (randomized percentile; target 80%). Green within 8 points; amber too wide; purple too narrow. As D-094 warned, this split was seen before the entry was written, so it does not decide.</p>
</section>

<section>
  <h2>What this means</h2>
  <ul>
  <li><b>No change to the model.</b> The held-out score is flat, so the narrower state ranges are not earned.</li>
  <li><b>The fit's "core cities vary less" is a Minnesota suburbs story.</b> Its 41 suburbs are very uneven; that inflates one shared spread. Without them, nothing says core cities are steadier.</li>
  <li><b>Narrowing honestly still means more counted core cities.</b> Sixteen core cities in four states cannot pin a separate spread; the data hunt for Texas, Ohio and Oregon sources is the route.</li>
  </ul>
</section>

<p class="foot">Source: reports/adu-type-spread/ (scripts/archive/adu_type_spread.py, offline, St. Paul excluded, checked rule rows). The state multiplier's spread is learned with one α for every form (τ's profile), as under A + types. Built by scripts/dev/adu_type_spread_page.py.</p>
</div>
"""
out.write_text(html)
print(f"wrote {out}")
