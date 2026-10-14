"""City of Raleigh building permits (Open Raleigh, ArcGIS FeatureServer) → canonical `permits`.

One row per issued building or demolition permit, 2000 to the present, refreshed daily by the city. The layer
follows the BLDS permit standard and adds two reform flags the city maintains: `adu_type` (Attached /
Detached / Internal ADU) and `missing_middle` (Yes / No).

**Building type** comes from `censuslandusecode`, the Census Building Permits Survey type code the city
assigns to each permit (101 single-family detached, 102 townhouse, 103 duplex, 104 three-or-four family,
105 five-or-more family, 112 manufactured home, 645-648 residential demolitions). An `adu_type` of
Attached / Detached / Internal ADU overrides it with `ADU`.

**Units (the repair rule).** `housingunitstotal` is nearly empty for permits issued from 2024 on and holds
scattered implausible values (e.g. duplexes reported as 1 unit, 0-unit apartment buildings), so it is used
only where it agrees with the building-type code, and the code supplies the count otherwise (see `units_for`):

| Code | Plausible reported units | Derived when reported is missing or implausible |
|---|---|---|
| 101 SFD, 112 manufactured, ADU | 1 | 1 |
| 102 townhouse | 1 or more (some permits cover a whole building) | 1 |
| 103 duplex | 2 | 2 |
| 104 three-or-four family | 3 or 4 | unknown (null): 3 and 4 can't be told apart |
| 105 five-or-more family | 5 or more | unknown (null) |
| anything else (alterations, accessory, nonresidential) | not used | unknown (null) |

For alterations and additions `housingunitstotal` holds the building's existing units (thousands of rows a
year through 2023), so it is never read as new units there.

Reported values that pass are `units_confidence="reported"`; code-derived ones are `"derived"`; nulls are
`"unknown"`. A missing count is never filled with 0. Demolitions get `units_new = 0` and `units_removed`
from `housingunitsexist` or the demolition code (645 → 1, 646 → 2, 647/648 unknown).

Only non-personal fields are requested (no owner, contractor, address or free-text fields).
"""

from __future__ import annotations

import pandas as pd

from lotline.io import DataStore
from lotline.io.arcgis import download_layer, epoch_ms_to_timestamp
from lotline.schemas import validate
from lotline.validation import holdout

ADAPTER = "states.nc.raleigh_permits"
VERSION = "1.0"
SOURCE = "raleigh_permits"
TABLE = "permits"
LAYER_URL = (
    "https://services.arcgis.com/v400IkDOw1ad7Yad/arcgis/rest/services/Building_Permits/FeatureServer/0"
)
LANDING_URL = "https://data-ral.opendata.arcgis.com/datasets/ral::building-permits"
LICENSE = "Open Raleigh Data Policy (public open data, no warranty; https://data.raleighnc.gov)"
RALEIGH_GEOID = "3755000"  # Census place GEOID of the permit-issuing city

# Non-personal fields only: no owner, contractor, address, coordinates or comment fields.
OUT_FIELDS = [
    "OBJECTID",
    "permitnum",
    "permittypemapped",
    "workclass",
    "workclassmapped",
    "permitclass",
    "permitclassmapped",
    "censuslandusecode",
    "issueddate",
    "issueddate_yr",
    "applieddate",
    "coissueddate",
    "housingunitstotal",
    "housingunitsexist",
    "adu_type",
    "missing_middle",
    "estprojectcost",
    "totalsqft",
    "pin",
    "jurisdiction_inout_ral",
    "statuscurrentmapped",
]

# Census BPS building-type code -> (building_type_std, units per permit when derivable)
NEW_CODES: dict[int, tuple[str, int | None]] = {
    101: ("SFD", 1),
    102: ("TH", 1),
    103: ("U2", 2),
    104: ("U3_4", None),
    105: ("MF5", None),
    112: ("OTHER", 1),  # manufactured home: BPS excludes these, so they stay out of the BPS-comparable types
}
DEMOLITION_CODES: dict[int, tuple[str, int | None]] = {
    645: ("SFD", 1),
    646: ("U2", 2),
    647: ("U3_4", None),
    648: ("MF5", None),
    649: ("OTHER", None),  # nonresidential: no dwelling units removed, but not known to be 0 from the code
}
ADU_TYPES = {"attached adu": "attached", "detached adu": "detached", "internal adu": "internal_conversion"}
PLAUSIBLE = {"SFD": (1, 1), "TH": (1, None), "ADU": (1, 1), "U2": (2, 2), "U3_4": (3, 4), "MF5": (5, None)}

