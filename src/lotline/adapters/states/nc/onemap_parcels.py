"""NC OneMap statewide parcels (NC1Map_Parcels, county-sourced) → canonical `parcels`.

NC OneMap (NC Center for Geographic Information and Analysis) transforms each county's parcel export into one
statewide layer with standard field names. The values inside some fields are still each county's own:

- **Land use.** `parusecode`, `parusedesc`, `parusecd2` and `parusedsc2` hold whatever the county sends.
  Wake sends its Type & Use code in `parusecd2` and its one-letter Land Class in `parusedesc`; Mecklenburg
  its building type in `parusecd2` and land use in `parusedesc`; Durham its zoning district in `parusecode`
  and its land-use description in `parusedesc`. `config/crosswalks/nc_land_use_counties.csv` says, per
  county, which fields to read in which order (the first field with a crosswalk match wins) and points to
  the county's crosswalk `config/crosswalks/nc_land_use_<county>.csv` (field, code → `land_use_std`).
  Where the county flag `vacant_when_unimproved` is set, a residential match from a fallback field (a land
  use, not a building type) on a parcel with no building value (`improvval` 0 or empty) becomes
  `VACANT_RESIDENTIAL`: the land use says "single-family", but nothing is built yet.
- **Year built.** `structyear`; 0 or empty means unknown (completeness differs by county).
- **Lot size.** `gisacres` (GIS polygon area) × 43,560.
- **Values.** `landval` / `improvval`, the county's assessed values as of its last revaluation
  (`value_basis = "assessed"`; NC assesses at market value as of the revaluation date).

**Vintage.** The layer is a current roll only. `vintage_date` is the county's latest transform date from
`NC1Map_Parcels_Transform_Dates` (one polygon per county), and `vintage` its year.

**Jurisdiction.** Each parcel point is placed with `lotline.geo.place_or_township`: the incorporated place
(TIGERweb ACS 2025) the point falls in, else the county's remainder row (5-digit GEOID; NC townships do not
issue permits). The place GEOID is kept even when the place is not in the NC `jurisdictions` table (the
Census permit universe): BPS files Charlotte and the other Mecklenburg towns under Mecklenburg County, so
mapping them to the county would hide Charlotte from the holdout filter. `assign_jurisdictions` returns how
each parcel was placed so these cases can be reported.

**Holdout.** Charlotte (3712000) is the V5 holdout from 2023-06-01. This roll is from 2026, so every
Charlotte parcel is dropped by the snapshot rule (`holdout.apply(..., snapshot=True)`) before anything is
returned. The rest of Mecklenburg stays.

**Privacy.** Only non-personal fields are requested (see `OUT_FIELDS`): no owner names or types, mailing or
site addresses, legal descriptions, subdivision names or deed references.
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

ADAPTER = "states.nc.onemap_parcels"
VERSION = "1.0"
SOURCE = "onemap_parcels"
TABLE = "parcels"
SERVICE = "https://services.nconemap.gov/secure/rest/services"
LAYER_URL = f"{SERVICE}/NC1Map_Parcels/MapServer/0"  # parcel points (the polygons are layer 1)
DATES_URL = f"{SERVICE}/NC1Map_Parcels_Transform_Dates/FeatureServer/0"
LANDING_URL = "https://www.nconemap.gov/pages/parcels"
LICENSE = "NC OneMap public data; county-sourced, provided as is with no warranty (no open license stated)"
CROSSWALK_DIR = CONFIG_DIR / "crosswalks"
COUNTIES_CSV = CROSSWALK_DIR / "nc_land_use_counties.csv"
SQFT_PER_ACRE = 43_560.0
OID_CHUNK = 100_000  # OBJECTIDs per query (mechanics: keeps paging offsets shallow; counties are contiguous)
RETRIES = 5  # pager retries on ArcGIS error bodies (mechanics)
RESIDENTIAL = {
    "SF_DETACHED",
    "SF_ATTACHED",
    "DUPLEX",
    "TRI_QUAD",
    "MULTIFAMILY_5P",
    "CONDO_UNIT",
    "MOBILE_HOME",
}

PERSONAL = {
    "ownname", "ownname2", "ownfrst", "ownlast", "owntype", "subowntype", "subsurfown",
    "mailadd", "munit", "mcity", "mstate", "mzip", "maddpref", "maddrno", "maddstname", "maddstr",
    "maddstsuf", "maddsttyp",
    "siteadd", "sunit", "scity", "saddno", "saddpref", "saddstname", "saddstr", "saddstsuf", "saddsttyp",
    "sstate", "szip",
    "legdecfull", "subdivisio", "sourceref", "mapref",
}  # fmt: skip
OUT_FIELDS = [
    "objectid",
    "parno",
    "cntyfips",
    "parusecode",
    "parusedesc",
    "parusecd2",
    "parusedsc2",
    "gisacres",
    "landval",
    "improvval",
    "structyear",
    "saledate",
    "transfdate",
]

PROVENANCE = {
    "title": "NC OneMap statewide parcels (NC1Map_Parcels; county tax data transformed by NC CGIA)",
    "landing_url": LANDING_URL,
    "table": TABLE,
    "cleaning": [
        "Requested fields exclude owner names and types, mailing and site addresses, legal descriptions, "
        "subdivision names and deed references (no personal data or free text)",
        "Downloaded one county at a time from the parcel-point layer (server-side filter cntyfips='<fips>', "
        "split into OBJECTID ranges); counties listed in config/crosswalks/nc_land_use_counties.csv",
        "parcel_id = county GEOID + parno; a parno repeated within a county keeps the lowest OBJECTID; "
        "parcels without a parno are dropped",
        "land_use_std from the county's crosswalk (config/crosswalks/nc_land_use_<county>.csv), reading the "
        "fields in the county's order; a residential land use (fallback field) with no building value → "
        "VACANT_RESIDENTIAL where the county flag says so; unmatched → UNKNOWN",
        "land_use_raw = '<field>=<code>' of the matched code (else the first field's raw value)",
        "year_built = structyear when 1700..vintage year; 0 and empty → unknown",
        "lot_sqft = gisacres × 43,560 (GIS polygon area); land_value/bldg_value = landval/improvval, "
        "value_basis 'assessed'; last_sale_date = saledate",
        "zoning_raw from the county's zoning field where it sends one (Durham: parusecode)",
        "vintage_date = the county's transform date from NC1Map_Parcels_Transform_Dates; vintage = its year",
        "jurisdiction_geoid = incorporated place by lotline.geo.place_or_township (TIGERweb ACS 2025), kept "
        "even when the place is not a BPS permit issuer; else the county remainder (5-digit GEOID)",
        "Holdout filter applied with snapshot=True: the 2026 roll drops every Charlotte (3712000) parcel",
    ],
    "limitations": [
        "Current roll only: no history; per-county transform dates differ (Mecklenburg 2026-01-07, Wake "
        "2026-05-17, Durham 2026-05-13 on 2026-10-19)",
        "Land-use codes are county-native and crosswalked county by county; some codes are ambiguous "
        "(Mecklenburg DUPLEX-TRIPLEX → DUPLEX; patio homes → SF_ATTACHED; Wake ONE FAMILY includes "
        "townhouses and condominium units, which only the county file's Design Style separates)",
        "No dwelling-unit counts or building area in the layer",
        "structyear completeness varies by county (see the PR / V0 report)",
        "Jurisdictions come from parcel points and 2025 boundaries; a place that is not a BPS permit issuer "
        "(Charlotte and the Mecklenburg towns, which BPS reports under the county) keeps its place GEOID",
        "Charlotte parcels are all held out (current roll, V5 holdout); a pre-2023-06-01 Mecklenburg roll "
        "is needed for the Charlotte denominator",
    ],
}


@dataclass(frozen=True)
class County:
    fips: str  # 5-digit
    name: str
    crosswalk: Path
    fields: tuple[str, ...]
    vacant_when_unimproved: bool
    zoning_field: str | None


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def counties(path: Path = COUNTIES_CSV) -> dict[str, County]:
    out = {}
    for r in _read_csv(path):
        flag = r["vacant_when_unimproved"].strip()
        if flag not in {"True", "False"}:
            raise ValueError(f"{path.name}: vacant_when_unimproved must be True/False, got {flag!r}")
        out[r["county_fips"]] = County(
            fips=r["county_fips"],
            name=r["county"],
            crosswalk=path.parent / r["crosswalk"],
            fields=tuple(f.strip() for f in r["land_use_fields"].split(";") if f.strip()),
            vacant_when_unimproved=flag == "True",
            zoning_field=r["zoning_field"].strip() or None,
        )
    return out


def crosswalk(path: Path) -> dict[tuple[str, str], str]:
    """(field, code) → land_use_std. Codes are matched after stripping spaces."""
    return {(r["field"], r["code"].strip()): r["land_use_std"] for r in _read_csv(path)}


def _clean(s: pd.Series) -> pd.Series:
    return s.astype("string").str.strip().fillna("")


def land_use(df: pd.DataFrame, county: County) -> tuple[pd.Series, pd.Series]:
    """(land_use_std, land_use_raw) for one county's rows."""
    xw = crosswalk(county.crosswalk)
    std = pd.Series(pd.NA, index=df.index, dtype="string")
    raw = pd.Series(pd.NA, index=df.index, dtype="string")
    from_fallback = pd.Series(False, index=df.index)
    for i, field in enumerate(county.fields):
        codes = _clean(df[field]) if field in df else pd.Series("", index=df.index)
        mapped = codes.map(lambda c, f=field: xw.get((f, c))).astype("string")
        take = std.isna() & mapped.notna()
        std = std.mask(take, mapped)
        raw = raw.mask(take, field + "=" + codes)
        from_fallback = from_fallback | (take & (i > 0))
    if county.vacant_when_unimproved:
        bldg = pd.to_numeric(df["improvval"], errors="coerce").fillna(0)
        vacant = from_fallback & std.isin(RESIDENTIAL).fillna(False) & (bldg <= 0)
        std = std.mask(vacant, "VACANT_RESIDENTIAL")
    first = _clean(df[county.fields[0]]).replace("", pd.NA)
    raw = raw.fillna(first)
    return std.fillna("UNKNOWN"), raw


