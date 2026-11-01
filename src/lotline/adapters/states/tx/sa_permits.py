"""City of San Antonio building permits (Development Services, Accela) → canonical `permits`.

San Antonio publishes the permits it has issued since its move to Accela (2020-07-20) as two CSV files on
Open Data SA (Creative Commons Attribution): "Permits issued 2020-2024" and "Permits issued" (2025 on). Each
row has the permit type, number, project name, work type, address, submitted and issued dates, declared
valuation, floor area, and the council district (`CD`), neighborhood conservation district and historic
district. There is **no unit count**. San Antonio's 2023 ADU amendments (effective 2023-01-01,
TX-4865000-adu-2023) and its own ADU permit type ("Res Accessory Dwelling Permit") make it a treated Texas
city for the ADU estimate (D-025), with about two and a half years before the change and three after.

**Access.** The CSVs are downloaded from their `/dataset/<id>/resource/<id>/download` links, which
robots.txt allows; the CKAN API (`/api/`) and DataStore (`/datastore/`) are disallowed and never used.

**Rows kept** (`PERMIT_TYPES`): new residential buildings, ADUs, residential accessory buildings and
additions, residential foundations, new commercial buildings and demolitions. Repairs, fences, trade, sign
and garage-sale permits are not kept.

**One row per permit.** A permit revised after issue appears once per revision (same number and issue
date, later submitted date): the row with the earliest submitted date is kept. A combination permit can
carry several permit types under one number; the type that matters most here wins (`PERMIT_TYPES` order).

**Building type and units:**

- **Res Accessory Dwelling Permit** → `ADU`, 1 unit (`derived`; type `high`, the city's own type), with the
  description parser's attached / detached / conversion type from the project name when it names one;
- **Res New Building Permit** (one- and two-family dwellings and townhouses under the residential code) →
  `SFD`, 1 unit (`derived`, type `inferred`), unless the parser reads a duplex or another type in the
  project name (`inferred`). Duplexes are rare in the names (a handful a year), so BPS stays the source for
  2–4 unit homes;
- residential accessory buildings and additions: 0 units (`derived`) unless the parser names an ADU
  (`inferred`);
- residential foundations: 0 units (`derived`): the home is counted on its building permit;
- new commercial buildings: the parser's type and count from the project name (`inferred`), else unknown
  (most are not housing, but nothing in the row says which);
- demolitions: `is_demolition`, 0 new units; `units_removed` from the parser, else unknown.

**Jurisdiction.** San Antonio also issues permits in its extraterritorial jurisdiction (ETJ): the address
reads "City of San Antonio ETJ" and the council district is 0. Those permits are **not** San Antonio's
(4865000) but the Bexar County remainder's (48029), so the city's permits line up with its own parcels.
Census BPS files the ETJ permits under San Antonio, so a V0 comparison with BPS adds them back. Parts of
the ETJ lie in neighbouring counties; all of it is filed under Bexar here (see limitations).

**Dates.** `issue_date` = `DATE ISSUED` (day); `application_date` = `DATE SUBMITTED` (the earliest).
The files hold no completion date.

**Other fields.** `permit_id` = `PERMIT #`; `permit_class_raw` = permit type | work type;
`valuation_usd` = `DECLARED VALUATION`; `floor_area_sqft` = `AREA (SF)`. No parcel number.

**Privacy.** The files also hold the primary contact's name, the address and coordinates. The contact,
coordinates and location are never read (`READ_COLUMNS`); the address is read only to find ETJ permits and
the project name only for the parser (it often holds an owner's name); neither is kept.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pandas as pd

from lotline.io import DataStore
from lotline.io.http import fetch
from lotline.parse.permit_text import parse_description
from lotline.schemas import validate

ADAPTER = "states.tx.sa_permits"
VERSION = "1.0"
SOURCE = "sa_permits"
TABLE = "permits"
DATASET = "05012dcb-ba1b-4ade-b5f3-7403bc7f52eb"
LANDING_URL = "https://data.sanantonio.gov/dataset/building-permits"
LICENSE = "CC-BY (City of San Antonio open data, Creative Commons Attribution)"
RESOURCES = {
    "permits_2020_2024": "c22b1ef2-dcf8-4d77-be1a-ee3638092aab",
    "permits_current": "c21106f9-3ef5-4f3a-8604-f992b4db7512",
}
SAN_ANTONIO = "4865000"
BEXAR_REMAINDER = "48029"

ADU = "Res Accessory Dwelling Permit"
NEW_RES = "Res New Building Permit"
ACCESSORY = ("Res Accessory-Addition Permit", "Accessory Building Permit")
FOUNDATION = "Res Foundation Permit"
NEW_COMM = "Comm New Building Permit"
DEMOLITION = "Demolition Permit"
PERMIT_TYPES = [ADU, NEW_RES, DEMOLITION, *ACCESSORY, FOUNDATION, NEW_COMM]  # priority for shared numbers
READ_COLUMNS = [
    "PERMIT TYPE",
    "PERMIT #",
    "PROJECT NAME",  # parser input only, never kept
    "WORK TYPE",
    "ADDRESS",  # ETJ test only, never kept
    "DATE SUBMITTED",
    "DATE ISSUED",
    "DECLARED VALUATION",
    "AREA (SF)",
    "CD",
]
PERSONAL = {"PRIMARY CONTACT", "LOCATION", "X_COORD", "Y_COORD"}

PROVENANCE = {
    "title": "City of San Antonio building permits issued (Development Services, since 2020-07)",
    "landing_url": LANDING_URL,
    "table": TABLE,
    "cleaning": [
        "Two CSVs (2020-2024 and 2025 on) from the /dataset/ download links; the CKAN API and DataStore, "
        "disallowed by robots.txt, are never used",
        "The primary contact, location and coordinates are never read; the address (ETJ test) and project "
        "name (description parser) are read in memory and never kept",
        "Kept: new residential and commercial buildings, ADUs, residential accessory buildings and "
        "additions, residential foundations, demolitions; one row per permit number (earliest submitted "
        "revision)",
        "ADU = 'Res Accessory Dwelling Permit' (1 unit, derived); new residential building = SFD 1 unit "
        "(derived) unless the parser reads another type; accessory, addition and foundation permits 0 units; "
        "new commercial buildings and demolitions from the parser, else unknown",
        "Permits in the ETJ (address 'City of San Antonio ETJ' or council district 0) filed under the Bexar "
        "County remainder (48029), the rest under San Antonio (4865000)",
        "issue_date = DATE ISSUED; application_date = DATE SUBMITTED; valuation_usd = DECLARED VALUATION; "
        "floor_area_sqft = AREA (SF)",
    ],
    "limitations": [
        "Starts 2020-07-20 (Accela); 2020 is a part year",
        "No unit count: new residential buildings are counted as one house each unless the project name says "
        "otherwise, and apartments only where the project name gives a count; use BPS for 2-4 and 5+ units",
        "ETJ permits are all filed under Bexar County although parts of the ETJ lie in neighbouring "
        "counties; BPS counts them under San Antonio",
        "No completion date and no parcel number",
    ],
}


def resource_url(resource_id: str) -> str:
    return f"https://data.sanantonio.gov/dataset/{DATASET}/resource/{resource_id}/download"


def download_files(store: DataStore, *, vintage: str | None = None, refresh: bool = False) -> dict[str, Path]:
    vintage = vintage or dt.date.today().isoformat()
    return {
        name: fetch(
            resource_url(rid),
            store.raw(SOURCE, vintage) / f"{name}.csv",
            store=store,
            source=SOURCE,
            license=LICENSE,
            adapter=ADAPTER,
            adapter_version=VERSION,
            refresh=refresh,
        )
        for name, rid in RESOURCES.items()
    }


def read_raw(paths: dict[str, Path]) -> pd.DataFrame:
    frames = [
        pd.read_csv(p, dtype=str, encoding="utf-8-sig", na_values=["NULL"], usecols=READ_COLUMNS)
        for p in paths.values()
    ]
    return pd.concat(frames, ignore_index=True)


def _clean(s: pd.Series) -> pd.Series:
    return s.astype("string").str.strip().fillna("")


def _date(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, errors="coerce", format="mixed").dt.normalize()


def is_etj(address: pd.Series, district: pd.Series) -> pd.Series:
    """Permits outside the city limits: the address says ETJ, or the council district is 0."""
    return _clean(address).str.contains(r"\bETJ\b", case=False, regex=True) | (_clean(district) == "0")


def classify(ptype: str, text: str) -> dict:
    """building_type_std, type_confidence, adu_type, units_new, units_removed, units_confidence, flags."""
    facts = parse_description(text)
    out = dict(adu_type=None, units_new=None, units_removed=None, units_confidence="unknown",
               is_demolition=ptype == DEMOLITION, is_conversion=facts.is_conversion)  # fmt: skip
    adu_type = facts.adu_type or "unknown"
    if ptype == ADU:
        out.update(adu_type=adu_type, units_new=1, units_removed=0, units_confidence="derived")
        return dict(out, building_type_std="ADU", type_confidence="high")
    if ptype == DEMOLITION:
        out.update(units_new=0, units_removed=facts.units_removed,
                   units_confidence="inferred" if facts.units_removed is not None else "unknown")  # fmt: skip
        return dict(out, building_type_std=facts.building_type_std or "UNKNOWN", type_confidence="inferred")
    if ptype in ACCESSORY and facts.building_type_std == "ADU" and not facts.is_demolition:
        out.update(adu_type=adu_type, units_new=1, units_removed=0, units_confidence="inferred")
        return dict(out, building_type_std="ADU", type_confidence="inferred")
    if ptype in ACCESSORY or ptype == FOUNDATION:
        out.update(units_new=0, units_removed=0, units_confidence="derived")
        btype = "OTHER" if ptype in ACCESSORY else "UNKNOWN"
        return dict(out, building_type_std=btype, type_confidence="high")
    read = facts.building_type_std not in (None, "ADU") and facts.units_new
    if ptype == NEW_RES and not read:
        out.update(units_new=1, units_removed=0, units_confidence="derived")
        return dict(out, building_type_std="SFD", type_confidence="inferred")
    if read:  # new residential building of another type, or a commercial building the parser reads
        out.update(units_new=facts.units_new, units_removed=0, units_confidence="inferred")
        return dict(out, building_type_std=facts.building_type_std, type_confidence="inferred")
    return dict(out, building_type_std="UNKNOWN", type_confidence="unknown")


def build(raw: pd.DataFrame, state: str = "TX") -> pd.DataFrame:
    """Raw CSV rows → `permits` rows."""
    df = raw.copy()
    df["ptype"] = _clean(df["PERMIT TYPE"])
    df["permit_id"] = _clean(df["PERMIT #"])
    df["issue_date"] = _date(df["DATE ISSUED"])
    df["submitted"] = _date(df["DATE SUBMITTED"])
    df = df.loc[df["ptype"].isin(PERMIT_TYPES) & (df["permit_id"] != "") & df["issue_date"].notna()].copy()
    df["rank"] = df["ptype"].map({t: i for i, t in enumerate(PERMIT_TYPES)})
    df = df.sort_values(["permit_id", "rank", "submitted"], na_position="last")
    df = df.drop_duplicates("permit_id", keep="first").reset_index(drop=True)
    text = df["PROJECT NAME"].where(df["PROJECT NAME"].notna(), "")
    facts = pd.DataFrame([classify(t, s) for t, s in zip(df["ptype"], text, strict=True)], index=df.index)
    etj = is_etj(df["ADDRESS"], df["CD"])
    out = pd.DataFrame(
        {
            "state": state,
            "permit_id": df["permit_id"].astype("string"),
            "parcel_id": pd.Series(pd.NA, index=df.index, dtype="string"),
            "jurisdiction_geoid": etj.map({True: BEXAR_REMAINDER, False: SAN_ANTONIO}).astype(str),
            "issue_year": df["issue_date"].dt.year.astype("Int64"),
            "issue_date": df["issue_date"],
            "date_precision": "day",
            "application_date": df["submitted"],
            "permit_class_raw": df["ptype"] + " | " + _clean(df["WORK TYPE"]),
            "valuation_usd": pd.to_numeric(df["DECLARED VALUATION"], errors="coerce").where(lambda v: v >= 0),
            "floor_area_sqft": pd.to_numeric(df["AREA (SF)"], errors="coerce").where(lambda v: v > 0),
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
    return read_raw(download_files(store, refresh=refresh))


def load(state: str, store: DataStore, *, refresh: bool = False) -> pd.DataFrame:
    if state.upper() != "TX":
        raise ValueError(f"{SOURCE} covers San Antonio, Texas only, not {state}")
    return validate(build(download(store, refresh=refresh), state=state), TABLE)
