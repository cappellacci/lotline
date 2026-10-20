"""Metropolitan Council Regional Parcel Dataset (7-county Twin Cities metro) → `parcels`, one row per tax
parcel per roll.

**Layers.** The point layers of the regional dataset (one point per tax parcel, condominium units included,
same attributes as the polygons): the 7-county layer of `Parcel_Points_2021` ... `Parcel_Points_2025` (the
"year-end" archives) and `Parcel_Points_Aggregate` (the current quarterly roll). Points give each parcel's
location directly, so no polygons are downloaded. Older rolls (2002-2020, `ds1/.../GISParcels/...`) need a
token: they are not used (Ben has asked Met Council for them, #11).

**Vintages** (Ben, 2026-10-19). `vintage` is the year in the service name (the "current" roll takes the year
of its export) and `vintage_date` is the county's latest export date (`EXP_DATE`), never the name: the
counties export the "2023" roll between 2023-10-01 (Scott) and 2024-01-08 (Hennepin), and the "2025" roll is
a mid-2025 export (June-July 2025), not a year-end one.

**Holdout.** A roll exported on or after 2024-01-01 shows what St. Paul built during the V5 window, so St.
Paul rows survive only from rolls exported up to 2023 (`holdout.apply(..., snapshot=True)`). The filter runs
right after jurisdictions are assigned, before any attribute is read, on both the point's jurisdiction and
the county's own city name (`CTU_NAME`), so a parcel that either source puts in St. Paul is hidden.

**Jurisdiction.** Each point is placed with `lotline.geo.place_or_township` (incorporated place, else county
subdivision: MN townships issue permits) and checked against the MN jurisdictions table and against the
county's `CTU_NAME` (matched by name to the same table):

1. the place or township found, if it is in the table;
2. else the jurisdiction named by `CTU_NAME`, if it is in the table;
3. else the county's remainder row (5-digit GEOID).

**Land use.** `USECLASS1` (the county's label of the Minnesota property class, Minn. Stat. 273.13; labels
differ by county) → `land_use_std` by the ordered rules of `config/crosswalks/mn_land_use.csv`. Where the
county records a dwelling type (`DWELL_TYPE`: Ramsey, Dakota, Washington, part of Anoka), the rules of
`config/crosswalks/mn_land_use_dwelling.csv` override a residential use class (they tell townhomes, condos,
duplexes and triplexes apart). A rule flagged `refine_by_units` is refined by the parcel's unit count where
it is known (1 → SF_DETACHED, 2 → DUPLEX, 3-4 → TRI_QUAD, 5+ → MULTIFAMILY_5P: the definitions of those
codes).

**Personal data.** The layer carries owner and taxpayer names and addresses and situs addresses. They are
never requested: `FIELDS` lists exactly what is read.
"""

from __future__ import annotations

import csv
import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from lotline.config import CONFIG_DIR
from lotline.io import DataStore
from lotline.io.arcgis import download_layer, epoch_ms_to_timestamp, query_url
from lotline.io.http import fetch
from lotline.schemas import validate
from lotline.validation import holdout

ADAPTER = "states.mn.metc_parcels"
VERSION = "1.0"
SOURCE = "metc_parcels"
TABLE = "parcels"
LICENSE = (
    "Public domain (Minnesota Government Data Practices Act); MetroGIS counties share parcel data "
    "without fee or license"
)
SERVICE_ROOT = "https://arcgis.metc.state.mn.us/data1/rest/services/parcels"
LANDING_URL = "https://www.arcgis.com/home/item.html?id=9cea9e4cbfec4e21ac552750072dd0d5"
USE_CROSSWALK = CONFIG_DIR / "crosswalks" / "mn_land_use.csv"
DWELLING_CROSSWALK = CONFIG_DIR / "crosswalks" / "mn_land_use_dwelling.csv"
SQFT_PER_ACRE = 43_560.0  # definition of the acre
MIN_YEAR_BUILT = 1800  # earlier years are placeholders in county rolls
OID_CHUNK = 100_000  # OBJECTIDs per query: keeps paging offsets shallow (mechanics only)
RETRIES = 5  # pager retries on ArcGIS error bodies (mechanics only)


@dataclass(frozen=True)
class Roll:
    label: str  # "2021" ... "2025" or "current"
    service: str
    layer: int

    @property
    def url(self) -> str:
        return f"{SERVICE_ROOT}/{self.service}/FeatureServer/{self.layer}"

    @property
    def raw_vintage(self) -> str | None:
        """Raw folder: archive rolls never change (one folder each); the current roll is a dated snapshot."""
        return None if self.label == "current" else f"roll_{self.label}"


