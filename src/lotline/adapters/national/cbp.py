"""Census County Business Patterns: paid employment by 2-digit NAICS sector, for counties and the nation.

Source: Census Data API, https://api.census.gov/data/<year>/cbp. Public domain (U.S. Government work). Uses
the same free key as the ACS (CENSUS_API_KEY). Inputs to `build/demand.py` (the shift-share local demand
index); no canonical table of its own.

What CBP counts: paid employees in the pay period including March 12, at private non-farm establishments
(no government, no self-employed, little agriculture). Rows are "all establishments, all sizes"
(LFO = 001, EMPSZES = 001); county 999 ("statewide", establishments with no fixed county) is dropped.

**Suppression.** Through 2016, CBP withholds county-sector employment that would identify a business: the
value is published as 0 with a letter flag (`EMP_F`) giving the true range. Such a cell is filled at a
position inside that range set by `config/params/demand.yaml` (`suppressed_cell_position`; 0.5 = midpoint),
and marked `imputed`. From 2017, CBP adds noise instead of withholding, so no cell is imputed. A sector with
no row for a county has no establishments there (0 employees).

Requests: one per state-year (all sectors at once) and one per year for the nation.
"""

from __future__ import annotations

import pandas as pd

from lotline.adapters.national.acs import _fetch_json, api_key
from lotline.io import DataStore

ADAPTER = "national.cbp"
VERSION = "1.0"
SOURCE = "census_cbp"
BASE_URL = "https://api.census.gov/data"
DEFAULT_YEARS = range(2010, 2024)  # 2023 is the latest vintage on the API (checked 2026-10-20)

# 2-digit NAICS sectors, the same at this level in NAICS 2007, 2012 and 2017. Excluded: 00 (total) and 99
# (establishments CBP could not classify).
SECTORS = (
    "11",
    "21",
    "22",
    "23",
    "31-33",
    "42",
    "44-45",
    "48-49",
    "51",
    "52",
    "53",
    "54",
    "55",
    "56",
    "61",
    "62",
    "71",
    "72",
    "81",
)

# Employment-size ranges behind the suppression flags (CBP methodology, "Noise and suppression flags").
# The top range is open-ended; its lower bound is used as both ends.
FLAG_RANGES = {
    "a": (0, 19),
    "b": (20, 99),
    "c": (100, 249),
    "e": (250, 499),
    "f": (500, 999),
    "g": (1_000, 2_499),
    "h": (2_500, 4_999),
    "i": (5_000, 9_999),
    "j": (10_000, 24_999),
    "k": (25_000, 49_999),
    "l": (50_000, 99_999),
    "m": (100_000, 100_000),
}
LAST_FLAGGED_YEAR = 2016  # from 2017 CBP adds noise instead of suppressing; EMP_F no longer exists

PROVENANCE = {
    "title": "Census County Business Patterns: paid employment by NAICS sector (counties and U.S.)",
    "landing_url": "https://www.census.gov/programs-surveys/cbp.html",
    "table": "market_geo_year (inputs to demand_bartik, via build/demand.py)",
    "cleaning": [
        "2-digit NAICS sectors; all legal forms (LFO 001) and all establishment sizes (EMPSZES 001)",
        "County 999 (statewide, no fixed location) dropped; a missing county-sector row means 0 employees",
        "Through 2016, suppressed cells (EMP 0 with a flag a-m) are set inside the flag's range at "
        "suppressed_cell_position (config/params/demand.yaml) and marked imputed",
    ],
    "limitations": [
        "Private non-farm wage employment only: no government, self-employed or most farm jobs",
        "March employment each year; county is where the establishment is, not where workers live",
        "From 2017 CBP adds noise to every cell instead of suppressing; small cells can be off by 5% or more",
        "Requires a free Census API key (CENSUS_API_KEY); the key is never written to the manifest",
    ],
}


def naics_var(year: int) -> str:
    """The NAICS column name for a CBP vintage."""
    if year >= 2017:
        return "NAICS2017"
    if year >= 2012:
        return "NAICS2012"
    return "NAICS2007"


def url(year: int, geo: str) -> str:
    """The request for every sector's employment in `geo` (`for=...` clause) in one vintage."""
    naics = naics_var(year)
    get = f"EMP,{naics}" + (",EMP_F" if year <= LAST_FLAGGED_YEAR else "")
    sectors = "&".join(f"{naics}={s}" for s in SECTORS)
    return f"{BASE_URL}/{year}/cbp?get={get}&{geo}&LFO=001&EMPSZES=001&{sectors}"


def parse(payload: list[list[str]], year: int, position: float) -> pd.DataFrame:
    """One API response → rows (geo, year, sector, emp, imputed). `geo` is the 5-digit county or 'US'.

    Suppressed cells are set at `position` (0 = bottom, 1 = top) inside their flag's range."""
    head, rows = payload[0], payload[1:]
    df = pd.DataFrame(rows, columns=head).loc[:, lambda d: ~d.columns.duplicated()]
    if "county" in df:
        df = df[df["county"] != "999"]
        geo = df["state"] + df["county"]
    else:
        geo = pd.Series("US", index=df.index)
    emp = pd.to_numeric(df["EMP"], errors="coerce").astype(float)
    flag = df["EMP_F"].fillna("").str.strip() if "EMP_F" in df else pd.Series("", index=df.index)
    lo = flag.map(lambda f: FLAG_RANGES.get(f, (None, None))[0])
    hi = flag.map(lambda f: FLAG_RANGES.get(f, (None, None))[1])
    imputed = lo.notna() & (emp == 0)
    fill = lo.astype(float) + position * (hi.astype(float) - lo.astype(float))
    return pd.DataFrame(
        {
            "geo": geo.to_numpy(),
            "year": year,
            "sector": df[naics_var(year)].str.strip().to_numpy(),
            "emp": emp.where(~imputed, fill).to_numpy(),
            "imputed": imputed.to_numpy(),
        }
    )


def load(
    fips: str, store: DataStore, years: range = DEFAULT_YEARS, *, position: float, refresh: bool = False
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(county rows for one state, national rows) over `years`, downloaded once and cached."""
    key = api_key()
    county, nation = [], []
    for year in years:
        raw = store.raw(SOURCE, year)
        for geo, dest, out in (
            (f"for=county:*&in=state:{fips}", raw / f"state_{fips}.json", county),
            ("for=us:*", raw / "us.json", nation),
        ):
            payload = _fetch_json(
                url(year, geo),
                dest,
                store,
                refresh,
                key,
                source=SOURCE,
                adapter=ADAPTER,
                adapter_version=VERSION,
            )
            out.append(parse(payload, year, position))
    return pd.concat(county, ignore_index=True), pd.concat(nation, ignore_index=True)
