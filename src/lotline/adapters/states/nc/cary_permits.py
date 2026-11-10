"""Town of Cary building permit applications (open data portal) → canonical `permits`.

Cary publishes its permit applications on its open-data portal (data.townofcary.org, dataset
`permit-applications`, BLDS layout, updated daily, CC0 1.0 on the dataset page): one row per **application**
since January 2019, with the permit type (Census BPS-style codes: B101 new detached house, B102 townhouse,
B105 5+ family, B434 residential alteration/addition ...), the work class (New / Existing), the status, the
Wake PIN, a housing-unit count and a free-text description. Cary is NC's seventh-largest place (2020 Census)
and sits mostly in Wake County, so its permits widen the NC ADU panel (D-025) beyond Raleigh, Durham,
Greensboro and the Mecklenburg towns.

**Download by hand.** data.townofcary.org/robots.txt disallows `/api/` and `/explore/dataset/*/download`
for every user agent, so nothing here fetches from the portal. A person exports the whole dataset as CSV in a
browser (`EXPORT_URL`) and registers it (see `MISSING`); the adapter reads the latest registration, which is
recorded in `manifest.jsonl` like any download.

**Kept rows.** Building and demolition permits (`Permit Type Mapped` Building / Demolition) that were issued
(an `Issue Date`) and not cancelled (`Status Current Mapped` "Permit Cancelled": rejected, withdrawn, expired
applications). Trade permits (mechanical, electrical, plumbing, solar) are dropped: they never add homes.
Expired permits stay (they were issued, as BPS counts them).

**Activity.** `Work Class` "New" builds; a demolition permit type (B645 ...) demolishes; the rest are
alterations.

**Building type and units** (`config/crosswalks/nc_cary_permit_types.csv`, one row per permit type):

- `dwelling` (B101 SFD, B102 townhouse): `Housing Units` when it is 1 → `reported`, else 1 (`derived`);
- `multi` (B103-B105): `Housing Units` when it fits the type (2; 3-4; 5+) → `reported`; else B103 gives 2
  (`derived`) and B104/B105 leave the units unknown;
- `adu` (the dedicated "ADU" permit type): ADU, 1 unit (`derived`);
- `accessory`, `alteration` and `nonresidential` types, and any type on a Non-Residential application: 0 units
  (`derived`);
- **accessory dwelling units** on alteration, accessory and garage/shed permits (B434, B417, B438): Cary
  files nearly every ADU there, with the ADU named only in the description, so `adu_from_text` reads it (see
  its docstring) → `ADU`, 1 unit, `inferred`. Before ACT 32 (effective 2025-06-02) Cary called an ADU
  inside or attached to the house a **utility dwelling unit** (UDU: its own kitchen, bath and outside
  entrance), so "UDU" counts as an ADU too. The shared parser (`lotline.parse.permit_text`) misses common
  Cary phrasings ("ADU ADDITION W/ PORCH", "Remodel Lower Level for ADU") because it reads an ADU only as a
  new dwelling, so Cary uses its own narrow rule and takes only the parser's conversion flag;
- a new house (B101) whose description also names an ADU stays one SFD: the ADU is not counted from it
  (precision over recall; the report counts these);
- demolitions: `units_new` 0; `units_removed` from the type (B645 1, B646 2) or from `Housing Units`;
- a permit type not in the crosswalk: 0 units on a Non-Residential application, unknown otherwise.

**Jurisdiction** (`Jurisdiction`): TC (Town of Cary, Wake side) and CC (the Chatham County side of Cary,
west of about -78.88 longitude, no PINs) → Cary 3710740. With CC, new one-unit homes match Census BPS for
Cary within about 1% in 2020-2025 (3% in 2022); without it they fall short by up to 9%. The other codes (TOM
Morrisville, WC Wake County, APEX, RTP: 331 of 88,219 rows on 2026-11-10) are sites Cary inspects outside its
limits and are dropped.

**Parcel.** `parcel_id` = the Wake PIN, left-padded to 10 digits (the export drops the leading 0 of Cary's
07xxxxxxxx PINs). The Wake roll carries the same 10-digit PIN beside its Real Estate ID (the `wake_realestate`
adapter keys parcels by REID and does not read the PIN yet), so the Wake-roll ADU counts can be matched later.
Chatham-side PINs keep the source's digits.

**Other fields.** `permit_id` = `Permit Number`; `application_date` = `Applied Date`; `valuation_usd` =
`Project Cost`; `floor_area_sqft` = `Total SqFt` (0 → null); `final_date` = `CO Issued Date`, else `Completed
Date`. No zoning district.

**Privacy.** The export also holds the site address, coordinates, owner names and addresses and contractor
details. None of them are read (`COLUMNS` is the whole read list). The description is read for the ADU rule,
in memory, and never kept.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

import pandas as pd

from lotline.config import CONFIG_DIR
from lotline.io import DataStore
from lotline.parse.permit_text import parse_description
from lotline.schemas import validate

ADAPTER = "states.nc.cary_permits"
VERSION = "1.0"
SOURCE = "cary_permits"
TABLE = "permits"
LANDING_URL = "https://data.townofcary.org/explore/dataset/permit-applications/"
EXPORT_URL = LANDING_URL + "export/"
LICENSE = (
    "CC0 1.0 Universal (dataset page); portal terms of service: Open Database License (ODbL) v1.0, "
    "attribution to the Town of Cary, North Carolina"
)
CARY = "3710740"
JURISDICTIONS = {"TC": CARY, "CC": CARY}  # Town of Cary in Wake; in Chatham County
TYPES_CSV = CONFIG_DIR / "crosswalks" / "nc_cary_permit_types.csv"
MISSING = (
    "No Cary permit export is registered. data.townofcary.org/robots.txt disallows automated downloads, so "
    f"export the whole dataset as CSV in a browser from {EXPORT_URL} and register it:\n"
    f"  uv run lotline manifest register ~/Downloads/permit-applications.csv --source {SOURCE} "
    f'--url {LANDING_URL} --license "{LICENSE}"'
)

# Canonical name -> header spellings (labels, as the portal's CSV export writes them, and field names),
# compared after lower-casing and dropping everything but letters and digits.
COLUMNS = {
    "permit_number": ("permitnumber", "permitnum"),
    "description": ("description",),
    "status_mapped": ("statuscurrentmapped",),
    "applied": ("applieddate",),
    "issued": ("issuedate", "issueddate"),
    "completed": ("completeddate",),
    "co": ("coissueddate",),
    "pin": ("pin",),
    "jurisdiction": ("jurisdiction",),
    "sqft": ("totalsqft",),
    "units": ("housingunits",),
    "cost": ("projectcost",),
    "class_mapped": ("permitclassmapped",),
    "work_class": ("workclass",),
    "ptype": ("permittype",),
    "ptype_mapped": ("permittypemapped",),
}
PERSONAL = {
    "originaladdress1", "originaladdress2", "originalcity", "originalstate", "originalzip", "latitude",
    "longitude", "geopoint", "ownername", "owneraddress1", "owneraddress2", "ownerzip",
    "contractorcompanyname", "contractorphone", "contractoraddress1", "contractoraddress2", "contractorzip",
}  # fmt: skip
KEPT_TYPES = ("Building", "Demolition")
CANCELLED = ("Permit Cancelled",)
FITS = {"SFD": (1, 1), "TH": (1, 1), "U2": (2, 2), "U3_4": (3, 4), "MF5": (5, 10_000)}
ADU_PERMIT_TYPES = {"B434", "B417", "B438"}

# ---- the ADU rule ------------------------------------------------------------------------------------------
# "ADU", "A.D.U.", "ADUs", "accessory dwelling"; and Cary's pre-June-2025 name for an ADU inside or attached
# to the house, the utility dwelling unit ("UDU", "utility dwelling"): its own kitchen, bath and outside
# entrance (Town of Cary, Planning and Development Services checklist, Oct. 2024); ACT 32 merged it into
# the ADU.
UNIT = (
    r"(?:\bA\.?D\.?U\.?S?\b|\bU\.?D\.?U\.?S?\b"
    r"|\bacc(?:essory|\.)?\s+(?:use\s+)?dwelling|\butility\s*dwelling)"
)
ADU_WORD = re.compile(UNIT, re.I)
UDU_WORD = re.compile(r"\bU\.?D\.?U\.?S?\b|\butility\s*dwelling", re.I)
# The unit already exists, is being taken out, or the text says it is not one: not a new unit.
NOT_NEW = re.compile(
    r"\b(?:remov\w*|demo\w*|abandon\w*|decommission\w*|eliminat\w*|delet\w*)\b[^;]{0,25}"
    + UNIT
    + r"|\bexist\w*\s+(?:(?:de)?tached\s+)?"
    + UNIT
    + r"|\bnot\s+(?:an?\s+)?"
    + UNIT
    + r"|"
    + UNIT
    + r"(?:\s+unit)?\s+(?:\w+\s+){0,2}(?:repair|reroof|re-roof|deck|hvac)\b",
    re.I,
)
DETACHED = re.compile(r"\bdetached\b|\bdet\.?\s|\bDADU\b|\bcottage\b|\bfree[- ]?standing\b", re.I)
INTERNAL = re.compile(
    r"\bconver\w*|\bbasement\b|\bbsmt\b|\bfin(?:ish)?\.?\s+(?:base|bsmt|bonus|attic|2nd|second|lower|upper)"
    r"|\blower\s+level\b|\bupfit\b|\bbonus\s+room\b|\battic\b",
    re.I,
)
ATTACHED = re.compile(r"\battached\b|\baddition\b|\badd\b", re.I)


def adu_from_text(text: str) -> str | None:
    """The ADU type ("detached", "internal_conversion", "attached" or "unknown") when `text` names a new ADU.

    A new ADU is named when the text has the word "ADU" (also "A.D.U.", "ADUs"), "accessory (use) dwelling",
    or Cary's pre-2025 "utility dwelling unit" ("UDU") and none of these: removing, demolishing or abandoning
    the unit; an *existing* unit; "not a UDU"; repairs, re-roofs, decks or HVAC on the unit. "Adult", "guest
    house", "guest suite", "in-law suite" and "kitchenette" are not ADUs. The type is the first that matches:
    detached ("detached", "det.", "cottage"; a unit over a detached garage is detached), then an internal
    conversion (convert, basement, finish a bonus room / attic / lower level), then attached ("attached",
    "addition"; a UDU with no other cue, since a UDU sits inside or against the house); else "unknown".
    Returns None when no new ADU is named.
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
    return "attached" if UDU_WORD.search(text) else "unknown"


