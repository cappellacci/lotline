"""Minneapolis Construction Code Services (CCS) permits → `permits` (Minneapolis only, Dec 2016 on).

Source: City of Minneapolis open data, `CCS_Permits` feature layer (CC0: the city waives copyright). The
layer is a **rolling window** that starts in December 2016, so every fetch is written as a dated snapshot (the
default vintage of `download_layer` is today's date) and older snapshots are never overwritten.

Field meanings come from the layer's item description on ArcGIS Online: `dwellingUnitsNew` / `...Eliminated`
are "the number of residential units added / eliminated ... with the issuing of the permit"; `issueDate` is
when reviews passed and fees were paid; `completeDate` is "the date the final inspection has been completed
and passed" (the permit then moves to Closed); `occupancyType` TFD means a two- *or three*-family dwelling.

**Personal data.** The layer carries the applicant's name, the owner's full name and the applicant's street
address and city. They are never requested: `FIELDS` lists exactly what is read. `comments` (the scope of
work) is read only to find ADUs; it can name engineers or architects, so it is never written to the table.

**ADUs.** The city has no ADU flag and records most ADU permits with `dwellingUnitsNew = 0` (the scope of
work says "ADU", the unit field does not). A permit is typed `ADU` (`type_confidence="inferred"`) only when
all hold: a residential building permit on an SFD/two-family/accessory structure, work that builds or
converts space (not a whole new house), a scope of work that names an ADU and does not negate it ("NOT AN
ADU", "FUTURE ADU"), an existing house on the parcel, and a reported unit gain of at most 1. Units stay as
the city reported them.
"""

from __future__ import annotations

import re

import httpx
import pandas as pd

from lotline.io import DataStore
from lotline.io.arcgis import download_layer, epoch_ms_to_timestamp
from lotline.schemas import validate
from lotline.validation import holdout

ADAPTER = "states.mn.mpls_permits"
VERSION = "1.0"
SOURCE = "mpls_ccs_permits"
TABLE = "permits"
LICENSE = "CC0 1.0 (City of Minneapolis open data waiver)"
LAYER_URL = "https://services.arcgis.com/afSMGVsC7QlRK1kZ/arcgis/rest/services/CCS_Permits/FeatureServer/0"
LANDING_URL = "https://opendata.minneapolismn.gov/datasets/cityoflakes::ccs-permits"
ITEM_URL = "https://www.arcgis.com/home/item.html?id=df4bfccbe60b42a6a93fb7bc1fd84cc0"

MINNEAPOLIS = "2743000"  # place GEOID (state 27 + FIPS place 43000)
HENNEPIN = "27053"  # county GEOID; Minneapolis APNs are 13-digit Hennepin PINs
TIMEZONE = "America/Chicago"

# Exactly what is read. Never "*": applicantName, fullName, applicantAddress1 and applicantCity identify
# people.
FIELDS = [
    "OBJECTID",
    "APN",
    "permitNumber",
    "permitType",
    "occupancyType",
    "workType",
    "status",
    "dwellingUnitsNew",
    "dwellingUnitsEliminated",
    "permit_Value",
    "totalFees",
    "issueDate",
    "completeDate",
    "comments",
]
PERSONAL = {"applicantName", "fullName", "applicantAddress1", "applicantCity"}

# Building permits only. Plumbing and Mechanical permits (about 250k rows) never add or remove a home, and
# Site permits are footings for commercial projects.
PERMIT_TYPES = ("Res", "Commercial", "Wrecking")
WHERE = "permitType IN ({})".format(",".join(f"'{t}'" for t in PERMIT_TYPES))

# occupancyType → building_type_std when the permit reports no positive unit count. TFD covers two- and
# three-family dwellings (item description), so it is DTQ, not U2. MFD (multifamily) is listed apart from
# 3to4, so it is MF5. Comm and Accessory (garages, sheds) are OTHER.
OCCUPANCY_TYPES = {
    "SFD": "SFD",
    "TH": "TH",
    "TFD": "DTQ",
    "3to4": "U3_4",
    "MFD": "MF5",
    "Comm": "OTHER",
    "Accessory": "OTHER",
}
MULTI = {"TFD", "3to4", "MFD", "Mixed", "Comm"}  # 2+ reported new units refine these to a size class

CONVERSION_WORK = {"Conversion", "UnitCon"}
ADU_WORK = {"Accessory", "Conversion", "UnitCon", "Remodel", "Addition", "New", "UnitFinish"}
ADU_OCCUPANCY = {"SFD", "TFD", "Accessory"}
HOUSE_OCCUPANCY = {"SFD", "TFD"}
CANCELLED = {"Cancelled", "Void", "Withdrawn", "Denied"}

