"""City of Greensboro building permits (Engineering & Inspections) → canonical `permits`.

Greensboro publishes its building permits (not trade permits) as a table in the city's open-data map service:
one row per permit since 1990, with the permit type (Residential / Commercial), the application type (New
Construction, Addition, Total Demolish ...), the occupancy (One Family Residence, Townhouse, Duplex ...), a
unit count (`NumUnits`), the zoning district and a free-text description. Greensboro is NC's third-largest
city and adopted by-right ADUs on 2024-04-16 (`config/reforms/nc.csv`), so its permits give the ADU
estimate (D-025) a third North Carolina adoption.

**Activity** (`ApplicationType`): "New Construction" and "Place on Lot" (manufactured homes) build;
"Total Demolish" demolishes; everything else (alterations, additions, repairs, decks ...) is an alteration.
Permits with a `CancelDate` are dropped; expired permits stay (they were issued, as BPS counts them).

**Building type and units** (`config/crosswalks/nc_gso_occupancy.csv`, one row per occupancy):

- `dwelling` occupancies (one-family house SFD, townhouse TH, duplex U2, mobile home OTHER): `NumUnits` when
  it fits the type (SFD, TH and mobile home 1; duplex 1-2) → `reported`; else the type's count (`derived`);
- `multi` occupancies (apartment building shells, condominiums): a `NumUnits` of 2 or more gives the type
  (2 U2, 3-4 U3_4, 5+ MF5) and the count (`reported`); otherwise the type and units are unknown;
- `apartment_unit` ("Apartment-Individual Units"): Greensboro files one permit per apartment inside a
  building permitted by its shell permit. Some of them (144 in 2021) repeat the building's `NumUnits` on
  every apartment, so these permits never count units (unknown), which keeps buildings from being counted
  twice. Shell permits start in 2019, so multifamily units before 2019 are not in this source;
- `foundation` (foundation-only permits): 0 units (`derived`): the home is counted on its building permit;
- `accessory` (sheds, carports, garages) and `nonresidential` occupancies: 0 units (`derived`);
- an occupancy not in the crosswalk: 0 units on a Commercial permit, unknown on a Residential one;
- **accessory dwelling units:** the description parser (`lotline.parse.permit_text`) names an ADU on a
  one-family, accessory-building or garage permit, or one with no occupancy → `ADU`, 1 unit, `inferred`
  (type and units), with the parser's attached / detached / conversion type. Words such as "guest house"
  or "in-law suite" are not read as ADUs (precision over recall);
- demolitions: `units_new` 0; `units_removed` from `NumUnits` when it fits, else the type's count;
- alterations: 0 units (`derived`) unless the parser reads a conversion that adds units (`inferred`).

**Jurisdiction.** Every row is Greensboro (3728000): the city issues permits only inside its limits
(Guilford County Inspections covers the rest of the county).

**Other fields.** `permit_id` = `PermitNum`; `zoning_raw` = `Zoning`; `valuation_usd` = `TotalCost`;
`floor_area_sqft` = `BuildingSqFt`; `final_date` = `FinalCODate` (certificate of occupancy), else
`FinalInspectionDate` (final inspection). There is no parcel number in the table (`parcel_id` null).

**Privacy.** The table also holds the contractor, owner names and mailing addresses, the site address and
coordinates; none of them are requested (`OUT_FIELDS`). The description sometimes contains an owner's name,
phone number or email, so it is requested only for the parser, read in memory and never kept.
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

ADAPTER = "states.nc.greensboro_permits"
VERSION = "1.0"
SOURCE = "greensboro_permits"
TABLE = "permits"
LAYER_URL = "https://gis.greensboro-nc.gov/arcgis/rest/services/OpenGateCity/OpenData_HRES_DS/MapServer/2"
LANDING_URL = LAYER_URL
LICENSE = "City of Greensboro open data (public records; no license stated)"
GREENSBORO = "3728000"
OCCUPANCY_CSV = CONFIG_DIR / "crosswalks" / "nc_gso_occupancy.csv"

OUT_FIELDS = [
    "Sakey",
    "PermitNum",
    "PermitType",
    "ApplicationType",
    "OccupancyDesc",
    "NumUnits",
    "BuildingSqFt",
    "IssuedDate",
    "CancelDate",
    "FinalInspectionDate",
    "FinalCODate",
    "TotalCost",
    "Zoning",
    "Description",  # parser input only, never kept
]
PERSONAL = {
    "Contractor", "OwnerName", "OwnerName2", "OwnerMailAddress", "OwnerMailAddress2", "OwnerMailCity",
    "OwnerMailState", "OwnerMailZip", "StNumber", "StApt", "StPrefix", "StName", "StType", "StSfxDir",
    "FullAddress", "XCoord", "YCoord", "AdSakey",
}  # fmt: skip
NEW = ("New Construction", "Place on Lot")
DEMOLITION = ("Total Demolish",)
FITS = {"SFD": (1, 1), "TH": (1, 1), "OTHER": (1, 1), "U2": (1, 2)}
ADU_OCCUPANCIES = {"One Family Residence", "Accessory Building/Carport-detached", "Residential Garage", ""}

PROVENANCE = {
    "title": "City of Greensboro building permits (Engineering & Inspections, since 1990)",
    "landing_url": LANDING_URL,
    "table": TABLE,
    "cleaning": [
        "Requested fields exclude the contractor, owner names and mailing addresses, the site address and "
        "coordinates; Description is read only by the description parser and never kept",
        "Permits with a CancelDate are dropped; expired permits are kept",
        "activity from ApplicationType: New Construction / Place on Lot build, Total Demolish demolishes, "
        "the rest are alterations",
        "building_type_std and units from OccupancyDesc (config/crosswalks/nc_gso_occupancy.csv); NumUnits "
        "when it fits the type (reported), else the type's count (derived); apartment shells and "
        "condominiums only from a NumUnits of 2 or more; per-apartment permits never count units; "
        "foundation-only, accessory and nonresidential permits 0 units",
        "ADU when the description parser names one on a one-family, accessory or garage permit (inferred)",
        "jurisdiction_geoid = Greensboro (3728000) for every row; zoning_raw = Zoning; valuation_usd = "
        "TotalCost; floor_area_sqft = BuildingSqFt; final_date = FinalCODate, else FinalInspectionDate",
    ],
    "limitations": [
        "Apartments are counted from building shell permits only (from 2019); per-apartment permits never "
        "count units (some repeat the building's count). Before 2019 the source has no multifamily units",
        "No parcel number; permits cannot be joined to parcels",
        "ADUs only where the description names one ('ADU', 'accessory dwelling'); 'guest house' and "
        "'in-law suite' are not counted",
        "Duplex permits usually carry NumUnits 1: read as one permit per half of the building",
    ],
}


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def occupancies(path: Path = OCCUPANCY_CSV) -> dict[str, dict[str, str]]:
    return {r["occupancy"]: r for r in _read_csv(path)}


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


def classify(row: pd.Series, occ: dict[str, dict[str, str]]) -> dict:
    """building_type_std, type_confidence, adu_type, units_new, units_removed, units_confidence, flags."""
    app = row["app"]
    activity = "new" if app.startswith(NEW) else "demolition" if app.startswith(DEMOLITION) else "alteration"
    info = occ.get(row["occ"])
    role = info["role"] if info else ("nonresidential" if row["ptype"] == "Commercial" else None)
    btype = info["building_type_std"] if info else ("OTHER" if role else "UNKNOWN")
    derived = int(info["derived_units"]) if info and info["derived_units"] else None
    n = pd.to_numeric(row["NumUnits"], errors="coerce")
    facts = parse_description(row["Description"] if isinstance(row["Description"], str) else "")
    out = dict(adu_type=None, units_new=None, units_removed=None, units_confidence="unknown",
               is_demolition=activity == "demolition", is_conversion=facts.is_conversion)  # fmt: skip
    conf = "high" if info else "unknown"
    if facts.building_type_std == "ADU" and row["occ"] in ADU_OCCUPANCIES and not facts.is_demolition:
        out.update(adu_type=facts.adu_type or "unknown", units_new=1, units_removed=0)
        return dict(out, building_type_std="ADU", type_confidence="inferred", units_confidence="inferred")
    if role == "multi":
        mt = multi_type(n)
        btype, conf = (mt, "high") if mt else ("UNKNOWN", "unknown")
    if activity == "demolition":
        out.update(units_new=0)
        if role == "dwelling":
            out.update(units_removed=int(n) if _fits(btype, n) else derived, units_confidence="derived")
        elif role == "multi" and multi_type(n):
            out.update(units_removed=int(n), units_confidence="reported")
        elif role in ("foundation", "accessory", "nonresidential"):
            out.update(units_removed=0, units_confidence="derived")
    elif activity == "new":
        out["units_removed"] = 0
        if role == "dwelling":
            ok = _fits(btype, n)
            out.update(units_new=int(n) if ok else derived, units_confidence="reported" if ok else "derived")
        elif role == "multi" and multi_type(n):
            out.update(units_new=int(n), units_confidence="reported")
        elif role in ("foundation", "accessory", "nonresidential"):
            out.update(units_new=0, units_confidence="derived")
    elif facts.is_conversion and facts.units_new:
        out.update(units_new=facts.units_new, units_removed=facts.units_removed, units_confidence="inferred")
    elif role is not None:
        out.update(units_new=0, units_removed=0, units_confidence="derived")
    return dict(out, building_type_std=btype, type_confidence=conf)


def build(raw: pd.DataFrame, state: str = "NC") -> pd.DataFrame:
    """Raw table attributes → `permits` rows."""
    df = raw.copy()
    df["issue_date"] = epoch_ms_to_timestamp(df["IssuedDate"]).dt.normalize()
    cancelled = pd.to_numeric(df["CancelDate"], errors="coerce").notna()
    df = df.loc[df["issue_date"].notna() & ~cancelled].copy()
    df["app"] = _clean(df["ApplicationType"])
    df["occ"] = _clean(df["OccupancyDesc"])
    df["ptype"] = _clean(df["PermitType"])
    occ = occupancies()
    facts = pd.DataFrame([classify(r, occ) for _, r in df.iterrows()], index=df.index)
    co = epoch_ms_to_timestamp(df["FinalCODate"]).dt.normalize()
    fi = epoch_ms_to_timestamp(df["FinalInspectionDate"]).dt.normalize()
    final_type = pd.Series(pd.NA, index=df.index, dtype="string")
    final_type = final_type.mask(fi.notna(), "final_inspection").mask(co.notna(), "certificate_of_occupancy")
    out = pd.DataFrame(
        {
            "state": state,
            "permit_id": _clean(df["PermitNum"]).replace("", pd.NA),
            "parcel_id": pd.Series(pd.NA, index=df.index, dtype="string"),
            "jurisdiction_geoid": GREENSBORO,
            "issue_year": df["issue_date"].dt.year.astype("Int64"),
            "issue_date": df["issue_date"],
            "date_precision": "day",
            "final_date": co.fillna(fi),
            "final_date_type": final_type,
            "permit_class_raw": df["ptype"] + " | " + df["app"] + " | " + df["occ"],
            "zoning_raw": _clean(df["Zoning"]).replace("", pd.NA),
            "valuation_usd": pd.to_numeric(df["TotalCost"], errors="coerce").where(lambda v: v >= 0),
            "floor_area_sqft": pd.to_numeric(df["BuildingSqFt"], errors="coerce").where(lambda v: v > 0),
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
        out_fields=",".join(OUT_FIELDS),
        geometry=False,
        refresh=refresh,
    )


def load(state: str, store: DataStore, *, refresh: bool = False) -> pd.DataFrame:
    if state.upper() != "NC":
        raise ValueError(f"{SOURCE} covers Greensboro, North Carolina only, not {state}")
    return validate(build(download(store, refresh=refresh), state=state), TABLE)
