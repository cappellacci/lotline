"""Canonical tables (pandera schemas), versioned. Frozen as `schemas-v1`; see docs/schemas.md.

Every adapter emits these tables; contract tests call `assert_conforms(df, "permits")`. Optional columns
may be absent and nullable ones null in some sources; the V0 report counts every null.

Conventions (all tables):
- **Unknown is null, never 0 or False.** A source that doesn't record demolitions leaves them null.
- **Money** (`*_usd`) is nominal dollars of the row's own year unless a `dollar_year` column says otherwise;
  the engine converts to real 2025 dollars with `market_geo_year.cpi_u` (protocol §5.9).
- **Jurisdiction keys** are GEOIDs: state (2), county or county unincorporated area (5), place (7), county
  subdivision (10).
- **Never guess a finer category**: combined codes (DTQ, MF5) exist for sources that can't split further, and
  confidence columns say how a value was obtained.

Versioning: within v1, only additive changes (new optional columns, new enum values) are allowed, each a
minor bump. Renaming, retyping, removing a column or making one required is a v2 change (`contract-change`).
"""

from __future__ import annotations

import difflib
from typing import Optional

import pandas as pd
import pandera.pandas as pa
from pandera.typing import Series

SCHEMAS_VERSION = "1.4"  # schemas-v1 freeze; history in docs/schemas.md

# Building types. Combined codes exist because some sources (Met Council, BPS) can't split further:
# never guess a finer category, mark type_confidence instead.
BUILDING_TYPES = ["SFD", "ADU", "TH", "U2", "U3_4", "U5_6", "U7P", "DTQ", "MF5", "OTHER", "UNKNOWN"]
TYPE_CONFIDENCE = ["high", "inferred", "unknown"]
JURISDICTION_KINDS = ["state", "county", "county_unincorporated", "place", "township", "region", "other"]
DATA_TIERS = [1, 2, 3]
REFORM_THEMES = [
    "adu",
    "missing_middle",
    "fees",
    "parking",
    "tod",  # Handbook benchmark themes
    "lot_size",
    "process",
    "hoa",
    "moratorium",
    "other",  # confounders and state-specific reforms (C20, C21)
]
REFORM_STATUS = ["in_force", "suspended", "repealed", "opted_out", "pending"]
CODER_AGREEMENT = ["agree", "adjudicated", "single_coder"]
# Standard land uses every state crosswalk maps to (BUILD_PLAN §5.3). Extend only via `contract-change`.
LAND_USES = [
    "SF_DETACHED",
    "SF_ATTACHED",
    "DUPLEX",
    "TRI_QUAD",
    "MULTIFAMILY_5P",
    "MOBILE_HOME",
    "CONDO_UNIT",
    "VACANT_RESIDENTIAL",
    "MIXED_USE",
    "COMMERCIAL",
    "INDUSTRIAL",
    "AGRICULTURAL",
    "INSTITUTIONAL",
    "OTHER",
    "UNKNOWN",
]
UNITS_CONFIDENCE = ["reported", "derived", "inferred", "unknown"]
ADU_TYPES = ["attached", "detached", "internal_conversion", "unknown"]
FINAL_DATE_TYPES = ["certificate_of_occupancy", "completion", "final_inspection", "other"]
DATE_PRECISION = ["day", "month", "year"]
VALUE_BASIS = ["market", "assessed", "appraisal", "unknown"]
FEE_COMPONENTS = ["water_sewer", "impact", "permit", "planning", "other"]
FEE_BASIS = ["per_unit", "per_sqft", "per_lue", "pct_of_value", "flat", "other"]
DENOMINATOR_SOURCES = ["parcels", "acs_sf_fallback", "published"]
QUALITY = ["high", "medium", "low"]

_STATE = {"str_matches": r"^[A-Z]{2}$"}
_COUNT = {"ge": 0}


