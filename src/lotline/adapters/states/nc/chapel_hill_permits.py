"""Town of Chapel Hill legacy building permits (LAMA system, 2015-2021) → canonical `permits`.

Chapel Hill's open-data hub publishes the permits from its former permit system, LAMA, as one zipped File
Geodatabase ("LAMA Legacy Permit Data Production", hub item f336a911f4fc424bbe1a53a5e7abb529, uploaded
2024-09-16). It holds every permit created from 2015-05-11 to 2021-05-10 (issued 2015-2021), when the
town moved to an OpenGov portal that has no public export. Permits from mid-2021 on, including everything
after the 2023 Housing Choices amendments, are **not** in this source (see
`reports/nc/chapel-hill-adu-scout.md` for the records request). The file is read with
`lotline.adapters.states.nc.filegdb` (standard library).

Tables read: `LAMA_LegacyPermitData` (one row per permit) and `LAMA_Legacy_PermitPropertyFeatures` (named
values per permit: dwelling units, cost of construction, heated square feet, certificate-of-occupancy date).

**Which rows.** Only `Class == "Building"` (building permits; trade sub-permits and zoning compliance
permits for the same work are left out so a project is counted once). Dropped: deleted records, permits
never issued (no start date `D_Start`) and those closed as Void, Applicant Withdrew Permit or Incomplete
Application. `issue_date` = `D_Start` (the permit's start; `D_Exp` is six months later, NC's expiry rule);
`application_date` = `D_Create`.

**Building type** from `LandUse`, the use of the property (Single Family → SFD, Townhouse → TH, Duplex → U2,
Triplex → U3_4, Mobile Home / Trailer → OTHER, commercial, office, institutional, utility and medical uses →
OTHER; apartments, condominiums, multifamily and mixed use → UNKNOWN because the source gives no building
size), unless the description parser (`lotline.parse.permit_text`) names a type (`inferred`). Such a building
with a reported unit count of 2 or more gets its size class from the count (2 U2, 3-4 U3_4, 5+ MF5).

**Units.** `New Dwelling Units` from the property features when the permit has it (`reported`; a negative
value is read as units removed); else the description parser's count (`inferred`); else 0 for permits on
non-residential uses (`derived`); else unknown. Demolitions (parser) have 0 new units.

**Accessory dwelling units** (on building permits for single-family, accessory-apartment or townhouse
properties, `ADU`, 1 unit, `inferred`). Chapel Hill staff usually write an ADU into an addition or
renovation ("ADDITION - ADU", "Garage with 2 bedroom accessory apartment addition"), which the shared parser
leaves as "unit change unclear". So an ADU is read when the description

1. names one (`ADU`, "accessory dwelling", "accessory apartment", "garage/basement apartment", an apartment
   "above/over/underneath" something, a garage turned "into ... apartment"), and
2. says it is being created: a creation word (new, add, adding, addition, include(s), with, construct, build,
   convert, turn ... into, finish, upfit, "will be") or the description starts with the ADU's name, or the
   shared parser itself reads an ADU, and
3. does not negate it or describe only an existing one ("not ADU", "no new ADU", "prohibited", "remove
   stove", "grandfathered", "existing accessory ...", "renovation/remodel/relocation of ... ADU",
   "convert ... with accessory apartment to SFR", "convert duplex ...": no net new unit).

"Guest house", "in-law suite" and "cottage" are not read as ADUs (precision over recall, as in Greensboro).
A new house permitted together with its ADU ("NEW SINGLE FAMILY RESIDENCE ... with 612 sqft accessory
dwelling unit") is one permit: it is coded as the ADU (1 unit) and the house is not counted. The rule was
checked by hand on a random sample (scout report).

**Jurisdiction.** Every row is Chapel Hill (3711800): the town issues permits inside its planning
jurisdiction (`Project_Jurisdiction` is "Town of Chapel Hill" on every row). The town's extraterritorial
area and the Durham County part of town are both in it; there is no parcel number (`parcel_id` null).

**Privacy.** The tables also hold the site address, the submitter, project names and locations, contractor
names and inspection notes; none of them are read. The description is read only by the ADU rule and the
parser, in memory, and never kept.
"""

from __future__ import annotations

import re
import zipfile
from pathlib import Path

import pandas as pd

from lotline.adapters.states.nc import filegdb
from lotline.io import DataStore
from lotline.parse.permit_text import parse_description
from lotline.schemas import validate

ADAPTER = "states.nc.chapel_hill_permits"
VERSION = "1.0"
SOURCE = "chapel_hill_permits"
TABLE = "permits"
ITEM_ID = "f336a911f4fc424bbe1a53a5e7abb529"
URL = f"https://www.arcgis.com/sharing/rest/content/items/{ITEM_ID}/data"
LANDING_URL = f"https://opendata-townofchapelhill.hub.arcgis.com/content/{ITEM_ID}"
LICENSE = "Town of Chapel Hill open data hub (public record, NCGS 132; no license stated on the item)"
VINTAGE = "2024-09-16"  # the hub item's upload date; the file is a closed legacy extract
FILE_NAME = "LAMA_Legacy_Permit_Data_Production.gdb.zip"
CHAPEL_HILL = "3711800"

