"""City-County of Durham building permits (hosted ArcGIS layer "All Building Permits") → canonical `permits`.

One row per building permit, October 2007 to the present, edited daily. City-County Inspections issues
permits for both the City of Durham and unincorporated Durham County, and the layer has **no jurisdiction
field**, so each permit is placed by location (see *Jurisdiction* below).

**Kept rows.** Permits with an issue date whose status is not Void, Disapproved or Received (voided permits
are mostly re-issued under a new number; disapproved and received ones were never issued).

**Building type** comes from `BLD_Type`, the type the city records for the building:

| BLD_Type | building_type_std | Plausible DWELLING_UNITS | Derived when missing or implausible |
|---|---|---|---|
| Single Family House | SFD | 1 | 1 |
| Modular Unit with Single Family occupancy | SFD (type inferred) | 1 | 1 |
| Townhouse | TH | 1 or more (some permits cover a whole row) | 1 |
| Accessory Dwelling | ADU (`adu_type` unknown) | 1 | 1 |
| Duplex | U2 | 1 or 2 (each side is often its own permit) | unknown |
| 3-4 Residential Units | U3_4 | 3 or 4 | unknown |
| 5+ Residential Units | MF5 | 5 or more | unknown |
| Mobile Home | OTHER (manufactured; BPS excludes it) | 1 | 1 |
| anything else | OTHER (UNKNOWN if blank) | not used | unknown |

A multifamily permit whose reported count of 2 or more contradicts its label (a "5+" building reported
with 4 units, a "Duplex" with 3) is re-typed by its count with `type_confidence="inferred"`: the count is
the more specific field (the 2025 "5+" permits with 4 units match the Census BPS 3-4 unit row exactly).

**Units.** Only new construction (`BLDB_ACTIVITY` = NEW) adds units. Reported counts that fit the type are
`units_confidence="reported"`; type-derived ones are `"derived"`; nulls are `"unknown"` (never 0).
Alterations, additions, foundation-only and shell-only permits get null `units_new`: their DWELLING_UNITS
often repeats the building's or project's units. Demolitions (DEM) get `units_new = 0` and `units_removed`
from DWELLING_UNITS or the type (SFD, TH, ADU, mobile home → 1; duplex → 2; others unknown).

**Jurisdiction.** In order:

1. The permit's point (the layer's geometry, WGS84) inside the City of Durham corporate limits polygon
   (city's `CoD_Boundary` layer, current as of the latest quarterly annexation) → `3719000` (Durham city);
   outside → `37063` (Durham County, unincorporated). Even-odd ray casting in numpy; no GIS dependency.
2. No point (about 3% of permits, mostly new parcels not yet mapped): the parcel's NC PIN. PINs are
   built from state-plane grid digits, so parcels that share a PIN prefix are neighbours. The permit takes
   the majority side of located permits sharing the longest 8- to 5-digit prefix of its normalised
   10-digit PIN. Checked on located permits (leave-one-PIN-out): 99.5% agreement at 8 digits, 97% at 6.
   **Annexation date (#94).** Today's limits include land annexed after a permit was issued. A located
   permit inside the city that also lies inside an approved annexation (the city's "Consolidated
   Annexation" development cases, `Planning` layer 19, approved from 2013 on) whose approval date
   (`A_STATUS_DATE`) is after the permit's issue date was outside the city when issued → `37063`. Limits:
   annexations approved before 2013 are not in that layer, so 2007-2012 permits on land annexed in
   2007-2012 stay with the city; permits placed by PIN (step 2) are not re-dated.
3. Else a pending-plat parcel ID ("154829-PP221052") takes the majority side of located permits on its
   parent parcel 154829.
4. Else `UNLOCATED_GEOID` (the city, where 96% of located new-construction permits fall). About 0.5% of
   kept permits.

Only non-personal fields are requested: no owner, contractor, applicant, address, project-name, comment or
description fields (`PROJECT_TYPE` and `COMMENTS` hold phone numbers and e-mail addresses).
"""

from __future__ import annotations

import datetime as dt
import json
import re

import numpy as np
import pandas as pd

