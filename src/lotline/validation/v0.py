"""V0 data-reproduction report for the national sources (validation plan §3, V0).

Question: do our adapters count what the publishers count? For each state this writes
`reports/<st>/V0-national.md` with:

1. BPS reconciliation: our place-level units summed to the state, against Census's own state totals, by year
   and building size. **Held-out state-years are not compared**: state total minus our sum would reveal the
   held-out place by subtraction.
2. Attribution: share of BPS units we can tie to a jurisdiction, and the share Census imputed.
3. Coverage of every processed table: rows, years, geographies, null rate per column.
4. FHFA and ACS gaps that later steps must work around.
5. Licenses, from the manifest.

Pass rule: every compared year within TOLERANCE (1%) of Census's state total; years outside it are listed for
explanation. This replaces the validation plan's proposed "match exactly" (deviation D-001 in
docs/analysis_plan.md, adopted by Ben 2026-10-06): Census revises state totals after the annual survey with
late reports and corrections the place files may not carry (BPS methodology), so exact agreement isn't
achievable. The check is directional: it shows our pipeline counts what Census counts, not that it is exact.
A chart of the yearly gap is written next to the report.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pandas as pd

from lotline.adapters.national import bps_state
from lotline.config import load_state
from lotline.io import DataStore
from lotline.schemas import SCHEMAS_VERSION

REPO_ROOT = Path(__file__).resolve().parents[3]
UNITS = ["units_1", "units_2", "units_3_4", "units_5p"]
TOLERANCE = 0.01  # pass rule: |ours - Census| / Census within 1% per year (analysis plan D-001)


def held_out_years(state: str) -> set[int]:
    """Years in which any held-out place has outcomes, capped at the current year."""
    this_year = dt.date.today().year
    return {
        y
        for h in load_state(state).holdouts
        for y in range(h.outcome_from.year, min(h.outcome_until.year, this_year) + 1)
    }


def reconcile(places: pd.DataFrame, census_state: pd.DataFrame, blocked: set[int]) -> pd.DataFrame:
    """Per year: our place sum vs Census state total, total and by size. Blocked years carry no numbers."""
    ours = places.groupby("year")[UNITS].sum()
    theirs = census_state.set_index("year")[UNITS]
    years = sorted(set(ours.index) | set(theirs.index))
    rows = []
    for y in years:
        if y in blocked:
            rows.append({"year": y, "status": "held out (not compared)"})
            continue
        if y not in ours.index or y not in theirs.index:
            rows.append({"year": y, "status": "missing on one side"})
            continue
        diff = ours.loc[y] - theirs.loc[y]
        rows.append(
            {
                "year": y,
                "ours": int(ours.loc[y].sum()),
                "census": int(theirs.loc[y].sum()),
                "diff": int(diff.sum()),
                "diff_pct": f"{diff.sum() / theirs.loc[y].sum():+.2%}",
                **{f"diff_{c[6:]}": int(diff[c]) for c in UNITS},
                "status": "match"
                if (diff == 0).all()
                else ("within 1%" if abs(diff.sum()) <= TOLERANCE * theirs.loc[y].sum() else "gap"),
            }
        )
    return pd.DataFrame(rows)


def passes(rec: pd.DataFrame) -> bool:
    """Pass rule (analysis plan D-001): no compared year outside TOLERANCE. Held-out years don't count."""
    return not (rec["status"] == "gap").any()


def attribution(places: pd.DataFrame) -> pd.DataFrame:
    """Share of units with no jurisdiction and share imputed by Census, by period."""
    df = places.assign(u=places[UNITS].sum(axis=1), u_rep=places[[c + "_rep" for c in UNITS]].sum(axis=1))
    out = []
    for label, lo, hi in (("1992–2008", 1992, 2008), ("2009 on", 2009, 9999)):
        w = df[df["year"].between(lo, hi)]
        total = w["u"].sum()
        out.append(
            {
                "period": label,
                "units": int(total),
                "unattributed": _pct(w.loc[w["geoid"].isna(), "u"].sum(), total),
                "imputed by Census": _pct(total - w["u_rep"].sum(), total),
                "place-years flagged imputed": _pct(w["imputed"].sum(), len(w)),
            }
        )
    return pd.DataFrame(out)


