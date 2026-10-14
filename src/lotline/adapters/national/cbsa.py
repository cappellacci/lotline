"""County → metro/micro area (CBSA) crosswalk from the official OMB delineation (Census "List 1").

Source: Census delineation file list1_2023.xlsx (OMB Bulletin 23-01, July 2023; URL below). Public domain
(U.S. Government work). These are the CBSA codes FHFA's annual HPI uses (all 175 FHFA CBSAs in MN, NC, OH and
TX match), so a county without its own FHFA index can fall back to its metro or micro area's index.

Counties outside any CBSA (rural) have no row; they fall back to FHFA's state "non CBSA" or state index.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from lotline.io import DataStore, fetch

ADAPTER = "national.cbsa"
VERSION = "1.0"
SOURCE = "census_cbsa_delineation"
LICENSE = "Public domain (U.S. Government work, 17 U.S.C. §105)"
VINTAGE = 2023
URL = (
    "https://www2.census.gov/programs-surveys/metro-micro/geographies/reference-files/2023/delineation-files/"
    "list1_2023.xlsx"
)
CBSA_TYPES = {"Metropolitan Statistical Area": "metro", "Micropolitan Statistical Area": "micro"}

PROVENANCE = {
    "title": "OMB core-based statistical area (CBSA) delineation, July 2023 (county to metro/micro area)",
    "landing_url": "https://www.census.gov/geographies/reference-files/time-series/demo/metro-micro/"
    "delineation-files.html",
    "table": "jurisdictions (cbsa_code, cbsa_type)",
    "cleaning": [
        "Skip the title rows; keep CBSA code, title, metro/micro type and county FIPS",
        "County GEOID = state FIPS + county FIPS; one CBSA per county",
        "Each jurisdiction gets its county's CBSA (multi-county places: the county BPS files them under)",
    ],
    "limitations": [
        "Rural counties belong to no CBSA (no code)",
        "2023 delineation applied to all years; CBSA boundaries changed in 2013 and 2023",
    ],
}


def parse(path: Path) -> pd.DataFrame:
    """county_geoid, cbsa_code, cbsa_title, cbsa_type (metro/micro), central (bool)."""
    head = pd.read_excel(path, header=None, nrows=10, dtype=str)
    header_row = next(i for i, r in head.iterrows() if "CBSA Code" in {str(v).strip() for v in r})
    df = pd.read_excel(path, header=header_row, dtype=str)
    df = df.dropna(subset=["CBSA Code", "FIPS State Code", "FIPS County Code"])
    df = df[df["CBSA Code"].str.fullmatch(r"\d{5}")]
    out = pd.DataFrame(
        {
            "county_geoid": df["FIPS State Code"].str.zfill(2) + df["FIPS County Code"].str.zfill(3),
            "cbsa_code": df["CBSA Code"],
            "cbsa_title": df["CBSA Title"].str.strip(),
            "cbsa_type": df["Metropolitan/Micropolitan Statistical Area"].map(CBSA_TYPES),
            "central": df["Central/Outlying County"].str.strip().eq("Central"),
        }
    )
    if out["county_geoid"].duplicated().any():
        raise ValueError("a county appears in more than one CBSA")
    return out.reset_index(drop=True)


def load(store: DataStore, *, refresh: bool = False) -> pd.DataFrame:
    path = fetch(
        URL,
        store.raw(SOURCE, VINTAGE) / Path(URL).name,
        store=store,
        source=SOURCE,
        license=LICENSE,
        adapter=ADAPTER,
        adapter_version=VERSION,
        refresh=refresh,
    )
    return parse(path)
