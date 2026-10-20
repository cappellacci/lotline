"""Ramsey County attributed parcel points (current roll) → `parcels` for Ramsey County **outside St. Paul**.

Source: Ramsey County GIS, `Cadastral/CAD_AttributedParcelPoint_ViewOnly` (one point per tax parcel, including
manufactured homes). It adds what the Met Council regional layer lacks for Ramsey: lot frontage
(`ParcelFrontage` → `lot_width_ft`, C14) and the county's detailed land-use description.

**St. Paul.** The layer is a single current roll (property data joined 2026-10-08 at the first fetch), so
under the V5 snapshot rule St. Paul (2758000) can have no rows from it. Its parcels are excluded twice: the
server query leaves out `SiteCityName = 'SAINT PAUL'` (they are never downloaded; parcels with no site city
are fetched by a second query and placed by their point), and `holdout.apply(..., snapshot=True)` runs on
the point's jurisdiction and on the site city before any attribute is read. St. Paul's parcel state through
2023 comes from `metc_parcels` (the 2021-2023 rolls carry Ramsey's units and dwelling types).

**Land use.** `LandUseCodeDescription` → `land_use_std` by the ordered rules in
`config/crosswalks/mn_land_use_ramsey.csv`, refined by `LivingUnit` where a rule is flagged (the same rule
mechanics as `metc_parcels`).

**Personal data.** Owner, taxpayer and homestead names and addresses and the site address are in the layer and
are never requested: `FIELDS` lists exactly what is read.
"""

from __future__ import annotations

import pandas as pd

from lotline.adapters.states.mn import metc_parcels as metc
from lotline.config import CONFIG_DIR
from lotline.io import DataStore
from lotline.io.arcgis import download_layer
from lotline.schemas import validate
from lotline.validation import holdout

ADAPTER = "states.mn.ramsey_parcels"
VERSION = "1.0"
SOURCE = "ramsey_parcels"
TABLE = "parcels"
LICENSE = "Public data (Ramsey County GIS open data; no license terms stated, Minn. Stat. ch. 13)"
LAYER_URL = (
    "https://gis.ramseycountymn.gov/server/rest/services/Cadastral/"
    "CAD_AttributedParcelPoint_ViewOnly/FeatureServer/0"
)
LANDING_URL = "https://www.ramseycounty.us/your-government/open-government/research-data"
CROSSWALK = CONFIG_DIR / "crosswalks" / "mn_land_use_ramsey.csv"
RAMSEY = "27123"
ST_PAUL_SITE = "SAINT PAUL"
# Two queries: the county's firewall rejects "... OR ... IS NULL" in one where clause (HTTP 403).
WHERES = [f"SiteCityName <> '{ST_PAUL_SITE}'", "SiteCityName IS NULL"]

# Exactly what is read. Never "*": OwnerName*, OwnerAddress*, TaxName*, TaxAddress*, Homestead names and
# addresses and the site address fields identify people or homes.
FIELDS = [
    "OBJECTID",
    "ParcelID",
    "RollType",
    "SiteCityName",
    "HomesteadYN",
    "ParcelAcresPolygon",
    "ParcelAcresDeed",
    "ParcelFrontage",
    "EMVYear",
    "EMVLand",
    "EMVBuilding",
    "LandUseCode",
    "LandUseCodeDescription",
    "DwellingType",
    "LivingUnit",
    "LivingAreaSquareFeet",
    "YearBuilt",
    "LastSaleDate",
    "SalePrice",
    "PropertyDataJoinDate",
]
PERSONAL = {
    "OwnerLastName",
    "OwnerName",
    "OwnerName1",
    "OwnerName2",
    "OwnerAddress1",
    "OwnerAddress2",
    "OwnerCityStateZIP",
    "TaxName1",
    "TaxName2",
    "TaxAddress1",
    "TaxAddress2",
    "TaxCityStateZIP",
    "HomesteadName1",
    "HomesteadName2",
    "HomesteadAddress1",
    "HomesteadAddress2",
    "HomesteadCityStateZIP",
    "SiteAddress",
    "BuildingNumber",
    "StreetName",
}

