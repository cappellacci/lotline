"""Build the `jurisdictions` table: every place that issues building permits in a state.

The universe is the set of GEOIDs in the state's BPS table (places, townships, and counties for their
unincorporated areas), so permits, ACS and FHFA can all be joined through one key. Names and 2020
population come from the 2020 Census (P.L. 94-171); a jurisdiction that no longer existed in 2020 keeps its
latest BPS name and a missing population. Unincorporated county areas also get no population (see build).

`data_tier` is 3 (national data only: BPS, ACS, FHFA) unless the loaded parcels show better data: tier 2 with
land use, tier 1 with land use and year built (`tiers_from_parcels`, D-016). `data_tiers: {geoid: tier}` in
`config/states/<st>.yaml` overrides the data-driven tier.
"""

from __future__ import annotations

import warnings
from collections.abc import Iterable
from pathlib import Path

import pandas as pd

from lotline.adapters.national import bps, cbsa, decennial, geoparts
from lotline.config import load_params, load_state
from lotline.io import DataStore
from lotline.schemas import validate

SOURCE = "jurisdictions"
READS = ("bps_place_year",)  # `lotline fetch` order (registry.fetch_order)
RERUN_AFTER = ("parcels",)  # data tiers come from the parcels, which need this list first
MANIFEST_SOURCES = [
    bps.SOURCE,
    decennial.SOURCE,
    cbsa.SOURCE,
]  # what this build reads (for `lotline provenance --check`)
DEFAULT_TIER = 3


def kind_of(geoid: str, township_permits: bool) -> str:
    return {5: "county_unincorporated", 7: "place", 10: "township" if township_permits else "other"}.get(
        len(geoid), "other"
    )


def build(
    state: str,
    bps_table: pd.DataFrame,
    census: pd.DataFrame,
    cbsas: pd.DataFrame | None = None,
    local_geoids: Iterable[str] = (),
    *,
    place_counties: dict[str, str] | None = None,
    parcel_tiers: dict[str, int] | None = None,
    main_counties: dict[str, str] | None = None,
) -> pd.DataFrame:
    """Combine one state's BPS place-years with 2020 Census names and populations, and (if given) the
    OMB metro/micro area of each jurisdiction's county.

    `local_geoids` are jurisdictions that a state's own permit source reports but BPS doesn't (e.g. Met
    Council townships whose permits BPS files under the county). They're added with `in_bps = False`, named
    from the 2020 Census; a GEOID the Census doesn't know is skipped with a warning, never invented.
    `place_counties` gives such a place's county (from the Census place-by-county file).
    `main_counties` (place GEOID -> county, `geoparts.main_county`) settles a place that spans counties: it is
    filed under the county holding most of its 2020 homes, in this table and in the baseline panel (task 5
    rule 5). Without it, a BPS place keeps the county of its latest BPS row.
    """
    cfg = load_state(state)
    latest = (
        bps_table.dropna(subset=["geoid"])
        .sort_values("year")
        .groupby("geoid")
        .agg(name=("name", "last"), bps_id=("bps_id", "last"), county_geoid=("county_geoid", "last"))
        .reset_index()
    )
    # County remainders get no population here; `load` fills it (`remainder_population`, task 5 rule 6).
    pops = census[census["level"] != "county"].drop_duplicates("geoid").set_index("geoid")
    df = latest.assign(
        state=state,
        kind=[kind_of(g, cfg.township_permits) for g in latest["geoid"]],
        census_name=latest["geoid"].map(pops["census_name"]),
        pop_2020=latest["geoid"].map(pops["pop_2020"]).astype("Int64"),
    )
    df["in_bps"] = True
    df = pd.concat(
        [df, _local_rows(state, df, census, local_geoids, place_counties or {})], ignore_index=True
    )
    if main_counties:
        df["county_geoid"] = df["geoid"].map(main_counties).fillna(df["county_geoid"])
    df["name"] = df["census_name"].fillna(df["name"])
    tiers = pd.Series({**(parcel_tiers or {}), **cfg.data_tiers}, dtype="Int64")  # config overrides data
    df["data_tier"] = df["geoid"].map(tiers).fillna(DEFAULT_TIER).astype("Int64")
    if cbsas is not None:
        by_county = cbsas.set_index("county_geoid")
        df["cbsa_code"] = df["county_geoid"].map(by_county["cbsa_code"])
        df["cbsa_type"] = df["county_geoid"].map(by_county["cbsa_type"])
    return validate(df, "jurisdictions")


