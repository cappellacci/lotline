"""Travis Central Appraisal District (TCAD) certified appraisal roll → `parcels` for the City of Austin.

**Hand-downloaded files.** TCAD publishes its rolls at https://traviscad.org/publicinformation/ behind a
browser check that our HTTP client cannot (and must not try to) pass, so Ben downloads each zip in a browser
and registers it (`lotline manifest register`, see `REGISTER_HELP`). `load()` reads every registered zip
(`DataStore.registered("tcad")`), one roll each; with none registered it stops and prints the command.

**Format.** TCAD's "Legacy 8.0.33 Appraisal Export Layout" (fixed-width text files in the zip; layout
spreadsheet linked in `LAYOUT_URL`). Only these files and fields are read, by position:

- `PROP.TXT` (appraisal info): prop_id, prop_type_cd, prop_val_yr (roll year), sup_num, geo_id, legal_acreage,
  land and improvement homestead / non-homestead values, hs_exempt, imprv_state_cd, land_state_cd;
- `PROP_ENT.TXT` (property to taxing unit): prop_id, entity_name;
- `STATE_CD.TXT` (district code → state category): state_cd, ptd_state_cd;
- `LAND_DET.TXT` (land segments): prop_id, size_square_feet, size_acres;
- `IMP_DET.TXT` (improvement details): prop_id, yr_built.

Owner names, owner and mortgage-company addresses, mortgage loan numbers, deed references, agent and
exemption-applicant fields sit in the same records, at other positions: they are **never sliced out of the
line**, so nothing personal reaches memory as a field or the table. The raw zip stays in `LOTLINE_DATA_DIR`.

**Rules.**

- Real property only (`prop_type_cd` R); one row per prop_id and roll (highest sup_num).
- City of Austin: a property is placed in a city when one of its `PROP_ENT.TXT` taxing units is named in
  `config/crosswalks/tx_tcad_entities.csv` (CITY OF AUSTIN → 4805000). Properties not taxed by a listed city
  are left out of this table (they belong to other cities or the county).
- Land use: the improvement's state code (else the land's) → its state category via `STATE_CD.TXT`
  (`ptd_state_cd`), else the code itself, then `config/crosswalks/tx_ptad_land_use.csv` at the category level
  (A, B, C1, ...; tried as the full code, then its first two characters, then the first). Unmatched → UNKNOWN.
  `land_use_raw` keeps the district code.
- Lot size: the sum of the land segments' square feet; where that is 0 or missing, legal acreage × 43,560.
- Year built: the earliest improvement-detail year from 1800 to the roll year (additions are later; the
  first year is the original building). Units and building area are not in the export: left null.
- Values: land = land homestead + non-homestead; building = improvement homestead + non-homestead;
  `value_basis = "appraisal"`. **Texas is a non-disclosure state: there are no sale prices.**
- Numbers: a field with a decimal point is read as written; a documented implied-decimal field without one
  ("Legal Acreage (4 Decimals)") is divided by 10^4.
- `parcel_id` = "48453" + geo_id digits, the ID the city's permits carry as `tcad_id`.
- `vintage` = prop_val_yr; `vintage_date` = the registration's vintage folder when it is a date (register
  with `--vintage <export date>`).
"""

from __future__ import annotations

import csv
import io
import re
import zipfile
from pathlib import Path

import pandas as pd

from lotline.config import CONFIG_DIR
from lotline.io import DataStore
from lotline.schemas import validate
from lotline.validation import holdout

ADAPTER = "states.tx.tcad_parcels"
VERSION = "1.0"
SOURCE = "tcad"
TABLE = "parcels"
LANDING_URL = "https://traviscad.org/publicinformation/"
LAYOUT_URL = (
    "https://traviscad.org/wp-content/largefiles/Website_Legacy8.0.33-AppraisalExportLayout_06182026.zip"
)
LICENSE = "Public information (Texas Public Information Act); published by Travis Central Appraisal District"
TRAVIS_FIPS = "48453"
LAND_USE_CROSSWALK = CONFIG_DIR / "crosswalks" / "tx_ptad_land_use.csv"
ENTITY_CROSSWALK = CONFIG_DIR / "crosswalks" / "tx_tcad_entities.csv"
SQFT_PER_ACRE = 43_560  # definition of the acre

REGISTER_HELP = (
    "No TCAD roll is registered. Download the certified appraisal export zip in a browser from "
    f"{LANDING_URL} (e.g. '2026 Certified Appraisal Export Supp 0_07182026.zip'), then run:\n"
    "  uv run lotline manifest register ~/Downloads/<file>.zip --source tcad "
    f"--url {LANDING_URL} --license '{LICENSE}' --vintage <export date, e.g. 2026-07-18>\n"
    "and fetch again: uv run lotline fetch --state TX --source tcad_parcels"
)