# ---- reading -----------------------------------------------------------------------------------------------
def _key(header: str) -> str:
    return re.sub(r"[^a-z0-9]", "", header.lower())


def read(path: Path) -> pd.DataFrame:
    """The registered CSV export → a frame with the canonical `COLUMNS` (as strings), nothing personal."""
    with path.open(newline="", encoding="utf-8-sig") as f:
        sep = csv.Sniffer().sniff(f.readline(), delimiters=";,\t").delimiter
    header = pd.read_csv(path, sep=sep, nrows=0, encoding="utf-8-sig").columns
    by_key = {_key(h): h for h in header}
    pick, missing = {}, []
    for name, spellings in COLUMNS.items():
        hit = next((by_key[s] for s in spellings if s in by_key), None)
        (missing.append(name) if hit is None else pick.__setitem__(hit, name))
    if missing:
        raise ValueError(f"{path.name}: no column for {', '.join(missing)} (headers: {list(header)})")
    df = pd.read_csv(
        path, sep=sep, usecols=list(pick), dtype=str, keep_default_na=False, encoding="utf-8-sig"
    )
    return df.rename(columns=pick)


def permit_types(path: Path = TYPES_CSV) -> dict[str, dict[str, str]]:
    with path.open(newline="") as f:
        return {r["permit_type"]: r for r in csv.DictReader(f)}


