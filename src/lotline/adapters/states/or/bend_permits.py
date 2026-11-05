"""City of Bend Permitting Table (ArcGIS FeatureServer, 1934 to present) → `permits`.

One row per application in the city's permitting system. Only building applications that can add or remove
dwellings are downloaded (server-side filter on `ApplicationType`): new construction (NC), additions (AD),
renovations and alterations (RE), manufactured or tiny home placement (MA) and demolitions (DE). Trade permits
(electrical, mechanical, plumbing) for the same buildings are left out, so a building is not counted once per
trade.

**ADUs.** A permit is an ADU when its building use (`BldgUse`) is `ADU`. This is the city's own code, used
consistently from 2013. **`HB2001ADU` is not the ADU flag**, despite its name: it is empty before 2019, partly
filled in 2019-2020, and once filled it marks permits taken under HB 2001's provisions. About a quarter of its
'Y' permits are duplexes, and about a quarter of ADU-use building permits since 2021 carry 'N'. It is kept as
`reform_flag_raw` (with `HB2306Path`). `adu_type` from the application type: NC unknown (attached or detached
is not recorded), AD attached, RE internal_conversion, MA detached.

**No ADU use code before 2013.** Building uses are coded in 2010-2012, but none is `ADU`; ADUs then were filed
under other uses (probably accessory structures or houses). Counts by this flag start in 2013, and 2010-2012
are unknown, not zero.

**Other types** from `BldgUse`: SFD → SFD; SFDA (townhome) → TH; DUP → U2; MFD → by `Units` (2 U2, 3-4 U3_4,
5+ MF5); MH (manufactured or tiny home), commercial, accessory structures and other uses → OTHER; blank →
UNKNOWN. `units_new` = `Units` (reported), except an ADU with no units, which is 1 (inferred).
`is_conversion`: RE and AD True, NC and MA False. Demolitions: `is_demolition`, `units_new` 0, `units_removed`
= `Units` for dwelling uses.

**Rows and dates.** The table repeats some applications (about 375 since 2019): the copies are identical
except, in some, the taxlot. One row per `ApplicationNumber` is kept (the lowest OBJECTID, with the first
taxlot in sort order). Applications never issued, withdrawn (WDRN), void or denied are dropped. `issue_date` =
`IssueDate`, `application_date` = `ApplicationDate`, `final_date` = `DateFinaled` (final inspection).

Every row is assigned to Bend (4105800). Parcel: `TAXLOT`. Owner names and addresses are not requested.
"""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd

from lotline.io import DataStore
from lotline.io.arcgis import download_layer, epoch_ms_to_timestamp
from lotline.schemas import validate
from lotline.validation import holdout

ADAPTER = "states.or.bend_permits"
VERSION = "1.0"
SOURCE = "bend_permits"
TABLE = "permits"
LAYER_URL = (
    "https://services5.arcgis.com/JisFYcK2mIVg9ueP/arcgis/rest/services/Permitting_Table/FeatureServer/0"
)
LANDING_URL = "https://www.arcgis.com/home/item.html?id=56a9f599d81445abad0435d88e3f5fa4"
LICENSE = (
    "City of Bend GIS terms: provided as is, use at your own risk, no warranty; no reuse restriction stated"
)
BEND_GEOID = "4105800"

FIELDS = [
    "OBJECTID",
    "ApplicationNumber",
    "ApplicationDate",
    "IssueDate",
    "DateFinaled",
    "SQFT",
    "Units",
    "ProjectValuation",
    "ApplicationType",
    "ApplicationStatus",
    "BldgUse",
    "BuildingCategory",
    "HB2001ADU",
    "HB2306Path",
    "TAXLOT",
]
PERSONAL = {"Owner", "Address", "SITEADDID", "LOCID"}
APP_TYPES = ("NC", "AD", "RE", "MA", "DE")
WHERE = "ApplicationType IN (" + ",".join(f"'{t}'" for t in APP_TYPES) + ")"
DROP_STATUS = {"WDRN", "VOID", "DEN"}
ADU_KIND = {"NC": "unknown", "AD": "attached", "RE": "internal_conversion", "MA": "detached"}
USE_TYPES = {"SFD": "SFD", "SFDA": "TH", "DUP": "U2"}
DWELLING_USES = {"SFD", "SFDA", "DUP", "MFD", "ADU", "MH"}

