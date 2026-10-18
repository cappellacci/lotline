"""City of Cincinnati building permits (Socrata `uhjb-xac9`, plus combo permits `thvx-5mem`) → `permits`.

The main dataset follows the BLDS permit standard: one row per permit, 2010 to the present, public domain.
Only the permits that can add or remove dwellings are downloaded, with a server-side filter: building
permits for new construction (`workclass` RNEW residential, CNEW commercial) and wrecking permits
(RDMO, CDMO). Excavation/fill, plumbing and HVAC permits for the same projects carry the same work class and
are left out, so a project is not counted once per trade.

**No Census code.** The city records the building-code use group (`proposeduse`), not the Census building
type, so the type comes from the use group and the unit count (`classify`):

| Use group | Meaning | Type |
|---|---|---|
| `1-2-3 FM`, `1-2-3`, `1-2-3 FA`, R-3, R-5 | 1-3 family dwellings (Residential Code of Ohio) | by `units` |
| R-2 | apartments | by `units` (usually MF5) |

By `units`: 1 SFD, 2 U2, 3-4 U3_4, 5+ MF5.
| anything else (R-1 hotels, B, M, S, A, ...) | not a dwelling building | OTHER, units unknown |

A one-unit permit is a single-family house, attached or detached: the city files each townhouse as its own
one-unit permit, and the data can't tell them apart, so 1-unit permits are SFD with `type_confidence`
"inferred" unless the combo permit's work description says townhouse (then TH, inferred). A 0 or blank unit
count is unknown (null), never 0.

**ADUs and townhouses from the combo permits.** The main dataset's `description` is only the work class text
("New Building"). The combo dataset repeats each permit once per plan-review item and has a real work
description (`desc_of_work`). Only combo rows whose description names an ADU, carriage house, garage
apartment or townhouse are downloaded (server-side `WHERE`); the text is parsed with
`lotline.parse.permit_text.parse_description` and never stored. A permit it calls an ADU becomes `ADU`
(1 unit, inferred), and permits named there are downloaded from the main dataset even when their work class is
not RNEW (e.g. a new garage with an ADU above).

**Demolitions.** Wrecking permits: `units_new` 0, `units_removed` from `units` for dwelling use groups
(reported; 0 or blank → unknown), unknown otherwise.

**Dates.** `issue_date` = `issueddate` (permits never issued are dropped), `application_date` = `applieddate`,
`final_date` = `coissueddate` (certificate of occupancy), else none.

Only non-personal fields are requested: no company names, addresses or links; the combo dataset's reviewer
names and plan-review comments are never requested.
"""

from __future__ import annotations

import pandas as pd

from lotline.io import DataStore
from lotline.io.socrata import download_dataset
from lotline.parse.permit_text import parse_description
from lotline.schemas import validate
from lotline.validation import holdout

ADAPTER = "states.oh.cincy_permits"
VERSION = "1.0"
SOURCE = "cincy_permits"
TABLE = "permits"
DOMAIN = "data.cincinnati-oh.gov"
DATASET = "uhjb-xac9"
COMBO_DATASET = "thvx-5mem"
LANDING_URL = (
    "https://data.cincinnati-oh.gov/Thriving-Healthy-Neighborhoods/Cincinnati-Building-Permits/uhjb-xac9"
)
LICENSE = "Public Domain (City of Cincinnati open data)"
CINCINNATI_GEOID = "3915000"

PERSONAL = {
    "companyname",
    "originaladdress1",
    "originalcity",
    "originalzip",
    "link",
    "entry_by",
    "location",
    "entry_comments",
}
SELECT = [
    "permitnum",
    "permittypemapped",
    "permitclass",
    "workclass",
    "statuscurrentmapped",
    "proposeduse",
    "units",
    "applieddate",
    "issueddate",
    "coissueddate",
    "totalsqft",
    "estprojectcostdec",
    "pin",
]
COMBO_SELECT = ["number_key", "sub_type_desc", "desc_of_work"]
NEW_CLASSES = ("RNEW", "CNEW")
DEMO_CLASSES = ("RDMO", "CDMO")
WHERE = (
    "(permittypemapped='Building' AND workclass IN ('RNEW','CNEW')) "
    "OR (permittypemapped='Wrecking' AND workclass IN ('RDMO','CDMO'))"
)
# Work-description words that make a combo row worth reading (ADUs and townhouses only).
COMBO_WORDS = ["ADU", "ACCESSORY DWELLING", "CARRIAGE", "GARAGE APARTMENT", "IN-LAW", "TOWNHO"]
COMBO_WHERE = " OR ".join(f"upper(desc_of_work) like '%{w}%'" for w in COMBO_WORDS)
DWELLING_USES = {"1-2-3 FM", "1-2-3", "1-2-3 FA", "R-3", "R-5", "R-2"}
DROP_STATUS = {"Permit Withdrawn", "VOIDED", "REVOKED", "DENIED", "W/REFUND"}

