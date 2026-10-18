"""Census TIGERweb boundaries of incorporated places and county subdivisions, for assigning points.

Parcel and permit layers often carry only a county field (Ohio's statewide parcels, for one). `lotline.geo`
places each point in an incorporated place, else (where townships issue permits) a county subdivision, using
these polygons.

Source: TIGERweb `Places_CouSub_ConCity_SubMCD` MapServer, **ACS 2025 vintage** (layer group 13): layer 18
"Incorporated Places" and layer 15 "County Subdivisions" (boundaries as of January 1, 2025). A fixed vintage,
not the "current" layers, so reruns give the same answer. Public domain (U.S. Government work).

Census-designated places (layer 19) are left out on purpose: they are statistical areas, not governments,
so they don't issue permits. Polygons are heavy (Columbus alone has 256 rings), so pages are small.
"""

from __future__ import annotations

import pandas as pd

from lotline.config import load_state
from lotline.io import DataStore
from lotline.io.arcgis import download_layer

ADAPTER = "national.tiger_boundaries"
VERSION = "1.0"
SOURCE = "census_tigerweb_acs2025"
LICENSE = "Public domain (U.S. Government work, 17 U.S.C. §105)"
VINTAGE = "acs2025"
SERVICE = (
    "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Places_CouSub_ConCity_SubMCD/MapServer"
)
LAYERS = {"place": 18, "cousub": 15}  # ACS 2025: Incorporated Places, County Subdivisions
PAGE_SIZE = 50  # polygons per page: some boundaries have tens of thousands of vertices

PROVENANCE = {
    "title": "Census TIGERweb boundaries, ACS 2025 vintage (incorporated places, county subdivisions)",
    "landing_url": "https://tigerweb.geo.census.gov/tigerwebmain/TIGERweb_main.html",
    "table": "none (boundaries for point assignment)",
    "cleaning": [
        "Query layers 18 (incorporated places) and 15 (county subdivisions) of the ACS 2025 group by state",
        "Keep GEOID (7-digit place, 10-digit county subdivision), NAME, FUNCSTAT and polygon rings in WGS84",
        "Points are assigned with the even-odd rule over every ring, so holes and enclaves are respected",
    ],
    "limitations": [
        "One boundary vintage (January 2025) is applied to every year: annexations move points near edges",
        "Census-designated places are excluded on purpose: they are statistical areas, not permit issuers",
        "A point exactly on a boundary goes to one side by a fixed rule, not by any legal determination",
    ],
}


def load_polygons(state: str, store: DataStore, level: str, *, refresh: bool = False) -> pd.DataFrame:
    """geoid, name, funcstat, rings (list of [[lon, lat], ...] rings) for one state's places or townships."""
    if level not in LAYERS:
        raise ValueError(f"level must be one of {sorted(LAYERS)}")
    fips = load_state(state).fips
    df = download_layer(
        f"{SERVICE}/{LAYERS[level]}",
        store=store,
        source=SOURCE,
        license=LICENSE,
        adapter=ADAPTER,
        adapter_version=VERSION,
        name=f"{level}_{fips}",
        where=f"STATE='{fips}'",
        out_fields="GEOID,NAME,FUNCSTAT",
        geometry="polygon",
        vintage=VINTAGE,
        page_size=PAGE_SIZE,
        refresh=refresh,
    )
    if df.empty:
        return pd.DataFrame(columns=["geoid", "name", "funcstat", "rings"])
    out = df.rename(columns={"GEOID": "geoid", "NAME": "name", "FUNCSTAT": "funcstat"})
    out = out[["geoid", "name", "funcstat", "rings"]].dropna(subset=["rings"])
    return out.sort_values("geoid", ignore_index=True)
