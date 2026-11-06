"""Oregon Metro RLIS Taxlots (Public) (Multnomah, Washington and Clackamas counties) → `parcels`, one row per
tax lot of the current roll.

**Layer.** Metro's Regional Land Information System compiles the three county assessors' tax lots each quarter
and standardizes selected attributes across the region (`Taxlots (Public)`, hosted FeatureServer layer 3,
648,079 features on 2026-11-06). It is read per county and FID range, attributes plus the server's polygon
label point (`geometry="centroid"`), so no polygons are downloaded.

**One roll.** RLIS Discovery publishes only the current roll: there are no dated tax-lot archives (the
"Vacant and Developed Land" series holds vacancy polygons, not a roll; `Taxlots Change - Geometry` lists
geometry edits since 2021). `vintage_date` is the layer's last data edit (`editingInfo.dataLastEditDate`) and
`vintage` its year. The November release carries the certified tax roll for the coming year (RLIS metadata).

**Rows.** Features without an assessor account (`PRIMACCNUM` blank: rights of way, rivers, tracts) are not tax
lots and are dropped. `parcel_id` = county GEOID + `TLID` (the map tax-lot number, letters and digits only);
a TLID repeated within a county keeps its first row (lowest FID).

**Jurisdiction.** `JURIS_CITY` is Metro's own city-boundary assignment (not the postal city). A city name that
matches one place in the OR jurisdictions table (case and the "city" suffix ignored) gives that place;
`UNINCORPORATED`, a blank, or a city not in the table (Gladstone, Banks, Rivergrove, ...: not Census permit
issuers, so BPS files them under the county) gives the county's remainder row (5-digit GEOID), the same rule
as the ACS fallback's county remainder (`build/eligible.py` `allocate_homes`).

**Land use.** `PROP_CODE` (the Oregon Department of Revenue property class, from each county's own class
field) → `land_use_std` by the ordered rules of `config/crosswalks/or_rlis_land_use.csv` (first match wins;
codes are zero-padded to three digits first). The class's last digit says vacant (0), improved (1) or
condominium (2). Residential land, improved (1x1) and tract land, improved (4x1, an acreage homesite) are
`SF_DETACHED`; residential land, vacant (1x0) is `VACANT_RESIDENTIAL`. Metro's own `LANDUSE` is derived from
the same code and is not read. No class (000), a blank or an unlisted code is `UNKNOWN`.

**Not in the layer.** Unit counts, building type (detached vs attached), zoning, HOA, floodplain and historic
district: those columns stay null (unknown), so `build/eligible.py` treats zoning as single-family-only and
flags it as an assumption, as for every other roll without zoning.

**Personal data.** The layer has no owner names; site address, site city and ZIP (`SITEADDR`, `SITECITY`,
`SITEZIP`) identify homes and are never requested: `FIELDS` lists exactly what is read.
"""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from lotline.config import CONFIG_DIR
from lotline.io import DataStore
from lotline.io.arcgis import download_layer, epoch_ms_to_timestamp, query_url
from lotline.io.http import fetch
from lotline.schemas import validate
from lotline.validation import holdout