def year_built(structyear: pd.Series, vintage: pd.Series) -> pd.Series:
    y = pd.to_numeric(structyear, errors="coerce")
    ok = (y >= 1700) & (y <= vintage.astype("float64"))
    return y.where(ok).round().astype("Int64")


def vintage_dates(dates: pd.DataFrame) -> dict[str, pd.Timestamp]:
    """5-digit county GEOID → transform date (normalized), from the Transform Dates layer attributes."""
    ts = epoch_ms_to_timestamp(dates["transfdate"]).dt.normalize()
    fips = "37" + dates["cntyfips"].astype("string").str.zfill(3)
    return dict(zip(fips, ts, strict=True))


def build(raw: pd.DataFrame, dates: dict[str, pd.Timestamp], state: str = "NC") -> pd.DataFrame:
    """Raw layer attributes (+ `lon`/`lat`) → `parcels` rows, before jurisdictions are assigned."""
    df = raw.copy()
    df["county_geoid"] = "37" + df["cntyfips"].astype("string").str.strip().str.zfill(3)
    df["local_id"] = _clean(df["parno"]).replace("", pd.NA)
    df = df.loc[df["local_id"].notna()].copy()
    cfg = counties()
    unknown = sorted(set(df["county_geoid"]) - set(cfg))
    if unknown:
        raise ValueError(f"onemap_parcels: counties without a crosswalk in {COUNTIES_CSV.name}: {unknown}")
    missing = sorted(set(df["county_geoid"]) - set(dates))
    if missing:
        raise ValueError(f"onemap_parcels: no transform date for {missing}")
    vintage_date = df["county_geoid"].map(dates).astype("datetime64[ns]")
    vintage = vintage_date.dt.year.astype("Int64")
    std = pd.Series("UNKNOWN", index=df.index, dtype="string")
    lu_raw = pd.Series(pd.NA, index=df.index, dtype="string")
    zoning = pd.Series(pd.NA, index=df.index, dtype="string")
    for fips, part in df.groupby("county_geoid"):
        county = cfg[fips]
        s, r = land_use(part, county)
        std.loc[part.index] = s
        lu_raw.loc[part.index] = r
        if county.zoning_field:
            zoning.loc[part.index] = _clean(part[county.zoning_field]).replace("", pd.NA)
    acres = pd.to_numeric(df["gisacres"], errors="coerce")
    nan = pd.Series(float("nan"), index=df.index)
    out = pd.DataFrame(
        {
            "state": state,
            "parcel_id": df["county_geoid"] + df["local_id"],
            "vintage": vintage,
            "vintage_date": vintage_date,
            "jurisdiction_geoid": pd.Series(pd.NA, index=df.index, dtype="string"),
            "county_geoid": df["county_geoid"],
            "lot_sqft": (acres * SQFT_PER_ACRE).where(acres > 0).astype("float64"),
            "land_use_std": std,
            "land_use_raw": lu_raw,
            "year_built": year_built(df["structyear"], vintage),
            "land_value": pd.to_numeric(df["landval"], errors="coerce").where(lambda v: v >= 0),
            "bldg_value": pd.to_numeric(df["improvval"], errors="coerce").where(lambda v: v >= 0),
            "value_basis": "assessed",
            "last_sale_date": epoch_ms_to_timestamp(df["saledate"]).astype("datetime64[ns]"),
            "zoning_raw": zoning,
            "zoning_source": zoning.notna().map({True: "county tax data (OneMap parusecode)", False: pd.NA}),
            "lon": pd.to_numeric(df.get("lon", nan), errors="coerce"),
            "lat": pd.to_numeric(df.get("lat", nan), errors="coerce"),
            "source": SOURCE,
            "_oid": pd.to_numeric(df["objectid"], errors="coerce"),
        },
        index=df.index,
    )
    out["zoning_source"] = out["zoning_source"].astype("string")
    out = out.sort_values(["parcel_id", "_oid"]).drop_duplicates(["state", "parcel_id", "vintage"])
    return out.drop(columns="_oid").reset_index(drop=True)


