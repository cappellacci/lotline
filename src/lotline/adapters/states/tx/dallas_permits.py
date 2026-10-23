"""City of Dallas building permits, 1971 to 2024-11 ("New Permits 1971-2024") → canonical `permits`.

The City's Planning and Development Department pulled every permit from its POSSE system in November 2024,
when the City moved to a new permitting system (DallasNow), and published the extract as a point layer,
`NewPermit_2008_2024` on ArcGIS Online (public; no license stated; "no updates planned"). 1,798,425 permits
created 1971-2024: permit type, activity (new construction, addition, alteration ...), land use, a unit count
(`UNITS`), base zoning, created and issue dates, value, floor area, status at extraction, and a free-text
work description. Dallas has no by-right ADU (`config/reforms/tx.csv`, TX-4819000-adu-2018), so its permits
give the ADU estimate (D-025) a large Texas comparison city, and BPS a 2-4 unit check.

**Rows requested** (`WHERE`): building permits (`Building (BU)`) for new construction and additions that are
single-family or multifamily, or have a dwelling land use. Trade, sign, fence, pool and other permits, and
alterations, are not requested.

**Rows kept:** status at extraction Complete, Issued or Expired (an issued permit that lapsed, as BPS counts
it), with an issue date. Cancelled, Revoked and "Other" (New, Approved, In Review, Rejected ... applications
never issued) are dropped. One row per permit number (the latest issued, if a number repeats).

**Building type and units** (`config/crosswalks/tx_dallas_land_use.csv`, one row per land use; the source
pads land uses with a leading space):

- `dwelling` land uses on new construction (single-family SFD, two-family U2): `UNITS` when it fits the type
  (SFD 1; duplex 1-2) → `reported`; else the type's count (`derived`). Many 1975-1982 house permits carry 10
  or 20 units (old coding), read as not fitting;
- `multi` (multi-family dwelling) on new construction: a `UNITS` of 2 or more gives the type (2 U2, 3-4 U3_4,
  5+ MF5) and the count (`reported`); otherwise type and units unknown;
- **accessory dwelling units:** the description parser (`lotline.parse.permit_text`) names an ADU on a
  single-family new-construction or addition permit → `ADU`, 1 unit, `inferred`;
- additions: 0 units (`derived`) unless the parser reads a conversion that adds units (`inferred`);
- other land uses: the parser's type and count if it reads one (`inferred`), else unknown.

**Repeated project totals.** Some apartment projects put the project's total on every building's permit
(2023: eleven consecutive permits, including the amenity building and site work, each with 471 units). The
table has no parcel number, so D-008 cannot group them yet (issue #221). Against BPS, 1-unit homes are
0.84-1.01 of BPS in 2005-2024, but 5+ unit homes run up to 3.3x (2023) as reported; a same-issue-date
grouping brings most years within 0.86-1.27.

**Coverage in time.** The layer ends 2024-11-12, so 2024 is a part year and **2025 is not in this source**
(the City's later monthly workbooks are not ingested). Demolitions are not in the extract (three rows).

**Jurisdiction.** Every row is Dallas (4819000): Texas cities issue building permits only inside their limits.

**Other fields.** `permit_id` = `PERMIT_No`; `permit_class_raw` = type | activity | land use; `zoning_raw` =
`BASE_ZONING`; `issue_date` = `ISSUE_DATE`; `application_date` = `CREATED_DATE`; `valuation_usd` = `VALUE`;
`floor_area_sqft` = `AREA`. No parcel number and no completion date.

**Privacy.** The layer also holds the address, ZIP code, coordinates (geometry, `XCOORD`, `YCOORD`) and
comments; none of them are requested (`OUT_FIELDS`, no geometry). The work description often holds the
address, so it is requested only for the parser, read in memory and never kept.
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

ADAPTER = "states.tx.dallas_permits"
VERSION = "1.0"
SOURCE = "dallas_permits"
TABLE = "permits"
LAYER_URL = (
    "https://services2.arcgis.com/rwnOSbfKSwyTBcwN/arcgis/rest/services/NewPermit_2008_2024/FeatureServer/0"
)
LANDING_URL = "https://www.arcgis.com/home/search.html?q=NewPermit_2008_2024"
LICENSE = "City of Dallas Planning and Development Department (public ArcGIS item; no license stated)"
DALLAS = "4819000"
LAND_USE_CSV = CONFIG_DIR / "crosswalks" / "tx_dallas_land_use.csv"

BUILDING = "Building (BU)"
NEW = "(A) New Construction"
ADDITION = "(G) Addition"
WHERE = (
    f"PERMIT_TYPE = '{BUILDING}' AND ACTIVITY IN ('{NEW}', '{ADDITION}') "
    "AND (Type IN ('Single Family', 'Multi Family') OR LAND_USE LIKE '%DWELLING%')"
)
OUT_FIELDS = [
    "OBJECTID",
    "PERMIT_No",
    "PERMIT_TYPE",
    "ACTIVITY",
    "CREATED_DATE",
    "ISSUE_DATE",
    "VALUE",
    "AREA",
    "WORK_DESCRIPTION",  # parser input only, never kept
    "LAND_USE",
    "UNITS",
    "BASE_ZONING",
    "Type",
    "Grouped_Status",
]
PERSONAL = {"ADDRESS", "ZIP_CODE", "XCOORD", "YCOORD", "COMMENTS", "COUNCILPER"}
KEEP_STATUS = {"Complete", "Issued", "Expired"}
SINGLE_FAMILY = "SINGLE FAMILY DWELLING"
FITS = {"SFD": (1, 1), "U2": (1, 2)}

PROVENANCE = {
    "title": "City of Dallas building permits 1971-2024 (POSSE extract, Planning and Development)",
    "landing_url": LANDING_URL,
    "table": TABLE,
    "cleaning": [
        "Requested: building permits for new construction and additions that are single-family, multifamily "
        "or have a dwelling land use",
        "Requested fields exclude the address, ZIP code, coordinates and comments; the work description is "
        "read only by the description parser and never kept",
        "Kept: status Complete, Issued or Expired with an issue date; one row per permit number",
        "building_type_std and units from the land use (config/crosswalks/tx_dallas_land_use.csv); UNITS "
        "when it fits the type (reported), else the type's count (derived); multifamily only from a UNITS of "
        "2 or more",
        "ADU when the description parser names one on a single-family new-construction or addition permit "
        "(inferred); additions 0 units unless the parser reads a conversion",
        "jurisdiction_geoid = Dallas (4819000); zoning_raw = BASE_ZONING; issue_date = ISSUE_DATE; "
        "application_date = CREATED_DATE; valuation_usd = VALUE; floor_area_sqft = AREA",
    ],
    "limitations": [
        "Ends 2024-11-12 (the move to DallasNow): 2024 is a part year and 2025 is not covered",
        "Some apartment projects repeat the project total on every building's permit, and with no parcel "
        "number the D-008 rule cannot group them (issue #221)",
        "No parcel number, no completion date, no demolitions",
        "Many 1975-1982 house permits carry UNITS of 10 or 20; houses are counted as one unit each",
        "ADUs only where the description names one; Dallas allows rentable ADUs only by special exception or "
        "overlay (TX-4819000-adu-2018)",
    ],
}


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def land_uses(path: Path = LAND_USE_CSV) -> dict[str, dict[str, str]]:
    return {r["land_use"]: r for r in _read_csv(path)}


def _clean(s: pd.Series) -> pd.Series:
    return s.astype("string").str.strip().fillna("")


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


def classify(row: pd.Series, xw: dict[str, dict[str, str]]) -> dict:
    """building_type_std, type_confidence, adu_type, units_new, units_removed, units_confidence, flags."""
    new = row["activity"] == NEW
    info = xw.get(row["land_use"])
    role = info["role"] if info else None
    btype = info["building_type_std"] if info else "UNKNOWN"
    derived = int(info["derived_units"]) if info and info["derived_units"] else None
    n = row["n"]
    text = row["WORK_DESCRIPTION"] if isinstance(row["WORK_DESCRIPTION"], str) else ""
    facts = parse_description(text)
    out = dict(adu_type=None, units_new=None, units_removed=None, units_confidence="unknown",
               is_demolition=False, is_conversion=facts.is_conversion)  # fmt: skip
    conf = "high" if info else "unknown"
    single = row["land_use"] == SINGLE_FAMILY or row["ptype"] == "Single Family"
    if facts.building_type_std == "ADU" and single and not facts.is_demolition:
        out.update(adu_type=facts.adu_type or "unknown", units_new=1, units_removed=0)
        return dict(out, building_type_std="ADU", type_confidence="inferred", units_confidence="inferred")
    if role == "multi":
        mt = multi_type(n)
        btype, conf = (mt, "high") if mt else ("UNKNOWN", "unknown")
    if not new:
        if facts.is_conversion and facts.units_new:
            out.update(
                units_new=facts.units_new, units_removed=facts.units_removed, units_confidence="inferred"
            )
        else:
            out.update(units_new=0, units_removed=0, units_confidence="derived")
        return dict(out, building_type_std=btype, type_confidence=conf)
    out["units_removed"] = 0
    if role == "dwelling":
        ok = _fits(btype, n)
        out.update(units_new=int(n) if ok else derived, units_confidence="reported" if ok else "derived")
    elif role == "multi" and btype != "UNKNOWN":
        out.update(units_new=int(n), units_confidence="reported")
    elif role is None and facts.building_type_std and facts.units_new:
        out.update(units_new=facts.units_new, units_confidence="inferred")
        return dict(out, building_type_std=facts.building_type_std, type_confidence="inferred")
    return dict(out, building_type_std=btype, type_confidence=conf)


def build(raw: pd.DataFrame, state: str = "TX") -> pd.DataFrame:
    """Raw layer attributes → `permits` rows."""
    df = raw.copy()
    df["issue_date"] = epoch_ms_to_timestamp(df["ISSUE_DATE"]).dt.normalize()
    df["permit_id"] = pd.to_numeric(df["PERMIT_No"], errors="coerce").astype("Int64").astype("string")
    df["status"] = _clean(df["Grouped_Status"])
    df = df.loc[df["status"].isin(KEEP_STATUS) & df["issue_date"].notna() & df["permit_id"].notna()].copy()
    df = df.sort_values(["permit_id", "issue_date", "OBJECTID"]).drop_duplicates("permit_id", keep="last")
    df = df.reset_index(drop=True)
    df["activity"] = _clean(df["ACTIVITY"])
    df["land_use"] = _clean(df["LAND_USE"])
    df["ptype"] = _clean(df["Type"])
    df["n"] = pd.to_numeric(df["UNITS"], errors="coerce")
    xw = land_uses()
    facts = pd.DataFrame([classify(r, xw) for _, r in df.iterrows()], index=df.index)
    parts = [_clean(df["PERMIT_TYPE"]), df["activity"], df["land_use"]]
    out = pd.DataFrame(
        {
            "state": state,
            "permit_id": df["permit_id"],
            "parcel_id": pd.Series(pd.NA, index=df.index, dtype="string"),
            "jurisdiction_geoid": DALLAS,
            "issue_year": df["issue_date"].dt.year.astype("Int64"),
            "issue_date": df["issue_date"],
            "date_precision": "day",
            "application_date": epoch_ms_to_timestamp(df["CREATED_DATE"]).dt.normalize(),
            "permit_class_raw": parts[0] + " | " + parts[1] + " | " + parts[2],
            "zoning_raw": _clean(df["BASE_ZONING"]).replace("", pd.NA),
            "valuation_usd": pd.to_numeric(df["VALUE"], errors="coerce").where(lambda v: v >= 0),
            "floor_area_sqft": pd.to_numeric(df["AREA"], errors="coerce").where(lambda v: v > 0),
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
        raise ValueError(f"{SOURCE} covers Dallas, Texas only, not {state}")
    return validate(build(download(store, refresh=refresh), state=state), TABLE)