ADAPTER = "states.or.rlis_parcels"
VERSION = "1.0"
SOURCE = "rlis_parcels"
TABLE = "parcels"
LICENSE = (
    "RLIS Open Database End User License Agreement (Metro, revised February 2023): copy, adapt and "
    "redistribute with attribution; compatible with CC BY 4.0 and ODC-By; personal data not licensed"
)
ATTRIBUTION = (
    "Regional Land Information System data are a product of Metro and made publicly available according to "
    "the license agreement found in https://rlisdiscovery.oregonmetro.gov/pages/open-database-license."
)
LAYER_URL = (
    "https://services2.arcgis.com/McQ0OlIABe29rJJy/arcgis/rest/services/Taxlots_(Public)/FeatureServer/3"
)
LANDING_URL = "https://rlisdiscovery.oregonmetro.gov/datasets/b3cabe5845ec47eab61c54e0c631313c"
METADATA_URL = "https://gis.oregonmetro.gov/rlis-metadata/#/details/3733"
USE_CROSSWALK = CONFIG_DIR / "crosswalks" / "or_rlis_land_use.csv"
SQFT_PER_ACRE = 43_560.0  # definition of the acre
MIN_YEAR_BUILT = 1800  # 0 and earlier years are placeholders in the county rolls
FID_CHUNK = 100_000  # FIDs per query: keeps paging offsets shallow (mechanics only)
RETRIES = 5  # pager retries on ArcGIS error bodies (mechanics only)
# RLIS county letter -> county GEOID (Census FIPS)
COUNTIES = {"M": "41051", "W": "41067", "C": "41005"}

# Exactly what is read. Never "*": SITEADDR, SITECITY and SITEZIP locate homes and are never requested.
FIELDS = [
    "FID",
    "TLID",
    "PRIMACCNUM",
    "COUNTY",
    "JURIS_CITY",
    "PROP_CODE",
    "A_T_ACRES",
    "AREA",
    "YEARBUILT",
    "BLDGSQFT",
    "LANDVAL",
    "BLDGVAL",
    "SALEDATE",
    "SALEPRICE",
]
PERSONAL = {"SITEADDR", "SITECITY", "SITEZIP", "OWNER1", "OWNER2", "OWNER3", "OWNERADDR"}

PROVENANCE = {
    "title": "Oregon Metro RLIS Taxlots (Public): Multnomah, Washington and Clackamas tax lots, current roll",
    "landing_url": LANDING_URL,
    "table": TABLE,
    "attribution": ATTRIBUTION,
    "cleaning": [
        f"Hosted layer {LAYER_URL}, downloaded per county (COUNTY M, W, C) and FID range, requesting only "
        + ", ".join(FIELDS)
        + " and the polygon label point (WGS84). No owner fields exist; site address, city and ZIP are "
        "never requested",
        "One roll: RLIS publishes no dated tax-lot archives. vintage_date = the layer's last data edit "
        "(editingInfo.dataLastEditDate); vintage = its year",
        "Features without an assessor account (PRIMACCNUM blank: rights of way, rivers, tracts) dropped",
        "parcel_id = county GEOID + TLID (letters and digits only); a TLID repeated within a county keeps "
        "its lowest-FID row",
        "jurisdiction_geoid: JURIS_CITY (Metro's city-boundary field) matched by name to an OR place in the "
        "jurisdictions table; UNINCORPORATED, blank, or a city not in the table → the county's remainder row",
        "land_use_std: PROP_CODE (Oregon DOR property class, zero-padded to 3 digits) by the ordered "
        "rules of config/crosswalks/or_rlis_land_use.csv; 1x1 residential improved and 4x1 tract improved → "
        "SF_DETACHED, 1x0 → VACANT_RESIDENTIAL; 000, blank or unlisted → UNKNOWN; land_use_raw = PROP_CODE",
        "lot_sqft = A_T_ACRES (assessor) × 43,560 where > 0, else AREA (GIS polygon square feet), else null",
        "year_built = YEARBUILT from 1800 to the roll year + 1, else null; bldg_sqft = BLDGSQFT > 0",
        "land_value / bldg_value = LANDVAL / BLDGVAL (real market value, value_basis=market)",
        "last_sale_price / last_sale_date = SALEPRICE (> 0) / SALEDATE (YYYYMM read as the 1st of the month, "
        "YYYYMMDD as the day; 1900 to the roll year + 1)",
    ],
    "limitations": [
        "Current roll only: no history before the roll, so other years are scaled from ACS "
        "(parcels_scaled_acs, #208)",
        "DOR class 1x1 (residential improved) does not tell a detached house from an attached townhouse on "
        "its own lot or a duplex: all are SF_DETACHED, so the count can exceed ACS one-unit-detached homes",
        "No unit counts, zoning, HOA, floodplain or historic-district fields: those stay unknown",
        "RLIS warns land use and PROP_CODE suit generalized maps, not parcel-specific use; field "
        "verification has not been done",
        "Values are the assessor's real market value for the roll's tax year, not sale prices; sale dates "
        "are mostly month-only, so sale_multi_parcel is left null",
        "Covers the three Metro counties only; every other Oregon jurisdiction stays on the ACS fallback",
    ],
}


