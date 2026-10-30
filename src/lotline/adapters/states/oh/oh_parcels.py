"""Ohio Statewide Parcels, public view (Ohio OGRIP, ArcGIS FeatureServer) → canonical `parcels` (tier 2).

One polygon per county parcel, 6.31 million parcels in all 88 counties on 2026-10-15, assembled from county
auditor exports. The layer carries only a few attributes. This adapter reads two of them:

- `StateLUC`: the Ohio Department of Taxation (DTE) land-use class, e.g. "510: Res-Single Family", mapped to
  `land_use_std` by `config/crosswalks/oh_dte_luc.csv`. Residential codes 5x1-5x5 are the same use on an
  unplatted tract (the last digit is an acreage class), so 511-515 are single-family too. Codes the layer
  labels "Custom Code" outside that pattern mean different things in different counties and stay `UNKNOWN`.
- `LandArea`: the auditor's land area in acres. Franklin County leaves it empty or 0 for nearly every parcel
  (443,209 of 454,405), so `lot_sqft` falls back to the polygon area `Shape__Area` (square feet in the
  layer's Ohio South State Plane projection, EPSG:3735) where `LandArea` is missing or 0.

**Vintage.** The layer is edited as counties send new exports, so `vintage_date` is the county's export date
(`CurrentTo`, the latest in the county), and `vintage` its year: Franklin and Hamilton are both 2023 exports.

**Jurisdiction.** The layer has no city or township field, so each parcel's label point (centroid, requested
from the server) is placed with `lotline.geo.place_or_township`: an incorporated place, else the county
subdivision (Ohio townships issue permits). The result is then checked against the OH `jurisdictions` table
(the Census permit-issuing places and townships) by `resolve_jurisdictions`:

1. the place or township found, if it is in the table;
2. else the parcel's county subdivision, if that is in the table (a village that is not a permit issuer in
   its own right sits inside a township that is);
3. else the county's remainder row (`county_unincorporated`, 5-digit GEOID), e.g. for a parcel whose
   centroid falls in a fictitious or non-functioning subdivision (FUNCSTAT F/N), on a boundary sliver, or
   has no centroid, or where the county building department, not the township, permits unincorporated
   land (the case in Franklin and Hamilton, where the county remainder is the Census permit issuer). These
   counts are reported, not hidden.

**One roll per jurisdiction.** A city spanning two counties whose exports are dated differently (Twinsburg:
Summit 2026, Cuyahoga 2023) would otherwise get two partial "rolls", one per export year, each counted as the
whole city. The layer is one current snapshot, so after placement every parcel of a jurisdiction takes the
latest export date among its counties (`one_vintage_per_jurisdiction`; the later date is the conservative one
under the snapshot rule).

**County layers.** Where a county auditor publishes its own parcel layer, `COUNTY_LAYERS` names it, and its
attributes (no geometry) are joined on the parcel ID (`apply_county_attributes`): the county's DTE land-use
code fills `land_use_std` where the statewide layer has none (`UNKNOWN`), read with the same crosswalk, and
its residential year built becomes `year_built` (a year from 1700 to now; 0 or blank → unknown). A known
statewide code is never replaced. Summit County (Akron, Cuyahoga Falls) sends no land use to the statewide
layer; its Fiscal Office layer lists every parcel twice, identical rows, so the first row per parcel is kept.
Lucas (Toledo) leaves 55% blank; its Auditor's 2025 land-use layer fills them (no year built). Cuyahoga
(Cleveland) sends 999 for 12%; its Fiscal Office layer has 4-digit codes (the DTE class plus a county digit,
read as the first three), an exempt-use code where the tax code is blank (`ext_luc`: Cleveland's 25,000
land-bank and other exempt parcels) and the year each building was built (`min_age`, the oldest). Butler
(Hamilton, Middletown) has DTE land use and year built in the county's `CURRENTPARCELS` layer. Franklin
(Columbus) sends land use already; the Auditor's appraisal `Dwelling.xlsx` adds year built (one row per
dwelling card; the earliest is kept). A layer with `table` set is an Excel workbook, fetched through the IO
layer. Montgomery (Dayton) publishes no parcel land-use code: its weekly geodatabase (GIS_SQLDB, read on
2026-10-26) has only generalized land-use polygons and a building tax class, so Dayton stays on the ACS
fallback.

**Franklin County yearly rolls.** The statewide layer is one snapshot (Franklin: 2023), so every other
year of a place's denominator would be its ACS series scaled to that roll (D-035). The Franklin County
Auditor keeps a `Parcel.xlsx` (parcel ID, DTE land-use code) in every appraisal snapshot since 2016.
`FRANKLIN_ROLLS` reads the last snapshot of each year 2016-2025, except the statewide roll's own year, as
more `parcels` vintages (`franklin_yearly_rolls`), so `build.eligible` counts those years from real parcels
and scales only 2010-2015 (checked against the scaled history in `docs/build/oh-franklin-history-check.md`).
Rules:

- only jurisdictions with at least `FRANKLIN_MIN_SHARE` of their single-family houses in Franklin County get
  yearly rolls: the files cover Franklin only, so a city reaching into another county (Columbus, Dublin,
  Westerville) would be undercounted in those years; it keeps its single roll and the scaled history;
- an archive parcel takes the jurisdiction, lot size, year built and centroid of the same parcel in the
  statewide roll; a parcel not in it (split, combined or renumbered) takes its taxing district's jurisdiction
  where at least `FRANKLIN_DISTRICT_SHARE` of the district's roll parcels lie in one jurisdiction, with
  unknown lot size (dropped otherwise: about 50-280 eligible parcels a year county-wide);
- year built missing from the roll comes from the Auditor's `Dwelling.xlsx` (today's parcel numbers), so a
  renumbered parcel keeps it and a place's data tier (read from its latest roll) does not drop;
- land use comes from the archive's own code, through the same crosswalk.

**Scope.** `COUNTIES` lists the counties downloaded: one server-side query per county and OBJECTID range
(`OID_CHUNK`), so each query stays shallow, is cached on its own and resumes after a failure.

Only non-personal fields are requested: no situs address, mailing address fields or CAMA links.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from lotline.config import CONFIG_DIR
from lotline.io import DataStore
from lotline.io.arcgis import download_layer, epoch_ms_to_timestamp
from lotline.schemas import validate
from lotline.validation import holdout

ADAPTER = "states.oh.oh_parcels"
VERSION = "1.0"
SOURCE = "oh_parcels"
TABLE = "parcels"
LAYER_URL = (
    "https://services2.arcgis.com/MlJ0G8iWUyC7jAmu/arcgis/rest/services/"
    "OhioStatewidePacels_full_view/FeatureServer/0"
)
LANDING_URL = LAYER_URL
LICENSE = (
    "State of Ohio OGRIP public data, provided 'as is' (no use restrictions stated for public downloads)"
)
LUC_CROSSWALK = CONFIG_DIR / "crosswalks" / "oh_dte_luc.csv"
COUNTY_FIPS = CONFIG_DIR / "crosswalks" / "oh_county_fips.csv"
COUNTIES: list[str] | None = None  # None: all 88 counties in oh_county_fips.csv (a list limits the run)
SQFT_PER_ACRE = 43_560.0
# The server intermittently answers deep-offset pages with "400: Invalid query parameters" and serves the same
# page on a later try (seen on Franklin at offset ~418,000); the pager retries error bodies.
OID_CHUNK = 100_000  # OBJECTIDs per query (mechanics: keeps paging offsets shallow)
RETRIES = 5  # pager retries on ArcGIS error bodies (mechanics, not a model parameter)
YEAR_BUILT_MIN = 1700  # an earlier year built is a data error (unknown)


@dataclass(frozen=True)
class CountyLayer:
    """A county auditor's parcel layer whose attributes fill gaps in the statewide layer."""

    name: str
    url: str  # an ArcGIS layer, or an Excel workbook (`table` set: the sheet)
    license: str
    as_of: str  # the layer's last edit date, for provenance
    parcel_field: str  # the county's parcel number (= the statewide LocalParcelID)
    luc_field: str | None = None  # DTE land-use code (None: year built only)
    year_built_field: str | None = None
    exempt_luc_field: str | None = None  # the use code of a tax-exempt parcel, read where luc_field is blank
    table: str | int | None = None  # file only: the Excel sheet to read
    parcel_regex: str | None = None  # first group = the statewide LocalParcelID, where the formats differ