# (first column, width), 1-based, from the Legacy 8.0.33 layout. Only non-personal fields are listed.
PROP_FIELDS = {
    "prop_id": (1, 12),
    "prop_type_cd": (13, 5),
    "prop_val_yr": (18, 5),
    "sup_num": (23, 12),
    "geo_id": (547, 50),
    "legal_acreage": (1660, 16),
    "land_hstd_val": (1796, 15),
    "land_non_hstd_val": (1811, 15),
    "imprv_hstd_val": (1826, 15),
    "imprv_non_hstd_val": (1841, 15),
    "hs_exempt": (2609, 1),
    "imprv_state_cd": (2732, 10),
    "land_state_cd": (2742, 10),
}
PROP_ENT_FIELDS = {"prop_id": (1, 12), "entity_name": (64, 50)}
STATE_CD_FIELDS = {"state_cd": (1, 10), "ptd_state_cd": (61, 10)}
LAND_DET_FIELDS = {"prop_id": (1, 12), "size_acres": (70, 14), "size_square_feet": (84, 14)}
IMP_DET_FIELDS = {"prop_id": (1, 12), "yr_built": (86, 4)}
IMPLIED_DECIMALS = {"legal_acreage": 4, "size_acres": 4}  # per the layout's field descriptions
# Short and long names of each file in the export (the layout gives both)
FILES = {
    "prop": ("PROP.TXT", "APPRAISAL_INFO.TXT"),
    "prop_ent": ("PROP_ENT.TXT", "APPRAISAL_ENTITY_INFO.TXT"),
    "state_cd": ("STATE_CD.TXT", "APPRAISAL_STATE_CODE.TXT"),
    "land_det": ("LAND_DET.TXT", "APPRAISAL_LAND_DETAIL.TXT"),
    "imp_det": ("IMP_DET.TXT", "APPRAISAL_IMPROVEMENT_DETAIL.TXT"),
}
ENCODING = "latin-1"  # fixed-width export; never fails on stray bytes
MIN_YEAR_BUILT = 1800

PROVENANCE = {
    "title": "Travis Central Appraisal District certified appraisal roll (City of Austin parcels)",
    "landing_url": LANDING_URL,
    "table": TABLE,
    "attribution": "Travis Central Appraisal District",
    "cleaning": [
        "Zips are downloaded by hand in a browser (the site's bot check blocks scripted downloads) and "
        "registered with `lotline manifest register --source tcad`; nothing is fetched by script",
        "Fixed-width files read by position (TCAD Legacy 8.0.33 layout): PROP.TXT, PROP_ENT.TXT, "
        "STATE_CD.TXT, LAND_DET.TXT, IMP_DET.TXT. Excluded entirely (never sliced from the record): owner "
        "names and IDs, owner, mailing and mortgage-company addresses, mortgage loan numbers, deed "
        "book/page/number, agents, ARB, lawsuit and exemption-applicant data, situs address",
        "Real property only (prop_type_cd R); one row per prop_id and roll, the highest supplement",
        "City placement: properties taxed by an entity named in config/crosswalks/tx_tcad_entities.csv "
        "(CITY OF AUSTIN → 4805000); others are left out",
        "land_use_std: improvement (else land) state code → state category (STATE_CD.TXT ptd_state_cd) → "
        "config/crosswalks/tx_ptad_land_use.csv; land_use_raw keeps the district code",
        "lot_sqft: sum of land-segment square feet, else legal acreage × 43,560",
        "year_built: earliest improvement-detail year built (1800 to the roll year); units, bldg_sqft null",
        "land_value / bldg_value: homestead + non-homestead appraisal values; value_basis appraisal; "
        "homestead from hs_exempt",
        "parcel_id: '48453' + geo_id digits (matches the permits' tcad_id)",
        "Holdout filter applied with the parcel-roll snapshot rule (Texas has no holdouts)",
    ],
    "limitations": [
        "Texas is a non-disclosure state: no sale prices; values are appraisals",
        "Units per parcel and building area are not in the export",
        "Land use at the state-category level only until TCAD's district subcodes are crosswalked: "
        "category A (SF_DETACHED) may include townhomes and condominiums; category B (2+ units) is OTHER",
        "Parcels in Austin outside Travis County (Williamson, Hays) are in other districts' rolls",
        "The entity-name match and the implied-decimal rule have only been tested on synthetic fixtures",
    ],
}


