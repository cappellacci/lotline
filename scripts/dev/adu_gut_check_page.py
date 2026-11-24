# ruff: noqa: E501  (long lines are the HTML/CSS page template)
"""The ADU gut-check page: how well the model predicts ADUs within a state, and what it predicts for 2027-31.

Usage: uv run python scripts/dev/adu_gut_check_page.py . reports/adu-gut-check/results.html

Reads: reports/adu-drift/ (D-091: forecast 2021-25 from 2016-20, own counts with drift, the engine's
no-reform method), reports/adu-types-fixed-rows/tiers.csv (D-096: each state left out), and
reports/adu-gut-check/ (counted ADUs by place and year; per-place engine results) and
reports/adu-mx-engine/ (D-097: statewide engine totals, m_x drawn from the grid).
"""

import math
import sys
from pathlib import Path

import pandas as pd

root, out = Path(sys.argv[1]), Path(sys.argv[2])
R = root / "reports"
tokens = (root / "docs/build/identity/tokens.css").read_text()
NAME = {"MN": "Minnesota", "NC": "North Carolina", "OH": "Ohio", "TX": "Texas", "OR": "Oregon"}
ORDER = ["MN", "NC", "OH", "TX", "OR"]
W = 660

drift_tot = pd.read_csv(R / "adu-drift/totals.csv")
drift_tot = drift_tot[
    (drift_tot.line == "history") & (drift_tot.variant == "drift") & (drift_tot.forecaster == "F0")
].set_index("state")
drift_pl = pd.read_csv(R / "adu-drift/place_scores.csv", dtype={"geoid": str})
drift_pl = drift_pl[
    (drift_pl["class"] == "history") & (drift_pl.variant == "drift") & (drift_pl.forecaster == "F0")
]
tiers = pd.read_csv(R / "adu-types-fixed-rows/tiers.csv")
tiers = tiers[(tiers.form == "A+P") & (tiers.tier == 1) & tiers.observed.notna()].set_index("held_out")
py = pd.read_csv(R / "adu-gut-check/place_years.csv", dtype={"geoid": str})
pl = pd.read_csv(R / "adu-gut-check/places.csv", dtype={"geoid": str})
eng = pd.read_csv(R / "adu-mx-engine/totals.csv")
eng = eng[eng.variant == "grid"]
basis = pd.read_csv(R / "adu-mx-engine/by_basis.csv")
basis = basis[(basis.variant == "grid") & (basis.no_reform_basis == "own ADU counts")].set_index("state")


def esc(x):
    return str(x).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def fmt(v):
    return f"{v:,.0f}"


def log_axis(lo, hi, x0, x1):
    a, b = math.log(lo), math.log(hi)
    return lambda v: x0 + (math.log(min(max(v, lo), hi)) - a) / (b - a) * (x1 - x0)


def range_rows(rows, ticks, lo, hi, caption, label_w=150):
    """rows: (label, sublabel, p10, p50, p90, observed)."""
    top, rh = 16, 34
    h = top + rh * len(rows) + 34
    sx = log_axis(lo, hi, label_w, W - 70)
    g = [f'<svg viewBox="0 0 {W} {h}" class="chart" role="img" aria-label="{esc(caption)}">']
    for t in ticks:
        g.append(f'<line x1="{sx(t):.1f}" x2="{sx(t):.1f}" y1="{top - 8}" y2="{h - 28}" class="grid"/>')
        g.append(f'<text x="{sx(t):.1f}" y="{h - 14}" class="tick" text-anchor="middle">{t:,}</text>')
    for i, (lab, sub, p10, p50, p90, obs) in enumerate(rows):
        y = top + rh * i + 8
        inside = p10 <= obs <= p90
        g.append(f'<text x="0" y="{y + 1}" class="st">{esc(lab)}</text>')
        g.append(f'<text x="0" y="{y + 14}" class="tick">{esc(sub)}</text>')
        g.append(f'<line x1="{sx(p10):.1f}" x2="{sx(p90):.1f}" y1="{y + 4}" y2="{y + 4}" class="band"/>')
        g.append(f'<line x1="{sx(p50):.1f}" x2="{sx(p50):.1f}" y1="{y - 3}" y2="{y + 11}" class="med"/>')
        x = sx(obs)
        g.append(
            f'<path d="M{x:.1f} {y - 3} L{x + 7:.1f} {y + 4} L{x:.1f} {y + 11} L{x - 7:.1f} {y + 4} Z" class="{"obs" if inside else "miss"}"/>'
        )
        g.append(f'<text x="{W - 64}" y="{y + 8}" class="val">{"inside" if inside else "outside"}</text>')
    g.append(f'<text x="{W - 8}" y="{h - 1}" class="tick" text-anchor="end">{esc(caption)}</text>')
    g.append("</svg>")
    return "".join(g)


