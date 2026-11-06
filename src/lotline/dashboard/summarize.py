"""Summarize the collected data for the data dashboard: coverage, parcels, reforms and growth, by state.

The dashboard is a check on the data, not a model output. Every number here is a count or a share of what the
adapters have already written to `LOTLINE_DATA_DIR/processed/` (holdouts are filtered there, before anything
reaches this module), plus the coded reforms in `config/reforms/` and Census population estimates.

**States are discovered**, never listed: every `config/states/<st>.yaml` with processed data is summarized, so
a fifth state appears once its adapters have run. Nothing here is specific to one state.

Rules (documented in `docs/data_dashboard.md`):

- **Latest roll per jurisdiction.** Each parcel source is reduced to its latest vintage *per jurisdiction*
  (not per county or per file), because rolls arrive county by county and some places are kept only in older
  rolls (St. Paul, V5 snapshot rule).
- **One source per jurisdiction.** Where sources overlap, a jurisdiction takes the source named for it in
  `parcel_sources` (`config/states/<st>.yaml`, `"*"` for the rest) if that source has parcels there, otherwise
  the source with the most parcels. Counts are never added across sources.
- **Population covered.** A jurisdiction is covered when its chosen source has at least one parcel. Population
  is the 2020 Census count from the jurisdictions table; an unincorporated county area has none there, so it
  gets the county's 2020 population estimate less every other jurisdiction listed in that county (floored at
  zero, flagged `pop_estimated`).
- **Parcels outside any listed jurisdiction** (no `jurisdiction_geoid`, or one not in the jurisdictions table)
  are counted per county and reported as a data check, never dropped.
- **Precision.** Outputs are counts per jurisdiction or county; no parcel-level record leaves this module.
"""

from __future__ import annotations

import datetime as dt
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from lotline.config import CONFIG_DIR, all_states, load_state
from lotline.io import DataStore

UNASSIGNED = "unassigned"
LAND_USE_ORDER = [
    "SF_DETACHED",
    "DUPLEX",
    "TRI_QUAD",
    "MULTIFAMILY_5P",
    "CONDO_UNIT",
    "MOBILE_HOME",
    "VACANT_RESIDENTIAL",
    "AGRICULTURAL",
    "COMMERCIAL",
    "INDUSTRIAL",
    "INSTITUTIONAL",
    "OTHER",
    "UNKNOWN",
]
ACS_HOUSING_UNITS = "B25024_001"  # units in structure: total housing units
REFORM_THEMES_SHOWN = ("adu", "missing_middle", "fees", "parking")
COMPONENT_CHARS = 180


# --------------------------------------------------------------------------------------------- parcels
def parcel_counts_from_frame(df: pd.DataFrame, source: str) -> pd.DataFrame:
    """Counts of one source's parcels at each jurisdiction's latest vintage.

    `df` needs jurisdiction_geoid, county_geoid, vintage, land_use_std and optionally zoning_raw. Returns
    source, jkey, county_geoid, vintage, land_use_std, zoned (bool), n. `jkey` is the jurisdiction GEOID, or
    "unassigned:<county>" for parcels with none.
    """
    d = pd.DataFrame(
        {
            "county_geoid": df["county_geoid"].astype("string").fillna("?"),
            "jurisdiction_geoid": df["jurisdiction_geoid"].astype("string"),
            "vintage": pd.to_numeric(df["vintage"], errors="coerce").fillna(0).astype(int),
            "land_use_std": df["land_use_std"].astype("string").fillna("UNKNOWN"),
        }
    )
    if "zoning_raw" in df:
        z = df["zoning_raw"].astype("string")
        d["zoned"] = z.notna() & (z.str.strip() != "")
    else:
        d["zoned"] = False
    d["jkey"] = d["jurisdiction_geoid"].fillna(UNASSIGNED + ":" + d["county_geoid"])
    g = d.groupby(["jkey", "county_geoid", "vintage", "land_use_std", "zoned"], observed=True).size()
    g = g.rename("n").reset_index()
    latest = g.groupby("jkey")["vintage"].transform("max")
    out = g[g["vintage"] == latest].copy()
    out.insert(0, "source", source)
    return out.reset_index(drop=True)


