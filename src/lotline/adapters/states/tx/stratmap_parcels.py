"""TxGIO StratMap Land Parcels (statewide, from 253 appraisal districts) → `parcels` for Texas.

**Source.** The Texas Geographic Information Office (TxGIO, part of the Texas Water Development Board)
collects each appraisal district's parcels and attributes once a year, translates them into one schema and
publishes them as **CC0 1.0** (public domain) on its DataHub: collections for 2019, 2021, 2022, 2023, 2024,
2025 and 2026 (acquired 2026-09-25, 253 counties), each with one statewide zip and one zip per county.

**Hand-downloaded files.** The DataHub download host (`data.geographic.texas.gov`) answers scripted requests
with a CloudFront 403, so Ben downloads each zip in a browser and registers it (`lotline manifest register
--source stratmap_parcels --vintage <YYYY-MM>`, see `REGISTER_HELP`); nothing is fetched by script. `load()`
reads the registered rolls named in `ROLLS` (2019-03 and 2025-06: the releases with the most land-use codes;
see the comment there), one roll at a time.

**Format.** Zipped ESRI shapefiles (`lotline.adapters.states.tx.shapefile`), any number per zip, or a zipped
Esri file geodatabase (`lotline.adapters.states.tx.filegdb`), as the statewide files are: every polygon
table in it except the geodatabase's own `GDB_*` tables. Both readers are numpy only (Ben chose this over
GDAL/pyogrio, whose wheels bundle LGPL libraries, 2026-10-27). Coordinates are converted with the `.prj`
or the table's coordinate system (`lotline.adapters.states.tx.projection`).

**Fields read** (`FIELDS`, matched also by their 10-character `.dbf` truncation): prop_id, geo_id, fips,
county, tax_year, stat_land_use, loc_land_use, legal_area, lgl_area_unit, gis_area, gis_area_unit,
land_value, imp_value, year_built. Owner names (`owner_name`, `name_care`), mailing addresses (`mail_*`),
site addresses (`situs_*`) and the legal description are in the same records but **never decoded**.

**Rules.**

- **County:** `county_geoid` = "48" + the last three digits of `fips` (StratMap stores the county FIPS).
- **Parcel ID:** county_geoid + `prop_id` (the appraisal district's property ID, unique within a district);
  `geo_id` where prop_id is blank. A property drawn as several polygons keeps its largest polygon, so it
  counts once.
- **Land use:** the state category code `stat_land_use` (the Comptroller's PTAD codes A1, B2, C1 ...) through
  `config/crosswalks/tx_ptad_land_use.csv`, tried as the full code, its first two characters, then its first
  (as in `tcad_parcels`). Blank or unmatched → UNKNOWN; the county's own code (`loc_land_use`) is kept in
  `land_use_raw` when the state code is blank, for county crosswalks later. Counties with too little known
  land use stay on the ACS denominator by the D-017 gate (`build/eligible`), not here.
- **Lot size:** `legal_area` in its stated unit (`lgl_area_unit`: acres ×43,560, square feet ×1, square
  metres ×10.7639); else `gis_area` in its unit; else the polygon's own area, on an equal-area projection
  (Albers) as drawn and on Web Mercator corrected to true area at the centroid's latitude
  (`projection.sqm_per_unit2`). Otherwise missing. StratMap 2026 has no area units at all, so its lots come
  from the polygons.
- **Year built:** `year_built` from 1800 to the roll year, else missing (StratMap fills it in few counties).
- **Values:** land = `land_value`, building = `imp_value`; `value_basis = "appraisal"`. **Texas is a
  non-disclosure state: there are no sale prices.**
- **Roll year:** the registration's vintage year for every parcel in the release, so a release is one roll
  (the 2019-03 release mixes counties' 2018 and 2019 tax years; splitting by `tax_year` would leave a city
  that spans counties with partial rolls); `tax_year` (1900-2100, some districts send 0) only when the
  registration has no vintage. `vintage_date` = the vintage folder when it is a date.
- **Jurisdiction:** the parcel's centroid placed with `lotline.geo.place_or_township` (TIGERweb incorporated
  places); a centroid in no place, or in a place that is not a Texas jurisdiction, goes to its county's
  remainder (the county GEOID). Units, building area and homestead are not in StratMap: left null.
- **Partial extracts:** a county's part of a release with fewer than `min_county_roll_completeness` (0.8,
  config/params/parcels.yaml) of the parcels the county has in the other release read is left out of that
  release, with every jurisdiction that has parcels in it (`drop_partial_counties`); in 2019, Harris (0.66)
  and about 30 smaller counties.
- **Austin** keeps the TCAD roll (`config/states/tx.yaml` `parcel_sources`), so its parcels here are dropped
  later by `build/eligible.single_source`, not by this adapter.
"""