# ---- land use --------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Rule:
    pattern: re.Pattern
    land_use_std: str


def load_rules(path: Path = USE_CROSSWALK) -> list[Rule]:
    with open(path, newline="") as fh:
        return [Rule(re.compile(r["pattern"]), r["land_use_std"].strip()) for r in csv.DictReader(fh)]


def prop_code(raw: pd.Series) -> pd.Series:
    """PROP_CODE stripped and zero-padded to three digits ('81' → '081'); <NA> when blank."""
    s = raw.astype("string").str.strip().replace("", pd.NA)
    digits = s.str.fullmatch(r"\d{1,3}").fillna(False).astype(bool)
    return s.mask(digits, s.str.zfill(3)).astype("string")


def land_use(raw: pd.Series, rules: list[Rule] | None = None) -> pd.Series:
    """`land_use_std` per row: the first rule whose pattern matches the padded code, else UNKNOWN."""
    rules = rules if rules is not None else load_rules()
    codes = prop_code(raw)
    lookup = {}
    for code in codes.dropna().unique():
        lookup[code] = next((r.land_use_std for r in rules if r.pattern.search(code)), "UNKNOWN")
    return codes.map(lookup).fillna("UNKNOWN").astype("string")


# ---- jurisdictions ---------------------------------------------------------------------------------------


def _name_key(name: str) -> str:
    """Lower case, single spaces: RLIS writes the bare city name ('OREGON CITY', 'KING CITY')."""
    return " ".join(name.strip().lower().split())


def _census_key(name: str) -> str:
    """A Census place name without its legal-description suffix: 'Oregon City city' → 'oregon city'."""
    return _name_key(re.sub(r"\s+city$", "", name.strip(), flags=re.I))


def city_lookup(jurisdictions: pd.DataFrame) -> dict[str, str]:
    """Normalized place name → GEOID for places whose name is unique in the table."""
    places = jurisdictions[jurisdictions["kind"] == "place"]
    keys = places["name"].map(_census_key)
    counts = keys.value_counts()
    return {k: g for k, g in zip(keys, places["geoid"], strict=True) if counts[k] == 1}


def resolve(
    juris_city: pd.Series, county_geoid: pd.Series, jurisdictions: pd.DataFrame
) -> tuple[pd.Series, pd.Series]:
    """(jurisdiction_geoid, how): the named city if it is a place in the table, else the county remainder."""
    lookup = city_lookup(jurisdictions)
    keys = juris_city.astype("string").fillna("").map(_name_key)
    city = keys.map(lookup).astype("string")
    found = city.notna()
    geoid = city.where(found, county_geoid.astype("string")).astype("string")
    how = pd.Series("county_remainder", index=juris_city.index, dtype="string").mask(found, "juris_city")
    return geoid, how


# ---- table -----------------------------------------------------------------------------------------------


def _tlid(values: pd.Series) -> pd.Series:
    clean = values.astype("string").str.upper().str.replace(r"[^0-9A-Z]", "", regex=True)
    return clean.mask(clean.str.fullmatch(r"0*").fillna(True)).astype("string")