# Ben (2026-10-19): the 2023 and current rolls first, then the other archives.
ROLLS = [
    Roll("2023", "Parcel_Points_2023", 7),
    Roll("current", "Parcel_Points_Aggregate", 0),
    Roll("2021", "Parcel_Points_2021", 7),
    Roll("2022", "Parcel_Points_2022", 7),
    Roll("2024", "Parcel_Points_2024", 7),
    Roll("2025", "Parcel_Points_2025", 7),
]

# Exactly what is read. Never "*": OWNER_NAME, OWNER_MORE, OWN_ADD_L1-4, TAX_NAME, TAX_ADD_L1-4 and the situs
# address fields (ANUMBER ... ZIP4) identify people or homes and are never requested.
FIELDS = [
    "OBJECTID",
    "COUNTY_PIN",
    "CO_CODE",
    "CO_NAME",
    "CTU_NAME",
    "HOMESTEAD",
    "ACRES_POLY",
    "ACRES_DEED",
    "EMV_LAND",
    "EMV_BLDG",
    "USECLASS1",
    "DWELL_TYPE",
    "FIN_SQ_FT",
    "YEAR_BUILT",
    "NUM_UNITS",
    "SALE_DATE",
    "SALE_VALUE",
    "EXP_DATE",
]
PERSONAL = {
    "OWNER_NAME",
    "OWNER_MORE",
    "OWN_ADD_L1",
    "OWN_ADD_L2",
    "OWN_ADD_L3",
    "OWN_ADD_L4",
    "TAX_NAME",
    "TAX_ADD_L1",
    "TAX_ADD_L2",
    "TAX_ADD_L3",
    "TAX_ADD_L4",
    "ANUMBER",
    "ST_NAME",
    "ZIP",
}
RESIDENTIAL = {
    "SF_DETACHED",
    "SF_ATTACHED",
    "DUPLEX",
    "TRI_QUAD",
    "MULTIFAMILY_5P",
    "CONDO_UNIT",
    "UNKNOWN",
}

PROVENANCE = {
    "title": "Met Council Regional Parcel Dataset, parcel points (7-county metro, 2021-2025 and current)",
    "landing_url": LANDING_URL,
    "table": TABLE,
    "attribution": "Metropolitan Council / MetroGIS; parcel data from Anoka, Carver, Dakota, Hennepin, "
    "Ramsey, Scott and Washington counties",
    "cleaning": [
        f"7-county parcel point layers {', '.join(r.service for r in ROLLS)} ({SERVICE_ROOT}), downloaded "
        "per county and OBJECTID range, requesting only "
        + ", ".join(FIELDS)
        + " and the point (WGS84). Owner, "
        "taxpayer and situs address fields are never requested",
        "vintage = the year in the service name (current roll: year of its export); vintage_date = the "
        "county's latest EXP_DATE in that roll (the 2025 roll is a mid-2025 export)",
        "parcel_id = county GEOID (CO_CODE) + COUNTY_PIN (letters and digits only); a PIN repeated within a "
        "county and roll keeps its first row",
        "jurisdiction_geoid by lotline.geo.place_or_township on the point (TIGERweb ACS 2025), kept if in "
        "the MN jurisdictions table; else the jurisdiction CTU_NAME names; else the county's remainder row",
        "Held-out rows removed right after jurisdictions are assigned, before attributes are read "
        "(V5-MN-STPAUL, snapshot rule: St. Paul only from rolls exported before 2024-01-01), on both the "
        "point's jurisdiction and the CTU_NAME jurisdiction",
        "land_use_std: USECLASS1 by the ordered rules in config/crosswalks/mn_land_use.csv; a residential "
        "result is overridden by DWELL_TYPE rules (config/crosswalks/mn_land_use_dwelling.csv); rules "
        "flagged refine_by_units use NUM_UNITS where known (1 SF_DETACHED, 2 DUPLEX, 3-4 TRI_QUAD, 5+ "
        "MULTIFAMILY_5P); land_use_raw = USECLASS1",
        "units = NUM_UNITS; null where the county leaves it unpopulated in a roll (no positive value at all, "
        "e.g. Hennepin, where it is 0 everywhere)",
        "lot_sqft = ACRES_POLY × 43,560, else ACRES_DEED × 43,560, else null",
        "year_built = YEAR_BUILT from 1800 to the roll year + 1, else null; bldg_sqft = FIN_SQ_FT > 0",
        "land_value / bldg_value = EMV_LAND / EMV_BLDG (estimated market value, value_basis=market)",
        "last_sale_price / last_sale_date = SALE_VALUE (> 0) / SALE_DATE; sale_multi_parcel = the same sale "
        "date and price on more than one parcel of the county in the roll; null for sales dated the 1st of a "
        "month (Hennepin records most sales by month only)",
        "homestead: HOMESTEAD Yes/Partial → True, No → False, else null",
    ],
    "limitations": [
        "Rolls before 2021 are token-locked (2002-2020 services); requested from Met Council (#11)",
        "Hennepin leaves NUM_UNITS and DWELL_TYPE blank: units are null and land use comes from the use "
        "class only",
        "Use-class labels differ by county and over time; the crosswalk is rule-based (first match wins) and "
        "class 4b(1) '1-3 units' is read as 2-3 units (DUPLEX) unless units or dwelling type say otherwise",
        "Condominium points carry their building lot's acres, so lot_sqft overstates condo lots",
        "Values are the assessor's estimated market value for the roll's assessment year, not sale prices",
        "sale_multi_parcel can also flag separate sales at the same price on the same day (new townhomes); "
        "it is null for most Hennepin sales (month-only dates)",
        "Jurisdictions use 2025 boundaries; annexations since a roll's date are not reflected",
        "St. Paul parcels exist only in the 2021-2023 rolls (V5 holdout)",
    ],
}


