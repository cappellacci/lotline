"""Met Council Residential Building Permits (7-county Twin Cities metro, 2009 on) → `permits`.

Source: Metropolitan Council "Residential Permits" feature layer, listed on the Minnesota Geospatial Commons
(dataset `us-mn-state-metc-econ-residential-building-permts`, now an ArcGIS Hub item). Public domain under
the Minnesota Government Data Practices Act. The Commons page also links a file geodatabase, but reading it
needs a GDAL-based dependency, so we use the feature layer it recommends, through the ArcGIS pager.

Each row is one entry in a stock ledger: a gain or a loss of `UNITS` units of one housing type, coded
by `RES_PERMIT_TYPE` (field definitions: Met Council metadata page, "Section 5: Attributes"). Rows carry the
permit year only. Communities that don't return the survey are filled from Census BPS by Met Council staff.
"""

from __future__ import annotations

import httpx
import pandas as pd

from lotline.config import load_state
from lotline.io import DataStore
from lotline.io.arcgis import download_layer
from lotline.schemas import validate
from lotline.validation import holdout

ADAPTER = "states.mn.metc_permits"
VERSION = "1.0"
SOURCE = "metc_residential_permits"
TABLE = "permits"
LICENSE = "Public domain (Minnesota Government Data Practices Act, Minn. Stat. ch. 13)"
LAYER_URL = (
    "https://arcgis.metc.state.mn.us/data1/rest/services/structure/Other_Structure_Public/FeatureServer/0"
)
LANDING_URL = "https://gisdata.mn.gov/dataset/us-mn-state-metc-econ-residential-building-permts"
METADATA_URL = (
    "https://metrocouncil.org/Data-and-Maps/Research-and-Data/Metadata/Residential-Building-Permits.aspx"
)

# Only what the table needs. ADDRESS, ZIP, NAME (building, developer or *owner* name) and NOTES are never
# requested: they can identify people and nothing downstream uses them.
FIELDS = [
    "OBJECTID",
    "SDE_ID",
    "CO_CODE",
    "CTU_CODE",
    "CTU_NAME",
    "YEAR",
    "TENURE",
    "HOUSING_TYPE",
    "RES_PERMIT_TYPE",
    "BUILDINGS",
    "UNITS",
    "PIN",
    "PERMIT_VALUE",
]

# Met Council housing types map one to one; DTQ (2-4 units) and MF5 (5+) are kept whole, never split.
HOUSING_TYPES = {"SFD": "SFD", "ADU": "ADU", "TH": "TH", "DTQ": "DTQ", "MF5": "MF5"}

# RES_PERMIT_TYPE codes (metadata page). Gains add UNITS to the stock, losses remove them, RE (remodel over
# $1 million) changes neither.
GAINS = {"NU", "MI", "MU", "FC", "FS", "FD", "FM"}  # new, moved in, converted to more / from another use
LOSSES = {"RM", "MO", "TF", "TC", "TS", "TD", "TM"}  # removed, moved out, converted to fewer / to another use
NO_CHANGE = {"RE"}
CONVERSIONS = {"MU", "TF", "FC", "TC", "FS", "TS", "FD", "TD", "FM", "TM"}
DEMOLITION = {"RM"}  # "removed from stock"

TENURE = {"OWN": "owner", "RNT": "renter", "COP": "cooperative"}

# Local PIN length by county (CO_CODE). Some rows prefix the PIN with the 3-digit county code; it is stripped
# when the remainder has the county's local length. Lengths read from the source's own unprefixed rows.
LOCAL_PIN_LENGTH = {"003": 12, "019": 9, "037": 12, "053": 13, "123": 12, "139": 9, "163": 13}

