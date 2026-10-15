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

**Jurisdiction.** The layer has no city or township field. `jurisdiction_geoid` would need a point-in-polygon
join of parcel centroids to Census places and county subdivisions (townships), which needs a WS-CORE helper.
Until then the rows carry only `county_geoid`, and `load()` refuses to run (see `JURISDICTION_READY`), so a
county-wide denominator can never reach `eligible_parcels`. `build()` works for diagnostics.

**Scope.** `COUNTIES` lists the counties downloaded (server-side `County='...'` filter, one query per county).

Only non-personal fields are requested: no situs address, mailing address fields or CAMA links.
"""

from __future__ import annotations

import csv
import time
from pathlib import Path

import pandas as pd

from lotline.config import CONFIG_DIR
from lotline.io import DataStore
from lotline.io.arcgis import ArcGISError, download_layer, epoch_ms_to_timestamp
from lotline.schemas import validate
from lotline.validation import holdout

ADAPTER = "states.oh.oh_parcels"
VERSION = "0.1"
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
COUNTIES = ["Franklin", "Hamilton"]  # first pass; the full state is 88 counties (see PROVENANCE)
SQFT_PER_ACRE = 43_560.0
# The server intermittently answers deep-offset pages with "400: Invalid query parameters" and then serves the
# same page on a later try (seen on Franklin at offset ~418,000). Pages already fetched are cached, so a retry
# resumes where it stopped. (A retry in the shared pager would be better: WS-CORE request.)
RETRIES = 5
RETRY_WAIT_S = 20.0
JURISDICTION_READY = False  # flips once parcels can be placed in a city or township (WS-CORE helper)

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

PROVENANCE = {
    "title": "Ohio Statewide Parcels, public view (Ohio OGRIP; county auditor exports)",
    "landing_url": LANDING_URL,
    "table": TABLE,
    "cleaning": [
        "Requested fields exclude situs and mailing address fields and CAMA links (no personal data)",
        "Downloaded one county at a time with a server-side filter (County='<name>'); Franklin and Hamilton "
        "so far",
        "Rows without a LocalParcelID (polygons with no auditor record) are dropped; parcel_id = county "
        "GEOID + LocalParcelID; a parcel ID repeated within a county (stacked polygons) keeps one row, the "
        "largest polygon",
        "land_use_std from StateLUC via config/crosswalks/oh_dte_luc.csv (DTE land-use classes; 5x1-5x5 "
        "residential codes are the 5x0 use on unplatted acreage); county 'Custom Code' classes outside "
        "that pattern, 7xx abatement codes, 999 and blanks → UNKNOWN",
        "lot_sqft = LandArea (acres) × 43,560 where LandArea > 0, else Shape__Area (sq ft in EPSG:3735, "
        "Ohio South State Plane)",
        "vintage_date = the county's latest CurrentTo (export date); vintage = its year",
        "county_geoid from the county name via config/crosswalks/oh_county_fips.csv",
        "Holdout filter applied (Ohio has no holdouts); the snapshot rule (#100) is not on main yet",
    ],
    "limitations": [
        "No jurisdiction below the county: the layer has no city/township field. load() refuses to run "
        "until parcels are placed by point-in-polygon (needs a WS-CORE helper and parcel centroids)",
        "Attributes are minimal: no units, year built, building area, values or sales; county CAMA data are "
        "needed for those (tier 1 counties such as Franklin)",
        "County exports are of different dates (Franklin 2023-09-26, Hamilton 2023-08-02); the layer is "
        "a current snapshot, not a history",
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


def build(raw: pd.DataFrame, state: str = "OH") -> pd.DataFrame:
    """Raw layer attributes → `parcels` rows; jurisdiction_geoid stays null (only county_geoid is known)."""
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
    code = luc_code(df["StateLUC"])
    xwalk = luc_crosswalk()
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
            "source": SOURCE,
            "_shape": pd.to_numeric(df["Shape__Area"], errors="coerce"),
        },
        index=df.index,
    )
    out = out.sort_values(["parcel_id", "_shape"], ascending=[True, False], na_position="last")
    out = out.drop_duplicates(["state", "parcel_id", "vintage"], keep="first").drop(columns="_shape")
    return out.reset_index(drop=True)


def download(store: DataStore, *, counties: list[str] | None = None, refresh: bool = False) -> pd.DataFrame:
    frames = []
    for county in counties or COUNTIES:
        for attempt in range(1, RETRIES + 1):
            try:
                frames.append(
                    download_layer(
                        LAYER_URL,
                        store=store,
                        source=SOURCE,
                        license=LICENSE,
                        adapter=ADAPTER,
                        adapter_version=VERSION,
                        name="parcels",
                        where=f"County='{county}'",
                        out_fields=",".join(OUT_FIELDS),
                        refresh=refresh and attempt == 1,
                    )
                )
                break
            except ArcGISError:
                if attempt == RETRIES:
                    raise
                time.sleep(RETRY_WAIT_S * attempt)
    return pd.concat(frames, ignore_index=True)


def load(state: str, store: DataStore, *, refresh: bool = False) -> pd.DataFrame:
    if not JURISDICTION_READY:
        raise RuntimeError(
            "oh_parcels: parcels can't be placed in a city or township yet (no jurisdiction field in the "
            "layer). Writing county-wide rows would give eligible_parcels a wrong denominator, so load() is "
            "off until the WS-CORE point-in-polygon helper exists. Use build(download(store)) to inspect."
        )
    df = build(download(store, refresh=refresh), state=state)
    df = holdout.apply(df, state, geoid_col="jurisdiction_geoid", date_col="vintage_date", year_col="vintage")
    return validate(df, TABLE)