PROVENANCE = {
    "title": "Ramsey County attributed parcel points (current roll, outside St. Paul)",
    "landing_url": LANDING_URL,
    "table": TABLE,
    "attribution": "Ramsey County GIS",
    "cleaning": [
        f"Download {LAYER_URL} with the ArcGIS pager into a dated snapshot, where {' / '.join(WHERES)} "
        "(two queries; parcels whose site city is St. Paul are never downloaded), requesting only "
        f"{', '.join(FIELDS)} and the point (WGS84). Owner, taxpayer and homestead names and addresses and "
        "the site address are never requested",
        "vintage_date = latest PropertyDataJoinDate (the roll's property-data date); vintage = its year",
        "parcel_id = '27123' + ParcelID (letters and digits only)",
        "jurisdiction_geoid by lotline.geo.place_or_township on the point, kept if in the MN jurisdictions "
        "table; else the jurisdiction SiteCityName names; else the county",
        "Held-out rows removed right after jurisdictions are assigned (V5 snapshot rule: a 2026 roll has no "
        "St. Paul rows), on both the point's jurisdiction and the site city's",
        "land_use_std from LandUseCodeDescription by config/crosswalks/mn_land_use_ramsey.csv, refined by "
        "LivingUnit for flagged rules; land_use_raw = LandUseCode: LandUseCodeDescription",
        "units = LivingUnit; lot_sqft = ParcelAcresPolygon (else ParcelAcresDeed) × 43,560; lot_width_ft = "
        "ParcelFrontage (> 0); year_built 1800 to the roll year + 1; bldg_sqft = LivingAreaSquareFeet (> 0)",
        "land_value / bldg_value = EMVLand / EMVBuilding (estimated market value, value_basis=market)",
        "last_sale_price / last_sale_date = SalePrice (> 0) / LastSaleDate; sale_multi_parcel = the same "
        "sale date and price on more than one parcel (null for sales dated the 1st of a month)",
        "homestead: HomesteadYN Y/P → True, N → False",
    ],
    "limitations": [
        "Current roll only: no history, and no St. Paul rows (V5 holdout); St. Paul parcels through 2023 "
        "come from metc_parcels",
        "Frontage is missing on many parcels (irregular and interior lots)",
        "Values are the assessor's estimated market value for the EMV year, not sale prices",
        "sale_multi_parcel can also flag separate sales at the same price on the same day",
    ],
}