COUNTY_LAYERS: dict[str, CountyLayer] = {
    "39153": CountyLayer(
        name="summit",
        url=(
            "https://services3.arcgis.com/3Ukh5HzAdI6WZ3KP/arcgis/rest/services/"
            "TaxParcels_dashboard/FeatureServer/0"
        ),
        license=(
            "Summit County Fiscal Office public GIS data (ArcGIS Online, owner Summit_Admin; "
            "no reuse terms stated)"
        ),
        as_of="2025-03-25",
        parcel_field="PARCELID",
        luc_field="USECD",
        year_built_field="RESYRBLT",
    ),
    "39095": CountyLayer(
        name="lucas",
        url=(
            "https://lcaudgis.co.lucas.oh.us/gisaudserver/rest/services/Hosted/"
            "Parcel_General_Land_Use_Classification_2025/FeatureServer/0"
        ),
        license="Lucas County Auditor (AREIS) public GIS data (no reuse terms stated)",
        as_of="tax year 2025",
        parcel_field="parid",
        luc_field="luc",
    ),
    "39035": CountyLayer(
        name="cuyahoga",
        url="https://gis.cuyahogacounty.gov/server/rest/services/CCFO/Parcel_Fabric_Taxparcels/FeatureServer/0",
        license="Cuyahoga County Fiscal Office public GIS data (no reuse terms stated)",
        as_of="tax year 2026",
        parcel_field="parcel_id",
        luc_field="tax_luc",  # 4-digit: the DTE class plus a county digit ('5100' → 510)
        exempt_luc_field="ext_luc",  # blank tax_luc on exempt parcels (Cleveland land-bank lots: 6411)
        year_built_field="min_age",  # the oldest building's year built (the field holds years, not ages)
    ),
    "39017": CountyLayer(
        name="butler",
        url="https://maps.bcohio.gov/server/rest/services/PARCELSEARCH/MapServer/0",
        license="Butler County public GIS data (maps.bcohio.gov; no reuse terms stated)",
        as_of="read 2026-10-26",
        parcel_field="PIN",
        luc_field="LUC",
        year_built_field="YRBLT",
    ),
    "39049": CountyLayer(
        name="franklin",
        url=(
            "https://apps.franklincountyauditor.com/Outside_User_Files/2026/"
            "2026-10-15%20Appraisal/Dwelling.xlsx"
        ),
        license="Franklin County Auditor public records (disclaimer: 'as is'; no reuse terms stated)",
        as_of="appraisal snapshot 2026-10-15",
        parcel_field="PARCEL ID",  # '010-000002-00': district, parcel, card suffix
        year_built_field="YRBLT",  # one row per dwelling card; the earliest is kept
        table=0,
        parcel_regex=r"^(\d{3}-\d{6})",
    ),
}