PERMIT_TABLE = "LAMA_LegacyPermitData"
FEATURE_TABLE = "LAMA_Legacy_PermitPropertyFeatures"
PERMIT_FIELDS = ["PrmtID", "Num", "Class", "PrmtType", "LandUse", "D_Start", "D_Create", "Deleted",
                 "Exit_Reason", "Descr"]  # fmt: skip  # Descr: ADU rule and parser input only, never kept
FEATURE_FIELDS = ["PrmtID", "Prop", "Val", "NumVal", "DateVal"]
PERSONAL = {"Address", "Submitter", "Project_Name", "Project_Location", "Project_Desc", "repAddress",
            "point_x", "point_y", "ContractorName", "Comment", "UserID"}  # fmt: skip
FEATURES = {
    "New Dwelling Units": "units_new_raw",
    "Cost of Construction": "valuation_usd",
    "New Total Heated Square Footage": "floor_area_sqft",
    "CO Date": "co_date",
}
DROPPED_EXITS = {"Void", "Applicant Withdrew Permit", "Incomplete Application"}
LAND_USE = {
    "Single Family": "SFD", "Accessory Apartment": "SFD", "Townhouse": "TH", "Duplex": "U2",
    "Triplex": "U3_4",
    "Mobile Home": "OTHER", "Trailer": "OTHER",
    "Apartment": "UNKNOWN", "Multifamily": "UNKNOWN", "Condo": "UNKNOWN", "Mixed Use": "UNKNOWN",
    "Commercial Services": "OTHER", "Commercial Office": "OTHER", "Commercial Retail": "OTHER",
    "Institutional": "OTHER", "Utility": "OTHER", "Medical Facility": "OTHER",
}  # fmt: skip
NONRESIDENTIAL = {"Commercial Services", "Commercial Office", "Commercial Retail", "Institutional", "Utility",
                  "Medical Facility"}  # fmt: skip
ADU_LAND_USES = {"Single Family", "Accessory Apartment", "Townhouse"}

# --- the Chapel Hill ADU rule (module docstring, steps 1-3) ---------------------------------------------
_ADU_NOUN = (
    r"(?:\badu\b|\baccessory\s+(?:dwelling|apartment|apt\b)|\b(?:garage|basement)\s+apartment\b"
    r"|\bapartment\s+(?:above|over|underneath|below)\b"
    r"|\binto\s+(?:an?\s+)?(?:new\s+)?(?:[\w-]+\s+){0,4}apartment\b)"
)
ADU_NAMED = re.compile(_ADU_NOUN, re.I)
ADU_FIRST = re.compile(rf"^\W*(?:new\s+)?{_ADU_NOUN}", re.I)
CREATION = re.compile(
    r"\b(?:new|add|adds|adding|added|addition|includ(?:e|es|ing)|with|create[sd]?|creating|construct\w*"
    r"|build\w*|conver(?:t|ts|ting|ted|sion)|turn(?:s|ing)?|finish\w*|upfit|will\s+be)\b",
    re.I,
)
NOT_NEW = re.compile(
    rf"\b(?:not|no(?:\s+new)?|non)[- ]+(?:an?\s+)?{_ADU_NOUN}|\bprohibited\b|\bremove\s+stove\b"
    rf"|\bgrandfathered\b|\bexisting\s+{_ADU_NOUN}"
    rf"|\b(?:renovat\w*|remodel\w*|relocat\w*|repair\w*)\s+(?:[\w()-]+\s+){{0,2}}?(?:of|to)\s+"
    rf"(?:the\s+)?(?:[\w()-]+\s+){{0,6}}?{_ADU_NOUN}"
    r"|\bwith\s+accessory\s+apartment\s+to\s+(?:sfr|sfd|single)|\bconvert\w*\s+(?:an?\s+|the\s+)?duplex\b",
    re.I,
)


def adu_named_new(text: str) -> bool:
    """True when the description names an ADU being created (rule steps 1-3, without the parser)."""
    if not text or not ADU_NAMED.search(text) or NOT_NEW.search(text):
        return False
    return bool(CREATION.search(text) or ADU_FIRST.search(text))


def _str(s: pd.Series) -> pd.Series:
    return s.astype("string").str.strip().replace({"NULL": pd.NA, "": pd.NA})


def _when(s: pd.Series) -> pd.Series:
    return pd.to_datetime(_str(s), format="%m/%d/%y %I:%M %p", errors="coerce")


