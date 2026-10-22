"""Mecklenburg County building permits ("Building Permit Locations") → canonical `permits`, holdout-first.

Charlotte-Mecklenburg Code Enforcement (LUESA) issues building permits for Charlotte, the six other
Mecklenburg towns and the unincorporated county. The county's layer has one point per permit since 1990
with the Census (USDC) item code, building type, unit count, zoning and tax jurisdiction.

**Holdout first (V5, D-012).** Charlotte (3712000) is the V5 blind test from 2023-06-01, and BPS files
Charlotte's permits under Mecklenburg County (37119), so both GEOIDs are held out from that date. The
adapter keeps held-out rows from ever being downloaded where it can, and drops the rest before anything
else touches them:

1. **Server-side filter.** The query asks only for permits issued before the window opens, or issued
   later in a town that is not held out (`taxjuris` in the town list of
   `config/crosswalks/nc_meck_tax_jurisdictions.csv`). The window date and the held-out GEOIDs are read
   from the holdout config, never typed here. If a town's spelling is wrong, its later permits are simply
   not downloaded (lost, never leaked); `check_town_rows` then stops the run, so the gap can't go unseen.
2. **`holdout.apply` right after the rows are built**, on the place found from each permit's point
   (a permit filed under a town but standing in Charlotte or the unincorporated county is dropped). Only
   the filtered table is returned or written; the adapter never prints or counts held-out rows.

**Jurisdiction.** The permit's point (WGS84) → incorporated place (`lotline.geo.place_or_township`),
kept even though BPS has no row for these places (#123); no point → the `taxjuris` crosswalk; else 37119.

**Building type and units** (`config/crosswalks/nc_meck_usdc_codes.csv`, the Census item codes):

- the code is the first three digits of `usdcdesc` (101 single-family, 103 two-family, 104 three- and
  four-family, 105 five or more, 434 residential alterations, 645-649 demolitions, others nonresidential);
- new housing (101-105): `numunits` when it fits the type (101: 1; 103: 1-2; 104: 3-4; 105: 5+) →
  `reported`; else a count read from the description (`lotline.parse.permit_text`) that fits → `inferred`;
  else 1 for a single-family code → `derived`; else unknown (null, never 0);
- 101 covers attached houses too, so it is `SFD` with `type_confidence="inferred"` unless the description
  names a townhouse (`TH`) or an accessory dwelling (`ADU`);
- an ADU named in the description of a 101, 434 or 438 permit (or one with no code) → `ADU`, 1 unit,
  `inferred`;
- demolitions: `units_new` 0 and `units_removed` from `numunits` when it fits, else the code's count;
- residential alterations (434): units from the description where it states them, else unknown;
- nonresidential codes: 0 units (`derived`).

**Other fields.** `zoning_raw` = `zonecode` (N1 districts after 2023-06-01: the V5 outcome);
`parcel_id` = "37119" + `parcelnum`; `valuation_usd` = `bldgcost`; `floor_area_sqft` = `heatsqft`;
`final_date` = `compldate` (completion). Only these fields are requested (`OUT_FIELDS`): no owner name,
owner city/state/ZIP, project name, project description or address. The two work descriptions
(`permitdesc`, `workdesc`) are requested only for the parser; they are read in memory and never kept.

**Registered file (2026-10-21).** Ben downloaded the same layer by hand from the county's Open Data Viewer
(https://maps.mecklenburgcountync.gov/opendata-viewer, dataset "Building Permits - Winchester", described
as legacy permits; newer permits are in a separate Accela file) as `Winchester_BuildingPermits.zip`, a
GeoPackage with the same field names. When that file is registered (`lotline manifest register --source
meck_permits`), `load` reads it instead of the server, with the same holdout-first rule: the SQL query
(`file_where`) never reads Charlotte or unincorporated permits from the window, and only `FILE_COLUMNS`
are selected (no owner name, phone, e-mail or address). Points come as NC State Plane feet
(`x_coord`/`y_coord`) and are converted with `stateplane.to_lonlat`.

**Access (2026-10-20).** The layer's server (meckgis.mecklenburgcountync.gov) answers this network with a
Cloudflare browser challenge (HTTP 403). The adapter does not try to get past it; until the county serves
the query API to scripts again, a run stops at the download with that error.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd

from lotline.config import CONFIG_DIR
from lotline.io import DataStore
from lotline.io.arcgis import epoch_ms_to_timestamp
from lotline.parse.permit_text import parse_description
from lotline.schemas import validate
from lotline.validation import holdout

ADAPTER = "states.nc.meck_permits"
VERSION = "1.0"
SOURCE = "meck_permits"
TABLE = "permits"
LAYER_URL = "https://meckgis.mecklenburgcountync.gov/server/rest/services/BuildingPermits/FeatureServer/0"
LANDING_URL = "https://www.arcgis.com/home/item.html?id=fc9d171ecd4d44a58c7dad840cd58aa2"
LICENSE = "Mecklenburg County GIS public data (accuracy disclaimer; no license stated)"
COUNTY = "37119"
CHARLOTTE = "3712000"
USDC_CSV = CONFIG_DIR / "crosswalks" / "nc_meck_usdc_codes.csv"
JURIS_CSV = CONFIG_DIR / "crosswalks" / "nc_meck_tax_jurisdictions.csv"

OUT_FIELDS = [
    "objectid",
    "permitnum",
    "permitstat",
    "permittype",
    "parcelnum",
    "taxjuris",
    "zonecode",
    "typeofbldg",
    "numunits",
    "usdcdesc",
    "issuedate",
    "compldate",
    "bldgcost",
    "worktype",
    "heatsqft",
    "permitdesc",  # parser input only, never kept
    "workdesc",  # parser input only, never kept
]
PERSONAL = {"ownname", "owncity", "ownstate", "ownzipcode", "projname", "projadd", "projdesc", "projnum"}
TEXT_FIELDS = ("permitdesc", "workdesc")
FITS = {"SFD": (1, 1), "TH": (1, None), "ADU": (1, 1), "U2": (1, 2), "U3_4": (3, 4), "MF5": (5, None)}

PROVENANCE = {
    "title": "Mecklenburg County Building Permit Locations (Code Enforcement, since 1990)",
    "landing_url": LANDING_URL,
    "table": TABLE,
    "cleaning": [
        "Read from Ben's hand download of the county's 'Building Permits - Winchester' GeoPackage (Open "
        "Data Viewer, data dated 2026-10-12, registered 2026-10-21; downloaded from Europe through a US VPN "
        "because the county's GIS servers did not answer there); the server query is used only when no "
        "file is registered",
        "Holdout-first filter in the query itself (file_where in SQLite; server_where on the live layer): "
        "only permits issued before the Charlotte window (2023-06-01, from the holdout config), or later in "
        "a non-held-out town by taxjuris; held-out rows are never read",
        "holdout.apply on the point-based place right after the rows are built (D-012: 3712000 and 37119)",
        "Requested fields exclude owner name, phone, e-mail, address, city, state and ZIP, project name, "
        "number, description and address; permitdesc/workdesc are read only by the description parser and "
        "never kept",
        "File points (x_coord/y_coord, NC State Plane feet, EPSG:2264) converted to lon/lat by "
        "stateplane.to_lonlat (checked: median 7 m from the pre-UDO parcel centroids of the same parcels)",
        "jurisdiction_geoid = place of the permit point (TIGERweb ACS 2025), else taxjuris, else 37119",
        "building_type_std and units from the Census item code in usdcdesc "
        "(config/crosswalks/nc_meck_usdc_codes.csv, including the county's own 102 townhouse, 112 mobile "
        "home, 114 and 115 condominium codes); numunits when it fits the type; description parser "
        "for gaps (inferred); single-family code → 1 unit (derived)",
        "zoning_raw = zonecode; parcel_id = 37119 + parcelnum; valuation_usd = bldgcost; final_date = "
        "compldate (completion); floor_area_sqft = heatsqft",
    ],
    "limitations": [
        "A 'legacy' file: the county moved residential applications to Accela in 2025 and publishes those "
        "permits in a separate Accela file, not loaded; the towns' legacy permits still run to 2026-10",
        "Countywide new one-unit homes are 0.88-1.02 of BPS 37119 in 2012-2022 (1.2-1.3 in 2010-2011); "
        "apartments vary 0.5-1.6 by year (permit timing)",
        "Code 101 is SFD unless the description names a townhouse; the county codes townhouses 102",
        "Permits filed under Charlotte but standing in a town after 2023-06-01 are not downloaded",
    ],
}


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def usdc_codes(path: Path = USDC_CSV) -> dict[str, dict[str, str]]:
    return {r["usdc_code"]: r for r in _read_csv(path)}


def tax_jurisdictions(path: Path = JURIS_CSV) -> dict[str, str]:
    return {r["taxjuris"].strip().upper(): r["geoid"] for r in _read_csv(path)}


def held_out_geoids(state: str = "NC") -> set[str]:
    return {g for h in holdout.holdouts_for(state) for g in h.geoids}


def window_opens(state: str = "NC") -> pd.Timestamp:
    """The earliest outcome date of any holdout covering Charlotte or the county."""
    hs = [h for h in holdout.holdouts_for(state) if set(h.geoids) & {CHARLOTTE, COUNTY}]
    return min(pd.Timestamp(h.outcome_from) for h in hs)


def open_towns(state: str = "NC") -> list[str]:
    """taxjuris names whose place is not held out (their later permits may be downloaded)."""
    out = held_out_geoids(state)
    return sorted(n for n, g in tax_jurisdictions().items() if g not in out)


def server_where(state: str = "NC") -> str:
    """Query filter that leaves out held-out rows: before the window, or a non-held-out town after it."""
    opens = window_opens(state).date().isoformat()
    towns = ",".join("'" + t.replace("'", "''") + "'" for t in open_towns(state))
    return f"issuedate < DATE '{opens}' OR (issuedate >= DATE '{opens}' AND UPPER(taxjuris) IN ({towns}))"


def usdc_code(desc: pd.Series) -> pd.Series:
    return desc.astype("string").str.extract(r"^\s*(\d{3})", expand=False)


def _fits(t: str | None, n: object) -> bool:
    if t not in FITS or n is None or pd.isna(n):
        return False
    lo, hi = FITS[t]
    return n >= lo and (hi is None or n <= hi)


def _text(row: pd.Series) -> str:
    return " ; ".join(
        str(row[f]) for f in TEXT_FIELDS if f in row and pd.notna(row[f]) and str(row[f]).strip()
    )


def classify(row: pd.Series, codes: dict[str, dict[str, str]]) -> dict:
    """building_type_std, type_confidence, adu_type, units_new, units_removed, units_confidence, flags."""
    code = row["usdc"]
    info = codes.get(code) if isinstance(code, str) else None
    activity = info["activity"] if info else None
    btype = info["building_type_std"] if info else "UNKNOWN"
    conf = "high" if info else "unknown"
    n = pd.to_numeric(row.get("numunits"), errors="coerce")
    facts = parse_description(_text(row))
    out = dict(adu_type=None, units_new=None, units_removed=None, units_confidence="unknown",
               is_demolition=activity == "demolition" if activity else None,
               is_conversion=facts.is_conversion)  # fmt: skip
    adu_ok = not isinstance(code, str) or code in ("101", "434", "438")  # no code (None or NA) is fine
    if facts.building_type_std == "ADU" and adu_ok and not facts.is_demolition:
        out.update(adu_type=facts.adu_type or "unknown", units_new=1, units_confidence="inferred")
        return dict(out, building_type_std="ADU", type_confidence="inferred")
    if activity == "new":
        if code == "101":
            btype, conf = ("TH", "inferred") if facts.building_type_std == "TH" else ("SFD", "inferred")
        if _fits(btype, n):
            out.update(units_new=int(n), units_confidence="reported")
        elif _fits(btype, facts.units_new):
            out.update(units_new=facts.units_new, units_confidence="inferred")
        elif info["derived_units"]:
            out.update(units_new=int(info["derived_units"]), units_confidence="derived")
        out["units_removed"] = 0
    elif activity == "demolition":
        out.update(units_new=0, units_confidence="derived")
        if _fits(btype, n):
            out["units_removed"] = int(n)
        elif info["derived_units"]:
            out["units_removed"] = int(info["derived_units"])
    elif activity == "alteration" and code == "434":
        if facts.units_new is not None:
            out.update(
                units_new=facts.units_new, units_removed=facts.units_removed, units_confidence="inferred"
            )
    elif activity in ("nonresidential", "alteration"):
        out.update(units_new=0, units_removed=0, units_confidence="derived")
    return dict(out, building_type_std=btype, type_confidence=conf)


def build(raw: pd.DataFrame, place: pd.Series, state: str = "NC") -> pd.DataFrame:
    """Raw layer attributes + each row's place (point-based, may be NA) → `permits` rows (before holdout)."""
    df = raw.copy()
    df["issue_date"] = epoch_ms_to_timestamp(df["issuedate"]).dt.normalize()
    df = df.loc[df["issue_date"].notna()].copy()
    df["usdc"] = usdc_code(df["usdcdesc"])
    codes = usdc_codes()
    facts = pd.DataFrame([classify(r, codes) for _, r in df.iterrows()], index=df.index)
    juris = df["taxjuris"].astype("string").str.strip().str.upper().map(tax_jurisdictions())
    geoid = place.reindex(df.index).astype("string").fillna(juris).fillna(COUNTY)
    parcel = df["parcelnum"].astype("string").str.strip().replace("", pd.NA)
    raw_class = (
        df["usdcdesc"].astype("string").str.strip() + " | " + df["typeofbldg"].astype("string").fillna("")
    )
    out = pd.DataFrame(
        {
            "state": state,
            "permit_id": df["permitnum"].astype("string").str.strip(),
            "parcel_id": (COUNTY + parcel).astype("string"),
            "jurisdiction_geoid": geoid,
            "issue_year": df["issue_date"].dt.year.astype("Int64"),
            "issue_date": df["issue_date"],
            "date_precision": "day",
            "final_date": epoch_ms_to_timestamp(df["compldate"]).dt.normalize(),
            "permit_class_raw": raw_class,
            "zoning_raw": df["zonecode"].astype("string").str.strip().replace("", pd.NA),
            "valuation_usd": pd.to_numeric(df["bldgcost"], errors="coerce").where(lambda v: v >= 0),
            "floor_area_sqft": pd.to_numeric(df["heatsqft"], errors="coerce").where(lambda v: v > 0),
            "source": SOURCE,
        }
    )
    out["final_date_type"] = (
        out["final_date"].notna().map({True: "completion", False: pd.NA}).astype("string")
    )
    for col in ["building_type_std", "type_confidence", "adu_type", "units_confidence"]:
        out[col] = facts[col].astype("string")
    for col in ["units_new", "units_removed"]:
        out[col] = pd.array(facts[col], dtype="Int64")
    for col in ["is_demolition", "is_conversion"]:
        out[col] = pd.array(facts[col], dtype="boolean")
    out = out.loc[out["permit_id"].notna() & (out["permit_id"] != "")]
    return out.drop_duplicates(["state", "permit_id"], keep="last").reset_index(drop=True)


