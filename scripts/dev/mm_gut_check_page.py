#!/usr/bin/env python3
# ruff: noqa: E501  (long lines are the HTML/CSS page template)
"""Results page for the missing-middle gut check: reports/mm-gut-check/results.html.

    uv run python scripts/dev/mm_gut_check_page.py

Reads summary.json (`mm_gut_check_data.py`); borrows the Lotline stylesheet from the D-092 run-6 page.
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "reports" / "mm-gut-check"
STYLE_FROM = REPO / "reports" / "mm-d092" / "run6-results" / "d092-results.html"
NAMES = {"MN": "Minnesota", "NC": "North Carolina", "OH": "Ohio", "TX": "Texas", "OR": "Oregon"}
FUNNEL_STATES = ("MN", "NC", "OR")  # the largest and smallest added homes next to history
FUNNEL_ROWS = (
    ("legal", "Newly legal lots", "{:,.0f}"),
    ("pencil_out_share", "Share where building pays", "{:.1%}"),
    ("pencils", "Lots where building pays", "{:,.0f}"),
    ("theta_per_1000", "Uptake: homes per 1,000 such lots, 5 yrs", "{:.2g}"),
    ("permits_added", "Extra permitted homes", "{:,.0f}"),
    ("completion", "Completion", "{:.2f}"),
    ("net_new_share", "Share not replacing a torn-down house", "{:.2f}"),
    ("homes_in_place", "Homes in place", "{:,.0f}"),
    ("displacement", "Built elsewhere anyway", "{:.2f}"),
    ("homes_net_statewide", "Net new homes", "{:,.0f}"),
)
EXTRA_CSS = """
.wrap{max-width:860px;margin:0 auto;padding-block:var(--space-7) var(--space-8);padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px))}
body{font-size:15px;line-height:1.55}
.eyebrow{font-family:var(--font-mono);font-size:12px;letter-spacing:.06em;text-transform:uppercase;color:var(--ink-muted)}
h1{font-family:var(--font-serif);font-weight:600;font-size:36px;line-height:1.15;margin:var(--space-2) 0 var(--space-3);text-wrap:balance}
h2{font-family:var(--font-sans);font-weight:700;font-size:20px;margin:0 0 var(--space-2);text-wrap:balance}
.lede{font-family:var(--font-serif);font-size:18px;max-width:65ch;margin:0}
section{border-top:var(--stroke-hair) solid var(--rule);padding-block:var(--space-6);display:grid;gap:var(--space-3)}
section>p,section>ul{max-width:68ch;margin:0}
.verdicts{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:var(--space-3);margin-top:var(--space-5)}
.v{background:var(--paper-raised);border:var(--stroke-hair) solid var(--rule);padding:var(--space-4);display:grid;gap:var(--space-1);align-content:start}
.v .k{font-family:var(--font-mono);font-size:12px;letter-spacing:.05em;text-transform:uppercase;color:var(--ink-muted)}
.v b{font-size:17px}
.pill{display:inline-block;font-family:var(--font-mono);font-size:11px;padding:1px 6px;border-radius:var(--radius-sm);letter-spacing:.04em;text-transform:uppercase}
.ok{background:color-mix(in srgb,var(--confidence-inside) 18%,transparent);color:var(--confidence-inside)}
.warn{background:color-mix(in srgb,var(--brass) 20%,transparent);color:var(--brass)}
.scroll{overflow-x:auto}
table{border-collapse:collapse;width:100%;font-size:14px}
th,td{padding:6px 8px;border-bottom:var(--stroke-hair) solid var(--rule);text-align:left;vertical-align:top}
thead th{font-family:var(--font-mono);font-size:11px;font-weight:500;letter-spacing:.04em;text-transform:uppercase;color:var(--ink-muted);vertical-align:bottom}
td.num,th.num{text-align:right;font-family:var(--font-mono);font-variant-numeric:tabular-nums;white-space:nowrap}
.rg{display:block;font-size:11px;color:var(--ink-faint)}
td.mid{font-weight:500;color:var(--ink)}
td.num:not(.mid){color:var(--ink-muted)}
tr.drv th,tr.drv td{background:var(--survey-band)}
.spark{width:84px;height:24px}.spark polyline{fill:none;stroke:var(--ink-muted);stroke-width:1.5}
svg text{fill:var(--ink-muted);font-family:var(--font-mono);font-size:11px}
svg .lab{fill:var(--ink);font-family:var(--font-sans);font-size:13px}
svg .strong{fill:var(--ink)}
.grid{stroke:var(--rule);stroke-width:1}.one{stroke:var(--ink);stroke-width:1.5;stroke-dasharray:3 3}
.base-band{stroke:var(--scenario-baseline);stroke-width:6;stroke-linecap:round;opacity:.55}.base-dot{fill:var(--scenario-baseline)}
.add-band{stroke:var(--scenario-missing-middle);stroke-width:6;stroke-linecap:round;opacity:.45}.add-dot{fill:var(--scenario-missing-middle)}
.key{display:flex;flex-wrap:wrap;gap:var(--space-4);font-size:13px;color:var(--ink-muted)}
.key i{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:6px;vertical-align:-1px}
.say li{margin-bottom:var(--space-2)}
.foot{font-size:13px;color:var(--ink-muted)}
code{font-family:var(--font-mono);font-size:13px}
"""
TEMPLATE = """<div class="wrap">
<header>
<div class="eyebrow">Lotline · missing middle · 2026-11-17 · main {sha} · {draws:,} draws</div>
<h1>Missing-middle gut check</h1>
<p class="lede">Do the app's missing-middle numbers hold up against what each state actually permitted in 2–4 unit buildings from 2019 to 2025? Yes. No state forecasts less with reform than it built recently, and none is out of line with history. One label in the app mixed up permits and net homes; that wording fix is in PR #474.</p>
<div class="verdicts">
<div class="v"><span class="k">Units</span><b>One label fixed</b><span><span class="pill warn">wording</span> The app asked how many homes would be "permitted" but showed net new homes.</span></div>
<div class="v"><span class="k">Baseline vs history</span><b>Close, a little low</b><span><span class="pill ok">pass</span> Midpoints are {b_lo}–{b_hi}% of the recent pace; averages are {m_lo}–{m_hi}%.</span></div>
<div class="v"><span class="k">Reform vs history</span><b>All five pass</b><span><span class="pill ok">pass</span> With reform runs {f_lo:.1f} to {f_hi:.1f} times the 2023–25 pace.</span></div>
<div class="v"><span class="k">What drives it</span><b>Uptake</b><span>How many owners build sets both the level and almost all of the range.</span></div>
</div>
</header>