from __future__ import annotations

import csv
import re
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

from lotline.adapters.states.tx import filegdb, projection, shapefile
from lotline.config import CONFIG_DIR, load_params
from lotline.io import DataStore
from lotline.schemas import validate
from lotline.validation import holdout

ADAPTER = "states.tx.stratmap_parcels"
VERSION = "1.0"
SOURCE = "stratmap_parcels"
TABLE = "parcels"
LANDING_URL = "https://data.geographic.texas.gov/collection/?c=1d33dafb-6e9c-40ac-887d-f4577909ed9b"
LICENSE = "CC0 1.0 (TxGIO StratMap Land Parcels)"
COLLECTION_URL = "https://data.geographic.texas.gov/collection/?c={}"
LAND_USE_CROSSWALK = CONFIG_DIR / "crosswalks" / "tx_ptad_land_use.csv"
SQFT_PER_ACRE = 43_560  # definition of the acre
SQFT_PER_SQM = 10.763910  # 1 / 0.3048**2
MIN_YEAR_BUILT = 1800
MIN_TAX_YEAR, MAX_TAX_YEAR = 1900, 2100  # the parcels schema's vintage range
FIELDS = [
    "prop_id", "geo_id", "fips", "county", "tax_year", "stat_land_use", "loc_land_use", "legal_area",
    "lgl_area_unit", "gis_area", "gis_area_unit", "land_value", "imp_value", "year_built",
]  # fmt: skip
PERSONAL = {
    "owner_name", "name_care", "mail_addr", "mail_line1", "mail_line2", "mail_city", "mail_stat", "mail_zip",
    "situs_addr", "situs_num", "situs_stre", "situs_st_1", "situs_st_2", "situs_city", "situs_stat",
    "situs_zip", "legal_desc",
}  # fmt: skip

# Registered vintages that are read (vintage folder names). StratMap's releases differ in what they carry
# (WS-TX, 2026-10-27, share of parcels with a state land-use code): 2019-03 60%, 2022-07 none, 2024-02 35%,
# 2025-06 55%, 2026-09 none (no land use or area units for any county). A roll without land use never passes
# the D-017 gate, and each statewide roll takes about 2.6 GB in memory, so the two rolls with the most land
# use are read: 2019 (Harris, Tarrant, Bexar, Travis, El Paso, Fort Bend all 98%+) and 2025 (Harris, Tarrant,
# Dallas, Bexar, Hidalgo 88%+). They are the D-035 anchors; the other registered rolls are kept but not read.
ROLLS = ("2019-03", "2025-06")

REGISTER_HELP = (
    "No StratMap parcels zip is registered. Download the statewide files in a browser (each vintage has its "
    f"own collection; 2026: {LANDING_URL}), e.g. stratmap25-landparcels_48_lp.zip (2.8 GB) from "
    f"{COLLECTION_URL.format('0fa04328-872e-481c-b453-126a74777593')}, then run:\n"
    "  uv run lotline manifest register ~/Downloads/stratmap25-landparcels_48_lp.zip --source "
    f'stratmap_parcels --vintage 2025-06 --url "<collection URL>" --license "{LICENSE}"\n'
    f"Rolls read: {', '.join(ROLLS)} (ROLLS)."
)