def sale_dates(raw: pd.Series, latest_year: int) -> pd.Series:
    """SALEDATE text → timestamp: YYYYMM → 1st of the month, YYYYMMDD → the day; else (or outside
    1900..latest_year) NaT."""
    s = raw.astype("string").str.strip()
    month = pd.to_datetime(s.where(s.str.fullmatch(r"\d{6}").fillna(False)), format="%Y%m", errors="coerce")
    day = pd.to_datetime(s.where(s.str.fullmatch(r"\d{8}").fillna(False)), format="%Y%m%d", errors="coerce")
    out = day.fillna(month)
    ok = out.dt.year.between(1900, latest_year)
    return out.where(ok).astype("datetime64[ns]")


def _num(df: pd.DataFrame, col: str) -> pd.Series:
    return pd.to_numeric(df[col], errors="coerce").astype(float)


def to_parcels(
    raw: pd.DataFrame,
    vintage_date: pd.Timestamp,
    jurisdictions: pd.DataFrame,
    state: str = "OR",
    *,
    rules: list[Rule] | None = None,
) -> tuple[pd.DataFrame, pd.Series]:
    """The roll's raw features (+ lon/lat) → validated `parcels` without held-out rows, and how each row was
    placed (`juris_city` or `county_remainder`)."""
    raw = raw.drop(columns=[c for c in raw.columns if c in PERSONAL])
    account = raw["PRIMACCNUM"].astype("string").str.strip().replace("", pd.NA)
    county = raw["COUNTY"].astype("string").str.strip().str.upper().map(COUNTIES).astype("string")
    df = raw.assign(county_geoid=county, tlid=_tlid(raw["TLID"]))
    df = df[account.notna() & df["tlid"].notna() & df["county_geoid"].notna()]
    if "FID" in df:
        df = df.sort_values("FID", kind="stable")
    df = df.assign(parcel_id=df["county_geoid"] + df["tlid"]).drop_duplicates("parcel_id", keep="first")

    year = int(vintage_date.year)
    geoid, how = resolve(df["JURIS_CITY"], df["county_geoid"], jurisdictions)
    df = df.assign(
        jurisdiction_geoid=geoid,
        how=how,
        vintage=pd.array([year] * len(df), dtype="Int64"),
        vintage_date=pd.Series(vintage_date, index=df.index).astype("datetime64[ns]"),
    )
    # Before any attribute is read: the snapshot rule (a released holdout no longer hides anything).
    df = holdout.apply(
        df, state, geoid_col="jurisdiction_geoid", date_col="vintage_date", year_col="vintage", snapshot=True
    )

    acres = _num(df, "A_T_ACRES")
    area = _num(df, "AREA")
    lot = (acres * SQFT_PER_ACRE).where(acres > 0, area.where(area > 0))
    built = pd.to_numeric(df["YEARBUILT"], errors="coerce").round().astype("Int64")
    built = built.where(built.between(MIN_YEAR_BUILT, year + 1))
    price = _num(df, "SALEPRICE").where(lambda s: s > 0)
    sold = sale_dates(df["SALEDATE"], year + 1)
    sale = price.notna() & sold.notna()
    lon = pd.to_numeric(df["lon"], errors="coerce") if "lon" in df else pd.Series(float("nan"), df.index)
    lat = pd.to_numeric(df["lat"], errors="coerce") if "lat" in df else pd.Series(float("nan"), df.index)

    out = pd.DataFrame(
        {
            "state": state,
            "parcel_id": df["parcel_id"],
            "vintage": df["vintage"],
            "vintage_date": df["vintage_date"],
            "jurisdiction_geoid": df["jurisdiction_geoid"],
            "county_geoid": df["county_geoid"],
            "lot_sqft": lot.astype(float),
            "land_use_std": land_use(df["PROP_CODE"], rules),
            "land_use_raw": prop_code(df["PROP_CODE"]),
            "year_built": built,
            "bldg_sqft": _num(df, "BLDGSQFT").where(lambda s: s > 0),
            "land_value": _num(df, "LANDVAL").where(lambda s: s >= 0),
            "bldg_value": _num(df, "BLDGVAL").where(lambda s: s >= 0),
            "value_basis": "market",
            "last_sale_price": price.where(sale),
            "last_sale_date": sold.where(sale),
            "lon": lon.where(lon.between(-180, 180)),
            "lat": lat.where(lat.between(-90, 90)),
            "source": SOURCE,
        }
    )
    return validate(out.reset_index(drop=True), TABLE), df["how"].reset_index(drop=True)