<section>
<h2>Five-year permits next to each state's recent pace</h2>
<p>Each bar is a five-year total divided by five years at the state's 2023–2025 pace, on a log scale. The dashed line is "same as recent years". Dots are midpoints; bars run from P10 to P90.</p>
<div class="key"><span><i style="background:var(--scenario-baseline)"></i>No reform: 2–4 unit homes permitted</span><span><i style="background:var(--scenario-missing-middle)"></i>Reform: extra permitted homes</span></div>
<div class="scroll">{svg}</div>
<p>The grey bars all sit just left of the line: the no-reform forecast is close to, and a little under, recent building. The green bars show what the reform adds on top. In Minnesota and North Carolina the midpoint roughly doubles the state's recent 2–4 unit output, and the high end is 5 to 6 times it. Oregon adds little, because its 2019 law (HB 2001) already made most of these lots legal.</p>
</section>

<section>
<h2>1 · What the numbers count</h2>
<ul>
<li><b>Period:</b> a five-year total, 2027–2031. The added homes build up slowly: 2027 holds about {y1}% of the total and 2031 about {y5}%.</li>
<li><b>Added or total:</b> added on top of the no-reform forecast.</li>
<li><b>Where:</b> statewide. The Census permit survey places cover {c_lo:.0f}–{c_hi:.1f}% of each state's permits.</li>
<li><b>Permits or homes:</b> three measures, each smaller than the last. <i>Extra permits</i> → <i>homes in place</i> (finished, minus houses torn down to build them) → <i>net new homes</i> (minus a quarter that would have been built elsewhere in the state anyway). The app's headline is net new homes, about {netshare}% of the extra permits.</li>
</ul>
<p>The app's Method card asked how many homes "would be permitted", which doesn't match a headline that counts net homes. The ADU session has changed it to "how many more homes would it gain" in PR #474.</p>
</section>

