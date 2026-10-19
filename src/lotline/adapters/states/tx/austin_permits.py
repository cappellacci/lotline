"""City of Austin Issued Construction Permits (Socrata `3syk-w9eu`, data.austintexas.gov) → `permits`.

One row per issued permit from the city's AMANDA / AB+C permit system, 1970s to the present, refreshed daily,
public domain. Only **building permits** (`permittype = 'BP'`) that can add or remove dwellings are downloaded
(server-side `$where`): the permit classes carrying a Census Building Permits Survey (BPS) code for new
housing (101-106), additions that increase housing units (436), demolitions (645-649), and the few permits
with a plain class ("Residential" / "Commercial", mostly before 2007) whose work class is "New". Electrical,
plumbing, mechanical and driveway permits for the same project are never downloaded, so a building is
counted once.

**Building type** comes from the Census code inside `permit_class`. The label is either coded
("R- 101 Single Family Houses", "C- 105 Five or More Family Bldgs") or plain ("Residential"); the R-/C- prefix
only says which review track the permit took (`permit_class_mapped`), so a C- 101 is still a house:

| Code | Austin label | `building_type_std` | Plausible `housing_units` | Derived when missing / implausible |
|---|---|---|---|---|
| 101 | Single Family Houses | SFD | 1 | 1 |
| 102 | **Secondary Apartment (the city's ADU class)** | ADU | 1 | 1 |
| 103 | Two Family Bldgs | U2 | 1 or 2 (one permit per side, or per building) | 2 |
| 104 | Three & Four Family Bldgs | U3_4 | 3 or 4 | unknown |
| 105 | Five or More Family Bldgs | MF5 | 5 or more | unknown |
| 106 | Mixed Use | OTHER | 1 or more | unknown |
| 436 | Addition to increase housing units | OTHER (conversion) | n/a (building's units) | description |

R-102 = ADU: the city's own ADU dataset (`687g-qcqy`) says "R-102 Secondary Apartment is the category of
permit that most closely fits the definition of an Accessory Dwelling Unit". HOME (Dec 2023) removed the
secondary-apartment use, so R-102 permits nearly stop after 2023 (90 in 2024, 9 in 2025 on 2026-10-18): a
second or third home on a lot is now filed as **one permit per building** (an R-101 house or an R-103
duplex) whose description names the use, "New THREE UNIT RES." / "TWO UNIT RES.". That phrase goes to
`reform_flag_raw`; the class still sets the type. ADU counts after 2023 are therefore not comparable with
earlier years.

**Demolitions** (645 one-family, 646 two-family, 647 three-four, 648 five+, 649 other buildings):
`units_new = 0`, `units_removed` from `housing_units` where it fits the code, else 645 → 1, 646 → 2; 647/648
without a plausible count and 649 stay unknown.

**Description fallback.** `lotline.parse.permit_text.parse_description` reads the work description only to
fill what the structured fields lack: units of 104/105/106 permits with no plausible `housing_units`, units
added by 436 permits, type and units of plain-class "New" permits, and the ADU kind (attached / detached /
conversion) of 102 permits. Those values are marked `inferred`. The description itself is never stored in the
table.

**Jurisdiction.** The `jurisdiction` field (the city's own location attribute) decides it:
"AUSTIN FULL PURPOSE" and "AUSTIN LTD" (limited-purpose annexation: the city zones and permits there) → Austin
city, place GEOID 4805000. Everything else (Austin's 2- and 5-mile ETJ, other cities' areas, the SB 2038 ETJ
releases, blank) is outside the City of Austin as a permit-issuing place, and those rows are left out (counted
in the PR and in PROVENANCE). The attribute reflects today's boundaries, not those of the issue date.

Only non-personal fields are requested: no contractor or applicant names, organizations, phones or
addresses, no property address (`original_address1`, `permit_location`), no legal description and no
permit-portal link.
"""

from __future__ import annotations

import re

import pandas as pd

from lotline.io import DataStore
from lotline.io.socrata import download_dataset
from lotline.parse.permit_text import parse_description
from lotline.schemas import validate
from lotline.validation import holdout

ADAPTER = "states.tx.austin_permits"
VERSION = "1.1"
SOURCE = "austin_permits"
TABLE = "permits"
DOMAIN = "data.austintexas.gov"
DATASET_ID = "3syk-w9eu"
LANDING_URL = "https://data.austintexas.gov/Building-and-Development/Issued-Construction-Permits/3syk-w9eu"
LICENSE = "Public Domain U.S. Government (City of Austin open data)"
AUSTIN_GEOID = "4805000"  # Census place GEOID, Austin city
TRAVIS_FIPS = "48453"  # tcad_id is the Travis CAD geographic ID

