# ruff: noqa: E501  (long lines are the HTML/CSS page template)
"""Build the D-099 results page from reports/adu-new-rule.

Usage: uv run python scripts/dev/adu_new_rule_page.py . reports/adu-new-rule/results.html
"""

import json
import sys
from pathlib import Path

import pandas as pd

root, out = Path(sys.argv[1]), Path(sys.argv[2])
rep = root / "reports/adu-new-rule"
s = json.loads((rep / "summary.json").read_text())
prof = pd.read_csv(rep / "profile_main.csv")
ho = pd.read_csv(rep / "held_out_main.csv")
ho["diff"] = ho.ls_hat - ho.ls_one
tokens = (root / "docs/build/identity/tokens.css").read_text()
W = 660
v = s["variants"]
m = v["main"]


def esc(x):
    return str(x).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def profile_chart():
    w, h, lw, bot, top = W, 220, 46, 34, 12
    p = prof[prof.nu <= 1.5]
    y = p.loglik - p.loglik.max()
    ymin = -40

    def sx(x):
        return lw + (x - 0.05) / (1.5 - 0.05) * (w - lw - 12)

    def sy(val):
        return top + (max(val, ymin) / ymin) * (h - top - bot)

    g = [
        f'<svg viewBox="0 0 {w} {h}" class="chart" role="img" aria-label="profile likelihood of the first-years share">'
    ]
    for t in (0.25, 0.5, 0.75, 1.0, 1.25, 1.5):
        g.append(
            f'<line x1="{sx(t):.1f}" x2="{sx(t):.1f}" y1="{top}" y2="{h - bot}" class="{"one" if t == 1 else "grid"}"/>'
        )
        g.append(f'<text x="{sx(t):.1f}" y="{h - bot + 16}" class="tick" text-anchor="middle">{t}</text>')
    for t in (0, -10, -20, -30, -40):
        g.append(f'<text x="{lw - 4}" y="{sy(t) + 4:.1f}" class="tick" text-anchor="end">{t}</text>')
    cut = -0.5 * 2.705543454095404
    g.append(f'<line x1="{lw}" x2="{w - 12}" y1="{sy(cut):.1f}" y2="{sy(cut):.1f}" class="cut"/>')
    pts = " ".join(f"{sx(a):.1f},{sy(b):.1f}" for a, b in zip(p.nu, y, strict=True))
    g.append(f'<polyline points="{pts}" class="curve"/>')
    g.append(f'<text x="{sx(1.0) + 4:.1f}" y="{top + 12}" class="tick">no discount (today)</text>')
    g.append(
        f'<text x="{w - 12}" y="{h - 2}" class="tick" text-anchor="end">ν: share of the mature rate in a place\'s first five years allowing ADUs · dashed: 90% cut</text>'
    )
    g.append("</svg>")
    return "".join(g)


def variants_table():
    lab = {
        "main": "Main (K = 5)",
        "K = 3": "First 3 years only",
        "explicit no-ADU before": "Only places with an explicit no-ADU rule before",
        "without Raleigh": "Raleigh left out",
    }
    rows = []
    for k, r in v.items():
        iv = r["interval"]
        rows.append(
            f"<tr><td class='form'>{lab.get(k, k)}</td><td>{r['places']}</td><td>{iv['nu']:.2f} ({iv['low']:.2f}–{iv['high']:.2f})</td><td>{r['gain']:+.2f} (2 SE {2 * r['se']:.2f})</td></tr>"
        )
    return "".join(rows)


def held_table():
    rows = []
    for _, r in ho.sort_values("observed", ascending=False).head(10).iterrows():
        rows.append(
            f"<tr><td class='form'>{esc(r['name'])}</td><td>{r.state}</td><td>{int(r.years)}</td><td>{r.observed:.0f}</td><td>{r.nu_minus_j:.2f}</td><td>{r['diff']:+.2f}</td></tr>"
        )
    return "".join(rows)


