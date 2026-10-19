"""Wake County real estate roll, final pre-revaluation file of December 2023 → canonical `parcels` (tier 1).

Wake County Tax Administration posts its full real estate file daily and kept the last file before the
2024 revaluation (`Real_Est_Data_Final_Dec2023.xlsx`, posted 2024-01-02). That file is the **V2 baseline
state** for Raleigh: the parcels as they stood before 2024-26 permits.

**Record layout.** The spreadsheet's 87 column names match the county's Record Layout (as of 2019-01-14) field
for field, without the layout's "Unused" filler; codes are in the county's Code Descriptions list. One row
per *card* (building record): 443,785 cards for 427,566 parcels (`REAL_ESTATE_ID`). Values, acreage, sale
and land class repeat on every card; units and heated area are per card.

- **Parcel.** `parcel_id` = "37183" + `REAL_ESTATE_ID`. Card 01 gives the parcel's Type & Use, Design Style
  and year built (the main building); `units` and `bldg_sqft` add up all cards.
- **Land use** (`config/crosswalks/nc_land_use_wake_realestate.csv`, same codes as the OneMap Wake crosswalk):
  1. Type & Use + Design Style on card 01, so a ONE FAMILY card styled TOWNHOUSE, CONDO or DUPLEX is
     attached, a condominium unit or a duplex;
  2. Type & Use alone;
  3. the Land Class letter; a residential class with no building value is vacant.
- **Year built.** `Year_Built` of card 01; 0 is unknown.
- **Lot size.** `Deeded_Acreage` × 43,560.
- **Values.** Assessed land and building values from the 2020 revaluation (`value_basis = "assessed"`).
- **Last sale.** `Total_sale_Price` / `Total_Sale_Date`; `sale_qualified` when the county's qualifying flag
  is A (single-property) or C (multi-property), `sale_multi_parcel` when it is C. Other flags disqualify;
  no flag means unknown.
- **Zoning.** `Zoning` as recorded by the assessor (`zoning_source = "county tax roll"`).
- **Jurisdiction.** `CITY` (the city whose limits contain the parcel) via
  `config/crosswalks/nc_land_use_wake_jurisdictions.csv`; outside city limits → Wake's county remainder
  (37183). No coordinates in the file.

**Vintage.** `vintage_date` 2023-12-31 (the "Final Dec2023" roll; the file's web listing shows 2024-01-02),
`vintage` 2023. Wake has no holdout; `holdout.apply(..., snapshot=True)` runs anyway.

**Privacy.** The spreadsheet carries owner names and mailing addresses. Only the columns in `USECOLS` are
read, so owner, mailing, street-address, legal-description, deed and free-text fields never reach memory or
the table. The raw file stays in `LOTLINE_DATA_DIR` as downloaded.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd

from lotline.adapters.states.nc.onemap_parcels import map_land_use
from lotline.config import CONFIG_DIR
from lotline.io import DataStore
from lotline.schemas import validate
from lotline.validation import holdout

ADAPTER = "states.nc.wake_realestate"
VERSION = "1.0"
SOURCE = "wake_realestate"
TABLE = "parcels"
BASE = "https://services.wake.gov/realdata_extracts"
ROLL_URL = f"{BASE}/Real_Est_Data_Final_Dec2023.xlsx"
ROLL_VINTAGE = "2023-12"  # raw folder name
VINTAGE_DATE = pd.Timestamp("2023-12-31")  # "Final Dec2023" roll, the last before the 2024 revaluation
LANDING_URL = (
    "https://www.wake.gov/departments-government/tax-administration/data-files-statistics-and-reports/"
    "real-estate-property-data-files"
)
LICENSE = "Wake County public records (no license stated)"
LAND_USE_CSV = CONFIG_DIR / "crosswalks" / "nc_land_use_wake_realestate.csv"
CITY_CSV = CONFIG_DIR / "crosswalks" / "nc_land_use_wake_jurisdictions.csv"
LAND_USE_FIELDS = ("TYPE_AND_USE|DESIGN_STYLE", "TYPE_AND_USE", "Land_classification")
BUILDING_FIELDS = 2  # the first two describe the building; Land_classification is the land use
COUNTY = "37183"
SQFT_PER_ACRE = 43_560.0
QUALIFIED = {"A", "C"}  # Code Descriptions: qualifying sale flags (C = multi-property)

PERSONAL = {
    "OWNER1", "OWNER2", "Mailing_address1", "Mailing_Address2", "Mailing_Address3",
    "Street_Number", "Street_Prefix", "Street_Name", "Street_Type", "Street_Suffix", "Street_Misc",
    "PROPERTY_DESCRIPTION", "PROPERTY_INDEX", "DEED_BOOK", "DEED_PAGE", "Special_Write_In",
    "PHYSICAL_CITY", "PHYSICAL_ZIP_CODE", "BILLING_CLASS",
}  # fmt: skip
USECOLS = [
    "REAL_ESTATE_ID",
    "CARD_NUMBER",
    "Zoning",
    "Deeded_Acreage",
    "Total_sale_Price",
    "Total_Sale_Date",
    "Assessed_Building_Value",
    "Assessed_Land_Value",
    "Land_classification",
    "Year_Built",
    "UNITS",
    "HEATED_AREA",
    "DESIGN_STYLE",
    "TYPE_AND_USE",
    "CITY",
    "Disq_and_Qual_flag",
]

PROVENANCE = {
    "title": "Wake County real estate roll, final pre-revaluation file (December 2023)",
    "landing_url": LANDING_URL,
    "table": TABLE,
    "cleaning": [
        "Only non-personal columns are read (USECOLS): owner names, mailing and street addresses, legal "
        "description, property index, deed book/page, special write-in and billing class are never loaded",
        "Column names checked against the county Record Layout (2019-01-14): all 87 match, without 'Unused'",
        "One row per card collapsed to one per parcel: card 01 gives Type & Use, Design Style, year built; "
        "units and heated area summed over cards; values, acreage, sale, zoning, city repeat on every card",
        "parcel_id = 37183 + REAL_ESTATE_ID",
        "land_use_std via config/crosswalks/nc_land_use_wake_realestate.csv: Type & Use + Design Style, then "
        "Type & Use, then Land Class; a residential Land Class with no building value → VACANT_RESIDENTIAL",
        "year_built = Year_Built of card 01 when 1700..2023; 0 → unknown",
        "lot_sqft = Deeded_Acreage × 43,560; land/bldg values assessed (2020 revaluation)",
        "last_sale_price/date = Total_sale_Price/Total_Sale_Date (price 0 → unknown); sale_qualified = "
        "flag A or C; sale_multi_parcel = flag C; no flag → unknown",
        "jurisdiction_geoid from CITY via config/crosswalks/nc_land_use_wake_jurisdictions.csv; outside "
        "city limits → 37183 (county remainder)",
        "vintage_date 2023-12-31, vintage 2023; holdout filter applied with snapshot=True (no Wake holdout)",
    ],
    "limitations": [
        "One county only (Wake); values are as of the 2020 revaluation, not market values in 2023",
        "Jurisdiction is the assessor's city code (no coordinates); parcels in Raleigh's ETJ outside city "
        "limits go to the county remainder",
        "Design Style on card 01 only; multi-card parcels (1.1% of cards) take the main building's type",
        "Last sale only, not a sales history; the 24-month qualified-sales file (raw only) has no "
        "canonical table yet",
    ],
}


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def land_use_crosswalk(path: Path = LAND_USE_CSV) -> dict[tuple[str, str], str]:
    return {(r["field"], r["code"].strip()): r["land_use_std"] for r in _read_csv(path)}


def city_geoids(path: Path = CITY_CSV) -> dict[str, str]:
    return {r["city_code"]: r["geoid"] for r in _read_csv(path) if r["geoid"]}


def _num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce")


def build(raw: pd.DataFrame, state: str = "NC") -> pd.DataFrame:
    """Card rows (USECOLS, as text) → one `parcels` row per REAL_ESTATE_ID."""
    df = raw.copy()
    df["reid"] = df["REAL_ESTATE_ID"].astype("string").str.strip().replace("", pd.NA)
    df = df.loc[df["reid"].notna()].copy()
    df["card"] = _num(df["CARD_NUMBER"])
    df = df.sort_values(["reid", "card"])
    per_parcel = df.groupby("reid", sort=False)
    sums = pd.DataFrame(
        {"units": per_parcel["UNITS"].apply(lambda s: _num(s).sum(min_count=1)),
         "bldg_sqft": per_parcel["HEATED_AREA"].apply(lambda s: _num(s).sum(min_count=1))}
    )  # fmt: skip
    main = df.drop_duplicates("reid", keep="first").set_index("reid")  # card 01 (lowest card number)
    main = main.join(sums)
    std, lu_raw = map_land_use(
        main,
        land_use_crosswalk(),
        LAND_USE_FIELDS,
        vacant_when_unimproved=True,
        building_fields=BUILDING_FIELDS,
        bldg_col="Assessed_Building_Value",
    )
    year = _num(main["Year_Built"])
    year = year.where((year >= 1700) & (year <= VINTAGE_DATE.year)).round().astype("Int64")
    acres = _num(main["Deeded_Acreage"])
    price = _num(main["Total_sale_Price"])
    flag = main["Disq_and_Qual_flag"].astype("string").str.strip().replace("", pd.NA)
    city = main["CITY"].astype("string").str.strip()
    out = pd.DataFrame(
        {
            "state": state,
            "parcel_id": COUNTY + main.index.astype("string"),
            "vintage": VINTAGE_DATE.year,
            "vintage_date": VINTAGE_DATE,
            "jurisdiction_geoid": city.map(city_geoids()).fillna(COUNTY).astype("string"),
            "county_geoid": COUNTY,
            "lot_sqft": (acres * SQFT_PER_ACRE).where(acres > 0).astype("float64"),
            "land_use_std": std,
            "land_use_raw": lu_raw,
            "units": main["units"].round().astype("Int64"),
            "year_built": year,
            "bldg_sqft": main["bldg_sqft"].where(main["bldg_sqft"] > 0).astype("float64"),
            "land_value": _num(main["Assessed_Land_Value"]).where(lambda v: v >= 0),
            "bldg_value": _num(main["Assessed_Building_Value"]).where(lambda v: v >= 0),
            "value_basis": "assessed",
            "last_sale_price": price.where(price > 0).astype("float64"),
            "last_sale_date": pd.to_datetime(main["Total_Sale_Date"], errors="coerce"),
            "sale_qualified": flag.map(lambda f: f in QUALIFIED, na_action="ignore").astype("boolean"),
            "sale_multi_parcel": flag.map(lambda f: f == "C", na_action="ignore").astype("boolean"),
            "zoning_raw": main["Zoning"].astype("string").str.strip().replace("", pd.NA),
            "source": SOURCE,
        }
    )
    out["zoning_source"] = out["zoning_raw"].notna().map({True: "county tax roll", False: pd.NA})
    out["zoning_source"] = out["zoning_source"].astype("string")
    out["vintage"] = out["vintage"].astype("Int64")
    return out.reset_index(drop=True)


def download(store: DataStore, *, refresh: bool = False) -> Path:
    from lotline.io.http import fetch

    return fetch(
        ROLL_URL,
        store.raw(SOURCE, ROLL_VINTAGE) / Path(ROLL_URL).name,
        store=store,
        source=SOURCE,
        license=LICENSE,
        adapter=ADAPTER,
        adapter_version=VERSION,
        refresh=refresh,
    )


def read(path: Path) -> pd.DataFrame:
    """The roll's non-personal columns only, as text."""
    return pd.read_excel(path, usecols=USECOLS, dtype=str, engine="openpyxl")


def load(state: str, store: DataStore, *, refresh: bool = False) -> pd.DataFrame:
    df = build(read(download(store, refresh=refresh)), state=state)
    df = holdout.apply(
        df,
        state,
        geoid_col="jurisdiction_geoid",
        date_col="vintage_date",
        year_col="vintage",
        snapshot=True,
    )
    return validate(df, TABLE)