from lotline.io import DataStore, fetch
from lotline.io.arcgis import download_layer, epoch_ms_to_timestamp, query_url
from lotline.schemas import validate
from lotline.validation import holdout

ADAPTER = "states.nc.durham_permits"
VERSION = "1.0"
SOURCE = "durham_permits"
TABLE = "permits"
LAYER_URL = "https://services2.arcgis.com/G5vR3cOjh6g2Ed8E/arcgis/rest/services/Inspections/FeatureServer/12"
BOUNDARY_URL = (
    "https://services2.arcgis.com/G5vR3cOjh6g2Ed8E/arcgis/rest/services/CoD_Boundary/FeatureServer/1"
)
# Approved "Consolidated Annexation" development cases (polygons; A_STATUS_DATE = council approval), 2013 on.
ANNEX_URL = "https://services2.arcgis.com/G5vR3cOjh6g2Ed8E/arcgis/rest/services/Planning/FeatureServer/19"
ANNEX_WHERE = "A_TYPE='PL_ANEX' AND A_STATUS='APP'"
# The public ArcGIS item of the hosted "Inspections" service (layer 12 is All Building Permits). The Hub item
# f352381d9b3c4949b4aead66f6e62889 points at the older MapServer, which times out.
LANDING_URL = "https://www.arcgis.com/home/item.html?id=c169c12616a54fcc99aac37ff4997a82"
LICENSE = "City of Durham open data (Privacy Notice and Terms of Service on the Durham Open Data Hub)"

DURHAM_CITY_GEOID = "3719000"  # Census place GEOID, City of Durham
DURHAM_COUNTY_GEOID = "37063"  # Durham County: permits outside the city limits (unincorporated)
UNLOCATED_GEOID = DURHAM_CITY_GEOID  # permits with no point, PIN or parent-parcel match (~0.5% of rows)
PIN_PREFIXES = (8, 7, 6, 5)  # longest first: 8-digit cells are ~10 m, 5-digit cells a few km

# Non-personal fields only (no owner, contractor, address, project name, comments or description).
OUT_FIELDS = [
    "OBJECTID",
    "PermitNum",
    "PIN15",
    "PID",
    "ISSUE_DATE",
    "CO_SIGNOFF_DATE",
    "BLDB_ACTIVITY",
    "BLD_Type",
    "Occupancy",
    "TYPE",
    "PmtStatus",
    "DWELLING_UNITS",
    "BLD_Cost",
    "SQFT_FLOOR",
]
DROP_STATUS = {"void", "disapproved", "received"}

# EHC (Expanding Housing Choices, 2019) reform flags live in PROJECT_TYPE, which elsewhere holds phone numbers
# and e-mail addresses. Only rows starting "EHC" are requested (server-side), and only the code plus these
# whitelisted component keywords are kept; the text itself is never stored (Ben, 2026-10-14).
EHC_WHERE = "PROJECT_TYPE LIKE 'EHC%'"
EHC_COMPONENTS = {
    "adu": re.compile(r"\badu\b|accessory", re.I),
    "duplex": re.compile(r"duplex", re.I),
    "flag_lot": re.compile(r"flag[\s-]*lot", re.I),
    "small_lot": re.compile(r"small[\s-]*lot", re.I),
}

# BLD_Type -> (building_type_std, units derived when the reported count is missing or implausible)
BLD_TYPES: dict[str, tuple[str, int | None]] = {
    "single family house": ("SFD", 1),
    "townhouse": ("TH", 1),
    "accessory dwelling": ("ADU", 1),
    "duplex": ("U2", None),
    "3-4 residential units": ("U3_4", None),
    "5+ residential units": ("MF5", None),
    "mobile home": ("OTHER", 1),  # manufactured: BPS excludes these, so they stay out of BPS-comparable types
}
MULTI = {"U2", "U3_4", "MF5"}
PLAUSIBLE = {
    "SFD": (1, 1),
    "TH": (1, None),
    "ADU": (1, 1),
    "U2": (1, 2),
    "U3_4": (3, 4),
    "MF5": (5, None),
    "OTHER": (1, 1),
}
DEMO_REMOVED = {"SFD": 1, "TH": 1, "ADU": 1, "U2": 2}  # mobile homes handled via the OTHER/derived path

