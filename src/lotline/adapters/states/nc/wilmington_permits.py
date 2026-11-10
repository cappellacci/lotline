"""New Hanover County building permits (Wilmington and the county) → canonical `permits`.

New Hanover County Building Safety issues every building permit inside the City of Wilmington, as well as in
the unincorporated county. Its GIS server publishes those permits as a point layer
(`Thematic/BuildingPermits` FeatureServer layer 0): one row per permit, plan sign-off or trade permit,
from the county's Tyler EnerGov system (2019 on) and records converted from its earlier OneSolution system
(2014-2018, `WORK_CLASS` "Converted"). Wilmington has no Census BPS row of its own (BPS files it under New
Hanover County), so this file is the only record-level count of its homes and ADUs.

**What is downloaded.** Building permits only (`PERMIT_TYPES`: residential building, accessory, addition,
demolition and relocation permits, and commercial building, accessory and demolition permits). Not
downloaded: trade permits (electrical, plumbing, mechanical), building *applications* (pre-issue records with
no issue date) and the 71,000 "NHC Converted" rows, which are agency sign-off holds ("NEEDS CITY ZONING",
"CFPUA FINAL") attached to a permit, not permits.

**Kept.** Permits with an issue date and a status other than void, withdrawn, denied, revoked or still in
review (`NOT_ISSUED`); expired permits stay (they were issued, as BPS counts them). Converted records whose
description ends in "Job master" are dropped (`JOB_MASTER`): they are the old system's job containers, and
each building job also has its own structure permit, so keeping both would count every building twice.

**Activity, building type and units.** The layer has no unit count and no building-type code, so:

- demolition permit types → `is_demolition`, `units_new` 0, `units_removed` from the description parser
  (`inferred`) or unknown;
- residential building permits with work class "New Single Family Residence" / "NSFR" → `SFD`, 1 unit
  (`derived`), unless the description parser names another dwelling type (townhouse, duplex, ...), which then
  gives the type and, when it fits, the count (`inferred`);
- converted residential building permits (2014-2018, work class "Converted") carry no work class: the
  description parser's new-construction reading ("NEW HOUSE", "NEW SFD", "NEW TOWNHOME") gives the type and
  count (`inferred`); other converted permits are alterations;
- manufactured-home placements (relocation work class "Mobile Home", converted mobile-home relocations) →
  `OTHER`, 1 unit (`derived`); relocated site-built houses → `SFD`, units unknown (a moved house is not new);
- new residential accessory structures (sheds, garages, pools) → `OTHER`, 0 units (`derived`);
- new commercial buildings and shells → the parser's dwelling type and count (`inferred`), else `UNKNOWN`
  with units unknown (apartment buildings are commercial permits and rarely state a unit count);
- every other permit (alterations, additions, repairs) → 0 units (`derived`) unless the parser reads a
  conversion that adds units (`inferred`).

**Accessory dwelling units (`is_adu_text`).** A residential permit (building, accessory, addition or
converted SFR / accessory-structure types) is an `ADU` (1 unit, `inferred`) when its description names one
and no veto applies. The county files most ADUs as new single-family residence (NSFR) permits whose text says
both "single family" and "ADU" ("SFR - 1BR 1BA - ADU"); the shared parser gives no type for such a text, so
the rule asks only for an ADU term, not the parser's full reading:

- an ADU term: the shared parser's `permit_text.ADU` ("ADU", "accessory dwelling", "accessory apartment",
  "garage apartment", "in-law suite", "carriage house" ...), or `LOCAL_ADU` ("garage apt", "additional
  dwelling unit", "built as ADU", "in-law cottage", "new apartment", "apartment over", "dwelling unit above",
  "Unit A - new guest house");
- vetoes: a note ruling an ADU out (`NOT_ADU`: "Not to be used as an accessory dwelling unit", "NOT APPROVED
  FOR ADU"; the county adds this note to many garage and shed permits from 2025); work on an ADU that already
  exists (`EXISTING_ADU`: "renovate existing ADU", "repairs to garage apartment", "new home in front of
  existing ADU"); the ADU is on another permit and this one is the house (`ELSEWHERE`: "ADU TO BE PERMITTED
  SEPARATELY", "New SFR ONLY", "MAIN HOUSE ADU IS PERMIT 23-..."; but "NEW ADU / Primary dwelling permitted
  separately" stays an ADU); a duplex (`DUPLEX`).

The kind (attached / detached / internal conversion) comes from the parser's `ADU_KIND` phrases, else
`unknown`. "Guest house", "guest suite", "pool house" and "cottage" alone are not read as ADUs (precision over
recall, as in Greensboro). A permit that builds a house and its ADU together ("Single Family Home with ADU")
is one ADU row, so that house is not counted. `reports/nc/wilmington-adu-scout.md` reports the hand check of
the rule (precision and missed phrasings). Before parsing, converted records' trailing occupancy class
("- R3SingleFamilyResidence Structure", `LEGACY_SUFFIX`) is removed and underscores become spaces.

**Jurisdiction.** Each permit is placed by its point (`Lat`/`Lon`) against Census place boundaries
(`lotline.geo.place_or_township`, TIGERweb ACS 2025): Wilmington is 3774440; points outside every place are
unincorporated New Hanover County (37129). Permits with no point fall back to the county's own `DISTRICT`
label (EnerGov permits only), else 37129. One boundary vintage applies to every year.

**Parcel.** `PID` is the county's tax-parcel id (R06220-001-027-000), not the NC PIN the parcel tables use.
The county's parcel layer (same service, layer 4) maps PID → PIN, so `parcel_id` = "37129" + PIN, the
OneMap parcel id; null when the PID is missing or no longer in the parcel layer.

**Other fields.** `permit_id` = `PERMIT_NUMBER`; `zoning_raw` = `MAIN_ZONE`; `valuation_usd` = `VALUATION`;
`floor_area_sqft` = `SQUARE_FEET` (> 0); `application_date` = `APPLICATION_DATE`; `final_date` =
`FINALED_DATE` (`final_inspection`); `permit_class_raw` = permit type | work class.

**Privacy.** The layer also holds the general contractor, the project contact, the inspector and the site
address; none of them are requested (`OUT_FIELDS`). The description often begins with an owner's or builder's
name, so it is requested only for the parser, read in memory and never kept.
"""