PROVENANCE = {
    "title": "TxGIO StratMap Land Parcels (statewide, from Texas appraisal districts)",
    "landing_url": LANDING_URL,
    "table": TABLE,
    "cleaning": [
        "Downloaded by hand in a browser (the DataHub host blocks scripts) and registered with "
        "`lotline manifest register --source stratmap_parcels`; nothing is fetched by script",
        "Only parcel ID, county, tax year, land-use codes, areas, values and year built are decoded (from "
        "the .dbf or the geodatabase table); owner names, mailing and site addresses and legal descriptions "
        "are never decoded",
        "land_use_std from the PTAD state code (stat_land_use) via config/crosswalks/tx_ptad_land_use.csv; "
        "blank or unmatched -> UNKNOWN",
        "lot_sqft from legal_area, else gis_area, in their stated units, else the polygon's true area "
        "(equal-area projection, or Web Mercator corrected for latitude)",
        "jurisdiction_geoid = incorporated place holding the polygon centroid (lotline.geo), else the county "
        "remainder; parcel_id = county GEOID + prop_id; one row per parcel and roll (largest polygon)",
        "value_basis = appraisal; no sale prices (Texas non-disclosure)",
        "Rolls read: 2019-03 and 2025-06 (ROLLS), each release one roll at its release year; a county part "
        "with under 80% of the county's parcels in the other release (min_county_roll_completeness) is left "
        "out with every jurisdiction that touches it",
    ],
    "limitations": [
        "Attribute coverage varies by appraisal district: some counties send no state land-use code or year "
        "built; the D-017 gate keeps those on the ACS denominator",
        "The 2026-09 release has no land-use codes and no area units for any county (all null), so its "
        "rolls never pass the land-use gate; earlier releases carry the state code for part of the state",
        "PTAD category B (multifamily) does not say how many units; no unit counts",
        "Centroids of very irregular parcels can fall just outside them; placing by centroid can misplace "
        "parcels on a city boundary",
    ],
}


def load_land_use_crosswalk(path: Path = LAND_USE_CROSSWALK) -> dict[str, str]:
    with open(path, newline="") as fh:
        return {r["ptad_code"].strip().upper(): r["land_use_std"].strip() for r in csv.DictReader(fh)}


def land_use(code: str, crosswalk: dict[str, str]) -> str:
    """PTAD state code → land_use_std: full code, then its first two characters, then its first."""
    code = (code or "").strip().upper()
    if not code:
        return "UNKNOWN"
    for key in (code, code[:2], code[:1]):
        if key in crosswalk:
            return crosswalk[key]
    return "UNKNOWN"


def unit_sqft(unit: pd.Series) -> pd.Series:
    """Square feet per stated area unit (acres, square feet, square metres); NaN when unknown."""
    u = unit.astype("string").str.upper().str.replace(r"[^A-Z]", "", regex=True).fillna("")
    out = pd.Series(np.nan, index=unit.index)
    out[u.str.startswith("AC")] = SQFT_PER_ACRE
    out[u.isin(["SF", "SQFT", "SQFEET", "FT", "SQUAREFEET", "FEET"])] = 1.0
    out[u.isin(["SM", "SQM", "M", "SQMETERS", "SQUAREMETERS", "METERS"])] = SQFT_PER_SQM
    return out


def _number(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.astype("string").str.replace(",", "", regex=False), errors="coerce")


