"""National annual series from FRED (Federal Reserve Bank of St. Louis) → `market_geo_year` at `national:US`.

| Column | FRED series | Original source | Frequency |
|---|---|---|---|
| `mortgage_rate` | MORTGAGE30US | Freddie Mac Primary Mortgage Market Survey (30-year fixed, %) | weekly |
| `ppi_resid_inputs` | WPUIP2311001 | BLS PPI, residential construction inputs (1986-06=100) | monthly |
| `cpi_u` | CPIAUCSL | BLS CPI-U, all items, seasonally adjusted (1982-84 = 100) | monthly |

Downloads use FRED's public CSV endpoint (no key). BLS series are public domain. The mortgage rate is
Freddie Mac data that FRED republishes with permission; cite "Freddie Mac, Primary Mortgage Market Survey,
via FRED" wherever it is shown (see docs/data_provenance.md).

Annual values are the mean of a calendar year's observations, and only for **complete** years (52+ weekly or
12 monthly observations). Partial years, such as the current one, are left missing rather than averaged.

One exception, stated because it is an assumption: a **single** missing observation between two published ones
is filled by linear interpolation before averaging. This exists for October 2025, when BLS published no CPI
because of the federal shutdown; without it the 2025 base year for real dollars would be missing. Longer gaps
stay missing.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from lotline.io import DataStore, fetch
from lotline.schemas import validate

ADAPTER = "national.fred"
VERSION = "1.0"
SOURCE = "fred"
BASE_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"

# column -> (series id, frequency, license)
SERIES = {
    "mortgage_rate": (
        "MORTGAGE30US",
        "weekly",
        "Freddie Mac PMMS, republished by FRED with permission; attribution required",
    ),
    "ppi_resid_inputs": ("WPUIP2311001", "monthly", "Public domain (BLS, U.S. Government work)"),
    "cpi_u": ("CPIAUCSL", "monthly", "Public domain (BLS, U.S. Government work)"),
}
MIN_OBS = {"weekly": 52, "monthly": 12}


def parse(text: str) -> pd.Series:
    """FRED CSV (observation_date, value) → float series indexed by date; '.' marks a missing value."""
    from io import StringIO

    df = pd.read_csv(StringIO(text), dtype=str)
    values = pd.to_numeric(df.iloc[:, 1], errors="coerce")
    return pd.Series(values.to_numpy(), index=pd.to_datetime(df.iloc[:, 0]))


def annual_mean(obs: pd.Series, frequency: str) -> pd.Series:
    """Calendar-year means over complete years only (others NaN); single interior gaps interpolated."""
    obs = obs.interpolate(method="time", limit=1, limit_area="inside").dropna()
    grouped = obs.groupby(obs.index.year)
    means = grouped.mean()
    return means.where(grouped.count() >= MIN_OBS[frequency]).rename_axis("year")


def load(state: str, store: DataStore, *, refresh: bool = False) -> pd.DataFrame:
    """National series (identical for every state; written per state so each state folder is complete)."""
    vintage = date.today().isoformat()[:7]  # FRED revises series in place; one raw copy per month pulled
    cols = {}
    for col, (series_id, freq, license) in SERIES.items():
        url = f"{BASE_URL}?id={series_id}"
        path = fetch(
            url,
            store.raw(SOURCE, vintage) / f"{series_id}.csv",
            store=store,
            source=SOURCE,
            license=license,
            adapter=ADAPTER,
            adapter_version=VERSION,
            refresh=refresh,
        )
        cols[col] = annual_mean(parse(Path(path).read_text()), freq)
    df = pd.DataFrame(cols).reset_index()
    df.insert(0, "geo", "national:US")
    return validate(df, "market_geo_year")
