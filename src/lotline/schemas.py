"""Canonical tables (pandera schemas), versioned.

Every adapter emits these tables; contract tests call `assert_conforms(df, "permits")`. Optional columns
may be absent and nullable ones null in some sources; the V0 report counts every null. Spec: BUILD_PLAN §5.1.

Bump SCHEMAS_VERSION (and note the migration in the PR) whenever a column is added, removed or retyped.
"""

from __future__ import annotations

from typing import Optional

import pandas as pd
import pandera.pandas as pa
from pandera.typing import Series

SCHEMAS_VERSION = "1.0"

# Building types. Combined codes exist because some sources (Met Council, BPS) can't split further:
# never guess a finer category, mark type_confidence instead.
BUILDING_TYPES = ["SFD", "ADU", "TH", "U2", "U3_4", "U5_6", "U7P", "DTQ", "MF5", "OTHER", "UNKNOWN"]
TYPE_CONFIDENCE = ["high", "inferred", "unknown"]
JURISDICTION_KINDS = ["place", "county", "township", "county_unincorporated", "other"]
DATA_TIERS = [1, 2, 3]
REFORM_THEMES = ["adu", "missing_middle", "fees", "parking", "tod", "other"]

_STATE = {"str_matches": r"^[A-Z]{2}$"}
_COUNT = {"ge": 0}


class _Strict(pa.DataFrameModel):
    class Config:
        strict = "filter"  # extra columns are dropped on validate, so adapters can carry raw fields upstream
        coerce = True


class Jurisdictions(_Strict):
    state: Series[str] = pa.Field(**_STATE)
    geoid: Series[str] = pa.Field(unique=True)
    name: Series[str]
    kind: Series[str] = pa.Field(isin=JURISDICTION_KINDS)
    county_geoid: Optional[Series[str]] = pa.Field(nullable=True)
    bps_id: Optional[Series[str]] = pa.Field(nullable=True)
    pop_2020: Optional[Series[pd.Int64Dtype]] = pa.Field(nullable=True, ge=0)
    data_tier: Series[pd.Int64Dtype] = pa.Field(isin=DATA_TIERS)


class Parcels(_Strict):
    state: Series[str] = pa.Field(**_STATE)
    parcel_id: Series[str]
    vintage: Series[pd.Int64Dtype] = pa.Field(ge=1900, le=2100)
    jurisdiction_geoid: Series[str]
    lot_sqft: Series[float] = pa.Field(ge=0, nullable=True)
    land_use_std: Series[str]
    land_use_raw: Series[str] = pa.Field(nullable=True)
    units: Optional[Series[pd.Int64Dtype]] = pa.Field(nullable=True, ge=0)
    year_built: Optional[Series[pd.Int64Dtype]] = pa.Field(nullable=True)
    land_value: Optional[Series[float]] = pa.Field(nullable=True, ge=0)
    bldg_value: Optional[Series[float]] = pa.Field(nullable=True, ge=0)
    last_sale_price: Optional[Series[float]] = pa.Field(nullable=True, ge=0)
    last_sale_date: Optional[Series[pd.Timestamp]] = pa.Field(nullable=True)
    homestead: Optional[Series[pd.BooleanDtype]] = pa.Field(nullable=True)
    zoning_raw: Optional[Series[str]] = pa.Field(nullable=True)
    sf_only_zoned: Optional[Series[pd.BooleanDtype]] = pa.Field(nullable=True)
    source: Series[str]

    @pa.dataframe_check
    def one_row_per_parcel_vintage(cls, df: pd.DataFrame) -> bool:
        return not df.duplicated(["state", "parcel_id", "vintage"]).any()


class Permits(_Strict):
    state: Series[str] = pa.Field(**_STATE)
    permit_id: Series[str]
    parcel_id: Optional[Series[str]] = pa.Field(nullable=True)
    jurisdiction_geoid: Series[str]
    issue_date: Series[pd.Timestamp]
    final_date: Optional[Series[pd.Timestamp]] = pa.Field(nullable=True)
    building_type_std: Series[str] = pa.Field(isin=BUILDING_TYPES)
    units_new: Series[pd.Int64Dtype] = pa.Field(**_COUNT)
    units_removed: Series[pd.Int64Dtype] = pa.Field(**_COUNT)
    is_demolition: Series[bool]
    is_conversion: Series[bool]
    source: Series[str]
    type_confidence: Series[str] = pa.Field(isin=TYPE_CONFIDENCE)


