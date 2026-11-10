"""City of College Station permits (Socrata `hrbn-znt6`, data.cstx.gov) → canonical `permits`.

"Permits - Master Dataset": one row per permit from the city's permitting system, 1989 to the present,
updated daily (203,521 rows of every type on 2026-11-10). College Station coded ADU rules in 2018 and 2023
(`config/reforms/tx.csv`), so its permits give the ADU estimate (D-025) a Texas place outside the four
largest cities. Only the permit types that can build, add or remove a dwelling are downloaded (`WHERE`):
Residential, Multi-Family, Residential Accessory, Accessory, Residential Addition Attached, Addition and
Demolition. Reroofs, trade, pool, irrigation, remodel and commercial-only permits are not.

**Building type and units** (`permit_type | permit_subtype`):

- Residential, Single-Family / Single Family Detached → SFD, 1 (derived).
- Residential, Townhome / Single Family Attached Townhome / 1 Unit Attached New (Townhome) → TH, 1 (derived).
- Residential, Duplex / Duplex Split-Lot → U2, `number_units` if 1-2 (reported), else 2 (derived).
- Residential, Shared Housing → OTHER, `number_units` if 1+ (reported), else unknown.
- Multi-Family, "N Dwelling Units" (N 1-4) → 1 OTHER, 2 U2, 3-4 U3_4; N units (reported when
  `number_units` agrees, else derived).
- Multi-Family, "5 Dwelling Units Or More" → MF5, `number_units` if 5+ (reported), else unknown.
- Multi-Family, None / Multi-Family → by `number_units` if 2+, else unknown.
- **Residential Accessory or Accessory, "Living Quarters" → ADU** (the city's own subtype), 1 (reported).
- Accessory, Addition and Residential Addition Attached permits whose description names an ADU (parser) →
  ADU, 1 (inferred).
- Demolition, Single-Family / Duplex / Multi-Family → SFD / U2 / by `number_units`; `units_removed` 1 / 2 /
  `number_units`.
- Everything else downloaded (garages, carports, patios, storage, pool houses, other demolitions) → OTHER,
  0 (derived).

**ADU kind:** "Living Quarters" accessory permits are detached (`adu_type` detached unless the parser says
otherwise); parser ADUs keep the parser's kind. A "Living Space" attached addition is an addition, not an
ADU, unless its description names one (`lotline.parse.permit_text`; "guest house", "pool house" and similar
words are not ADUs, precision over recall). Dropped: permits whose `current_status` is Void, Withdrawn,
Cancelled or Denied, and permits with no issue date (applications not issued).

**Jurisdiction.** Every row is College Station (4815976): the city issues permits only inside its limits.
`parcel_id` = "48041" + `site_apn` (Brazos CAD account) when present.

**Privacy.** The dataset also holds the site address, subdivision and map location; none of them are
requested (`SELECT`). The description is read only by the parser and never kept.

**License.** No license is stated on the dataset or the portal (as for Dallas). robots.txt allows
`/resource` with a one-second crawl delay; the Socrata client pauses between pages.
"""

from __future__ import annotations

import re

import pandas as pd

from lotline.io import DataStore
from lotline.parse.permit_text import parse_description
from lotline.schemas import validate
from lotline.validation import holdout

ADAPTER = "states.tx.cstx_permits"
VERSION = "1.0"
SOURCE = "cstx_permits"
TABLE = "permits"
DOMAIN = "data.cstx.gov"
DATASET_ID = "hrbn-znt6"
LANDING_URL = "https://data.cstx.gov/Business-and-Economic-Development/Permits-Master-Dataset/hrbn-znt6"
LICENSE = "City of College Station open data portal (no license stated)"
COLLEGE_STATION = "4815976"
BRAZOS_FIPS = "48041"

