"""How permit-issuing places split across counties and townships, from the 2020 Census.

Used by `build/eligible.py` to build "rest of county" denominators without counting a home twice:

- **county shares**: a place that spans counties (e.g. Raleigh: Wake and Durham) contributes to each county in
  proportion to its 2020 housing units there (2020 Census DHC `H1_001N`, geography "county (or part)").
- **township shares**: in MN and OH some incorporated places are not their own county subdivision, so their
  homes are also inside a township's ACS count (e.g. Ada village inside Liberty township, Hardin County, OH).
  Their 2020 housing-unit parts per township come from DHC geography "place/remainder (or part)" (the P.L.
  94-171 redistricting file doesn't publish that geography).

Which places span counties, and which are their own county subdivision, comes from the Census 2020 code files
(`national_place_by_county2020.txt`, `national_cousub2020.txt`). Shares are fixed at 2020 for every ACS year:
an assumption, stated in provenance. The Census API allows no wildcards for these part geographies, so the
requests are one per multi-county place and one per township in a county holding a dependent place, made once.
"""

from __future__ import annotations

import io

import pandas as pd

from lotline.adapters.national.acs import _fetch_json, api_key
from lotline.io import DataStore, fetch

ADAPTER = "national.geoparts"
VERSION = "1.0"
SOURCE = "census_geo_codes"
LICENSE = "Public domain (U.S. Government work, 17 U.S.C. §105)"
CODES_URL = "https://www2.census.gov/geo/docs/reference/codes2020"
DHC_URL = "https://api.census.gov/data/2020/dec/dhc"  # 2020 Census Demographic and Housing Characteristics

PROVENANCE = {
    "title": "Census 2020 geography: code files and DHC housing-unit parts",
    "landing_url": "https://www.census.gov/library/reference/code-lists/ansi.html",
    "table": "none (inputs to eligible_parcels allocation)",
    "cleaning": [
        "Read pipe-delimited files; build 7-digit place and 10-digit county-subdivision GEOIDs",
        "A place is its own county subdivision when a subdivision with its FIPS code has class C*",
        "Places with more than one county get 2020 housing-unit shares by county (DHC H1_001N)",
        "Places that aren't their own subdivision get 2020 housing-unit shares by township (DHC H1_001N)",
    ],
    "limitations": [
        "Splits use 2020 housing units, fixed for every ACS year: homes are assumed spread like 2020 housing",
        "Housing units of all types are used to split one-unit detached homes",
    ],
}


def _codes(name: str, store: DataStore, refresh: bool) -> pd.DataFrame:
    path = fetch(
        f"{CODES_URL}/{name}",
        store.raw(SOURCE, 2020) / name,
        store=store,
        source=SOURCE,
        license=LICENSE,
        adapter=ADAPTER,
        adapter_version=VERSION,
        refresh=refresh,
    )
    return pd.read_csv(io.StringIO(path.read_text(encoding="latin-1")), sep="|", dtype=str)


def place_by_county(fips: str, store: DataStore, refresh: bool = False) -> pd.DataFrame:
    df = _codes("national_place_by_county2020.txt", store, refresh)
    df = df[df["STATEFP"] == fips]
    return pd.DataFrame(
        {"place_geoid": df["STATEFP"] + df["PLACEFP"], "county_geoid": df["STATEFP"] + df["COUNTYFP"]}
    )


def county_subdivisions(fips: str, store: DataStore, refresh: bool = False) -> pd.DataFrame:
    df = _codes("national_cousub2020.txt", store, refresh)
    df = df[df["STATEFP"] == fips]
    return pd.DataFrame(
        {
            "cousub_geoid": df["STATEFP"] + df["COUNTYFP"] + df["COUSUBFP"],
            "county_geoid": df["STATEFP"] + df["COUNTYFP"],
            "cousub_fp": df["COUSUBFP"],
            "classfp": df["CLASSFP"],
        }
    )


