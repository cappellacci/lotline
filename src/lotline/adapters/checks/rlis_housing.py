"""Metro RLIS Housing inventory (ADU rows) and Portland's flag undercount k (D-074 step 1 for Oregon).

The inventory (`Housing/FeatureServer/11`, Metro Data Resource Center, updated quarterly) lists every housing
unit in Multnomah, Washington and Clackamas counties: one row per tax lot and unit type, with the unit count,
`UNIT_TYPE` (ADU, DETACHED, DUPLEXES ...) and the `DATASOURCE` each row was built from (county assessors, RLIS
tax lots, Metro's Master Address File, field checks, city permits ...). Only the ADU rows are downloaded
(server-side `UNIT_TYPE = 'ADU'`), and only non-personal fields: no site address, city or ZIP (`PERSONAL`).

It is a cross-section (the stock on the update date), not a dated roll, so it does not enter `parcels`. It is
used as the independent list R in the k comparison (rule in `reports/or/adu-coverage-and-undercount.md` §2.2):

- R = Portland ADU rows whose `DATASOURCE` is not permit-based (`PERMIT_SOURCES`), one per tax lot;
- P = tax lots of Portland ADU-flagged permits issued in the window;
- (a) = lots in R \\ P with an unflagged new-unit permit (central: house types only, `HOUSE_TYPES`);
- (b) = the rest of R \\ P.

Tax lots are matched by `taxlot_key` (map and lot number). k and the Chapman check reuse NC's pure functions
(`lotline.adapters.states.nc.wake_roll_diff`).
"""

from __future__ import annotations

import re

import pandas as pd

from lotline.adapters.states.nc import wake_roll_diff as wd
from lotline.io import DataStore
from lotline.io.arcgis import download_layer

ADAPTER = "checks.rlis_housing"
VERSION = "1.0"
SOURCE = "rlis_housing"
LAYER_URL = "https://services2.arcgis.com/McQ0OlIABe29rJJy/arcgis/rest/services/Housing/FeatureServer/11"
LANDING_URL = "https://gis.oregonmetro.gov/rlis-metadata/#/details/3783"
LICENSE = (
    "RLIS Open Database End User License Agreement (Metro): attribution only; "
    "https://rlisdiscovery.oregonmetro.gov/pages/open-database-license"
)
FIELDS = [
    "FID",
    "TLID",
    "YEARBUILT",
    "JURIS_CITY",
    "UNITS",
    "UNIT_TYPE",
    "UNIT_SUBTY",
    "DATASOURCE",
    "CONFIDENCE",
    "COUNTY",
]
PERSONAL = {"SITEADDR", "SITECITY", "SITEZIP", "COMMONNAME"}
WHERE = "UNIT_TYPE = 'ADU'"
PERMIT_SOURCES = {"City of Portland Building Permits", "METRO - Building permit data"}
ADU_STUDY = "METRO - Accesory Dwelling Unit Study"  # the source's spelling
HOUSE_TYPES = {"SFD", "TH", "OTHER", "UNKNOWN"}  # group (a), central: not U2, U3_4, MF5

PROVENANCE = {
    "title": "Metro RLIS Housing inventory (ADU rows)",
    "landing_url": LANDING_URL,
    "table": "none (check only: the independent list in Portland's k comparison)",
    "attribution": "Metro Regional Land Information System (RLIS), Metro Data Resource Center",
    "cleaning": [
        "Server-side filter UNIT_TYPE = 'ADU'; site address, city, ZIP and common name are not requested",
        "Tax lots keyed as MAP-LOT (taxlot_key); rows whose TLID doesn't fit are dropped and counted",
        "Used only as the independent list in Portland's k comparison; not written to a processed table",
    ],
    "limitations": [
        "A cross-section dated by Metro's update, not a roll: ADUs that were removed are not in it",
        "Not fully independent of permits: the Master Address File gains addresses when permits are issued",
        "YEARBUILT is sometimes the main house's year, so it can't date the ADU",
    ],
}