# A scope of work that names an ADU ...
ADU_TEXT = re.compile(r"\badus?\b|\ba\.d\.u\b|accessory\s+dwelling", re.I)
# ... unless it says the space is not one, or not yet ("future ADU", "ADU is not being built", "not creating
# a second unit or ADU", "ADU not changed").
_ADU = r"(?:adu|accessory\s+dwelling)"
ADU_NEGATED = re.compile(
    rf"\b(?:not|no|non)[- ](?:an?\s+|for\s+(?:an?\s+)?|to\s+be\s+used\s+as\s+(?:an?\s+)?)?{_ADU}\b"
    rf"|\badu\s+(?:is\s+|was\s+|will\s+)?not\b|\bfuture\s+{_ADU}\b"
    rf"|\bnot\s+(?:creating|create|adding|add)\b[^.]{{0,40}}\b{_ADU}\b",
    re.I,
)
# Work on an ADU that already exists ("remodel existing basement level ADU", "repairs to lower level ADU",
# "relocate ADU") unless the permit legalizes it.
_PLACE = r"(?:basement|lower|upper|main|second|2nd|level|floor|attic|detached|attached|internal|interior)"
ADU_EXISTING = re.compile(
    rf"\bexisting\s+(?:{_PLACE}\s+){{0,3}}{_ADU}\b"
    rf"|\b(?:repair|repairs|relocate|replace|reroof)\b[^.]{{0,40}}\b{_ADU}\b",
    re.I,
)
LEGALIZE = re.compile(r"\blea?gali[sz]", re.I)
# The text says the house already stands ("accessory to a SFD", "existing SFD", "existing house").
EXISTING_HOUSE = re.compile(
    r"\b(?:existing\s+|accessory\s+to\s+(?:an?\s+|the\s+)?)"
    r"(?:sfd|single[- ]family|house|home|duplex|dwelling)",
    re.I,
)
# ADU form, first match wins.
ADU_KINDS = [
    ("internal_conversion", re.compile(r"\b(?:basement|attic|internal|interior|lower\s+level)\b", re.I)),
    ("detached", re.compile(r"\b(?:detached|garage|carriage|backyard|cottage)\b", re.I)),
    ("attached", re.compile(r"\b(?:attached|addition)\b", re.I)),
]

PROVENANCE = {
    "title": "City of Minneapolis CCS Permits (building permits, Dec 2016 on)",
    "landing_url": LANDING_URL,
    "table": TABLE,
    "attribution": "City of Minneapolis, Construction Code Services (open data, CC0)",
    "cleaning": [
        f"Download the CCS_Permits feature layer ({LAYER_URL}) with the ArcGIS pager into a dated snapshot "
        f"(the layer is a rolling window from Dec 2016), requesting only {', '.join(FIELDS)} where "
        f"{WHERE}. Applicant name, owner name and applicant address/city are never requested; Plumbing, "
        "Mechanical and Site permits are not downloaded",
        "One row per permitNumber: a permit listed once per parcel it touches (about 3,700 permits) is "
        "collapsed to its lowest OBJECTID row, and its unit counts are counted once, not once per parcel",
        "parcel_id: '27053' (Hennepin) + the 13-digit APN; for a multi-parcel permit, the lowest APN",
        "issueDate / completeDate (epoch ms, UTC) → local Minneapolis calendar dates; issue_year from "
        "issue_date; date_precision=day",
        "final_date = completeDate only for Closed permits, final_date_type=final_inspection (the item "
        "description defines completeDate as the passed final inspection); cancelled permits get no "
        "final_date",
        "dwellingUnitsNew / dwellingUnitsEliminated (text) → units_new / units_removed; empty → null "
        "(unknown), never 0; units_confidence=reported when both are present",
        "Wrecking permits: is_demolition=True; dwellingUnitsEliminated is always empty there, so a whole SFD "
        "wrecked → units_removed=1 (derived), any other building → null",
        "building_type_std from occupancyType: SFD→SFD, TH→TH, TFD (two- or three-family)→DTQ, 3to4→U3_4, "
        "MFD→MF5, Comm and Accessory→OTHER, blank→UNKNOWN; when TFD/3to4/MFD/Mixed/Comm reports N≥2 new "
        "units the Census size class of N is used (2→U2, 3-4→U3_4, 5-6→U5_6, 7+→U7P)",
        "ADU (type_confidence=inferred): Res permit on an SFD/TFD/Accessory occupancy; work type Accessory, "
        "Conversion, UnitCon, Remodel, Addition, UnitFinish, or New on an Accessory structure; comments "
        "name an ADU and do not negate it ('NOT AN ADU', 'FUTURE ADU') or describe work on an existing "
        "ADU (unless legalizing it); an existing house on the parcel (the occupancy is a house and the "
        "work is not a new house, the comments say 'accessory to a SFD'/'existing house', or the APN has "
        "another non-new house permit); and at most 1 new unit reported. adu_type from the comments "
        "(basement/attic → internal_conversion, garage/detached → detached, attached/addition → attached, "
        "else unknown)",
        "is_conversion=True for work types Conversion/UnitCon or when a permit both adds and removes units",
        "valuation_usd = permit_Value, fees_paid_usd = totalFees (city fees and taxes; 0 kept as 0)",
        "permit_class_raw = permitType:occupancyType:workType:status (status is kept so cancelled permits "
        "can be dropped downstream)",
        "comments are read for the ADU rule only and never stored",
        "jurisdiction_geoid = 2743000 (Minneapolis); held-out place-years removed (validation/holdout.py)",
    ],
    "limitations": [
        "Rolling window: the layer starts in Dec 2016 and older permits drop out; only dated snapshots keep "
        "them. 2016 holds December only",
        "dwellingUnitsNew is reported as 0 on most ADU permits, so units_new undercounts ADUs; count ADU "
        "permits (or parcels) instead of summing units_new",
        "ADU typing is inferred from free text: it misses ADUs whose scope of work doesn't say 'ADU' and "
        "can't tell a new house built with an ADU (typed SFD) from one without",
        "Cancelled, expired and withdrawn permits stay in the table (status is in permit_class_raw)",
        "Demolished units are unknown for anything but whole single-family houses",
        "A permit listed on several parcels keeps only its lowest APN",
        "Minneapolis only; Commercial permits cover apartments, mixed use and non-residential alike",
    ],
}