# ---- reading ---------------------------------------------------------------------------------------------


def _slice(line: str, fields: dict[str, tuple[int, int]]) -> dict[str, str]:
    return {k: line[s - 1 : s - 1 + n].strip() for k, (s, n) in fields.items()}


def _member(zf: zipfile.ZipFile, key: str) -> str | None:
    wanted = {n.upper() for n in FILES[key]}
    for name in zf.namelist():
        if Path(name).name.upper() in wanted:
            return name
    return None


def _lines(zf: zipfile.ZipFile, key: str):
    name = _member(zf, key)
    if name is None:
        return
    with zf.open(name) as fh:
        for line in io.TextIOWrapper(fh, encoding=ENCODING, newline=""):
            line = line.rstrip("\r\n")
            if line.strip():
                yield line


def number(text: str, field: str = "") -> float | None:
    """A fixed-width number: as written if it has a decimal point, else with the field's implied decimals."""
    text = (text or "").strip()
    if not text:
        return None
    try:
        value = float(text)
    except ValueError:
        return None
    if "." not in text and field in IMPLIED_DECIMALS:
        value /= 10 ** IMPLIED_DECIMALS[field]
    return value


def load_land_use_crosswalk(path: Path = LAND_USE_CROSSWALK) -> dict[str, str]:
    with open(path, newline="") as fh:
        return {r["ptad_code"].strip().upper(): r["land_use_std"].strip() for r in csv.DictReader(fh)}


def load_entities(path: Path = ENTITY_CROSSWALK) -> dict[str, str]:
    with open(path, newline="") as fh:
        return {_norm(r["entity_name"]): r["jurisdiction_geoid"].strip() for r in csv.DictReader(fh)}


def _norm(name: str) -> str:
    return re.sub(r"\s+", " ", name or "").strip().upper()


def land_use(code: str | None, state_codes: dict[str, str], crosswalk: dict[str, str]) -> str:
    """District state code → land_use_std via its state category (see the module docstring)."""
    if not code:
        return "UNKNOWN"
    code = code.strip().upper()
    ptd = state_codes.get(code, code).strip().upper() or code
    for key in (ptd, ptd[:2], ptd[:1]):
        if key in crosswalk:
            return crosswalk[key]
    return "UNKNOWN"