# ---- crosswalks ------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Rule:
    county: str  # county name or "*"
    pattern: re.Pattern
    land_use_std: str
    refine: bool


def load_rules(path: Path) -> list[Rule]:
    with open(path, newline="") as fh:
        return [
            Rule(
                r["county"].strip(),
                re.compile(r["pattern"], re.I),
                r["land_use_std"].strip(),
                r["refine_by_units"].strip().lower() == "yes",
            )
            for r in csv.DictReader(fh)
        ]


def _norm_text(values: pd.Series) -> pd.Series:
    return values.astype("string").str.split().str.join(" ").replace("", pd.NA)


def apply_rules(county: pd.Series, text: pd.Series, rules: list[Rule]) -> tuple[pd.Series, pd.Series]:
    """(land_use_std or <NA>, refine flag) per row: the first rule whose county and pattern match.

    Rules are tried once per distinct (county, text) pair, so millions of rows cost a few hundred lookups.
    """
    keys = pd.DataFrame({"county": county.astype("string"), "text": _norm_text(text)})
    out: dict[tuple, tuple] = {}
    for c, t in keys.drop_duplicates().itertuples(index=False):
        hit = (pd.NA, False)
        if not pd.isna(t):
            for r in rules:
                if (r.county == "*" or r.county == c) and r.pattern.search(t):
                    hit = (r.land_use_std, r.refine)
                    break
        out[(c, t)] = hit
    pairs = [out[(c, t)] for c, t in keys.itertuples(index=False)]
    use = pd.Series([p[0] for p in pairs], index=county.index, dtype="string")
    refine = pd.Series([p[1] for p in pairs], index=county.index, dtype=bool)
    return use, refine


def units_class(units: pd.Series) -> pd.Series:
    """Land use implied by a building's unit count (definitions of the codes); <NA> when unknown or 0."""
    u = pd.to_numeric(units, errors="coerce").astype("float64")  # NaN compares False, unlike pd.NA
    out = pd.Series(pd.NA, index=units.index, dtype="string")
    out = out.mask(u == 1, "SF_DETACHED").mask(u == 2, "DUPLEX").mask(u.between(3, 4), "TRI_QUAD")
    return out.mask(u >= 5, "MULTIFAMILY_5P")


def land_use(
    county: pd.Series,
    useclass: pd.Series,
    dwelling: pd.Series,
    units: pd.Series,
    use_rules: list[Rule] | None = None,
    dwell_rules: list[Rule] | None = None,
) -> pd.Series:
    use, use_refine = apply_rules(county, useclass, use_rules or load_rules(USE_CROSSWALK))
    dwell, dwell_refine = apply_rules(county, dwelling, dwell_rules or load_rules(DWELLING_CROSSWALK))
    use = use.fillna("UNKNOWN")
    by_dwelling = dwell.notna() & use.isin(RESIDENTIAL)
    result = use.mask(by_dwelling, dwell)
    refine = use_refine.where(~by_dwelling, dwell_refine)
    implied = units_class(units)
    return result.mask(refine & implied.notna(), implied).astype("string")