def _parts(url: str, name: str, store: DataStore, refresh: bool, key: str) -> list[list[str]]:
    return _fetch_json(
        url,
        store.raw(SOURCE, 2020) / "parts" / name,
        store,
        refresh,
        key,
        source=SOURCE,
        adapter=ADAPTER,
        adapter_version=VERSION,
    )


def county_shares(fips: str, places: list[str], store: DataStore, refresh: bool = False) -> pd.DataFrame:
    """place_geoid, county_geoid, share for each permit-issuing place (shares sum to 1 per place)."""
    pbc = place_by_county(fips, store, refresh)
    pbc = pbc[pbc["place_geoid"].isin(places)]
    n = pbc.groupby("place_geoid")["county_geoid"].transform("nunique")
    single = pbc[n == 1].assign(share=1.0)
    rows = [single]
    key = api_key() if (n > 1).any() else None
    for place in sorted(pbc.loc[n > 1, "place_geoid"].unique()):
        url = f"{DHC_URL}?get=H1_001N&for=county%20(or%20part):*&in=state:{fips}&in=place:{place[2:]}"
        payload = _parts(url, f"place_{place}_by_county.json", store, refresh, key)
        df = pd.DataFrame(payload[1:], columns=payload[0])
        hu = pd.to_numeric(df["H1_001N"], errors="coerce").fillna(0)
        total = hu.sum()
        rows.append(
            pd.DataFrame(
                {
                    "place_geoid": place,
                    "county_geoid": fips + df["county (or part)"],
                    "share": hu / total if total else 1.0 / len(df),
                }
            )
        )
    return pd.concat(rows, ignore_index=True)[["place_geoid", "county_geoid", "share"]]


def township_shares(
    fips: str, places: list[str], townships: list[str], store: DataStore, refresh: bool = False
) -> pd.DataFrame:
    """place_geoid, township_geoid, share for permit-issuing places that are not their own county
    subdivision (their homes sit inside a township's ACS count). Empty when there are none."""
    subs = county_subdivisions(fips, store, refresh)
    own = set(fips + subs.loc[subs["classfp"].str.startswith("C"), "cousub_fp"])
    dependent = [p for p in places if p not in own]
    if not dependent or not townships:
        return pd.DataFrame(columns=["place_geoid", "township_geoid", "share"])
    pbc = place_by_county(fips, store, refresh)
    counties = set(pbc.loc[pbc["place_geoid"].isin(dependent), "county_geoid"])
    candidates = subs[subs["county_geoid"].isin(counties) & subs["cousub_geoid"].isin(townships)]
    key = api_key()
    parts = []
    for r in candidates.itertuples():
        url = (
            f"{DHC_URL}?get=H1_001N&for=place/remainder%20(or%20part):*"
            f"&in=state:{fips}&in=county:{r.county_geoid[2:]}&in=county%20subdivision:{r.cousub_fp}"
        )
        payload = _parts(url, f"township_{r.cousub_geoid}_places.json", store, refresh, key)
        df = pd.DataFrame(payload[1:], columns=payload[0])
        df = df.assign(
            place_geoid=fips + df["place/remainder (or part)"],
            township_geoid=r.cousub_geoid,
            hu=pd.to_numeric(df["H1_001N"], errors="coerce").fillna(0),
        )
        parts.append(df[df["place_geoid"].isin(dependent)][["place_geoid", "township_geoid", "hu"]])
    if not parts:
        return pd.DataFrame(columns=["place_geoid", "township_geoid", "share"])
    parts = pd.concat(parts, ignore_index=True)
    # Share of each dependent place's 2020 housing units in each township it overlaps (summing to 1): a
    # dependent place is taken to lie wholly inside townships, which is what "dependent" means.
    totals = (
        pd.DataFrame({"place_geoid": dependent})
        .merge(
            parts.groupby("place_geoid", as_index=False)["hu"].sum().rename(columns={"hu": "total"}),
            how="left",
            on="place_geoid",
        )
        .set_index("place_geoid")["total"]
    )
    parts["share"] = parts["hu"] / parts["place_geoid"].map(totals)
    return parts.dropna(subset=["share"])[["place_geoid", "township_geoid", "share"]]
