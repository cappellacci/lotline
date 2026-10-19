"""Charlotte "UDO Zoning Translation" layer → canonical `parcels` (pre-UDO zoning, V5 denominator).

The layer joins every parcel in Charlotte's zoning jurisdiction to its **pre-UDO** zoning district and the
**UDO** district it was translated to on 2023-06-01 (UDO Table 3-1). Its data were last edited on 2023-05-31,
the day before the V5 window opens (`config/states/nc.yaml`, holdout V5-NC-CHARLOTTE), so it is a roll taken
before the window and the snapshot holdout rule lets it through. That is the one reason to use it:
`reports/nc/charlotte_pre_udo_parcels.md` explains why no other public Charlotte parcel source is.

**Window guard.** Before anything is saved, `load()` reads the layer description over HTTP and checks
`editingInfo.dataLastEditDate`. If the layer was edited on or after the window opens (`outcome_from` of
the Charlotte holdout), it stops: such a layer is no longer the pre-window state and must not be fetched.
The same date becomes `vintage_date`, so `holdout.apply(..., snapshot=True)` re-checks it on every row.

**Fields.** Only these are requested (`OUT_FIELDS`): `taxpid`, pre- and post-UDO district and overlay,
zoning petition, rezone date, zoning class and `Shape__Area`, plus label points (centroids, WGS84) and
`last_edited_date`. The address (`FULL_ADDRESS`), editor user names and the hyperlink are never requested.

- `parcel_id` = "37119" + `taxpid` (the Mecklenburg parcel number, as in `onemap_parcels`); a repeated
  `taxpid` (split polygons) keeps the largest polygon and sums the areas.
- `lot_sqft` = `Shape__Area`. The layer's spatial reference is NC State Plane in US feet (EPSG 2264), so
  the area is in square feet.
- `zoning_raw` = `OldZoneDes` (the pre-UDO district, e.g. R-3, R-5(CD), UR-2(CD)); `zoning_source` names
  the layer. The UDO district (`ZoneDes`) has no canonical column; it follows from `zoning_raw` through
  UDO Table 3-1, except on parcels rezoned in the translation.
- `land_use_std` = UNKNOWN: the layer has no land use, year built or units (see the report for the gap).
- `jurisdiction_geoid` from the label point (`lotline.geo.place_or_township`), as in `onemap_parcels`:
  Charlotte is 3712000 even though BPS files Mecklenburg as one county row; other points go to 37119.
"""

from __future__ import annotations

import datetime as dt

import pandas as pd

from lotline.io import DataStore
from lotline.schemas import validate
from lotline.validation import holdout

ADAPTER = "states.nc.clt_udo_translation"
VERSION = "1.0"
SOURCE = "clt_udo_translation"
TABLE = "parcels"
LAYER_URL = (
    "https://services.arcgis.com/9Nl857LBlQVyzq54/arcgis/rest/services/"
    "Unified_Development_Ordinance_Zoning_Translation/FeatureServer/193"
)
LICENSE = "City of Charlotte open data (public records; no license stated)"
COUNTY = "37119"
CHARLOTTE = "3712000"
ZONING_SOURCE = "Charlotte UDO Zoning Translation layer (pre-UDO district)"
OUT_FIELDS = [
    "taxpid",
    "OldZoneDes",
    "ZoneDes",
    "OldOverlay",
    "Overlay",
    "ZonePetition",
    "RezoneDate",
    "ZoneClass",
    "Shape__Area",
    "last_edited_date",
]
PERSONAL = {"FULL_ADDRESS", "created_user", "last_edited_user", "Hyperlink"}

PROVENANCE = {
    "title": "City of Charlotte UDO Zoning Translation (parcels with pre-UDO and UDO districts, May 2023)",
    "landing_url": LAYER_URL,
    "table": TABLE,
    "cleaning": [
        "Window guard: the layer description is read first and nothing is downloaded unless "
        "editingInfo.dataLastEditDate falls before the Charlotte holdout window (2023-06-01); it read "
        "2023-05-31T18:29:59Z on 2026-10-19",
        "Requested fields exclude the address, editor user names and the hyperlink",
        "parcel_id = 37119 + taxpid; a repeated taxpid keeps the largest polygon's attributes, areas summed",
        "lot_sqft = Shape__Area (NC State Plane, US feet: square feet)",
        "zoning_raw = OldZoneDes (pre-UDO district); land_use_std = UNKNOWN (no land use in the layer)",
        "jurisdiction_geoid = place of the label point (TIGERweb ACS 2025), else 37119",
        "vintage_date = dataLastEditDate (2023-05-31), vintage 2023; holdout filter with snapshot=True",
    ],
    "limitations": [
        "Zoning only: no land use, year built, units or values, so it cannot split vacant from built lots",
        "The UDO district (ZoneDes) is not kept in the canonical table; it follows from UDO Table 3-1",
        "Covers Charlotte's zoning jurisdiction (city and ETJ), not the Mecklenburg towns",
    ],
}


