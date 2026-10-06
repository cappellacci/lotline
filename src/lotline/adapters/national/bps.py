"""Census Building Permits Survey (BPS): annual place-level permits → `bps_place_year`.

Source: https://www2.census.gov/econ/bps/Place/ (one comma-separated text file per Census region per year,
1980 onward; layout documented in Documentation/placeasc.pdf). Public domain (U.S. Government work).

Each file has two header lines, then one row per permit-issuing place. The last 24 columns are always
bldgs/units/value for 1, 2, 3-4 and 5+ unit buildings, first including Census imputation for months a place
didn't report, then reported only ("rep"). Identifier columns before them vary by era, so they are found by
header name. FIPS place and MCD codes appear from about 2007; earlier years get their GEOID from later years
(`backfill_geoids`). The 6-digit IDs were renumbered in 1992 (Minneapolis: 140500 in 1991, 497800 from 1992)
and old numbers were reused for other places, so IDs only link years from 1992 on; before that, rows are
matched on county and place name.
"""

from __future__ import annotations

import csv
import io
from pathlib import Path

import pandas as pd

from lotline.io import DataStore, fetch
from lotline.schemas import validate
from lotline.validation import holdout

ADAPTER = "national.bps"
VERSION = "1.0"
SOURCE = "census_bps_place_annual"
LICENSE = "Public domain (U.S. Government work, 17 U.S.C. §105)"
BASE_URL = "https://www2.census.gov/econ/bps/Place"

REGIONS = {"Northeast Region": "ne", "Midwest Region": "mw", "South Region": "so", "West Region": "we"}
STATE_FIPS = {"MN": "27", "NC": "37", "OH": "39", "TX": "48"}
STATE_REGION = {"MN": "Midwest Region", "NC": "South Region", "OH": "Midwest Region", "TX": "South Region"}

SIZES = ["1", "2", "3_4", "5p"]
NUMERIC = [f"{kind}_{s}" for s in SIZES for kind in ("bldgs", "units", "value")]
NUMERIC += [f"{c}_rep" for c in NUMERIC]  # 24 columns, in file order
NO_PLACE = {"", "00000", "99990", "99999"}
NO_MCD = {"", "00000", "99999"}
ID_ERA_START = 1992  # first year of the current 6-digit ID numbering
DEFAULT_YEARS = range(ID_ERA_START, 2026)


def file_url(region: str, year: int) -> str:
    return f"{BASE_URL}/{region.replace(' ', '%20')}/{REGIONS[region]}{year}a.txt"


def _header_index(row1: list[str], row2: list[str]) -> dict[str, int]:
    """Map 'Row1 Row2' header labels (e.g. 'FIPS Place Code', 'Place Name') to column positions."""
    return {f"{a.strip()} {b.strip()}".strip(): i for i, (a, b) in enumerate(zip(row1, row2, strict=False))}


def parse(text: str, year: int) -> pd.DataFrame:
    """Parse one annual BPS place file into raw-but-typed rows (all states in the region)."""
    rows = list(csv.reader(io.StringIO(text)))
    head = _header_index(rows[0], rows[1])
    name_at = head["Place Name"]
    months_at = head["Number of Months Rep"]
    fips_place_at = head.get("FIPS Place Code")
    fips_mcd_at = head.get("FIPS MCD Code")

    out = []
    for r in rows[2:]:
        if len(r) < name_at + 25 or not r[1].strip():
            continue  # blank spacer line
        nums = r[-24:]
        out.append(
            {
                "state_fips": r[head["State Code"]].strip().zfill(2),
                "id6": r[head["6-Digit ID"]].strip().zfill(6),
                "county": r[head["County Code"]].strip().zfill(3),
                "fips_place": r[fips_place_at].strip() if fips_place_at is not None else "",
                "fips_mcd": r[fips_mcd_at].strip() if fips_mcd_at is not None else "",
                # names can contain commas, so take everything between the name column and the numbers
                "name": ",".join(r[name_at:-24]).strip().strip(","),
                "months_reported": int(r[months_at].strip() or 0),
                **{c: int(float(v.strip() or 0)) for c, v in zip(NUMERIC, nums, strict=True)},
            }
        )
    df = pd.DataFrame(out)
    df["year"] = year
    return df


