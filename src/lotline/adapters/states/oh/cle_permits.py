"""City of Cleveland building permits (Building & Housing, ArcGIS FeatureServer) → canonical `permits`.

One row per permit, 2015 to the present, refreshed weekly, published under the **ODbL 1.0** (share-alike on
derived databases). Ben approved fetching it at run time on 2026-10-23 (`docs/build/oh-data-plan.md` S7):
the raw snapshot and every derived table stay in `LOTLINE_DATA_DIR`, outside the repo, and are never
committed or published; results cite the source and its license.

**What is downloaded** (server-side `WHERE`): building permits, not trade permits. `PERMIT_TYPE` "Building
Permit" with `PERMIT_CATEGORY` "New" (the city's code for a building permit, whatever the work: about 75,000
of 203,000 permits), plus the 2025-26 "Construction Project" records filed as "Residential Building" or
"Commercial Building". Electrical, plumbing, HVAC, board-up, elevator and amusement-device permits are left
out: they repeat a building project's work.

**Building type and units** come from `JOB_DESCRIPTION` (the work) and `USE_GROUP_1` (the building):

| Work | Use group | Result |
|---|---|---|
| New Construction | One Family / Two Family / Three Family | SFD 1 / U2 2 / U3_4 3 (derived) |
| Demolition | One / Two / Three Family | demolition, units removed 1 / 2 / 3 (derived) |
| Demolition | Accessory Use | demolition, 0 removed (a garage or shed) |
| anything else | any | OTHER (commercial use groups) or UNKNOWN, units unknown |

The layer has no unit count, so a new apartment building (a commercial use group such as R-2) has unknown
units.

**ADUs** come from the work description alone (`adu_from_text`). Cleveland's zoning allowed no by-right
ADUs in the window; the few built went through the Board of Zoning Appeals (BOZA) and are filed as an
"in-law suite" (often above a garage) or a "carriage house". A permit is an ADU when its description names a
new one on a residential or accessory permit (`ADU_USE_GROUPS`) and none of the vetoes in `NOT_NEW` fires.
When the description also builds the main house ("new single family residence with in-law suite above the
garage"), the row stays a new SFD with 1 unit (the BPS counts the house), and `adu_type` is set, so the ADU
is counted by `adu_type` without being counted as a house (`lotline.model.scenarios.adu` counts
`building_type_std == "ADU"` or a set `adu_type`). The description is read only by this rule and never
kept in the table.

Only non-personal fields are requested: no address, contractor names or licence numbers, coordinates or
portal links.
"""

from __future__ import annotations

import re

import pandas as pd

from lotline.io import DataStore
from lotline.io.arcgis import download_layer, epoch_ms_to_timestamp
from lotline.schemas import validate
from lotline.validation import holdout

ADAPTER = "states.oh.cle_permits"
VERSION = "1.0"
SOURCE = "cle_permits"
TABLE = "permits"
LAYER_URL = (
    "https://services3.arcgis.com/dty2kHktVXHrqO8i/arcgis/rest/services/Building_Permits/FeatureServer/0"
)
LANDING_URL = "https://data.clevelandohio.gov/"
LICENSE = "ODbL-1.0 (City of Cleveland open data; fetched at run time, derived tables never redistributed)"
CLEVELAND_GEOID = "3916000"
CUYAHOGA = "39035"

PERSONAL = {
    "PRIMARY_ADDRESS", "CONTRACTOR_NAME", "CONTRATOR_BUSINESS_NAME", "CONTRATOR_LICENSE_ID",
    "ACCELA_CITIZEN_ACCESS_URL", "LON", "LAT",
}  # fmt: skip
OUT_FIELDS = [
    "OBJECTID",
    "PERMIT_ID",
    "PERMIT_TYPE",
    "PERMIT_SUBTYPE",
    "PERMIT_CATEGORY",
    "JOB_DESCRIPTION",
    "USE_GROUP_1",
    "WORK_DESCRIPTION",
    "JOB_VALUE",
    "ISSUE_DATE",
    "PARCEL_NUMBER",
    "SIZE_OF_BUILDING",
    "DW_Form_Based_Code_Area",
]
WHERE = (
    "(PERMIT_TYPE = 'Building Permit' AND PERMIT_CATEGORY = 'New') OR (PERMIT_TYPE = 'Construction Project' "
    "AND PERMIT_CATEGORY IN ('Residential Building', 'Commercial Building'))"
)