def window_opens(state: str = "NC") -> pd.Timestamp:
    return min(pd.Timestamp(h.outcome_from) for h in holdout.holdouts_for(state) if h.geoid == CHARLOTTE)


def data_last_edited(meta: dict) -> pd.Timestamp:
    ms = (meta.get("editingInfo") or {}).get("dataLastEditDate")
    if ms is None:
        raise ValueError(f"{SOURCE}: the layer description has no editingInfo.dataLastEditDate")
    return pd.Timestamp(dt.datetime.fromtimestamp(ms / 1000, dt.UTC).replace(tzinfo=None))


def check_window(meta: dict, opens: pd.Timestamp) -> pd.Timestamp:
    """The layer's data edit time, or ValueError when it is not strictly before the holdout window."""
    edited = data_last_edited(meta)
    if edited.normalize() >= opens:
        raise ValueError(
            f"{SOURCE}: data last edited {edited.isoformat()}, on or after the Charlotte holdout window "
            f"({opens.date()}): the layer no longer shows the pre-UDO state and must not be fetched"
        )
    return edited


def build(raw: pd.DataFrame, edited: pd.Timestamp, state: str = "NC") -> pd.DataFrame:
    """Layer attributes (+ `lon`/`lat`) → `parcels` rows, before jurisdictions are assigned."""
    df = raw.copy()
    df["pin"] = df["taxpid"].astype("string").str.strip().replace("", pd.NA)
    df = df.loc[df["pin"].notna()].copy()
    df["area"] = pd.to_numeric(df["Shape__Area"], errors="coerce")
    total = df.groupby("pin")["area"].sum(min_count=1)
    df = df.sort_values("area", ascending=False, na_position="last").drop_duplicates("pin")
    vintage_date = edited.normalize()
    out = pd.DataFrame(
        {
            "state": state,
            "parcel_id": COUNTY + df["pin"],
            "vintage": vintage_date.year,
            "vintage_date": vintage_date,
            "county_geoid": COUNTY,
            "lot_sqft": df["pin"].map(total).astype("float64").where(lambda a: a > 0),
            "land_use_std": "UNKNOWN",
            "land_use_raw": pd.Series(pd.NA, index=df.index, dtype="string"),
            "zoning_raw": df["OldZoneDes"].astype("string").str.strip().replace("", pd.NA),
            "lon": pd.to_numeric(df.get("lon"), errors="coerce"),
            "lat": pd.to_numeric(df.get("lat"), errors="coerce"),
            "source": SOURCE,
        }
    )
    out["zoning_source"] = out["zoning_raw"].notna().map({True: ZONING_SOURCE, False: pd.NA}).astype("string")
    out["vintage"] = out["vintage"].astype("Int64")
    return out.reset_index(drop=True)


def assign_jurisdictions(df: pd.DataFrame, state: str, store: DataStore) -> pd.DataFrame:
    from lotline import geo

    place = geo.place_or_township(df["lon"], df["lat"], state, store).astype("string")
    return df.assign(jurisdiction_geoid=place.fillna(COUNTY))


def layer_description() -> dict:
    """The layer's JSON description, read over HTTP and not saved (the window is checked before saving)."""
    from lotline.io.http import client

    with client(timeout=60) as http:
        resp = http.get(LAYER_URL, params={"f": "json"})
        resp.raise_for_status()
        return resp.json()


def download(store: DataStore, *, refresh: bool = False) -> pd.DataFrame:
    from lotline.io.arcgis import download_layer

    return download_layer(
        LAYER_URL,
        store=store,
        source=SOURCE,
        license=LICENSE,
        adapter=ADAPTER,
        adapter_version=VERSION,
        name="udo_translation",
        out_fields=",".join(OUT_FIELDS),
        geometry="centroid",
        refresh=refresh,
    )


def load(state: str, store: DataStore, *, refresh: bool = False) -> pd.DataFrame:
    if state.upper() != "NC":
        raise ValueError(f"{SOURCE} covers Charlotte, North Carolina only, not {state}")
    edited = check_window(layer_description(), window_opens(state))
    df = build(download(store, refresh=refresh), edited, state=state)
    df = assign_jurisdictions(df, state, store)
    df = holdout.apply(
        df,
        state,
        geoid_col="jurisdiction_geoid",
        date_col="vintage_date",
        year_col="vintage",
        snapshot=True,
    )
    return validate(df, TABLE)