PROVENANCE = {
    "title": "City-County of Durham All Building Permits (hosted ArcGIS layer, daily, Oct 2007 to present)",
    "landing_url": LANDING_URL,
    "table": TABLE,
    "cleaning": [
        "Requested fields exclude owner, contractor, address, project-name, comment and description fields "
        "(PROJECT_TYPE and COMMENTS hold phone numbers and e-mail addresses)",
        "Kept: permits with an ISSUE_DATE whose PmtStatus is not Void, Disapproved or Received",
        "building_type_std from BLD_Type (Single Family House SFD, Townhouse TH, Accessory Dwelling ADU, "
        "Duplex U2, 3-4 Residential Units U3_4, 5+ Residential Units MF5, Mobile Home OTHER; Modular Unit "
        "with Single Family occupancy SFD inferred); a multifamily label contradicted by a reported count of "
        "2+ is re-typed by the count (type_confidence inferred)",
        "Units only for new construction (BLDB_ACTIVITY NEW): DWELLING_UNITS kept where it fits the type "
        "(1 SFD/ADU/mobile home, 1+ TH, 1-2 duplex, 3-4, 5+), else SFD/TH/ADU/mobile home → 1 derived, "
        "multifamily → null",
        "Demolitions: units_new 0, units_removed from DWELLING_UNITS or the type (SFD/TH/ADU/mobile 1, "
        "duplex 2)",
        "final_date = CO_SIGNOFF_DATE (certificate of occupancy); parcel_id = PIN15 as published",
        "Jurisdiction by location: permit point inside the City of Durham corporate limits (CoD_Boundary "
        "layer, fetched with the permits) → 3719000, outside → 37063; permits without a point take the "
        "majority side of located permits sharing the longest 8-5 digit prefix of their NC PIN, then of "
        "their parent parcel (pending plats); the rest (~0.5%) go to the city",
        "Annexation date (#94): a located city permit inside an approved Consolidated Annexation case "
        "(Planning layer 19) approved after its issue date goes to the county (37063)",
        "One row per permit number (a permit spanning several parcels is listed once per parcel)",
        "Permits whose side can't be inferred (~0.5%) default to the city (Ben, 2026-10-14): ~92% of located "
        "permits are in the city",
        "reform_flag_raw: 'EHC' plus whitelisted components (adu, duplex, flag_lot, small_lot) for "
        "permits whose PROJECT_TYPE starts 'EHC', fetched by a server-side filter; the text is never stored",
        "Holdout filter applied (NC holdout is Charlotte; no Durham rows are held out)",
    ],
    "limitations": [
        "City limits are today's, corrected by annexation date from 2013 on only: annexations approved "
        "before 2013 are not in the Consolidated Annexation layer, so a 2007-2012 permit on land annexed in "
        "2007-2012 still counts as city; permits placed by PIN are not re-dated",
        "About 3% of permits have no point; their side is inferred from neighbouring PINs (97-99.5% "
        "agreement on located permits) and ~0.5% are assigned to the city by default",
        "5+ and 3-4 unit permits without a plausible DWELLING_UNITS have unknown units (null)",
        "Mixed-use and other Non-Residential buildings with apartments are OTHER with unknown units: their "
        "DWELLING_UNITS mixes in hotels, parking decks and project totals",
        "ADU permits filed as alterations, additions or other work (about 110) have unknown units: the "
        "permit may create the ADU or alter an existing one",
        "Duplex sides are often permitted separately (1 unit each), so permit counts exceed BPS building "
        "counts for duplexes",
        "The city revises records in place (status, CO dates); each pull is a dated raw snapshot",
    ],
}