# ---- download --------------------------------------------------------------------------------------------


def _fetch_json(url: str, name: str, store: DataStore, refresh: bool) -> dict:
    path = fetch(
        url,
        store.raw(SOURCE, pd.Timestamp.today().date().isoformat()) / "parcels" / name,
        store=store,
        source=SOURCE,
        license=LICENSE,
        adapter=ADAPTER,
        adapter_version=VERSION,
        refresh=refresh,
    )
    return json.loads(path.read_text())


def roll_date(store: DataStore, *, refresh: bool = False) -> pd.Timestamp:
    """The layer's last data edit (editingInfo.dataLastEditDate), as a date."""
    info = _fetch_json(f"{LAYER_URL}?f=json", "layer_info.json", store, refresh)
    ms = (info.get("editingInfo") or {}).get("dataLastEditDate")
    if ms is None:
        raise RuntimeError(f"{LAYER_URL} reports no editingInfo.dataLastEditDate; can't date the roll")
    return pd.Timestamp(epoch_ms_to_timestamp(pd.Series([ms])).iloc[0]).normalize()


def fid_ranges(store: DataStore, *, refresh: bool = False) -> dict[str, tuple[int, int]]:
    """County letter → (min, max) FID, from one statistics query downloaded through `fetch()`."""
    stats = json.dumps(
        [
            {"statisticType": "min", "onStatisticField": "FID", "outStatisticFieldName": "lo"},
            {"statisticType": "max", "onStatisticField": "FID", "outStatisticFieldName": "hi"},
        ]
    )
    url = query_url(
        LAYER_URL, where="1=1", groupByFieldsForStatistics="COUNTY", outStatistics=stats, f="json"
    )
    feats = _fetch_json(url, "fid_ranges.json", store, refresh)["features"]
    return {
        f["attributes"]["COUNTY"].strip(): (f["attributes"]["lo"], f["attributes"]["hi"])
        for f in feats
        if (f["attributes"].get("COUNTY") or "").strip() in COUNTIES
    }


def chunks(lo: int, hi: int, size: int = FID_CHUNK) -> list[tuple[int, int]]:
    """Half-open FID ranges [a, b) covering lo..hi."""
    start = lo - lo % size
    return [(a, a + size) for a in range(start, hi + 1, size)]


def download(store: DataStore, *, refresh: bool = False) -> pd.DataFrame:
    """One query per county and FID range, each cached and resumable on its own."""
    frames = []
    for county, (lo, hi) in sorted(fid_ranges(store, refresh=refresh).items()):
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
                    where=f"COUNTY='{county}' AND FID>={a} AND FID<{b}",
                    out_fields=",".join(FIELDS),
                    geometry="centroid",
                    retries=RETRIES,
                    refresh=refresh,
                )
            )
    frames = [f for f in frames if len(f)]
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=FIELDS)


def _jurisdictions(state: str, store: DataStore) -> pd.DataFrame:
    juris = store.read(state, "jurisdictions")
    if juris is None:
        from lotline.build import jurisdictions as jur

        juris = jur.load(state, store)
    return juris


def load(state: str, store: DataStore, *, refresh: bool = False) -> pd.DataFrame:
    if state.upper() != "OR":
        raise ValueError(f"{SOURCE} covers Oregon Metro's three counties only, not {state}")
    juris = _jurisdictions(state, store)
    table, _ = to_parcels(download(store, refresh=refresh), roll_date(store, refresh=refresh), juris, state)
    return table