def check_town_rows(df: pd.DataFrame, state: str = "NC") -> None:
    """Stop when no non-held-out town has a permit from the window on: the town spellings are wrong."""
    opens = window_opens(state)
    towns = set(tax_jurisdictions().values()) - held_out_geoids(state)
    later = df.loc[df["issue_date"] >= opens, "jurisdiction_geoid"]
    if not later.isin(towns).any():
        raise ValueError(
            f"{SOURCE}: no town permits from {opens.date()} on: "
            f"check the taxjuris spellings in {JURIS_CSV.name}"
        )


def download(store: DataStore, state: str = "NC", *, refresh: bool = False) -> pd.DataFrame:
    from lotline.io.arcgis import download_layer

    return download_layer(
        LAYER_URL,
        store=store,
        source=SOURCE,
        license=LICENSE,
        adapter=ADAPTER,
        adapter_version=VERSION,
        name="permits",
        where=server_where(state),
        out_fields=",".join(OUT_FIELDS),
        geometry=True,
        refresh=refresh,
    )


FILE_NAME = "Winchester_BuildingPermits.zip"
GPKG_TABLE = "BuildingPermits_Winchester"
# File column → the layer's field name used by `build` (the file renames two of them).
FILE_COLUMNS = {
    "OBJECTID": "objectid",
    "permitnum": "permitnum",
    "permitstat": "permitstat",
    "permittype": "permittype",
    "parcelnum": "parcelnum",
    "taxjuris": "taxjuris",
    "zonecode": "zonecode",
    "typeofbldg": "typeofbldg",
    "num_units": "numunits",
    "usdcdesc": "usdcdesc",
    "issuedate": "issuedate",
    "compldate": "compldate",
    "bldgcost": "bldgcost",
    "worktype": "worktype",
    "heat_sqft": "heatsqft",
    "permitdesc": "permitdesc",  # parser input only, never kept
    "workdesc": "workdesc",  # parser input only, never kept
    "x_coord": "x_coord",
    "y_coord": "y_coord",
}
FILE_PERSONAL = {"ownname", "ownphone", "ownaddr", "owncity", "ownstate", "ownemail", "owner_zip", "projname",
                 "projnum", "projdesc", "projadd", "subdiv", "addressid", "cntystcode"}  # fmt: skip