def within_state_chart():
    rows = []
    for st in ORDER:
        if st not in drift_tot.index:
            continue
        r = drift_tot.loc[st]
        rows.append((NAME[st], f"{int(r.places)} places", r.p10, r.p50, r.p90, r.observed))
    return range_rows(
        rows,
        (30, 100, 300, 1000, 3000),
        30,
        4000,
        "ADUs counted 2021–25 in places with 2016–20 counts (log scale)",
    )


def scatter():
    d = drift_pl.copy()
    w, h, lw, bot, top = W, 330, 46, 36, 10
    lo, hi = 0.5, 3000
    sx = log_axis(lo, hi, lw, w - 12)
    a, b = math.log(lo), math.log(hi)

    def sy(v):
        return top + (1 - (math.log(min(max(v, lo), hi)) - a) / (b - a)) * (h - top - bot)

    g = [
        f'<svg viewBox="0 0 {w} {h}" class="chart" role="img" aria-label="place forecasts against what was built">'
    ]
    for t in (1, 10, 100, 1000):
        g.append(f'<line x1="{sx(t):.1f}" x2="{sx(t):.1f}" y1="{top}" y2="{h - bot}" class="grid"/>')
        g.append(f'<line x1="{lw}" x2="{w - 12}" y1="{sy(t):.1f}" y2="{sy(t):.1f}" class="grid"/>')
        g.append(f'<text x="{sx(t):.1f}" y="{h - bot + 14}" class="tick" text-anchor="middle">{t:,}</text>')
        g.append(f'<text x="{lw - 4}" y="{sy(t) + 4:.1f}" class="tick" text-anchor="end">{t:,}</text>')
    g.append(f'<line x1="{sx(lo):.1f}" y1="{sy(lo):.1f}" x2="{sx(hi):.1f}" y2="{sy(hi):.1f}" class="diag"/>')
    for k in (2,):
        g.append(
            f'<line x1="{sx(lo * k):.1f}" y1="{sy(lo):.1f}" x2="{sx(hi):.1f}" y2="{sy(hi / k):.1f}" class="band2"/>'
        )
        g.append(
            f'<line x1="{sx(lo):.1f}" y1="{sy(lo * k):.1f}" x2="{sx(hi / k):.1f}" y2="{sy(hi):.1f}" class="band2"/>'
        )
    for _, r in d.iterrows():
        x, y = sx(max(r.p50, 0.5)), sy(max(r.observed, 0.5))
        g.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" class="{"in" if r.inside else "out"}"><title>{esc(r["name"])}: forecast {r.p50:,.0f} ({r.p10:,.0f}–{r.p90:,.0f}), built {r.observed:,.0f}</title></circle>'
        )
    g.append(
        f'<text x="{w - 12}" y="{h - 4}" class="tick" text-anchor="end">forecast P50, 2021–25 (log)</text>'
    )
    g.append(f'<text x="{lw + 4}" y="{top + 10}" class="tick">built, 2021–25 (log)</text>')
    g.append("</svg>")
    return "".join(g)


def unseen_chart():
    rows = []
    for st in ORDER:
        if st not in tiers.index:
            continue
        r = tiers.loc[st]
        rows.append((NAME[st], f"{int(r.targets)} target places", r.p10, r.p50, r.p90, r.observed))
    return range_rows(
        rows,
        (10, 30, 100, 300, 1000, 3000),
        10,
        4000,
        "ADUs counted in the left-out state's target places, all fit years (log scale)",
    )