SELECT = [
    "permit_number",
    "permit_type",
    "permit_subtype",
    "permit_description",  # parser input only, never kept
    "applied_date",
    "issued_date",
    "current_status",
    "number_units",
    "site_apn",
    "valuation",
    "heated_sq_ft",
]
PERSONAL = {"address_1", "address_2", "city", "state", "zip", "site_subdivision", "location"}
TYPES = (
    "Residential",
    "Multi-Family",
    "Residential Accessory",
    "Accessory",
    "Residential Addition Attached",
    "Addition",
    "Demolition",
)
WHERE = "permit_type in (" + ", ".join(f"'{t}'" for t in TYPES) + ")"
DROP_STATUS = re.compile(r"^(void|withdrawn|cancel|denied)", re.I)
SFD_SUB = {"Single-Family", "Single Family Detached"}
TH_SUB = {"Townhome", "Single Family Attached Townhome", "Residential, 1 Unit Attached New (Townhome)"}
DUPLEX_SUB = {"Duplex", "Duplex Split-Lot"}
ADU_SUB = "Living Quarters"
ACCESSORY_TYPES = {"Residential Accessory", "Accessory"}
PARSER_TYPES = {"Residential Accessory", "Accessory", "Residential Addition Attached", "Addition"}
MF_N = re.compile(r"^(\d+) Dwelling Units?")

PROVENANCE = {
    "title": "City of College Station Permits - Master Dataset (1989 on)",
    "landing_url": LANDING_URL,
    "table": TABLE,
    "attribution": "City of College Station, via data.cstx.gov",
    "cleaning": [
        "Server-side filter to permit types Residential, Multi-Family, Residential Accessory, Accessory, "
        "Residential Addition Attached, Addition and Demolition; no address, subdivision or location field "
        "is requested; the description is read only by the ADU parser and never kept",
        "Permits with status Void, Withdrawn, Cancelled or Denied, or without an issue date, are dropped",
        "building_type_std and units from permit_type and permit_subtype (module list); number_units when "
        "it fits the type",
        "ADU: accessory permits of subtype 'Living Quarters' (the city's subtype, detached), plus accessory "
        "and addition permits whose description names an ADU (inferred)",
        "jurisdiction_geoid = College Station (4815976) for every row; parcel_id = '48041' + site_apn",
        "Holdout filter applied (Texas has no holdouts)",
    ],
    "limitations": [
        "No license stated on the dataset or the portal",
        "'Living Quarters' starts in 2016 (Accessory) and 2018 (Residential Accessory); earlier ADUs only "
        "through the description parser",
        "No Census building-size code; multifamily units from number_units or the subtype",
        "Guest and pool houses are not counted as ADUs unless the description names an ADU",
    ],
}


def _clean(s: pd.Series) -> pd.Series:
    return s.astype("string").str.strip().fillna("")


def _units(n) -> float | None:
    v = pd.to_numeric(n, errors="coerce")
    return None if pd.isna(v) else float(v)


def size_type(n: float | None) -> str | None:
    if n is None or n < 2:
        return None
    return "U2" if n == 2 else "U3_4" if n <= 4 else "MF5"


def classify(ptype: str, sub: str, units, description: str) -> dict:
    """building_type_std, type_confidence, adu_type, units_new, units_removed, units_confidence, flags."""
    n = _units(units)
    facts = parse_description(description or "")
    out = dict(adu_type=None, units_new=0, units_removed=0, units_confidence="derived",
               is_demolition=ptype == "Demolition", is_conversion=False)  # fmt: skip
    if ptype in ACCESSORY_TYPES and sub == ADU_SUB:
        kind = facts.adu_type if facts.building_type_std == "ADU" and facts.adu_type else "detached"
        return dict(out, building_type_std="ADU", type_confidence="high", adu_type=kind, units_new=1,
                    units_confidence="reported")  # fmt: skip
    if ptype in PARSER_TYPES and facts.building_type_std == "ADU" and not facts.is_demolition:
        kind = facts.adu_type or "unknown"
        return dict(
            out, building_type_std="ADU", type_confidence="inferred", adu_type=kind, units_new=1,
            units_confidence="inferred",
        )  # fmt: skip
    if ptype == "Demolition":
        if sub == "Single-Family":
            return dict(out, building_type_std="SFD", type_confidence="high", units_removed=1)
        if sub == "Duplex":
            ok = n is not None and 1 <= n <= 2
            return dict(
                out, building_type_std="U2", type_confidence="high", units_removed=int(n) if ok else 2
            )
        if sub == "Multi-Family":
            t = size_type(n)
            if t:
                return dict(out, building_type_std=t, type_confidence="high", units_removed=int(n),
                            units_confidence="reported")  # fmt: skip
            return dict(out, building_type_std="UNKNOWN", type_confidence="unknown", units_removed=None,
                        units_confidence="unknown")  # fmt: skip
        return dict(out, building_type_std="OTHER", type_confidence="high")
    if ptype == "Residential":
        if sub in SFD_SUB:
            return dict(out, building_type_std="SFD", type_confidence="high", units_new=1)
        if sub in TH_SUB:
            return dict(out, building_type_std="TH", type_confidence="high", units_new=1)
        if sub in DUPLEX_SUB:
            ok = n is not None and 1 <= n <= 2
            return dict(out, building_type_std="U2", type_confidence="high", units_new=int(n) if ok else 2,
                        units_confidence="reported" if ok else "derived")  # fmt: skip
        if sub == "Shared Housing" and n and n >= 1:
            return dict(out, building_type_std="OTHER", type_confidence="high", units_new=int(n),
                        units_confidence="reported")  # fmt: skip
        return dict(out, building_type_std="UNKNOWN", type_confidence="unknown", units_new=None,
                    units_confidence="unknown")  # fmt: skip
    if ptype == "Multi-Family":
        m = MF_N.match(sub)
        k = int(m.group(1)) if m else None  # "N Dwelling Units"; "5 Dwelling Units Or More" is a floor
        if k == 1:
            return dict(out, building_type_std="OTHER", type_confidence="high", units_new=1)
        if k and "Or More" not in sub:  # the subtype gives the size; number_units only if it agrees
            ok = n == k
            return dict(out, building_type_std=size_type(k), type_confidence="high", units_new=k,
                        units_confidence="reported" if ok else "derived")  # fmt: skip
        floor = k or 2
        if n is not None and n >= floor:
            return dict(out, building_type_std=size_type(n), type_confidence="high", units_new=int(n),
                        units_confidence="reported")  # fmt: skip
        if k:  # 5 or more, count unknown
            return dict(out, building_type_std="MF5", type_confidence="high", units_new=None,
                        units_confidence="unknown")  # fmt: skip
        return dict(out, building_type_std="UNKNOWN", type_confidence="unknown", units_new=None,
                    units_confidence="unknown")  # fmt: skip
    return dict(out, building_type_std="OTHER", type_confidence="high")