def features(raw: pd.DataFrame) -> pd.DataFrame:
    """Property features (long) → one row per PrmtID with the named values in `FEATURES`."""
    f = raw.loc[raw["Prop"].isin(FEATURES)].copy()
    f["value"] = pd.to_numeric(_str(f["NumVal"]).fillna(_str(f["Val"])), errors="coerce")
    co = f["Prop"] == "CO Date"
    f.loc[co, "value"] = pd.NA
    wide = f.loc[~co].pivot_table(index="PrmtID", columns="Prop", values="value", aggfunc="last")
    dates = pd.to_datetime(
        _str(f.loc[co, "DateVal"]).fillna(_str(f.loc[co, "Val"])), errors="coerce", format="mixed"
    )
    co_by = dates.groupby(f.loc[co, "PrmtID"]).max()
    out = wide.rename(columns=FEATURES).reindex(columns=[c for c in FEATURES.values() if c != "co_date"])
    return out.join(co_by.rename("co_date"), how="outer")


def classify(land_use: str, text: str) -> dict:
    """building_type_std, type_confidence, adu_type, units_new, units_removed, units_confidence, flags."""
    facts = parse_description(text)
    out = dict(adu_type=None, units_new=None, units_removed=None, units_confidence="unknown",
               is_demolition=bool(facts.is_demolition), is_conversion=bool(facts.is_conversion))  # fmt: skip
    if land_use in ADU_LAND_USES and not facts.is_demolition:
        parser_adu = facts.building_type_std == "ADU" and ADU_NAMED.search(text) and not NOT_NEW.search(text)
        if parser_adu or adu_named_new(text):
            adu_type = facts.adu_type if parser_adu and facts.adu_type else "unknown"
            out.update(adu_type=adu_type, units_new=1, units_removed=0, units_confidence="inferred")
            return dict(out, building_type_std="ADU", type_confidence="inferred")
    btype, conf = LAND_USE.get(land_use, "UNKNOWN"), "high" if land_use in LAND_USE else "unknown"
    if btype == "UNKNOWN":
        conf = "unknown"
    if facts.building_type_std and facts.building_type_std != "ADU":
        btype, conf = facts.building_type_std, "inferred"
    if facts.is_demolition:
        out.update(units_new=0, units_removed=facts.units_removed, units_confidence="inferred")
    elif facts.units_new is not None:
        out.update(units_new=facts.units_new, units_removed=facts.units_removed or 0,
                   units_confidence="inferred")  # fmt: skip
    elif land_use in NONRESIDENTIAL:
        out.update(units_new=0, units_removed=0, units_confidence="derived")
    return dict(out, building_type_std=btype, type_confidence=conf)


def build(permits: pd.DataFrame, feats: pd.DataFrame, state: str = "NC") -> pd.DataFrame:
    """Raw permit rows + property features (`features()`) → `permits` rows."""
    df = permits.copy()
    df["issue_date"] = _when(df["D_Start"]).dt.normalize()
    keep = (
        (_str(df["Class"]) == "Building")
        & (_str(df["Deleted"]).fillna("No") != "Yes")
        & ~_str(df["Exit_Reason"]).isin(DROPPED_EXITS).fillna(False)
        & df["issue_date"].notna()
    )
    df = df.loc[keep].copy()
    df["land_use"] = _str(df["LandUse"]).fillna("")
    df = df.join(feats, on="PrmtID")
    text = _str(df["Descr"]).fillna("")
    facts = pd.DataFrame(
        [classify(lu, t) for lu, t in zip(df["land_use"], text, strict=True)], index=df.index
    )
    reported = pd.to_numeric(df["units_new_raw"], errors="coerce")
    use = reported.notna() & (facts["building_type_std"] != "ADU") & ~facts["is_demolition"].astype(bool)
    facts.loc[use, "units_new"] = reported[use].clip(lower=0)
    facts.loc[use, "units_removed"] = (-reported[use]).clip(lower=0)
    facts.loc[use, "units_confidence"] = "reported"
    sized = use & (facts["building_type_std"] == "UNKNOWN") & (reported >= 2)
    facts.loc[sized, "building_type_std"] = reported[sized].map(
        lambda n: "U2" if n == 2 else "U3_4" if n <= 4 else "MF5"
    )
    facts.loc[sized, "type_confidence"] = "high"
    co = pd.to_datetime(df["co_date"], errors="coerce").dt.normalize()
    out = pd.DataFrame(
        {
            "state": state,
            "permit_id": df["Num"].astype("Int64").astype("string"),
            "parcel_id": pd.Series(pd.NA, index=df.index, dtype="string"),
            "jurisdiction_geoid": CHAPEL_HILL,
            "issue_year": df["issue_date"].dt.year.astype("Int64"),
            "issue_date": df["issue_date"],
            "date_precision": "day",
            "application_date": _when(df["D_Create"]).dt.normalize(),
            "final_date": co,
            "final_date_type": pd.Series(pd.NA, index=df.index, dtype="string").mask(
                co.notna(), "certificate_of_occupancy"
            ),
            "permit_class_raw": _str(df["Class"]).fillna("")
            + " | "
            + _str(df["PrmtType"]).fillna("")
            + " | "
            + df["land_use"],
            "valuation_usd": pd.to_numeric(df["valuation_usd"], errors="coerce").where(lambda v: v >= 0),
            "floor_area_sqft": pd.to_numeric(df["floor_area_sqft"], errors="coerce").where(lambda v: v > 0),
            "source": SOURCE,
        }
    )
    for col in ["building_type_std", "type_confidence", "adu_type", "units_confidence"]:
        out[col] = facts[col].astype("string")
    for col in ["units_new", "units_removed"]:
        out[col] = pd.array(pd.to_numeric(facts[col], errors="coerce"), dtype="Int64")
    for col in ["is_demolition", "is_conversion"]:
        out[col] = pd.array(facts[col], dtype="boolean")
    out = out.loc[out["permit_id"].notna()]
    return out.drop_duplicates(["state", "permit_id"], keep="last").reset_index(drop=True)