# USE_GROUP_1 → (building_type_std, units) for new construction and demolition
DWELLING_USE = {"one family": ("SFD", 1), "two family": ("U2", 2), "three family": ("U3_4", 3)}
ACCESSORY_USE = "accessory use"
NEW_WORK = {"new construction"}
DEMO_WORK = {"demolition"}
COMMERCIAL_USE = re.compile(
    r"^(?:[a-z]-\d|[a-z]\s|commercial|mixed|industrial)", re.I
)  # "R-2 ...", "B Business"
# Use groups an ADU can be filed under: the city's residential groups, accessory use, the placeholder
# "PLEASE CHANGE" and blank (the residential subtype always has one of these).
ADU_USE_GROUPS = {"one family", "two family", "accessory use", "please change", ""}

# ---- the ADU rule ------------------------------------------------------------------------------------------
# A named ADU: "ADU", "A.D.U.", "accessory dwelling", "in-law suite/apartment/unit", "mother-in-law suite",
# "carriage house", "granny flat", "garage apartment", "apartment above/over the garage".
UNIT = (
    r"(?:\bA\.?D\.?U\.?S?\b|\baccessory\s+dwelling|\b(?:mother[- ]?|father[- ]?)?in[- ]?law\s+"
    r"(?:suite|apartment|apt|unit|quarters)|\bcarriage\s+house|\bgranny\s+(?:flat|unit|suite)"
    r"|\bgarage\s+apartment|\bapartment\s+(?:above|over)\s+(?:the\s+|a\s+)?(?:new\s+)?(?:detached\s+)?garage)"
)
ADU_WORD = re.compile(UNIT, re.I)
# The unit already exists, is being taken out or worked on, or the text says it is not one.
NOT_NEW = re.compile(
    r"\b(?:remov\w*|demo\w*|raze\w*|wreck\w*|abandon\w*|eliminat\w*)\b[^.;]{0,30}" + UNIT
    + r"|\b(?:exist\w*|historic|old)\s+(?:\w+\s+){0,2}" + UNIT
    + r"|\b(?:not|nor|no)\b[^.;]{0,30}" + UNIT
    + r"|" + UNIT + r"\s+(?:\w+\s+){0,3}"
    + r"(?:repair|reroof|re-roof|roof|siding|window|deck|porch|hvac|furnace)\b"
    + r"|\b(?:alteration|repair|renovat\w*|remodel\w*)\w*\s+(?:\w+\s+){0,3}(?:to|of|on|in)\s+"
    + r"(?:the\s+|an?\s+)?(?:\w+\s+){0,3}" + UNIT,
    re.I,
)  # fmt: skip
NEW_HOUSE = re.compile(
    r"\b(?:new|erect|construct)\b[^;]{0,80}?\b(?:single[- ]?fam\w*|sfr|sfd|1[- ]family|one[- ]family)\s+"
    r"(?:res\w*|reid\w*|home|house|dwelling)",
    re.I,
)  # periods are allowed in between: "ERECT A 2 STY. 3,708 S.F. SINGLE FAMILY RESIDENCE"
# A single-family "residence" that *is* the in-law suite ("ERECT ... SINGLE FAMILY RESIDENCE IN-LAW SUITE ON
# SECOND FLOOR OF EXISTING 2 CAR GARAGE"): the suite is the subject, so it is not a new house.
SUITE_IS_SUBJECT = re.compile(
    r"\b(?:single[- ]?fam\w*|sfr)\s+(?:res\w*\s+|reid\w*\s+)?" + UNIT
    + r"|" + UNIT + r"\s+(?:on|above|over)\s+(?:the\s+)?(?:second|2nd|upper)\s+floor\s+of\s+"
    + r"(?:an?\s+|the\s+)?exist",
    re.I,
)  # fmt: skip
DETACHED = re.compile(
    r"\bdetached\b|\bdet\.?\s|\bgarage\b|\bcarriage\s+house\b|\brear\b|\bcottage\b", re.I
)  # a suite over or behind a garage, or a carriage house, is a separate building
INTERNAL = re.compile(r"\bbasement\b|\battic\b|\bconver\w*", re.I)
ATTACHED = re.compile(r"\battached\b|\baddition\b", re.I)