# Never requested: names, organizations, phones and addresses of contractors and applicants, the property
# address, the legal description and the permit-portal link.
PERSONAL_PREFIXES = ("contractor_", "applicant")
PERSONAL = {"original_address1", "permit_location", "legal_description", "link"}
SELECT = [
    "permit_number",
    "permittype",
    "permit_class_mapped",
    "permit_class",
    "work_class",
    "condominium",
    "description",
    "tcad_id",
    "applieddate",
    "issue_date",
    "calendar_year_issued",
    "status_current",
    "completed_date",
    "total_new_add_sqft",
    "total_job_valuation",
    "housing_units",
    "jurisdiction",
    "project_id",
]

# Census BPS code in permit_class -> (building_type_std, plausible units (lo, hi), derived units)
NEW_CODES: dict[str, tuple[str, tuple[int, int | None], int | None]] = {
    "101": ("SFD", (1, 1), 1),
    "102": ("ADU", (1, 1), 1),
    "103": ("U2", (1, 2), 2),  # duplexes are permitted per side (1) or per building (2)
    "104": ("U3_4", (3, 4), None),
    "105": ("MF5", (5, None), None),
    "106": ("OTHER", (1, None), None),  # mixed use: dwellings above or beside nonresidential space
}
DEMOLITION_CODES: dict[str, tuple[str, tuple[int, int | None] | None, int | None]] = {
    "645": ("SFD", (1, 1), 1),
    "646": ("U2", (1, 2), 2),
    "647": ("U3_4", (3, 4), None),
    "648": ("MF5", (5, None), None),
    "649": ("OTHER", None, None),  # all other buildings: no dwelling count can be read
}
CONVERSION_CODE = "436"  # "Addn to increase housing units"
PLAIN_CLASSES = ("Residential", "Commercial")  # no Census code; only work class "New" is downloaded
WHERE = (
    "permittype = 'BP' AND ("
    "permit_class LIKE '_- 10_ %' OR permit_class LIKE '_- 436 %' OR permit_class LIKE '_- 64_ %' "
    "OR (permit_class IN ('Residential', 'Commercial') AND work_class = 'New'))"
)
_CODE = re.compile(r"^[RC]-\s*(\d{3,4})\b")

AUSTIN_JURISDICTIONS = {"AUSTIN FULL PURPOSE", "AUSTIN LTD"}
# Statuses meaning the permit was never validly issued; Expired, Revoked etc. were issued and are kept.
DROP_STATUSES = {"void", "withdrawn", "aborted"}
DROP_STATUS_PREFIXES = ("cancelled",)
HOME_USE = re.compile(r"\b(TWO|THREE)[ -]UNIT RES", re.IGNORECASE)  # HOME two-/three-unit residential use

