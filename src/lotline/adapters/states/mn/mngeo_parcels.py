"""MnGeo "Parcels, Compiled from Opt-In Open Data Counties" (Greater Minnesota) → `parcels`, one current roll.

**What it is.** MnGeo compiles the parcel layers of the counties that opt in to open data (59 of 87 on
2026-11-01, the 7 metro counties among them) into one layer with the state's GAC parcel schema, the same
schema as the Met Council regional parcels. One roll, refreshed as counties re-send; each county's date is in
the companion metadata layer (`acqdate`). The item's license field reads "None" (provided as is): recorded in
the provenance and in `docs/disclosures.md`.

**Which counties.** The metro counties stay on `metc_parcels` (yearly rolls) and `mpls_assessor_parcels`, so
only outstate counties are read, and only those marked `loaded` in `config/crosswalks/mn_mngeo_counties.csv`
(31 of 52). That file records, for each outstate county, its share of parcels with a known land use and its
single-family parcels against ACS one-unit detached homes. Counties are left out when:

- `no_land_use`: the county sends no use class (18 counties), so every parcel would be UNKNOWN;
- `acs_check`: single-family parcels fall outside 0.6-1.4 times ACS one-unit detached homes, the band NC
  uses for drafted crosswalks (Aitkin, Cass, Cook: lake counties where ACS counts seasonal cabins as homes).

Places in loaded counties still pass the D-017 gate one by one (`build.eligible.usable_rolls`).

**Land use.** `useclass1` → `land_use_std` by `config/crosswalks/mn_land_use_mngeo.csv` (outstate labels:
property classes such as 1a, 4bb, 4b4 and 4c12, and the three-digit code scheme that Pipestone and Renville
label), then the metro rules of `mn_land_use.csv` (first match wins). Bare codes that no county labels stay
UNKNOWN. Dwelling type and unit count refine a residential class as in `metc_parcels`.

**Rows.** Built by `metc_parcels.to_parcels` (same schema), so parcel IDs, jurisdictions (point, then
`ctu_name`, then the county remainder), units, year built, values and sales follow the same rules.
`vintage_date` is the county's latest `exp_date`, or its `acqdate` where the county sends none.

**Personal data.** The layer carries owner and taxpayer names and addresses and situs addresses. They are
never requested: `FIELDS` lists exactly what is read.
"""

from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path

import pandas as pd

from lotline.adapters.states.mn import metc_parcels as metc
from lotline.config import CONFIG_DIR
from lotline.io import DataStore
from lotline.schemas import validate

ADAPTER = "states.mn.mngeo_parcels"
VERSION = "1.0"
SOURCE = "mngeo_parcels"
TABLE = "parcels"
LICENSE = "MnGeo compilation of opt-in county open data; item license 'None' (provided as is)"
SERVICE = (
    "https://enterprise.gisdata.mn.gov/aghost/rest/services/us_mn_state_mngeo/plan_parcels_open/FeatureServer"
)
PARCEL_LAYER = f"{SERVICE}/1"
LANDING_URL = "https://www.arcgis.com/home/item.html?id=69148d3959194a05a23964cc60f6517b"
COUNTIES_CSV = CONFIG_DIR / "crosswalks" / "mn_mngeo_counties.csv"
USE_CROSSWALK = CONFIG_DIR / "crosswalks" / "mn_land_use_mngeo.csv"
# Cache key for the raw download: the item's last-modified date. Set MN_MNGEO_VINTAGE to read a later pull.
RAW_VINTAGE = os.environ.get("MN_MNGEO_VINTAGE", "2026-09-17")
RETRIES = 5  # pager retries on ArcGIS error bodies (mechanics only)

# Exactly what is read (lower case in this layer). Never "*": owner_name, owner_more, own_add_l1-4,
# tax_name, tax_add_l1-4 and the situs address fields (anumber ... zip4) identify people or homes.
FIELDS = [
    "objectid",
    "county_pin",
    "co_code",
    "co_name",
    "ctu_name",
    "homestead",
    "acres_poly",
    "acres_deed",
    "emv_land",
    "emv_bldg",
    "useclass1",
    "dwell_type",
    "fin_sq_ft",
    "year_built",
    "num_units",
    "sale_date",
    "sale_value",
    "exp_date",
]
PERSONAL = {
    "owner_name",
    "owner_more",
    "own_add_l1",
    "own_add_l2",
    "own_add_l3",
    "own_add_l4",
    "tax_name",
    "tax_add_l1",
    "tax_add_l2",
    "tax_add_l3",
    "tax_add_l4",
    "anumber",
    "st_name",
    "zip",
}