class _Strict(pa.DataFrameModel):
    class Config:
        strict = "filter"  # extra columns are dropped on validate, so adapters can carry raw fields upstream
        coerce = True  # booleans use pandas' nullable BooleanDtype, which rejects strings like "False" loudly


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
    """One row per parcel per roll vintage. Feeds the eligible-parcel rule (build/eligible.py)."""

    state: Series[str] = pa.Field(**_STATE)
    parcel_id: Series[str]  # normalized: county FIPS + local PIN where PINs repeat across counties
    vintage: Series[pd.Int64Dtype] = pa.Field(ge=1900, le=2100)  # roll year
    vintage_date: Optional[Series[pd.Timestamp]] = pa.Field(nullable=True)  # e.g. Wake pre-reval Dec 2023
    jurisdiction_geoid: Series[str]
    county_geoid: Optional[Series[str]] = pa.Field(nullable=True, str_matches=r"^\d{5}$")
    lot_sqft: Series[float] = pa.Field(ge=0, nullable=True)
    lot_width_ft: Optional[Series[float]] = pa.Field(nullable=True, ge=0)  # frontage (C14, C46)
    land_use_std: Series[str] = pa.Field(isin=LAND_USES)
    land_use_raw: Series[str] = pa.Field(nullable=True)
    units: Optional[Series[pd.Int64Dtype]] = pa.Field(nullable=True, ge=0)
    year_built: Optional[Series[pd.Int64Dtype]] = pa.Field(nullable=True)
    bldg_sqft: Optional[Series[float]] = pa.Field(nullable=True, ge=0)
    land_value: Optional[Series[float]] = pa.Field(nullable=True, ge=0)
    bldg_value: Optional[Series[float]] = pa.Field(nullable=True, ge=0)
    value_basis: Optional[Series[str]] = pa.Field(nullable=True, isin=VALUE_BASIS)  # TX: appraisal
    last_sale_price: Optional[Series[float]] = pa.Field(nullable=True, ge=0)
    last_sale_date: Optional[Series[pd.Timestamp]] = pa.Field(nullable=True)
    sale_qualified: Optional[Series[pd.BooleanDtype]] = pa.Field(nullable=True)  # arm's-length sale
    sale_multi_parcel: Optional[Series[pd.BooleanDtype]] = pa.Field(nullable=True)
    homestead: Optional[Series[pd.BooleanDtype]] = pa.Field(nullable=True)
    zoning_raw: Optional[Series[str]] = pa.Field(nullable=True)
    zoning_source: Optional[Series[str]] = pa.Field(nullable=True)  # e.g. "zoning layer", "planned land use"
    sf_only_zoned: Optional[Series[pd.BooleanDtype]] = pa.Field(nullable=True)
    hoa: Optional[Series[pd.BooleanDtype]] = pa.Field(nullable=True)  # exclusions where data allow (C12, C38)
    in_floodplain: Optional[Series[pd.BooleanDtype]] = pa.Field(nullable=True)
    in_historic_district: Optional[Series[pd.BooleanDtype]] = pa.Field(nullable=True)
    lon: Optional[Series[float]] = pa.Field(nullable=True, ge=-180, le=180)  # centroid, WGS84
    lat: Optional[Series[float]] = pa.Field(nullable=True, ge=-90, le=90)
    source: Series[str]

    @pa.dataframe_check
    def one_row_per_parcel_vintage(cls, df: pd.DataFrame) -> bool:
        return not df.duplicated(["state", "parcel_id", "vintage"]).any()


class EligibleParcels(_Strict):
    """The denominator: eligible parcels per jurisdiction-year, stored apart from permits (protocol §5.1-5.2).

    One row per jurisdiction, year and eligibility-rule version, so a rule change never overwrites history.
    """

    state: Series[str] = pa.Field(**_STATE)
    jurisdiction_geoid: Series[str]
    year: Series[pd.Int64Dtype] = pa.Field(ge=1980, le=2100)
    theme: Series[str] = pa.Field(isin=REFORM_THEMES)  # eligibility differs by reform (ADU vs MM lots)
    rule_version: Series[str]
    eligible_parcels: Series[pd.Int64Dtype] = pa.Field(ge=0)
    data_tier: Series[pd.Int64Dtype] = pa.Field(isin=DATA_TIERS)
    denominator_source: Series[str] = pa.Field(isin=DENOMINATOR_SOURCES)
    denominator_quality: Series[str] = pa.Field(isin=QUALITY)

    @pa.dataframe_check
    def one_row_per_key(cls, df: pd.DataFrame) -> bool:
        return not df.duplicated(["jurisdiction_geoid", "year", "theme", "rule_version"]).any()