from __future__ import annotations

import re

import pandas as pd

from lotline.io import DataStore
from lotline.io.arcgis import epoch_ms_to_timestamp
from lotline.parse.permit_text import ADU, ADU_KIND, parse_description
from lotline.schemas import validate

ADAPTER = "states.nc.wilmington_permits"
VERSION = "1.0"
SOURCE = "wilmington_permits"
TABLE = "permits"
SERVICE_URL = "https://gis.nhcgov.com/server/rest/services/Thematic/BuildingPermits/FeatureServer"
LAYER_URL = f"{SERVICE_URL}/0"
PARCELS_URL = f"{SERVICE_URL}/4"
LANDING_URL = "https://www.arcgis.com/home/item.html?id=b84f1cf36cf440efb66ef14e8d93ea06"
LICENSE = (
    "New Hanover County public records; no license stated. County open-data disclaimer: provided as is, "
    "no warranty, use at your own risk, user holds the County harmless (https://opendata.nhcgov.com)"
)
WILMINGTON = "3774440"
COUNTY = "37129"  # New Hanover County unincorporated area
DISTRICTS = {"City of Wilmington": WILMINGTON, "New Hanover County": COUNTY}

PERMIT_TYPES = [
    "NHC Residential Building",
    "NHC Residential Accessory",
    "NHC Residential Accessory Structure - Converted",
    "NHC Residential Addition",
    "NHC SFR Existing - Converted",
    "NHC Residential Demolition",
    "NHC Residential Relocation ",  # the service spells it with a trailing space
    "NHC Residential Relocation Mobile Home - Converted",
    "NHC Commercial Building",
    "NHC Commercial Accessory",
    "NHC Commercial Demolition",
]
WHERE = "PERMIT_TYPE IN ({})".format(", ".join(f"'{t}'" for t in PERMIT_TYPES))
OUT_FIELDS = [
    "OBJECTID",
    "PERMIT_NUMBER",
    "PERMIT_TYPE",
    "WORK_CLASS",
    "PERMIT_STATUS",
    "APPLICATION_DATE",
    "ISSUE_DATE",
    "FINALED_DATE",
    "DISTRICT",
    "SQUARE_FEET",
    "VALUATION",
    "MAIN_ZONE",
    "PID",
    "Lat",
    "Lon",
    "DESCRIPTION",  # parser input only, never kept
]
PERSONAL = {
    "GENERAL_CONTRACTOR", "PROJECT_CONTACT", "ASSIGNED_TO", "PROJECT", "NUMBER", "SUBNUM", "STREET", "TYPE",
    "DIR", "UNIT", "UTYPE", "ZIPCODE", "GEO_X", "GEO_Y",
}  # fmt: skip
NOT_ISSUED = {
    "Void", "Withdrawn", "Denied", "Revoked", "In Review", "Awaiting Payment", "Application Incomplete",
    "Submitted", "Submitted - Online", "On Hold",
}  # fmt: skip
ADU_TYPES = {
    "NHC Residential Building",
    "NHC Residential Accessory",
    "NHC Residential Accessory Structure - Converted",
    "NHC Residential Addition",
    "NHC SFR Existing - Converted",
}
NEW_SFR = {"New Single Family Residence", "NSFR"}
DWELLINGS = {"SFD", "TH", "U2", "U3_4", "DTQ", "MF5"}
# Terms the county uses on top of the shared parser's ADU terms (`permit_text.ADU`).
LOCAL_ADU = re.compile(
    r"\bgarage\s+apt\b|\badditional\s+dwelling\s+unit\b|\bbuilt\s+as\s+(?:an?\s+)?adu\b"
    r"|\bin[- ]law\s+(?:cottage|house)\b|\bnew\s+apartment\b"
    r"|\bapartment\s+next\s+to\s+(?:the\s+)?main\s+house\b|\b(?:dwelling\s+unit|apartment)\s+(?:above|over)\b"
    r"|\bwill\s+be\s+an?\s+dwelling\s+unit\b"
    r"|\bunit\s+a\b\W{0,5}(?:new\s+)?guest\s+(?:house|cottage)\b",
    re.I,
)
# Reviewer notes that rule an ADU out: "Not to be used as an accessory dwelling unit", "NOT APPROVED FOR
# ADU", "Not proposed nor approved as an ADU", "SHALL NOT BE AN ADU". The county adds these to many garage
# and shed permits from 2025, so without this veto they would read as ADUs.
NOT_ADU = re.compile(
    r"\b(?:not|nor)\b[^.;/*]{0,50}?\(?\b(?:adus?|accessory\s+(?:dwelling|apartment))\b|\bnon-adu\b", re.I
)
# Work on an ADU that is already there ("Renovate existing ADU", "ADU WAS ALREADY IN PLACE", "New home in
# front of existing detached ADU"), and a contractor whose name contains "ADU": not a new ADU.
EXISTING_ADU = re.compile(
    r"\b(?:adu|accessory\s+dwelling(?:\s+unit)?)\s+(?:was\s+|is\s+)?already\b"
    r"|\bexist(?:ing|ent)\s+(?:(?:de|at)tached\s+)?(?:adu|accessory\s+(?:dwelling|apartment)|garage\s+apartment)\b"
    r"|\b(?:repairs?|alterations?|renovations?|remodel)\s+(?:to|of)\s+(?:the\s+|an?\s+)?(?:existing\s+)?"
    r"(?:adu|garage\s+apartment|accessory\s+(?:dwelling|apartment))\b"
    r"|\bexisting\s+home\s*/\s*adu\b|\beastern\s+adu\b|\b(?:doors?|windows?|roof)\s+(?:to|on)\s+(?:the\s+)?carriage\s+house\b",
    re.I,
)
# The ADU is on another permit and this one is the house: "ADU TO BE PERMITTED SEPARATELY", "ADU ON SEPARATE
# PERMIT", "MAIN HOUSE ADU IS PERMIT 23-...", "New SFR ONLY / ADU at rear ...", "PERMIT ONLY FOR MAIN HOUSE".
# Between the ADU term and "permitted separately" no house word may appear, so "NEW ADU / Primary dwelling
# permitted separately" stays an ADU.
_ADU_WORDS = r"(?:adu|accessory\s+(?:dwelling|apartment)(?:\s+unit)?|garage\s+apt\.?|garage\s+apartment)"
_NO_HOUSE = r"(?:(?!\b(?:primary|main|house|home|sfr|residence|addition|alterations?)\b)[^.;]){0,45}?"
ELSEWHERE = re.compile(
    rf"\b{_ADU_WORDS}\b{_NO_HOUSE}(?:permit+ed\s+separately|(?:on|need\w*)\s+(?:a\s+)?separate\s+permit"
    r"|\bis\s+(?:under\s+)?permit\s*#?\s*\d|under\s+(?:a\s+)?separate)"
    r"|(?<!guest\s)\b(?:new\s+|main\s+)?(?:house|home|sfr|residence)\s+only\b"
    r"|\bpermit\s+only\s+for\s+(?:the\s+)?main\s+house\b|\bthis\s+is\s+(?:the\s+)?main\s+house\b",
    re.I,
)
# A duplex permit that mentions an ADU ("DUPLEX - ADU MAIN UNIT") is a duplex.
DUPLEX = re.compile(r"\bduplex\b", re.I)
# Converted 2014-2018 records end with the old system's occupancy class:
# "... - R3SingleFamilyResidence Structure".
LEGACY_SUFFIX = re.compile(r"\s+-\s+\w+\s+(?:Structure|Job master|Location)\s*$", re.I)
# Converted "Job master" records are the old system's job containers: a building job also has its own
# structure permit (same parcel, own number), so job masters would count each building twice.
JOB_MASTER = re.compile(r"\bJob master\s*$", re.I)