# --------------------------------------------------------------------------------------------------------
# Geometry helpers (numpy only)
# --------------------------------------------------------------------------------------------------------
def points_in_rings(lon, lat, rings: list[list[list[float]]]) -> np.ndarray:
    """Boolean mask: is each point inside the polygon made of `rings` (even-odd rule, so holes work)?

    Points are sorted by latitude once; each edge then tests only the points in its latitude band.
    """
    x = np.asarray(lon, dtype="float64")
    y = np.asarray(lat, dtype="float64")
    inside = np.zeros(len(x), dtype=bool)
    order = np.argsort(y, kind="stable")
    ys, xs = y[order], x[order]
    for ring in rings:
        r = np.asarray(ring, dtype="float64")
        if len(r) < 3:
            continue
        if not np.array_equal(r[0], r[-1]):
            r = np.vstack([r, r[:1]])
        x1, y1, x2, y2 = r[:-1, 0], r[:-1, 1], r[1:, 0], r[1:, 1]
        lo = np.searchsorted(ys, np.minimum(y1, y2), side="left")
        hi = np.searchsorted(ys, np.maximum(y1, y2), side="left")  # half-open band [min, max)
        for k in np.nonzero(hi > lo)[0]:
            band = slice(lo[k], hi[k])
            x_cross = x1[k] + (ys[band] - y1[k]) * (x2[k] - x1[k]) / (y2[k] - y1[k])
            inside[order[band][xs[band] < x_cross]] ^= True
    return inside


def normalise_pin(pin: pd.Series) -> pd.Series:
    """NC PIN → 10 digits: '0822530923' as is; Durham's '0822-15-53-5325' drops its 5th-6th digits ('15').

    Both forms place a parcel on the same state-plane grid (checked: matching 8-digit cells sit ~12 m apart).
    Anything else (pending-plat IDs such as '154829-PP221052') → <NA>.
    """
    s = pin.astype("string").str.strip()
    digits = s.str.replace("-", "", regex=False)
    ten = s.str.fullmatch(r"\d{10}").fillna(False)
    twelve = s.str.fullmatch(r"\d{4}-\d{2}-\d{2}-\d{4}").fillna(False)
    out = pd.Series(pd.NA, index=pin.index, dtype="string")
    out[ten] = digits[ten]
    out[twelve] = digits[twelve].str[:4] + digits[twelve].str[6:]
    return out


def assign_jurisdiction(df: pd.DataFrame, rings: list) -> pd.Series:
    """GEOID per row: point in polygon, else PIN-prefix majority, else parent parcel, else the default.

    `df` needs `lon`, `lat`, `PIN15` and `PID`.
    """
    has_pt = df["lon"].notna() & df["lat"].notna()
    in_city = pd.Series(np.nan, index=df.index, dtype="float64")
    in_city[has_pt] = points_in_rings(df.loc[has_pt, "lon"], df.loc[has_pt, "lat"], rings).astype(float)

    located = df.loc[has_pt].assign(_city=in_city[has_pt])
    pin10 = normalise_pin(df["PIN15"])
    loc_pin = pin10[has_pt]
    share = pd.Series(np.nan, index=df.index, dtype="float64")
    need = ~has_pt
    for k in PIN_PREFIXES:
        cells = located["_city"].groupby(loc_pin.str[:k]).mean()
        fill = need & share.isna() & pin10.notna()
        share[fill] = pin10[fill].str[:k].map(cells).astype("float64")
    parent = df["PID"].astype("string").str.split("-").str[0]
    cells = located["_city"].groupby(parent[has_pt]).mean()
    fill = need & share.isna() & parent.notna()
    share[fill] = parent[fill].map(cells).astype("float64")

    city = in_city.where(has_pt, (share >= 0.5).astype(float).where(share.notna()))
    geoid = pd.Series(UNLOCATED_GEOID, index=df.index, dtype="string")
    geoid[city.eq(1.0)] = DURHAM_CITY_GEOID
    geoid[city.eq(0.0)] = DURHAM_COUNTY_GEOID
    return geoid