def resolve_jurisdictions(
    county_geoid: pd.Series, place: pd.Series, known: set[str]
) -> tuple[pd.Series, pd.Series]:
    """(jurisdiction_geoid, how): the place if any ('place' / 'place_not_in_bps'), else the county row."""
    place = place.astype("string")
    has = place.notna()
    geoid = place.where(has, county_geoid.astype("string"))
    how = pd.Series("county_remainder", index=place.index, dtype="string")
    how = how.mask(has, "place_not_in_bps").mask(has & place.isin(known).fillna(False), "place")
    return geoid, how


def assign_jurisdictions(df: pd.DataFrame, state: str, store: DataStore) -> tuple[pd.DataFrame, pd.Series]:
    from lotline import geo
    from lotline.build import jurisdictions as jur

    juris = store.read(state, "jurisdictions")
    if juris is None:
        juris = jur.load(state, store)
    place = geo.place_or_township(df["lon"], df["lat"], state, store)
    geoid, how = resolve_jurisdictions(df["county_geoid"], place, set(juris["geoid"]))
    return df.assign(jurisdiction_geoid=geoid), how


def _oid_ranges(store: DataStore, fips3: list[str], *, refresh: bool) -> dict[str, tuple[int, int]]:
    """cntyfips → (min, max) OBJECTID, from one statistics query downloaded through `fetch()`."""
    import json

    from lotline.io.arcgis import query_url
    from lotline.io.http import fetch

    stats = json.dumps(
        [
            {"statisticType": "min", "onStatisticField": "objectid", "outStatisticFieldName": "lo"},
            {"statisticType": "max", "onStatisticField": "objectid", "outStatisticFieldName": "hi"},
        ]
    )
    where = "cntyfips IN (" + ",".join(f"'{c}'" for c in sorted(fips3)) + ")"
    url = query_url(
        LAYER_URL, where=where, outStatistics=stats, groupByFieldsForStatistics="cntyfips", f="json"
    )
    name = "oid_ranges_" + "_".join(sorted(fips3)) + ".json"
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
    feats = json.loads(path.read_text())["features"]
    return {
        f["attributes"]["cntyfips"]: (int(f["attributes"]["lo"]), int(f["attributes"]["hi"])) for f in feats
    }


