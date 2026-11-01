"""City of Fort Worth development permits (Development Services, Accela) → canonical `permits`.

Fort Worth publishes every development permit it has filed since 2001 (building and trade permits) as one
open-data table, `CFW_Open_Data_Development_Permits_View` (CC-BY 4.0): permit number, type and subtype, the
building's use (`Use_Type`, `Specific_Use`), a unit count (`Units`), floor area, job value, filing date,
current status and its date, and a free-text work description. Fort Worth is Texas's fifth-largest city and
has no rentable-ADU rule (`config/reforms/tx.csv`, TX-4827000-adu-2010), so its permits give the ADU
estimate (D-025) a Texas comparison city and the missing-middle work a check of 2–4 unit counts against BPS.

**Rows requested** (`WHERE`): residential building permits, residential accessory-structure permits (where
detached ADUs would be filed) and commercial building permits with a residential use (apartment and
rental-community buildings). Trade permits (plumbing, electrical, mechanical), backflow, forestry, grading,
design review and non-residential commercial permits are not requested.

**One row per permit.** The table holds status snapshots: a permit can appear once per status it passed
through (Approved, Issued, Finaled ...), each row repeating the permit's units. Rows are collapsed by
`Permit_No`, so units are counted once per permit (D-008): the use and unit count come from the latest
row that has a use, the status from the latest row by status date. A permit is kept if any of its rows is
Issued, Issued Without Contractor or Finaled, or its latest status is Expired (expired permits were issued,
as BPS counts them); Void, Withdrawn, Denied and permits still in review are dropped.

**Dates.** The table has **no issue date**: only the filing date and the date of each status. So
`issue_year` is the **filing year**, `issue_date` is empty and `date_precision` is `year`;
`application_date` = filing date; `final_date` = the date of the Finaled status (`final_inspection`).
Filing comes some weeks before issue, so a permit filed in December may be counted a year before BPS
counts it. The status date 1900-01-01 means "none" and is read as missing.

**Building type and units** (`config/crosswalks/tx_fw_use.csv`, one row per permit type and use):

- `dwelling` uses on new residential building permits (single-family house SFD, townhouse TH, duplex U2):
  `Units` when it fits the type (SFD and TH 1; duplex 1-2) → `reported`; else the type's count (`derived`);
- `multi` uses on new commercial building permits (apartments, townhouse apartments): a `Units` of 2 or more
  gives the type (2 U2, 3-4 U3_4, 5+ MF5) and the count (`reported`); otherwise type and units unknown;
- `multi_detached` (detached cottages in rental communities): `Units` 1 is a one-unit building (SFD, as
  BPS counts it); 2 or more as `multi`;
- `foundation` permits: 0 units (`derived`): the home is counted on its building permit;
- `accessory` permits (sheds, garages, pools ... and the use "Accessory Dwelling", which also holds storm
  shelters, studios and game rooms) and `nonresidential` uses (hotels, motels): 0 units (`derived`);
- `group` uses (group homes, congregate living): type OTHER, units unknown;
- **accessory dwelling units:** the description parser (`lotline.parse.permit_text`) names an ADU on a
  residential building or accessory-structure permit → `ADU`, 1 unit, `inferred` (type and units), with the
  parser's attached / detached / conversion type. "Studio", "living quarters", "guest house" and similar
  words are not read as ADUs (precision over recall);
- remodels and additions: 0 units (`derived`) unless the parser reads a conversion that adds units
  (`inferred`); a whole-building demolition the parser reads sets `is_demolition` and its `units_removed`;
- a `Units` value above `MAX_UNITS` (job values and square feet typed into the field) is read as missing;
- a use not in the crosswalk: the parser's type and count if it reads one (`inferred`), else unknown.

**Repeated project totals.** Some apartment projects put the project's total on every building's permit
(2024: seven permits each with 404 units). D-008 counts such totals once only for permits on the same
parcel, and this table has no parcel number, so the rule cannot apply yet (issue #221): 5+ unit counts run
above BPS in some years (see limitations). 1-unit counts match BPS within 10% in every year 2002–2025.

**Demolitions** are filed as separate permits that this table does not hold (no demolition permit type;
only remodels that mention one), so `units_removed` is mostly missing.

**Jurisdiction.** Every row is Fort Worth (4827000): Texas cities issue building permits only inside their
limits (not in the extraterritorial jurisdiction), so a permit's address was inside the city when it was
filed, whatever was annexed later.

**Other fields.** `permit_id` = `Permit_No`; `permit_class_raw` = type | subtype | use | specific use;
`valuation_usd` = `JobValue`; `floor_area_sqft` = `SqFt`. There is no parcel number (`parcel_id` null).

**Privacy.** The table also holds owner names, site addresses, legal descriptions (lot, block, tract) and
coordinates; none of them are requested (`OUT_FIELDS`). The work description is requested only for the
parser, read in memory and never kept.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd

from lotline.config import CONFIG_DIR
from lotline.io import DataStore
from lotline.io.arcgis import epoch_ms_to_timestamp
from lotline.parse.permit_text import parse_description
from lotline.schemas import validate

ADAPTER = "states.tx.fw_permits"
VERSION = "1.0"
SOURCE = "fw_permits"
TABLE = "permits"
LAYER_URL = (
    "https://services5.arcgis.com/3ddLCBXe1bRt7mzj/arcgis/rest/services/"
    "CFW_Open_Data_Development_Permits_View/FeatureServer/0"
)
LANDING_URL = "https://data.fortworthtexas.gov/"
LICENSE = "CC-BY 4.0 (City of Fort Worth open data)"
FORT_WORTH = "4827000"
USE_CSV = CONFIG_DIR / "crosswalks" / "tx_fw_use.csv"

RESIDENTIAL = "Residential Building Permit"
ACCESSORY = "Residential Accessory Struct"
COMMERCIAL = "Commercial Building Permit"
WHERE = (
    f"Permit_Type IN ('{RESIDENTIAL}', '{ACCESSORY}') "
    f"OR (Permit_Type = '{COMMERCIAL}' AND Use_Type = 'Residential')"
)
OUT_FIELDS = [
    "ObjectId",
    "Permit_No",
    "Permit_Type",
    "Permit_SubType",
    "Use_Type",
    "Specific_Use",
    "Units",
    "SqFt",
    "JobValue",
    "File_Date",
    "Current_Status",
    "Status_Date",
    "B1_WORK_DESC",  # parser input only, never kept
]
PERSONAL = {
    "Owner_Full_Name", "Addr_No", "Direction", "Street_Name", "Street_Suffix", "Street_Suffix_Dir",
    "Full_Street_Address", "Zip_Code", "B1_LOT", "B1_BLOCK", "B1_TRACT", "B1_LEGAL_DESC", "Location_1",
    "B1_SPECIAL_TEXT",
}  # fmt: skip
ISSUED = {"Issued", "Issued Without Contractor", "Finaled"}
EXPIRED = "Expired"
FINALED = "Finaled"
NO_DATE_BEFORE = pd.Timestamp("1901-01-01")  # the table writes 1900-01-01 for "no date"
MAX_UNITS = 1000  # larger Units values are job values or square feet typed into the field
FITS = {"SFD": (1, 1), "TH": (1, 1), "U2": (1, 2)}
ADU_PERMITS = {RESIDENTIAL, ACCESSORY}

PROVENANCE = {
    "title": "City of Fort Worth development permits (Accela, since 2001)",
    "landing_url": LANDING_URL,
    "table": TABLE,
    "cleaning": [
        "Requested: residential building and accessory-structure permits, and commercial building permits "
        "with a residential use; trade, backflow, forestry, grading, design-review and non-residential "
        "commercial permits are not",
        "Requested fields exclude owner names, site addresses, legal descriptions and coordinates; the work "
        "description is read only by the description parser and never kept",
        "Status snapshots collapsed to one row per Permit_No (units counted once, D-008); kept if any row is "
        "Issued / Issued Without Contractor / Finaled or the latest status is Expired",
        "issue_year = filing year (no issue date in the source; date_precision year); application_date = "
        "File_Date; final_date = date of the Finaled status",
        "building_type_std and units from the use (config/crosswalks/tx_fw_use.csv); Units when it fits the "
        "type (reported), else the type's count (derived); apartment buildings only from a Units of 2 or "
        "more; Units above 1,000 read as missing",
        "ADU when the description parser names one on a residential building or accessory-structure permit "
        "(inferred)",
        "jurisdiction_geoid = Fort Worth (4827000) for every row; valuation_usd = JobValue; "
        "floor_area_sqft = SqFt",
    ],
    "limitations": [
        "No issue date: permits are dated by filing year, a few weeks before issue",
        "Demolition permits are not in the table: units_removed is mostly missing",
        "ADUs only where the description names one ('ADU', 'accessory dwelling'); the source's 'Accessory "
        "Dwelling' use also holds storm shelters and game rooms and is not used on its own. Fort Worth "
        "allows accessory dwellings in one-family districts only when not rented (TX-4827000-adu-2010), so "
        "these are non-rental units",
        "No parcel number; permits cannot be joined to parcels",
        "Duplex permits with Units 1 are read as one permit per half of the building",
        "5+ unit homes run above BPS in some years (2.6x in 2020, 2023 and 2024): some projects repeat the "
        "project total on every building's permit, and with no parcel number the D-008 rule cannot group "
        "them (issue #221); 2022's excess (1.8x) has another cause, not yet found",
    ],
}


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def uses(path: Path = USE_CSV) -> dict[tuple[str, str], dict[str, str]]:
    """(permit type, use in lower case) → crosswalk row; use "*" covers every use of that permit type."""
    return {(r["permit_type"], r["use"].casefold()): r for r in _read_csv(path)}


def _clean(s: pd.Series) -> pd.Series:
    return s.astype("string").str.strip().fillna("")


def _units(s: pd.Series) -> pd.Series:
    n = pd.to_numeric(_clean(s), errors="coerce")
    return n.where((n >= 0) & (n <= MAX_UNITS) & (n == n.round()))


def _date(s: pd.Series) -> pd.Series:
    d = epoch_ms_to_timestamp(s).dt.normalize()
    return d.where(d >= NO_DATE_BEFORE)


def _fits(t: str, n: object) -> bool:
    if t not in FITS or n is None or pd.isna(n):
        return False
    lo, hi = FITS[t]
    return lo <= n <= hi


def multi_type(n: object) -> str | None:
    """Building type from a unit count of 2 or more (Census size classes), else None."""
    if n is None or pd.isna(n) or n < 2:
        return None
    return "U2" if n == 2 else "U3_4" if n <= 4 else "MF5"


def collapse(raw: pd.DataFrame) -> pd.DataFrame:
    """Status snapshots → one row per permit: latest use and units, latest status, filing and final dates."""
    df = raw.copy()
    df["permit_id"] = _clean(df["Permit_No"])
    df = df.loc[df["permit_id"] != ""]
    df["status"] = _clean(df["Current_Status"])
    df["status_date"] = _date(df["Status_Date"])
    df["file_date"] = _date(df["File_Date"])
    df["n"] = _units(df["Units"])
    df["use_type"] = _clean(df["Use_Type"])
    df["specific"] = _clean(df["Specific_Use"])
    df = df.sort_values(["permit_id", "status_date", "ObjectId"], na_position="first")
    g = df.groupby("permit_id", sort=False)
    out = g.last()[["Permit_Type", "Permit_SubType", "SqFt", "JobValue", "B1_WORK_DESC"]]
    out["status"] = g["status"].last()
    with_use = df.loc[df["use_type"] != ""].groupby("permit_id")
    out["use_type"] = with_use["use_type"].last().reindex(out.index).fillna("")
    out["specific"] = with_use["specific"].last().reindex(out.index).fillna("")
    out["n"] = with_use["n"].last().reindex(out.index).fillna(g["n"].max())
    out["file_date"] = g["file_date"].min()
    finaled = df.loc[df["status"] == FINALED].groupby("permit_id")["status_date"].max()
    out["final_date"] = finaled.reindex(out.index)
    issued = df.loc[df["status"].isin(ISSUED)].groupby("permit_id").size().reindex(out.index).fillna(0) > 0
    keep = issued | (out["status"] == EXPIRED)
    return out.loc[keep].reset_index()


def _use_row(row: pd.Series, xw: dict) -> dict[str, str] | None:
    ptype = row["Permit_Type"]
    use = row["specific"] if ptype == COMMERCIAL else row["use_type"]
    return xw.get((ptype, use.casefold())) or xw.get((ptype, "*"))


def classify(row: pd.Series, xw: dict) -> dict:
    """building_type_std, type_confidence, adu_type, units_new, units_removed, units_confidence, flags."""
    new = row["Permit_SubType"] == "New"
    info = _use_row(row, xw)
    role = info["role"] if info else None
    btype = info["building_type_std"] if info else "UNKNOWN"
    derived = int(info["derived_units"]) if info and info["derived_units"] else None
    n = row["n"]
    text = row["B1_WORK_DESC"] if isinstance(row["B1_WORK_DESC"], str) else ""
    facts = parse_description(text)
    out = dict(adu_type=None, units_new=None, units_removed=None, units_confidence="unknown",
               is_demolition=bool(facts.is_demolition), is_conversion=facts.is_conversion)  # fmt: skip
    conf = "high" if info else "unknown"
    if facts.building_type_std == "ADU" and row["Permit_Type"] in ADU_PERMITS and not facts.is_demolition:
        out.update(adu_type=facts.adu_type or "unknown", units_new=1, units_removed=0)
        return dict(out, building_type_std="ADU", type_confidence="inferred", units_confidence="inferred")
    if facts.is_demolition:
        out.update(units_new=0, units_removed=facts.units_removed,
                   units_confidence="inferred" if facts.units_removed is not None else "unknown")  # fmt: skip
        return dict(out, building_type_std=facts.building_type_std or btype, type_confidence="inferred")
    if role in ("multi", "multi_detached"):
        mt = multi_type(n)
        if mt is None and role == "multi_detached" and pd.notna(n) and n == 1:
            mt = "SFD"
        btype, conf = (mt, "high") if mt else ("UNKNOWN", "unknown")
    if not new:
        if facts.is_conversion and facts.units_new:
            out.update(
                units_new=facts.units_new, units_removed=facts.units_removed, units_confidence="inferred"
            )
        elif role is not None:
            out.update(units_new=0, units_removed=0, units_confidence="derived")
        return dict(out, building_type_std=btype, type_confidence=conf)
    out["units_removed"] = 0
    if role == "dwelling":
        ok = _fits(btype, n)
        out.update(units_new=int(n) if ok else derived, units_confidence="reported" if ok else "derived")
    elif role in ("multi", "multi_detached") and btype != "UNKNOWN":
        out.update(units_new=int(n), units_confidence="reported")
    elif role in ("foundation", "accessory", "nonresidential"):
        out.update(units_new=0, units_confidence="derived")
    elif role is None and facts.building_type_std and facts.units_new:
        out.update(units_new=facts.units_new, units_confidence="inferred")
        return dict(out, building_type_std=facts.building_type_std, type_confidence="inferred")
    return dict(out, building_type_std=btype, type_confidence=conf)


def build(raw: pd.DataFrame, state: str = "TX") -> pd.DataFrame:
    """Raw table attributes → `permits` rows."""
    df = collapse(raw)
    df = df.loc[df["file_date"].notna()].reset_index(drop=True)
    xw = uses()
    facts = pd.DataFrame([classify(r, xw) for _, r in df.iterrows()], index=df.index)
    final = df["final_date"]
    parts = [df["Permit_Type"], df["Permit_SubType"], df["use_type"], df["specific"]]
    out = pd.DataFrame(
        {
            "state": state,
            "permit_id": df["permit_id"].astype("string"),
            "parcel_id": pd.Series(pd.NA, index=df.index, dtype="string"),
            "jurisdiction_geoid": FORT_WORTH,
            "issue_year": df["file_date"].dt.year.astype("Int64"),
            "issue_date": pd.Series(pd.NaT, index=df.index, dtype="datetime64[ns]"),
            "date_precision": "year",
            "application_date": df["file_date"],
            "final_date": final,
            "final_date_type": pd.Series(pd.NA, index=df.index, dtype="string").mask(
                final.notna(), "final_inspection"
            ),
            "permit_class_raw": pd.Series(
                [" | ".join(map(str, p)) for p in zip(*parts, strict=True)], index=df.index
            ),
            "valuation_usd": pd.to_numeric(_clean(df["JobValue"]), errors="coerce").where(lambda v: v >= 0),
            "floor_area_sqft": pd.to_numeric(_clean(df["SqFt"]), errors="coerce").where(lambda v: v > 0),
            "source": SOURCE,
        }
    )
    for col in ["building_type_std", "type_confidence", "adu_type", "units_confidence"]:
        out[col] = facts[col].astype("string")
    for col in ["units_new", "units_removed"]:
        out[col] = pd.array(facts[col], dtype="Int64")
    for col in ["is_demolition", "is_conversion"]:
        out[col] = pd.array(facts[col], dtype="boolean")
    return out


def download(store: DataStore, *, refresh: bool = False) -> pd.DataFrame:
    from lotline.io.arcgis import download_layer

    return download_layer(
        LAYER_URL,
        store=store,
        source=SOURCE,
        license=LICENSE,
        adapter=ADAPTER,
        adapter_version=VERSION,
        name="permits",
        where=WHERE,
        out_fields=",".join(OUT_FIELDS),
        geometry=False,
        refresh=refresh,
    )


def load(state: str, store: DataStore, *, refresh: bool = False) -> pd.DataFrame:
    if state.upper() != "TX":
        raise ValueError(f"{SOURCE} covers Fort Worth, Texas only, not {state}")
    return validate(build(download(store, refresh=refresh), state=state), TABLE)
