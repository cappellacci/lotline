"""City of Asheville building permits (Accela, November 2013 to the present) → canonical `permits`.

Asheville publishes every record in its Accela permitting system as one map-service layer ("Accela Permits
View", refreshed nightly; Hub item "City of Asheville Permit Inspections", Open Data Commons PDDL 1.0). One
row per record: building, trade, sign, fire, event and other permits. Only `record_module = 'Permits'`
records of type Residential or Commercial are requested. The record type has three levels:
`record_type_type` (Residential / Commercial), `record_type_subtype` (New Building, Existing Building,
Accessory Structure, Trade, Demolition ...) and `record_type_category` (SFD, Duplex, Townhome, ADU
Detached, ADU Attached, Multi-Family, Alterations ...). Asheville (place 3702140) has
permitted ADUs by right in its single-family districts since at least 2015
(`config/reforms/nc.csv`), so its permits add a mountain-region city to the ADU estimate (D-025).

**Dates.** The layer has no issue date. `issue_year` is the year the record was opened (`date_opened`, the
application date, also stored as `application_date`); `issue_date` is left null and `date_precision` is
"year". Records whose status shows they were never issued (in review, denied, revoked ...; `NOT_ISSUED`)
are dropped; expired permits stay (they were issued).

**Building type and units** (`classify`):

- **ADUs, from the city's own type** (categories "ADU Detached" under New Building and "ADU Attached" under
  Existing Building, used from 2022): `ADU`, type `high`, 1 unit `derived`; detached / attached (an
  attached ADU the description calls a basement or interior conversion is `internal_conversion`);
- **ADUs, from the description** (`lotline.parse.permit_text`, before the city's ADU categories and for
  ADUs filed under another category): the parser names an ADU on a building permit for a house, an
  accessory structure, an alteration, an addition or a remodel (`ADU_TEXT_CATEGORIES`) → `ADU`, 1 unit,
  `inferred`. Trade, site-work, deck, demolition, duplex, townhouse and commercial permits are never read
  as ADUs: they are the companion permits of a dwelling counted elsewhere. Text about an ADU that already
  exists or is going away ("under the existing ADU", "where the ADU was", "from a permitted ADU",
  `EXISTING_ADU`) is not a new ADU. A house permit whose text also
  builds the new house ("new single family residence ... with ADU") stays a house (1 unit) and carries
  `reform_flag_raw = "adu_text_with_new_house"`: one row cannot hold two building types;
- new houses (SFD, SFD Waiver, Modular SFD) `SFD` 1 unit; townhouses `TH` 1 unit (one permit per home);
  manufactured homes `OTHER` 1 unit; all `derived`;
- duplexes (Duplex, Modular Duplex) `U2`: 1 unit when the text says the permit is one half, side or unit
  of the building, else 2 (`derived`);
- multifamily (Commercial New Building "Multi-Family") and the 2014-2016 "New" records (no category):
  the parser's building type and count when it reads one (`inferred`; never an ADU on a commercial
  permit), else unknown;
- other commercial new buildings (shells, tenants, upfits) `OTHER` 0 units; demolitions 0 new units and
  the parser's count removed, else unknown (a demolished ADU is never typed `ADU`, so ADU rows only
  add); every other permit (alterations, additions, accessory, trade, site work, signs) 0 units
  (`derived`) unless the parser reads a conversion that adds units (`inferred`).

**Jurisdiction.** Every row is Asheville (3702140): the city issues permits inside its limits only
(Buncombe County Permits & Inspections covers the rest of the county).

**Other fields.** `permit_id` = `record_id`; `permit_class_raw` = `record_type`, then the three type
levels; `reform_flag_raw` = the ADU category, or "adu_text_with_new_house"; `valuation_usd` = `job_value`.
No parcel number: `parcel_number` is a city-internal key (4-6 digits), not the Buncombe County PIN, so
`parcel_id` stays null.

**Privacy.** The layer also holds the site address, the project name, the contractor's business name and
license number, and staff comments; none of them are requested (`OUT_FIELDS`). The description often
names the owner ("... FOR <name>"), so it is requested only for the parser, read in memory and never kept.
"""