STATUS = {
    "handbook": "allows",
    "partial": "allows",
    "uncertain": "allows",
    "none": "none",
    "unknown": "uncoded",
}
SEGMENTS = [  # (label, column, status, css class)
    ("Built anyway: rules allow ADUs", "current_rules_adus_mean", "allows", "s-base"),
    ("Built anyway: rule not coded", "current_rules_adus_mean", "uncoded", "s-base2"),
    ("Added: rules allow ADUs but restrict them", "adu_permits_added_mean", "allows", "s-add"),
    ("Added: no ADUs allowed today", "adu_permits_added_mean", "none", "s-none"),
    ("Added: rule not coded", "adu_permits_added_mean", "uncoded", "s-add2"),
]


def reform_chart():
    """ADUs a year per state, 2027-31: no reform against full statewide reform (P10-P90, tick at P50)."""
    f = eng[eng.period.str.contains("-")].set_index(["state", "outcome"])
    lw, top, gh = 130, 14, 50
    h = top + gh * len(ORDER) + 34
    sx = log_axis(20, 20000, lw, W - 80)
    g = [
        f'<svg viewBox="0 0 {W} {h}" class="chart" role="img" aria-label="ADUs a year with no reform and with full reform">'
    ]
    for t in (30, 100, 300, 1000, 3000, 10000):
        g.append(f'<line x1="{sx(t):.1f}" x2="{sx(t):.1f}" y1="{top - 6}" y2="{h - 28}" class="grid"/>')
        g.append(f'<text x="{sx(t):.1f}" y="{h - 14}" class="tick" text-anchor="middle">{t:,}</text>')
    for i, st in enumerate(ORDER):
        y0 = top + gh * i
        g.append(f'<text x="0" y="{y0 + 18}" class="st">{NAME[st]}</text>')
        for j, (o, cls) in enumerate((("current_rules_adus", "nr"), ("handbook_adus", "fr"))):
            r = f.loc[(st, o)]
            y = y0 + 6 + 16 * j
            p10, p50, p90 = r.p10 / 5, r.p50 / 5, r.p90 / 5
            g.append(f'<line x1="{sx(p10):.1f}" x2="{sx(p90):.1f}" y1="{y}" y2="{y}" class="{cls}"/>')
            g.append(
                f'<line x1="{sx(p50):.1f}" x2="{sx(p50):.1f}" y1="{y - 6}" y2="{y + 6}" class="{cls}m"/>'
            )
            g.append(f'<text x="{sx(p90) + 6:.1f}" y="{y + 4}" class="val">{p50:,.0f}</text>')
    g.append(
        f'<text x="{W - 8}" y="{h - 1}" class="tick" text-anchor="end">ADUs a year, statewide, 2027–31 average: P10–P90, tick and label at P50 (log scale)</text>'
    )
    g.append("</svg>")
    return "".join(g)


def source_chart():
    """Where each state's five-year ADUs come from (means over draws): built anyway vs added, by today's rule."""
    p = pl.assign(status=pl.rule_class.map(STATUS).fillna("uncoded"))
    lw, top, rh = 130, 10, 40
    h = top + rh * len(ORDER) + 6
    g = [f'<svg viewBox="0 0 {W} {h}" class="chart" role="img" aria-label="where the ADUs come from">']
    x1 = W - 70
    for i, st in enumerate(ORDER):
        q = p[p.state == st]
        vals = [q.loc[q.status == stt, col].sum() for _, col, stt, _ in SEGMENTS]
        tot = sum(vals)
        y = top + rh * i
        g.append(f'<text x="0" y="{y + 18}" class="st">{NAME[st]}</text>')
        x = lw
        for v, (lab, _, _, cls) in zip(vals, SEGMENTS, strict=True):
            wv = v / tot * (x1 - lw) if tot else 0
            if wv > 0:
                g.append(
                    f'<rect x="{x:.1f}" y="{y + 4}" width="{wv:.1f}" height="22" class="{cls}"><title>{esc(lab)}: {v:,.0f}</title></rect>'
                )
                if wv > 34:
                    g.append(
                        f'<text x="{x + wv / 2:.1f}" y="{y + 19}" class="{"seg dark" if cls == "s-base2" else "seg"}" text-anchor="middle">{v / tot:.0%}</text>'
                    )
            x += wv
        added = sum(v for v, s_ in zip(vals, SEGMENTS, strict=True) if s_[1] == "adu_permits_added_mean")
        g.append(f'<text x="{x1 + 6}" y="{y + 19}" class="val">{tot / 5:,.0f}/yr</text>')
        g.append(
            f'<text x="{lw}" y="{y + 38}" class="tick">built anyway {(tot - added) / 5:,.0f} a year · added by the reform {added / 5:,.0f} a year</text>'
        )
    g.append("</svg>")
    legend = "".join(f'<span><i class="{c}"></i>{esc(lab)}</span>' for lab, _, _, c in SEGMENTS)
    return f'<div class="legend">{legend}</div>' + "".join(g)


