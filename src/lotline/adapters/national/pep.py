"""Census Population Estimates Program (PEP): annual July 1 population for states and counties, 2010-2025.

Used by the data dashboard (`lotline.dashboard`) to set housing growth beside population growth. Not a model
input.

Source: the national county "alldata" files, which also carry one state-total row per state (SUMLEV 040):

- Vintage 2020, https://www2.census.gov/programs-surveys/popest/datasets/2010-2020/counties/totals/
  co-est2020-alldata.csv: POPESTIMATE2010..POPESTIMATE2020 (2010 Census base)
- Vintage 2025, https://www2.census.gov/programs-surveys/popest/datasets/2020-2025/counties/totals/
  co-est2025-alldata.csv: POPESTIMATE2020..POPESTIMATE2025 (2020 Census base)

Public domain (U.S. Government work). **Splice rule**: years 2010-2019 come from vintage 2020 and years
2020-2025 from vintage 2025, so each year has one value and the decade seam sits at 2020, where the base
changes from the 2010 to the 2020 Census. The seam is shown in the dashboard, not smoothed.
"""

from __future__ import annotations

import csv
import io
from pathlib import Path

import pandas as pd

from lotline.io import DataStore, fetch

ADAPTER = "national.pep"
VERSION = "1.0"
SOURCE = "census_pep"
LICENSE = "Public domain (U.S. Government work, 17 U.S.C. §105)"
BASE = "https://www2.census.gov/programs-surveys/popest/datasets"
# vintage -> (url, first year, last year used from this vintage)
FILES = {
    2020: (f"{BASE}/2010-2020/counties/totals/co-est2020-alldata.csv", 2010, 2019),
    2025: (f"{BASE}/2020-2025/counties/totals/co-est2025-alldata.csv", 2020, 2025),
}

PROVENANCE = {
    "title": "Census Population Estimates Program, state and county totals (vintages 2020 and 2025)",
    "landing_url": "https://www.census.gov/programs-surveys/popest.html",
    "table": "none (data dashboard: population growth beside housing growth)",
    "cleaning": [
        "POPESTIMATE<year> for state (SUMLEV 040) and county (SUMLEV 050) rows of the national alldata files",
        "Spliced: 2010-2019 from vintage 2020, 2020-2025 from vintage 2025 (one value per year)",
    ],
    "limitations": [
        "Estimates, not counts; each vintage revises past years; the 2020 seam changes the Census base",
        "Used only for the data dashboard, never as a model input",
    ],
}


def parse(text: str, vintage: int) -> pd.DataFrame:
    """geo ('state:SS' or 'county:SSCCC'), name, year, population, vintage per row of one alldata file."""
    _, first, last = FILES[vintage]
    rows = []
    for r in csv.DictReader(io.StringIO(text)):
        level = {"040": "state", "050": "county"}.get(r["SUMLEV"].strip())
        if level is None:
            continue
        st, co = r["STATE"].strip().zfill(2), r["COUNTY"].strip().zfill(3)
        geo = f"state:{st}" if level == "state" else f"county:{st}{co}"
        name = (r["STNAME"] if level == "state" else r["CTYNAME"]).strip()
        for year in range(first, last + 1):
            v = (r.get(f"POPESTIMATE{year}") or "").strip()
            if v:
                rows.append(
                    {"geo": geo, "name": name, "year": year, "population": int(v), "vintage": vintage}
                )
    return pd.DataFrame(rows, columns=["geo", "name", "year", "population", "vintage"])


def cached(store: DataStore) -> bool:
    """True when every PEP file is already in the raw store (so `load` needs no network)."""
    return all((store.raw(SOURCE, v) / Path(u).name).exists() for v, (u, _, _) in FILES.items())


def load(store: DataStore, *, state_fips: list[str] | None = None, refresh: bool = False) -> pd.DataFrame:
    """Spliced state and county population, 2010-2025, optionally limited to some states' FIPS codes."""
    frames = []
    for vintage, (url, _, _) in FILES.items():
        path = fetch(
            url,
            store.raw(SOURCE, vintage) / Path(url).name,
            store=store,
            source=SOURCE,
            license=LICENSE,
            adapter=ADAPTER,
            adapter_version=VERSION,
            refresh=refresh,
        )
        frames.append(parse(path.read_text(encoding="latin-1"), vintage))
    out = pd.concat(frames, ignore_index=True)
    if state_fips is not None:
        st = out["geo"].str.split(":").str[1].str[:2]
        out = out[st.isin(state_fips)]
    return out.sort_values(["geo", "year"], ignore_index=True)