PROVENANCE = {
    "title": "City of Austin Issued Construction Permits (Development Services, daily)",
    "landing_url": LANDING_URL,
    "table": TABLE,
    "attribution": "City of Austin, Texas - data.austintexas.gov",
    "cleaning": [
        "Socrata pager with an explicit field list: no contractor or applicant names, organizations, phones "
        "or addresses, no property address, legal description or portal link. The work description is "
        "downloaded (raw pages only) for the description fallback and never stored in the table",
        "Server-side filter: building permits (permittype BP) whose permit_class carries a Census code "
        "101-106, 436 or 645-649 (R- or C- prefix), plus plain-class 'Residential'/'Commercial' permits with "
        "work class 'New'",
        "Rows without an issue date, issued before 1970, or with status VOID, Withdrawn, Aborted or "
        "Cancelled... are dropped (never validly issued); Expired permits are kept, as in the BPS",
        "jurisdiction 'AUSTIN FULL PURPOSE' or 'AUSTIN LTD' (limited purpose) → Austin city 4805000; every "
        "other value (Austin ETJ, other cities, SB 2038 ETJ releases, blank) is left out",
        "building_type_std from the Census code: 101 SFD, 102 ADU (the city's 'Secondary Apartment' class, "
        "which its ADU dataset 687g-qcqy names as the ADU class), 103 U2, 104 U3_4, 105 MF5, 106 mixed use "
        "and 436 additions → OTHER; plain classes from the description, else UNKNOWN",
        "Units: housing_units kept where it fits the code (101/102 → 1; 103 → 1 or 2, since duplexes are "
        "permitted per side or per building; 104 → 3-4; 105 → 5+; 106 → 1+); otherwise 101/102 → 1 and "
        "103 → 2 (derived); 104/105/106 from the description (inferred) or null",
        "Demolitions 645-649: is_demolition, units_new 0, units_removed from housing_units where it fits "
        "the code, else 645 → 1, 646 → 2 (derived); 647/648 without a plausible count and 649 unknown",
        "436 'Addition to increase housing units': is_conversion, units_new from the description (inferred) "
        "or null (housing_units there counts the building's units, not units added)",
        "adu_type of 102 permits from the description (attached/detached/internal conversion), else unknown",
        "reform_flag_raw: 'TWO UNIT RES' / 'THREE UNIT RES' when the description names the HOME two- or "
        "three-unit residential use",
        "final_date = completed_date (final_date_type completion); application_date = applieddate",
        "parcel_id = '48453' + tcad_id where it is a Travis CAD geographic ID (digits only); an ID that "
        "starts with a letter (e.g. 'R654373', the account format of the Williamson and Hays appraisal "
        "districts) is kept as written, without a county prefix, because the permit doesn't say which "
        "district it is",
        "permit_class_raw = permit_class | work_class; Holdout filter applied (Texas has no holdouts)",
        "Cross-check only (not loaded): the city's ADU dataset 687g-qcqy (a view of R-102 permits) was read "
        "once under this source as 'adu_permits_687g' (permit number, class, date, status, jurisdiction, "
        "units); all 3,244 of its permits are R-102 rows of 3syk-w9eu (2026-10-18)",
    ],
    "limitations": [
        "The jurisdiction attribute reflects current boundaries, so permits issued before an annexation are "
        "assigned by today's city limits",
        "Austin full- and limited-purpose areas both count as Austin (the city zones and permits both); the "
        "Census place boundary may not include limited-purpose areas",
        "R-102 (ADU) nearly stops after HOME (2024): two- and three-unit uses are one permit per building "
        "(each home an R-101 or R-103), marked only by the description phrase, so ADU series break in 2024",
        "Five-or-more permits sometimes repeat a project total on each building permit (e.g. nine permits "
        "on one parcel in 2022 each report 280 units), so 2019-2023 5+ units exceed the BPS (up to 1.41x in "
        "2022); kept as reported here and counted once when permits are counted (D-008)",
        "Single-family (R-101) units alone run 5-20% below BPS 1-unit units 2010-2025: the BPS files most "
        "ADUs and duplex sides as 1-unit homes. All homes in 1-2 unit buildings (R-101 + R-102 + R-103 vs "
        "BPS 1 + 2 units) are within 10% every year (0.91-1.09; reports/tx/V0.md)",
        "Mixed-use (106) dwellings are OTHER, not MF5: compare 5+ counts with the BPS with and without them",
        "Some 104/105 permits lack a plausible housing_units value; their units come from the description "
        "or stay null",
        "Records are revised in place (status, completion); each pull is a dated raw snapshot",
    ],
}


def _text(values: pd.Series) -> pd.Series:
    return values.astype("string").str.strip().replace("", pd.NA)


def _dates(values: pd.Series) -> pd.Series:
    return pd.to_datetime(values, errors="coerce").dt.normalize().astype("datetime64[ns]")


def class_code(permit_class) -> str | None:
    """The Census code in an Austin permit class ('R- 101 Single Family Houses' → '101'), else None."""
    if permit_class is None or pd.isna(permit_class):
        return None
    m = _CODE.match(str(permit_class).strip())
    return m.group(1) if m else None


def _fits(value, bounds: tuple[int, int | None] | None) -> bool:
    if bounds is None or pd.isna(value):
        return False
    lo, hi = bounds
    return value == int(value) and lo <= value and (hi is None or value <= hi)


def classify(code: str | None, permit_class, units_reported, description) -> dict:
    """Canonical type and unit fields for one permit (see the module docstring for the rules)."""
    text = None if pd.isna(description) else str(description)

    def read():  # the description is parsed only where a structured field is missing
        return parse_description(text)

    out = {
        "building_type_std": "UNKNOWN",
        "type_confidence": "unknown",
        "units_new": pd.NA,
        "units_removed": pd.NA,
        "units_confidence": "unknown",
        "is_demolition": False,
        "is_conversion": pd.NA,
        "adu_type": pd.NA,
    }
    if code in DEMOLITION_CODES:
        btype, bounds, derived = DEMOLITION_CODES[code]
        out.update(building_type_std=btype, type_confidence="high", units_new=0, is_demolition=True)
        if _fits(units_reported, bounds):
            out.update(units_removed=int(units_reported), units_confidence="reported")
        elif derived is not None:
            out.update(units_removed=derived, units_confidence="derived")
        return out
    if code in NEW_CODES:
        btype, bounds, derived = NEW_CODES[code]
        out.update(building_type_std=btype, type_confidence="high", is_conversion=False)
        if _fits(units_reported, bounds):
            out.update(units_new=int(units_reported), units_confidence="reported")
        elif derived is not None:
            out.update(units_new=derived, units_confidence="derived")
        elif (n := read().units_new) is not None and _fits(n, bounds):
            out.update(units_new=n, units_confidence="inferred")
        if btype == "ADU":
            out["adu_type"] = read().adu_type or "unknown"
        return out
    if code == CONVERSION_CODE:
        out.update(building_type_std="OTHER", type_confidence="high", is_conversion=True, units_removed=0)
        if (n := read().units_new) is not None:
            out.update(units_new=n, units_confidence="inferred")
        else:
            out["units_removed"] = pd.NA
        return out
    # plain class ("Residential"/"Commercial", work class New): the description is all there is
    facts = read()
    if facts.building_type_std is not None:
        out.update(building_type_std=facts.building_type_std, type_confidence="inferred")
        if facts.building_type_std == "ADU":
            out["adu_type"] = facts.adu_type or "unknown"
    if facts.units_new is not None:
        out.update(units_new=facts.units_new, units_confidence="inferred")
    out["is_demolition"] = bool(facts.is_demolition) if facts.is_demolition is not None else pd.NA
    return out


