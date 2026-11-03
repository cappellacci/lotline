"""City of Houston residential building permits by month (single-family and multi-family counts).

Used only to check Census BPS for Houston (D-039 groundwork, `docs/research/lotline-causal-diagram-mm.md`
§6.5): it has no canonical table and is not run by `lotline fetch`. The file is the city's own monthly summary
of permits applied for; it has no building-size classes, so it can test BPS's 1-unit count directly and its
2-4 unit count only as multi-family minus BPS 3+ units.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from lotline.io import DataStore, fetch

ADAPTER = "checks.houston_permits"
VERSION = "1.0"
SOURCE = "houston_permits_summary"
URL = (
    "https://data.houstontx.gov/dataset/525772a1-0b4b-4d55-9b43-4d3b589fe1b7/resource/"
    "c9cef716-4d81-4dac-9b05-d19acddf159f/download/summary_residential_permits.xlsx"
)
LICENSE = "Open Data Commons Attribution License (City of Houston open data portal)"

PROVENANCE = {
    "title": "City of Houston Residential Building Permits by Month and Year (summary counts)",
    "landing_url": "https://data.houstontx.gov/dataset/residential-building-permits",
    "table": "none (check only)",
    "attribution": "City of Houston, Houston Permitting Center, via data.houstontx.gov",
    "cleaning": [
        "Columns renamed to year, month, single_family, multi_family, residential",
        "Annual sums over complete years only (12 months)",
        "Compared with Census BPS Houston (4835000) by scripts/dev/houston_bps_check.py; nothing is stored",
    ],
    "limitations": [
        "Counts of permits applied for, not issued; no building-size classes (duplexes are in multi-family)",
        "Unit of count (permits or homes) is not stated by the publisher",
        "2018 and 2019 carry identical totals (5,159 single-family, 7,933 multi-family): a copied year?",
    ],
}


def annual(monthly: pd.DataFrame) -> pd.DataFrame:
    """Monthly rows (year, month, single_family, multi_family) → annual sums for complete years."""
    g = monthly.groupby("year")
    out = g[["single_family", "multi_family"]].sum()
    return out[g["month"].nunique() == 12]


def read(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path)
    df.columns = ["year", "month", "single_family", "multi_family", "residential"]
    return df


def load(store: DataStore, *, refresh: bool = False) -> pd.DataFrame:
    """Download (or reuse) the city's file and return annual counts."""
    vintage = date.today().isoformat()[:7]  # the city replaces the file in place
    path = fetch(
        URL,
        store.raw(SOURCE, vintage) / "summary_residential_permits.xlsx",
        store=store,
        source=SOURCE,
        license=LICENSE,
        adapter=ADAPTER,
        adapter_version=VERSION,
        refresh=refresh,
    )
    return annual(read(path))