PERSONAL = {
    "SitusAddressAll",
    "MailAddressAll",
    "MailNumber",
    "MailStreetPrefix",
    "MailStreetName",
    "MailStreetSuffix",
    "MailUnitNumber",
    "MailCity",
    "MailZip",
    "MailState",
}
OUT_FIELDS = [
    "OBJECTID",
    "County",
    "LocalParcelID",
    "StateParcelID",
    "StateLUC",
    "LandArea",
    "CurrentTo",
    "Shape__Area",
]

FRANKLIN_GEOID = "39049"
FRANKLIN_ROLL_URL = (
    "https://apps.franklincountyauditor.com/Outside_User_Files/{year}/{date}%20Appraisal/Parcel.xlsx"
)
FRANKLIN_LICENSE = "Franklin County Auditor public records (disclaimer: 'as is'; no reuse terms stated)"
# The last appraisal snapshot of each year (directory listings read 2026-10-27; 2015 and earlier have none).
FRANKLIN_ROLLS = {
    2016: "2016-12-22",
    2017: "2017-12-19",
    2018: "2018-12-17",
    2019: "2019-12-18",
    2020: "2020-12-25",
    2021: "2021-12-22",
    2022: "2022-12-20",
    2023: "2023-12-26",
    2024: "2024-12-30",
    2025: "2025-12-31",
}
FRANKLIN_MIN_SHARE = 0.99  # share of a jurisdiction's houses in Franklin County for it to get yearly rolls
FRANKLIN_DISTRICT_SHARE = 0.95  # taxing district → jurisdiction, for parcels missing from the statewide roll