PROVENANCE = {
    "title": "New Hanover County building permits (Wilmington and unincorporated county, 2014 to present)",
    "landing_url": LANDING_URL,
    "table": TABLE,
    "cleaning": [
        "Building permit types only (server-side filter); trade permits, building applications and the "
        "'NHC Converted' agency sign-off holds are not downloaded. Requested fields exclude the contractor, "
        "project contact, inspector and site address; DESCRIPTION is read only by the description parser and "
        "never kept",
        "Permits without an issue date, or void, withdrawn, denied, revoked or still in review, are dropped; "
        "expired permits are kept; converted 'Job master' records (job containers that duplicate the "
        "structure permit) are dropped",
        "No unit or building-type field: new single-family work classes are SFD, 1 unit (derived); converted "
        "2014-2018 permits, other dwelling types, demolitions and new commercial buildings from the "
        "description parser (inferred); manufactured-home placements OTHER, 1 unit; accessory structures 0",
        "ADU when a residential building, accessory or addition permit's description names one (shared "
        "parser terms plus the county's: 'garage apt', 'additional dwelling unit' ...), unless a note "
        "rules it out ('Not to be used as an accessory dwelling unit'), it is an existing ADU, the ADU is "
        "on another permit ('ADU to be permitted separately') or it is a duplex: ADU, 1 unit, inferred",
        "jurisdiction_geoid by point in Census place polygons (TIGERweb ACS 2025): Wilmington 3774440, else "
        "unincorporated New Hanover 37129; no point: the county's DISTRICT label, else 37129",
        "parcel_id = 37129 + NC PIN via the county parcel layer (PID -> PIN); zoning_raw = MAIN_ZONE; "
        "valuation_usd = VALUATION; floor_area_sqft = SQUARE_FEET; final_date = FINALED_DATE",
    ],
    "limitations": [
        "Starts in 2014 (the county's OneSolution records converted to EnerGov); nothing before 2014",
        "No unit count: multifamily units only where the description states them; new commercial buildings "
        "without one are UNKNOWN",
        "ADUs from the description only (no ADU field): hand check of 30 matches and 30 likely-ADU "
        "non-matches gave precision about 90% and a few percent of ADUs missed ('garage with apartment', "
        "'attached dwelling unit'; guest houses are never counted). See reports/nc/wilmington-adu-scout.md",
        "A few ADUs have two permits (a reissue after an expired permit, or a house-and-ADU pair): 291 "
        "Wilmington ADU permits 2014-2026 sit on 279 parcels. A permit that builds a house and its ADU "
        "together is one ADU row, so that house is not counted",
        "Current place boundaries are applied to every year: permits on land annexed later are placed in "
        "Wilmington",
        "The layer also covers Carolina Beach, Kure Beach and Wrightsville Beach where the county issued the "
        "permit; their coverage is partial and they are not checked",
    ],
}


