"""City of Minneapolis Assessing Department parcel data (one table per assessment year) → `parcels`.

Proposed in place of `hennepin_parcels` (round 3, task 3): Hennepin County's parcel service sits on
`gis.hennepin.us`, whose robots.txt disallows every path for every agent, and the open-data Hub download of
it is a whole-file export that carries owner and taxpayer names and addresses (it can't be limited to non-
personal fields), and it has no unit count. The city's own assessor tables are CC0, served from ArcGIS
Online with field selection, and carry what the denominators need for Minneapolis: units (`TOTAL_UNITS`),
building use (incl. houses and duplexes with ADUs), property type, year built, zoning, lot area and values.

**Rolls.** One table per assessment year (`ASMTYEAR`); the city states values "as of January 2 of its
assessment year", so `vintage` = ASMTYEAR and `vintage_date` = January 2 of that year. The tables come in
three layouts (2017-2020, 2021-2024, 2025-2026); `LAYOUTS` maps each to the same names. Minneapolis is not a
holdout, but `holdout.apply(..., snapshot=True)` still runs on every roll.

**Units.** `TOTAL_UNITS` where positive. The 2025-2026 tables report 0 units for single-family houses, so a
0 on a residential parcel is unknown (null); on a non-residential or vacant parcel it is 0.

**Land use.** Property type (parcel) by `config/crosswalks/mn_land_use_mpls.csv`; for residential parcels
the building use overrides it where `config/crosswalks/mn_land_use_mpls_building.csv` has a rule (ADU
houses, apartment sizes); flagged rules are refined by `TOTAL_UNITS` (rule mechanics of `metc_parcels`).

**Personal data.** Owner and taxpayer names and the address fields are never requested (`LAYOUTS` lists
exactly what is read). Coordinates (`X`, `Y`) are in the Hennepin County coordinate system and are not
converted, so `lon`/`lat` stay null.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from lotline.adapters.states.mn import metc_parcels as metc
from lotline.config import CONFIG_DIR
from lotline.io import DataStore
from lotline.io.arcgis import download_layer
from lotline.schemas import validate
from lotline.validation import holdout

ADAPTER = "states.mn.mpls_assessor_parcels"
VERSION = "1.0"
SOURCE = "mpls_assessor_parcels"
TABLE = "parcels"
LICENSE = "CC0 1.0 (City of Minneapolis open data waiver)"
SERVICE_ROOT = "https://services.arcgis.com/afSMGVsC7QlRK1kZ/arcgis/rest/services"
LANDING_URL = "https://www.arcgis.com/home/item.html?id=d9bb827c0465472a937d325b22f9939d"
USE_CROSSWALK = CONFIG_DIR / "crosswalks" / "mn_land_use_mpls.csv"
BUILDING_CROSSWALK = CONFIG_DIR / "crosswalks" / "mn_land_use_mpls_building.csv"
MINNEAPOLIS = "2743000"
HENNEPIN = "27053"
YEARS = list(range(2017, 2027))
RESIDENTIAL = {
    "SF_DETACHED",
    "SF_ATTACHED",
    "DUPLEX",
    "TRI_QUAD",
    "MULTIFAMILY_5P",
    "CONDO_UNIT",
    "MIXED_USE",
}

# canonical name → field in each table layout. Only these are requested.
CANONICAL = [
    "pin",
    "asmt_year",
    "zoning",
    "area_sqft",
    "prop_type",
    "land_value",
    "bldg_value",
    "homestead",
    "building_use",
    "year_built",
    "above_ground_sqft",
    "units",
]
LAYOUTS = {
    "2017": dict(
        zip(
            CANONICAL,
            [
                "APN",
                "ASSESSMENT_YEAR",
                "ZONING",
                "PARCEL_AREA_SQFT",
                "PROPERTY_TYPE",
                "LANDVALUE",
                "BUILDINGVALUE",
                "HOMESTEAD",
                "BUILDINGUSE",
                "YEARBUILT",
                "ABOVEGROUNDAREA",
                "TOTAL_UNITS",
            ],
            strict=True,
        )
    ),
    "2021": dict(
        zip(
            CANONICAL,
            [
                "PIN",
                "ASMTYEAR",
                "ZONING",
                "PARCEL_AREA_SQFT",
                "PRIMARY_PROP_TYPE",
                "LANDVALUE",
                "BLDGVALUE",
                "IS_HOMESTEAD",
                "BUILDINGUSE",
                "YEARBUILT",
                "ABOVEGROUNDAREA",
                "TOTAL_UNITS",
            ],
            strict=True,
        )
    ),
    "2025": dict(
        zip(
            CANONICAL,
            [
                "TAX_MAP_UFMT",
                "ASMTYEAR",
                "ZONING",
                "PARCELAREA",
                "PROPERTYTYPE",
                "LANDVALUE",
                "BUILDINGVALUE",
                "HOMESTEAD",
                "BUILDINGUSE",
                "YEARBUILT",
                "ABOVEGROUNDAREA",
                "TOTALUNITS",
            ],
            strict=True,
        )
    ),
}
PIN_FIELD_2026 = "F_No_column_name_"  # the 2026 table's PIN column has no name in the source
PERSONAL = {
    "OWNERNAME",
    "OWNERNM",
    "TAXPAYER1",
    "TAXPAYER2",
    "TAXPAYER3",
    "TAXPAYER4",
    "FORMATTED_ADDRESS",
    "ADDRESSFORMATTED",
    "ANUMBER",
    "HOUSE_NO",
    "ST_NAME",
    "STREET_NAME",
    "ADRSTR",
}


@dataclass(frozen=True)
class Roll:
    year: int

    @property
    def service(self) -> str:
        prefix = "Assessors_Parcel_Data" if self.year <= 2022 else "Assessing_Department_Parcel_Data"
        return f"{prefix}_{self.year}"

    @property
    def url(self) -> str:
        return f"{SERVICE_ROOT}/{self.service}/FeatureServer/0"

    @property
    def fields(self) -> dict[str, str]:
        key = "2017" if self.year <= 2020 else ("2021" if self.year <= 2024 else "2025")
        fields = dict(LAYOUTS[key])
        if self.year == 2026:
            fields["pin"] = PIN_FIELD_2026
        return fields


PROVENANCE = {
    "title": "City of Minneapolis Assessing Department parcel data (assessment years 2017-2026)",
    "landing_url": LANDING_URL,
    "table": TABLE,
    "attribution": "City of Minneapolis Assessing Department (open data, CC0)",
    "cleaning": [
        f"One table per assessment year ({SERVICE_ROOT}/Assessors_Parcel_Data_2017 ... "
        "Assessing_Department_Parcel_Data_2026), downloaded with the ArcGIS pager, requesting only the PIN, "
        "assessment year, zoning, parcel area, property type, land and building value, homestead, building "
        "use, year built, above-ground area and total units (names differ by layout). Owner, taxpayer and "
        "address fields are never requested",
        "vintage = assessment year; vintage_date = January 2 of that year (the assessment date the city "
        "states)",
        "parcel_id = '27053' (Hennepin) + the 13-digit PIN (a leading 'p' and punctuation removed); the "
        "2025-2026 tables list one row per building: units and above-ground area are summed per PIN, year "
        "built is the earliest, building use is the building with the most units",
        "jurisdiction_geoid = 2743000 (Minneapolis); holdout filter applied with the snapshot rule",
        "land_use_std: property type by config/crosswalks/mn_land_use_mpls.csv, overridden for residential "
        "parcels by building use (config/crosswalks/mn_land_use_mpls_building.csv); flagged rules refined by "
        "TOTAL_UNITS; land_use_raw = property type | building use",
        "units = TOTAL_UNITS where > 0; a 0 is kept only on non-residential or vacant parcels (the 2025-2026 "
        "tables report 0 for single-family houses), else null",
        "lot_sqft = parcel area; year_built 1800 to the roll year + 1; bldg_sqft = above-ground area (> 0)",
        "land_value / bldg_value = the assessor's values as of January 2 (value_basis=market); homestead "
        "from HOMESTEADED / Y",
        "zoning_raw = ZONING, zoning_source = 'assessor'",
    ],
    "limitations": [
        "Minneapolis only; no sale prices; coordinates are in the county system and are not converted",
        "Layouts and labels change over time (property types were renamed in 2025); land use is rule-based",
        "TOTAL_UNITS is 0 for single-family houses in 2025-2026, so those units are null",
        "Assessment-date tables, not year-end rolls: the 2024 table describes parcels on 2024-01-02",
    ],
}


def to_parcels(raw: pd.DataFrame, roll: Roll, state: str = "MN") -> pd.DataFrame:
    """One roll's raw attributes → validated `parcels`."""
    raw = raw.drop(columns=[c for c in raw.columns if c in PERSONAL])
    df = raw.rename(columns={v: k for k, v in roll.fields.items()})
    pin = df["pin"].astype("string").str.upper().str.replace(r"[^0-9]", "", regex=True)
    df = df.assign(pin=pin.where(pin.str.fullmatch(r"\d{13}").fillna(False)))
    df = collapse_buildings(df[df["pin"].notna()])
    df = df.assign(
        jurisdiction_geoid=MINNEAPOLIS,
        vintage=pd.array([roll.year] * len(df), dtype="Int64"),
        vintage_date=pd.Timestamp(f"{roll.year}-01-02"),
    )
    df = holdout.apply(
        df, state, geoid_col="jurisdiction_geoid", date_col="vintage_date", year_col="vintage", snapshot=True
    )

    ptype = metc._norm_text(df["prop_type"]).str.upper()
    use = metc._norm_text(df["building_use"]).str.upper()
    units = pd.to_numeric(df["units"], errors="coerce").round().astype("Int64")
    positive = units.where(units > 0)
    county = pd.Series("Minneapolis", index=df.index)
    land = metc.land_use(
        county,
        ptype,
        use,
        positive,
        use_rules=metc.load_rules(USE_CROSSWALK),
        dwell_rules=metc.load_rules(BUILDING_CROSSWALK),
    )
    units = positive.mask((units == 0).fillna(False) & ~land.isin(RESIDENTIAL | {"UNKNOWN"}), 0)
    built = pd.to_numeric(df["year_built"], errors="coerce").round().astype("Int64")
    built = built.where(built.between(metc.MIN_YEAR_BUILT, roll.year + 1))
    home = df["homestead"].astype("string").str.strip().str.upper()
    homestead = home.map({"HOMESTEADED": True, "Y": True, "NON-HOMESTEADED": False, "N": False})

    def number(col: str) -> pd.Series:
        v = pd.to_numeric(df[col], errors="coerce").astype(float)
        return v.where(v >= 0)

    raw_label = (ptype.fillna("") + " | " + use.fillna("")).where(ptype.notna() | use.notna())
    out = pd.DataFrame(
        {
            "state": state,
            "parcel_id": HENNEPIN + df["pin"],
            "vintage": df["vintage"],
            "vintage_date": df["vintage_date"],
            "jurisdiction_geoid": MINNEAPOLIS,
            "county_geoid": HENNEPIN,
            "lot_sqft": number("area_sqft"),
            "land_use_std": land,
            "land_use_raw": raw_label,
            "units": units,
            "year_built": built,
            "bldg_sqft": number("above_ground_sqft").where(lambda s: s > 0),
            "land_value": number("land_value"),
            "bldg_value": number("bldg_value"),
            "value_basis": "market",
            "homestead": homestead.astype("boolean"),
            "zoning_raw": metc._norm_text(df["zoning"]),
            "zoning_source": "assessor",
            "source": SOURCE,
        }
    )
    return validate(out.reset_index(drop=True), TABLE)