PROVENANCE = {
    "title": "City of Cincinnati Building Permits (BLDS, 2010 to present) and combo permits with plan review",
    "landing_url": LANDING_URL,
    "table": TABLE,
    "cleaning": [
        "Selected fields exclude company names, addresses and links; from the combo dataset only the permit "
        "number, sub-type and work description are requested (never reviewer names or review comments)",
        "Server-side filter: Building permits with work class RNEW/CNEW, Wrecking permits RDMO/CDMO; trade "
        "permits (plumbing, HVAC, excavation/fill) for the same projects are not downloaded",
        "Combo permits: only rows whose work description names an ADU, carriage house, garage apartment, "
        "in-law suite or townhouse; parsed with lotline.parse.permit_text, text never stored; those permit "
        "numbers are also downloaded from the main dataset whatever their work class",
        "Permits never issued, withdrawn, voided, revoked, denied or refunded are dropped",
        "building_type_std from the building-code use group and units: 1-2-3 family/R-3/R-5/R-2 by units "
        "(1 SFD inferred, 2 U2, 3-4 U3_4, 5+ MF5); other use groups OTHER with unknown units; 0 or blank "
        "units → unknown; the combo description turns a permit into ADU (1 unit) or TH, marked inferred",
        "Wrecking permits: is_demolition, units_new 0, units_removed = units for dwelling use groups",
        "final_date = coissueddate (certificate of occupancy)",
        "Every row is assigned to Cincinnati (3915000), the permit-issuing city",
        "Holdout filter applied (Ohio has no holdouts)",
    ],
    "limitations": [
        "No Census building-type code: 1-unit permits can't be split into detached and attached houses "
        "except where the combo description says townhouse; they are SFD, inferred",
        "Apartments inside mixed-use or commercial use groups (B, M, ...) are OTHER with unknown units",
        "ADUs are found only where the combo work description names one; an ADU described otherwise is "
        "missed",
        "units on wrecking permits is the building's units; commercial-use wrecking permits have unknown "
        "units removed",
        "The city revises records in place; each pull is a dated raw snapshot",
    ],
}


def _date(values: pd.Series) -> pd.Series:
    return pd.to_datetime(values, errors="coerce").dt.normalize().astype("datetime64[ns]")


def _use(values: pd.Series) -> pd.Series:
    """'"1-2-3 FM"' → '1-2-3 FM' (the city quotes the use group)."""
    return values.astype("string").str.strip().str.strip('"').str.strip()


def size_class(units) -> str | None:
    if pd.isna(units) or units <= 0:
        return None
    return "SFD" if units == 1 else "U2" if units == 2 else "U3_4" if units <= 4 else "MF5"


def classify(use, units, demo: bool) -> tuple[str, str, object, object, str]:
    """(building_type_std, type_confidence, units_new, units_removed, units_confidence) for one permit."""
    dwelling = pd.notna(use) and use in DWELLING_USES
    n = units if pd.notna(units) and units > 0 else pd.NA
    if not dwelling:
        return (
            "OTHER" if pd.notna(use) else "UNKNOWN",
            "high" if pd.notna(use) else "unknown",
            (0 if demo else pd.NA),
            pd.NA,
            "unknown",
        )
    btype = size_class(units)
    conf_t = "inferred" if btype == "SFD" else "high" if btype else "unknown"
    btype = btype or "UNKNOWN"
    conf_u = "reported" if pd.notna(n) else "unknown"
    if demo:
        return btype, conf_t, 0, n, conf_u
    return btype, conf_t, n, pd.NA, conf_u


def combo_facts(combo: pd.DataFrame) -> pd.DataFrame:
    """Per permit number: building type and ADU kind parsed from the combo descriptions (text not kept)."""
    if combo.empty:
        return pd.DataFrame(columns=["text_type", "text_adu_type"])
    text = combo.dropna(subset=["desc_of_work"]).drop_duplicates(["number_key", "desc_of_work"])
    joined = text.groupby("number_key")["desc_of_work"].agg(" . ".join)
    facts = joined.map(parse_description)
    return pd.DataFrame(
        {
            "text_type": facts.map(lambda f: f.building_type_std),
            "text_adu_type": facts.map(lambda f: f.adu_type),
        },
        index=joined.index,
    )