<section>
<h2>2–3 · Baseline and reform against history</h2>
<div class="scroll"><table>
<thead><tr><th>State</th><th>2019–25 2–4 unit homes</th><th class="num">2023–25 a year</th><th class="num">No reform, 5 yrs</th><th class="num">÷ recent 5-yr pace</th><th class="num">Reform adds, 5 yrs</th><th class="num">÷ recent 5-yr pace</th><th class="num">With reform ÷ recent pace</th><th class="num">Net new homes</th></tr></thead>
<tbody>{trs}</tbody></table></div>
<p><b>Baseline.</b> The no-reform midpoints sit {u_lo}–{u_hi}% under five years at the 2023–25 pace; {low_name} is lowest ({low_b:,.0f} against {low_p:,.0f}). The averages are within {m_dev}%. The yearly midpoint drifts down only because the spread of possible building cycles widens each year; the yearly averages stay flat. No state is far below its history.</p>
<p><b>Reform.</b> The app's own check compares the with-reform midpoint, a year, with the 2023–25 average: every state passes ({f_lo:.2f} to {f_hi:.2f}). In Minnesota and North Carolina the added midpoint is about the state's whole recent five-year output. That fits St. Paul, which went from about 6 to 33 two-to-four unit buildings a year after its reform. Our blind test there said the model undershoots, not overshoots.</p>
</section>

<section>
<h2>4 · Funnel for the states at the edges</h2>
<p>Minnesota and North Carolina have the largest added homes next to their history, Oregon the smallest. Each cell is P10 / <b>P50</b> / P90 across the draws. The highlighted row drives the result.</p>
<div class="scroll"><table>
<thead><tr><th>Stage</th><th class="num" colspan="3">Minnesota</th><th class="num" colspan="3">North Carolina</th><th class="num" colspan="3">Oregon</th></tr></thead>
<tbody>{ftr}</tbody></table></div>
<p>Newly legal lots and the share where building pays barely move between draws. Uptake ranges about {theta_fold:.0f}-fold, from {theta_lo:.1f} to {theta_hi:.0f} homes per 1,000 lots where building pays, and carries almost all of the range. Its value is pooled, so it is the same in every state. A state's added homes next to its history depend on how many lots pencil out per home it already builds. That is about {ratio_text}.</p>
<p>One thing to know: the share where building pays has almost no spread (P10 to P90 within {pc_spread:.0f} points), so uncertainty about costs and prices is not adding to the range.</p>
</section>

<section class="say">
<h2>5 · One line per state</h2>
<ul>{lines}</ul>
<p class="foot">"0.8% built" is the median uptake: about 8 homes per 1,000 lots where building pays, over five years.</p>
</section>