def annexed_after_issue(df: pd.DataFrame, annexations: list[tuple[pd.Timestamp, list]]) -> pd.Series:
    """True for located permits inside an annexation approved after the permit's issue date (#94).

    `df` needs `lon`, `lat` and `issue_date`; `annexations` holds (approval date, rings) per case.
    """
    out = pd.Series(False, index=df.index)
    has_pt = df["lon"].notna() & df["lat"].notna() & df["issue_date"].notna()
    for approved, rings in annexations:
        cand = has_pt & (df["issue_date"] < approved) & ~out
        if not cand.any():
            continue
        inside = points_in_rings(df.loc[cand, "lon"], df.loc[cand, "lat"], rings)
        out[df.index[cand][inside]] = True
    return out


# --------------------------------------------------------------------------------------------------------
# Attribute rules
# --------------------------------------------------------------------------------------------------------
def _dates(values: pd.Series) -> pd.Series:
    """ArcGIS epoch ms → day-precision timestamps in the schema's datetime64[ns]."""
    ms = pd.to_numeric(values, errors="coerce").astype("float64")
    return epoch_ms_to_timestamp(ms).dt.normalize().astype("datetime64[ns]")


def _type_for_count(n: int) -> str | None:
    return "U2" if n == 2 else "U3_4" if n in (3, 4) else "MF5" if n >= 5 else None


def classify(bld_type, occupancy) -> tuple[str, str, int | None]:
    """(building_type_std, type_confidence, derived units) from BLD_Type (and Occupancy for modular units)."""
    if pd.isna(bld_type) or not str(bld_type).strip():
        return "UNKNOWN", "unknown", None
    key = str(bld_type).strip().lower()
    if key in BLD_TYPES:
        btype, derived = BLD_TYPES[key]
        return btype, "high", derived
    if key == "modular unit" and str(occupancy).strip().lower() == "single family":
        return "SFD", "inferred", 1
    return "OTHER", "high", None


def units_for(btype: str, reported, derived) -> tuple[object, str]:
    """(units, units_confidence) for a new-construction permit: reported if plausible, else derived."""
    lo, hi = PLAUSIBLE.get(btype, (1, None))
    if pd.notna(reported) and reported >= lo and (hi is None or reported <= hi):
        return int(reported), "reported"
    if derived is not None:
        return int(derived), "derived"
    return pd.NA, "unknown"


def _row(bld_type, occupancy, activity, reported) -> tuple:
    """(type, type_confidence, units_new, units_removed, units_confidence, is_demolition) for one permit."""
    btype, conf_t, derived = classify(bld_type, occupancy)
    if activity == "DEM":
        if pd.notna(reported) and reported > 0:
            removed, conf_u = int(reported), "reported"
        elif btype in DEMO_REMOVED or derived is not None:
            removed, conf_u = DEMO_REMOVED.get(btype, derived), "derived"
        else:
            removed, conf_u = pd.NA, "unknown"
        return btype, conf_t, 0, removed, conf_u, True
    dwelling = btype in PLAUSIBLE and (btype != "OTHER" or derived is not None)  # OTHER: mobile homes only
    if activity != "NEW" or not dwelling:
        return btype, conf_t, pd.NA, pd.NA, "unknown", False
    if btype in MULTI and pd.notna(reported) and reported >= 2:
        by_count = _type_for_count(int(reported))
        if by_count and by_count != btype:
            btype, conf_t = by_count, "inferred"
    units, conf_u = units_for(btype, reported, derived)
    return btype, conf_t, units, pd.NA, conf_u, False


def ehc_flags(raw: pd.DataFrame) -> pd.Series:
    """PermitNum → 'EHC' or 'EHC:<components>' from rows whose PROJECT_TYPE starts with EHC. Only the code and
    whitelisted component keywords survive; the free text is dropped here."""
    text = raw["PROJECT_TYPE"].astype("string").fillna("")
    ehc = text.str.match(r"\s*EHC", case=False)
    flags = {}
    for permit, value in zip(raw.loc[ehc, "PermitNum"].astype("string").str.strip(), text[ehc], strict=True):
        parts = sorted(k for k, pattern in EHC_COMPONENTS.items() if pattern.search(value))
        flags[permit] = "EHC" + (":" + ",".join(parts) if parts else "")
    return pd.Series(flags, dtype="string")