PROVENANCE = {
    "title": "City of Raleigh Building Permits (Open Raleigh, daily, 2000 to present)",
    "landing_url": LANDING_URL,
    "table": TABLE,
    "cleaning": [
        "Requested fields exclude owner, contractor, address, coordinate and comment fields "
        "(no personal data)",
        "Permits without an issued date (applications under review) are dropped; issue_year is the issue "
        "date's year",
        "building_type_std from the Census BPS code in censuslandusecode (101 SFD, 102 TH, 103 U2, "
        "104 U3_4, 105 MF5, 112 manufactured → OTHER); adu_type Attached/Detached/Internal ADU → ADU",
        "Units repair: housingunitstotal is kept only where it fits the type code (1 for SFD/ADU/"
        "manufactured, 1+ for townhouse, 2 for duplex, 3-4 for 104, 5+ for 105; 0 never fits); otherwise "
        "SFD/TH/ADU/manufactured → 1 and duplex → 2 with units_confidence=derived; 104 and 105 without a "
        "plausible count stay null",
        "Alterations, additions, accessory and nonresidential permits: units_new null (their "
        "housingunitstotal is the existing building's units, not new ones)",
        "Demolitions (645-649): is_demolition, units_new 0, units_removed from housingunitsexist or the "
        "code (645 → 1, 646 → 2)",
        "missing_middle flag copied to reform_flag_raw; censuslandusecode/workclass to permit_class_raw",
        "Every row is assigned to Raleigh (3755000), the permit-issuing office, including permits issued "
        "in its extraterritorial jurisdiction (totals match the Census BPS Raleigh row within a few %)",
        "Holdout filter applied (NC holdout is Charlotte; no Raleigh rows are held out)",
    ],
    "limitations": [
        "housingunitstotal is nearly empty for permits issued from 2024 on, so most 2024+ unit counts are "
        "derived from the building-type code rather than reported",
        "Five-or-more and three-or-four family permits without a plausible reported count have unknown "
        "units (null). From 2024 almost every 105 permit is unknown, so 2024+ multifamily units are "
        "missing, not zero (the unit count is often in the free-text description, not yet parsed)",
        "Townhouse permits with no reported count are derived as 1 unit; the few that cover a whole "
        "building (4-9 units reported in 2023-24) would be undercounted when unreported",
        "The adu_type and missing_middle flags are populated only from 2019-2020 on; earlier ADUs and "
        "missing-middle projects are not flagged",
        "The catalog's '2013 anomaly' was not reproduced: 2013 new-dwelling counts match the Census BPS; "
        "implausible values are scattered (mostly duplexes reported as 1 unit before 2008) and repaired",
        "Alterations, additions and accessory structures are kept as OTHER with unknown units; an "
        "internal conversion that adds a unit is visible only when flagged as an ADU",
        "The city revises records in place (status, CO dates); each pull is a dated raw snapshot",
    ],
}


def _dates(values: pd.Series) -> pd.Series:
    """ArcGIS epoch ms → day-precision timestamps in the schema's datetime64[ns]."""
    ms = pd.to_numeric(values, errors="coerce").astype("float64")  # float NaN, not Int64 <NA>, for nulls
    return epoch_ms_to_timestamp(ms).dt.normalize().astype("datetime64[ns]")


def _code(df: pd.DataFrame) -> pd.Series:
    """Census BPS type code: censuslandusecode, falling back to permitclass (the same code as text)."""
    code = pd.to_numeric(df["censuslandusecode"], errors="coerce")
    alt = pd.to_numeric(df.get("permitclass"), errors="coerce")
    return code.where(code.notna() & (code > 0), alt).astype("Int64")


def _adu_type(raw: pd.Series) -> pd.Series:
    return raw.astype("string").str.strip().str.lower().map(ADU_TYPES).astype("string")


def units_for(btype: str, reported, derived) -> tuple[object, str]:
    """(units, units_confidence) for a new-construction permit: reported if plausible, else derived."""
    lo, hi = PLAUSIBLE.get(btype, (1, None))
    if pd.notna(reported) and reported >= lo and (hi is None or reported <= hi):
        return int(reported), "reported"
    if derived is not None and pd.notna(derived):
        return int(derived), "derived"
    return pd.NA, "unknown"