PROVENANCE = {
    "title": "MnGeo Parcels, Compiled from Opt-In Open Data Counties (Greater Minnesota, current roll)",
    "landing_url": LANDING_URL,
    "table": TABLE,
    "attribution": "Minnesota Geospatial Information Office (MnGeo); parcel data from the opt-in counties",
    "cleaning": [
        f"Parcel layer {PARCEL_LAYER}, downloaded one county at a time (label points, WGS84), requesting "
        "only " + ", ".join(FIELDS) + ". Owner, taxpayer and situs address fields are never requested",
        "Only outstate counties marked 'loaded' in config/crosswalks/mn_mngeo_counties.csv are read (31 "
        "of 52 on 2026-11-01); metro counties stay on metc_parcels and mpls_assessor_parcels",
        "land_use_std: useclass1 by config/crosswalks/mn_land_use_mngeo.csv, then config/crosswalks/"
        "mn_land_use.csv (first match wins); bare codes no county labels stay UNKNOWN",
        "Rows built by metc_parcels.to_parcels (same GAC schema): parcel_id, jurisdictions, units, year "
        "built, values and sales as documented for metc_parcels",
        "vintage_date = the county's latest exp_date, else its acqdate in the metadata layer; vintage = the "
        "year of the newest vintage_date",
        "Parcels in no MN jurisdiction are left out: points outside every place and permit-issuing township "
        "in a county with no remainder row (Otter Tail 31,257 and Clearwater 7,070 parcels on 2026-11-01)",
        "Parcels of a jurisdiction whose main county (jurisdictions.county_geoid) is not a loaded county are "
        "left out: a place split with an unloaded county keeps the ACS fallback, not a slice of its parcels",
    ],
    "limitations": [
        "One current roll: no history (D-035 scales ACS to it)",
        "18 opt-in counties send no use class, and 28 counties have not opted in: they stay on the ACS "
        "fallback",
        "Aitkin, Cass and Cook are left out: single-family parcels are under 0.6 times ACS one-unit homes, "
        "because seasonal cabins (class 4c12) are not read as houses",
        "Year built and unit counts are blank in most counties, so most places are tier 2 at best",
        "Five counties send bare three-digit codes; only the codes Pipestone and Renville label are read",
        "Class 4b(1) '1-3 units' is read as DUPLEX unless units say otherwise, as in the metro rules",
        "Seasonal cabins (class 4c12) and farm homesteads (class 2a) are not read as houses, as in the metro "
        "rules, while ACS counts both as one-unit homes: lake and farm townships count fewer eligible lots "
        "than ACS (21 of 362 newly parcel-counted jurisdictions under half their ACS count on 2026-11-02)",
    ],
}


def counties(path: Path = COUNTIES_CSV, status: str | None = "loaded") -> pd.DataFrame:
    """The outstate county table (all rows, or those with `status`)."""
    df = pd.read_csv(path, dtype={"county_fips": str})
    return df if status is None else df.loc[df["status"] == status].reset_index(drop=True)


def use_rules() -> list[metc.Rule]:
    """Outstate rules first, then the metro rules (their county-specific rows never match outstate names)."""
    return metc.load_rules(USE_CROSSWALK) + metc.load_rules(metc.USE_CROSSWALK)


def _ms(day: str) -> float:
    """An ISO date as epoch milliseconds (the layer's date format)."""
    return dt.datetime.fromisoformat(day).replace(tzinfo=dt.UTC).timestamp() * 1000


def to_metc_schema(raw: pd.DataFrame, acquired: dict[str, str]) -> pd.DataFrame:
    """Lower-case MnGeo columns → the upper-case names `metc_parcels.to_parcels` reads.

    `acquired`: county GEOID (27xxx) → acquisition date (ISO), used where `exp_date` is blank.
    """
    df = raw.drop(columns=[c for c in raw.columns if c in PERSONAL]).copy()
    df.columns = [c if c in ("lon", "lat") else c.upper() for c in df.columns]
    county = metc._county_geoid(df["CO_CODE"])
    fallback = county.map({k: _ms(v) for k, v in acquired.items() if isinstance(v, str) and v})
    df["EXP_DATE"] = pd.to_numeric(df["EXP_DATE"], errors="coerce").fillna(fallback)
    return df