html = f"""<title>ADU First-Years Uptake</title>
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
.verdict {{ border-left: 4px solid var(--brass); padding: 10px 14px; background: var(--paper-raised); border-radius: 0 8px 8px 0; }}
.chart {{ width: 100%; height: auto; display: block; }}
.chart text {{ fill: var(--ink-muted); font-size: 11px; font-family: inherit; }}
.grid {{ stroke: var(--rule); }} .one {{ stroke: var(--brass); stroke-dasharray: 4 3; stroke-width: 1.5; }}
.cut {{ stroke: var(--ink-faint); stroke-dasharray: 3 3; }} .curve {{ fill: none; stroke: var(--survey); stroke-width: 2.5; }}
.scroll {{ overflow-x: auto; }}
table {{ border-collapse: collapse; width: 100%; font-variant-numeric: tabular-nums; font-size: .88rem; }}
th, td {{ padding: 6px 8px; border-bottom: 1px solid var(--rule); text-align: right; }}
th {{ color: var(--ink-muted); font-weight: 500; font-size: .76rem; text-transform: uppercase; letter-spacing: .05em; }}
td.form, th.form {{ text-align: left; }}
ul {{ margin: 0; padding-left: 20px; display: grid; gap: 8px; max-width: 65ch; }}
.foot {{ color: var(--ink-faint); font-size: .8rem; }}
</style>
<div class="wrap">
<header style="display:grid;gap:8px">
  <div class="kicker">Lotline · ADU model · D-099 · 16 Nov 2026</div>
  <h1>Do places that newly allow ADUs build less at first?</h1>
  <p>The gut check found that under the Handbook reform, cities that allow no ADUs today (Dallas, Fort Worth, Cleveland, now Akron) get the full rate of cities with established ADU programs. D-099 asked whether the {m["places"]} counted places that first allowed ADUs after 2016 built less in their first five years than similar places that already allowed them.</p>
</header>

<div class="verdict"><b>Verdict: no change to the model.</b> In the fit they do build somewhat less, about {m["interval"]["nu"]:.0%} of the mature rate, but that doesn't predict any better for a place left out (log score {m["gain"]:+.2f}, 2 SE {2 * m["se"]:.2f}). D-099's rule needs both, so ν stays 1.</div>

<div class="cards">
  <div class="card"><span>First-years share, fitted</span><b>{m["interval"]["nu"]:.2f}</b><span>90% interval {m["interval"]["low"]:.2f}–{m["interval"]["high"]:.2f}: excludes 1, so part 1 passes.</span></div>
  <div class="card"><span>Held-out gain</span><b>{m["gain"]:+.2f}</b><span>{m["places"]} places, each left out in turn. Part 2 fails.</span></div>
  <div class="card"><span>Would it fix Dallas?</span><b>No</b><span>Even at 0.75, θ rises in the refit while the core term falls, so a no-rule core city's rate drops by only about a quarter (×0.77), not the half to two-thirds the gut check pointed to.</span></div>
</div>

<section>
  <h2>How strongly the data favour a discount</h2>
  {profile_chart()}
  <p>The profile peaks at 0.75 and drops off on both sides. At 1.0 (no discount) it is {prof.loglik.max() - prof[prof.nu == 1.0].loglik.iloc[0]:.1f} log-likelihood units below the peak: a real but small preference, carried mostly by Minnesota suburbs that counted few or none.</p>
</section>

<section>
  <h2>The sensitivities fixed in advance</h2>
  <div class="scroll"><table><tr><th class="form">Variant</th><th>Places</th><th>ν (90%)</th><th>Held-out gain</th></tr>{variants_table()}</table></div>
  <p class="foot">With only the first three years, ν falls to 0.40, so the discount is concentrated in years 1–3, but the held-out gain is still within noise. None of the four variants passes part 2.</p>
</section>

<section>
  <h2>The places with the most ADUs</h2>
  <div class="scroll"><table><tr><th class="form">Place</th><th>State</th><th>New-rule years</th><th>ADUs built</th><th>ν without it</th><th>Log score: ν vs 1</th></tr>{held_table()}</table></div>
  <p class="foot">Each place's new-rule years predicted from its rules and type alone, from a fit without it. Positive favours the discount.</p>
</section>

<section>
  <h2>What this leaves</h2>
  <ul>
  <li><b>No first-years discount.</b> Places that newly allow ADUs build only a little less at first, and that doesn't carry over to a held-out place.</li>
  <li><b>The Dallas gap was mostly the average, not the model.</b> After this run we found the gut check had compared Dallas's average over draws (2.3 a year per 1,000 lots) with other cities' actual rates. Its median is 0.35 (P10–P90 0.01–5.1), below what Austin (0.73) and Portland (1.2) built. A single city's average is pulled far above its median by its own place luck. The gut-check page is corrected.</li>
  <li><b>One coding question remains:</b> since 2018 Dallas allows rentable ADUs by special exception or overlay, coded as "no ADUs". Recoding it as a restricted rule would scale Dallas's own tiny count instead, which would almost erase its gain.</li>
  </ul>
</section>

<p class="foot">Source: reports/adu-new-rule/ (scripts/dev/adu_new_rule.py, through adu_refit_fixed_rows.py on the D-096 rule rows; offline; St. Paul excluded). Method fixed in D-099 and accepted before the run. Built by scripts/dev/adu_new_rule_page.py.</p>
</div>
"""
out.write_text(html)
print(f"wrote {out}")