def _clean(s: pd.Series) -> pd.Series:
    return s.astype("string").str.strip().fillna("")


def clean_description(text: object) -> str:
    """The description without the converted records' occupancy suffix (it reads as 'single family'), and
    with underscores as spaces ("NEW ADU_New construction": "_" is a word character, so it hides "ADU")."""
    return LEGACY_SUFFIX.sub("", text).replace("_", " ") if isinstance(text, str) else ""


def is_adu_text(text: str) -> bool:
    """True when the description names an accessory dwelling built (or legalized) on this permit.

    An ADU term (`permit_text.ADU` or `LOCAL_ADU`) must appear, and none of the vetoes: a note ruling an ADU
    out (`NOT_ADU`), work on an existing ADU (`EXISTING_ADU`), an ADU on another permit (`ELSEWHERE`) or a
    duplex (`DUPLEX`). The shared parser's full reading is not required: it gives no type when a permit says
    both "single family" and "ADU" ("SFR - 1BR 1BA - ADU"), which is how the county files most ADUs.
    """
    if not text or not (ADU.search(text) or LOCAL_ADU.search(text)):
        return False
    return not any(p.search(text) for p in (NOT_ADU, EXISTING_ADU, ELSEWHERE, DUPLEX))


def adu_kind(text: str) -> str | None:
    """The shared parser's attached / detached / internal kind, for ADUs it names but leaves untyped."""
    return next((kind for kind, pattern in ADU_KIND if pattern.search(text)), None)