def chunks(lo: int, hi: int, size: int = OID_CHUNK) -> list[tuple[int, int]]:
    """Half-open OBJECTID ranges [a, b) covering lo..hi."""
    return [(a, min(a + size, hi + 1)) for a in range(lo, hi + 1, size)]


def download_dates(store: DataStore, *, refresh: bool = False) -> pd.DataFrame:
    return download_layer(
        DATES_URL,
        store=store,
        source=SOURCE,
        license=LICENSE,
        adapter=ADAPTER,
        adapter_version=VERSION,
        name="transform_dates",
        out_fields="cntyname,cntyfips,transfdate",
        refresh=refresh,
    )


def download(store: DataStore, *, fips: list[str] | None = None, refresh: bool = False) -> pd.DataFrame:
    fips3 = [f[2:] for f in (fips or sorted(counties()))]
    ranges = _oid_ranges(store, fips3, refresh=refresh)
    frames = []
    for c in fips3:
        lo, hi = ranges[c]
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
                    where=f"cntyfips='{c}' AND objectid>={a} AND objectid<{b}",
                    out_fields=",".join(OUT_FIELDS),
                    geometry=True,
                    retries=RETRIES,
                    refresh=refresh,
                )
            )
    frames = [f for f in frames if len(f)]
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=OUT_FIELDS)


def load(state: str, store: DataStore, *, refresh: bool = False) -> pd.DataFrame:
    dates = vintage_dates(download_dates(store, refresh=refresh))
    df = build(download(store, refresh=refresh), dates, state=state)
    df, _ = assign_jurisdictions(df, state, store)
    df = holdout.apply(
        df,
        state,
        geoid_col="jurisdiction_geoid",
        date_col="vintage_date",
        year_col="vintage",
        snapshot=True,
    )
    return validate(df, TABLE)