def read_roll(path: Path, *, vintage_date: pd.Timestamp | None = None) -> pd.DataFrame:
    """One registered TCAD zip → parcels rows for the cities in the entity crosswalk (before validation)."""
    entities = load_entities()
    crosswalk = load_land_use_crosswalk()
    with zipfile.ZipFile(path) as zf:
        if _member(zf, "prop") is None:
            raise FileNotFoundError(
                f"{path.name}: no PROP.TXT / APPRAISAL_INFO.TXT inside; is it a TCAD export?"
            )
        city_of: dict[str, str] = {}
        seen_names: set[str] = set()
        for line in _lines(zf, "prop_ent"):
            r = _slice(line, PROP_ENT_FIELDS)
            name = _norm(r["entity_name"])
            seen_names.add(name)
            if name in entities:
                city_of.setdefault(r["prop_id"], entities[name])
        if not city_of:
            near = sorted(n for n in seen_names if "AUSTIN" in n) or sorted(seen_names)[:20]
            raise ValueError(
                f"{path.name}: no property is taxed by an entity in {ENTITY_CROSSWALK.name}; "
                f"entity names seen include {near}"
            )
        state_codes = {}
        for line in _lines(zf, "state_cd"):
            r = _slice(line, STATE_CD_FIELDS)
            if r["state_cd"]:
                state_codes[r["state_cd"].upper()] = r["ptd_state_cd"]
        land_sqft: dict[str, float] = {}
        for line in _lines(zf, "land_det"):
            r = _slice(line, LAND_DET_FIELDS)
            if r["prop_id"] not in city_of:
                continue
            sqft = number(r["size_square_feet"], "size_square_feet")
            if not sqft:
                acres = number(r["size_acres"], "size_acres")
                sqft = acres * SQFT_PER_ACRE if acres else None
            if sqft:
                land_sqft[r["prop_id"]] = land_sqft.get(r["prop_id"], 0.0) + sqft
        props = []
        for line in _lines(zf, "prop"):
            r = _slice(line, PROP_FIELDS)
            if r["prop_type_cd"].upper() == "R" and r["prop_id"] in city_of:
                props.append(r)
        built: dict[str, int] = {}
        roll_years = {p["prop_val_yr"] for p in props}
        max_year = max((int(y) for y in roll_years if y.isdigit()), default=2100)
        for line in _lines(zf, "imp_det"):
            r = _slice(line, IMP_DET_FIELDS)
            if r["prop_id"] not in city_of or not r["yr_built"].isdigit():
                continue
            year = int(r["yr_built"])
            if MIN_YEAR_BUILT <= year <= max_year + 1:
                built[r["prop_id"]] = min(year, built.get(r["prop_id"], year))
    df = pd.DataFrame(props, columns=list(PROP_FIELDS))
    if df.empty:
        return df
    df["sup"] = pd.to_numeric(df["sup_num"], errors="coerce").fillna(0)
    df = df.sort_values("sup").drop_duplicates(["prop_id", "prop_val_yr"], keep="last")
    vals = {c: df[c].map(lambda t, c=c: number(t, c)) for c in PROP_FIELDS if c.endswith("_val")}
    code = df["imprv_state_cd"].where(df["imprv_state_cd"] != "", df["land_state_cd"])
    acreage = df["legal_acreage"].map(lambda t: number(t, "legal_acreage"))
    seg = df["prop_id"].map(land_sqft)
    geo = df["geo_id"].str.replace(r"\D", "", regex=True)
    out = pd.DataFrame(
        {
            "state": "TX",
            "parcel_id": (TRAVIS_FIPS + geo).where(geo != "", TRAVIS_FIPS + "p" + df["prop_id"]),
            "vintage": pd.to_numeric(df["prop_val_yr"], errors="coerce").astype("Int64"),
            "vintage_date": pd.Series(vintage_date, index=df.index, dtype="datetime64[ns]"),
            "jurisdiction_geoid": df["prop_id"].map(city_of),
            "county_geoid": TRAVIS_FIPS,
            "lot_sqft": seg.where(seg > 0, acreage * SQFT_PER_ACRE).astype("float64"),
            "land_use_std": code.map(lambda c: land_use(c, state_codes, crosswalk)),
            "land_use_raw": code.replace("", pd.NA),
            "units": pd.Series(pd.NA, index=df.index, dtype="Int64"),
            "year_built": df["prop_id"].map(built).astype("Int64"),
            "land_value": (vals["land_hstd_val"].fillna(0) + vals["land_non_hstd_val"].fillna(0)).astype(
                float
            ),
            "bldg_value": (vals["imprv_hstd_val"].fillna(0) + vals["imprv_non_hstd_val"].fillna(0)).astype(
                float
            ),
            "value_basis": "appraisal",
            "homestead": df["hs_exempt"].str.upper().map({"T": True, "F": False}).astype("boolean"),
            "source": SOURCE,
        }
    )
    both_null = vals["land_hstd_val"].isna() & vals["land_non_hstd_val"].isna()
    out.loc[both_null.values, "land_value"] = float("nan")
    both_null = vals["imprv_hstd_val"].isna() & vals["imprv_non_hstd_val"].isna()
    out.loc[both_null.values, "bldg_value"] = float("nan")
    # a geo_id shared by two prop_ids (e.g. a split in progress) keeps the higher prop_id's row
    out = out.assign(_pid=df["prop_id"].values).sort_values("_pid")
    out = out.drop_duplicates(["state", "parcel_id", "vintage"], keep="last").drop(columns="_pid")
    return out.reset_index(drop=True)


def _vintage_date(rel_path: str) -> pd.Timestamp | None:
    folder = Path(rel_path).parent.name
    try:
        return pd.Timestamp(folder) if re.fullmatch(r"\d{4}-\d{2}-\d{2}", folder) else None
    except ValueError:
        return None


def load(state: str, store: DataStore, *, refresh: bool = False) -> pd.DataFrame:
    if state.upper() != "TX":
        raise ValueError(f"{SOURCE} covers Travis County, Texas only, not {state}")
    entries = [e for e in store.registered(SOURCE) if e.path.lower().endswith(".zip")]
    if not entries:
        raise FileNotFoundError(REGISTER_HELP)
    stale = [e.path for e in entries if store.is_stale(e)]
    if stale:
        raise FileNotFoundError(f"registered TCAD files missing or changed since registration: {stale}")
    rolls = [read_roll(store.root / e.path, vintage_date=_vintage_date(e.path)) for e in entries]
    df = pd.concat(rolls, ignore_index=True)
    # the same roll registered twice (e.g. a re-download) counts once: keep the later registration
    df = df.drop_duplicates(["state", "parcel_id", "vintage"], keep="last")
    df = holdout.apply(
        df,
        "TX",
        geoid_col="jurisdiction_geoid",
        date_col="vintage_date",
        year_col="vintage",
        snapshot=True,
    )
    return validate(df, TABLE)