class Permits(_Strict):
    """One row per permit, or per permit type × year where a source publishes only aggregates (`n_buildings`).

    `issue_year` is always set; `issue_date` only when the source has it (`date_precision` says which).
    Unit counts may be derived (Raleigh land-use codes) or inferred (Mecklenburg Census codes): say so in
    `units_confidence`, and leave them null if unknown.
    """

    state: Series[str] = pa.Field(**_STATE)
    permit_id: Series[str]
    parcel_id: Optional[Series[str]] = pa.Field(nullable=True)
    jurisdiction_geoid: Series[str]
    issue_year: Series[pd.Int64Dtype] = pa.Field(ge=1970, le=2100)
    issue_date: Series[pd.Timestamp] = pa.Field(nullable=True)
    date_precision: Series[str] = pa.Field(isin=DATE_PRECISION)
    application_date: Optional[Series[pd.Timestamp]] = pa.Field(nullable=True)  # approval time (C21)
    final_date: Optional[Series[pd.Timestamp]] = pa.Field(nullable=True)
    final_date_type: Optional[Series[str]] = pa.Field(nullable=True, isin=FINAL_DATE_TYPES)
    building_type_std: Series[str] = pa.Field(isin=BUILDING_TYPES)
    type_confidence: Series[str] = pa.Field(isin=TYPE_CONFIDENCE)
    adu_type: Optional[Series[str]] = pa.Field(nullable=True, isin=ADU_TYPES)
    permit_class_raw: Optional[Series[str]] = pa.Field(nullable=True)  # e.g. Austin R-102, Met Council type
    reform_flag_raw: Optional[Series[str]] = pa.Field(nullable=True)  # e.g. Raleigh missing_middle flag
    n_buildings: Optional[Series[pd.Int64Dtype]] = pa.Field(nullable=True, ge=0)  # aggregate rows
    units_new: Series[pd.Int64Dtype] = pa.Field(nullable=True, ge=0)
    units_removed: Series[pd.Int64Dtype] = pa.Field(nullable=True, ge=0)
    units_confidence: Series[str] = pa.Field(isin=UNITS_CONFIDENCE)
    is_demolition: Series[pd.BooleanDtype] = pa.Field(nullable=True)
    is_conversion: Series[pd.BooleanDtype] = pa.Field(nullable=True)
    floor_area_sqft: Optional[Series[float]] = pa.Field(nullable=True, ge=0)  # e.g. 750 sq ft bunching (V6c)
    zoning_raw: Optional[Series[str]] = pa.Field(nullable=True)  # district at the permit (Charlotte N1, V5)
    valuation_usd: Optional[Series[float]] = pa.Field(nullable=True, ge=0)
    fees_paid_usd: Optional[Series[float]] = pa.Field(nullable=True, ge=0)
    tenure: Optional[Series[str]] = pa.Field(nullable=True)
    source: Series[str]

    @pa.dataframe_check
    def one_row_per_permit(cls, df: pd.DataFrame) -> bool:
        return not df.duplicated(["state", "permit_id"]).any()

    @pa.dataframe_check
    def date_matches_year(cls, df: pd.DataFrame) -> bool:
        dated = df["issue_date"].notna()
        return bool((df.loc[dated, "issue_date"].dt.year == df.loc[dated, "issue_year"]).all())


class BpsPlaceYear(_Strict):
    """Census Building Permits Survey, annual, one row per permit-issuing place.

    `units_*` include Census imputation for months a place didn't report; `units_*_rep` are reported only.
    `imputed` is True when any month was imputed (months_reported < 12 or reported != total).
    """

    state: Series[str] = pa.Field(**_STATE)
    bps_id: Series[str] = pa.Field(str_matches=r"^\d{2}\d{6}$")  # state FIPS + BPS 6-digit ID
    # jurisdiction GEOID: place (7), county subdivision (10) or county for unincorporated areas (5)
    geoid: Series[str] = pa.Field(nullable=True)
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
    imputed: Series[pd.BooleanDtype]

    @pa.dataframe_check
    def one_row_per_place_year(cls, df: pd.DataFrame) -> bool:
        return not df.duplicated(["bps_id", "year"]).any()