from __future__ import annotations

import re

import pandas as pd

from lotline.io import DataStore
from lotline.io.arcgis import epoch_ms_to_timestamp
from lotline.parse.permit_text import parse_description
from lotline.schemas import validate

ADAPTER = "states.nc.asheville_permits"
VERSION = "1.0"
SOURCE = "asheville_permits"
TABLE = "permits"
LAYER_URL = "https://gis.ashevillenc.gov/server/rest/services/Permits/AccelaPermitsView/FeatureServer/2"
LANDING_URL = "https://www.arcgis.com/home/item.html?id=b8fdb63db30b42d0875afb617e1551f4"
LICENSE = "Open Data Commons Public Domain Dedication and License (PDDL) 1.0 (City of Asheville Hub item)"
ASHEVILLE = "3702140"
WHERE = "record_module = 'Permits' AND record_type_type IN ('Residential', 'Commercial')"

OUT_FIELDS = [
    "objectid",
    "record_id",
    "date_opened",
    "record_status",
    "status",
    "record_type",
    "record_type_type",
    "record_type_subtype",
    "record_type_category",
    "job_value",
    "description",  # parser input only, never kept
]
PERSONAL = {
    "address", "record_name", "business_name", "license_number", "record_comments", "short_notes",
}  # fmt: skip

NOT_ISSUED = {
    "Application Received", "Application Incomplete", "Application Complete", "Submittal Required",
    "Plan Check", "In Review", "Pending", "Pending Applicant Action", "Pending Payment",
    "Pending Bldg Permits", "Permit Verification", "Denied", "Disapproved", "Revoked", "DISABLED",
}  # fmt: skip
ADU_CATEGORIES = {"ADU Detached": "detached", "ADU Attached": "attached"}
SFD_CATEGORIES = {"SFD", "SFD Waiver", "Modular SFD"}
DUPLEX_CATEGORIES = {"Duplex", "Modular Duplex"}
# (record_type_subtype, record_type_category) of Residential permits whose description may name an ADU.
ADU_TEXT_CATEGORIES = {
    ("New Building", "SFD"), ("New Building", "SFD Waiver"), ("New Building", "Modular SFD"), ("New", "NA"),
    ("Accessory Structure", "Other"), ("Accessory Structure", "NA"), ("Existing Building", "Alterations"),
    ("Existing Building", "Alterations w Addition"), ("Existing Building", "Addition"), ("Remodel", "NA"),
    ("Addition", "NA"),
}  # fmt: skip
# The text of a house permit that also builds the house itself (not an ADU behind an existing one).
NEW_HOUSE = re.compile(
    r"\b(?:NEW\s+)?(?:SINGLE[\s-]+FAMILY\s+(?:RESIDENCE|HOME|DWELLING|HOUSE|CONSTRUCTION)|SFR|SFD)\b", re.I
)
EXISTING_HOUSE = re.compile(
    r"\b(?:EXISTING|BEHIND|PRIMARY)\b[^.]{0,25}\b(?:SINGLE|SFR|SFD|HOUSE|HOME|RESIDENCE)", re.I
)
# Work on an ADU that already exists (or is being removed), not a new one: "beneath an existing partially
# finished ADU", "garage where the ADU was", "change of use from a permitted ADU", "turn existing ADU into".
_ADU_WORD = r"(?:ADU|ACCESSORY\s+DWELLING|ACCESSORY\s+APARTMENT)"
EXISTING_ADU = re.compile(
    rf"\b(?:EXISTING|PERMITTED|FORMER|CURRENT)\s+"
    rf"(?:(?!INTO\b|TO\b|AS\b|AND\b|WITH\b)[\w-]+\s+){{0,3}}{_ADU_WORD}"
    rf"|\b{_ADU_WORD}\s+WAS\b|\bFROM\s+(?:AN?\s+)?(?:PERMITTED\s+)?{_ADU_WORD}",
    re.I,
)
HALF = re.compile(r"\b(?:HALF|LEFT\s+SIDE|RIGHT\s+SIDE|UNIT\s+[12AB]\b|SIDE\s+[12AB]\b)", re.I)
DWELLINGS = {"SFD": (1, 1), "ADU": (1, 1), "TH": (1, 1), "OTHER": (1, 1), "U2": (1, 2), "U3_4": (3, 4)}