def _fits(btype: str, n: object) -> bool:
    if n is None or pd.isna(n):
        return False
    lo, hi = {"SFD": (1, 1), "TH": (1, 99), "U2": (1, 2), "U3_4": (3, 4), "DTQ": (2, 4)}.get(btype, (5, 9999))
    return lo <= n <= hi


def classify(ptype: str, wclass: str, desc: str) -> dict:
    """building_type_std, type_confidence, adu_type, units_new, units_removed, units_confidence, flags."""
    desc = clean_description(desc)
    facts = parse_description(desc)
    out = dict(adu_type=None, units_new=None, units_removed=None, units_confidence="unknown",
               is_demolition=False, is_conversion=bool(facts.is_conversion))  # fmt: skip
    parsed = facts.building_type_std if facts.building_type_std in DWELLINGS else None
    if "Demolition" in ptype:
        out.update(is_demolition=True, units_new=0, is_conversion=False)
        if facts.units_removed:
            out.update(units_removed=facts.units_removed, units_confidence="inferred")
        return dict(
            out, building_type_std=parsed or "UNKNOWN", type_confidence="inferred" if parsed else "unknown"
        )
    if ptype in ADU_TYPES and is_adu_text(desc):
        kind = facts.adu_type or adu_kind(desc)
        out.update(adu_type=kind or "unknown", units_new=1, units_removed=0)
        return dict(out, building_type_std="ADU", type_confidence="inferred", units_confidence="inferred")
    residential = ptype == "NHC Residential Building"
    legacy_new = residential and wclass == "Converted" and parsed and facts.units_new
    if (residential and wclass in NEW_SFR) or legacy_new:
        out.update(units_removed=0)
        if parsed and parsed != "SFD":
            ok = _fits(parsed, facts.units_new)
            out.update(
                units_new=facts.units_new if ok else None, units_confidence="inferred" if ok else "unknown"
            )
            return dict(out, building_type_std=parsed, type_confidence="inferred")
        if legacy_new:
            out.update(units_new=1, units_confidence="inferred")
            return dict(out, building_type_std="SFD", type_confidence="inferred")
        out.update(units_new=1, units_confidence="derived")
        return dict(out, building_type_std="SFD", type_confidence="high")
    if "Relocation" in ptype:
        if wclass == "Mobile Home" or "Mobile Home" in ptype:
            out.update(units_new=1, units_removed=0, units_confidence="derived")
            return dict(out, building_type_std="OTHER", type_confidence="high")
        return dict(out, building_type_std="SFD", type_confidence="high")  # a moved house: units unknown
    if ptype in ("NHC Residential Accessory", "NHC Commercial Accessory") and wclass == "New":
        out.update(units_new=0, units_removed=0, units_confidence="derived")
        return dict(out, building_type_std="OTHER", type_confidence="high")
    if ptype == "NHC Commercial Building" and wclass in ("New", "Shell"):
        if parsed and _fits(parsed, facts.units_new):
            out.update(units_new=facts.units_new, units_removed=0, units_confidence="inferred")
            return dict(out, building_type_std=parsed, type_confidence="inferred")
        return dict(out, building_type_std="UNKNOWN", type_confidence="unknown")
    # alterations, additions, repairs and converted non-new permits
    if facts.is_conversion and facts.units_new:
        out.update(units_new=facts.units_new, units_removed=facts.units_removed, units_confidence="inferred")
    else:
        out.update(units_new=0, units_removed=0, units_confidence="derived")
    btype = "SFD" if ptype.startswith(("NHC Residential", "NHC SFR")) else "OTHER"
    return dict(out, building_type_std=btype, type_confidence="inferred")


def pid_to_pin(parcels: pd.DataFrame) -> dict[str, str]:
    """County PID → OneMap parcel id (37129 + PIN); PIDs with more than one PIN are left out."""
    p = parcels.assign(PID=_clean(parcels["PID"]), PIN=_clean(parcels["PIN"]))
    p = p.loc[(p["PID"] != "") & (p["PIN"] != "")].drop_duplicates(["PID", "PIN"])
    p = p.loc[~p["PID"].duplicated(keep=False)]
    return dict(zip(p["PID"], COUNTY + p["PIN"], strict=True))