def read_parcel_counts(path: Path) -> pd.DataFrame:
    """`parcel_counts_from_frame` on one processed parcels file, reading only the columns it needs."""
    names = pq.ParquetFile(path).schema_arrow.names
    cols = [
        c
        for c in ("jurisdiction_geoid", "county_geoid", "vintage", "land_use_std", "zoning_raw")
        if c in names
    ]
    strings = [c for c in cols if c != "vintage" and c != "zoning_raw"]
    table = pq.read_table(path, columns=cols, read_dictionary=strings)
    df = table.to_pandas()
    if "jurisdiction_geoid" not in df:
        df["jurisdiction_geoid"] = pd.NA
    return parcel_counts_from_frame(df, path.stem)


def choose_sources(counts: pd.DataFrame, preferences: dict[str, str]) -> pd.DataFrame:
    """One parcel source per jkey: the configured one if it has parcels there, else the largest.

    Returns jkey, source, vintage, n_total, sources (all sources with parcels, as 'name (vintage): n').
    """
    if counts.empty:
        return pd.DataFrame(columns=["jkey", "source", "vintage", "n_total", "sources"])
    per = counts.groupby(["jkey", "source"], as_index=False).agg(n=("n", "sum"), vintage=("vintage", "max"))
    rows = []
    for jkey, grp in per.groupby("jkey", sort=True):
        geoid = jkey.split(":", 1)[0] if not jkey.startswith(UNASSIGNED) else jkey
        pref = preferences.get(geoid, preferences.get("*"))
        has = grp[grp["n"] > 0]
        pick = has[has["source"] == pref]
        if pick.empty:
            pick = has.sort_values(["n", "source"], ascending=[False, True]).head(1)
        p = pick.iloc[0]
        listing = "; ".join(
            f"{r.source} ({r.vintage}): {r.n:,}" for r in grp.sort_values("source").itertuples()
        )
        rows.append(
            {
                "jkey": jkey,
                "source": p["source"],
                "vintage": int(p["vintage"]),
                "n_total": int(p["n"]),
                "sources": listing,
            }
        )
    return pd.DataFrame(rows)


def chosen_counts(counts: pd.DataFrame, chosen: pd.DataFrame) -> pd.DataFrame:
    """The rows of `counts` that belong to each jkey's chosen source."""
    if counts.empty:
        return counts
    keep = chosen[["jkey", "source"]]
    return counts.merge(keep, on=["jkey", "source"], how="inner")


# ------------------------------------------------------------------------------------------ population
def jurisdiction_population(jur: pd.DataFrame, county_pop: pd.Series | None) -> pd.DataFrame:
    """pop and pop_estimated per jurisdiction (rule in the module docstring)."""
    out = jur[["geoid", "county_geoid", "kind"]].copy()
    out["pop"] = pd.to_numeric(jur["pop_2020"], errors="coerce").astype("Float64")
    out["pop_estimated"] = False
    if county_pop is None:
        return out
    uninc = (out["kind"] == "county_unincorporated") & out["pop"].isna()
    others = out[~uninc].groupby("county_geoid")["pop"].sum(min_count=1)
    for i in out.index[uninc]:
        c = out.at[i, "county_geoid"]
        total = county_pop.get(c)
        if total is None or (isinstance(total, float) and math.isnan(total)):
            continue
        listed = others.get(c, 0)
        listed = 0 if pd.isna(listed) else listed
        out.at[i, "pop"] = max(0.0, float(total) - float(listed))
        out.at[i, "pop_estimated"] = True
    return out