PROVENANCE = {
    "title": "Metropolitan Council Residential Building Permits (7-county metro)",
    "landing_url": LANDING_URL,
    "table": TABLE,
    "attribution": "Metropolitan Council, via the Minnesota Geospatial Commons",
    "cleaning": [
        f"Download the 'Residential Permits' feature layer ({LAYER_URL}) with the ArcGIS pager, requesting "
        f"only {', '.join(FIELDS)}; address, ZIP, building/owner name and notes are never requested",
        "HOUSING_TYPE SFD/ADU/TH/DTQ/MF5 → building_type_std of the same code, type_confidence=high (the "
        "survey records the type); anything else → UNKNOWN. DTQ and MF5 are never split",
        "RES_PERMIT_TYPE gains (NU, MI, MU, FC, FS, FD, FM) → units_new=UNITS, units_removed=0; losses "
        "(RM, MO, TF, TC, TS, TD, TM) → units_new=0, units_removed=UNITS; RE (remodel over $1M) → "
        "both 0. Each row is one side of a ledger, so the other side is 0 by construction; a missing "
        "UNITS leaves both null",
        "is_demolition=True for RM; is_conversion=True for the conversion codes (MU, TF, FC, TC, FS, TS, FD, "
        "TD, FM, TM); unknown codes leave both null",
        "YEAR → issue_year; issue_date null; date_precision=year",
        "jurisdiction_geoid: '27' + CTU_CODE (FIPS place code) when that place is in the MN jurisdictions "
        "table, else '27' + CO_CODE + CTU_CODE (county subdivision, e.g. townships)",
        "parcel_id: '27' + CO_CODE + local PIN (punctuation removed; a leading county code stripped when the "
        "remainder has the county's local length; '0' placeholders → null)",
        "permit_id: 'metc-' + SDE_ID (the layer's unique identifier)",
        "Remove held-out place-years (validation/holdout.py) before the table is written",
    ],
    "limitations": [
        "Year of permit only, no dates; no permit number (SDE_ID is Met Council's row id, not a city's)",
        "City-reported annual survey; non-responding communities are filled from Census BPS without PINs",
        "PIN present on well under half the rows, and almost none in 2010-2014",
        "DTQ lumps 2-4 unit buildings; 5-6 unit buildings sit in MF5 with large buildings",
        "ADU recording starts in 2016 (C32): no ADU rows 2009-2013 and one in 2014 (fetch of 2026-10-14). "
        "Minneapolis ADUs 2016-2022 are about half the city's published count, so ADUs may also sit in SFD",
        "About 1.7% of rows are in county subdivisions not in the jurisdictions table (Carver and Scott "
        "townships, Empire, Credit River, Fort Snelling, Shakopee Mdewakanton Sioux Community)",
        "Covers the 7-county metro only",
    ],
}


def load(
    state: str, store: DataStore, *, refresh: bool = False, http: httpx.Client | None = None
) -> pd.DataFrame:
    if state.upper() != "MN":
        raise ValueError(f"{SOURCE} covers Minnesota only, not {state}")
    jur_path = store.processed("MN", "jurisdictions")
    if not jur_path.exists():
        raise FileNotFoundError(
            f"{jur_path} missing: run `lotline fetch --state MN --source jurisdictions` first"
        )
    raw = download_layer(
        LAYER_URL,
        store=store,
        source=SOURCE,
        license=LICENSE,
        adapter=ADAPTER,
        adapter_version=VERSION,
        name="residential_permits",
        out_fields=",".join(FIELDS),
        refresh=refresh,
        http=http,
    )
    return to_permits(raw, pd.read_parquet(jur_path), "MN")


