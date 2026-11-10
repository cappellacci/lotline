"""Mid-Willamette Valley COG residential building permits since 1998 (ArcGIS FeatureServer) → `permits`.

The Mid-Willamette Valley Council of Governments (MWVCOG) keeps a geocoded file of every residential building
permit issued in the Salem-Keizer area and Marion and Polk counties since 1998, one row per permit, with a
type code (`Type`): NSFD new single-family house, NDUP duplex, MULT multifamily, MH manufactured home, **ADU**
accessory dwelling unit, and DEMO* demolitions. It is the only record-level source found for **Salem**
(Oregon's 4th-largest pool of ADU-eligible lots) and **Marion County's unincorporated area**: the City of
Salem's own permit layer covers only a rolling year and its terms bar copying the data
(`reports/or/adu-coverage-and-undercount.md` §3).

**Dates.** The file carries the year (`YearNo`) and quarter (`QUARTER`) only, so `issue_date` is null and
`date_precision` is `year`.

**ADUs.** `Type` ADU is the COG's own category (a field flag, not text): `building_type_std` ADU, 1 unit,
`adu_type` unknown (the file doesn't say attached or detached). A DEMOADU row removes one.

**Other types.** NSFD → SFD; NDUP → U2; MULT → by `UNITS` (2 U2, 3-4 U3_4, 5+ MF5); MH → OTHER (manufactured
home). `units_new` = `UNITS` (reported; an ADU or house without units is 1, derived). Demolitions (DEMO,
DEMOSF, DEMODUP, DEMOMF, DEMOMH, DEMOADU, DEMODP): `is_demolition`, `units_new` 0, `units_removed` = `UNITS`
(or 1 for a one-unit type when blank).

**Jurisdiction.** `City` is where the permit is; `JURISD` is the office that issued it. They differ: Marion
County issues Keizer's and Turner's permits (934 Keizer rows carry `JURISD` MC), so `City` decides
(`CITIES`: Salem, Keizer, Turner, Marion County and Polk County spellings). When `City` is blank (mostly
2023–2024), `JURISD` decides, but only for the cities that issue their own permits (SALEM; KEIZER and TURNER
when stated). A blank-`City` permit from Marion or Polk County could be in any city those counties serve, so
it is dropped, as is a row with neither (`unassigned`, counted by `build`). County permits outside a city go
to
the county remainders (41047, 41053). **Only Salem is kept by default** (`KEEP`): the other places are only
partly in the file (Keizer's houses run at 30-90% of Census BPS, the Marion remainder's at 10-50%), so their
counts are floors and must not look like covered places. `build(raw, keep=None)` keeps every place.

**Privacy.** The file holds the street address, the geocoder's match and the coordinates. None of them is
requested (`FIELDS`).
"""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd

from lotline.io import DataStore
from lotline.io.arcgis import download_layer
from lotline.schemas import validate
from lotline.validation import holdout

ADAPTER = "states.or.mwvcog_permits"
VERSION = "1.0"
SOURCE = "mwvcog_permits"
TABLE = "permits"
LAYER_URL = (
    "https://services2.arcgis.com/89BLPQl3PdPQE7iy/arcgis/rest/services/Permits_online/FeatureServer/0"
)
LANDING_URL = "https://www.mwvcog.org/"
LICENSE = (
    "No license stated (Mid-Willamette Valley Council of Governments public ArcGIS Online layer "
    "'PermitsSince1998'; credit www.mwvcog.org)"
)
FIELDS = [
    "FID",
    "PERMIT",
    "VALUE",
    "Type",
    "DESC_",
    "UNITS",
    "QUARTER",
    "JURISD",
    "City",
    "YearNo",
    "UGB",
    "IN_OUT",
]
PERSONAL = {"ADDRESS", "Match_addr", "StAddr", "AddNum", "StName", "POINT_X", "POINT_Y", "ZIP"}
SALEM, KEIZER, TURNER = "4164900", "4138500", "4175150"
MARION, POLK = "41047", "41053"
CITIES = {
    "SALEM": SALEM,
    "KEIZER": KEIZER,
    "TURNER": TURNER,
    "MARION COUNTY": MARION,
    "MARION CO": MARION,
    "POLK COUNTY": POLK,
    "POLK CO": POLK,
}
OFFICES = {"SALEM": SALEM, "KEIZER": KEIZER, "TURNER": TURNER}  # JURISD values that name the place
# Only Salem's permits are complete in the file (new houses within 2% of Census BPS in most years to 2023);
# Keizer, Turner and the county remainders are partial, so `build` keeps Salem unless told otherwise.
KEEP = (SALEM,)
DEMO_TYPES = {"DEMO", "DEMOSF", "DEMODUP", "DEMOMF", "DEMOMH", "DEMOADU", "DEMODP"}
ONE_UNIT = {"NSFD", "ADU", "MH", "DEMOSF", "DEMOMH", "DEMOADU"}