# ---- jurisdictions ---------------------------------------------------------------------------------------


def _name_key(name: str) -> str:
    s = name.lower().replace("saint ", "st. ").replace(".", "")
    s = re.sub(r"\btwp\b", "township", s)
    s = re.sub(r"\s*\(.*?\)", "", s)  # "St. Anthony city (Hennepin and Ramsey Counties)"
    s = re.sub(r"\s+(city|ut)$", "", s.strip())  # "Fort Snelling UT" (unorganized territory)
    return " ".join(s.split())


METRO_COUNTIES = ("27003", "27019", "27037", "27053", "27123", "27139", "27163")


def ctu_lookup(jurisdictions: pd.DataFrame, counties: tuple[str, ...] | None = None) -> dict[str, str]:
    """Normalized place/township name → GEOID, leaving out names that two jurisdictions share.

    A Census-style name ("... city", "... township") wins over a bare duplicate of the same name.
    `counties` keeps only jurisdictions whose primary county is listed (St. Anthony, Hennepin/Ramsey, not
    St. Anthony, Stearns).
    """
    j = jurisdictions[jurisdictions["kind"].isin(["place", "township"])]
    if counties is not None and "county_geoid" in j:
        j = j[j["county_geoid"].isin(counties)]
    keys = j["name"].map(_name_key)
    standard = j["name"].str.contains(r"\s(?:city|township|UT)\b", regex=True)
    j = j.assign(key=keys, standard=standard).sort_values("standard", ascending=False)
    j = j[~(j.duplicated("key", keep="first") & ~j["standard"])]  # bare duplicates of a standard name
    counts = j["key"].value_counts()
    return {k: g for k, g in zip(j["key"], j["geoid"], strict=True) if counts[k] == 1}


def ctu_geoids(ctu_name: pd.Series, lookup: dict[str, str]) -> pd.Series:
    names = ctu_name.astype("string")
    keys = names.map(lambda n: _name_key(n) if isinstance(n, str) else pd.NA, na_action="ignore")
    direct = keys.map(lookup)
    # Met Council writes townships as bare names ("Credit River"): try the township form too.
    twp = keys.map(lambda k: lookup.get(f"{k} township") if isinstance(k, str) else None, na_action="ignore")
    return direct.fillna(twp).astype("string")


def resolve(
    county_geoid: pd.Series, found: pd.Series, ctu: pd.Series, known: set[str]
) -> tuple[pd.Series, pd.Series]:
    """(jurisdiction_geoid, how): the point's place/township if known, else CTU_NAME's, else the county."""
    found = found.astype("string")
    ctu = ctu.astype("string")
    in_found = found.isin(known).fillna(False).astype(bool)
    in_ctu = ctu.isin(known).fillna(False).astype(bool)
    geoid = found.where(in_found, ctu.where(in_ctu, county_geoid.astype("string")))
    how = pd.Series("county_fallback", index=found.index, dtype="string")
    how = how.mask(in_ctu & ~in_found, "ctu_name").mask(in_found, "point")
    return geoid, how


Locator = Callable[[pd.Series, pd.Series], pd.Series]


def multi_parcel_sales(county: pd.Series, date: pd.Series, price: pd.Series) -> pd.Series:
    """True when the same sale date and price appear on more than one parcel of a county; null if unknown.

    A sale dated the 1st of a month is left null: Hennepin records most sales by month only (83% of its 2023
    sale dates fall on the 1st, against about 3% elsewhere), and month and price alone match unrelated sales.
    """
    usable = price.notna() & date.notna() & (date.dt.day != 1).fillna(False)
    group = pd.DataFrame({"c": county, "d": date, "p": price})[usable]
    repeats = group.groupby(["c", "d", "p"])["c"].transform("size")
    multi = pd.Series(pd.NA, index=county.index, dtype="boolean")
    multi[usable] = (repeats > 1).to_numpy()
    return multi


# ---- table -----------------------------------------------------------------------------------------------


def _county_geoid(co_code: pd.Series) -> pd.Series:
    digits = co_code.astype("string").str.replace(r"\D", "", regex=True)
    return digits.where(digits.str.len() == 5, "27" + digits.str.zfill(3)).astype("string")