<section class="foot">
<p>Source: <code>lotline results --all</code> at main {sha} (schemas {schemas}), {draws:,} draws, seed 20261106, origin 2025. History is the Census Building Permits Survey: homes in 2–4 unit buildings, every place in the bundle's <code>observed</code> table. "With reform ÷ recent pace" is the bundle's <code>historical_floor</code> scorecard value. Nothing in config changed. Report only.</p>
</section>
</div>"""


def n(v: float) -> str:
    return f"{v:,.0f}"


def lots(v: float) -> str:
    return f"{v / 1e6:.2f}M" if v >= 1e6 else f"{v / 1e3:.0f}k"


def chart(s: dict) -> str:
    """Five-year baseline and added permits as multiples of five years at the 2023-2025 pace, log scale."""
    W, L, R, lo, hi, y0, rh = 720, 120, 24, 0.015, 12.0, 40, 56

    def x(r: float) -> float:
        return L + (math.log10(r) - math.log10(lo)) / (math.log10(hi) - math.log10(lo)) * (W - L - R)

    rows = []
    for i, (st, d) in enumerate(s.items()):
        y, p5 = y0 + i * rh, 5 * d["recent_pace"]
        rows.append(f'<text x="{L - 12}" y="{y + 14}" text-anchor="end" class="lab">{NAMES[st]}</text>')
        for j, (v, cls) in enumerate(((d["baseline"][:3], "base"), (d["added"]["permits_added"], "add"))):
            yy, r = y + j * 20 + 4, [max(t / p5, lo) for t in v]
            rows.append(
                f'<line x1="{x(r[0]):.1f}" x2="{x(r[2]):.1f}" y1="{yy}" y2="{yy}" class="{cls}-band"/>'
            )
            rows.append(f'<circle cx="{x(r[1]):.1f}" cy="{yy}" r="5" class="{cls}-dot"/>')
    bottom = y0 + len(s) * rh
    grid = "".join(
        f'<line x1="{x(t):.1f}" x2="{x(t):.1f}" y1="28" y2="{bottom - 8}" class="{"one" if t == 1 else "grid"}"/>'
        f'<text x="{x(t):.1f}" y="{bottom + 8}" text-anchor="middle" class="tick">{t:g}×</text>'
        for t in (0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10)
    )
    return (
        f'<svg viewBox="0 0 {W} {bottom + 28}" role="img" aria-label="Five-year missing-middle permits without reform '
        f"and added by reform, each as a multiple of the state's 2023-2025 pace\">{grid}"
        f'<text x="{x(1):.1f}" y="20" text-anchor="middle" class="tick strong">recent pace</text>{"".join(rows)}</svg>'
    )


def spark(h: list[float]) -> str:
    m, w, hh = max(h), 84, 22
    pts = " ".join(f"{i * w / (len(h) - 1):.1f},{hh - v / m * hh:.1f}" for i, v in enumerate(h))
    return f'<svg viewBox="-2 -2 {w + 4} {hh + 4}" class="spark" aria-hidden="true"><polyline points="{pts}"/></svg>'


def main() -> None:
    s = json.loads((OUT / "summary.json").read_text())
    p5 = {st: 5 * d["recent_pace"] for st, d in s.items()}
    b_share = {st: d["baseline"][1] / p5[st] * 100 for st, d in s.items()}
    m_share = {st: d["baseline"][3] / p5[st] * 100 for st, d in s.items()}
    floors = [d["floor"] for d in s.values()]
    low = min(b_share, key=b_share.get)
    add_years = [sum(d["added_by_year_p50"]) for d in s.values()]
    first = [d["added_by_year_p50"][0] / t * 100 for d, t in zip(s.values(), add_years, strict=True)]
    last = [d["added_by_year_p50"][-1] / t * 100 for d, t in zip(s.values(), add_years, strict=True)]
    net = [d["added"]["homes_net_statewide"][1] / d["added"]["permits_added"][1] * 100 for d in s.values()]
    th_lo = min(d["funnel"]["theta_per_1000"][0] for d in s.values())
    th_hi = max(d["funnel"]["theta_per_1000"][2] for d in s.values())
    per_home = {st: d["funnel"]["pencils"][1] / d["recent_pace"] for st, d in s.items()}
    ratio_text = ", ".join(f"{per_home[st]:,.0f} in {NAMES[st]}" for st in s)
    pc_spread = max(
        (d["funnel"]["pencil_out_share"][2] - d["funnel"]["pencil_out_share"][0]) * 100 for d in s.values()
    )
    trs = "".join(
        f'<tr><th scope="row">{NAMES[st]}</th><td class="sp">{spark(list(d["history"].values()))}</td>'
        f'<td class="num">{n(d["recent_pace"])}</td>'
        f'<td class="num">{n(d["baseline"][1])}<span class="rg">{n(d["baseline"][0])}–{n(d["baseline"][2])}</span></td>'
        f'<td class="num">{b_share[st]:.0f}%</td>'
        f'<td class="num">{n(d["added"]["permits_added"][1])}<span class="rg">{n(d["added"]["permits_added"][0])}–{n(d["added"]["permits_added"][2])}</span></td>'
        f'<td class="num">{d["added"]["permits_added"][1] / p5[st]:.2f}×</td>'
        f'<td class="num">{d["floor"]:.2f}</td><td class="num">{n(d["added"]["homes_net_statewide"][1])}</td></tr>'
        for st, d in s.items()
    )
    ftr = "".join(
        f'<tr{" class=drv" if key == "theta_per_1000" else ""}><th scope="row">{label}</th>'
        + "".join(
            f'<td class="num{" mid" if k == 1 else ""}">{fmt.format(v)}</td>'
            for st in FUNNEL_STATES
            for k, v in enumerate(s[st]["funnel"][key])
        )
        + "</tr>"
        for key, label, fmt in FUNNEL_ROWS
    )
    lines = "".join(
        f"<li><b>{NAMES[st]}:</b> {lots(d['funnel']['legal'][1])} newly legal lots × "
        f"{d['funnel']['pencil_out_share'][1]:.0%} where building pays × "
        f"{d['funnel']['theta_per_1000'][1] / 10:.1f}% built in five years ≈ "
        f"<b>{n(round(d['added']['permits_added'][1], -2))}</b> extra permitted homes "
        f"({n(round(d['added']['homes_net_statewide'][1], -1))} net), against about "
        f"{n(round(d['baseline'][1], -2))} without reform.</li>"
        for st, d in s.items()
    )
    any_d = next(iter(s.values()))
    page = TEMPLATE.format(
        sha=any_d["commit_sha"][:8], draws=any_d["n_draws"], schemas=any_d["schemas_version"],
        b_lo=round(min(b_share.values())), b_hi=round(max(b_share.values())),
        m_lo=round(min(m_share.values())), m_hi=round(max(m_share.values())),
        f_lo=min(floors), f_hi=max(floors), y1=round(sum(first) / len(first)), y5=round(sum(last) / len(last)),
        c_lo=min(d["baseline_coverage"] for d in s.values()) * 100,
        c_hi=max(d["baseline_coverage"] for d in s.values()) * 100,
        netshare=round(sum(net) / len(net)),
        u_lo=round(100 - max(b_share.values())), u_hi=round(100 - min(b_share.values())),
        low_name=NAMES[low], low_b=s[low]["baseline"][1], low_p=p5[low],
        m_dev=round(max(abs(v - 100) for v in m_share.values())),
        theta_fold=th_hi / th_lo, theta_lo=th_lo, theta_hi=th_hi, ratio_text=ratio_text, pc_spread=pc_spread,
        svg=chart(s), trs=trs, ftr=ftr, lines=lines,
    )  # fmt: skip
    head = (
        '<meta charset="utf-8">\n<title>Missing-middle gut check</title>\n<meta name="claude:viewport-fit-sides" content="cover">\n'
        '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500'
        '&family=Public+Sans:wght@400;600;700&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&display=swap">\n'
    )
    html = f"{head}<style>{style()}{EXTRA_CSS}</style>\n{page}\n"
    (OUT / "results.html").write_text(html)
    print(f"wrote {OUT / 'results.html'}")


def style() -> str:
    return re.search(r"<style>(.*?)</style>", STYLE_FROM.read_text(), re.S).group(1)


if __name__ == "__main__":
    main()