PROVENANCE = {
    "title": "Ohio Statewide Parcels, public view (Ohio OGRIP; county auditor exports)",
    "landing_url": LANDING_URL,
    "table": TABLE,
    "cleaning": [
        "Requested fields exclude situs and mailing address fields and CAMA links (no personal data)",
        "Downloaded one county at a time (all 88) with a server-side filter (County='<name>') and OBJECTID "
        "ranges",
        "Rows without a LocalParcelID (polygons with no auditor record) are dropped; parcel_id = county "
        "GEOID + LocalParcelID; a parcel ID repeated within a county (stacked polygons) keeps one row, the "
        "largest polygon",
        "land_use_std from StateLUC via config/crosswalks/oh_dte_luc.csv (DTE land-use classes; 5x1-5x5 "
        "residential codes are the 5x0 use on unplatted acreage); county 'Custom Code' classes outside "
        "that pattern, 7xx abatement codes, 999 and blanks → UNKNOWN",
        "lot_sqft = LandArea (acres) × 43,560 where LandArea > 0, else Shape__Area (sq ft in EPSG:3735, "
        "Ohio South State Plane)",
        "vintage_date = the county's latest CurrentTo (export date); vintage = its year; a county with no "
        "CurrentTo on any parcel takes the download (snapshot) date",
        "county_geoid from the county name via config/crosswalks/oh_county_fips.csv",
        "County layers (COUNTY_LAYERS: Summit Fiscal Office as of 2025-03-25, Lucas Auditor tax year 2025, "
        "Cuyahoga Fiscal Office tax year 2026, Butler CURRENTPARCELS read 2026-10-26; owner and address "
        "fields never requested) joined on the parcel ID, attributes only: the county's DTE land-use code "
        "fills land_use_std where the statewide layer is UNKNOWN (never replacing a known code); residential "
        "year built → year_built (1700 to now, else unknown); a parcel listed more than once keeps its first "
        "code and its earliest year built (Summit lists each parcel twice; Franklin's Dwelling.xlsx, "
        "appraisal snapshot 2026-10-15, has one row per dwelling card and adds year built only)",
        "Franklin County yearly rolls: the Auditor's Parcel.xlsx (parcel ID, LUC) from the last appraisal "
        "snapshot of 2016-2025 (except the statewide roll's year) added as vintages for jurisdictions with "
        ">= 99% of their single-family houses in Franklin County; each parcel takes the statewide roll's "
        "jurisdiction, lot size, year built and centroid, else its taxing district's jurisdiction (>= 95% "
        "of the district in one jurisdiction) with unknown lot size, else it is dropped",
        "One roll per jurisdiction: after placement, a jurisdiction spanning counties with different export "
        "dates takes the latest one for all its parcels (8 jurisdictions on 2026-10-26, e.g. Twinsburg)",
        "Each parcel's label point (centroid, WGS84) is requested from the server (geometry='centroid') and "
        "stored as lon/lat",
        "jurisdiction_geoid by lotline.geo.place_or_township (TIGERweb ACS 2025 incorporated places, else "
        "county subdivisions), kept only if in the OH jurisdictions table; else the parcel's county "
        "subdivision if in the table; else the county's remainder row (5-digit GEOID)",
        "Holdout filter applied with snapshot=True (Ohio has no holdouts)",
    ],
    "limitations": [
        "Jurisdictions come from centroids and 2025 boundaries, not from the auditor: a parcel straddling a "
        "boundary goes wherever its label point falls, and annexations after 2025 are not reflected",
        "In Franklin and Hamilton no township is a permit issuer in the jurisdictions table (the county "
        "building department permits unincorporated land), so township parcels go to the county's remainder "
        "row (174,159 parcels on 2026-10-18), as do 9 villages outside the Census permit universe (8,679: "
        "Indian Hill, Amberley); 6 parcels had no centroid polygon match",
        "Attributes are minimal: no units, year built, building area, values or sales; county layers fill "
        "land use and year built only where listed in COUNTY_LAYERS (Summit, Lucas, Cuyahoga, Butler, "
        "Franklin); Montgomery (Dayton) publishes no parcel land-use code: its engineer's server failed TLS "
        "verification and the Auditor's weekly geodatabase (read 2026-10-26) has only generalized land-use "
        "polygons and a building tax class",
        "Lucas and Cuyahoga county GIS hosts dropped connections from some networks on 2026-10-26 (they "
        "answered over a VPN); a failed county download stops the run rather than silently skipping",
        "A county layer is of its own date (Summit 2025-03), not the statewide export's: a parcel created "
        "after it keeps the statewide (unknown) land use",
        "County exports are of different dates (Franklin 2023-09-26, Hamilton 2023-08-02); the layer is "
        "a current snapshot, not a history (Franklin County's yearly Auditor files are the exception)",
        "Franklin yearly rolls cover only places wholly in Franklin County: Columbus (97.7% of its houses), "
        "Dublin, Westerville, Reynoldsburg, Canal Winchester and others reaching into other counties keep "
        "one roll and D-035's scaled history; parcels created after 2023 are placed by taxing district, and "
        "50-280 eligible parcels a year with no dominant district are dropped",
        "Franklin's LandArea is empty or 0 for 97.5% of parcels, so its lot sizes are GIS polygon areas",
        "Shape__Area is in the Ohio South State Plane projection; for northern counties (Ohio North zone) "
        "the area carries a small projection error",
        "A parcel ID can repeat within a county (Hamilton 1,992, Franklin 15 on 2026-10-15: multi-polygon "
        "parcels); one row is kept, so a polygon-area lot size can miss the other parts",
        "'Custom Code' classes (e.g. 553 in Franklin, 508 in Hamilton) vary by county and stay UNKNOWN; "
        "county crosswalks from each auditor's code list would recover them",
    ],
}


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def luc_crosswalk(path: Path = LUC_CROSSWALK) -> dict[str, str]:
    """3-digit DTE class → land_use_std."""
    return {r["state_luc"]: r["land_use_std"] for r in _read_csv(path)}


def county_fips(path: Path = COUNTY_FIPS) -> dict[str, str]:
    return {r["county"]: r["county_geoid"] for r in _read_csv(path)}