class BpsPlaceYear(_Strict):
    """Census Building Permits Survey, annual, one row per permit-issuing place.

    `units_*` include Census imputation for months a place didn't report; `units_*_rep` are reported only.
    `imputed` is True when any month was imputed (months_reported < 12 or reported != total).
    """

    state: Series[str] = pa.Field(**_STATE)
    bps_id: Series[str] = pa.Field(str_matches=r"^\d{2}\d{6}$")  # state FIPS + BPS 6-digit ID
    geoid: Series[str] = pa.Field(nullable=True)  # Census place (7) or county subdivision (10) GEOID
    county_geoid: Series[str] = pa.Field(str_matches=r"^\d{5}$")
    name: Series[str]
    year: Series[pd.Int64Dtype] = pa.Field(ge=1980, le=2100)
    months_reported: Series[pd.Int64Dtype] = pa.Field(ge=0, le=12)
    bldgs_1: Series[pd.Int64Dtype] = pa.Field(**_COUNT)
    bldgs_2: Series[pd.Int64Dtype] = pa.Field(**_COUNT)
    bldgs_3_4: Series[pd.Int64Dtype] = pa.Field(**_COUNT)
    bldgs_5p: Series[pd.Int64Dtype] = pa.Field(**_COUNT)
    units_1: Series[pd.Int64Dtype] = pa.Field(**_COUNT)
    units_2: Series[pd.Int64Dtype] = pa.Field(**_COUNT)
    units_3_4: Series[pd.Int64Dtype] = pa.Field(**_COUNT)
    units_5p: Series[pd.Int64Dtype] = pa.Field(**_COUNT)
    units_1_rep: Series[pd.Int64Dtype] = pa.Field(**_COUNT)
    units_2_rep: Series[pd.Int64Dtype] = pa.Field(**_COUNT)
    units_3_4_rep: Series[pd.Int64Dtype] = pa.Field(**_COUNT)
    units_5p_rep: Series[pd.Int64Dtype] = pa.Field(**_COUNT)
    imputed: Series[bool]

    @pa.dataframe_check
    def one_row_per_place_year(cls, df: pd.DataFrame) -> bool:
        return not df.duplicated(["bps_id", "year"]).any()


class MarketGeoYear(_Strict):
    geo: Series[str]
    year: Series[pd.Int64Dtype] = pa.Field(ge=1970, le=2100)
    hpi: Series[float] = pa.Field(nullable=True)
    median_value: Optional[Series[float]] = pa.Field(nullable=True, ge=0)
    median_rent: Optional[Series[float]] = pa.Field(nullable=True, ge=0)
    ppi_resid_inputs: Series[float] = pa.Field(nullable=True)
    mortgage_rate: Series[float] = pa.Field(nullable=True)


class Reforms(_Strict):
    state: Series[str] = pa.Field(**_STATE)
    jurisdiction_geoid: Series[str]
    theme: Series[str] = pa.Field(isin=REFORM_THEMES)
    component: Series[str]
    effective_date: Series[pd.Timestamp]
    announced_date: Optional[Series[pd.Timestamp]] = pa.Field(nullable=True)
    by_right: Series[pd.BooleanDtype] = pa.Field(nullable=True)
    owner_occ: Series[pd.BooleanDtype] = pa.Field(nullable=True)
    unit_cap: Series[pd.Int64Dtype] = pa.Field(nullable=True, ge=0)
    far_cap: Optional[Series[float]] = pa.Field(nullable=True, ge=0)
    lot_split: Series[pd.BooleanDtype] = pa.Field(nullable=True)
    parking: Series[str] = pa.Field(nullable=True)
    fee_change_usd: Optional[Series[float]] = pa.Field(nullable=True)
    coverage: Series[str]
    source_url: Series[str]
    coder: Series[str]


class Fees(_Strict):
    geoid: Series[str]
    year: Series[pd.Int64Dtype] = pa.Field(ge=1970, le=2100)
    fee_type: Series[str]
    basis: Series[str]
    amount_per_unit_usd: Series[float] = pa.Field(ge=0)
    source: Series[str]


TABLES: dict[str, type[pa.DataFrameModel]] = {
    "jurisdictions": Jurisdictions,
    "parcels": Parcels,
    "permits": Permits,
    "bps_place_year": BpsPlaceYear,
    "market_geo_year": MarketGeoYear,
    "reforms": Reforms,
    "fees": Fees,
}


def validate(df: pd.DataFrame, table: str) -> pd.DataFrame:
    """Return `df` coerced to the canonical schema for `table`, keeping only canonical columns.

    Raises pandera.errors.SchemaErrors listing every failing check (lazy validation).
    """
    if table not in TABLES:
        raise KeyError(f"unknown table {table!r}; expected one of {sorted(TABLES)}")
    return TABLES[table].validate(df, lazy=True)


def assert_conforms(df: pd.DataFrame, table: str) -> None:
    """Contract-test helper: fail with every schema error at once."""
    validate(df, table)