class MarketGeoYear(_Strict):
    """Market conditions by geography and year. Each source fills its own columns; the rest may be absent.

    `geo` is prefixed by level so codes can't collide (county 27053 vs ZIP 27053): `national:US`,
    `state:27`, `cbsa:33460`, `county:27053`, `zip5:55415`, `tract:27053000100`.
    """

    geo: Series[str] = pa.Field(
        str_matches=r"^(national|state|cbsa|county|place|cousub|zip5|tract):[0-9A-Z]+$"
    )
    year: Series[pd.Int64Dtype] = pa.Field(ge=1940, le=2100)
    hpi: Optional[Series[float]] = pa.Field(nullable=True, gt=0)  # FHFA, base 100 in the series' first year
    hpi_base2000: Optional[Series[float]] = pa.Field(nullable=True, gt=0)  # comparable across places
    hpi_change_pct: Optional[Series[float]] = pa.Field(nullable=True)
    median_value: Optional[Series[float]] = pa.Field(nullable=True, ge=0)
    median_rent: Optional[Series[float]] = pa.Field(nullable=True, ge=0)
    ppi_resid_inputs: Optional[Series[float]] = pa.Field(nullable=True)
    mortgage_rate: Optional[Series[float]] = pa.Field(nullable=True)
    cpi_u: Optional[Series[float]] = pa.Field(nullable=True, gt=0)  # deflator: real dollars (protocol §5.9)

    @pa.dataframe_check
    def one_row_per_geo_year(cls, df: pd.DataFrame) -> bool:
        return not df.duplicated(["geo", "year"]).any()


class AcsGeoYear(_Strict):
    """American Community Survey 5-year estimates, long format: one row per geography, vintage and variable.

    `end_year` is the last year of the 5-year window (2023 = 2019-2023). Adjacent vintages share four years
    of sample, so never difference them; compare non-overlapping windows. `moe` is the published 90% margin
    of error (0 where Census marks the estimate as controlled). Labels are kept per vintage because some
    categories changed over time (e.g. B25034 year-built bands).
    """

    geo: Series[str] = pa.Field(str_matches=r"^(state|county|place|cousub|tract):[0-9]+$")
    end_year: Series[pd.Int64Dtype] = pa.Field(ge=2009, le=2100)
    table_id: Series[str] = pa.Field(str_matches=r"^[BC]\d{5}[A-Z]?$")
    variable: Series[str] = pa.Field(str_matches=r"^[BC]\d{5}[A-Z]?_\d{3}$")
    label: Series[str]
    estimate: Series[float] = pa.Field(nullable=True)
    moe: Series[float] = pa.Field(nullable=True, ge=0)

    @pa.dataframe_check
    def one_row_per_geo_vintage_variable(cls, df: pd.DataFrame) -> bool:
        return not df.duplicated(["geo", "end_year", "variable"]).any()


class Reforms(_Strict):
    """One row per reform component, coded with the protocol §5.4 rubric (a vector, not a yes/no).

    Amendments are new rows that `supersedes` the earlier one (dose increments, C09). Two coders per row,
    disagreements logged (protocol §5.4). Treatment timing: `adoption_date` vs `effective_date` (§5.3).
    """

    reform_id: Series[str] = pa.Field(unique=True)
    state: Series[str] = pa.Field(**_STATE)
    jurisdiction_geoid: Series[str]  # a 2-digit state GEOID for state laws
    theme: Series[str] = pa.Field(isin=REFORM_THEMES)
    component: Series[str]
    status: Series[str] = pa.Field(isin=REFORM_STATUS)
    announced_date: Optional[Series[pd.Timestamp]] = pa.Field(nullable=True)
    adoption_date: Optional[Series[pd.Timestamp]] = pa.Field(nullable=True)
    effective_date: Series[pd.Timestamp]
    end_date: Optional[Series[pd.Timestamp]] = pa.Field(
        nullable=True
    )  # suspended/repealed (e.g. MN 2040 plan)
    supersedes: Optional[Series[str]] = pa.Field(nullable=True)
    by_right: Series[pd.BooleanDtype] = pa.Field(nullable=True)
    owner_occ: Series[pd.BooleanDtype] = pa.Field(nullable=True)
    unit_cap: Series[pd.Int64Dtype] = pa.Field(nullable=True, ge=0)
    far_cap: Optional[Series[float]] = pa.Field(nullable=True, ge=0)
    max_stories: Optional[Series[float]] = pa.Field(nullable=True, ge=0)
    min_lot_sqft: Optional[Series[float]] = pa.Field(nullable=True, ge=0)  # C10
    adu_max_sqft: Optional[Series[float]] = pa.Field(nullable=True, ge=0)
    adu_detached_allowed: Optional[Series[pd.BooleanDtype]] = pa.Field(nullable=True)
    adus_per_lot: Optional[Series[pd.Int64Dtype]] = pa.Field(nullable=True, ge=0)
    lot_split: Series[pd.BooleanDtype] = pa.Field(nullable=True)
    parking: Series[str] = pa.Field(nullable=True)  # as written in the law
    parking_min_per_unit: Optional[Series[float]] = pa.Field(nullable=True, ge=0)
    fee_change_usd: Optional[Series[float]] = pa.Field(nullable=True)
    dollar_year: Optional[Series[pd.Int64Dtype]] = pa.Field(nullable=True, ge=1970, le=2100)
    coverage: Series[str]  # plain-language area description
    coverage_zones: Optional[Series[str]] = pa.Field(nullable=True)  # ";"-separated district codes, e.g. "N1"
    source_url: Series[str]
    coder: Series[str]
    coder_2: Series[str] = pa.Field(nullable=True)
    coder_agreement: Series[str] = pa.Field(isin=CODER_AGREEMENT)
    coding_notes: Optional[Series[str]] = pa.Field(nullable=True)  # disagreements and how they were resolved