TYPES = [("core", "Core cities"), ("suburb", "Suburbs"), ("town", "Towns")]


def by_type() -> pd.DataFrame:
    """Per state and place type: places, eligible lots, and ADUs a year (2027-31 means over draws) with no
    reform and added by full reform."""
    g = pl.groupby(["state", "place_type"]).agg(
        places=("geoid", "size"),
        lots=("eligible_parcels", "sum"),
        base=("current_rules_adus_mean", "sum"),
        added=("adu_permits_added_mean", "sum"),
    )
    g[["base", "added"]] /= 5
    return g


def type_chart():
    g = by_type()
    out = []
    for st in ORDER:
        rows = [(lab, g.loc[(st, t)]) for t, lab in TYPES if (st, t) in g.index]
        vmax = max(r.base + r.added for _, r in rows) * 1.05
        w, lw, top, rh = 300, 92, 6, 30
        h = top + rh * len(rows) + 4

        def sx(v, lw=lw, w=w, vmax=vmax):
            return lw + v / vmax * (w - lw - 70)

        svg = [
            f'<svg viewBox="0 0 {w} {h}" class="chart" role="img" aria-label="{NAME[st]} ADUs by place type">'
        ]
        for i, (lab, r) in enumerate(rows):
            y = top + rh * i
            svg.append(f'<text x="0" y="{y + 15}" class="lab">{esc(lab)}</text>')
            svg.append(
                f'<rect x="{lw}" y="{y + 4}" width="{sx(r.base) - lw:.1f}" height="16" class="s-base"/>'
            )
            svg.append(
                f'<rect x="{sx(r.base):.1f}" y="{y + 4}" width="{sx(r.base + r.added) - sx(r.base):.1f}" height="16" class="s-add"/>'
            )
            pct = r.added / r.base if r.base > 0 else float("inf")
            tag = f"+{pct:.0%}" if math.isfinite(pct) else "new"
            svg.append(
                f'<text x="{sx(r.base + r.added) + 5:.1f}" y="{y + 16}" class="val">{r.base + r.added:,.0f} ({tag})</text>'
            )
        svg.append("</svg>")
        out.append(
            f"<figure>{''.join(svg)}<figcaption><b>{NAME[st]}</b>: ADUs a year, built anyway (grey) and added by full reform (blue); label is the full-reform total and the rise.</figcaption></figure>"
        )
    return "".join(out)


def type_table():
    g = by_type()
    rows = []
    for st in ORDER:
        for t, lab in TYPES:
            if (st, t) not in g.index:
                continue
            r = g.loc[(st, t)]
            nr = r.base / r.lots * 1000
            fr = (r.base + r.added) / r.lots * 1000
            rows.append(
                f"<tr><td class='form'>{NAME[st] if t == 'core' else ''}</td><td class='form'>{lab}</td><td>{int(r.places):,}</td>"
                f"<td>{r.lots:,.0f}</td><td>{r.base:,.0f}</td><td>{r.added:,.0f}</td><td>{nr:.2f}</td><td>{fr:.2f}</td></tr>"
            )
    return "".join(rows)


def state_table():
    f = eng[eng.period.str.contains("-")].set_index(["state", "outcome"])
    rows = []
    for st in ORDER:
        cells = []
        for o in ("current_rules_adus", "handbook_adus", "adu_permits_added", "additional_homes"):
            r = f.loc[(st, o)]
            cells.append(f"<td>{fmt(r.p50)}<small>{fmt(r.p10)}–{fmt(r.p90)}</small></td>")
        rows.append(f"<tr><td class='form'>{NAME[st]}</td>{''.join(cells)}</tr>")
    return "".join(rows)