def adu_from_text(text: str | None) -> str | None:
    """The ADU type ("detached", "internal_conversion", "attached" or "unknown") when `text` names a new ADU.

    A new ADU is named when `ADU_WORD` matches and `NOT_NEW` does not (existing, historic or removed units;
    "not for in-law suite"; repairs, roofs or porches on the unit; alterations to it). The type is the first
    that matches: detached (detached, garage, carriage house, rear, cottage), then an internal conversion
    (basement, attic, convert), then attached (attached, addition); else "unknown". None when no new ADU is
    named. "Adult" is never an ADU (the word must end after "ADU" or "ADUs").
    """
    if not text or not ADU_WORD.search(text) or NOT_NEW.search(text):
        return None
    for adu_type, pattern in (
        ("detached", DETACHED),
        ("internal_conversion", INTERNAL),
        ("attached", ATTACHED),
    ):
        if pattern.search(text):
            return adu_type
    return "unknown"


def builds_house_too(text: str | None) -> bool:
    """True when the description also builds the main house (the ADU is not the permit's only dwelling)."""
    if not text:
        return False
    return bool(NEW_HOUSE.search(text)) and not SUITE_IS_SUBJECT.search(text)


PROVENANCE = {
    "title": "City of Cleveland Building Permits (Building & Housing, weekly, 2015 to present)",
    "landing_url": LANDING_URL,
    "table": TABLE,
    "cleaning": [
        "Requested fields exclude the address, contractor names and licence numbers, coordinates and portal "
        "links (no personal data); the work description is read by the ADU rule only and not kept",
        "Server-side filter keeps building permits only: PERMIT_TYPE 'Building Permit' with PERMIT_CATEGORY "
        "'New', and 'Construction Project' records in 'Residential Building' or 'Commercial Building'; "
        "electrical, plumbing, HVAC, board-up and elevator permits are not downloaded",
        "Permits without an ISSUE_DATE are dropped (ISSUE_DATE, epoch ms → local Cleveland calendar date)",
        "building_type_std and units from JOB_DESCRIPTION and USE_GROUP_1: New Construction on One / Two / "
        "Three Family → SFD 1, U2 2, U3_4 3 (derived); Demolition removes 1 / 2 / 3 (derived), 0 for "
        "Accessory Use; commercial use groups → OTHER, the rest UNKNOWN, units unknown",
        "ADU when cle_permits.adu_from_text names a new ADU on a One Family, Two Family, Accessory Use, "
        "'PLEASE CHANGE' or blank use group (ADU 1 unit, inferred); a permit that also builds the main house "
        "stays SFD 1 unit with adu_type set",
        "parcel_id = '39035' + the 8-digit Cuyahoga parcel number (as in oh_parcels)",
        "permit_class_raw = PERMIT_TYPE|PERMIT_CATEGORY|JOB_DESCRIPTION|USE_GROUP_1",
        "Every row is assigned to Cleveland (3916000); holdout filter applied (Ohio has none)",
    ],
    "limitations": [
        "ODbL 1.0: the raw snapshot and derived tables stay outside the repo and are never published",
        "No dwelling-unit count: new apartment buildings (commercial use groups) have unknown units",
        "ADUs only where the description names one; Cleveland's own words are 'in-law suite' and "
        "'carriage house'. ADUs filed as an addition or alteration without those words are missed",
        "Starts in 2015 (the current permit system)",
        "The 2025-26 'Construction Project' records use different job descriptions; most fall to UNKNOWN",
    ],
}


def _text(values: pd.Series) -> pd.Series:
    return values.astype("string").str.strip().replace("", pd.NA)


def _dates(values: pd.Series) -> pd.Series:
    ms = pd.to_numeric(values, errors="coerce").astype("float64")
    return epoch_ms_to_timestamp(ms).dt.normalize().astype("datetime64[ns]")


def parcel_id(values: pd.Series) -> pd.Series:
    """Cuyahoga parcel number '104-14-018' or '10414018' → roll ID '3903510414018'; else missing."""
    digits = values.astype("string").str.replace(r"\D", "", regex=True)
    ok = digits.str.len() == 8
    return (CUYAHOGA + digits).where(ok.fillna(False).astype(bool))


def classify(work, use) -> tuple[str, str, object, object, bool]:
    """(building_type_std, type_confidence, units_new, units_removed, is_demolition) for one permit."""
    w = (work or "").strip().lower() if isinstance(work, str) else ""
    u = (use or "").strip().lower() if isinstance(use, str) else ""
    if w in DEMO_WORK:
        if u in DWELLING_USE:
            btype, n = DWELLING_USE[u]
            return btype, "high", 0, n, True
        if u == ACCESSORY_USE:
            return "OTHER", "high", 0, 0, True
        return (
            ("OTHER", "high", 0, pd.NA, True)
            if COMMERCIAL_USE.match(u)
            else ("UNKNOWN", "unknown", 0, pd.NA, True)
        )
    if w in NEW_WORK and u in DWELLING_USE:
        btype, n = DWELLING_USE[u]
        return btype, "high", n, pd.NA, False
    if u and COMMERCIAL_USE.match(u):
        return "OTHER", "high", pd.NA, pd.NA, False
    return "UNKNOWN", "unknown", pd.NA, pd.NA, False