def build(raw: pd.DataFrame, state: str = "NC") -> pd.DataFrame:
    """Raw layer attributes → canonical permits rows (before the holdout filter)."""
    df = raw.copy()
    issue_date = _dates(df["issueddate"])
    df = df.loc[issue_date.notna()].copy()
    df["issue_date"] = issue_date[issue_date.notna()]
    code = _code(df)
    adu = _adu_type(df["adu_type"])
    reported_total = pd.to_numeric(df["housingunitstotal"], errors="coerce")
    reported_exist = pd.to_numeric(df["housingunitsexist"], errors="coerce")
    is_demo = code.isin(list(DEMOLITION_CODES)) | df["permittypemapped"].astype("string").str.strip().eq(
        "Demolition"
    )

    rows = []
    for i in df.index:
        c = code.at[i]
        a = adu.at[i]
        c_ok = pd.notna(c)
        if pd.notna(a):  # the city's ADU flag wins over the type code
            btype, conf_t, derived = "ADU", "high", 1
        elif c_ok and int(c) in NEW_CODES and not is_demo.at[i]:
            btype, derived = NEW_CODES[int(c)]
            conf_t = "high"
        elif c_ok and int(c) in DEMOLITION_CODES:
            btype, derived = DEMOLITION_CODES[int(c)]
            conf_t = "high"
        elif c_ok:
            btype, conf_t, derived = "OTHER", "high", None
        else:
            btype, conf_t, derived = "UNKNOWN", "unknown", None

        if is_demo.at[i]:
            removed = reported_exist.at[i]
            if pd.notna(removed) and removed > 0:
                units_removed, conf_u = int(removed), "reported"
            elif derived is not None:
                units_removed, conf_u = derived, "derived"
            else:
                units_removed, conf_u = pd.NA, "unknown"
            units_new = 0
        else:
            units_removed = pd.NA
            if btype in PLAUSIBLE or derived is not None:  # new dwellings (incl. manufactured homes)
                units_new, conf_u = units_for(btype, reported_total.at[i], derived)
            else:  # alterations, accessory and nonresidential: the unit field holds existing units
                units_new, conf_u = pd.NA, "unknown"
        rows.append((btype, conf_t, units_new, units_removed, conf_u, bool(is_demo.at[i])))

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
    workclass = df["workclass"].astype("string").str.strip()
    out = pd.DataFrame(
        {
            "state": state,
            "permit_id": df["permitnum"].astype("string").str.strip(),
            "parcel_id": df["pin"].astype("string").str.strip().replace("", pd.NA),
            "jurisdiction_geoid": RALEIGH_GEOID,
            "issue_year": df["issue_date"].dt.year.astype("Int64"),
            "issue_date": df["issue_date"],
            "date_precision": "day",
            "application_date": _dates(df["applieddate"]),
            "final_date": _dates(df["coissueddate"]),
            "adu_type": adu,
            "permit_class_raw": code.astype("string").fillna("") + "|" + workclass.fillna(""),
            "reform_flag_raw": df["missing_middle"].astype("string").str.strip().replace("", pd.NA),
            "is_conversion": adu.eq("internal_conversion").astype("boolean").where(adu.notna(), pd.NA),
            "floor_area_sqft": pd.to_numeric(df["totalsqft"], errors="coerce").where(lambda s: s > 0),
            "valuation_usd": pd.to_numeric(df["estprojectcost"], errors="coerce").where(lambda s: s >= 0),
            "source": SOURCE,
        },
        index=df.index,
    ).join(parts)
    out["final_date_type"] = pd.Series("certificate_of_occupancy", index=out.index).where(
        out["final_date"].notna()
    )
    out["units_new"] = out["units_new"].astype("Int64")
    out["units_removed"] = out["units_removed"].astype("Int64")
    out["is_demolition"] = out["is_demolition"].astype("boolean")
    # Guard: permit numbers were unique on 2026-10-14; if one ever repeats, keep the latest issue.
    out = out.sort_values(["permit_id", "issue_date"]).drop_duplicates(["state", "permit_id"], keep="last")
    return out.reset_index(drop=True)


def download(store: DataStore, *, refresh: bool = False) -> pd.DataFrame:
    return download_layer(
        LAYER_URL,
        store=store,
        source=SOURCE,
        license=LICENSE,
        adapter=ADAPTER,
        adapter_version=VERSION,
        name="building_permits",
        out_fields=",".join(OUT_FIELDS),
        refresh=refresh,
    )


def load(state: str, store: DataStore, *, refresh: bool = False) -> pd.DataFrame:
    df = build(download(store, refresh=refresh), state=state)
    df = holdout.apply(
        df, state, geoid_col="jurisdiction_geoid", date_col="issue_date", year_col="issue_year"
    )
    return validate(df, TABLE)
