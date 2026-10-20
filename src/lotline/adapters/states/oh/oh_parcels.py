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

**Scope.** `COUNTIES` lists the counties downloaded: one server-side query per county and OBJECTID range
(`OID_CHUNK`), so each query stays shallow, is cached on its own and resumes after a failure.

Only non-personal fields are requested: no situs address, mailing address fields or CAMA links.
"""

from __future__ import annotations

import csv
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
    df, _ = assign_jurisdictions(build(raw, state=state, snapshot_date=snapshot_vintage()), state, store)
    df = holdout.apply(
        df,
        state,
        geoid_col="jurisdiction_geoid",
        date_col="vintage_date",
        year_col="vintage",
        snapshot=True,
    )
    return validate(df, TABLE)