PROVENANCE = {
    "title": "City of Asheville building permits (Accela Permits View, November 2013 to present)",
    "landing_url": LANDING_URL,
    "table": TABLE,
    "cleaning": [
        "Requested: record_module 'Permits' of type Residential or Commercial; fields exclude the site "
        "address, project name, contractor business name and license number and staff comments; the "
        "description is read only by the description parser and never kept",
        "Records never issued (in review, denied, revoked ...) are dropped; expired permits are kept",
        "issue_year = year of date_opened (the application date, also application_date); issue_date null",
        "ADU from the city's categories 'ADU Detached' / 'ADU Attached' (from 2022, type high), else when "
        "the description parser names one on a house, accessory, alteration, addition or remodel permit "
        "(inferred); a house permit that also builds the house stays SFD (reform_flag_raw "
        "'adu_text_with_new_house')",
        "SFD, townhouse and manufactured-home permits 1 unit; duplexes 2, or 1 for a half; multifamily and "
        "2014-2016 'New' records from the description parser (inferred), else unknown; other permits 0",
        "jurisdiction_geoid = Asheville (3702140) for every row; valuation_usd = job_value",
    ],
    "limitations": [
        "No issue date: years are application years, a few weeks before issue",
        "The city's ADU categories start in 2022; earlier ADUs are counted only where the description names "
        "one, and the parser finds about two in three of the 2022-2026 ADUs the city flags "
        "(reports/nc/asheville-adu-scout.md), so pre-2022 ADU counts are low",
        "No county PIN: parcel_number is a city-internal key, so permits cannot be joined to parcels",
        "Multifamily units only where the description states a count",
        "Records start with the Accela launch in November 2013 (2014 is the first full year)",
    ],
}


def _clean(s: pd.Series) -> pd.Series:
    return s.astype("string").str.strip().fillna("")


def _fits(btype: str | None, n: int | None) -> bool:
    """True when the parser's count n fits its building type (MF5: 5 or more)."""
    if n is None:
        return False
    if btype == "MF5":
        return n >= 5
    if btype not in DWELLINGS:
        return False
    lo, hi = DWELLINGS[btype]
    return lo <= n <= hi


def classify(row: pd.Series) -> dict:
    """building_type_std, type_confidence, adu_type, units_new, units_removed, units_confidence, flags."""
    kind, sub, cat = row["kind"], row["sub"], row["cat"]
    text = row["description"] if isinstance(row["description"], str) else ""
    facts = parse_description(text)
    out = dict(adu_type=None, units_new=0, units_removed=0, units_confidence="derived", flag=None,
               building_type_std="OTHER" if kind == "Commercial" else "UNKNOWN", type_confidence="high",
               is_demolition=sub == "Demolition", is_conversion=bool(facts.is_conversion))  # fmt: skip
    if kind == "Residential" and cat in ADU_CATEGORIES:
        adu = "internal_conversion" if facts.adu_type == "internal_conversion" else ADU_CATEGORIES[cat]
        return dict(out, building_type_std="ADU", adu_type=adu, units_new=1, flag=cat)
    text_adu = facts.building_type_std == "ADU" and not facts.is_demolition and not EXISTING_ADU.search(text)
    if kind == "Residential" and text_adu and (sub, cat) in ADU_TEXT_CATEGORIES:
        if cat in SFD_CATEGORIES and NEW_HOUSE.search(text) and not EXISTING_HOUSE.search(text):
            return dict(out, building_type_std="SFD", units_new=1, flag="adu_text_with_new_house")
        adu = facts.adu_type or "unknown"
        return dict(out, building_type_std="ADU", adu_type=adu, units_new=1, type_confidence="inferred",
                    units_confidence="inferred")  # fmt: skip
    if sub == "Demolition":
        known = facts.units_removed is not None
        btype = facts.building_type_std if facts.building_type_std != "ADU" else None  # ADU rows add homes
        return dict(out, building_type_std=btype or out["building_type_std"],
                    type_confidence="inferred" if btype else "unknown", units_removed=facts.units_removed,
                    units_confidence="inferred" if known else "unknown")  # fmt: skip
    if kind == "Residential" and sub == "New Building" and cat in SFD_CATEGORIES:
        return dict(out, building_type_std="SFD", units_new=1)
    if kind == "Residential" and sub == "New Building" and cat == "Townhome":
        return dict(out, building_type_std="TH", units_new=1)
    if kind == "Residential" and sub == "New Building" and cat in DUPLEX_CATEGORIES:
        return dict(out, building_type_std="U2", units_new=1 if HALF.search(text) else 2)
    if kind == "Residential" and sub == "Manufactured Home":
        return dict(out, building_type_std="OTHER", units_new=1)
    if (sub, cat) in {("New Building", "Multi-Family"), ("New", "NA")}:
        t, n = facts.building_type_std, facts.units_new
        if _fits(t, n) and not (t == "ADU" and kind == "Commercial"):  # "residential building 8" is no ADU
            return dict(out, building_type_std=t, type_confidence="inferred", units_new=n,
                        units_confidence="inferred", adu_type=facts.adu_type)  # fmt: skip
        return dict(out, building_type_std="UNKNOWN", type_confidence="unknown", units_new=None,
                    units_confidence="unknown")  # fmt: skip
    if facts.is_conversion and facts.units_new:
        return dict(out, units_new=facts.units_new, units_removed=facts.units_removed or 0,
                    units_confidence="inferred")  # fmt: skip
    return out