def file_where(state: str = "NC") -> str:
    """SQLite version of `server_where`: issue dates are ISO text ('2023-05-31T12:00:00.0Z')."""
    opens = window_opens(state).date().isoformat()
    towns = ",".join("'" + t.replace("'", "''") + "'" for t in open_towns(state))
    return f"issuedate < '{opens}' OR (issuedate >= '{opens}' AND UPPER(TRIM(taxjuris)) IN ({towns}))"


def _iso_to_ms(values: pd.Series) -> pd.Series:
    ts = pd.to_datetime(values, utc=True, errors="coerce", format="ISO8601")
    ms = (ts - pd.Timestamp("1970-01-01", tz="UTC")) // pd.Timedelta(milliseconds=1)
    return ms.astype("Int64")


def read_file(path: Path, state: str = "NC") -> pd.DataFrame:
    """The registered GeoPackage zip → raw rows shaped like the layer's (dates in epoch ms, plus lon/lat).

    Held-out rows are filtered out by the query itself (`file_where`), before anything is read.
    """
    import sqlite3
    import zipfile

    from lotline.adapters.states.nc import stateplane

    extracted = path.parent / "extracted"
    with zipfile.ZipFile(path) as z:
        name = next(n for n in z.namelist() if n.endswith(".gpkg"))
        gpkg = extracted / name
        if not gpkg.exists():
            z.extract(name, extracted)
    cols = ", ".join(f'"{c}"' for c in FILE_COLUMNS)
    with sqlite3.connect(f"file:{gpkg}?mode=ro", uri=True) as con:
        raw = pd.read_sql(f'SELECT {cols} FROM "{GPKG_TABLE}" WHERE {file_where(state)}', con)
    raw = raw.rename(columns=FILE_COLUMNS)
    for col in ("issuedate", "compldate"):
        raw[col] = _iso_to_ms(raw[col])
    raw["lon"], raw["lat"] = stateplane.to_lonlat(raw.pop("x_coord"), raw.pop("y_coord"))
    return raw