# ------------------------------------------------------------------------------------------- eligible
def latest_eligible(eligible: pd.DataFrame | None) -> pd.DataFrame:
    """Per jurisdiction and theme, the latest year counted from a parcel roll (else the latest year)."""
    cols = [
        "jurisdiction_geoid",
        "theme",
        "year",
        "eligible_parcels",
        "denominator_source",
        "denominator_quality",
    ]
    if eligible is None or eligible.empty:
        return pd.DataFrame(columns=cols)
    e = eligible[cols].dropna(subset=["eligible_parcels"]).copy()
    e["rank"] = (e["denominator_source"] == "parcels").astype(int)
    e = e.sort_values(["jurisdiction_geoid", "theme", "rank", "year"])
    return e.groupby(["jurisdiction_geoid", "theme"], as_index=False).tail(1).drop(columns="rank")


# ------------------------------------------------------------------------------------------- reforms
def read_reforms(state: str, config_dir: Path = CONFIG_DIR) -> pd.DataFrame:
    """Coded reforms for a state: config/reforms/<st>.csv plus any <st>_*.csv in the same layout."""
    folder = config_dir / "reforms"
    frames = []
    for f in sorted(folder.glob(f"{state.lower()}*.csv")):
        if f.stem != state.lower() and not f.stem.startswith(state.lower() + "_"):
            continue
        df = pd.read_csv(f, dtype=str, keep_default_na=False)
        if {"reform_id", "theme", "jurisdiction_geoid"} <= set(df.columns):
            frames.append(df)
    if not frames:
        return pd.DataFrame(columns=["reform_id", "theme", "jurisdiction_geoid"])
    return pd.concat(frames, ignore_index=True)


def reform_events(reforms: pd.DataFrame, names: dict[str, str]) -> list[dict]:
    """Timeline rows: one per coded reform, dated by its effective date (else adoption date)."""
    out = []
    for r in reforms.itertuples(index=False):
        eff, adopt = getattr(r, "effective_date", ""), getattr(r, "adoption_date", "")
        date = eff or adopt
        comp = getattr(r, "component", "") or ""
        urls = (getattr(r, "source_url", "") or "").split(";")
        out.append(
            {
                "id": r.reform_id,
                "geoid": r.jurisdiction_geoid,
                "place": names.get(r.jurisdiction_geoid, r.jurisdiction_geoid),
                "theme": r.theme,
                "status": getattr(r, "status", ""),
                "date": date or None,
                "adopted": adopt or None,
                "effective": eff or None,
                "date_basis": "effective" if eff else ("adoption" if adopt else "none"),
                "coder_agreement": getattr(r, "coder_agreement", "") or "single_coder",
                "component": comp if len(comp) <= COMPONENT_CHARS else comp[: COMPONENT_CHARS - 1] + "…",
                "source_url": urls[0].strip() if urls and urls[0].strip() else None,
            }
        )
    return sorted(out, key=lambda e: (e["date"] or "9999", e["place"]))


# -------------------------------------------------------------------------------------------- growth
def acs_housing_units(acs: pd.DataFrame | None) -> pd.DataFrame:
    """geo, year (5-year end year), units: ACS total housing units for state and county geographies."""
    if acs is None or acs.empty:
        return pd.DataFrame(columns=["geo", "year", "units"])
    a = acs[(acs["variable"] == ACS_HOUSING_UNITS) & acs["geo"].str.match(r"^(state|county):")]
    return a.rename(columns={"end_year": "year", "estimate": "units"})[["geo", "year", "units"]]


def bps_units(bps: pd.DataFrame | None) -> pd.DataFrame:
    """county_geoid, year, units_1, units_2, units_3_4, units_5p, imputed_units (BPS, with imputation)."""
    cols = ["units_1", "units_2", "units_3_4", "units_5p"]
    if bps is None or bps.empty:
        return pd.DataFrame(columns=["county_geoid", "year", *cols, "imputed_units"])
    b = bps.copy()
    b["total"] = b[cols].sum(axis=1)
    b["imputed_units"] = b["total"].where(b["imputed"].fillna(False).astype(bool), 0)
    return b.groupby(["county_geoid", "year"], as_index=False)[[*cols, "imputed_units"]].sum()


