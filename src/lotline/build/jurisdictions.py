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

import pandas as pd

from lotline.adapters.national import bps, cbsa, decennial, geoparts
from lotline.config import load_params, load_state
from lotline.io import DataStore
from lotline.schemas import validate

SOURCE = "jurisdictions"
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
    parcel_tiers: dict[str, int] | None = None,
    place_counties: dict[str, str] | None = None,
) -> pd.DataFrame:
    """Combine one state's BPS place-years with 2020 Census names and populations, and (if given) the
    OMB metro/micro area of each jurisdiction's county.

    `local_geoids` are jurisdictions that a state's own permit source reports but BPS doesn't (e.g. Met
    Council townships whose permits BPS files under the county). They're added with `in_bps = False`, named
    from the 2020 Census; a GEOID the Census doesn't know is skipped with a warning, never invented.
    `place_counties` gives such a place's county (from the Census place-by-county file).
    """
    cfg = load_state(state)
    latest = (
        bps_table.dropna(subset=["geoid"])
        .sort_values("year")
        .groupby("geoid")
        .agg(name=("name", "last"), bps_id=("bps_id", "last"), county_geoid=("county_geoid", "last"))
        .reset_index()
    )
    # Unincorporated areas get no population: the county total would overstate them, and places that
    # straddle county lines make "county minus its places" unreliable from these files.
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


def local_geoids(state: str, store: DataStore) -> set[str]:
    """Jurisdictions a state's own sources report (permits and parcels), plus every holdout place.

    A holdout place is always its own jurisdiction, even where BPS files it under a county (Charlotte):
    otherwise an adapter that keeps only known GEOIDs would relabel its rows as the county's (#123).
    Rerun `lotline fetch --source jurisdictions` after adding a permit or parcel source.
    """
    local: set[str] = set()
    for table in ("permits", "parcels"):
        rows = store.read(state, table)
        if rows is not None:
            local |= set(rows["jurisdiction_geoid"].dropna().astype(str))
    return local | {h.geoid for h in load_state(state).holdouts}


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
    return build(state, bps_table, census, cbsa.load(store, refresh=refresh), local, place_counties, tiers)
