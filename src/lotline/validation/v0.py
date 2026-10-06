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

Pass rule *(proposed, validation plan §3)*: BPS totals match exactly in every compared year. Census says exact
agreement isn't expected: state totals are revised after the annual survey and include late reports and
corrections the place files may not (BPS methodology). The report therefore also counts years within
TOLERANCE, the rule we suggest adopting at pre-registration.
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
TOLERANCE = 0.01  # suggested: |ours - Census| / Census within 1% per year


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


def build_report(state: str, store: DataStore) -> tuple[str, bool]:
    """Return (markdown, passed)."""
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
    gaps = compared[compared["status"] != "match"]
    passed = gaps.empty

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
        f"- **Result *(proposed rule: exact match every compared year)*:** "
        f"{'**PASS**' if passed else '**GAPS TO EXPLAIN**'}: {exact} of {len(compared)} years match exactly; "
        f"**{within} of {len(compared)} within {TOLERANCE:.0%}** (suggested rule; see module docstring)",
        "",
        "## 1. BPS place files add up to Census state totals",
        "",
        "Units in new privately owned residential buildings, with Census imputation. `diff` = ours − Census. "
        "Census revises state totals after the annual survey (late reports, corrections), so small gaps are "
        "expected.",
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
        sections += ["## Gaps to explain", "", _table(gaps), ""]
    return "\n".join(sections), passed


def write_report(state: str, store: DataStore, root: Path = REPO_ROOT) -> tuple[Path, bool]:
    text, passed = build_report(state, store)
    out = root / "reports" / state.lower() / "V0-national.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text)
    return out, passed