def luc_code(raw: pd.Series) -> pd.Series:
    """'510: Res-Single Family' → '510'; blanks → <NA>."""
    return raw.astype("string").str.extract(r"^\s*(\d{3})", expand=False)


def lot_sqft(land_acres: pd.Series, shape_sqft: pd.Series) -> pd.Series:
    acres = pd.to_numeric(land_acres, errors="coerce")
    shape = pd.to_numeric(shape_sqft, errors="coerce")
    return (acres * SQFT_PER_ACRE).where(acres > 0, shape.where(shape > 0)).astype("float64")


def build(raw: pd.DataFrame, state: str = "OH", snapshot_date: str | None = None) -> pd.DataFrame:
    """Raw layer attributes (+ `lon`/`lat` centroids) → `parcels` rows, before jurisdictions are assigned."""
    df = raw.copy()
    df["local_id"] = df["LocalParcelID"].astype("string").str.strip().replace("", pd.NA)
    df = df.loc[df["local_id"].notna()].copy()
    fips = county_fips()
    df["county_geoid"] = df["County"].astype("string").str.strip().map(fips)
    unknown = sorted(set(df.loc[df["county_geoid"].isna(), "County"].dropna()))
    if unknown:
        raise ValueError(f"oh_parcels: counties not in {COUNTY_FIPS.name}: {unknown}")
    exported = epoch_ms_to_timestamp(df["CurrentTo"]).dt.normalize().astype("datetime64[ns]")
    vintage_date = exported.groupby(df["county_geoid"]).transform("max")
    # Some counties' exports carry no CurrentTo at all: their roll date is unknown, so they take the
    # download (snapshot) date, the latest date the roll can describe (conservative under the snapshot rule).
    if snapshot_date is not None:
        vintage_date = vintage_date.fillna(pd.Timestamp(snapshot_date))
    code = luc_code(df["StateLUC"])
    xwalk = luc_crosswalk()
    nan = pd.Series(float("nan"), index=df.index)
    out = pd.DataFrame(
        {
            "state": state,
            "parcel_id": df["county_geoid"] + df["local_id"],
            "vintage": vintage_date.dt.year.astype("Int64"),
            "vintage_date": vintage_date,
            "jurisdiction_geoid": pd.Series(pd.NA, index=df.index, dtype="string"),
            "county_geoid": df["county_geoid"],
            "lot_sqft": lot_sqft(df["LandArea"], df["Shape__Area"]),
            "land_use_std": code.map(xwalk).fillna("UNKNOWN"),
            "land_use_raw": df["StateLUC"].astype("string").str.strip().replace("", pd.NA),
            "lon": pd.to_numeric(df.get("lon", nan), errors="coerce"),
            "lat": pd.to_numeric(df.get("lat", nan), errors="coerce"),
            "source": SOURCE,
            "_shape": pd.to_numeric(df["Shape__Area"], errors="coerce"),
        },
        index=df.index,
    )
    out = out.sort_values(["parcel_id", "_shape"], ascending=[True, False], na_position="last")
    out = out.drop_duplicates(["state", "parcel_id", "vintage"], keep="first").drop(columns="_shape")
    return out.reset_index(drop=True)


def county_attributes(raw: pd.DataFrame, county_geoid: str, layer: CountyLayer) -> pd.DataFrame:
    """A county layer's rows → one row per parcel: parcel_id, luc (3-digit code), year_built.

    A parcel listed more than once (Summit's doubled rows, one row per dwelling card in Franklin) keeps its
    first land-use code and its earliest year built (the principal dwelling).
    """
    pid = raw[layer.parcel_field].astype("string").str.strip().replace("", pd.NA)
    if layer.parcel_regex:
        pid = pid.str.extract(layer.parcel_regex, expand=False)
    nan = pd.Series(pd.NA, index=raw.index, dtype="string")
    luc = luc_code(raw[layer.luc_field]) if layer.luc_field else nan
    if layer.exempt_luc_field:
        luc = luc.fillna(luc_code(raw[layer.exempt_luc_field]))
    if layer.year_built_field:
        year = pd.to_numeric(raw[layer.year_built_field], errors="coerce")
        year = year.where(year.between(YEAR_BUILT_MIN, pd.Timestamp.today().year)).astype("Int64")
    else:
        year = pd.Series(pd.NA, index=raw.index, dtype="Int64")
    out = pd.DataFrame({"parcel_id": county_geoid + pid, "luc": luc, "year_built": year}).loc[pid.notna()]
    agg = out.groupby("parcel_id", sort=False).agg(luc=("luc", "first"), year_built=("year_built", "min"))
    agg["year_built"] = agg["year_built"].astype("Int64")
    return agg.reset_index()