def build(
    raw: pd.DataFrame,
    rings: list,
    state: str = "NC",
    ehc: pd.Series | None = None,
    annexations: list[tuple[pd.Timestamp, list]] | None = None,
) -> pd.DataFrame:
    """Raw layer attributes (+ lon/lat) and city-limit rings → canonical permits rows (before holdouts).

    `ehc` (from `ehc_flags`) adds the EHC reform flag as `reform_flag_raw`; `annexations` (from
    `download_annexations`) moves permits issued before their land was annexed to the county (#94)."""
    df = raw.copy()
    issue_date = _dates(df["ISSUE_DATE"])
    status = df["PmtStatus"].astype("string").str.strip().str.lower()
    keep = issue_date.notna() & ~status.isin(DROP_STATUS).fillna(False)
    df = df.loc[keep].copy()
    df["issue_date"] = issue_date[keep]
    for col in ("lon", "lat"):
        if col not in df:
            df[col] = np.nan
    df["jurisdiction_geoid"] = assign_jurisdiction(df, rings)
    if annexations:
        later = annexed_after_issue(df, annexations) & df["jurisdiction_geoid"].eq(DURHAM_CITY_GEOID)
        df.loc[later, "jurisdiction_geoid"] = DURHAM_COUNTY_GEOID

    activity = df["BLDB_ACTIVITY"].astype("string").str.strip().str.upper().fillna("")
    reported = pd.to_numeric(df["DWELLING_UNITS"], errors="coerce")
    bld, occ = df["BLD_Type"], df["Occupancy"]
    rows = [_row(bld.at[i], occ.at[i], activity.at[i], reported.at[i]) for i in df.index]
    parts = pd.DataFrame(
        rows,
        index=df.index,
        columns=[
            "building_type_std",
            "type_confidence",
            "units_new",
            "units_removed",
            "units_confidence",
            "is_demolition",
        ],
    )
    raw_class = (
        df["BLD_Type"].astype("string").fillna("")
        + "|"
        + activity.fillna("")
        + "|"
        + df["Occupancy"].astype("string").fillna("")
    )
    out = pd.DataFrame(
        {
            "state": state,
            "permit_id": df["PermitNum"].astype("string").str.strip(),
            "parcel_id": df["PIN15"].astype("string").str.strip().replace("", pd.NA),
            "jurisdiction_geoid": df["jurisdiction_geoid"],
            "issue_year": df["issue_date"].dt.year.astype("Int64"),
            "issue_date": df["issue_date"],
            "date_precision": "day",
            "final_date": _dates(df["CO_SIGNOFF_DATE"]),
            "adu_type": pd.Series("unknown", index=df.index, dtype="string").where(
                parts["building_type_std"].eq("ADU")
            ),
            "permit_class_raw": raw_class,
            "is_conversion": pd.Series(pd.NA, index=df.index, dtype="boolean"),
            "floor_area_sqft": pd.to_numeric(df["SQFT_FLOOR"], errors="coerce").where(lambda s: s > 0),
            "valuation_usd": pd.to_numeric(df["BLD_Cost"], errors="coerce").where(lambda s: s >= 0),
            "source": SOURCE,
            "_oid": df["OBJECTID"],
        },
        index=df.index,
    ).join(parts)
    out["final_date_type"] = pd.Series("certificate_of_occupancy", index=out.index).where(
        out["final_date"].notna()
    )
    flags = ehc if ehc is not None else pd.Series(dtype="string")
    out["reform_flag_raw"] = out["permit_id"].map(flags).astype("string")
    out["units_new"] = out["units_new"].astype("Int64")
    out["units_removed"] = out["units_removed"].astype("Int64")
    out["is_demolition"] = out["is_demolition"].astype("boolean")
    # A permit spanning several parcels is listed once per parcel: keep one row (the latest edit).
    out = out.sort_values(["permit_id", "issue_date", "_oid"])
    out = out.drop_duplicates(["state", "permit_id"], keep="last")
    return out.drop(columns="_oid").reset_index(drop=True)