def to_parcels(
    raw: pd.DataFrame, jurisdictions: pd.DataFrame, locate: metc.Locator, state: str = "MN"
) -> tuple[pd.DataFrame, pd.Series]:
    """Raw attributes (+ lon/lat) → validated `parcels` without held-out rows, and how each row was placed."""
    raw = raw.drop(columns=[c for c in raw.columns if c in PERSONAL])
    df = raw.assign(
        local_pin=metc._local_pin(raw["ParcelID"]),
        joined=metc._dates(raw["PropertyDataJoinDate"]),
    )
    df = df[df["local_pin"].notna()]
    df = df.assign(parcel_id=RAMSEY + df["local_pin"]).drop_duplicates("parcel_id", keep="first")
    vintage_date = df["joined"].max()
    year = int(vintage_date.year)

    lon = pd.to_numeric(df["lon"], errors="coerce")
    lat = pd.to_numeric(df["lat"], errors="coerce")
    county = pd.Series(RAMSEY, index=df.index, dtype="string")
    ctu = metc.ctu_geoids(df["SiteCityName"], metc.ctu_lookup(jurisdictions))
    geoid, how = metc.resolve(county, locate(lon, lat), ctu, set(jurisdictions["geoid"].astype(str)))
    df = df.assign(
        jurisdiction_geoid=geoid,
        ctu_geoid=ctu.fillna(""),
        how=how,
        vintage=pd.array([year] * len(df), dtype="Int64"),
        vintage_date=vintage_date,
        lon=lon,
        lat=lat,
    )
    # Before any attribute is read: the snapshot rule on the point's jurisdiction and on the site city's.
    rule = {"date_col": "vintage_date", "year_col": "vintage", "snapshot": True}
    df = holdout.apply(df, state, geoid_col="jurisdiction_geoid", **rule)
    df = holdout.apply(df, state, geoid_col="ctu_geoid", **rule)

    units = pd.to_numeric(df["LivingUnit"], errors="coerce").round().astype("Int64")
    units = units.where(units >= 0)
    built = pd.to_numeric(df["YearBuilt"], errors="coerce").round().astype("Int64")
    built = built.where(built.between(metc.MIN_YEAR_BUILT, year + 1))
    poly = pd.to_numeric(df["ParcelAcresPolygon"], errors="coerce")
    deed = pd.to_numeric(df["ParcelAcresDeed"], errors="coerce")
    acres = poly.where(poly > 0, deed.where(deed > 0))
    frontage = pd.to_numeric(df["ParcelFrontage"], errors="coerce").astype(float)
    price = pd.to_numeric(df["SalePrice"], errors="coerce").astype(float)
    price = price.where(price > 0)
    sold = metc._dates(df["LastSaleDate"])
    sale = price.notna() & sold.notna()
    multi = metc.multi_parcel_sales(pd.Series(RAMSEY, index=df.index), sold, price)
    homestead = (
        df["HomesteadYN"].astype("string").str.strip().str.upper().map({"Y": True, "P": True, "N": False})
    )
    desc = metc._norm_text(df["LandUseCodeDescription"])
    code = df["LandUseCode"].astype("string").str.strip()

    def money(col: str) -> pd.Series:
        v = pd.to_numeric(df[col], errors="coerce").astype(float)
        return v.where(v >= 0)

    out = pd.DataFrame(
        {
            "state": state,
            "parcel_id": df["parcel_id"],
            "vintage": df["vintage"],
            "vintage_date": df["vintage_date"],
            "jurisdiction_geoid": df["jurisdiction_geoid"],
            "county_geoid": RAMSEY,
            "lot_sqft": (acres * metc.SQFT_PER_ACRE).astype(float),
            "lot_width_ft": frontage.where(frontage > 0),
            "land_use_std": metc.land_use(
                pd.Series("Ramsey", index=df.index),
                desc,
                pd.Series(pd.NA, index=df.index, dtype="string"),
                units,
                use_rules=metc.load_rules(CROSSWALK),
                dwell_rules=[],
            ),
            "land_use_raw": (code.fillna("") + ": " + desc.fillna("")).where(desc.notna() | code.notna()),
            "units": units,
            "year_built": built,
            "bldg_sqft": money("LivingAreaSquareFeet").where(lambda s: s > 0),
            "land_value": money("EMVLand"),
            "bldg_value": money("EMVBuilding"),
            "value_basis": "market",
            "last_sale_price": price,
            "last_sale_date": sold.where(sale),
            "sale_multi_parcel": multi,
            "homestead": homestead.astype("boolean"),
            "lon": df["lon"],
            "lat": df["lat"],
            "source": SOURCE,
        }
    )
    return validate(out.reset_index(drop=True), TABLE), df["how"].reset_index(drop=True)


def download(store: DataStore, *, refresh: bool = False) -> pd.DataFrame:
    frames = [_query(where, store, refresh=refresh) for where in WHERES]
    return pd.concat([f for f in frames if len(f)], ignore_index=True)


def _query(where: str, store: DataStore, *, refresh: bool) -> pd.DataFrame:
    return download_layer(
        LAYER_URL,
        store=store,
        source=SOURCE,
        license=LICENSE,
        adapter=ADAPTER,
        adapter_version=VERSION,
        name="parcel_points",
        where=where,
        out_fields=",".join(FIELDS),
        geometry=True,
        retries=metc.RETRIES,
        refresh=refresh,
    )


def load(state: str, store: DataStore, *, refresh: bool = False) -> pd.DataFrame:
    if state.upper() != "MN":
        raise ValueError(f"{SOURCE} covers Ramsey County, Minnesota only, not {state}")
    from lotline import geo

    def locate(lon: pd.Series, lat: pd.Series) -> pd.Series:
        return geo.place_or_township(lon, lat, state, store)

    table, _ = to_parcels(download(store, refresh=refresh), metc._jurisdictions(state, store), locate, state)
    return table