def lot_sqft(df: pd.DataFrame, sqm_per_unit2: float | None) -> pd.Series:
    legal = _number(df.get("legal_area", pd.Series(index=df.index, dtype="string"))) * unit_sqft(
        df.get("lgl_area_unit", pd.Series("", index=df.index))
    )
    gis = _number(df.get("gis_area", pd.Series(index=df.index, dtype="string"))) * unit_sqft(
        df.get("gis_area_unit", pd.Series("", index=df.index))
    )
    out = legal.where(legal > 0, gis.where(gis > 0))
    if sqm_per_unit2 is not None:
        shape = pd.Series(df["area"].to_numpy() * sqm_per_unit2 * SQFT_PER_SQM, index=df.index)
        out = out.where(out > 0, shape.where(shape > 0))
    return out.astype("float64")


def read_layer(zf: zipfile.ZipFile, layer: shapefile.Layer) -> pd.DataFrame:
    """One shapefile → attributes, centroid lon/lat and polygon area, aligned by record."""
    encoding = "latin-1"
    if layer.cpg:
        encoding = zf.read(layer.cpg).decode("ascii", "replace").strip() or encoding
    attrs = pd.concat(list(shapefile.read_records(zf, layer.dbf, FIELDS, encoding)), ignore_index=True)
    shapes = shapefile.read_shapes(zf, layer.shp)
    if len(shapes) != len(attrs):
        raise ValueError(f"{layer.shp}: {len(shapes)} shapes but {len(attrs)} attribute records")
    if not layer.prj:
        raise ValueError(f"{layer.shp}: no .prj, so the coordinate system is unknown")
    wkt = zf.read(layer.prj).decode("ascii", "replace")
    lon, lat = projection.from_wkt(wkt)(shapes["x"].to_numpy(), shapes["y"].to_numpy())
    df = attrs.assign(lon=lon, lat=lat, area=shapes["area"].to_numpy())
    df.attrs["sqm_per_unit2"] = projection.sqm_per_unit2(wkt, lat)
    return df.loc[~df["_deleted"]].drop(columns="_deleted")


def build(df: pd.DataFrame, *, vintage: int | None, vintage_date=None, sqm_per_unit2=None) -> pd.DataFrame:
    """Attribute rows (with lon, lat, area) → parcels rows, before jurisdiction assignment."""
    return one_per_parcel(rows(df, vintage=vintage, vintage_date=vintage_date, sqm_per_unit2=sqm_per_unit2))


def one_per_parcel(df: pd.DataFrame) -> pd.DataFrame:
    """A property drawn as several polygons keeps its largest, so it counts once."""
    df = df.sort_values("_area", na_position="first").drop_duplicates(["parcel_id", "vintage"], keep="last")
    return df.drop(columns="_area").reset_index(drop=True)


def rows(df: pd.DataFrame, *, vintage: int | None, vintage_date=None, sqm_per_unit2=None) -> pd.DataFrame:
    """Attribute rows → parcels rows with their polygon area (`_area`), one per polygon."""
    crosswalk = load_land_use_crosswalk()
    get = lambda c: df[c].astype("string").fillna("") if c in df else pd.Series("", index=df.index)  # noqa: E731
    fips = get("fips").str.replace(r"\D", "", regex=True).str[-3:].str.zfill(3)
    county = ("48" + fips).where(fips.str.fullmatch(r"\d{3}") & (fips != "000"))
    prop = get("prop_id").str.replace(r"\.0$", "", regex=True)
    pid = prop.where(prop != "", get("geo_id"))
    if vintage is not None:  # one roll per release: county parts with an older tax year stay in it
        year = pd.Series(vintage, index=df.index, dtype="Int64")
    else:
        year = pd.to_numeric(get("tax_year"), errors="coerce")
        year = year.where(year.between(MIN_TAX_YEAR, MAX_TAX_YEAR)).astype("Int64")  # some districts send 0
    stat = get("stat_land_use").str.upper()
    raw_code = stat.where(stat != "", get("loc_land_use").str.upper())
    built = pd.to_numeric(get("year_built"), errors="coerce")
    built = built.where((built >= MIN_YEAR_BUILT) & (built <= year.astype("float64") + 1))
    out = pd.DataFrame(
        {
            "state": "TX",
            "parcel_id": (county + pid).where(county.notna() & (pid != "")),
            "vintage": year,
            "vintage_date": pd.Series(vintage_date, index=df.index, dtype="datetime64[ns]"),
            "county_geoid": county.astype("string"),
            "lot_sqft": lot_sqft(df, sqm_per_unit2),
            "land_use_std": stat.map(lambda c: land_use(c, crosswalk)),
            "land_use_raw": raw_code.replace("", pd.NA),
            "units": pd.Series(pd.NA, index=df.index, dtype="Int64"),
            "year_built": built.round().astype("Int64"),
            "land_value": _number(get("land_value")).where(lambda v: v >= 0).astype("float64"),
            "bldg_value": _number(get("imp_value")).where(lambda v: v >= 0).astype("float64"),
            "value_basis": "appraisal",
            "lon": pd.Series(df["lon"].to_numpy(), index=df.index).where(lambda v: v.between(-180, 180)),
            "lat": pd.Series(df["lat"].to_numpy(), index=df.index).where(lambda v: v.between(-90, 90)),
            "source": SOURCE,
            "_area": df["area"].to_numpy(),
        }
    )
    return out.loc[out["parcel_id"].notna() & out["vintage"].notna()]