def _local_pin(pin: pd.Series) -> pd.Series:
    clean = pin.astype("string").str.upper().str.replace(r"[^0-9A-Z]", "", regex=True)
    return clean.mask(clean.str.fullmatch(r"0*").fillna(True)).astype("string")


# Dates outside these bounds are keying errors in county rolls (e.g. a sale in 3009): treated as unknown.
EARLIEST, LATEST = pd.Timestamp("1900-01-01"), pd.Timestamp("2100-01-01")


def _dates(ms: pd.Series) -> pd.Series:
    ms = pd.to_numeric(ms, errors="coerce")
    lo, hi = (
        (EARLIEST - pd.Timestamp(0)) // pd.Timedelta(milliseconds=1),
        (LATEST - pd.Timestamp(0)) // pd.Timedelta(milliseconds=1),
    )
    ms = ms.where(ms.between(lo, hi))
    return epoch_ms_to_timestamp(ms).dt.normalize().astype("datetime64[ns]")


def to_parcels(
    raw: pd.DataFrame,
    label: str,
    jurisdictions: pd.DataFrame,
    locate: Locator,
    state: str = "MN",
) -> tuple[pd.DataFrame, pd.Series]:
    """One roll (+ lon/lat) → validated `parcels` without held-out rows, and how each row was placed."""
    raw = raw.drop(columns=[c for c in raw.columns if c in PERSONAL])
    df = raw.assign(
        county_geoid=_county_geoid(raw["CO_CODE"]),
        local_pin=_local_pin(raw["COUNTY_PIN"]),
        exported=_dates(raw["EXP_DATE"]),
    )
    df = df[df["local_pin"].notna()]
    df = df.assign(parcel_id=df["county_geoid"] + df["local_pin"])
    df = df.drop_duplicates("parcel_id", keep="first")
    vintage_date = df.groupby("county_geoid")["exported"].transform("max")
    year = int(label) if label.isdigit() else int(vintage_date.max().year)

    lon = pd.to_numeric(df.get("lon"), errors="coerce")
    lat = pd.to_numeric(df.get("lat"), errors="coerce")
    known = set(jurisdictions["geoid"].astype(str))
    ctu = ctu_geoids(df["CTU_NAME"], ctu_lookup(jurisdictions, METRO_COUNTIES))
    geoid, how = resolve(df["county_geoid"], locate(lon, lat), ctu, known)
    df = df.assign(
        jurisdiction_geoid=geoid,
        ctu_geoid=ctu,
        how=how,
        vintage=pd.array([year] * len(df), dtype="Int64"),
        vintage_date=vintage_date,
        lon=lon,
        lat=lat,
    )
    # Before any attribute is read: the snapshot rule on the point's jurisdiction and on CTU_NAME's.
    rule = {"date_col": "vintage_date", "year_col": "vintage", "snapshot": True}
    df = holdout.apply(df, state, geoid_col="jurisdiction_geoid", **rule)
    df = holdout.apply(df.assign(ctu_geoid=df["ctu_geoid"].fillna("")), state, geoid_col="ctu_geoid", **rule)
    how = df["how"]

    units = pd.to_numeric(df["NUM_UNITS"], errors="coerce").round().astype("Int64")
    populated = (units > 0).fillna(False).groupby(df["county_geoid"]).transform("any")
    units = units.where(populated & (units >= 0))
    built = pd.to_numeric(df["YEAR_BUILT"], errors="coerce").round().astype("Int64")
    built = built.where(built.between(MIN_YEAR_BUILT, year + 1))
    poly = pd.to_numeric(df["ACRES_POLY"], errors="coerce")
    deed = pd.to_numeric(df["ACRES_DEED"], errors="coerce")
    acres = poly.where(poly > 0, deed.where(deed > 0))
    sale_price = pd.to_numeric(df["SALE_VALUE"], errors="coerce").astype(float)
    sale_price = sale_price.where(sale_price > 0)
    sale_date = _dates(df["SALE_DATE"])
    sale = sale_price.notna() & sale_date.notna()
    multi = multi_parcel_sales(df["county_geoid"], sale_date, sale_price)
    homestead = (
        df["HOMESTEAD"]
        .astype("string")
        .str.strip()
        .str.lower()
        .map({"yes": True, "partial": True, "no": False})
    )
    county_name = df["CO_NAME"].astype("string").str.strip()

    out = pd.DataFrame(
        {
            "state": state,
            "parcel_id": df["parcel_id"],
            "vintage": df["vintage"],
            "vintage_date": df["vintage_date"],
            "jurisdiction_geoid": df["jurisdiction_geoid"],
            "county_geoid": df["county_geoid"],
            "lot_sqft": (acres * SQFT_PER_ACRE).astype(float),
            "land_use_std": land_use(county_name, df["USECLASS1"], df["DWELL_TYPE"], units),
            "land_use_raw": _norm_text(df["USECLASS1"]),
            "units": units,
            "year_built": built,
            "bldg_sqft": pd.to_numeric(df["FIN_SQ_FT"], errors="coerce").astype(float).where(lambda s: s > 0),
            "land_value": pd.to_numeric(df["EMV_LAND"], errors="coerce")
            .astype(float)
            .where(lambda s: s >= 0),
            "bldg_value": pd.to_numeric(df["EMV_BLDG"], errors="coerce")
            .astype(float)
            .where(lambda s: s >= 0),
            "value_basis": "market",
            "last_sale_price": sale_price,
            "last_sale_date": sale_date.where(sale),
            "sale_multi_parcel": multi,
            "homestead": homestead.astype("boolean"),
            "lon": df["lon"],
            "lat": df["lat"],
            "source": SOURCE,
        }
    )
    return validate(out.reset_index(drop=True), TABLE), how.reset_index(drop=True)