PROVENANCE = {
    "title": "City of Bend Permitting Table (applications 1934 to present)",
    "landing_url": LANDING_URL,
    "table": TABLE,
    "cleaning": [
        "Server-side filter: application types NC, AD, RE, MA and DE only; trade permits are not downloaded; "
        "owner names and addresses are not requested",
        "One row per ApplicationNumber (the table repeats some applications; copies are identical apart from "
        "the taxlot in some): the lowest OBJECTID is kept, with the first taxlot in sort order",
        "Applications never issued, withdrawn, void or denied are dropped",
        "ADU = building use ADU (the city's code, used from 2013); HB2001ADU and HB2306Path are kept as "
        "reform_flag_raw, not used as the ADU flag (HB2001ADU marks HB 2001 pathway permits, duplexes "
        "included, and is filled only from 2019-2021)",
        "adu_type from the application type: NC unknown, AD attached, RE internal_conversion, MA detached",
        "building_type_std from building use: SFD SFD; SFDA TH; DUP U2; MFD by units (2 U2, 3-4 U3_4, 5+ "
        "MF5); other uses OTHER; blank UNKNOWN; units_new = Units (reported; an ADU without units is 1, "
        "inferred)",
        "Demolitions: is_demolition, units_new 0, units_removed = Units for dwelling uses",
        "final_date = DateFinaled (final inspection); every row is assigned to Bend (4105800)",
        "Holdout filter applied: Oregon outcomes from 2018 on (V9-OR-TRANSFER) stay hidden unless the caller "
        "unblinds that test after its frozen prediction is on main",
    ],
    "limitations": [
        "No ADU building use before 2013: ADU counts start in 2013 (2010-2012 unknown, not zero)",
        "Before 2018 only new-construction permits carry the ADU use; conversions and additions are coded "
        "ADU later, so early conversions may be missed",
        "A permit spanning several taxlots keeps one taxlot, which can hide a co-built match on another lot",
        "Terms are a disclaimer (as is, no warranty); no license is stated",
    ],
}


def _date(values: pd.Series) -> pd.Series:
    return (
        epoch_ms_to_timestamp(pd.to_numeric(values, errors="coerce")).dt.normalize().astype("datetime64[ns]")
    )


def size_class(units) -> str:
    if pd.isna(units) or units < 2:
        return "UNKNOWN"
    return "U2" if units == 2 else "U3_4" if units <= 4 else "MF5"


def classify(use, units) -> tuple[str, str]:
    """(building_type_std, type_confidence) from the building use."""
    if pd.isna(use):
        return "UNKNOWN", "unknown"
    if use == "ADU":
        return "ADU", "high"
    if use in USE_TYPES:
        return USE_TYPES[use], "high"
    if use == "MFD":
        t = size_class(units)
        return t, "high" if t != "UNKNOWN" else "unknown"
    return "OTHER", "high"