def _number(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.astype("string").str.replace(r"[^0-9.\-]", "", regex=True), errors="coerce")


def _date(s: pd.Series) -> pd.Series:
    """Export dates → days. ISO values ("2021-10-01", "2021-10-01T00:00:00-04:00") keep their local date (the
    export writes times in the portal's US/Eastern zone); anything else is parsed as written."""
    s = s.astype("string").str.strip().replace("", pd.NA)
    iso = s.str.extract(r"^(\d{4}-\d{2}-\d{2})", expand=False)
    out = pd.to_datetime(iso, errors="coerce", format="%Y-%m-%d")
    rest = out.isna() & s.notna()
    if rest.any():
        out[rest] = pd.to_datetime(s[rest], errors="coerce", format="mixed").map(
            lambda t: t.tz_localize(None) if t is not pd.NaT and t.tzinfo else t
        )
    return out.dt.normalize()


def pin10(s: pd.Series) -> pd.Series:
    """Wake PINs as 10-digit strings (the export drops the leading zero); other values unchanged; '' → NA."""
    s = s.astype("string").str.strip().str.replace(r"\.0$", "", regex=True).replace("", pd.NA)
    return s.mask(s.str.fullmatch(r"\d{9}", na=False), s.str.zfill(10))


def _fits(t: str, n: object) -> bool:
    if t not in FITS or n is None or pd.isna(n):
        return False
    lo, hi = FITS[t]
    return lo <= n <= hi