def coverage(df: pd.DataFrame, year_col: str, geo_col: str) -> dict:
    return {
        "rows": len(df),
        "years": f"{df[year_col].min()}–{df[year_col].max()}" if len(df) else "n/a",
        "geographies": df[geo_col].nunique(),
        "nulls": {c: _pct(df[c].isna().sum(), len(df)) for c in df.columns if df[c].isna().any()},
    }


def _pct(part, whole) -> str:
    return f"{part / whole:.2%}" if whole else "n/a"


def _table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_none_"
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        lines.append("| " + " | ".join(str(r[c]) if c == "year" else _fmt(r[c]) for c in cols) + " |")
    return "\n".join(lines)


def _fmt(v) -> str:
    if v is None or (not isinstance(v, str) and pd.isna(v)):
        return ""
    if isinstance(v, (int, float)) and not isinstance(v, bool) and float(v).is_integer():
        return f"{int(v):,}"
    return str(v)


def _read(store: DataStore, state: str, table: str) -> pd.DataFrame | None:
    path = store.processed(state, table)
    return pd.read_parquet(path) if path.exists() else None


def build_report(state: str, store: DataStore) -> tuple[str, bool, pd.DataFrame]:
    """Return (markdown, passed, reconciliation table)."""
    cfg = load_state(state)
    bps_places = _read(store, state, "bps_place_year")
    if bps_places is None:
        raise FileNotFoundError(f"no BPS table for {state}: run `lotline fetch --state {state} --source bps`")
    years = range(int(bps_places["year"].min()), int(bps_places["year"].max()) + 1)
    census = bps_state.load(store, years)
    census = census[census["state_fips"] == cfg.fips]
    blocked = held_out_years(state)
    rec = reconcile(bps_places, census, blocked)
    compared = rec[rec["status"].isin(["match", "within 1%", "gap"])]
    exact = int((compared["status"] == "match").sum())
    within = int(compared["status"].isin(["match", "within 1%"]).sum())
    gaps = compared[compared["status"] == "gap"]
    passed = passes(rec)

    sections = [
        f"# V0 national data check: {cfg.name}",
        "",
        f"<!-- GENERATED by `lotline validate --state {state} --step V0`. Do not edit. -->",
        "",
        f"- **Generated:** {dt.date.today().isoformat()} · schemas {SCHEMAS_VERSION}",
        "- **Data:** as pulled into `LOTLINE_DATA_DIR`; sources and dates in `docs/data_provenance.md`",
        "- **Held-out years not compared:** "
        + (", ".join(str(y) for y in sorted(blocked)) or "none")
        + " ("
        + (", ".join(f"{h.test_id} ({h.place})" for h in cfg.holdouts) or "no holdouts")
        + ")",
        f"- **Result *(rule: every compared year within {TOLERANCE:.0%})*:** "
        f"{'**PASS**' if passed else '**GAPS TO EXPLAIN**'}: {within} of {len(compared)} years within "
        f"{TOLERANCE:.0%}; {exact} match exactly",
        "",
        "## 1. BPS place files add up to Census state totals",
        "",
        "Units in new privately owned residential buildings, with Census imputation. `diff` = ours − Census. "
        "Census revises state totals after the annual survey (late reports, corrections), so small gaps are "
        "expected.",
        "",
        f"![Yearly gap between our place sums and Census state totals]({CHART_NAME})",
        "",
        _table(rec),
        "",
        "## 2. Permits tied to a jurisdiction",
        "",
        _table(attribution(bps_places)),
        "",
        "## 3. Coverage of processed tables",
        "",
    ]
    for table, year_col, geo_col in (
        ("bps_place_year", "year", "bps_id"),
        ("jurisdictions", None, "geoid"),
        ("market_geo_year", "year", "geo"),
        ("acs_geo_year", "end_year", "geo"),
    ):
        df = _read(store, state, table)
        if df is None:
            sections += [f"- `{table}`: **not built**", ""]
            continue
        if year_col is None:
            sections += [f"- `{table}`: {len(df):,} rows; kinds {df['kind'].value_counts().to_dict()}", ""]
            continue
        c = coverage(df, year_col, geo_col)
        nulls = ", ".join(f"`{k}` {v}" for k, v in c["nulls"].items()) or "none"
        sections += [
            f"- `{table}`: {c['rows']:,} rows · {c['years']} · {c['geographies']:,} geographies · "
            f"nulls: {nulls}",
            "",
        ]

    market = _read(store, state, "market_geo_year")
    acs = _read(store, state, "acs_geo_year")
    sections += ["## 4. Gaps later steps must handle", ""]
    if market is not None:
        level = market["geo"].str.split(":").str[0]
        hpi = market[market["hpi"].notna()]
        n_counties = (
            acs.loc[acs["geo"].str.startswith("county:"), "geo"].nunique() if acs is not None else None
        )
        fhfa_counties = hpi.loc[level.loc[hpi.index] == "county", "geo"].nunique()
        sections.append(f"- FHFA county house price index: {fhfa_counties} of {n_counties} counties")
        for lv in ("county", "zip5", "tract"):
            sub = market[level == lv]
            if len(sub):
                sections.append(
                    f"- FHFA {lv}-years without an index: {_pct(sub['hpi'].isna().sum(), len(sub))}"
                )
    if acs is not None:
        for lv, sub in acs.groupby(acs["geo"].str.split(":").str[0]):
            sections.append(
                f"- ACS {lv} estimates suppressed: {_pct(sub['estimate'].isna().sum(), len(sub))}"
            )
    sections += ["", "## 5. Licenses", ""]
    lic = sorted({(e.source, e.license) for e in store.manifest()})
    sections += [f"- `{s}`: {licence}" for s, licence in lic] + [""]
    if not passed:
        sections += [f"## Years outside {TOLERANCE:.0%} (to explain)", "", _table(gaps), ""]
    return "\n".join(sections), passed, rec