def rate_chart():
    """ADUs a year per 1,000 eligible lots under the Handbook: the engine's P10-P90 range and median for selected
    core cities (matched by state and name), against what core cities that already allow ADUs built, 2021-25."""
    pred_names = [("TX", "Dallas city"), ("TX", "Fort Worth city"), ("TX", "Houston city"), ("TX", "Austin city"),
                  ("OH", "Cleveland city"), ("OH", "Akron city"), ("OR", "Portland city"), ("NC", "Raleigh city")]  # fmt: skip
    obs_names = [("NC", "Asheville city"), ("OR", "Portland city"), ("OR", "Bend city"), ("NC", "Durham city"),
                 ("TX", "Austin city"), ("NC", "Raleigh city"), ("MN", "Minneapolis city")]  # fmt: skip
    p = (
        pl.sort_values("eligible_parcels")
        .drop_duplicates(["state", "name"], keep="last")
        .set_index(["state", "name"])
        .sort_index()
    )
    items = []
    for key in pred_names:
        if key in p.index:
            r = p.loc[key]
            f = 1000 / 5 / r.eligible_parcels
            items.append(
                (
                    f"{key[1].replace(' city', '')} (predicted)",
                    r.handbook_adus_p50 * f,
                    r.handbook_adus_p10 * f,
                    r.handbook_adus_p90 * f,
                    "p",
                )
            )
    o = py[py.year >= 2021].groupby(["state", "name"]).agg(adus=("adus", "sum"), lots=("eligible", "sum"))
    for key in obs_names:
        if key in o.index:
            v = o.loc[key].adus / o.loc[key].lots * 1000
            items.append((f"{key[1].replace(' city', '')} (built, 2021–25)", v, None, None, "o"))
    items.sort(key=lambda t: -t[1])
    lw, top, rh = 200, 8, 22
    h = top + rh * len(items) + 28
    sx = log_axis(0.01, 10, lw, W - 50)
    g = [f'<svg viewBox="0 0 {W} {h}" class="chart" role="img" aria-label="ADU rates per 1,000 lots">']
    for t in (0.01, 0.1, 0.3, 1, 3, 10):
        g.append(f'<line x1="{sx(t):.1f}" x2="{sx(t):.1f}" y1="{top}" y2="{h - 24}" class="grid"/>')
        g.append(f'<text x="{sx(t):.1f}" y="{h - 10}" class="tick" text-anchor="middle">{t:g}</text>')
    for i, (lab, v, lo, hi, kind) in enumerate(items):
        y = top + rh * i + 11
        g.append(f'<text x="{lw - 8}" y="{y + 4}" class="lab" text-anchor="end">{esc(lab)}</text>')
        if kind == "p":
            g.append(f'<line x1="{sx(lo):.1f}" x2="{sx(hi):.1f}" y1="{y}" y2="{y}" class="whisk"/>')
            g.append(f'<circle cx="{sx(v):.1f}" cy="{y}" r="4.5" class="dotp"/>')
            g.append(f'<text x="{sx(hi) + 6:.1f}" y="{y + 4}" class="val">{v:.2f}</text>')
        else:
            g.append(
                f'<rect x="{sx(v) - 5:.1f}" y="{y - 5}" width="10" height="10" class="baro" transform="rotate(45 {sx(v):.1f} {y})"/>'
            )
            g.append(f'<text x="{sx(v) + 10:.1f}" y="{y + 4}" class="val">{v:.2f}</text>')
    g.append(
        f'<text x="{W - 8}" y="{h - 1}" class="tick" text-anchor="end">ADUs a year per 1,000 eligible lots (log scale)</text>'
    )
    g.append("</svg>")
    return "".join(g)


tx = pl[pl.state == "TX"]
tx_share = (
    tx[tx.name.isin(["Dallas city", "Fort Worth city"])].adu_permits_added_p50.sum()
    / tx.adu_permits_added_p50.sum()
)
inside_places = drift_pl.inside.mean()
n_inside_states = int(
    sum(
        drift_tot.loc[s].p10 <= drift_tot.loc[s].observed <= drift_tot.loc[s].p90
        for s in drift_tot.index
        if s in NAME
    )
)
n_unseen = int(sum(tiers.loc[s].p10 <= tiers.loc[s].observed <= tiers.loc[s].p90 for s in tiers.index))
homes = eng[eng.period.str.contains("-") & (eng.outcome == "additional_homes")]