def classify(row: pd.Series, types: dict[str, dict[str, str]]) -> dict:
    """building_type_std, type_confidence, adu_type, units_new, units_removed, units_confidence, flags."""
    code, info = row["ptype"], types.get(row["ptype"])
    nonres = row["class_mapped"] == "Non-Residential"
    role = info["role"] if info else ("nonresidential" if nonres else None)
    if nonres and role in ("alteration", "accessory"):
        role = "nonresidential"
    btype = info["building_type_std"] if info else ("OTHER" if role else "UNKNOWN")
    if role == "nonresidential":
        btype = "OTHER"
    derived = int(info["derived_units"]) if info and info["derived_units"] else None
    n = row["n"]
    desc = row["description"]
    conversion = parse_description(desc).is_conversion
    out = dict(adu_type=None, units_new=None, units_removed=None, units_confidence="unknown",
               is_demolition=role == "demolition", is_conversion=conversion)  # fmt: skip
    conf = "high" if info else "unknown"
    if role == "adu":
        out.update(adu_type=adu_from_text(desc) or "unknown", units_new=1, units_removed=0,
                   units_confidence="derived")  # fmt: skip
        return dict(out, building_type_std="ADU", type_confidence="high")
    if code in ADU_PERMIT_TYPES and not nonres:
        adu = adu_from_text(desc)
        if adu:
            out.update(adu_type=adu, units_new=1, units_removed=0, units_confidence="inferred",
                       is_conversion=bool(conversion) or adu == "internal_conversion")  # fmt: skip
            return dict(out, building_type_std="ADU", type_confidence="inferred")
    if role == "demolition":
        ok = _fits(btype, n)
        removed = int(n) if ok else derived
        how = "reported" if ok else "derived" if removed is not None else "unknown"
        out.update(units_new=0, units_removed=removed, units_confidence=how)
    elif role in ("dwelling", "multi") and row["new"]:
        ok = _fits(btype, n)
        units = int(n) if ok else derived
        how = "reported" if ok else "derived" if units is not None else "unknown"
        out.update(units_new=units, units_removed=0 if units is not None else None, units_confidence=how)
    elif role in ("dwelling", "multi", "alteration", "accessory", "nonresidential"):
        out.update(units_new=0, units_removed=0, units_confidence="derived")
    return dict(out, building_type_std=btype, type_confidence=conf)