def collapse_buildings(df: pd.DataFrame) -> pd.DataFrame:
    """One row per PIN. The 2025-2026 tables have a row per building: units and above-ground area are
    summed (units null if no building reports any), year built is the earliest, and the building use is
    that of the building with the most units; parcel fields (area, values, type) are the same on every row.
    """
    units = pd.to_numeric(df["units"], errors="coerce")
    df = df.assign(
        units=units,
        above_ground_sqft=pd.to_numeric(df["above_ground_sqft"], errors="coerce"),
        year_built=pd.to_numeric(df["year_built"], errors="coerce"),
    )
    df = df.sort_values("units", ascending=False, na_position="last", kind="stable")
    if not df["pin"].duplicated().any():
        return df
    grouped = df.groupby("pin", sort=False)
    first = grouped.first()
    first["units"] = grouped["units"].sum(min_count=1)
    first["above_ground_sqft"] = grouped["above_ground_sqft"].sum(min_count=1)
    first["year_built"] = grouped["year_built"].min()
    return first.reset_index()


def download(roll: Roll, store: DataStore, *, refresh: bool = False) -> pd.DataFrame:
    return download_layer(
        roll.url,
        store=store,
        source=SOURCE,
        license=LICENSE,
        adapter=ADAPTER,
        adapter_version=VERSION,
        name=f"parcels_{roll.year}",
        out_fields=",".join(roll.fields.values()),
        vintage=f"asmt_{roll.year}",
        retries=metc.RETRIES,
        refresh=refresh,
    )


def load(state: str, store: DataStore, *, refresh: bool = False) -> pd.DataFrame:
    if state.upper() != "MN":
        raise ValueError(f"{SOURCE} covers Minneapolis, Minnesota only, not {state}")
    tables = [to_parcels(download(Roll(y), store, refresh=refresh), Roll(y), state) for y in YEARS]
    return validate(pd.concat(tables, ignore_index=True), TABLE)