PROVENANCE = {
    "title": (
        "Mid-Willamette Valley COG residential building permits since 1998 (Salem, Keizer, Marion, Polk)"
    ),
    "landing_url": LANDING_URL,
    "table": TABLE,
    "attribution": "Mid-Willamette Valley Council of Governments",
    "cleaning": [
        "Only FID, permit number, value, type, units, quarter, city, office, year and UGB flags are "
        "requested; "
        "addresses, geocoder fields and coordinates are not",
        "issue_date null and date_precision 'year' (the file has the year and quarter only)",
        "ADU = the COG's Type ADU (field flag); adu_type unknown",
        "Types: NSFD SFD; NDUP U2; MULT by units; MH OTHER; DEMO* demolitions with units_removed",
        "Jurisdiction from City (where the permit is), else from JURISD for self-permitting cities (Salem, "
        "Keizer, Turner); blank-City county permits and rows with neither are dropped",
        "Holdout filter applied (Oregon's V9 holdout, released 2026-11-05)",
    ],
    "limitations": [
        "No license and no restriction (terms checked 2026-11-10: the ArcGIS Online item "
        "a790b37ed6554a78957df0084f04b45b has an empty licenseInfo; Ben checked mwvcog.org by hand and found "
        "no terms of use); treated like Portland and Medford. Salem's counts are attributed to MWVCOG "
        "wherever they are shown",
        "Year and quarter only; no tax lot, so no parcel match",
        "Only Salem is kept: Keizer, Turner and the county remainders are partial in the file",
        "About 170 rows of 2024 have no city, office or permit number and are dropped: 2024 is incomplete",
        "Residential permits only (no alterations), so an ADU filed as an alteration may be missing",
    ],
}


def jurisdiction(city: pd.Series, office: pd.Series) -> pd.Series:
    """GEOID from the permit's city (`City`), else from the issuing office (`JURISD`) for self-permitting
    cities only; NA when neither says where the permit is."""
    c = city.astype("string").str.strip().str.upper().map(CITIES)
    o = office.astype("string").str.strip().str.upper().map(OFFICES)
    return c.fillna(o).astype("string")


def size_class(n) -> str:
    if pd.isna(n) or n < 2:
        return "UNKNOWN"
    return "U2" if n == 2 else "U3_4" if n <= 4 else "MF5"


def build(raw: pd.DataFrame, state: str = "OR", keep: tuple[str, ...] | None = KEEP) -> pd.DataFrame:
    df = raw.copy()
    juris = jurisdiction(df["City"], df["JURISD"])
    year = pd.to_numeric(df["YearNo"], errors="coerce").astype("Int64")
    build.unassigned = int((~juris.notna() & year.notna()).sum())  # type: ignore[attr-defined]
    rows = juris.notna() & year.notna()
    if keep is not None:
        rows &= juris.isin(list(keep)).fillna(False)
    df, juris, year = df[rows], juris[rows], year[rows]

    t = df["Type"].astype("string").str.strip().str.upper().fillna(df["DESC_"].astype("string").str.upper())
    units = pd.to_numeric(df["UNITS"], errors="coerce").astype("Int64")
    units = units.where(units >= 0)
    demo = t.isin(list(DEMO_TYPES)).fillna(False).astype(bool)
    btype = t.map({"NSFD": "SFD", "NDUP": "U2", "ADU": "ADU", "MH": "OTHER"}).astype("string")
    multi = t.eq("MULT").fillna(False).astype(bool)
    btype[multi] = [size_class(n) for n in units[multi]]
    btype[demo] = "OTHER"
    btype = btype.fillna("UNKNOWN")
    conf = pd.Series("high", index=df.index).where(btype != "UNKNOWN", "unknown")

    one = t.isin(list(ONE_UNIT)).fillna(False).astype(bool)
    units_new = units.copy()
    uconf = pd.Series("reported", index=df.index).where(units.notna(), "unknown")
    fill = one & units.isna()
    units_new[fill] = 1
    uconf[fill] = "derived"
    nd = t.eq("NDUP").fillna(False).astype(bool) & units.isna()
    units_new[nd] = 2
    uconf[nd] = "derived"
    units_removed = pd.Series(pd.NA, index=df.index, dtype="Int64")
    units_removed[demo] = units_new[demo]
    units_new[demo] = 0

    permit = df["PERMIT"].astype("string").str.strip()
    pid = permit.where(permit.notna() & (permit != ""), "FID-" + df["FID"].astype("string"))
    pid = pid.where(~pid.duplicated(keep=False), pid + "#" + df["FID"].astype("string"))
    out = pd.DataFrame(
        {
            "state": state,
            "permit_id": pid,
            "parcel_id": pd.Series(pd.NA, index=df.index, dtype="string"),
            "jurisdiction_geoid": juris,
            "issue_year": year,
            "issue_date": pd.Series(pd.NaT, index=df.index, dtype="datetime64[ns]"),
            "date_precision": "year",
            "building_type_std": btype,
            "type_confidence": conf,
            "adu_type": pd.Series("unknown", index=df.index, dtype="string").where(t.eq("ADU").fillna(False)),
            "permit_class_raw": t.fillna(""),
            "reform_flag_raw": "UGB=" + df["UGB"].astype("string").str.strip().fillna(""),
            "units_new": units_new.astype("Int64"),
            "units_removed": units_removed,
            "units_confidence": uconf,
            "is_demolition": demo.astype("boolean"),
            "is_conversion": pd.Series(pd.NA, index=df.index, dtype="boolean"),
            "valuation_usd": pd.to_numeric(df["VALUE"], errors="coerce").where(lambda s: s >= 0),
            "source": SOURCE,
        },
        index=df.index,
    )
    return out.sort_values("permit_id").reset_index(drop=True)


def download(store: DataStore, *, refresh: bool = False) -> pd.DataFrame:
    return download_layer(
        LAYER_URL,
        store=store,
        source=SOURCE,
        license=LICENSE,
        adapter=ADAPTER,
        adapter_version=VERSION,
        name="permits_since_1998",
        out_fields=",".join(FIELDS),
        refresh=refresh,
    )


def load(state: str, store: DataStore, *, refresh: bool = False, unblind: Iterable[str] = ()) -> pd.DataFrame:
    """Validated permits with Oregon's holdouts removed (by year: the file has no dates)."""
    df = build(download(store, refresh=refresh), state=state)
    df = holdout.apply(df, state, unblind=unblind, geoid_col="jurisdiction_geoid", year_col="issue_year")
    return validate(df, TABLE)