# --------------------------------------------------------------------------------------------------------
# Download
# --------------------------------------------------------------------------------------------------------
def download(store: DataStore, *, refresh: bool = False, vintage: str | None = None) -> pd.DataFrame:
    return download_layer(
        LAYER_URL,
        store=store,
        source=SOURCE,
        license=LICENSE,
        adapter=ADAPTER,
        adapter_version=VERSION,
        name="all_building_permits",
        out_fields=",".join(OUT_FIELDS),
        geometry=True,
        vintage=vintage,
        refresh=refresh,
    )


def download_ehc(store: DataStore, *, refresh: bool = False, vintage: str | None = None) -> pd.Series:
    """EHC flags only: rows filtered on the server, PROJECT_TYPE reduced to a code immediately."""
    raw = download_layer(
        LAYER_URL,
        store=store,
        source=SOURCE,
        license=LICENSE,
        adapter=ADAPTER,
        adapter_version=VERSION,
        name="ehc_flags",
        where=EHC_WHERE,
        out_fields="OBJECTID,PermitNum,PROJECT_TYPE",
        vintage=vintage,
        refresh=refresh,
    )
    return ehc_flags(raw)


def download_city_limits(store: DataStore, *, refresh: bool = False, vintage: str | None = None) -> list:
    """Rings (WGS84 lon/lat) of the City of Durham corporate limits, fetched through the IO layer."""
    vintage = vintage or dt.date.today().isoformat()
    url = query_url(
        BOUNDARY_URL, where="1=1", outFields="OBJECTID", returnGeometry="true", outSR="4326", f="json"
    )
    path = fetch(
        url,
        store.raw(SOURCE, vintage) / "city_limits" / "city_limits.json",
        store=store,
        source=SOURCE,
        license=LICENSE,
        adapter=ADAPTER,
        adapter_version=VERSION,
        refresh=refresh,
    )
    data = json.loads(path.read_text())
    if "error" in data or not data.get("features"):
        path.unlink(missing_ok=True)
        raise RuntimeError(f"Durham city limits: no features from {BOUNDARY_URL}")
    return [ring for f in data["features"] for ring in f["geometry"]["rings"]]


def download_annexations(
    store: DataStore, *, refresh: bool = False, vintage: str | None = None
) -> list[tuple[pd.Timestamp, list]]:
    """(approval date, rings) of the City of Durham's approved annexations, fetched through the IO layer."""
    vintage = vintage or dt.date.today().isoformat()
    url = query_url(
        ANNEX_URL,
        where=ANNEX_WHERE,
        outFields="A_NUMBER,A_STATUS_DATE",
        returnGeometry="true",
        outSR="4326",
        f="json",
    )
    path = fetch(
        url,
        store.raw(SOURCE, vintage) / "annexations" / "annexations.json",
        store=store,
        source=SOURCE,
        license=LICENSE,
        adapter=ADAPTER,
        adapter_version=VERSION,
        refresh=refresh,
    )
    data = json.loads(path.read_text())
    if "error" in data or not data.get("features") or data.get("exceededTransferLimit"):
        path.unlink(missing_ok=True)
        raise RuntimeError(f"Durham annexations: no complete answer from {ANNEX_URL}")
    out = []
    for f in data["features"]:
        when = epoch_ms_to_timestamp(pd.Series([f["attributes"]["A_STATUS_DATE"]])).dt.normalize().iloc[0]
        if pd.notna(when) and f.get("geometry"):
            out.append((when, f["geometry"]["rings"]))
    return sorted(out, key=lambda t: t[0])


def load(state: str, store: DataStore, *, refresh: bool = False) -> pd.DataFrame:
    vintage = dt.date.today().isoformat()
    rings = download_city_limits(store, refresh=refresh, vintage=vintage)
    ehc = download_ehc(store, refresh=refresh, vintage=vintage)
    annexations = download_annexations(store, refresh=refresh, vintage=vintage)
    raw = download(store, refresh=refresh, vintage=vintage)
    df = build(raw, rings, state=state, ehc=ehc, annexations=annexations)
    df = holdout.apply(
        df, state, geoid_col="jurisdiction_geoid", date_col="issue_date", year_col="issue_year"
    )
    return validate(df, TABLE)
