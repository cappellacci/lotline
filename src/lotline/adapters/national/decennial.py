"""Census 2020 decennial redistricting counts (P.L. 94-171): official names and 2020 population.

Source: Census Data API, https://api.census.gov/data/2020/dec/pl (variable P1_001N, total population).
Public domain (U.S. Government work). Uses CENSUS_API_KEY like the ACS adapter.

Returns one row per county, place and county subdivision in a state, keyed by GEOID: county SS+CCC,
place SS+PPPPP, county subdivision SS+CCC+MMMMM.
"""

from __future__ import annotations

import pandas as pd

from lotline.adapters.national.acs import _fetch_json, api_key
from lotline.io import DataStore

SOURCE = "census_acs5"  # shares the Census API fetch path and key handling
URL = "https://api.census.gov/data/2020/dec/pl"
QUERIES = {
    "county": ("for=county:*&in=state:{fips}", ["state", "county"]),
    "place": ("for=place:*&in=state:{fips}", ["state", "place"]),
    "cousub": (
        "for=county%20subdivision:*&in=state:{fips}&in=county:*",
        ["state", "county", "county subdivision"],
    ),
}


def parse(payload: list[list[str]], level: str) -> pd.DataFrame:
    head, rows = payload[0], payload[1:]
    df = pd.DataFrame(rows, columns=head)
    return pd.DataFrame(
        {
            "geoid": df[QUERIES[level][1]].astype(str).agg("".join, axis=1),
            "level": level,
            "census_name": df["NAME"].str.split(",").str[0].str.strip(),
            "pop_2020": pd.to_numeric(df["P1_001N"], errors="coerce").astype("Int64"),
        }
    )


def load(state_fips: str, state: str, store: DataStore, *, refresh: bool = False) -> pd.DataFrame:
    key = api_key()
    raw = store.raw("census_dec_pl", 2020)
    frames = []
    for level, (query, _) in QUERIES.items():
        url = f"{URL}?get=NAME,P1_001N&{query.format(fips=state_fips)}"
        frames.append(
            parse(_fetch_json(url, raw / f"{state.lower()}_{level}.json", store, refresh, key), level)
        )
    return pd.concat(frames, ignore_index=True)