def build(raw: pd.DataFrame, combo: pd.DataFrame | None = None, state: str = "OH") -> pd.DataFrame:
    df = raw.copy()
    df["issue_date"] = _date(df["issueddate"])
    status = df["statuscurrentmapped"].astype("string").str.strip()
    df = df.loc[df["issue_date"].notna() & ~status.isin(DROP_STATUS).fillna(False).astype(bool)].copy()
    use = _use(df["proposeduse"])
    units = pd.to_numeric(df["units"], errors="coerce")
    wc = df["workclass"].astype("string").str.strip()
    demo = (
        df["permittypemapped"].astype("string").str.strip().eq("Wrecking") | wc.isin(DEMO_CLASSES)
    ).fillna(False)
    parts = pd.DataFrame(
        [classify(use.at[i], units.at[i], bool(demo.at[i])) for i in df.index],
        index=df.index,
        columns=["building_type_std", "type_confidence", "units_new", "units_removed", "units_confidence"],
    )
    parts["adu_type"] = pd.Series(pd.NA, index=df.index, dtype="string")
    facts = combo_facts(combo if combo is not None else pd.DataFrame(columns=["number_key", "desc_of_work"]))
    pid = df["permitnum"].astype("string").str.strip()
    text_type = pid.map(facts["text_type"]) if len(facts) else pd.Series(pd.NA, index=df.index)
    text_adu = pid.map(facts["text_adu_type"]) if len(facts) else pd.Series(pd.NA, index=df.index)
    is_adu = text_type.eq("ADU").fillna(False).astype(bool) & ~demo
    parts.loc[is_adu, ["building_type_std", "type_confidence", "units_new", "units_confidence"]] = [
        "ADU",
        "inferred",
        1,
        "inferred",
    ]
    parts.loc[is_adu, "adu_type"] = text_adu[is_adu].fillna("unknown")
    is_th = text_type.eq("TH").fillna(False).astype(bool) & parts["building_type_std"].eq("SFD") & ~demo
    parts.loc[is_th, ["building_type_std", "type_confidence"]] = ["TH", "inferred"]
    # Non-dwelling work classes downloaded only because the combo text named an ADU stay OTHER otherwise.
    extra = ~wc.isin(NEW_CLASSES + DEMO_CLASSES).fillna(False).astype(bool) & ~is_adu
    parts.loc[extra, ["building_type_std", "type_confidence", "units_new", "units_confidence"]] = [
        "OTHER",
        "high",
        pd.NA,
        "unknown",
    ]
    final = _date(df.get("coissueddate", pd.Series(pd.NA, index=df.index)))
    out = pd.DataFrame(
        {
            "state": state,
            "permit_id": pid,
            "parcel_id": df["pin"].astype("string").str.strip().str.strip('"').replace("", pd.NA),
            "jurisdiction_geoid": CINCINNATI_GEOID,
            "issue_year": df["issue_date"].dt.year.astype("Int64"),
            "issue_date": df["issue_date"],
            "date_precision": "day",
            "application_date": _date(df["applieddate"]),
            "final_date": final,
            "final_date_type": pd.Series("certificate_of_occupancy", index=df.index).where(final.notna()),
            "permit_class_raw": wc.fillna("") + "|" + use.fillna(""),
            "is_demolition": demo.astype("boolean"),
            "is_conversion": pd.Series(pd.NA, index=df.index, dtype="boolean"),
            "floor_area_sqft": pd.to_numeric(df["totalsqft"], errors="coerce").where(lambda s: s > 0),
            "valuation_usd": pd.to_numeric(df["estprojectcostdec"], errors="coerce").where(lambda s: s >= 0),
            "source": SOURCE,
        },
        index=df.index,
    ).join(parts)
    out["units_new"] = pd.to_numeric(out["units_new"], errors="coerce").astype("Int64")
    out["units_removed"] = pd.to_numeric(out["units_removed"], errors="coerce").astype("Int64")
    out = out.sort_values(["permit_id", "issue_date"]).drop_duplicates(["state", "permit_id"], keep="last")
    return out.reset_index(drop=True)


def download(store: DataStore, *, refresh: bool = False) -> tuple[pd.DataFrame, pd.DataFrame]:
    common = dict(store=store, source=SOURCE, license=LICENSE, adapter=ADAPTER, adapter_version=VERSION)
    combo = download_dataset(
        DOMAIN,
        COMBO_DATASET,
        select=COMBO_SELECT,
        where=COMBO_WHERE,
        name="combo_permits",
        refresh=refresh,
        **common,
    )
    keys = sorted(set(combo["number_key"].dropna().astype(str).str.strip()))
    where = WHERE
    if keys:
        where += " OR permitnum IN (" + ",".join(f"'{k}'" for k in keys) + ")"
    main = download_dataset(
        DOMAIN, DATASET, select=SELECT, where=where, name="building_permits", refresh=refresh, **common
    )
    return main, combo


def load(state: str, store: DataStore, *, refresh: bool = False) -> pd.DataFrame:
    main, combo = download(store, refresh=refresh)
    df = build(main, combo, state=state)
    df = holdout.apply(
        df, state, geoid_col="jurisdiction_geoid", date_col="issue_date", year_col="issue_year"
    )
    return validate(df, TABLE)