def jurisdictions(df: pd.DataFrame, place: pd.Series) -> pd.Series:
    """Place GEOID of the point; no place → unincorporated county; no point → DISTRICT label, else county."""
    has_point = (
        pd.to_numeric(df["Lat"], errors="coerce").notna() & pd.to_numeric(df["Lon"], errors="coerce").notna()
    )
    by_point = place.astype("string").fillna(COUNTY)
    by_label = _clean(df["DISTRICT"]).map(DISTRICTS).fillna(COUNTY)
    return by_point.where(has_point, by_label).astype("string")


def build(
    raw: pd.DataFrame, place: pd.Series, pins: dict[str, str] | None = None, state: str = "NC"
) -> pd.DataFrame:
    """Raw layer attributes + each row's place GEOID (None outside places) → `permits` rows."""
    df = raw.copy()
    df["place"] = place.reindex(df.index)
    df["issue_date"] = epoch_ms_to_timestamp(df["ISSUE_DATE"]).dt.normalize()
    df["status"] = _clean(df["PERMIT_STATUS"])
    job_master = df["DESCRIPTION"].map(lambda v: isinstance(v, str) and bool(JOB_MASTER.search(v)))
    df = df.loc[df["issue_date"].notna() & ~df["status"].isin(NOT_ISSUED) & ~job_master].copy()
    df["ptype"] = df["PERMIT_TYPE"].astype("string").fillna("")  # exact: one type ends in a space
    df["wclass"] = _clean(df["WORK_CLASS"])
    desc = df["DESCRIPTION"].where(df["DESCRIPTION"].map(lambda v: isinstance(v, str)), "")
    facts = pd.DataFrame(
        [classify(p, w, d) for p, w, d in zip(df["ptype"], df["wclass"], desc, strict=True)], index=df.index
    )
    pid = _clean(df["PID"])
    final = epoch_ms_to_timestamp(df["FINALED_DATE"]).dt.normalize()
    out = pd.DataFrame(
        {
            "state": state,
            "permit_id": _clean(df["PERMIT_NUMBER"]).replace("", pd.NA),
            "parcel_id": pid.map(pins or {}).astype("string"),
            "jurisdiction_geoid": jurisdictions(df, df["place"]),
            "issue_year": df["issue_date"].dt.year.astype("Int64"),
            "issue_date": df["issue_date"],
            "date_precision": "day",
            "application_date": epoch_ms_to_timestamp(df["APPLICATION_DATE"]).dt.normalize(),
            "final_date": final,
            "final_date_type": pd.Series("final_inspection", index=df.index, dtype="string").where(
                final.notna()
            ),
            "permit_class_raw": (df["ptype"].str.strip() + " | " + df["wclass"]).astype("string"),
            "zoning_raw": _clean(df["MAIN_ZONE"]).replace("", pd.NA),
            "valuation_usd": pd.to_numeric(df["VALUATION"], errors="coerce").where(lambda v: v >= 0),
            "floor_area_sqft": pd.to_numeric(df["SQUARE_FEET"], errors="coerce").where(lambda v: v > 0),
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


def download_parcels(store: DataStore, *, refresh: bool = False) -> pd.DataFrame:
    """PID and PIN of every county parcel (no geometry, no owner fields)."""
    from lotline.io.arcgis import download_layer

    return download_layer(
        PARCELS_URL,
        store=store,
        source=SOURCE,
        license=LICENSE,
        adapter=ADAPTER,
        adapter_version=VERSION,
        name="parcel_pins",
        out_fields="OBJECTID,PID,PIN",
        geometry=False,
        refresh=refresh,
    )


def load(state: str, store: DataStore, *, refresh: bool = False) -> pd.DataFrame:
    from lotline import geo

    if state.upper() != "NC":
        raise ValueError(f"{SOURCE} covers New Hanover County, North Carolina only, not {state}")
    raw = download(store, refresh=refresh)
    pins = pid_to_pin(download_parcels(store, refresh=refresh))
    lon = pd.to_numeric(raw["Lon"], errors="coerce")
    lat = pd.to_numeric(raw["Lat"], errors="coerce")
    place = geo.place_or_township(lon, lat, state, store, refresh=refresh)
    return validate(build(raw, place, pins, state=state), TABLE)