# ---- download --------------------------------------------------------------------------------------------


def oid_ranges(roll: Roll, store: DataStore, *, refresh: bool = False) -> dict[str, tuple[int, int]]:
    """County name → (min, max) OBJECTID in a roll, from one statistics query downloaded through `fetch()`."""
    stats = json.dumps(
        [
            {"statisticType": "min", "onStatisticField": "OBJECTID", "outStatisticFieldName": "lo"},
            {"statisticType": "max", "onStatisticField": "OBJECTID", "outStatisticFieldName": "hi"},
        ]
    )
    url = query_url(
        roll.url, where="1=1", groupByFieldsForStatistics="CO_NAME", outStatistics=stats, f="json"
    )
    vintage = roll.raw_vintage or pd.Timestamp.today().date().isoformat()
    path = fetch(
        url,
        store.raw(SOURCE, vintage) / "parcels" / f"oid_ranges_{roll.label}.json",
        store=store,
        source=SOURCE,
        license=LICENSE,
        adapter=ADAPTER,
        adapter_version=VERSION,
        refresh=refresh,
    )
    feats = json.loads(path.read_text())["features"]
    return {f["attributes"]["CO_NAME"]: (f["attributes"]["lo"], f["attributes"]["hi"]) for f in feats}


def chunks(lo: int, hi: int, size: int = OID_CHUNK) -> list[tuple[int, int]]:
    """Half-open OBJECTID ranges [a, b) covering lo..hi."""
    start = lo - lo % size
    return [(a, a + size) for a in range(start, hi + 1, size)]


def download(roll: Roll, store: DataStore, *, refresh: bool = False) -> pd.DataFrame:
    """One query per county and OBJECTID range, each cached and resumable on its own."""
    frames = []
    for county, (lo, hi) in sorted(oid_ranges(roll, store, refresh=refresh).items()):
        for a, b in chunks(lo, hi):
            frames.append(
                download_layer(
                    roll.url,
                    store=store,
                    source=SOURCE,
                    license=LICENSE,
                    adapter=ADAPTER,
                    adapter_version=VERSION,
                    name="parcels",
                    where=f"CO_NAME='{county}' AND OBJECTID>={a} AND OBJECTID<{b}",
                    out_fields=",".join(FIELDS),
                    geometry=True,
                    vintage=roll.raw_vintage,
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


def load(
    state: str, store: DataStore, *, refresh: bool = False, rolls: list[Roll] | None = None
) -> pd.DataFrame:
    if state.upper() != "MN":
        raise ValueError(f"{SOURCE} covers the Minnesota 7-county metro only, not {state}")
    from lotline import geo

    juris = _jurisdictions(state, store)

    def locate(lon: pd.Series, lat: pd.Series) -> pd.Series:
        return geo.place_or_township(lon, lat, state, store)

    tables = []
    for roll in rolls or ROLLS:
        table, _ = to_parcels(download(roll, store, refresh=refresh), roll.label, juris, locate, state)
        tables.append(table)
    return validate(pd.concat(tables, ignore_index=True), TABLE)