def load(
    state: str, store: DataStore, *, refresh: bool = False, http: httpx.Client | None = None
) -> pd.DataFrame:
    if state.upper() != "MN":
        raise ValueError(f"{SOURCE} covers Minneapolis, Minnesota only, not {state}")
    raw = download_layer(
        LAYER_URL,
        store=store,
        source=SOURCE,
        license=LICENSE,
        adapter=ADAPTER,
        adapter_version=VERSION,
        name="ccs_permits",
        where=WHERE,
        out_fields=",".join(FIELDS),
        refresh=refresh,
        http=http,
    )
    return to_permits(raw)


def to_permits(raw: pd.DataFrame, state: str = "MN") -> pd.DataFrame:
    """Raw layer attributes → validated `permits`, one row per permit, holdouts removed."""
    # Never requested (FIELDS); dropped here too, so no code path can carry them into a table.
    raw = raw.drop(columns=[c for c in raw.columns if c in PERSONAL])
    raw = raw[raw["permitType"].isin(PERMIT_TYPES)].copy()
    raw["APN"] = clean_apn(raw["APN"])
    has_house_permit = _apns_with_existing_house(raw)
    raw = raw.sort_values(["permitNumber", "OBJECTID"])
    first_apn = raw.groupby("permitNumber")["APN"].min()
    raw = raw.drop_duplicates("permitNumber", keep="first").set_index("permitNumber")
    raw["APN"] = first_apn

    ptype = raw["permitType"].astype("string").str.strip()
    occ = raw["occupancyType"].astype("string").str.strip()
    work = raw["workType"].astype("string").str.strip()
    status = raw["status"].astype("string").str.strip()
    text = raw["comments"].astype("string").fillna("")
    wrecking = ptype == "Wrecking"

    new = _units(raw["dwellingUnitsNew"])
    removed = _units(raw["dwellingUnitsEliminated"])
    issued = _local_date(raw["issueDate"])
    completed = _local_date(raw["completeDate"]).where(status == "Closed")

    btype = occ.map(OCCUPANCY_TYPES).fillna("UNKNOWN")
    refine = occ.isin(MULTI) & (new >= 2).fillna(False)
    btype = btype.mask(refine, new.map(size_class, na_action="ignore"))
    confidence = pd.Series("high", index=raw.index).mask(btype == "UNKNOWN", "unknown")

    adu = is_adu(ptype, occ, work, text, new, raw["APN"], has_house_permit)
    btype = btype.mask(adu, "ADU")
    confidence = confidence.mask(adu, "inferred")
    adu_type = pd.Series(pd.NA, index=raw.index, dtype="string").mask(adu, text.map(adu_kind))

    # Wrecking rows never report eliminated units; a whole single-family house is one unit.
    sfd_wreck = wrecking & (occ == "SFD") & removed.isna()
    removed = removed.mask(sfd_wreck, 1)
    new = new.mask(wrecking & new.isna(), 0)
    units_conf = pd.Series("unknown", index=raw.index)
    units_conf = units_conf.mask(new.notna() & removed.notna(), "reported")
    units_conf = units_conf.mask(sfd_wreck, "derived")
    units_conf = units_conf.mask(wrecking & ~sfd_wreck, "unknown")

    conversion = work.isin(CONVERSION_WORK) | ((new > 0) & (removed > 0)).fillna(False)

    df = pd.DataFrame(
        {
            "state": state,
            "permit_id": "mpls-" + raw.index.astype("string"),
            "parcel_id": (HENNEPIN + raw["APN"]).astype("string"),
            "jurisdiction_geoid": MINNEAPOLIS,
            "issue_year": issued.dt.year.astype("Int64"),
            "issue_date": issued,
            "date_precision": "day",
            "final_date": completed,
            "final_date_type": pd.Series(pd.NA, index=raw.index, dtype="string").mask(
                completed.notna(), "final_inspection"
            ),
            "building_type_std": btype,
            "type_confidence": confidence,
            "adu_type": adu_type,
            "permit_class_raw": (
                ptype.fillna("") + ":" + occ.fillna("") + ":" + work.fillna("") + ":" + status.fillna("")
            ),
            "units_new": new,
            "units_removed": removed,
            "units_confidence": units_conf,
            "is_demolition": pd.Series(wrecking, dtype="boolean"),
            "is_conversion": pd.Series(conversion, dtype="boolean"),
            "valuation_usd": pd.to_numeric(raw["permit_Value"], errors="coerce").astype(float),
            "fees_paid_usd": pd.to_numeric(raw["totalFees"], errors="coerce").astype(float),
            "source": SOURCE,
        }
    )
    df = df[df["issue_date"].notna()]  # never issued: not a permit yet
    df = holdout.apply(
        df, state, geoid_col="jurisdiction_geoid", date_col="issue_date", year_col="issue_year"
    )
    return validate(df.reset_index(drop=True), TABLE)