def resolve_jurisdictions(county_geoid: pd.Series, place: pd.Series, known: set[str]) -> pd.Series:
    """The place holding the centroid when it is a known jurisdiction, else the county remainder."""
    place = place.astype("string")
    ok = place.notna() & place.isin(known).fillna(False)
    return place.where(ok, county_geoid.astype("string"))


def assign_jurisdictions(df: pd.DataFrame, store: DataStore) -> pd.DataFrame:
    from lotline import geo
    from lotline.build import jurisdictions as jur

    juris = store.read("TX", "jurisdictions")
    if juris is None:
        juris = jur.load("TX", store)
    place = geo.place_or_township(df["lon"], df["lat"], "TX", store)
    return df.assign(jurisdiction_geoid=resolve_jurisdictions(df["county_geoid"], place, set(juris["geoid"])))


def read_roll(path: Path, *, vintage: int | None, vintage_date=None) -> pd.DataFrame:
    """One registered zip → parcels rows (before jurisdiction assignment)."""
    with zipfile.ZipFile(path) as zf:
        found = shapefile.layers(zf)
        if not found:
            if any(".gdb/" in n.lower() for n in zf.namelist()):
                return read_geodatabase(zf, vintage=vintage, vintage_date=vintage_date)
            raise FileNotFoundError(f"{path.name}: no shapefile (.shp with .dbf) or file geodatabase inside")
        rolls = []
        for layer in found:
            df = read_layer(zf, layer)
            rolls.append(
                build(df, vintage=vintage, vintage_date=vintage_date, sqm_per_unit2=df.attrs["sqm_per_unit2"])
            )
    return pd.concat(rolls, ignore_index=True)


def read_geodatabase(zf: zipfile.ZipFile, *, vintage: int | None, vintage_date=None) -> pd.DataFrame:
    """Every polygon table in a zipped file geodatabase → parcels rows, read in chunks."""
    found = filegdb.polygon_tables(zf)
    if not found:
        raise FileNotFoundError(f"{zf.filename}: the file geodatabase has no polygon table")
    parts = []
    for table in found:
        if not table.wkt:
            raise ValueError(f"{table.member}: no coordinate system, so the parcels cannot be placed")
        to_lonlat = projection.from_wkt(table.wkt)
        for chunk in filegdb.read_rows(zf, table, FIELDS):
            lon, lat = to_lonlat(chunk["x"].to_numpy(), chunk["y"].to_numpy())
            chunk = chunk.assign(lon=lon, lat=lat)
            sqm = projection.sqm_per_unit2(table.wkt, lat)
            parts.append(rows(chunk, vintage=vintage, vintage_date=vintage_date, sqm_per_unit2=sqm))
    return one_per_parcel(pd.concat(parts, ignore_index=True))