def growth_series(fips: str, pop: pd.DataFrame, hu: pd.DataFrame, permits: pd.DataFrame) -> list[dict]:
    """Statewide yearly rows: population (PEP), housing units (ACS 5-year), units permitted (BPS) by size."""
    years = sorted(
        set(pop.loc[pop["geo"] == f"state:{fips}", "year"])
        | set(hu.loc[hu["geo"] == f"state:{fips}", "year"])
        | set(permits["year"])
    )
    p = pop[pop["geo"] == f"state:{fips}"].set_index("year")["population"]
    h = hu[hu["geo"] == f"state:{fips}"].set_index("year")["units"]
    b = permits.groupby("year")[["units_1", "units_2", "units_3_4", "units_5p", "imputed_units"]].sum()
    rows = []
    for y in years:
        if y < 2000:
            continue
        row = {"year": int(y), "population": _num(p.get(y)), "housing_units": _num(h.get(y))}
        if y in b.index:
            row |= {k: int(v) for k, v in b.loc[y].items()}
        rows.append(row)
    return rows


def county_growth(
    pop: pd.DataFrame, hu: pd.DataFrame, permits: pd.DataFrame, start: int, end: int
) -> pd.DataFrame:
    """Per county: population and housing units at start and end, units permitted from start+1 to end."""

    def at(df, col, year):
        s = df[(df["year"] == year) & df["geo"].str.startswith("county:")]
        return s.assign(county_geoid=s["geo"].str[7:]).set_index("county_geoid")[col]

    out = pd.DataFrame(
        {
            "pop_start": at(pop, "population", start),
            "pop_end": at(pop, "population", end),
            "hu_start": at(hu, "units", start),
            "hu_end": at(hu, "units", end),
        }
    )
    pm = permits[(permits["year"] > start) & (permits["year"] <= end)]
    out["permits"] = (
        pm.groupby("county_geoid")[["units_1", "units_2", "units_3_4", "units_5p"]].sum().sum(axis=1)
    )
    return out


# -------------------------------------------------------------------------------------------- helpers
def lots_estimated(js: pd.DataFrame) -> int:
    """Jurisdictions whose eligible ADU lots come from the Census fallback (`acs_sf_fallback`, D-017), not a
    parcel roll. The map shades a county with no parcels but such estimates as "estimated", not "no data"."""
    if "eligible_adu_basis" not in js:
        return 0
    return int((js["eligible_adu_basis"] == "acs_sf_fallback").sum())


def _num(v):
    if v is None:
        return None
    try:
        if pd.isna(v):
            return None
    except (TypeError, ValueError):
        pass
    f = float(v)
    return int(f) if f.is_integer() else round(f, 4)


def _records(df: pd.DataFrame) -> list[dict]:
    recs = df.replace({np.nan: None}).to_dict("records")
    return [
        {
            k: _num(v) if isinstance(v, (int, float, np.number)) and not isinstance(v, bool) else v
            for k, v in r.items()
        }
        for r in recs
    ]


def _land_use_dict(df: pd.DataFrame) -> dict[str, int]:
    s = df.groupby("land_use_std")["n"].sum()
    return {k: int(s[k]) for k in LAND_USE_ORDER if k in s.index and s[k]} | {
        k: int(v) for k, v in s.items() if k not in LAND_USE_ORDER and v
    }


def jurisdiction_points(
    state: str, store: DataStore, township_permits: bool
) -> dict[str, tuple[float, float]]:
    """A map point (lon, lat) per place and township: centroid of its largest ring, from cached TIGERweb."""
    from lotline.adapters.national import tiger_boundaries

    fips = load_state(state).fips
    pts: dict[str, tuple[float, float]] = {}
    levels = ["place", "cousub"] if township_permits else ["place"]
    for level in levels:
        if not (store.raw(tiger_boundaries.SOURCE, tiger_boundaries.VINTAGE) / f"{level}_{fips}").exists():
            continue
        polys = tiger_boundaries.load_polygons(state, store, level)
        for r in polys.itertuples(index=False):
            best, best_area = None, 0.0
            for ring in r.rings:
                a = np.asarray(ring, dtype=float).reshape(-1, 2)
                if len(a) < 3:
                    continue
                x, y = a[:, 0], a[:, 1]
                cross = x * np.roll(y, -1) - np.roll(x, -1) * y
                area = cross.sum() / 2
                if abs(area) > best_area and area != 0:
                    cx = ((x + np.roll(x, -1)) * cross).sum() / (6 * area)
                    cy = ((y + np.roll(y, -1)) * cross).sum() / (6 * area)
                    best, best_area = (round(float(cx), 3), round(float(cy), 3)), abs(area)
            if best:
                pts[r.geoid] = best
    return pts


