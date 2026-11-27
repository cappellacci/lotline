"""Census TIGER/Line 2025 boundaries of incorporated places and county subdivisions, for assigning points.

Parcel and permit layers often carry only a county field (Ohio's statewide parcels, for one). `lotline.geo`
places each point in an incorporated place, else (where townships issue permits) a county subdivision, using
these polygons.

Source: the TIGER/Line 2025 shapefiles, one zip per state and level (`tl_2025_<fips>_place.zip`,
`tl_2025_<fips>_cousub.zip`), boundaries as of January 1, 2025. These are static files Census keeps
archived by year, so a fetch years from now gets the same polygons. Until 2026-11-27 this read the same
vintage from the TIGERweb map service, whose layer numbers move when Census adds a vintage and which began
refusing requests (stability review, 2026-11-27). On the four states cached from both, the places and
townships are identical and fewer than 1 in 1,000 sample points land differently (all on a boundary).
Public domain.

Census-designated places (class U) and military areas (class M) are left out on purpose: they are not
governments, so they don't issue permits. Only incorporated places (class C) are kept, the same set as
TIGERweb's "Incorporated Places" layer.
"""

from __future__ import annotations

import pandas as pd

from lotline.config import load_state
from lotline.io import DataStore, shapefile
from lotline.io.http import fetch

ADAPTER = "national.tiger_boundaries"
VERSION = "2.0"
SOURCE = "census_tigerline_2025"
LICENSE = "Public domain (U.S. Government work, 17 U.S.C. §105)"
VINTAGE = "2025"
BASE_URL = "https://www2.census.gov/geo/tiger/TIGER2025"
FOLDERS = {"place": "PLACE", "cousub": "COUSUB"}
INCORPORATED = "C"  # TIGER/Line place class codes C1-C9; U = census-designated, M = military


def url(fips: str, level: str) -> str:
    return f"{BASE_URL}/{FOLDERS[level]}/tl_2025_{fips}_{level}.zip"


def raw_path(store: DataStore, fips: str, level: str):
    return store.raw(SOURCE, VINTAGE) / f"tl_2025_{fips}_{level}.zip"


def cached(state: str, store: DataStore, level: str) -> bool:
    """Whether the state's boundary file for `level` is already downloaded."""
    return raw_path(store, load_state(state).fips, level).is_file()


PROVENANCE = {
    "title": "Census TIGER/Line 2025 boundaries (incorporated places, county subdivisions)",
    "landing_url": "https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.html",
    "table": "none (boundaries for point assignment)",
    "cleaning": [
        "Download the state's TIGER/Line 2025 place and county-subdivision zips; read them with the built-in "
        "shapefile reader (lotline.io.shapefile)",
        "Keep incorporated places only (class C); every county subdivision",
        "Keep GEOID (7-digit place, 10-digit county subdivision), NAME, FUNCSTAT and polygon rings (NAD83 "
        "longitude/latitude, within a metre of WGS84)",
        "Points are assigned with the even-odd rule over every ring, so holes and enclaves are respected",
    ],
    "limitations": [
        "One boundary vintage (January 2025) is applied to every year: annexations move points near edges",
        "Census-designated places and military areas are excluded on purpose: they are not permit issuers",
        "A point exactly on a boundary goes to one side by a fixed rule, not by any legal determination",
    ],
}


def load_polygons(state: str, store: DataStore, level: str, *, refresh: bool = False) -> pd.DataFrame:
    """geoid, name, funcstat, rings (list of [[lon, lat], ...] rings) for one state's places or townships."""
    if level not in FOLDERS:
        raise ValueError(f"level must be one of {sorted(FOLDERS)}")
    fips = load_state(state).fips
    dest = raw_path(store, fips, level)
    dest.parent.mkdir(parents=True, exist_ok=True)
    path = fetch(
        url(fips, level),
        dest,
        store=store,
        source=SOURCE,
        license=LICENSE,
        adapter=ADAPTER,
        adapter_version=VERSION,
        refresh=refresh,
    )
    df = pd.DataFrame(shapefile.read_zip(path))
    if df.empty:
        return pd.DataFrame(columns=["geoid", "name", "funcstat", "rings"])
    if level == "place":
        df = df[df["CLASSFP"].str.startswith(INCORPORATED)]
    out = df.rename(columns={"GEOID": "geoid", "NAME": "name", "FUNCSTAT": "funcstat"})
    out = out[["geoid", "name", "funcstat", "rings"]].dropna(subset=["rings"])
    return out.sort_values("geoid", ignore_index=True)
