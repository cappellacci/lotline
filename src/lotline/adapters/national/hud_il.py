"""HUD Section 8 income limits (FY 2026): each county's area median family income and its income limits by
household size -> `market_geo_year` (hud_* columns), for the AMI strip (`model/affordability.py`).

Source: https://www.huduser.gov/portal/datasets/il.html (FY 2026, "Section 8 Income Limits" data file).
Public domain (U.S. Government work). HUD's "area median income" (AMI) is the Median Family Income (MFI) of a
HUD area: a metropolitan area, part of one, or a non-metropolitan county. The file has one row per county
(per town in New England) with its area's MFI and the very-low (50%), extremely-low and low (80%) income
limits for 1 to 8 persons. HUD scales the limits by household size and adjusts some areas (high housing cost,
low income), so the published limit, not MFI times a factor, is what a housing official means by "X% AMI".

**Downloaded by hand.** huduser.gov answers every scripted request (the landing page and the file links)
with an AWS WAF bot challenge (checked 2026-11-19), and the house rules forbid working around a block. So, as
with the Wake roll, the file is saved in a browser and registered (Ben, 2026-11-19); nothing here sends a
request. Without a registered file, `load` returns no rows and says how to register one, so `lotline fetch`
still runs end to end; the AMI strip then shows nothing for the state.

**Columns read** (matched without case; HUD renames the year-stamped MFI column every year):

- `fips`: 10 digits, state + county + `99999` for a whole county (New England towns carry a town code instead
  and are left out: no Lotline state is in New England); a 5-digit county code is also accepted.
- `median<YYYY>` (or `median`): the area's 4-person MFI, dollars of the fiscal year.
- `l50_1` ... `l50_5`: the very-low-income (50%) limits for 1 to 5 persons.

Rows are written as `geo = county:<5 digits>`, `year = <fiscal year>` (2026), in nominal dollars of that year;
callers deflate with `money`.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from lotline.io import DataStore
from lotline.schemas import validate

ADAPTER = "national.hud_il"
VERSION = "1.0"
SOURCE = "hud_income_limits"
TABLE = "market_geo_year"
FISCAL_YEAR = 2026
LANDING_URL = "https://www.huduser.gov/portal/datasets/il.html"
LICENSE = "Public domain (U.S. Government work, 17 U.S.C. §105)"
SIZES = (1, 2, 3, 4, 5)
COLUMNS = ["hud_mfi", *(f"hud_l50_{n}" for n in SIZES)]
REGISTER_HELP = (
    "No HUD income limits file is registered. huduser.gov blocks scripted downloads (bot challenge), so the "
    f"file is saved by hand: open {LANDING_URL} in a browser, choose FY {FISCAL_YEAR}, download the "
    "Section 8 income limits data file (Excel), then run\n"
    f"  uv run lotline manifest register ~/Downloads/<file> --source {SOURCE} --url {LANDING_URL} "
    f'--license "{LICENSE}" --vintage fy{FISCAL_YEAR}'
)

PROVENANCE = {
    "title": f"HUD Section 8 income limits, FY {FISCAL_YEAR} (area median family income and limits by size)",
    "landing_url": LANDING_URL,
    "table": TABLE,
    "cleaning": [
        "File saved by hand in a browser and registered with `lotline manifest register --source "
        "hud_income_limits` (huduser.gov blocks scripted requests); nothing is fetched by script",
        "Keep whole-county rows (fips ending 99999, or 5-digit codes); geo = county:<state+county FIPS>",
        "Keep the area's 4-person MFI and the 50% limits for 1 to 5 persons (nominal dollars of the "
        "fiscal year)",
    ],
    "limitations": [
        "AMI is family income for the whole HUD area, owners included; the median renter earns less",
        "Non-metropolitan counties are their own HUD area; a metro's counties share one MFI",
        "HUD adjusts some areas' limits (high housing cost, low income), so limits are not "
        "exactly MFI x a factor",
        "One fiscal year only (FY 2026); a fresh setup needs the manual download step",
    ],
}


def _find(columns, pattern: str) -> str | None:
    for c in columns:
        if re.fullmatch(pattern, str(c).strip(), flags=re.IGNORECASE):
            return c
    return None


def read(path: Path) -> pd.DataFrame:
    """Read the HUD file (Excel or CSV) as strings."""
    path = Path(path)
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path, dtype=str)
    return pd.read_excel(path, dtype=str)


def to_canonical(raw: pd.DataFrame, fiscal_year: int = FISCAL_YEAR) -> pd.DataFrame:
    """One row per whole county: geo, year, hud_mfi, hud_l50_1 ... hud_l50_5 (every state in the file).

    By hand: fips '3718399999', median2026 '132300', l50_1 '46350' -> geo 'county:37183', hud_mfi 132300.
    """
    fips = _find(raw.columns, r"fips(2010)?")
    mfi = _find(raw.columns, rf"median({fiscal_year})?") or _find(raw.columns, r"median\d{4}")
    limits = {n: _find(raw.columns, rf"l50_{n}") for n in SIZES}
    missing = [name for name, c in [("fips", fips), ("median", mfi), *limits.items()] if c is None]
    if missing:
        raise ValueError(f"HUD income limits file lacks column(s) {missing}; has {list(raw.columns)}")
    code = raw[fips].astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
    code = code.where(code.str.len() != 9, "0" + code)  # Excel drops a leading zero on 10-digit codes
    code = code.where(code.str.len() != 4, "0" + code)
    county = code.str.len().eq(5) | (code.str.len().eq(10) & code.str.endswith("99999"))
    num = lambda c: pd.to_numeric(raw.loc[county, c].astype(str).str.replace(",", ""), errors="coerce")  # noqa: E731
    out = pd.DataFrame(
        {
            "geo": "county:" + code[county].str[:5],
            "year": pd.array([fiscal_year] * int(county.sum()), dtype="Int64"),
            "hud_mfi": num(mfi),
            **{f"hud_l50_{n}": num(c) for n, c in limits.items()},
        }
    )
    return out.dropna(subset=["hud_mfi"]).drop_duplicates("geo").reset_index(drop=True)


def for_state(df: pd.DataFrame, fips: str) -> pd.DataFrame:
    """Rows for one state's counties (state FIPS prefix)."""
    return df[df["geo"].str.startswith(f"county:{fips}")].reset_index(drop=True)


def entries(store: DataStore) -> list:
    return store.registered(SOURCE)


def empty() -> pd.DataFrame:
    return pd.DataFrame(
        {"geo": pd.Series(dtype=str), "year": pd.Series(dtype="Int64")}
        | {c: pd.Series(dtype=float) for c in COLUMNS}
    )


def load(state: str, store: DataStore, *, refresh: bool = False) -> pd.DataFrame:
    """This state's counties from the latest registered file; no rows (and a note) when none is registered."""
    from lotline.config import load_state

    found = entries(store)
    if not found:
        print(f"note: {REGISTER_HELP}")
        return validate(empty(), TABLE)
    entry = found[-1]
    if store.is_stale(entry):
        raise FileNotFoundError(f"registered HUD income limits file missing or changed: {entry.path}")
    df = for_state(to_canonical(read(store.root / entry.path)), load_state(state).fips)
    return validate(df, TABLE)