def _local_rows(
    state: str,
    bps_rows: pd.DataFrame,
    census: pd.DataFrame,
    geoids: Iterable[str],
    place_counties: dict[str, str],
) -> pd.DataFrame:
    cfg = load_state(state)
    known = census[census["level"] != "county"].drop_duplicates("geoid").set_index("geoid")
    rows, skipped = [], []
    for g in sorted(set(geoids) - set(bps_rows["geoid"])):
        if g not in known.index or len(g) not in (7, 10):
            skipped.append(g)
            continue
        county = g[:5] if len(g) == 10 else place_counties.get(g)
        rows.append(
            {
                "geoid": g,
                "name": known.loc[g, "census_name"],
                "bps_id": None,
                "county_geoid": county,
                "state": state,
                "kind": kind_of(g, cfg.township_permits),
                "census_name": known.loc[g, "census_name"],
                "pop_2020": known.loc[g, "pop_2020"],
                "in_bps": False,
            }
        )
    if skipped:
        warnings.warn(
            f"{state}: {len(skipped)} local permit GEOIDs unknown to the 2020 Census skipped: {skipped[:10]}",
            stacklevel=2,
        )
    return pd.DataFrame(
        rows,
        columns=[
            "geoid",
            "name",
            "bps_id",
            "county_geoid",
            "state",
            "kind",
            "census_name",
            "pop_2020",
            "in_bps",
        ],
    )


def remainder_population(
    juris: pd.DataFrame, census: pd.DataFrame, county_shares: pd.DataFrame, township_shares: pd.DataFrame
) -> pd.Series:
    """2020 population of each county remainder (task 5 rule 6, Ben 2026-11-17): the county's 2020 population
    minus every BPS-universe place in it (a place spanning counties split by its 2020 housing-unit shares) and
    every BPS-universe township net of the places inside it. The same subtraction as the remainder's eligible
    homes (`eligible.allocate_homes`), so a remainder's population and its homes describe the same area.
    Below 0 (never expected with census counts) is set to 0. Index: county GEOID.

    By hand: county 100,000; place A 30,000 (all in it); place B 20,000 with 25% of its homes here; township T
    10,000 holding dependent place C 4,000 → 100,000 − 30,000 − 5,000 − (10,000 − 4,000) − 4,000 = 55,000.
    """
    from lotline.build.eligible import allocate_homes

    pops = census.drop_duplicates("geoid").set_index("geoid")
    prefix = {"place": "place:", "cousub": "cousub:", "county": "county:"}
    as_acs = pd.DataFrame(
        {
            "geo": pops["level"].map(prefix) + pops.index,
            "end_year": 2020,
            "estimate": pd.to_numeric(pops["pop_2020"], errors="coerce").astype(float),
        }
    ).dropna(subset=["geo"])
    alloc = allocate_homes(as_acs, juris, county_shares, township_shares)
    counties = juris.loc[juris["kind"] == "county_unincorporated", "geoid"]
    got = alloc.set_index("jurisdiction_geoid")["homes"]
    return got.reindex(counties).round().astype("Int64").rename("pop_2020")


def tiers_from_parcels(parcels: pd.DataFrame | None, params: dict | None = None) -> dict[str, int]:
    """Data tier per jurisdiction from its latest parcel roll (D-016; thresholds in config/params/tiers.yaml).

    Tier 1: land use known for at least `tier2_min_land_use_share` of parcels and year built known for at
    least `tier1_min_year_built_share` of built (non-vacant) parcels; tier 2: land use only; tier 3 otherwise.
    """
    if parcels is None or parcels.empty:
        return {}
    p = params or load_params("tiers")
    latest = parcels[parcels["vintage"] == parcels.groupby("jurisdiction_geoid")["vintage"].transform("max")]
    built = latest["land_use_std"] != "VACANT_RESIDENTIAL"
    has_year = (
        latest["year_built"].notna() if "year_built" in latest else pd.Series(False, index=latest.index)
    )
    stats = (
        pd.DataFrame(
            {
                "geoid": latest["jurisdiction_geoid"].astype(str),
                "land_use": latest["land_use_std"] != "UNKNOWN",
                "year": has_year.where(built),
            }
        )
        .groupby("geoid")
        .agg(land_use=("land_use", "mean"), year=("year", "mean"))
    )
    has_land_use = stats["land_use"] >= p["tier2_min_land_use_share"].value
    has_year_built = stats["year"].fillna(0) >= p["tier1_min_year_built_share"].value
    tier = pd.Series(3, index=stats.index).mask(has_land_use, 2).mask(has_land_use & has_year_built, 1)
    return {g: int(t) for g, t in tier.items()}


def local_geoids(state: str, store: DataStore | None = None) -> set[str]:
    """Jurisdictions outside the Census permit survey: the state file's `local_jurisdictions`, plus every
    holdout place.

    A holdout place is always its own jurisdiction, even where BPS files it under a county (Charlotte):
    otherwise an adapter that keeps only known GEOIDs would relabel its rows as the county's (#123).
    Reads no permit or parcel table, so the list never depends on adapter output and needs no rerun
    (WS-SCALE straight-line build; `store` is unused and kept for callers). `unlisted` finds GEOIDs the
    state's data uses that are missing from the list.
    """
    cfg = load_state(state)
    return set(cfg.local_jurisdictions) | {h.geoid for h in cfg.holdouts if not h.statewide}