def is_adu(
    ptype: pd.Series,
    occ: pd.Series,
    work: pd.Series,
    text: pd.Series,
    new: pd.Series,
    apn: pd.Series,
    has_house_permit: set[str],
) -> pd.Series:
    """The inferred-ADU rule in the module docstring, one boolean per permit."""
    names_adu = text.str.contains(ADU_TEXT) & ~text.str.contains(ADU_NEGATED)
    existing_adu = text.str.contains(ADU_EXISTING) & ~text.str.contains(LEGALIZE)
    builds = work.isin(ADU_WORK) & ((work != "New") | (occ == "Accessory"))
    existing_house = (
        (occ.isin(HOUSE_OCCUPANCY) & (work != "New"))
        | text.str.contains(EXISTING_HOUSE)
        | apn.isin(has_house_permit)
    )
    at_most_one = (new <= 1).fillna(True)
    rule = (ptype == "Res") & occ.isin(ADU_OCCUPANCY) & builds & names_adu & ~existing_adu
    return (rule & existing_house & at_most_one).fillna(False).astype(bool)


def adu_kind(text: str) -> str:
    for kind, pattern in ADU_KINDS:
        if pattern.search(text):
            return kind
    return "unknown"


def size_class(n: int) -> str:
    """Census structure-size class of a building with n units."""
    if n == 1:
        return "SFD"
    if n == 2:
        return "U2"
    if n <= 4:
        return "U3_4"
    return "U5_6" if n <= 6 else "U7P"


def clean_apn(apn: pd.Series) -> pd.Series:
    """Digits only; anything that isn't a 13-digit Hennepin PIN (or is all zeros) → null."""
    digits = apn.astype("string").str.replace(r"\D", "", regex=True)
    return digits.where(
        digits.str.fullmatch(r"\d{13}").fillna(False) & ~digits.str.fullmatch(r"0+").fillna(True)
    )


def _apns_with_existing_house(raw: pd.DataFrame) -> set[str]:
    """Parcels with a residential permit on an existing house (any SFD/TFD work that isn't a new house)."""
    house = (
        (raw["permitType"] == "Res")
        & raw["occupancyType"].astype("string").str.strip().isin(HOUSE_OCCUPANCY)
        & (raw["workType"].astype("string").str.strip() != "New")
    )
    return set(raw.loc[house, "APN"].dropna())


def _units(values: pd.Series) -> pd.Series:
    """Text unit counts → Int64; empty or non-numeric text is unknown (null), never 0."""
    text = values.astype("string").str.strip()
    return pd.to_numeric(text.where(text.str.fullmatch(r"\d+").fillna(False)), errors="coerce").astype(
        "Int64"
    )


def _local_date(epoch_ms: pd.Series) -> pd.Series:
    """Epoch milliseconds (UTC) → the calendar date in Minneapolis."""
    utc = epoch_ms_to_timestamp(epoch_ms)
    return utc.dt.tz_localize("UTC").dt.tz_convert(TIMEZONE).dt.tz_localize(None).dt.normalize()