def apply_county_attributes(parcels: pd.DataFrame, attrs: pd.DataFrame, layer_name: str) -> pd.DataFrame:
    """Fill UNKNOWN land use and year built from a county layer (see the module docstring)."""
    xwalk = luc_crosswalk()
    a = attrs.set_index("parcel_id")
    out = parcels.copy()
    if "year_built" not in out:
        out["year_built"] = pd.Series(pd.NA, index=out.index, dtype="Int64")
    code = out["parcel_id"].map(a["luc"]).astype("string")
    std = code.map(xwalk)
    fill = out["land_use_std"].eq("UNKNOWN") & std.notna()
    out.loc[fill, "land_use_std"] = std[fill]
    out.loc[fill, "land_use_raw"] = code[fill] + f" ({layer_name} county layer)"
    year = out["parcel_id"].map(a["year_built"]).astype("Int64")
    out["year_built"] = out["year_built"].astype("Int64").fillna(year)
    return out


def read_county_file(path: Path, layer: CountyLayer, fields: list[str]) -> pd.DataFrame:
    """Named columns of a county Excel workbook (the only file format read so far)."""
    if path.suffix.lower() in (".xlsx", ".xls"):
        return pd.read_excel(
            path, sheet_name=layer.table or 0, usecols=fields, dtype={layer.parcel_field: str}
        )
    raise ValueError(f"oh_parcels: no reader for county file {path.name} (Excel workbooks only)")


def download_county(store: DataStore, layer: CountyLayer, *, refresh: bool = False) -> pd.DataFrame:
    optional = [layer.luc_field, layer.year_built_field, layer.exempt_luc_field]
    fields = [layer.parcel_field] + [f for f in optional if f]
    if layer.table is not None:
        from lotline.io.http import fetch

        name = layer.url.rsplit("/", 1)[-1]
        path = fetch(
            layer.url,
            store.raw(SOURCE, snapshot_vintage()) / f"county_{layer.name}" / name,
            store=store,
            source=SOURCE,
            license=layer.license,
            adapter=ADAPTER,
            adapter_version=VERSION,
            refresh=refresh,
        )
        return read_county_file(path, layer, fields)
    return download_layer(
        layer.url,
        store=store,
        source=SOURCE,
        license=layer.license,
        adapter=ADAPTER,
        adapter_version=VERSION,
        name=f"county_{layer.name}",
        out_fields=",".join(fields),
        retries=RETRIES,
        vintage=snapshot_vintage(),
        refresh=refresh,
    )


def one_vintage_per_jurisdiction(df: pd.DataFrame) -> pd.DataFrame:
    """Every parcel of a jurisdiction takes its latest county export date (see the module docstring)."""
    latest = df.groupby("jurisdiction_geoid")["vintage_date"].transform("max")
    out = df.assign(vintage_date=latest.fillna(df["vintage_date"]))
    out["vintage"] = out["vintage_date"].dt.year.astype("Int64").fillna(df["vintage"])
    return out


def franklin_share(df: pd.DataFrame) -> pd.Series:
    """Per jurisdiction reaching Franklin County: the share of its SF_DETACHED parcels inside it."""
    houses = df[df["land_use_std"] == "SF_DETACHED"]
    reach = houses.loc[houses["county_geoid"] == FRANKLIN_GEOID, "jurisdiction_geoid"].unique()
    houses = houses[houses["jurisdiction_geoid"].isin(reach)]
    return (houses["county_geoid"] == FRANKLIN_GEOID).groupby(houses["jurisdiction_geoid"]).mean()