html = f"""<title>ADU Gut Check</title>
<meta name="claude:viewport-fit-sides" content="cover">
<style>
{tokens}
body {{ background: var(--paper); color: var(--ink); font-family: var(--font-body, Inter, system-ui, sans-serif); font-size: 15px; line-height: 1.55; }}
.wrap {{ max-width: 760px; margin: 0 auto; padding-block: 32px 64px; padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); display: grid; gap: 30px; }}
h1, h2, h3 {{ font-family: var(--font-display, "Space Grotesk", system-ui, sans-serif); text-wrap: balance; margin: 0; }}
h1 {{ font-size: 1.9rem; line-height: 1.15; }} h2 {{ font-size: 1.3rem; }} h3 {{ font-size: 1.05rem; }}
.kicker {{ text-transform: uppercase; letter-spacing: .08em; font-size: .75rem; color: var(--ink-muted); }}
p {{ margin: 0; max-width: 65ch; }} section {{ display: grid; gap: 12px; }}
.cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; }}
.card {{ background: var(--paper-raised); border: 1px solid var(--rule); border-radius: 8px; padding: 14px 16px; display: grid; gap: 4px; }}
.card b {{ font-family: var(--font-display, "Space Grotesk", sans-serif); font-size: 1.6rem; }}
.card span {{ color: var(--ink-muted); font-size: .85rem; }}
.flag {{ border-left: 4px solid var(--confidence-edge); }}
.chart {{ width: 100%; height: auto; display: block; }}
.chart text {{ fill: var(--ink-muted); font-size: 11px; font-family: inherit; }}
.chart .st {{ fill: var(--ink); font-weight: 600; font-size: 12.5px; }} .chart .lab {{ fill: var(--ink); font-size: 12px; }} .chart .val {{ fill: var(--ink); }}
.grid {{ stroke: var(--rule); stroke-width: 1; }}
.band {{ stroke: var(--survey); stroke-width: 8; stroke-linecap: round; opacity: .35; }} .med {{ stroke: var(--survey); stroke-width: 2.5; }}
.obs {{ fill: var(--brass); }} .miss {{ fill: var(--confidence-outside); }}
.diag {{ stroke: var(--ink-faint); stroke-width: 1.2; }} .band2 {{ stroke: var(--ink-faint); stroke-dasharray: 3 3; }}
.in {{ fill: var(--survey); opacity: .75; }} .out {{ fill: var(--confidence-outside); opacity: .85; }}
.hist {{ fill: none; stroke: var(--ink); stroke-width: 2; }} .histd {{ fill: var(--ink); }}
.pred {{ stroke: var(--survey); stroke-width: 4; stroke-linecap: round; }} .recent {{ stroke: var(--brass); stroke-width: 4; stroke-linecap: round; }}
.nr {{ stroke: var(--ink-muted); stroke-width: 7; stroke-linecap: round; opacity: .45; }} .nrm {{ stroke: var(--ink); stroke-width: 2.5; }}
.fr {{ stroke: var(--survey); stroke-width: 7; stroke-linecap: round; opacity: .45; }} .frm {{ stroke: var(--survey); stroke-width: 2.5; }}
.s-base {{ fill: var(--ink-muted); }} .s-base2 {{ fill: var(--tier-none); }} .s-add {{ fill: var(--survey); }} .s-none {{ fill: var(--brass); }} .s-add2 {{ fill: var(--tier-3); }}
.legend i.s-base {{ background: var(--ink-muted); }} .legend i.s-base2 {{ background: var(--tier-none); }} .legend i.s-add {{ background: var(--survey); }} .legend i.s-none {{ background: var(--brass); }} .legend i.s-add2 {{ background: var(--tier-3); }}
.chart .seg {{ fill: var(--paper); font-size: 10.5px; font-weight: 600; }} .chart .seg.dark {{ fill: var(--ink); }}
.whisk {{ stroke: var(--survey); stroke-width: 2; opacity: .5; }} .dotp {{ fill: var(--survey); }} .barp {{ fill: var(--survey); }} .baro {{ fill: var(--brass); }}
.pair {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 16px; }}
figure {{ margin: 0; display: grid; gap: 6px; min-width: 0; }} figcaption {{ font-size: .85rem; color: var(--ink-muted); }}
.legend {{ display: flex; flex-wrap: wrap; gap: 14px; font-size: .85rem; color: var(--ink-muted); align-items: center; }}
.legend i {{ display: inline-block; width: 18px; height: 6px; border-radius: 3px; margin-right: 6px; vertical-align: middle; }}
.scroll {{ overflow-x: auto; }}
table {{ border-collapse: collapse; width: 100%; font-variant-numeric: tabular-nums; font-size: .88rem; }}
th, td {{ padding: 6px 8px; border-bottom: 1px solid var(--rule); text-align: right; vertical-align: top; }}
td small {{ display: block; color: var(--ink-faint); font-size: .75rem; }}
th {{ color: var(--ink-muted); font-weight: 500; font-size: .76rem; text-transform: uppercase; letter-spacing: .05em; }}
td.form, th.form {{ text-align: left; }}
ul {{ margin: 0; padding-left: 20px; display: grid; gap: 8px; max-width: 65ch; }}
.foot {{ color: var(--ink-faint); font-size: .8rem; }}
</style>
<div class="wrap">
<header style="display:grid;gap:8px">
  <div class="kicker">Lotline · ADU model · gut check · 15 Nov 2026</div>
  <h1>Does the ADU model hold up, and do its 2027–31 numbers look sane?</h1>
  <p>Two questions. First, when the model forecasts ADUs it then gets to check against, how close does it come? Second, what does it predict for each state from 2027, with today's rules and with the Handbook ADU bill? The last section lists what looks off.</p>
</header>

<div class="cards">
  <div class="card"><span>Forecasting forward within a state</span><b>{n_inside_states} of {len(drift_tot)}</b><span>state totals for 2021–25 inside the forecast range; {inside_places:.0%} of {len(drift_pl)} places inside theirs.</span></div>
  <div class="card"><span>A state the model has never seen</span><b>{n_unseen} of {len(tiers)}</b><span>held-out states inside the range, using only rules and other states' data.</span></div>
  <div class="card flag"><span>Gut-check flag</span><b>{tx_share:.0%}</b><span>of Texas's added ADUs (by place medians) come from Dallas and Fort Worth, which allow no rentable ADUs by right today.</span></div>
</div>

<section>
  <h2>1 · How well does it predict ADUs within a state?</h2>
  <h3>Forecasting forward: fit on 2016–20, check against 2021–25</h3>
  <p>This is how the engine sets each counted place's no-reform rate: its own recent count, plus a "drift" allowance because places' rates change over time (D-091). Here each place's 2016–20 count forecasts its 2021–25 count.</p>
  <div class="legend"><span><i style="background:var(--survey);opacity:.35"></i>forecast P10–P90, tick at P50</span><span>◆ built (gold inside, purple outside)</span></div>
  {within_state_chart()}
  <figure>{scatter()}<figcaption>Each dot is a place: forecast median against what it built in 2021–25. The diagonal is a perfect forecast and the dashed lines are ×2 either side. Purple dots fell outside their own P10–P90. Hover for names.</figcaption></figure>
  <p>The medians track the places well across three orders of magnitude, and the ranges are about the right width (D-091 targeted 80% inside). Minnesota's suburbs scatter most because they count only a handful each.</p>
  <h3>A state it has never seen</h3>
  <p>Each state is left out, the model is fitted on the others, and the left-out state's 20 largest places are predicted from their coded rules alone (D-096). This is the honest test for a new state.</p>
  {unseen_chart()}
  <p>Every state's actual count lands inside its range, but the ranges are wide (×5 to ×50), because without a place's own counts the model can't tell a busy city from a quiet one.</p>
</section>

<section>
  <h2>2 · What does it predict for 2027–31?</h2>
  <h3>No reform against full statewide reform, ADUs a year</h3>
  <p>"No reform": today's local rules stay as they are, and places keep building at their own pace (where a place has its own counts, its recent rate). "Full reform": the Handbook rule in every place from 2027.</p>
  <div class="legend"><span><i style="background:var(--ink-muted)"></i>no reform</span><span><i style="background:var(--survey)"></i>full statewide reform</span></div>
  {reform_chart()}
  <h3>Where the ADUs come from</h3>
  <p>Each bar is the state's ADUs under full reform, 2027–31 (averages over draws), split into what would be built anyway and what the reform adds, by the place's rule today.</p>
  {source_chart()}
  <p class="foot">"Rule not coded": places with no coded local rule. They take a rule drawn from coded places like them, so part of their "built anyway" and "added" is a guess about today's rules. Averages, not medians, so they sit above the medians in the table below.</p>
  <h3>By place type</h3>
  <p>The same split by the kind of place: core cities (the largest place in a metro area, or one at least a third its size), suburbs (other places in a metro area) and towns (places in a micropolitan area or outside any metro or micro area).</p>
  <div class="pair">{type_chart()}</div>
  <div class="scroll"><table>
  <tr><th class="form">State</th><th class="form">Place type</th><th>Places</th><th>Eligible lots</th><th>Built anyway, a year</th><th>Added by reform, a year</th><th>Per 1,000 lots, no reform</th><th>Per 1,000 lots, full reform</th></tr>
  {type_table()}
  </table></div>
  <p class="foot">Averages over draws, 2027–31, every place in the state. For scale: the busiest counted places build about 1 to 2.4 ADUs a year per 1,000 lots (Portland 1.2, Asheville 2.4, 2021–25).</p>
  <h3>Statewide totals, every place, 2027–31</h3>
  <div class="scroll"><table>
  <tr><th class="form">State</th><th>ADUs, today's rules</th><th>ADUs, Handbook bill</th><th>ADUs added by the bill</th><th>Additional homes</th></tr>
  {state_table()}
  </table></div>
  <p class="foot">P50 with P10–P90 below. m_x drawn from the D-097 grid. "Additional homes" counts only ADUs that are net new and not formalizing an existing unit. Five-state total of additional homes at P50: {fmt(homes.p50.sum())} (summing medians, for scale only).</p>
</section>

<section>
  <h2>3 · What looks off</h2>
  <h3>Predicted Handbook rates for cities that allow no ADUs today, against what ADU-friendly cities built</h3>
  {rate_chart()}
  <p class="foot">Blue: the engine's Handbook prediction for 2027–31, median with P10–P90. Gold: what core cities that already allow ADUs built, 2021–25. A single city's range is very wide because it carries its own place luck; its average sits far above its median.</p>
  <ul>
  <li><b>Dallas and Fort Worth carry {tx_share:.0%} of Texas's added ADUs.</b> Neither allows rentable ADUs by right today, so the engine gives them the fitted core-city rate for their market. At the median that is about 0.35 a year per 1,000 lots, below what Austin (0.73) or Portland (1.2) actually built: plausible for a large city with no ADU history. The range is wide (P90 about 5), and the <i>average</i> (2.3) is pulled up by those high draws. <b>Correction:</b> an earlier version of this page compared that average with other cities' actual rates and overstated the problem. Dallas's coding is a separate question: since 2018 it allows rentable ADUs by special exception, coded here as "no ADUs".</li>
  <li><b>The no-reform rate runs above recent counts.</b> In places with their own counts, the engine's 2027–31 mean is above their recent rate. Minnesota is ×{basis.loc["MN"].current_rules_adus_mean / 5 / basis.loc["MN"].observed_per_year:.1f}. Two reasons: the drift term's mean is 1.7× its median (the ranges are honest, but the mean is pulled up), and a half-count starting allowance on each of Minnesota's 184 counted places, most of which counted none. Medians sit closer to recent counts.</li>
  <li><b>Oregon's added homes are tiny</b> (about 10) because almost every Oregon lot already has a coded rule allowing ADUs (22% Handbook-equivalent, 74% allowed with some conditions not coded), so the bill changes little there. That is plausible after Oregon's 2017–19 state laws, but the 74% with uncoded conditions is worth a look.</li>
  <li><b>Austin still gains under the bill</b> even though its rule is Handbook-equivalent, because its zone list covers 64% of its lots (measured on parcels). The other 36% gain.</li>
  </ul>
</section>

<p class="foot">Sources: reports/adu-drift/ (D-091, run before the rule-row checks; its forecasts use only counts, not rules), reports/adu-types-fixed-rows/ (D-096), reports/adu-mx-engine/ and reports/adu-gut-check/ (D-097 engine on PR #440's rule rows with the D-096 config, 1,000 draws, origin 2025, St. Paul left out, offline). Built by scripts/dev/adu_gut_check_page.py.</p>
</div>
"""
out.write_text(html)
print(f"wrote {out}")
