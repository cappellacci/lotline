"""Census BPS annual **state** totals, used only to check the place-level adapter (V0 reconciliation).

Source: https://www2.census.gov/econ/bps/State/st<YYYY>a.txt. Public domain (U.S. Government work).
Same column layout in every year since 1992: identifiers, then bldgs/units/value for 1, 2, 3-4, 5+ units,
first including imputation, then reported only.
"""

from __future__ import annotations

import csv
import io
from pathlib import Path

import pandas as pd

from lotline.io import DataStore, fetch

ADAPTER = "national.bps_state"
VERSION = "1.0"
SOURCE = "census_bps_state_annual"
LICENSE = "Public domain (U.S. Government work, 17 U.S.C. §105)"
BASE_URL = "https://www2.census.gov/econ/bps/State"
SIZES = ["1", "2", "3_4", "5p"]

PROVENANCE = {
    "title": "Census Building Permits Survey (BPS), annual state totals (reconciliation only)",
    "landing_url": "https://www.census.gov/construction/bps/",
    "table": "none (V0 check against bps_place_year)",
    "cleaning": ["Parse units for 1, 2, 3-4 and 5+ unit buildings (with imputation) per state and year"],
    "limitations": [
        "Used only to check that place files add up; never an input to the model",
        "Held-out state-years are not compared, so a held-out place can't be recovered by subtraction",
    ],
}


def parse(text: str, year: int) -> pd.DataFrame:
    rows = []
    for r in list(csv.reader(io.StringIO(text)))[2:]:
        if len(r) < 29 or not r[1].strip().isdigit():
            continue
        nums = [int(float(v.strip() or 0)) for v in r[-24:]]
        rows.append(
            {"state_fips": r[1].strip().zfill(2), "year": year}
            | {f"units_{s}": nums[1 + 3 * i] for i, s in enumerate(SIZES)}
        )
    return pd.DataFrame(rows)


def load(store: DataStore, years: range, *, refresh: bool = False) -> pd.DataFrame:
    frames = []
    for year in years:
        url = f"{BASE_URL}/st{year}a.txt"
        path = fetch(
            url,
            store.raw(SOURCE, year) / Path(url).name,
            store=store,
            source=SOURCE,
            license=LICENSE,
            adapter=ADAPTER,
            adapter_version=VERSION,
            refresh=refresh,
        )
        frames.append(parse(path.read_text(encoding="latin-1"), year))
    return pd.concat(frames, ignore_index=True)