def file_entries(store: DataStore) -> list:
    """Registered copies of the hand-downloaded GeoPackage (latest last)."""
    return [e for e in store.registered(SOURCE) if Path(e.path).name == FILE_NAME]


def places(raw: pd.DataFrame, state: str, store: DataStore) -> pd.Series:
    from lotline import geo

    if not {"lon", "lat"} <= set(raw.columns):
        return pd.Series(pd.NA, index=raw.index, dtype="string")
    return geo.place_or_township(raw["lon"], raw["lat"], state, store).astype("string")


def load(state: str, store: DataStore, *, refresh: bool = False) -> pd.DataFrame:
    if state.upper() != "NC":
        raise ValueError(f"{SOURCE} covers Mecklenburg County, North Carolina only, not {state}")
    entries = file_entries(store)
    if entries:
        entry = entries[-1]
        if store.is_stale(entry):
            raise FileNotFoundError(f"registered Mecklenburg permits file missing or changed: {entry.path}")
        raw = read_file(store.root / entry.path, state)
    else:
        raw = download(store, state, refresh=refresh)
    df = build(raw, places(raw, state, store), state=state)
    df = holdout.apply(
        df, state, geoid_col="jurisdiction_geoid", date_col="issue_date", year_col="issue_year"
    )
    check_town_rows(df, state)
    return validate(df, TABLE)