class Fees(_Strict):
    """Development fees by jurisdiction, year, component and building type (protocol §5.9).

    Water/sewer is its own component. A fee charged as a percent of value goes in `pct_of_value` with
    `basis = "pct_of_value"`; a mixed fee is two rows (e.g. Raleigh: a per-unit amount plus a percent).
    """

    state: Series[str] = pa.Field(**_STATE)
    jurisdiction_geoid: Series[str]  # may be a region (e.g. Met Council SAC) via jurisdictions.kind = region
    year: Series[pd.Int64Dtype] = pa.Field(ge=1970, le=2100)
    effective_date: Optional[Series[pd.Timestamp]] = pa.Field(nullable=True)
    fee_component: Series[str] = pa.Field(isin=FEE_COMPONENTS)
    fee_type: Series[str]  # the source's own name for the fee
    building_type_std: Series[str] = pa.Field(isin=BUILDING_TYPES)
    basis: Series[str] = pa.Field(isin=FEE_BASIS)
    amount_usd: Series[float] = pa.Field(nullable=True, ge=0)  # per the basis (per unit, per LUE, ...)
    amount_per_unit_usd: Series[float] = pa.Field(nullable=True, ge=0)  # converted to one dwelling unit
    pct_of_value: Optional[Series[float]] = pa.Field(nullable=True, ge=0, le=100)
    dollar_year: Series[pd.Int64Dtype] = pa.Field(ge=1970, le=2100)
    payment_timing: Optional[Series[str]] = pa.Field(nullable=True)  # e.g. "at permit", "at CO" (C54)
    source: Series[str]

    @pa.dataframe_check
    def one_row_per_key(cls, df: pd.DataFrame) -> bool:
        key = ["jurisdiction_geoid", "year", "fee_component", "fee_type", "building_type_std", "basis"]
        return not df.duplicated(key).any()


TABLES: dict[str, type[pa.DataFrameModel]] = {
    "jurisdictions": Jurisdictions,
    "parcels": Parcels,
    "eligible_parcels": EligibleParcels,
    "permits": Permits,
    "bps_place_year": BpsPlaceYear,
    "market_geo_year": MarketGeoYear,
    "acs_geo_year": AcsGeoYear,
    "reforms": Reforms,
    "fees": Fees,
}


class ContractError(ValueError):
    """An adapter's output looks like a canonical table but has a misspelled column."""


def columns(table: str) -> list[str]:
    return list(TABLES[table].to_schema().columns)


def validate(df: pd.DataFrame, table: str) -> pd.DataFrame:
    """Return `df` coerced to the canonical schema for `table`, keeping only canonical columns.

    Extra columns are dropped (adapters may carry raw fields), except ones that look like a misspelling of a
    canonical column (e.g. `final_dat`): those raise ContractError, so an optional field is never lost
    silently. Raises pandera.errors.SchemaErrors listing every failing check (lazy validation).
    """
    if table not in TABLES:
        raise KeyError(f"unknown table {table!r}; expected one of {sorted(TABLES)}")
    canonical = columns(table)
    for extra in set(df.columns) - set(canonical):
        close = difflib.get_close_matches(str(extra), canonical, n=1, cutoff=0.85)
        if close:
            raise ContractError(f"{table}: column {extra!r} looks like a misspelling of {close[0]!r}")
    return TABLES[table].validate(df, lazy=True)