def build(raw: pd.DataFrame, state: str = "TX") -> pd.DataFrame:
    """Raw Socrata rows (strings) → canonical permits rows for Austin (before the holdout filter)."""
    df = raw.copy()
    df["_issue"] = _dates(df["issue_date"])
    status = _text(df["status_current"]).str.lower()
    dropped = status.isin(DROP_STATUSES) | status.str.startswith(DROP_STATUS_PREFIXES)
    in_austin = _text(df["jurisdiction"]).str.upper().isin(AUSTIN_JURISDICTIONS)
    keep = df["_issue"].notna() & (df["_issue"].dt.year >= 1970) & ~dropped.fillna(False) & in_austin
    df = df.loc[keep.fillna(False).astype(bool)].copy()

    pclass = _text(df["permit_class"])
    codes = pclass.map(class_code)
    reported = pd.to_numeric(df["housing_units"], errors="coerce")
    parts = pd.DataFrame(
        [classify(codes.at[i], pclass.at[i], reported.at[i], df["description"].at[i]) for i in df.index],
        index=df.index,
    )
    desc = df["description"].astype("string")
    home = desc.str.extract(HOME_USE, expand=False).str.upper()
    cad_id = _text(df["tcad_id"]).str.upper()
    other_cad = cad_id.str.match(r"^[A-Z]").fillna(False).astype(bool)  # e.g. R654373: not a TCAD geo ID
    tcad = cad_id.str.replace(r"\D", "", regex=True).replace("", pd.NA).where(~other_cad)
    sqft = pd.to_numeric(df["total_new_add_sqft"], errors="coerce")
    value = pd.to_numeric(df["total_job_valuation"], errors="coerce")
    final = _dates(df["completed_date"])
    out = pd.DataFrame(
        {
            "state": state,
            "permit_id": _text(df["permit_number"]),
            "parcel_id": (TRAVIS_FIPS + tcad).where(tcad.notna(), cad_id.where(other_cad)),
            "jurisdiction_geoid": AUSTIN_GEOID,
            "issue_year": df["_issue"].dt.year.astype("Int64"),
            "issue_date": df["_issue"],
            "date_precision": "day",
            "application_date": _dates(df["applieddate"]),
            "final_date": final,
            "final_date_type": pd.Series("completion", index=df.index, dtype="string").where(final.notna()),
            "permit_class_raw": pclass.fillna("") + "|" + _text(df["work_class"]).fillna(""),
            "reform_flag_raw": (home + " UNIT RES").where(home.notna()),
            "floor_area_sqft": sqft.where(sqft > 0),
            "valuation_usd": value.where(value >= 0),
            "source": SOURCE,
        },
        index=df.index,
    ).join(parts)
    for col in ("units_new", "units_removed"):
        out[col] = out[col].astype("Int64")
    for col in ("is_demolition", "is_conversion"):
        out[col] = out[col].astype("boolean")
    out["adu_type"] = out["adu_type"].astype("string")
    out = out.loc[out["permit_id"].notna()]
    # Guard: a permit number listed twice keeps its latest issue
    out = out.sort_values(["permit_id", "issue_date"]).drop_duplicates(["state", "permit_id"], keep="last")
    return out.reset_index(drop=True)


def download(store: DataStore, *, refresh: bool = False, vintage: str | None = None) -> pd.DataFrame:
    return download_dataset(
        DOMAIN,
        DATASET_ID,
        select=SELECT,
        where=WHERE,
        store=store,
        source=SOURCE,
        license=LICENSE,
        adapter=ADAPTER,
        adapter_version=VERSION,
        name="issued_construction_permits",
        vintage=vintage,
        refresh=refresh,
    )


def load(state: str, store: DataStore, *, refresh: bool = False) -> pd.DataFrame:
    if state.upper() != "TX":
        raise ValueError(f"{SOURCE} covers Austin, Texas only, not {state}")
    df = build(download(store, refresh=refresh), state="TX")
    df = holdout.apply(df, "TX", geoid_col="jurisdiction_geoid", date_col="issue_date", year_col="issue_year")
    return validate(df, TABLE)
