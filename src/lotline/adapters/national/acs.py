"""Census American Community Survey 5-year estimates → `acs_geo_year` (long format, with margins of error).

Source: Census Data API, https://api.census.gov/data/<year>/acs/acs5. Public domain (U.S. Government work).
Needs a free key (CENSUS_API_KEY in the environment or .env); the key is sent with each request but never
written to the manifest or to error messages.

Tables (WS-CORE brief): B25024 units in structure, B25003 tenure, B25064 median gross rent, B25077 median
value, B25034 year structure built. Geographies: state, county, place, tract, and county subdivisions where
the state config says townships issue permits (MN, OH).

Census marks special cases with large negative numbers. Estimates: all such codes → missing. Margins of
error: -555555555 ("controlled", estimate exact) → 0; other codes → missing.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd

from lotline.io import DataStore, fetch
from lotline.io.store import _dotenv_value
from lotline.schemas import validate

ADAPTER = "national.acs"
VERSION = "1.0"
SOURCE = "census_acs5"
LICENSE = "Public domain (U.S. Government work, 17 U.S.C. §105)"
BASE_URL = "https://api.census.gov/data"

TABLES = ("B25024", "B25003", "B25064", "B25077", "B25034")
DEFAULT_YEARS = range(2010, 2025)  # 5-year end years; 2024 = 2020-2024, released Dec 2025
LEVELS = ("state", "county", "place", "cousub", "tract")
MAX_VARS = 48  # API limit is 50 variables per call, including NAME

CONTROLLED_MOE = -555555555
GEO_COLS = {
    "state": ["state"],
    "county": ["state", "county"],
    "place": ["state", "place"],
    "cousub": ["state", "county", "county subdivision"],
    "tract": ["state", "county", "tract"],
}


class CensusKeyError(RuntimeError):
    pass


def api_key() -> str:
    key = os.environ.get("CENSUS_API_KEY") or _dotenv_value("CENSUS_API_KEY")
    if not key:
        raise CensusKeyError("CENSUS_API_KEY is not set (add it to .env; see README)")
    return key


def geo_clause(level: str, fips: str) -> str:
    """The `for=` / `in=` part of a request for every geography of `level` in one state."""
    return {
        "state": f"for=state:{fips}",
        "county": f"for=county:*&in=state:{fips}",
        "place": f"for=place:*&in=state:{fips}",
        "cousub": f"for=county%20subdivision:*&in=state:{fips}&in=county:*",
        "tract": f"for=tract:*&in=state:{fips}&in=county:*",
    }[level]


def variables_for(groups: dict[str, dict]) -> list[str]:
    """Estimate variables (…E) in the requested tables, sorted, from each table's groups/<T>.json."""
    out = []
    for meta in groups.values():
        out += [v[:-1] for v in meta["variables"] if v.endswith("E") and v[:-1][-3:].isdigit()]
    return sorted(out)


def labels_for(groups: dict[str, dict]) -> dict[str, str]:
    return {
        v[:-1]: meta["variables"][v]["label"].replace("Estimate!!", "")
        for meta in groups.values()
        for v in meta["variables"]
        if v.endswith("E") and v[:-1][-3:].isdigit()
    }


def chunks(variables: list[str], size: int = MAX_VARS // 2) -> list[list[str]]:
    """Split variables so each request (estimate + MOE columns) stays under the API limit."""
    return [variables[i : i + size] for i in range(0, len(variables), size)]


def parse(payload: list[list[str]], level: str, end_year: int, labels: dict[str, str]) -> pd.DataFrame:
    """Turn one API response (header row + data rows) into long-format rows."""
    head, rows = payload[0], payload[1:]
    df = pd.DataFrame(rows, columns=head)
    geo = level + ":" + df[GEO_COLS[level]].astype(str).agg("".join, axis=1)
    out = []
    for var in sorted({c[:-1] for c in head if c.endswith("E") and c[:-1] in labels}):
        est = pd.to_numeric(df[var + "E"], errors="coerce")
        moe = pd.to_numeric(df.get(var + "M"), errors="coerce") if var + "M" in df else pd.Series(pd.NA)
        moe = moe.where(moe != CONTROLLED_MOE, 0.0)
        out.append(
            pd.DataFrame(
                {
                    "geo": geo,
                    "end_year": end_year,
                    "table_id": var.split("_")[0],
                    "variable": var,
                    "label": labels[var],
                    "estimate": est.where(est > -100_000_000),
                    "moe": moe.where(moe >= 0),
                }
            )
        )
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()


def _fetch_json(url: str, dest: Path, store: DataStore, refresh: bool, key: str | None = None):
    path = fetch(
        url,
        dest,
        store=store,
        source=SOURCE,
        license=LICENSE,
        adapter=ADAPTER,
        adapter_version=VERSION,
        refresh=refresh,
        secret_params={"key": key} if key else None,
    )
    text = path.read_text()
    if not text.lstrip().startswith(("[", "{")):
        path.unlink()  # an HTML error page (e.g. invalid key) must not be cached as data
        raise CensusKeyError(f"Census API returned a non-JSON page for {url}; check CENSUS_API_KEY")
    return json.loads(text)


def load(
    state: str,
    store: DataStore,
    years: range = DEFAULT_YEARS,
    *,
    refresh: bool = False,
    levels: tuple[str, ...] | None = None,
) -> pd.DataFrame:
    """Download (cached) and build acs_geo_year for one state."""
    from lotline.config import load_state

    cfg = load_state(state)
    levels = levels or tuple(lv for lv in LEVELS if lv != "cousub" or cfg.township_permits)
    key = api_key()
    frames = []
    for year in years:
        raw = store.raw(SOURCE, year)
        groups = {
            t: _fetch_json(f"{BASE_URL}/{year}/acs/acs5/groups/{t}.json", raw / f"{t}.json", store, refresh)
            for t in TABLES
        }
        labels = labels_for(groups)
        for level in levels:
            for i, part in enumerate(chunks(variables_for(groups))):
                get = ",".join(f"{v}E,{v}M" for v in part)
                url = f"{BASE_URL}/{year}/acs/acs5?get={get}&{geo_clause(level, cfg.fips)}"
                payload = _fetch_json(url, raw / f"{state.lower()}_{level}_{i}.json", store, refresh, key)
                frames.append(parse(payload, level, year, labels))
    return validate(pd.concat(frames, ignore_index=True), "acs_geo_year")