# ------------------------------------------------------------------------------------------ per state
def summarize_state(
    state: str,
    store: DataStore,
    *,
    pep: pd.DataFrame | None = None,
    config_dir: Path = CONFIG_DIR,
    points: bool = True,
) -> dict | None:
    """Everything the dashboard shows for one state, or None if its jurisdictions table isn't built."""
    cfg = load_state(state, config_dir)
    jur = store.read(state, "jurisdictions")
    if jur is None:
        return None
    jur = jur.copy()
    fips = cfg.fips

    # parcels
    files = sorted(store.processed(state, "parcels").glob("*.parquet"))
    counts = (
        pd.concat([read_parcel_counts(f) for f in files], ignore_index=True)
        if files
        else pd.DataFrame(columns=["source", "jkey", "county_geoid", "vintage", "land_use_std", "zoned", "n"])
    )
    chosen = choose_sources(counts, cfg.parcel_sources)
    used = chosen_counts(counts, chosen)

    known = set(jur["geoid"])
    used = used.assign(listed=used["jkey"].isin(known))
    by_j = used[used["listed"]].groupby("jkey")
    j_parcels = by_j["n"].sum()
    j_zoned = used[used["listed"] & used["zoned"]].groupby("jkey")["n"].sum()
    j_unknown = used[used["listed"] & (used["land_use_std"] == "UNKNOWN")].groupby("jkey")["n"].sum()
    j_sf = used[used["listed"] & (used["land_use_std"] == "SF_DETACHED")].groupby("jkey")["n"].sum()
    ch = chosen.set_index("jkey")

    # population
    county_pop = None
    if pep is not None and not pep.empty:
        cp = pep[(pep["year"] == 2020) & pep["geo"].str.startswith(f"county:{fips}")]
        county_pop = cp.assign(c=cp["geo"].str[7:]).set_index("c")["population"].astype(float)
    pop = jurisdiction_population(jur, county_pop).set_index("geoid")

    # eligible and reforms
    elig = latest_eligible(store.read(state, "eligible_parcels"))
    reforms = read_reforms(state, config_dir)
    county_names = _county_names(jur)
    if pep is not None and "name" in pep:
        pn = pep[pep["geo"].str.startswith(f"county:{fips}")].drop_duplicates("geo", keep="last")
        county_names |= dict(zip(pn["geo"].str[7:], pn["name"], strict=True))
    names = dict(zip(jur["geoid"], jur["name"], strict=True)) | county_names | {fips: cfg.name}
    events = reform_events(reforms, names)
    ref_by_j = (
        reforms.groupby(["jurisdiction_geoid", "theme"]).size() if len(reforms) else pd.Series(dtype=int)
    )

    elig_ix = {(r["jurisdiction_geoid"], r["theme"]): r for r in elig.to_dict("records")}
    ref_ix: dict[str, dict[str, int]] = {}
    for (gg, t), n in ref_by_j.items():
        ref_ix.setdefault(gg, {})[t] = int(n)

    pts = {}
    if points:
        try:
            pts = jurisdiction_points(state, store, cfg.township_permits)
        except Exception:  # noqa: BLE001 - points are decoration; never fail the summary for them
            pts = {}

    jrows = []
    for r in jur.itertuples(index=False):
        g = r.geoid
        row = {
            "geoid": g,
            "name": r.name,
            "kind": r.kind,
            "county": r.county_geoid,
            "pop": _num(pop.at[g, "pop"]) if g in pop.index else None,
            "pop_estimated": bool(pop.at[g, "pop_estimated"]) if g in pop.index else False,
            "tier": _num(r.data_tier),
            "parcels": int(j_parcels.get(g, 0)),
            "zoned": int(j_zoned.get(g, 0)),
            "unknown_use": int(j_unknown.get(g, 0)),
            "sf_detached": int(j_sf.get(g, 0)),
            "source": ch.at[g, "source"] if g in ch.index else None,
            "vintage": int(ch.at[g, "vintage"]) if g in ch.index else None,
            "sources": ch.at[g, "sources"] if g in ch.index else None,
            "point": pts.get(g),
        }
        for theme in ("adu", "missing_middle"):
            e = elig_ix.get((g, theme))
            row[f"eligible_{theme}"] = _num(e["eligible_parcels"]) if e is not None else None
            row[f"eligible_{theme}_basis"] = e["denominator_source"] if e is not None else None
            row[f"eligible_{theme}_quality"] = e["denominator_quality"] if e is not None else None
        row["reforms"] = ref_ix.get(g, {})
        jrows.append(row)
    jdf = pd.DataFrame(jrows)

    # growth
    pep_s = pep if pep is not None else pd.DataFrame(columns=["geo", "year", "population"])
    hu = acs_housing_units(store.read(state, "acs_geo_year"))
    permits = bps_units(store.read(state, "bps_place_year"))
    series = growth_series(fips, pep_s, hu, permits)
    end = int(min(hu["year"].max(), pep_s["year"].max())) if len(hu) and len(pep_s) else None
    start = 2010
    cg = county_growth(pep_s, hu, permits, start, end) if end else pd.DataFrame()

    # counties
    crow = []
    unassigned = used[~used["listed"]].groupby("county_geoid")["n"].sum()
    all_counties = sorted(set(jur["county_geoid"].dropna()) | set(unassigned.index) - {"?"})
    for c in all_counties:
        if not str(c).startswith(fips):
            continue
        js = jdf[jdf["county"] == c]
        cu = used[used["county_geoid"] == c]
        covered = js[js["parcels"] > 0]
        cs = cu.groupby("source").agg(n=("n", "sum"), vintage=("vintage", "max"))
        row = {
            "geoid": c,
            "name": county_names.get(c, c),
            "jurisdictions": int(len(js)),
            "jurisdictions_covered": int(len(covered)),
            "pop": _num(js["pop"].sum(min_count=1)),
            "pop_covered": _num(covered["pop"].sum(min_count=1)) or 0,
            "parcels": int(cu["n"].sum()),
            "parcels_unassigned": int(unassigned.get(c, 0)),
            "zoned": int(cu.loc[cu["zoned"], "n"].sum()),
            "land_use": _land_use_dict(cu) if len(cu) else {},
            "sources": {s: {"n": int(v.n), "vintage": int(v.vintage)} for s, v in cs.iterrows()},
            "reforms": int(sum(sum(j.values()) for j in js["reforms"])),
            "eligible_adu": _num(js["eligible_adu"].sum(min_count=1)),
            "eligible_missing_middle": _num(js["eligible_missing_middle"].sum(min_count=1)),
            "tier_best": _num(js["tier"].min()) if len(js) else None,
            "lots_estimated": lots_estimated(js),
        }
        if len(cg) and c in cg.index:
            row |= {k: _num(v) for k, v in cg.loc[c].items()}
        crow.append(row)
    cdf = pd.DataFrame(crow)

    # sources table (every parcel source, whether or not it was chosen anywhere)
    src_rows = []
    for s, grp in counts.groupby("source"):
        chosen_n = int(used.loc[used["source"] == s, "n"].sum())
        src_rows.append(
            {
                "source": s,
                "parcels_latest": int(grp["n"].sum()),
                "parcels_used": chosen_n,
                "counties": int(grp["county_geoid"].nunique()),
                "jurisdictions": int(grp.loc[grp["jkey"].isin(known), "jkey"].nunique()),
                "vintages": sorted({int(v) for v in grp["vintage"]}),
                "zoned_share": _num(round(grp.loc[grp["zoned"], "n"].sum() / grp["n"].sum(), 4))
                if grp["n"].sum()
                else None,
            }
        )
    configured = [s.name for s in cfg.sources]

    totals = _state_totals(jdf, used, elig, reforms, permits)
    checks = data_checks(jdf, used, reforms, counts, known, permits)
    census_counties = set(county_names) - set(jdf["county"].dropna())
    totals["counties_census"] = len(set(county_names) | set(jdf["county"].dropna()))
    if pep is not None:
        missing = sorted(census_counties)
        checks.insert(
            0,
            {
                "level": "warn" if missing else "ok",
                "title": "Counties with no jurisdiction in the table",
                "value": str(len(missing)),
                "detail": "Census counties with no permit-issuing jurisdiction listed (no BPS row): nothing "
                "there is counted: no parcels, no population.",
                "items": [county_names[c] for c in missing][:60],
            },
        )
    return {
        "state": state,
        "name": cfg.name,
        "fips": fips,
        "township_permits": cfg.township_permits,
        "growth_window": [start, end] if end else None,
        "totals": totals,
        "land_use": _land_use_dict(used) if len(used) else {},
        "parcel_sources": src_rows,
        "configured_sources": configured,
        "counties": _records(cdf),
        "jurisdictions": _records(jdf),
        "reforms": events,
        "growth": series,
        "checks": checks,
    }


