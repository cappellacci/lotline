"""FHFA House Price Index, annual all-transactions indexes → `market_geo_year` (hpi columns).

Source: https://www.fhfa.gov/data/hpi/datasets (Additional Data, annual). Public domain (U.S. Government).
FHFA labels the sub-state annual files "developmental": thin places may be missing or noisy, and FHFA
suppresses series with too few repeat sales. Missing years stay missing; we never interpolate here.

Each file has a few title rows, then a header row (found by looking for "Year" and "HPI"), then one row per
geography-year. `HPI` is base 100 in the series' first year, so it isn't comparable across places;
`HPI with 2000 base` is.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pandas as pd

from lotline.io import DataStore, fetch
from lotline.schemas import validate

ADAPTER = "national.fhfa"
VERSION = "1.0"
SOURCE = "fhfa_hpi_annual"
LICENSE = "Public domain (U.S. Government work, 17 U.S.C. §105)"
BASE_URL = "https://www.fhfa.gov/hpi/download/annual"

# level -> (file name, column holding the geography code, code width)
LEVELS = {
    "state": ("hpi_at_state.xlsx", "FIPS", 2),
    "cbsa": ("hpi_at_cbsa.xlsx", "CBSA", 5),
    "county": ("hpi_at_county.xlsx", "FIPS code", 5),
    "zip5": ("hpi_at_zip5.xlsx", "Five-Digit ZIP Code", 5),
    "tract": ("hpi_at_tract.csv", "tract", 11),
}
DEFAULT_LEVELS = tuple(LEVELS)  # tract is ~80 MB nationally; all levels are cached after the first pull
RENAME = {"HPI": "hpi", "HPI with 2000 base": "hpi_base2000", "Annual Change (%)": "hpi_change_pct"}
TRACT_RENAME = {
    "year": "Year",
    "hpi": "HPI",
    "hpi2000": "HPI with 2000 base",
    "annual_change": "Annual Change (%)",
}


def read_table(path: Path) -> pd.DataFrame:
    """Read an FHFA annual file, skipping its title rows; everything as strings.

    Parsed files are cached per (path, size, mtime), so a multi-state run reads each national file once.
    """
    stat = path.stat()
    return _read_table(path, stat.st_size, stat.st_mtime_ns).copy()


@lru_cache(maxsize=8)
def _read_table(path: Path, _size: int, _mtime: int) -> pd.DataFrame:
    if path.suffix == ".csv":
        return pd.read_csv(path, dtype=str).rename(columns=TRACT_RENAME)
    head = pd.read_excel(path, header=None, nrows=30, dtype=str)
    for i, row in head.iterrows():
        labels = {str(v).strip() for v in row if pd.notna(v)}
        if {"Year", "HPI"} <= labels:
            df = pd.read_excel(path, header=i, dtype=str)
            df.columns = [str(c).strip() for c in df.columns]
            return df
    raise ValueError(f"{path}: no header row with 'Year' and 'HPI'")


def to_canonical(raw: pd.DataFrame, level: str) -> pd.DataFrame:
    """Map one FHFA file to market_geo_year rows with a level-prefixed `geo` (all states)."""
    _, code_col, width = LEVELS[level]
    df = raw.rename(columns=RENAME)
    code = df[code_col].str.strip().str.zfill(width)
    out = pd.DataFrame(
        {
            "geo": level + ":" + code,
            "year": pd.to_numeric(df["Year"], errors="coerce").astype("Int64"),
            **{c: pd.to_numeric(df[c], errors="coerce") for c in RENAME.values() if c in df},
        }
    )
    if level == "cbsa":
        out["name"] = df["Name"].str.strip()
    return out.dropna(subset=["year"])


def cbsa_states(name: str, code: str) -> set[str]:
    """States a CBSA touches, from its name ("Duluth, MN-WI" -> {"MN", "WI"}).

    FHFA's non-metro remainders use the 2-digit state FIPS as the code ("Minnesota (non CBSA areas)").
    """
    if len(code.lstrip("0")) <= 2 and "non CBSA" in name:
        return {f"fips:{code[-2:]}"}
    _, _, tail = name.rpartition(",")
    return {s.strip() for s in tail.split("-") if s.strip()}


def for_state(
    df: pd.DataFrame, level: str, state: str, fips: str, zip3: list[tuple[int, int]] = ()
) -> pd.DataFrame:
    """Keep rows that belong to (or, for CBSAs, touch) one state.

    ZIP5 rows carry no state, so they are assigned by 3-digit prefix ranges from the state config (`zip3`).
    """
    code = df["geo"].str.split(":").str[1]
    if level == "zip5":
        prefix = code.str[:3].astype(int)
        return df[pd.concat([prefix.between(lo, hi) for lo, hi in zip3], axis=1).any(axis=1)]
    if level == "cbsa":
        keep = [
            bool({state, f"fips:{fips}"} & cbsa_states(n, c)) for n, c in zip(df["name"], code, strict=True)
        ]
        return df[keep]
    return df[code.str.startswith(fips)]


def load(
    state: str,
    store: DataStore,
    levels: tuple[str, ...] = DEFAULT_LEVELS,
    *,
    refresh: bool = False,
    fips: str | None = None,
) -> pd.DataFrame:
    """Download (cached) and build HPI rows for one state at each level."""
    from lotline.config import load_state

    cfg = load_state(state)
    fips = fips or cfg.fips
    vintage = "current"  # FHFA overwrites the files in place; the manifest's sha256 + date identify each pull
    frames = []
    for level in levels:
        name = LEVELS[level][0]
        path = fetch(
            f"{BASE_URL}/{name}",
            store.raw(SOURCE, vintage) / name,
            store=store,
            source=SOURCE,
            license=LICENSE,
            adapter=ADAPTER,
            adapter_version=VERSION,
            refresh=refresh,
        )
        frames.append(for_state(to_canonical(read_table(path), level), level, state, fips, cfg.zip3_ranges))
    return validate(pd.concat(frames, ignore_index=True), "market_geo_year")