def assert_conforms(df: pd.DataFrame, table: str) -> None:
    """Contract-test helper: fail with every schema error at once."""
    validate(df, table)


# ---- data dictionary ---------------------------------------------------------------------------------------

_DTYPE_NAMES = {"Int64": "integer", "boolean": "true/false", "float64": "number", "datetime64[ns]": "date"}
HISTORY = [
    (
        "1.0",
        "seven canonical tables from BUILD_PLAN §5.1; bps_place_year adds bps_id, months, reported units",
    ),
    ("1.1", "market_geo_year: level-prefixed geo, FHFA HPI columns"),
    ("1.2", "acs_geo_year (ACS 5-year, long format with MOE)"),
    ("1.3", "market_geo_year.cpi_u"),
    (
        "1.4",
        "schemas-v1 freeze: eligible_parcels (denominator); permits allow year-only dates, unknown units "
        "and demolitions, ADU type, zoning, floor area; parcels eligibility inputs; reforms rubric fields, "
        "two coders, status and amendments; fees components, basis, dollar year; nullable booleans; "
        "misspelled-column guard",
    ),
]


def _describe_checks(col) -> str:
    out = []
    for ch in col.checks:
        stats = ch.statistics or {}
        if ch.name == "isin":
            out.append("one of " + ", ".join(f"`{v}`" for v in stats["allowed_values"]))
        elif ch.name == "str_matches":
            out.append(f"matches `{stats['pattern']}`")
        elif ch.name == "greater_than_or_equal_to":
            out.append(f"≥ {stats['min_value']}")
        elif ch.name == "greater_than":
            out.append(f"> {stats['min_value']}")
        elif ch.name == "less_than_or_equal_to":
            out.append(f"≤ {stats['max_value']}")
        elif ch.name == "in_range":
            out.append(f"{stats['min_value']} to {stats['max_value']}")
        else:
            out.append(ch.name)
    if col.unique:
        out.append("unique")
    return "; ".join(out)


def data_dictionary() -> str:
    """Markdown data dictionary for every canonical table, generated from the schemas (docs/schemas.md)."""
    lines = [
        "# Lotline: canonical tables (data dictionary)",
        "",
        "<!-- GENERATED from src/lotline/schemas.py by `lotline schemas --write`. Do not edit by hand. -->",
        "",
        f"**Schemas version {SCHEMAS_VERSION}** (tag `schemas-v1`). Every adapter's output is validated "
        "against these tables; a state that brings its own data only has to produce them.",
        "",
        "Conventions: unknown is null (never 0 or false); money is nominal dollars of the row's year "
        "unless `dollar_year` says otherwise; jurisdiction keys are Census GEOIDs (state 2, county 5, "
        "place 7, county subdivision 10 digits); combined categories are never split by guesswork. "
        "*Required* means the column must be present; *nullable* means its values may be empty.",
        "",
    ]
    for name, model in TABLES.items():
        schema = model.to_schema()
        doc = " ".join((model.__doc__ or "").split())
        lines += [f"## `{name}`", "", doc or "", ""]
        keys = [ch.name for ch in schema.checks]
        if keys:
            lines += ["Table checks: " + ", ".join(f"`{k}`" for k in keys), ""]
        lines += ["| Column | Type | Required | Nullable | Rule |", "|---|---|---|---|---|"]
        for col_name, col in schema.columns.items():
            dtype = str(col.dtype)
            dtype = _DTYPE_NAMES.get(dtype, "text" if "str" in dtype.lower() else dtype)
            lines.append(
                f"| `{col_name}` | {dtype} | {'yes' if col.required else 'no'} | "
                f"{'yes' if col.nullable else 'no'} | {_describe_checks(col)} |"
            )
        lines.append("")
    lines += ["## Version history", "", "| Version | Change |", "|---|---|"]
    lines += [f"| {v} | {c} |" for v, c in HISTORY] + [""]
    return "\n".join(lines)