def to_permits(raw: pd.DataFrame, jurisdictions: pd.DataFrame, state: str = "MN") -> pd.DataFrame:
    """Raw layer attributes → validated `permits`, holdouts removed."""
    fips = load_state(state).fips
    code = raw["RES_PERMIT_TYPE"].astype("string").str.strip().str.upper()
    units = pd.to_numeric(raw["UNITS"], errors="coerce").round().astype("Int64")
    zero = pd.Series(0, index=raw.index, dtype="Int64")
    null = pd.Series(pd.NA, index=raw.index, dtype="Int64")
    gain, loss, same = code.isin(GAINS), code.isin(LOSSES), code.isin(NO_CHANGE)
    known = gain | loss | same

    htype = raw["HOUSING_TYPE"].astype("string").str.strip().str.upper()
    std = htype.map(HOUSING_TYPES).fillna("UNKNOWN")
    county = raw["CO_CODE"].astype("string").str.zfill(3)

    df = pd.DataFrame(
        {
            "state": state,
            "permit_id": "metc-" + pd.to_numeric(raw["SDE_ID"]).astype("Int64").astype("string"),
            "parcel_id": normalize_pin(raw["PIN"], county, fips),
            "jurisdiction_geoid": jurisdiction_geoids(raw, jurisdictions, fips),
            "issue_year": pd.to_numeric(raw["YEAR"], errors="coerce").astype("Int64"),
            "issue_date": pd.Series(pd.NaT, index=raw.index, dtype="datetime64[ns]"),
            "date_precision": "year",
            "building_type_std": std,
            "type_confidence": std.map(lambda s: "unknown" if s == "UNKNOWN" else "high"),
            "adu_type": pd.Series(pd.NA, index=raw.index, dtype="string").mask(std == "ADU", "unknown"),
            "permit_class_raw": htype.fillna("") + ":" + code.fillna(""),
            "n_buildings": pd.to_numeric(raw["BUILDINGS"], errors="coerce").round().astype("Int64"),
            "units_new": units.where(gain, zero.where(loss | same, null)).where(units.notna() | same, null),
            "units_removed": units.where(loss, zero.where(gain | same, null)).where(
                units.notna() | same, null
            ),
            "is_demolition": pd.Series(code.isin(DEMOLITION), dtype="boolean").where(known, pd.NA),
            "is_conversion": pd.Series(code.isin(CONVERSIONS), dtype="boolean").where(known, pd.NA),
            "valuation_usd": pd.to_numeric(raw["PERMIT_VALUE"], errors="coerce").astype(float),
            "tenure": raw["TENURE"].astype("string").str.strip().str.upper().map(TENURE),
            "source": SOURCE,
        }
    )
    # A gain/loss row with no UNITS has unknown units (null, never 0); RE rows add nothing by definition.
    df["units_confidence"] = "unknown"
    df.loc[units.notna() & (gain | loss), "units_confidence"] = "reported"
    df.loc[same, "units_confidence"] = "derived"
    df = holdout.apply(
        df, state, geoid_col="jurisdiction_geoid", date_col="issue_date", year_col="issue_year"
    )
    return validate(df.reset_index(drop=True), TABLE)


def jurisdiction_geoids(raw: pd.DataFrame, jurisdictions: pd.DataFrame, fips: str) -> pd.Series:
    """Place GEOID (state + 5-digit FIPS place code) if it is a known place, else county subdivision GEOID."""
    ctu = raw["CTU_CODE"].astype("string").str.strip().str.zfill(5)
    county = raw["CO_CODE"].astype("string").str.strip().str.zfill(3)
    places = set(jurisdictions.loc[jurisdictions["kind"] == "place", "geoid"].astype(str))
    place = fips + ctu
    return place.where(place.isin(places), fips + county + ctu)


def normalize_pin(pin: pd.Series, county: pd.Series, fips: str) -> pd.Series:
    """County GEOID + local PIN; null when the PIN is missing or a placeholder ('0')."""
    clean = pin.astype("string").str.upper().str.replace(r"[^0-9A-Z]", "", regex=True)
    clean = clean.mask(clean.str.fullmatch(r"0*").fillna(True))
    local_len = county.map(LOCAL_PIN_LENGTH).astype("Int64")
    prefixed = (clean.str.slice(0, 3) == county) & (clean.str.len() == local_len + 3)
    local = clean.where(~prefixed.fillna(False), clean.str.slice(3))
    return (fips + county + local).astype("string")