def download(store: DataStore, *, refresh: bool = False) -> Path:
    from lotline.io.http import fetch

    return fetch(
        URL,
        store.raw(SOURCE, VINTAGE) / FILE_NAME,
        store=store,
        source=SOURCE,
        license=LICENSE,
        adapter=ADAPTER,
        adapter_version=VERSION,
        refresh=refresh,
    )


def read_file(path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """The zipped geodatabase → (permit rows, property features), reading only the needed columns."""
    extracted = path.parent / "extracted"
    with zipfile.ZipFile(path) as z:
        names = [n for n in z.namelist() if ".gdb/" in n]
        if not names:
            raise FileNotFoundError(f"no .gdb folder in {path}")
        gdb = extracted / names[0].split(".gdb/")[0]
        gdb = gdb.with_name(gdb.name + ".gdb")
        if not gdb.exists():
            for n in names:
                if not (extracted / n).resolve().is_relative_to(extracted.resolve()):
                    raise ValueError(f"unsafe path in {path}: {n}")
            z.extractall(extracted, members=names)
    permits = filegdb.read_table(gdb, PERMIT_TABLE, PERMIT_FIELDS)
    feats = filegdb.read_table(gdb, FEATURE_TABLE, FEATURE_FIELDS)
    return permits, features(feats)


def load(state: str, store: DataStore, *, refresh: bool = False) -> pd.DataFrame:
    if state.upper() != "NC":
        raise ValueError(f"{SOURCE} covers Chapel Hill, North Carolina only, not {state}")
    permits, feats = read_file(download(store, refresh=refresh))
    return validate(build(permits, feats, state=state), TABLE)


PROVENANCE = {
    "title": "Town of Chapel Hill legacy building permits (LAMA system, issued 2015-2021)",
    "landing_url": LANDING_URL,
    "table": TABLE,
    "cleaning": [
        "Read from the zipped File Geodatabase with a standard-library reader (filegdb.py); only the permit "
        "and property-feature tables, and only non-personal columns (no address, submitter, project name or "
        "location); the description is read only by the ADU rule and the parser and never kept",
        "Building-class permits only; deleted, never-issued (no D_Start) and Void / Withdrawn / Incomplete "
        "permits dropped; issue_date = D_Start, application_date = D_Create",
        "building_type_std from LandUse (the property's use) unless the description parser names a type; "
        "units from the New Dwelling Units property feature (reported), else the parser (inferred), else 0 "
        "on non-residential uses (derived), else unknown",
        "ADU (1 unit, inferred) when the description names an ADU being created on a single-family, "
        "accessory-apartment or townhouse property (Chapel Hill rule in the adapter, checked by hand on a "
        "random sample), or the shared parser reads one",
        "jurisdiction_geoid = Chapel Hill (3711800) for every row; valuation_usd = Cost of Construction; "
        "floor_area_sqft = New Total Heated Square Footage; final_date = CO Date",
    ],
    "limitations": [
        "Ends with permits created on 2021-05-10 (the town's switch to OpenGov); nothing after mid-2021, "
        "so the 2023 Housing Choices and 2026 omnibus amendments cannot be observed in this source",
        "2015 starts in May; 2021 holds only January to May",
        "ADUs only where the description names one; 'guest house', 'in-law suite' and 'cottage' are not "
        "counted, and a new house permitted with its ADU is counted as the ADU only",
        "No parcel number; permits cannot be joined to parcels",
        "Units for apartments, condominiums and mixed-use buildings only where New Dwelling Units or the "
        "description gives a count",
    ],
}