KEY = re.compile(r"^(\d[NS]\d[EW]\d{2}[A-D]{0,2})0*(\d+[A-Z0-9]*)$")


def taxlot_key(values: pd.Series) -> pd.Series:
    """Map-and-taxlot numbers → `MAP-LOT` (`1S2E22BA  -03305` and `1S2E22BA 3305` → `1S2E22BA-3305`); NA if
    the value doesn't fit (township, range, section, up to two quarter letters, then the lot number)."""
    s = values.astype("string").str.upper().str.replace(r"[\s\-]", "", regex=True)
    m = s.str.extract(KEY)
    return (m[0] + "-" + m[1]).astype("string")


def download(store: DataStore, *, refresh: bool = False) -> pd.DataFrame:
    return download_layer(
        LAYER_URL,
        store=store,
        source=SOURCE,
        license=LICENSE,
        adapter=ADAPTER,
        adapter_version=VERSION,
        name="housing_adu",
        where=WHERE,
        out_fields=",".join(FIELDS),
        refresh=refresh,
    )


def independent_lots(
    housing: pd.DataFrame,
    *,
    city: str = "Portland",
    drop_study: bool = False,
    high_only: bool = False,
    built_from: int | None = None,
) -> pd.Index:
    """R: tax-lot keys of `city`'s ADU rows built from sources other than permits (rule §2.2); the city name
    is compared in upper case."""
    h = housing[(housing["UNIT_TYPE"] == "ADU") & (housing["JURIS_CITY"].str.upper() == city.upper())]
    h = h[~h["DATASOURCE"].isin(PERMIT_SOURCES)]
    if drop_study:
        h = h[h["DATASOURCE"] != ADU_STUDY]
    if high_only:
        h = h[h["CONFIDENCE"] == "HIGH"]
    if built_from is not None:
        h = h[pd.to_numeric(h["YEARBUILT"], errors="coerce") >= built_from]
    return pd.Index(taxlot_key(h["TLID"]).dropna().unique())


def compare(
    r_lots: pd.Index, permits: pd.DataFrame, first_year: int = 1995, last_year: int = 2025
) -> dict[str, float]:
    """R vs Portland permits (canonical `permits` rows, Portland only), by tax lot, issue years inclusive.

    Returns |R|, |P|, |P∩R|, |a| central and as written, |b|, |P\\R|, k (central and as written, each with
    its 90% interval) and the Chapman total with its 95% interval."""
    w = permits[permits["issue_year"].between(first_year, last_year)].assign(
        key=taxlot_key(permits["parcel_id"])
    )
    w = w.dropna(subset=["key"])
    flagged = w["adu_type"].notna()
    p = set(w.loc[flagged, "key"])
    unflagged = w.loc[~flagged]
    any_permit = set(unflagged["key"])
    house_permit = set(unflagged.loc[unflagged["building_type_std"].isin(HOUSE_TYPES), "key"])
    r = set(r_lots)
    both = len(p & r)
    rest = r - p
    a_central, a_written = len(rest & house_permit), len(rest & any_permit)
    k, k_lo, k_hi = wd.k_undercount(both, a_central)
    kw, kw_lo, kw_hi = wd.k_undercount(both, a_written)
    n, n_lo, n_hi = wd.chapman(len(r), len(p), both)
    return {
        "R": len(r),
        "P": len(p),
        "both": both,
        "a_central": a_central,
        "a_as_written": a_written,
        "b": len(rest) - a_written,
        "permits_only": len(p - r),
        "k": k,
        "k_lo90": k_lo,
        "k_hi90": k_hi,
        "k_as_written": kw,
        "k_as_written_lo90": kw_lo,
        "k_as_written_hi90": kw_hi,
        "chapman": n,
        "chapman_lo95": n_lo,
        "chapman_hi95": n_hi,
    }
