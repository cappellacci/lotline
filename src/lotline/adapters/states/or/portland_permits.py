"""City of Portland Residential Building Permits (new units since 1995) → `permits`.

The layer (PortlandMaps `COP_OpenData_PlanningDevelopment/MapServer/89`) holds every permit that created one
or more new residential units, from the Bureau of Development Services' permit database. Its MapServer does
not answer from our network (connection timeouts on 2026-11-04 and 2026-11-05), so the adapter downloads the
full CSV extract the city's ArcGIS Hub item publishes (`opendata.arcgis.com`, item
02d99db039e0428da88262bff513056a, layer 89), through `fetch()`. The extract is a dated copy of the same layer;
its date is recorded in the manifest.

**ADUs.** The city flags them: `IS_ADU` is True on every permit that creates an accessory dwelling unit,
whatever the building type (`NEWTYPE`) or work (`NEWCLASS`). Read with the work class:

- New Construction of an Accessory Dwelling Unit, or of a 1-unit house-type permit: one ADU row (a new
  structure: `detached`).
- New Construction of a Single Family Dwelling, Townhouse or Rowhouse with `NEW_UNITS` >= 2: **two rows**, the
  new house (SFD or TH, `NEW_UNITS` - 1 units) and the ADU (1 unit).
- Alteration: one ADU row (`internal_conversion`, `is_conversion`).
- Addition: one ADU row (`attached`, `is_conversion`).
- Other work (Move, Replacement): one ADU row (`unknown`).

The split (`permit_id` + `#house` / `#adu`) makes a new house and its ADU on one permit visible to D-041's
co-built rule (`model.calibrate_adu.cobuilt`: a new SFD permit on the same parcel within a year), which keys
on parcel and year. Note that the rule as written only recognises SFD houses, so an ADU built on the same
permit as a new townhouse or rowhouse is not flagged co-built (the TH row is written as TH, not relabelled).

**Other permits.** `NEWTYPE` gives the type: Single Family Dwelling → SFD; Townhouse, Rowhouse → TH; Duplex →
U2; Apartments/Condos → by `NEW_UNITS` (2 U2, 3-4 U3_4, 5+ MF5); floating homes and non-residential types →
OTHER. `NEW_UNITS` is the city's count (reported). `is_conversion` is True for Alteration and Addition work,
False for New Construction, unknown otherwise.

**Place and dates.** Only permits inside the city (`PDXBND` = YES) are kept, all assigned to Portland
(4159000); BDS also permits some land outside the city limits, which is left out. `issue_date` = `ISSUEDATE`
(permits without one are dropped), `application_date` = `INDATE`. The layer has no final date. Expired permits
stay: they were issued.

Parcel: `PROPGISID1` (map and taxlot, spaces collapsed). Addresses, work descriptions and owner fields are
not kept.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Iterable
from pathlib import Path

import pandas as pd

from lotline.io import DataStore
from lotline.io.http import fetch
from lotline.schemas import validate
from lotline.validation import holdout

ADAPTER = "states.or.portland_permits"
VERSION = "1.0"
SOURCE = "portland_permits"
TABLE = "permits"
ITEM = "02d99db039e0428da88262bff513056a"
URL = f"https://opendata.arcgis.com/api/v3/datasets/{ITEM}_89/downloads/data?format=csv&spatialRefId=4326"
LAYER_URL = "https://www.portlandmaps.com/od/rest/services/COP_OpenData_PlanningDevelopment/MapServer/89"
LANDING_URL = f"https://www.arcgis.com/home/item.html?id={ITEM}"
LICENSE = "No license stated (City of Portland open data, Bureau of Planning and Sustainability)"
PORTLAND_GEOID = "4159000"

KEEP = [
    "FOLDERNUMB",
    "INDATE",
    "ISSUEDATE",
    "STATUS",
    "NEWCLASS",
    "NEWTYPE",
    "IS_ADU",
    "NEW_UNITS",
    "PROPGISID1",
    "PDXBND",
    "SQFT",
    "VALUATION",
]
HOUSE_TYPES = {"Single Family Dwelling": "SFD", "Townhouse": "TH", "Rowhouse": "TH"}
OTHER_RESIDENTIAL = {"Duplex": "U2"}
ADU_KIND = {"New Construction": "detached", "Alteration": "internal_conversion", "Addition": "attached"}

PROVENANCE = {
    "title": "City of Portland Residential Building Permits (permits creating new units, 1995 to present)",
    "landing_url": LANDING_URL,
    "table": TABLE,
    "cleaning": [
        "Downloaded as the ArcGIS Hub CSV extract of PortlandMaps MapServer/89 (the MapServer itself does "
        "not answer from our network); only permit number, dates, status, work class, building type, ADU "
        "flag, new units, parcel, city-boundary flag, floor area and valuation are kept (no addresses or "
        "text)",
        "Permits without an issue date are dropped; permits outside the city limits (PDXBND = NO) are "
        "dropped",
        "ADU = the city's IS_ADU flag; a new single-family, townhouse or rowhouse permit flagged IS_ADU with "
        "two or more new units is split into a house row and an ADU row (permit_id #house / #adu), so "
        "D-041's co-built rule sees both on the same parcel and year",
        "adu_type from the work class: New Construction detached, Alteration internal_conversion, Addition "
        "attached, otherwise unknown; is_conversion True for Alteration and Addition",
        "building_type_std from NEWTYPE: Single Family Dwelling SFD; Townhouse, Rowhouse TH; Duplex U2; "
        "Apartments/Condos by units (2 U2, 3-4 U3_4, 5+ MF5); other types OTHER; units_new = NEW_UNITS "
        "(reported)",
        "Every row is assigned to Portland (4159000)",
        "Holdout filter applied: Oregon outcomes from 2018 on (V9-OR-TRANSFER) stay hidden unless the caller "
        "unblinds that test after its frozen prediction is on main",
    ],
    "limitations": [
        "Only permits that create units: demolitions are in a separate layer, not read",
        "No final or certificate-of-occupancy date",
        "D-041's co-built rule recognises SFD houses only: an ADU on the same permit as a new townhouse or "
        "rowhouse is not flagged co-built",
        "The extract is the Hub's cached copy of the layer (its date is the version); the layer is updated "
        "continually, and the city revises records in place",
        "No license is stated for the layer",
    ],
}


def _date(values: pd.Series) -> pd.Series:
    t = pd.to_datetime(values, errors="coerce", utc=True, format="mixed")
    return t.dt.tz_localize(None).dt.normalize().astype("datetime64[ns]")


def size_class(units) -> str:
    if pd.isna(units) or units < 2:
        return "UNKNOWN"
    return "U2" if units == 2 else "U3_4" if units <= 4 else "MF5"


def building_type(newtype, units) -> tuple[str, str]:
    """(building_type_std, type_confidence) of a permit that is not an ADU."""
    if pd.isna(newtype):
        return "UNKNOWN", "unknown"
    if newtype in HOUSE_TYPES:
        return HOUSE_TYPES[newtype], "high"
    if newtype in OTHER_RESIDENTIAL:
        return OTHER_RESIDENTIAL[newtype], "high"
    if newtype == "Apartments/Condos":
        t = size_class(units)
        return t, "high" if t != "UNKNOWN" else "unknown"
    return "OTHER", "high"


def build(raw: pd.DataFrame, state: str = "OR") -> pd.DataFrame:
    df = raw[KEEP].copy()
    df["issue_date"] = _date(df["ISSUEDATE"])
    inside = df["PDXBND"].astype("string").str.strip().str.upper().eq("YES").fillna(False).astype(bool)
    df = df.loc[df["issue_date"].notna() & inside].copy()
    units = pd.to_numeric(df["NEW_UNITS"], errors="coerce")
    work = df["NEWCLASS"].astype("string").str.strip()
    newtype = df["NEWTYPE"].astype("string").str.strip()
    is_adu = df["IS_ADU"].astype("string").str.strip().str.lower().eq("true").fillna(False).astype(bool)
    new = work.eq("New Construction").fillna(False).astype(bool)
    split = is_adu & new & newtype.isin(list(HOUSE_TYPES)).fillna(False).astype(bool) & (units >= 2)

    conversion = pd.Series(pd.NA, index=df.index, dtype="boolean")
    conversion[work.isin(["Alteration", "Addition"]).fillna(False).astype(bool)] = True
    conversion[new] = False
    base = pd.DataFrame(
        {
            "state": state,
            "permit_id": df["FOLDERNUMB"].astype("string").str.strip(),
            "parcel_id": df["PROPGISID1"].astype("string").str.split().str.join(" ").replace("", pd.NA),
            "jurisdiction_geoid": PORTLAND_GEOID,
            "issue_year": df["issue_date"].dt.year.astype("Int64"),
            "issue_date": df["issue_date"],
            "date_precision": "day",
            "application_date": _date(df["INDATE"]),
            "permit_class_raw": work.fillna("") + "|" + newtype.fillna(""),
            "reform_flag_raw": "IS_ADU=" + df["IS_ADU"].astype("string").fillna(""),
            "units_removed": pd.Series(pd.NA, index=df.index, dtype="Int64"),
            "is_demolition": pd.Series(False, index=df.index, dtype="boolean"),
            "is_conversion": conversion,
            "floor_area_sqft": pd.to_numeric(df["SQFT"], errors="coerce").where(lambda s: s > 0),
            "valuation_usd": pd.to_numeric(df["VALUATION"], errors="coerce").where(lambda s: s >= 0),
            "source": SOURCE,
        },
        index=df.index,
    )

    # Permits that are not ADUs, and the house half of a split permit
    plain = ~is_adu | split
    rows = base.loc[plain].copy()
    types = [building_type(t, u) for t, u in zip(newtype[plain], units[plain], strict=True)]
    rows["building_type_std"] = [t for t, _ in types]
    rows["type_confidence"] = [c for _, c in types]
    rows["adu_type"] = pd.Series(pd.NA, index=rows.index, dtype="string")
    rows["units_new"] = units[plain].where(units[plain] > 0).astype("Int64")
    rows.loc[split[plain], "units_new"] = (units[split] - 1).astype("Int64")
    rows.loc[split[plain], "type_confidence"] = "inferred"
    rows.loc[split[plain], "permit_id"] = rows.loc[split[plain], "permit_id"] + "#house"
    rows["units_confidence"] = "reported"
    rows.loc[split[plain], "units_confidence"] = "derived"
    rows.loc[rows["units_new"].isna(), "units_confidence"] = "unknown"

    # ADU rows: every IS_ADU permit, one ADU each
    adu = base.loc[is_adu].copy()
    one_unit_house = new[is_adu] & newtype[is_adu].isin(list(HOUSE_TYPES)).fillna(False) & ~split[is_adu]
    kind = work[is_adu].map(ADU_KIND).fillna("unknown")
    adu["adu_type"] = kind.where(~one_unit_house, "detached").astype("string")
    adu["building_type_std"] = "ADU"
    adu["type_confidence"] = "high"
    adu["units_new"] = units[is_adu].where(units[is_adu] > 0).astype("Int64")
    adu.loc[split[is_adu], "units_new"] = 1
    adu.loc[split[is_adu], "permit_id"] = adu.loc[split[is_adu], "permit_id"] + "#adu"
    adu["units_confidence"] = "reported"
    adu.loc[split[is_adu], "units_confidence"] = "derived"
    adu.loc[adu["units_new"].isna(), "units_confidence"] = "unknown"

    out = pd.concat([rows, adu])
    out["units_new"] = out["units_new"].astype("Int64")
    out = out.sort_values(["permit_id", "issue_date"]).drop_duplicates(["state", "permit_id"], keep="last")
    return out.reset_index(drop=True)


def download(store: DataStore, *, refresh: bool = False, vintage: str | None = None) -> pd.DataFrame:
    vintage = vintage or dt.date.today().isoformat()
    path = fetch(
        URL,
        Path(store.root) / "raw" / SOURCE / vintage / "residential_permits.csv",
        store=store,
        source=SOURCE,
        license=LICENSE,
        adapter=ADAPTER,
        adapter_version=VERSION,
        refresh=refresh,
    )
    return pd.read_csv(path, dtype=str, usecols=KEEP, keep_default_na=True)


def load(state: str, store: DataStore, *, refresh: bool = False, unblind: Iterable[str] = ()) -> pd.DataFrame:
    """Validated permits with Oregon's holdouts removed. Scoring V9 passes `unblind=("V9-OR-TRANSFER",)`,
    which `holdout.apply` allows only once that test's frozen prediction is on `main`."""
    df = build(download(store, refresh=refresh), state=state)
    df = holdout.apply(
        df,
        state,
        unblind=unblind,
        geoid_col="jurisdiction_geoid",
        date_col="issue_date",
        year_col="issue_year",
    )
    return validate(df, TABLE)