def unlisted(state: str, store: DataStore) -> pd.DataFrame:
    """GEOIDs (7- or 10-digit) the state's permit and parcel tables use that are not in its jurisdictions
    table: candidates for `local_jurisdictions`. Columns: geoid, table, rows."""
    juris = store.read(state, "jurisdictions")
    known = set(juris["geoid"].astype(str)) if juris is not None else set()
    out = []
    for table in ("permits", "parcels"):
        rows = store.read(state, table)
        if rows is None:
            continue
        g = rows["jurisdiction_geoid"].dropna().astype(str)
        counts = g[g.str.len().isin([7, 10]) & ~g.isin(known)].value_counts()
        out += [{"geoid": k, "table": table, "rows": int(v)} for k, v in counts.items()]
    return pd.DataFrame(out, columns=["geoid", "table", "rows"])


# Config lists where a GEOID the jurisdictions table lacks matches nothing: an error. Reform rows are only
# listed, because a place Census files under a county row is blended into that row (D-021, `county_mix`)
# and a state's reform table may code places outside its modeled set.
CONFIG_GEOID_LISTS = ("fees", "local_jurisdictions", "data_tiers", "train_until", "holdouts")


def config_orphans(state: str, store: DataStore, config_dir: Path | None = None) -> pd.DataFrame:
    """GEOIDs (7- or 10-digit) named in config (config/reforms, config/fees, the state file's lists) that the
    built jurisdictions table lacks, e.g. after a Census re-key of the building-permit places. Columns: geoid,
    where, blocking (True for every list but reforms). Empty when the jurisdictions table isn't built."""
    from lotline.config import CONFIG_DIR, load_fees

    juris = store.read(state, "jurisdictions")
    if juris is None:
        return pd.DataFrame(columns=["geoid", "where", "blocking"])
    folder = config_dir or CONFIG_DIR
    known = set(juris["geoid"].astype(str))
    cfg = load_state(state, folder)
    named: dict[str, set[str]] = {}
    reforms = folder / "reforms" / f"{state.lower()}.csv"
    if reforms.exists():
        named["reforms"] = set(
            pd.read_csv(reforms, dtype=str, usecols=["jurisdiction_geoid"])["jurisdiction_geoid"]
        )
    fees = load_fees(state, folder)
    if fees is not None:
        named["fees"] = set(fees["jurisdiction_geoid"].astype(str))
    named["local_jurisdictions"] = set(cfg.local_jurisdictions)
    named["data_tiers"] = set(cfg.data_tiers)
    named["train_until"] = set(cfg.train_until)
    named["holdouts"] = {h.geoid for h in cfg.holdouts if not h.statewide}
    out = [
        {"geoid": g, "where": where, "blocking": where in CONFIG_GEOID_LISTS}
        for where, geoids in named.items()
        for g in sorted(x for x in geoids if isinstance(x, str) and len(x) in (7, 10) and x not in known)
    ]
    return pd.DataFrame(out, columns=["geoid", "where", "blocking"])


def load(state: str, store: DataStore, *, refresh: bool = False) -> pd.DataFrame:
    bps_table = store.read(state, "bps_place_year")
    if bps_table is None:
        bps_table = bps.load(state, store, refresh=refresh)
    fips = load_state(state).fips
    census = decennial.load(fips, state, store, refresh=refresh)
    local = local_geoids(state, store)
    pbc = geoparts.place_by_county(fips, store, refresh) if local else None
    place_counties = (
        dict(zip(pbc["place_geoid"], pbc["county_geoid"], strict=True)) if pbc is not None else {}
    )
    tiers = tiers_from_parcels(store.read(state, "parcels"))
    places = sorted({g for g in [*bps_table["geoid"].dropna(), *local] if len(g) == 7})
    main = geoparts.main_county(fips, places, store, refresh)
    out = build(
        state,
        bps_table,
        census,
        cbsa.load(store, refresh=refresh),
        local,
        place_counties=place_counties,
        parcel_tiers=tiers,
        main_counties=main,
    )
    # task 5 rule 6: county remainders get their 2020 population, so they land in the right size band
    in_list = out.loc[out["kind"] == "place", "geoid"].tolist()
    townships = out.loc[out["kind"] == "township", "geoid"].tolist()
    c_shares = geoparts.county_shares(fips, in_list, store, refresh)
    t_shares = geoparts.township_shares(fips, in_list, townships, store, refresh)
    rem = remainder_population(out, census, c_shares, t_shares)
    out["pop_2020"] = out["geoid"].map(rem).fillna(out["pop_2020"]).astype("Int64")
    return validate(out, "jurisdictions")