def franklin_roll(
    raw: pd.DataFrame,
    date: str,
    current: pd.DataFrame,
    state: str = "OH",
    year_built: pd.Series | None = None,
) -> pd.DataFrame:
    """One year-end `Parcel.xlsx` (PARCEL ID, LUC) → `parcels` rows of vintage `date`'s year.

    `current` is the statewide roll's Franklin parcels, already placed: it gives each archive parcel its
    jurisdiction and attributes, or, for a parcel missing from it, the taxing district's jurisdiction.
    `year_built` (by parcel ID, from the Auditor's `Dwelling.xlsx`) fills year built for parcels not in it.
    """
    pid = raw["PARCEL ID"].astype("string").str.strip().str.extract(r"^(\d{3}-\d{6})", expand=False)
    df = pd.DataFrame({"parcel_id": FRANKLIN_GEOID + pid, "code": luc_code(raw["LUC"])}).loc[pid.notna()]
    df = df.drop_duplicates("parcel_id")
    attrs = ["jurisdiction_geoid", "lot_sqft", "year_built", "lon", "lat"]
    cur = current.drop_duplicates("parcel_id").set_index("parcel_id")
    df = df.join(cur[[c for c in attrs if c in cur]], on="parcel_id")
    district = cur.index.str[5:8]
    juris = cur["jurisdiction_geoid"]
    top = juris.groupby(district).agg(lambda j: j.value_counts().index[0])
    share = juris.groupby(district).agg(lambda j: j.value_counts(normalize=True).iloc[0])
    fallback = top[share >= FRANKLIN_DISTRICT_SHARE]
    df["jurisdiction_geoid"] = df["jurisdiction_geoid"].fillna(df["parcel_id"].str[5:8].map(fallback))
    df = df.loc[df["jurisdiction_geoid"].notna()]
    built = df["year_built"].astype("Int64") if "year_built" in df else pd.Series(pd.NA, index=df.index)
    if year_built is not None:
        built = built.astype("Int64").fillna(df["parcel_id"].map(year_built).astype("Int64"))
    when = pd.Timestamp(date)
    xwalk = luc_crosswalk()
    return pd.DataFrame(
        {
            "state": state,
            "parcel_id": df["parcel_id"],
            "vintage": pd.Series(when.year, index=df.index, dtype="Int64"),
            "vintage_date": when,
            "jurisdiction_geoid": df["jurisdiction_geoid"].astype("string"),
            "county_geoid": FRANKLIN_GEOID,
            "lot_sqft": pd.to_numeric(df.get("lot_sqft"), errors="coerce").astype("float64"),
            "land_use_std": df["code"].map(xwalk).fillna("UNKNOWN"),
            "land_use_raw": (df["code"] + f" (Franklin Auditor {date})").astype("string"),
            "year_built": built.astype("Int64"),
            "lon": pd.to_numeric(df.get("lon"), errors="coerce").astype("float64"),
            "lat": pd.to_numeric(df.get("lat"), errors="coerce").astype("float64"),
            "source": SOURCE,
        }
    )


def download_franklin_roll(store: DataStore, date: str, *, refresh: bool = False) -> pd.DataFrame:
    from lotline.io.http import fetch

    path = fetch(
        FRANKLIN_ROLL_URL.format(year=date[:4], date=date),
        store.raw("franklin_auditor", date) / "Parcel.xlsx",
        store=store,
        source="franklin_auditor",
        license=FRANKLIN_LICENSE,
        adapter=ADAPTER,
        adapter_version=VERSION,
        refresh=refresh,
    )
    return pd.read_excel(path, usecols=["PARCEL ID", "LUC"], dtype=str)


def franklin_yearly_rolls(
    df: pd.DataFrame, rolls: dict[str, pd.DataFrame], year_built: pd.Series | None = None
) -> pd.DataFrame:
    """Add Franklin County yearly rolls (raw `Parcel.xlsx` frames by snapshot date) to the placed statewide
    roll, for jurisdictions wholly in the county; the statewide roll's own year is skipped."""
    current = df[df["county_geoid"] == FRANKLIN_GEOID]
    if current.empty:
        return df
    share = franklin_share(df)
    whole = set(share.index[share >= FRANKLIN_MIN_SHARE])
    have = set(current["vintage"].dropna().astype(int))
    extra = []
    for date, raw in rolls.items():
        if pd.Timestamp(date).year in have:
            continue
        roll = franklin_roll(raw, date, current, state=str(df["state"].iloc[0]), year_built=year_built)
        roll = roll[roll["jurisdiction_geoid"].isin(whole)]
        if len(roll):
            extra.append(roll)
    return pd.concat([df, *extra], ignore_index=True) if extra else df


def resolve_jurisdictions(
    county_geoid: pd.Series, found: pd.Series, cousub: pd.Series, known: set[str]
) -> tuple[pd.Series, pd.Series]:
    """(jurisdiction_geoid, how) per parcel, using only GEOIDs in the jurisdictions table (`known`).

    `found` is `place_or_township` (place, else county subdivision); `cousub` the county subdivision alone.
    `how` is "place", "township", "township_of_place" (a place not in the table → its township) or
    "county_fallback" (neither is in the table, or no centroid: the county's remainder row).
    """
    found = found.astype("string")
    cousub = cousub.astype("string")
    in_found = found.isin(known).fillna(False).astype(bool)
    in_cousub = cousub.isin(known).fillna(False).astype(bool)
    geoid = found.where(in_found, cousub.where(in_cousub, county_geoid.astype("string")))
    how = pd.Series("county_fallback", index=found.index, dtype="string")
    how = how.mask(in_cousub & ~in_found, "township_of_place")
    how = how.mask(in_found & found.str.len().eq(10), "township")
    how = how.mask(in_found & found.str.len().eq(7), "place")
    return geoid, how