def _vintage(rel_path: str) -> tuple[int | None, pd.Timestamp | None]:
    folder = Path(rel_path).parent.name
    m = re.fullmatch(r"(\d{4})(?:-(\d{2}))?(?:-(\d{2}))?", folder)
    if not m:
        return None, None
    date = pd.Timestamp(folder) if m.group(3) else None
    return int(m.group(1)), date


def drop_partial_counties(
    rolls: list[pd.DataFrame], min_share: float
) -> tuple[list[pd.DataFrame], pd.DataFrame]:
    """Leave out county parts of a release that look like partial extracts (`min_county_roll_completeness`).

    A county's part of release i is partial when its parcel count is below `min_share` times the county's
    largest count in the other releases (a county no other release has is kept). Every jurisdiction with
    parcels in a partial part is left out of that release too, so no city keeps a roll with part of its
    parcels missing; it counts from the other release or the ACS fallback. With one release nothing is
    dropped. Returns the filtered rolls and a table of what was dropped (release, county, counts, share).
    By hand: county 48201 with 66 parcels in release 0 and 100 in release 1 -> share 0.66 < 0.8, dropped
    from release 0 with every jurisdiction that has parcels in it.
    """
    counts = pd.DataFrame({i: r["county_geoid"].value_counts() for i, r in enumerate(rolls)})
    kept, dropped = [], []
    for i, roll in enumerate(rolls):
        others = counts.drop(columns=i).max(axis=1)
        share = counts[i] / others
        bad = share.index[share < min_share]
        for c in bad:
            dropped.append({"release": i, "county_geoid": c, "parcels": int(counts.at[c, i]),
                            "other_release_parcels": int(others[c]), "share": float(share[c])})  # fmt: skip
        juris = roll.loc[roll["county_geoid"].isin(bad), "jurisdiction_geoid"].unique()
        kept.append(roll.loc[~(roll["county_geoid"].isin(bad) | roll["jurisdiction_geoid"].isin(juris))])
    return kept, pd.DataFrame(dropped, columns=["release", "county_geoid", "parcels", "other_release_parcels",
                                                "share"])  # fmt: skip


def load(state: str, store: DataStore, *, refresh: bool = False) -> pd.DataFrame:
    if state.upper() != "TX":
        raise ValueError(f"{SOURCE} covers Texas only, not {state}")
    entries = [e for e in store.registered(SOURCE) if e.path.lower().endswith(".zip")]
    if not entries:
        raise FileNotFoundError(REGISTER_HELP)
    stale = [e.path for e in entries if store.is_stale(e)]
    if stale:
        raise FileNotFoundError(f"registered StratMap files missing or changed since registration: {stale}")
    # the same roll registered twice (e.g. a re-download) counts once: keep the later registration
    by_vintage = {Path(e.path).parent.name: e for e in entries}
    chosen = [e for v, e in sorted(by_vintage.items()) if v in ROLLS]
    if not chosen:
        raise FileNotFoundError(
            f"none of the rolls read ({', '.join(ROLLS)}) is registered: {sorted(by_vintage)}"
        )
    rolls = []
    for e in chosen:  # one roll at a time, so only one roll's raw fields are in memory
        year, date = _vintage(e.path)
        df = assign_jurisdictions(read_roll(store.root / e.path, vintage=year, vintage_date=date), store)
        df = holdout.apply(
            df,
            "TX",
            geoid_col="jurisdiction_geoid",
            date_col="vintage_date",
            year_col="vintage",
            snapshot=True,
        )
        rolls.append(validate(df, TABLE))
    min_share = load_params("parcels")["min_county_roll_completeness"].value
    rolls, _ = drop_partial_counties(rolls, min_share)
    return pd.concat(rolls, ignore_index=True)