def build(
    raw: pd.DataFrame,
    jurisdictions: pd.DataFrame,
    locate: metc.Locator,
    acquired: dict[str, str],
    state: str = "MN",
) -> pd.DataFrame:
    """Downloaded rows (+ lon/lat) → validated `parcels`, through the Met Council builder."""
    df = to_metc_schema(raw, acquired)
    table, _ = metc.to_parcels(
        df,
        "current",
        jurisdictions,
        locate,
        state,
        source=SOURCE,
        ctu_counties=tuple(sorted(acquired)),
        use_rules=use_rules(),
    )
    # A point in no jurisdiction falls back to its county's remainder row, which some outstate counties lack
    # (their townships don't issue permits as BPS reporters): such parcels belong to no jurisdiction. A
    # jurisdiction whose main county is not loaded would count only the slice in a loaded neighbour (Pine
    # Island, mostly in Goodhue, from its Olmsted part), so it keeps the ACS fallback instead.
    j = jurisdictions.assign(geoid=jurisdictions["geoid"].astype(str))
    whole = set(j.loc[j["county_geoid"].astype(str).isin(acquired), "geoid"])
    return table[table["jurisdiction_geoid"].isin(whole)].reset_index(drop=True)


def download(store: DataStore, fips: list[str], *, refresh: bool = False) -> pd.DataFrame:
    """One cached query per county (shallow paging offsets; each county resumable on its own)."""
    from lotline.io.arcgis import download_layer

    frames = [
        download_layer(
            PARCEL_LAYER,
            store=store,
            source=SOURCE,
            license=LICENSE,
            adapter=ADAPTER,
            adapter_version=VERSION,
            name=f"county_{f}",
            where=f"co_code='{f}'",
            out_fields=",".join(FIELDS),
            geometry="centroid",
            vintage=RAW_VINTAGE,
            retries=RETRIES,
            refresh=refresh,
        )
        for f in fips
    ]
    frames = [f for f in frames if len(f)]
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=FIELDS)


def load(state: str, store: DataStore, *, refresh: bool = False) -> pd.DataFrame:
    if state.upper() != "MN":
        raise ValueError(f"{SOURCE} covers Minnesota only, not {state}")
    from lotline import geo

    table = counties()
    acquired = dict(zip(table["county_fips"], table["acquired"], strict=True))
    juris = metc._jurisdictions(state, store)

    def locate(lon: pd.Series, lat: pd.Series) -> pd.Series:
        return geo.place_or_township(lon, lat, state, store)

    raw = download(store, list(table["county_fips"]), refresh=refresh)
    return validate(build(raw, juris, locate, acquired, state), TABLE)


def code_inventory(store: DataStore, fips: list[str], *, refresh: bool = False) -> pd.DataFrame:
    """Parcels per (county, use class) from statistics queries through `fetch()`: no parcel is downloaded.

    The inventory behind `mn_mngeo_counties.csv` and the outstate crosswalk (2026-11-01). Columns:
    county_fips, useclass1, parcels, land_use_std (by `use_rules`).
    """
    from lotline.io.arcgis import query_url
    from lotline.io.http import fetch

    stats = json.dumps(
        [{"statisticType": "count", "onStatisticField": "objectid", "outStatisticFieldName": "n"}]
    )
    rows = []
    for f in fips:
        url = query_url(
            PARCEL_LAYER,
            where=f"co_code='{f}'",
            groupByFieldsForStatistics="useclass1",
            outStatistics=stats,
            f="json",
        )
        path = fetch(
            url,
            store.raw(SOURCE, RAW_VINTAGE) / "inventory" / f"useclass1_{f}.json",
            store=store,
            source=SOURCE,
            license=LICENSE,
            adapter=ADAPTER,
            adapter_version=VERSION,
            refresh=refresh,
        )
        for feat in json.loads(path.read_text())["features"]:
            a = feat["attributes"]
            rows.append({"county_fips": f, "useclass1": a["useclass1"], "parcels": int(a["n"])})
    df = pd.DataFrame(rows, columns=["county_fips", "useclass1", "parcels"])
    names = counties(status=None).set_index("county_fips")["county"]
    blank = pd.Series(pd.NA, index=df.index, dtype="string")
    df["land_use_std"] = metc.land_use(
        df["county_fips"].map(names), df["useclass1"], blank, blank, use_rules()
    )
    return df