def _county_names(jur: pd.DataFrame) -> dict[str, str]:
    u = jur[jur["kind"] == "county_unincorporated"]
    return {g: n.replace(" Unincorporated Area", "") for g, n in zip(u["geoid"], u["name"], strict=True)}


def _state_totals(jdf, used, elig, reforms, permits) -> dict:
    pop_total = float(jdf["pop"].sum())
    covered = jdf[jdf["parcels"] > 0]
    themes = reforms["theme"].value_counts().to_dict() if len(reforms) else {}
    agree = (
        reforms["coder_agreement"].replace("", "single_coder").value_counts().to_dict()
        if len(reforms)
        else {}
    )
    return {
        "population": _num(pop_total),
        "population_covered": _num(float(covered["pop"].sum())),
        "population_covered_share": _num(round(float(covered["pop"].sum()) / pop_total, 4))
        if pop_total
        else None,
        "jurisdictions": int(len(jdf)),
        "jurisdictions_covered": int(len(covered)),
        "counties": int(jdf["county"].nunique()),
        "counties_with_parcels": int(used.loc[used["n"] > 0, "county_geoid"].nunique()) if len(used) else 0,
        "parcels": int(used["n"].sum()) if len(used) else 0,
        "parcels_zoned": int(used.loc[used["zoned"], "n"].sum()) if len(used) else 0,
        "eligible_adu": _num(jdf["eligible_adu"].sum(min_count=1)),
        "eligible_missing_middle": _num(jdf["eligible_missing_middle"].sum(min_count=1)),
        "tiers": {str(int(k)): int(v) for k, v in jdf["tier"].value_counts().sort_index().items()},
        "reforms": int(len(reforms)),
        "reforms_by_theme": {k: int(v) for k, v in themes.items()},
        "coder_agreement": {k: int(v) for k, v in agree.items()},
        "reform_places": int(reforms["jurisdiction_geoid"].nunique()) if len(reforms) else 0,
        "permit_years": [int(permits["year"].min()), int(permits["year"].max())] if len(permits) else None,
    }