def build(raw: pd.DataFrame, state: str = "OH") -> pd.DataFrame:
    """Raw layer attributes → canonical permits rows (before the holdout filter)."""
    assert not PERSONAL & set(raw.columns), "personal fields must never be requested"
    df = raw.copy()
    df["issue_date"] = _dates(df["ISSUE_DATE"])
    df = df.loc[df["issue_date"].notna()].copy()
    work, use = _text(df["JOB_DESCRIPTION"]), _text(df["USE_GROUP_1"])
    parts = pd.DataFrame(
        [
            classify(w if pd.notna(w) else None, u if pd.notna(u) else None)
            for w, u in zip(work, use, strict=True)
        ],
        index=df.index,
        columns=["building_type_std", "type_confidence", "units_new", "units_removed", "is_demolition"],
    )
    parts["units_confidence"] = "unknown"
    parts.loc[parts["units_new"].notna() | parts["units_removed"].notna(), "units_confidence"] = "derived"
    text = df["WORK_DESCRIPTION"].astype("string")
    adu = pd.Series([adu_from_text(t if pd.notna(t) else None) for t in text], index=df.index, dtype="string")
    use_ok = use.fillna("").str.lower().isin(ADU_USE_GROUPS) & ~parts["is_demolition"]
    adu = adu.where(use_ok)
    with_house = pd.Series([builds_house_too(t if pd.notna(t) else None) for t in text], index=df.index)
    only_adu = adu.notna() & ~with_house
    parts.loc[only_adu, ["building_type_std", "type_confidence", "units_new", "units_confidence"]] = [
        "ADU", "inferred", 1, "inferred"
    ]  # fmt: skip
    house_adu = adu.notna() & with_house
    parts.loc[house_adu, ["building_type_std", "type_confidence", "units_new", "units_confidence"]] = [
        "SFD", "inferred", 1, "derived"
    ]  # fmt: skip
    out = pd.DataFrame(
        {
            "state": state,
            "permit_id": "cle-" + _text(df["PERMIT_ID"]),
            "parcel_id": parcel_id(df["PARCEL_NUMBER"]),
            "jurisdiction_geoid": CLEVELAND_GEOID,
            "issue_year": df["issue_date"].dt.year.astype("Int64"),
            "issue_date": df["issue_date"],
            "date_precision": "day",
            "adu_type": adu,
            "permit_class_raw": (
                _text(df["PERMIT_TYPE"]).fillna("")
                + "|"
                + _text(df["PERMIT_CATEGORY"]).fillna("")
                + "|"
                + work.fillna("")
                + "|"
                + use.fillna("")
            ),
            "is_conversion": pd.Series(pd.NA, index=df.index, dtype="boolean"),
            "floor_area_sqft": pd.to_numeric(df["SIZE_OF_BUILDING"], errors="coerce").where(lambda s: s > 0),
            "valuation_usd": pd.to_numeric(df["JOB_VALUE"], errors="coerce").where(lambda s: s >= 0),
            "source": SOURCE,
        },
        index=df.index,
    ).join(parts)
    out["units_new"] = pd.to_numeric(out["units_new"], errors="coerce").astype("Int64")
    out["units_removed"] = pd.to_numeric(out["units_removed"], errors="coerce").astype("Int64")
    out["is_demolition"] = out["is_demolition"].astype("boolean")
    out = out.loc[out["permit_id"].notna()]
    out = out.sort_values(["permit_id", "issue_date"]).drop_duplicates(["state", "permit_id"], keep="last")
    return out.reset_index(drop=True)


def download(store: DataStore, *, refresh: bool = False) -> pd.DataFrame:
    return download_layer(
        LAYER_URL,
        name="building_permits",
        where=WHERE,
        out_fields=",".join(OUT_FIELDS),
        store=store,
        source=SOURCE,
        license=LICENSE,
        adapter=ADAPTER,
        adapter_version=VERSION,
        refresh=refresh,
    )


def load(state: str, store: DataStore, *, refresh: bool = False) -> pd.DataFrame:
    df = build(download(store, refresh=refresh), state=state)
    df = holdout.apply(
        df, state, geoid_col="jurisdiction_geoid", date_col="issue_date", year_col="issue_year"
    )
    return validate(df, TABLE)