def build(raw: pd.DataFrame, state: str = "OR") -> pd.DataFrame:
    df = raw.copy()
    df["ApplicationNumber"] = df["ApplicationNumber"].astype("string").str.strip()
    df["TAXLOT"] = df["TAXLOT"].astype("string").str.strip().replace("", pd.NA)
    first_lot = df.dropna(subset=["TAXLOT"]).groupby("ApplicationNumber")["TAXLOT"].min()
    df = df.sort_values("OBJECTID").drop_duplicates("ApplicationNumber", keep="first").copy()
    df["TAXLOT"] = df["ApplicationNumber"].map(first_lot)
    df["issue_date"] = _date(df["IssueDate"])
    status = df["ApplicationStatus"].astype("string").str.strip()
    df = df.loc[df["issue_date"].notna() & ~status.isin(DROP_STATUS).fillna(False).astype(bool)].copy()

    app = df["ApplicationType"].astype("string").str.strip()
    use = df["BldgUse"].astype("string").str.strip()
    units = pd.to_numeric(df["Units"], errors="coerce")
    demo = app.eq("DE").fillna(False).astype(bool)
    is_adu = use.eq("ADU").fillna(False).astype(bool) & app.isin(list(ADU_KIND)).fillna(False).astype(bool)

    types = [classify(u, n) for u, n in zip(use, units, strict=True)]
    btype = pd.Series([t for t, _ in types], index=df.index)
    conf = pd.Series([c for _, c in types], index=df.index)
    btype[use.eq("ADU").fillna(False).astype(bool) & ~is_adu] = "OTHER"  # e.g. an ADU's demolition

    n = units.where(units >= 0).astype("Int64")
    units_new = n.copy()
    units_conf = pd.Series("reported", index=df.index).where(n.notna(), "unknown")
    no_units = is_adu & n.isna()
    units_new[no_units] = 1
    units_conf[no_units] = "inferred"
    dwelling = use.isin(list(DWELLING_USES)).fillna(False).astype(bool)
    units_removed = pd.Series(pd.NA, index=df.index, dtype="Int64")
    units_removed[demo & dwelling] = n[demo & dwelling]
    units_new[demo] = 0
    units_conf[demo] = pd.Series("reported", index=df.index).where(n.notna() & dwelling, "unknown")[demo]

    conversion = pd.Series(pd.NA, index=df.index, dtype="boolean")
    conversion[app.isin(["RE", "AD"]).fillna(False).astype(bool)] = True
    conversion[app.isin(["NC", "MA"]).fillna(False).astype(bool)] = False

    final = _date(df["DateFinaled"])
    hb = df["HB2001ADU"].astype("string").fillna("")
    path = df["HB2306Path"].astype("string").fillna("")
    out = pd.DataFrame(
        {
            "state": state,
            "permit_id": df["ApplicationNumber"],
            "parcel_id": df["TAXLOT"],
            "jurisdiction_geoid": BEND_GEOID,
            "issue_year": df["issue_date"].dt.year.astype("Int64"),
            "issue_date": df["issue_date"],
            "date_precision": "day",
            "application_date": _date(df["ApplicationDate"]),
            "final_date": final,
            "final_date_type": pd.Series("final_inspection", index=df.index).where(final.notna()),
            "building_type_std": btype,
            "type_confidence": conf,
            "adu_type": app.map(ADU_KIND).where(is_adu).astype("string"),
            "permit_class_raw": app.fillna("") + "|" + use.fillna(""),
            "reform_flag_raw": "HB2001ADU=" + hb + "|HB2306Path=" + path,
            "units_new": units_new.astype("Int64"),
            "units_removed": units_removed,
            "units_confidence": units_conf,
            "is_demolition": demo.astype("boolean"),
            "is_conversion": conversion,
            "floor_area_sqft": pd.to_numeric(df["SQFT"], errors="coerce").where(lambda s: s > 0),
            "valuation_usd": pd.to_numeric(df["ProjectValuation"], errors="coerce").where(lambda s: s >= 0),
            "source": SOURCE,
        },
        index=df.index,
    )
    return out.sort_values("permit_id").reset_index(drop=True)


def download(store: DataStore, *, refresh: bool = False) -> pd.DataFrame:
    return download_layer(
        LAYER_URL,
        store=store,
        source=SOURCE,
        license=LICENSE,
        adapter=ADAPTER,
        adapter_version=VERSION,
        name="permitting_table",
        where=WHERE,
        out_fields=",".join(FIELDS),
        refresh=refresh,
    )


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