def build(raw: pd.DataFrame, state: str = "NC") -> pd.DataFrame:
    """Raw layer attributes → `permits` rows."""
    df = raw.copy()
    df["opened"] = epoch_ms_to_timestamp(df["date_opened"]).dt.normalize()
    status = _clean(df["record_status"]).mask(lambda s: s == "", _clean(df["status"]))
    df = df.loc[df["opened"].notna() & ~status.isin(NOT_ISSUED)].copy()
    df["kind"] = _clean(df["record_type_type"])
    df["sub"] = _clean(df["record_type_subtype"])
    df["cat"] = _clean(df["record_type_category"])
    facts = pd.DataFrame([classify(r) for _, r in df.iterrows()], index=df.index)
    if facts.empty:
        cols = ["building_type_std", "type_confidence", "adu_type", "units_confidence", "units_new",
                "units_removed", "is_demolition", "is_conversion", "flag"]  # fmt: skip
        facts = pd.DataFrame(columns=cols)
    out = pd.DataFrame(
        {
            "state": state,
            "permit_id": _clean(df["record_id"]).replace("", pd.NA),
            "parcel_id": pd.Series(pd.NA, index=df.index, dtype="string"),
            "jurisdiction_geoid": ASHEVILLE,
            "issue_year": df["opened"].dt.year.astype("Int64"),
            "issue_date": pd.Series(pd.NaT, index=df.index, dtype="datetime64[ns]"),
            "date_precision": "year",
            "application_date": df["opened"],
            "permit_class_raw": _clean(df["record_type"])
            + " | "
            + df["kind"]
            + " | "
            + df["sub"]
            + " | "
            + df["cat"],
            "reform_flag_raw": facts["flag"].astype("string"),
            "valuation_usd": pd.to_numeric(df["job_value"], errors="coerce").where(lambda v: v >= 0),
            "source": SOURCE,
        }
    )
    for col in ["building_type_std", "type_confidence", "adu_type", "units_confidence"]:
        out[col] = facts[col].astype("string")
    for col in ["units_new", "units_removed"]:
        out[col] = pd.array(facts[col], dtype="Int64")
    for col in ["is_demolition", "is_conversion"]:
        out[col] = pd.array(facts[col], dtype="boolean")
    out = out.loc[out["permit_id"].notna()]
    return out.drop_duplicates(["state", "permit_id"], keep="last").reset_index(drop=True)


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
    if state.upper() != "NC":
        raise ValueError(f"{SOURCE} covers Asheville, North Carolina only, not {state}")
    return validate(build(download(store, refresh=refresh), state=state), TABLE)