def to_canonical(raw: pd.DataFrame, state: str) -> pd.DataFrame:
    """Filter one state's rows and map them to the `bps_place_year` table."""
    fips = STATE_FIPS[state]
    df = raw[raw["state_fips"] == fips].copy()
    df["state"] = state
    df["bps_id"] = df["state_fips"] + df["id6"]
    df["county_geoid"] = df["state_fips"] + df["county"]
    df["geoid"] = [_geoid(r.state_fips, r.county, r.fips_place, r.fips_mcd) for r in df.itertuples()]
    total_rep = df[[f"units_{s}_rep" for s in SIZES]].sum(axis=1)
    total = df[[f"units_{s}" for s in SIZES]].sum(axis=1)
    df["imputed"] = (df["months_reported"] < 12) | (total_rep != total)
    return df


def _geoid(state_fips: str, county: str, place: str, mcd: str) -> str | None:
    """Census place GEOID (SS+PPPPP) where there is one, else county subdivision (SS+CCC+MMMMM), else None."""
    if place not in NO_PLACE:
        return state_fips + place.zfill(5)
    if mcd not in NO_MCD:
        return state_fips + county + mcd.zfill(5)
    return None  # e.g. "<County> Unincorporated Area": aggregate through county_geoid


def _name_key(name: pd.Series) -> pd.Series:
    """Normalize place names for matching across years ("St. Paul" == "Saint Paul city")."""
    s = (
        name.str.lower()
        .str.replace(r"\bsaint\b", "st", regex=True)
        .str.replace(r"[^a-z0-9 ]", "", regex=True)
    )
    return s.str.replace(r"\s+(city|village|town|borough)$", "", regex=True).str.strip()


def backfill_geoids(df: pd.DataFrame) -> pd.DataFrame:
    """Fill missing GEOIDs from the latest year that has one.

    From 1992 on, rows link by BPS ID. Before 1992 the IDs mean different places, so rows link by
    (county, normalized name) instead, and only where that key is unique.
    """
    df = df.copy()
    known = df.dropna(subset=["geoid"]).sort_values("year")
    era = df["year"] >= ID_ERA_START
    by_id = known[known["year"] >= ID_ERA_START].groupby("bps_id")["geoid"].last()
    df.loc[era, "geoid"] = df.loc[era, "geoid"].fillna(df.loc[era, "bps_id"].map(by_id))

    pre = ~era & df["geoid"].isna()
    if pre.any():
        ref = df[era].dropna(subset=["geoid"]).sort_values("year")
        ref = ref.assign(key=ref["county_geoid"] + "|" + _name_key(ref["name"]))
        ref = ref.groupby("key")["geoid"].agg(lambda g: g.iloc[-1] if g.nunique() == 1 else None).dropna()
        keys = df.loc[pre, "county_geoid"] + "|" + _name_key(df.loc[pre, "name"])
        df.loc[pre, "geoid"] = keys.map(ref)
    return df


def load(
    state: str,
    store: DataStore,
    years: range = DEFAULT_YEARS,
    *,
    refresh: bool = False,
    unblind: tuple[str, ...] = (),
) -> pd.DataFrame:
    """Download (cached) and build the canonical `bps_place_year` table for one state.

    Held-out place-years are removed before anything else sees the table (validation.holdout).
    The raw regional files on disk still contain them; never read those directly.
    """
    region = STATE_REGION[state]
    frames = []
    for year in years:
        url = file_url(region, year)
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
        frames.append(to_canonical(parse(path.read_text(encoding="latin-1"), year), state))
    df = backfill_geoids(pd.concat(frames, ignore_index=True))
    df = holdout.apply(df, state, unblind=unblind, geoid_col="geoid", year_col="year")
    return validate(df.reset_index(drop=True), "bps_place_year")