def build(raw: pd.DataFrame, state: str = "NC") -> pd.DataFrame:
    """Canonical-column export rows → `permits` rows (Cary only)."""
    df = raw.copy()
    for col in COLUMNS:
        df[col] = df[col].astype("string").str.strip().fillna("")
    df["issue_date"] = _date(df["issued"])
    keep = (
        (df["ptype_mapped"].isin(KEPT_TYPES) | df["ptype"].eq("ADU"))  # the ADU type has no mapped type
        & df["issue_date"].notna()
        & ~df["status_mapped"].isin(CANCELLED)
        & df["jurisdiction"].isin(JURISDICTIONS)
    )
    df = df.loc[keep].copy()
    df["new"] = df["work_class"].str.lower().eq("new")
    df["n"] = _number(df["units"])
    types = permit_types()
    facts = pd.DataFrame([classify(r, types) for _, r in df.iterrows()], index=df.index)
    co, done = _date(df["co"]), _date(df["completed"])
    final_type = pd.Series(pd.NA, index=df.index, dtype="string")
    final_type = final_type.mask(done.notna(), "completion").mask(co.notna(), "certificate_of_occupancy")
    out = pd.DataFrame(
        {
            "state": state,
            "permit_id": df["permit_number"].replace("", pd.NA),
            "parcel_id": pin10(df["pin"]),
            "jurisdiction_geoid": df["jurisdiction"].map(JURISDICTIONS),
            "issue_year": df["issue_date"].dt.year.astype("Int64"),
            "issue_date": df["issue_date"],
            "date_precision": "day",
            "application_date": _date(df["applied"]),
            "final_date": co.fillna(done),
            "final_date_type": final_type,
            "permit_class_raw": df["ptype_mapped"] + " | " + df["ptype"] + " | " + df["work_class"],
            "valuation_usd": _number(df["cost"]).where(lambda v: v >= 0),
            "floor_area_sqft": _number(df["sqft"]).where(lambda v: v > 0),
            "source": SOURCE,
        }
    )
    for col in ["building_type_std", "type_confidence", "adu_type", "units_confidence"]:
        out[col] = facts[col].astype("string") if len(df) else pd.Series(dtype="string")
    for col in ["units_new", "units_removed"]:
        out[col] = pd.array(facts[col] if len(df) else [], dtype="Int64")
    for col in ["is_demolition", "is_conversion"]:
        out[col] = pd.array(facts[col] if len(df) else [], dtype="boolean")
    out = out.loc[out["permit_id"].notna()]
    return out.drop_duplicates(["state", "permit_id"], keep="last").reset_index(drop=True)


PROVENANCE = {
    "title": "Town of Cary building permit applications (open data portal, since 2019)",
    "landing_url": LANDING_URL,
    "table": TABLE,
    "attribution": "Contains data from the Town of Cary, North Carolina (data.townofcary.org)",
    "cleaning": [
        "Downloaded by hand as the portal's CSV export (robots.txt disallows automated downloads) and "
        "registered with `lotline manifest register --source cary_permits`",
        "Only the permit number, description, status, dates, PIN, jurisdiction, square feet, housing units, "
        "project cost, permit class, work class and permit type are read; addresses, coordinates, owner and "
        "contractor fields never are; the description is read only by the ADU rule and never kept",
        "Building and demolition permits only; dropped without an Issue Date or with Status Current Mapped "
        "'Permit Cancelled'; expired permits kept; only Jurisdiction TC and CC (Cary's Wake and Chatham "
        "sides)",
        "activity: Work Class New builds, demolition permit types demolish, the rest are alterations",
        "building_type_std and units from the permit type (config/crosswalks/nc_cary_permit_types.csv); "
        "Housing Units when it fits the type (reported), else the type's count (derived)",
        "ADU when the Cary ADU rule (cary_permits.adu_from_text) names a new ADU on a residential "
        "alteration/addition, accessory or garage/shed permit (inferred), or the permit type is ADU",
        "parcel_id = Wake PIN padded to 10 digits; application_date = Applied Date; valuation_usd = Project "
        "Cost; floor_area_sqft = Total SqFt; final_date = CO Issued Date, else Completed Date",
    ],
    "limitations": [
        "Rows are applications, not permits: one application can produce several permits",
        "Starts in January 2019 (the current permit system); no earlier records on the portal",
        "ADUs only where the description names one ('ADU', 'accessory dwelling', or the pre-2025 'UDU' / "
        "'utility dwelling unit'); 'in-law suite', 'guest suite' and kitchenettes are not counted; a new "
        "house whose "
        "description also names an ADU counts as one house",
        "Jurisdiction codes other than TC and CC are dropped; Chatham-side (CC) permits carry no PIN",
        "Applications filed before 2019 in the old system are missing, so 2019 (and some of 2020) "
        "undercounts "
        "new homes against Census BPS",
    ],
}


def _registered(store: DataStore) -> Path:
    entries = store.registered(SOURCE)
    if not entries:
        raise FileNotFoundError(MISSING)
    entry = entries[-1]  # the latest registration
    if store.is_stale(entry):
        raise FileNotFoundError(f"registered Cary export missing or changed since registration: {entry.path}")
    return store.root / entry.path


def load(state: str, store: DataStore, *, refresh: bool = False) -> pd.DataFrame:
    if state.upper() != "NC":
        raise ValueError(f"{SOURCE} covers Cary, North Carolina only, not {state}")
    return validate(build(read(_registered(store)), state=state), TABLE)