def write_report(state: str, store: DataStore, root: Path = REPO_ROOT) -> tuple[Path, bool]:
    text, passed, rec = build_report(state, store)
    out = root / "reports" / state.lower() / "V0-national.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text)
    plot_reconciliation(rec, load_state(state).name, out.parent / CHART_NAME)
    return out, passed


# Chart colors: reference palette (dataviz skill), light surface; one series, so no legend.
CHART_NAME = "V0-bps-reconciliation.png"
SURFACE, INK, INK_2, INK_MUTED, SERIES, BAND = (
    "#fcfcfb",
    "#0b0b0b",
    "#52514e",
    "#8a8984",
    "#2a78d6",
    "#ebeae6",
)


def plot_reconciliation(rec: pd.DataFrame, state_name: str, path: Path) -> Path:
    """Bar per year: (ours − Census) / Census with the ±TOLERANCE band; held-out years marked only."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    df = rec.copy()
    shown = df[df["status"].isin(["match", "within 1%", "gap"])]
    pct = (shown["diff"] / shown["census"] * 100).astype(float)
    fig, ax = plt.subplots(figsize=(9, 3.4), dpi=120, facecolor=SURFACE)
    ax.set_facecolor(SURFACE)
    ax.axhspan(-TOLERANCE * 100, TOLERANCE * 100, color=BAND, zorder=0, lw=0)
    ax.axhline(0, color=INK_MUTED, lw=0.8, zorder=1)
    ax.bar(shown["year"], pct, width=0.6, color=SERIES, zorder=2)
    for year, value in zip(shown["year"], pct, strict=True):
        if (
            abs(value) > TOLERANCE * 100
        ):  # label only the years that break the rule; vertical so runs don't collide
            ax.annotate(
                f"{value:+.1f}%",
                (year, value),
                xytext=(0, 3 if value > 0 else -3),
                textcoords="offset points",
                ha="center",
                va="bottom" if value > 0 else "top",
                rotation=90,
                fontsize=7,
                color=INK_2,
            )
    held = df[df["status"] == "held out (not compared)"]["year"]
    for year in held:
        ax.text(year, 0, "held out", rotation=90, ha="center", va="bottom", fontsize=7, color=INK_MUTED)
    hi = max(2.0, float(pct.max()) * 1.35) if len(pct) else 2.0  # room above bars for vertical labels
    lo = min(-2.0, float(pct.min()) * 1.35) if len(pct) else -2.0
    ax.set_ylim(lo, hi)
    ax.set_xlim(df["year"].min() - 1, df["year"].max() + 1)
    ax.set_title(
        f"{state_name}: permit units, our place sums vs Census state totals (shaded band = ±1%)",
        loc="left",
        fontsize=10,
        color=INK,
    )
    ax.set_ylabel("ours − Census, % of Census", fontsize=8, color=INK_2)
    ax.tick_params(colors=INK_2, labelsize=8, length=0)
    ax.grid(axis="y", color=BAND, lw=0.6, zorder=0)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(INK_MUTED)
    fig.tight_layout()
    fig.savefig(path, facecolor=SURFACE)
    plt.close(fig)
    return path