def build(raw: pd.DataFrame, state: str = "TX") -> pd.DataFrame:
    """Raw Socrata rows (text) → `permits` rows."""
    df = raw.copy()
    for c in SELECT:
        if c not in df:
            df[c] = pd.NA
    df["issue_date"] = pd.to_datetime(df["issued_date"].astype("string").str[:10], errors="coerce")
    status = _clean(df["current_status"])
    df = df.loc[df["issue_date"].notna() & ~status.str.match(DROP_STATUS)].copy()
    ptype, sub = _clean(df["permit_type"]), _clean(df["permit_subtype"])
    desc = df["permit_description"].astype("string").fillna("")
    facts = pd.DataFrame(
        [classify(t, s, u, d) for t, s, u, d in zip(ptype, sub, df["number_units"], desc, strict=True)],
        index=df.index,
    )
    apn = _clean(df["site_apn"]).str.replace(r"\s+", "", regex=True)
    out = pd.DataFrame(
        {
            "state": state,
            "permit_id": _clean(df["permit_number"]).replace("", pd.NA),
            "parcel_id": (BRAZOS_FIPS + apn).where(apn != "", pd.NA).astype("string"),
            "jurisdiction_geoid": COLLEGE_STATION,
            "issue_year": df["issue_date"].dt.year.astype("Int64"),
            "issue_date": df["issue_date"],
            "date_precision": "day",
            "application_date": pd.to_datetime(df["applied_date"].astype("string").str[:10], errors="coerce"),
            "permit_class_raw": ptype + " | " + sub,
            "valuation_usd": pd.to_numeric(df["valuation"], errors="coerce").where(lambda v: v >= 0),
            "floor_area_sqft": pd.to_numeric(df["heated_sq_ft"], errors="coerce").where(lambda v: v > 0),
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


def download(store: DataStore, *, refresh: bool = False, vintage: str | None = None) -> pd.DataFrame:
    from lotline.io.socrata import download_dataset

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
        name="permits_master",
        vintage=vintage,
        pause=1.0,  # robots.txt Crawl-delay 1
        refresh=refresh,
    )


def load(state: str, store: DataStore, *, refresh: bool = False) -> pd.DataFrame:
    if state.upper() != "TX":
        raise ValueError(f"{SOURCE} covers College Station, Texas only, not {state}")
    df = build(download(store, refresh=refresh), state=state)
    df = holdout.apply(df, "TX", geoid_col="jurisdiction_geoid", date_col="issue_date", year_col="issue_year")
    return validate(df, TABLE)