def assign_jurisdictions(df: pd.DataFrame, state: str, store: DataStore) -> tuple[pd.DataFrame, pd.Series]:
    """Fill `jurisdiction_geoid` from the centroids; return the rows and how each was placed."""
    from lotline import geo
    from lotline.adapters.national.tiger_boundaries import load_polygons
    from lotline.build import jurisdictions as jur

    juris = store.read(state, "jurisdictions")
    if juris is None:
        juris = jur.load(state, store)
    known = set(juris["geoid"])
    found = geo.place_or_township(df["lon"], df["lat"], state, store)
    cousub = pd.Series(
        geo.assign(df["lon"].to_numpy(), df["lat"].to_numpy(), load_polygons(state, store, "cousub")),
        index=df.index,
        dtype=object,
    )
    geoid, how = resolve_jurisdictions(df["county_geoid"], found, cousub, known)
    return df.assign(jurisdiction_geoid=geoid), how


def snapshot_vintage() -> str:
    """Raw-snapshot folder: today's date, or `OH_PARCELS_VINTAGE` (YYYY-MM-DD) to resume an earlier run.

    A statewide run takes most of a day; resuming it on a later date with the same vintage reuses the pages
    already cached instead of starting a new snapshot.
    """
    import os

    return os.environ.get("OH_PARCELS_VINTAGE") or pd.Timestamp.today().date().isoformat()


def oid_range(store: DataStore, *, refresh: bool = False) -> tuple[int, int]:
    """(min, max) OBJECTID of the layer, from a statistics query downloaded through `fetch()`."""
    import json

    from lotline.io.arcgis import query_url
    from lotline.io.http import fetch

    stats = json.dumps(
        [
            {"statisticType": "min", "onStatisticField": "OBJECTID", "outStatisticFieldName": "lo"},
            {"statisticType": "max", "onStatisticField": "OBJECTID", "outStatisticFieldName": "hi"},
        ]
    )
    url = query_url(LAYER_URL, where="1=1", outStatistics=stats, f="json")
    path = fetch(
        url,
        store.raw(SOURCE, snapshot_vintage()) / "parcels" / "oid_range.json",
        store=store,
        source=SOURCE,
        license=LICENSE,
        adapter=ADAPTER,
        adapter_version=VERSION,
        refresh=refresh,
    )
    attrs = json.loads(path.read_text())["features"][0]["attributes"]
    return int(attrs["lo"]), int(attrs["hi"])


def chunks(lo: int, hi: int, size: int = OID_CHUNK) -> list[tuple[int, int]]:
    """Half-open OBJECTID ranges [a, b) covering lo..hi."""
    start = lo - lo % size
    return [(a, a + size) for a in range(start, hi + 1, size)]


def download(store: DataStore, *, counties: list[str] | None = None, refresh: bool = False) -> pd.DataFrame:
    """One query per county and OBJECTID range, so no query pages deeper than OID_CHUNK rows.

    Paging one county to the end (450,000 rows on Franklin) slows to 30+ s a page and the server starts
    failing pages past an offset of about 400,000. A county's OBJECTIDs are spread over the whole layer, so
    the ranges are the layer's (empty ones return at once); each range is its own cached, resumable query.
    """
    lo, hi = oid_range(store, refresh=refresh)
    frames = []
    for county in counties or COUNTIES or sorted(county_fips()):
        for a, b in chunks(lo, hi):
            frames.append(
                download_layer(
                    LAYER_URL,
                    store=store,
                    source=SOURCE,
                    license=LICENSE,
                    adapter=ADAPTER,
                    adapter_version=VERSION,
                    name="parcels",
                    where=f"County='{county}' AND OBJECTID>={a} AND OBJECTID<{b}",
                    out_fields=",".join(OUT_FIELDS),
                    geometry="centroid",
                    retries=RETRIES,
                    vintage=snapshot_vintage(),
                    refresh=refresh,
                )
            )
    frames = [f for f in frames if len(f)]
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=OUT_FIELDS)


def load(state: str, store: DataStore, *, refresh: bool = False) -> pd.DataFrame:
    raw = download(store, refresh=refresh)
    df = build(raw, state=state, snapshot_date=snapshot_vintage())
    franklin_years = None
    for county_geoid, layer in COUNTY_LAYERS.items():
        attrs = county_attributes(download_county(store, layer, refresh=refresh), county_geoid, layer)
        df = apply_county_attributes(df, attrs, layer.name)
        if county_geoid == FRANKLIN_GEOID:
            franklin_years = attrs.set_index("parcel_id")["year_built"]
    df, _ = assign_jurisdictions(df, state, store)
    df = one_vintage_per_jurisdiction(df)
    rolls = {date: download_franklin_roll(store, date, refresh=refresh) for date in FRANKLIN_ROLLS.values()}
    df = franklin_yearly_rolls(df, rolls, year_built=franklin_years)
    df = holdout.apply(
        df,
        state,
        geoid_col="jurisdiction_geoid",
        date_col="vintage_date",
        year_col="vintage",
        snapshot=True,
    )
    return validate(df, TABLE)