def data_checks(jdf, used, reforms, counts, known, permits) -> list[dict]:
    """Plain-language data checks: each with a level (ok / note / warn), a count and what it means."""
    out = []

    def add(level, title, value, detail, items=None):
        out.append({"level": level, "title": title, "value": value, "detail": detail, "items": items or []})

    total = int(used["n"].sum()) if len(used) else 0
    unassigned = int(used.loc[~used["listed"], "n"].sum()) if len(used) else 0
    if total:
        share = unassigned / total
        add(
            "warn" if share > 0.02 else "ok",
            "Parcels outside any listed jurisdiction",
            f"{share:.1%}",
            f"{unassigned:,} of {total:,} parcels have no jurisdiction or one missing from the table.",
        )
        unk = int(used.loc[used["land_use_std"] == "UNKNOWN", "n"].sum())
        add(
            "warn" if unk / total > 0.05 else "ok",
            "Parcels with unknown land use",
            f"{unk / total:.1%}",
            f"{unk:,} parcels could not be mapped to a standard land-use class by the crosswalks.",
        )
        z = int(used.loc[used["zoned"], "n"].sum())
        add(
            "note",
            "Parcels with a zoning code attached",
            f"{z / total:.1%}",
            "Where zoning is unknown, the missing-middle rule assumes single-family-only zoning "
            "(eligible-parcel rule 1.1), so a low share means more of that count rests on an assumption.",
        )
    if len(reforms):
        rj = set(reforms["jurisdiction_geoid"])
        uncovered = sorted(
            g for g in rj if g in known and int(jdf.loc[jdf["geoid"] == g, "parcels"].sum()) == 0
        )
        names = dict(zip(jdf["geoid"], jdf["name"], strict=True))
        add(
            "warn" if uncovered else "ok",
            "Reform places with no parcels",
            str(len(uncovered)),
            "Jurisdictions with a coded reform but no parcel roll; their eligible counts fall back to ACS.",
            [names.get(g, g) for g in uncovered][:40],
        )
        no_eff = reforms[reforms.get("effective_date", pd.Series("", index=reforms.index)) == ""]
        add(
            "note" if len(no_eff) else "ok",
            "Reforms dated by adoption, not effective date",
            str(len(no_eff)),
            "No effective date was found; the timeline uses the adoption date.",
        )
        single = int((reforms["coder_agreement"].replace("", "single_coder") == "single_coder").sum())
        add(
            "note",
            "Reforms checked by a second coder",
            f"{1 - single / len(reforms):.0%}",
            f"{len(reforms) - single} of {len(reforms)} reforms were double-coded (agree or adjudicated).",
        )
        unknown_geo = sorted(g for g in rj if g not in known and len(g) != 2)
        if unknown_geo:
            add(
                "warn",
                "Reforms in jurisdictions not in the table",
                str(len(unknown_geo)),
                "Reform GEOIDs that match no row of the jurisdictions table.",
                unknown_geo[:40],
            )
    if len(permits):
        tot = permits[["units_1", "units_2", "units_3_4", "units_5p"]].sum().sum()
        imp = permits["imputed_units"].sum()
        add(
            "note",
            "Permit units imputed by Census",
            f"{imp / tot:.1%}" if tot else "0%",
            "Share of BPS units from jurisdiction-years Census imputed (fewer than 12 months reported).",
        )
    stale = counts.groupby("source")["vintage"].max() if len(counts) else pd.Series(dtype=int)
    old = [f"{s} ({v})" for s, v in stale.items() if v and v < dt.date.today().year - 3]
    if old:
        add("note", "Parcel sources older than 3 years", str(len(old)), "Latest roll year per source.", old)
    return out


# ------------------------------------------------------------------------------------------ all states
def summarize(
    store: DataStore | None = None,
    states: list[str] | None = None,
    *,
    config_dir: Path = CONFIG_DIR,
    fetch_missing: bool = False,
    points: bool = True,
) -> dict:
    """Summaries for every configured state with processed data (or the ones named)."""
    from lotline.adapters.national import pep as pep_adapter

    store = store or DataStore()
    states = [s.upper() for s in (states or all_states(config_dir))]
    fips = [load_state(s, config_dir).fips for s in states]
    pep = None
    if fetch_missing or pep_adapter.cached(store):
        pep = pep_adapter.load(store, state_fips=fips)
    out = []
    for s in states:
        summary = summarize_state(s, store, pep=pep, config_dir=config_dir, points=points)
        if summary is not None:
            out.append(summary)
    return {
        "generated": dt.datetime.now(dt.UTC).strftime("%Y-%m-%d %H:%M UTC"),
        "population_source": "Census PEP vintages 2020 and 2025" if pep is not None else None,
        "states": out,
    }
