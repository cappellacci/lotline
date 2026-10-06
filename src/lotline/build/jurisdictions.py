"""Build the `jurisdictions` table: every place that issues building permits in a state.

The universe is the set of GEOIDs in the state's BPS table (places, townships, and counties for their
unincorporated areas), so permits, ACS and FHFA can all be joined through one key. Names and 2020
population come from the 2020 Census (P.L. 94-171); a jurisdiction that no longer existed in 2020 keeps its
latest BPS name and a missing population. Unincorporated county areas also get no population (see build).

`data_tier` defaults to 3 (national data only: BPS, ACS, FHFA). State workstreams raise it in
`config/states/<st>.yaml` (`data_tiers: {geoid: tier}`) as local parcel and permit data are added.
"""

from __future__ import annotations

import pandas as pd

from lotline.adapters.national import bps, decennial
from lotline.config import load_state
from lotline.io import DataStore
from lotline.schemas import validate

SOURCE = "jurisdictions"
DEFAULT_TIER = 3


def kind_of(geoid: str, township_permits: bool) -> str:
    return {5: "county_unincorporated", 7: "place", 10: "township" if township_permits else "other"}.get(
        len(geoid), "other"
    )


def build(state: str, bps_table: pd.DataFrame, census: pd.DataFrame) -> pd.DataFrame:
    """Combine one state's BPS place-years with 2020 Census names and populations."""
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
    df["name"] = df["census_name"].fillna(df["name"])
    df["data_tier"] = df["geoid"].map(cfg.data_tiers).fillna(DEFAULT_TIER).astype("Int64")
    return validate(df, "jurisdictions")


def load(state: str, store: DataStore, *, refresh: bool = False) -> pd.DataFrame:
    path = store.processed(state, "bps_place_year", "bps")
    bps_table = pd.read_parquet(path) if path.exists() else bps.load(state, store, refresh=refresh)
    return build(state, bps_table, decennial.load(load_state(state).fips, state, store, refresh=refresh))
