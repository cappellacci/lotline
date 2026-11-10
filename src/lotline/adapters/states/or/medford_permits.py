"""City of Medford TRAKiT permit export (ArcGIS FeatureServer, 2020 to present) → `permits`.

Medford publishes its permit system's export (`TRAKiTExport/TRAKiTPermits_service`, layer 1, "Permits from
2020 to Present"), one row per permit, with the permit type and subtype, status, applied, issued and finaled
dates, the tax lot (`SITE_APN`, map and lot), the site city and a free-text description. Only building
permits that can add or remove homes are downloaded (server-side filter on `PermitType`, `TYPES`): residential
new, remodel and other permits, master (plan-set) permits, manufactured homes and demolitions. Trade, sign,
right-of-way and commercial permits are left out.

**ADUs.** Medford files an ADU under its own subtype, so this is a field flag, not text: a new-construction
permit (`PermitType` RESIDENTIAL NEW or "ADU REDUCED SDC MASTER") with `PermitSubType` ADU, "ADU REDUCED SDC"
(the city's reduced system development charge for ADUs) or "ADU REDUCED CITY LOT" → one ADU row. A remodel or
addition permit with an ADU subtype is work on an existing ADU (a fire repair, "ADD 200 FT TO ADU", the hand
check in the report found no new unit among them), so it is not an ADU (OTHER, 0 units). A new house and its
ADU on one permit ("SFR W/ ADU REDUCED SDC", "SFR WITH ADU", or the type "RESIDENTIAL NEW MASTER WITH ADU
REDUCED SDC") → **two rows**, the house (`#house`, SFD) and the ADU (`#adu`), as Portland's adapter does, so
D-041's co-built rule sees both. `adu_type` from the description by Cary's rule (`cary_permits.adu_from_text`)
when it names one, else unknown. "GUEST HOUSE WITHOUT KITCHEN" is not an ADU. "COTTAGE" is a cottage-cluster
home (middle housing), not an ADU: DTQ.

**Other types** (`SUBTYPES`): SFR, SFR ORIGINAL/ADDITIONAL, NEW CITY LOT, ORIGINAL, ADDITIONAL (master-plan
houses) → SFD; SFR ATTACHED, TOWNHOUSE → TH; DUPLEX → U2; manufactured homes → OTHER; demolitions →
`is_demolition`. `NO_UNITS` is mostly blank, so units are derived from the type (SFD, TH, ADU, DTQ 1; U2 2)
and reported where `NO_UNITS` is filled and fits. Alterations that create nothing (pools, decks, solar,
garages, sheds, reroofs ...) → OTHER with 0 units (derived).

**Rows kept.** Issued permits (an `ISSUED` date) whose status is not voided or withdrawn, in Medford
(`SITE_CITY` MEDFORD or blank). Medford also inspects some Central Point permits (317 rows), which are left
out. `final_date` = `FINALED`.

**Privacy.** The export holds owner, applicant and contractor names and the site address. None is requested
(`FIELDS`). The description is read in memory for the ADU type and never kept; it can contain a street
address.
"""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd

from lotline.adapters.states.nc.cary_permits import adu_from_text
from lotline.io import DataStore
from lotline.io.arcgis import download_layer, epoch_ms_to_timestamp
from lotline.schemas import validate
from lotline.validation import holdout

ADAPTER = "states.or.medford_permits"
VERSION = "1.0"
SOURCE = "medford_permits"
TABLE = "permits"
LAYER_URL = (
    "https://maps.medfordmaps.org/arcgis/rest/services/TRAKiTExport/TRAKiTPermits_service/FeatureServer/1"
)
LANDING_URL = "https://opendata-medford.hub.arcgis.com/"
LICENSE = (
    "No license stated (City of Medford public ArcGIS service; open data hub disclaimer: as is, no warranty)"
)
MEDFORD = "4147000"
FIELDS = [
    "OBJECTID",
    "PERMIT_NO",
    "PermitType",
    "PermitSubType",
    "STATUS",
    "APPLIED",
    "ISSUED",
    "FINALED",
    "SITE_APN",
    "SITE_CITY",
    "DESCRIPTION",
    "NO_UNITS",
    "BLDG_SF",
    "JOBVALUE",
]
PERSONAL = {
    "OWNER_NAME",
    "APPLICANT_NAME",
    "CONTRACTOR_NAME",
    "Taxlots_FEEOWNER",
    "SITE_ADDR",
    "SITE_NUMBER",
    "SITE_STREETNAME",
    "SITE_ST_NO",
    "Taxlots_SITEADD",
}
TYPES = (
    "RESIDENTIAL",
    "RESIDENTIAL NEW",
    "RESIDENTIAL NEW MASTER PERMIT",
    "RESIDENTIAL OTHER",
    "RESIDENTIAL REMODEL",
    "RESIDENTIAL REMODEL ",
    "RESIDENTIAL REMODEL ADD",
    "RESIDENTIAL NEW MASTER WITH ADU REDUCED SDC",
    "ADU REDUCED SDC MASTER",
    "RESIDENTIAL NEW DUPLEX MASTER PERMIT",
    "MANUFACTURED HOME",
    "DEMOLITION",
)
WHERE = "PermitType IN (" + ",".join("'" + t + "'" for t in TYPES) + ")"
DROP_STATUS = {"VOIDED", "WITHDRAWN"}
ADU_SUBTYPES = {"ADU", "ADU REDUCED SDC", "ADU REDUCED CITY LOT"}
HOUSE_AND_ADU = {"SFR W/ ADU REDUCED SDC", "SFR WITH ADU"}
SUBTYPES = {
    "SFR": "SFD",
    "SFR ORIGINAL": "SFD",
    "SFR ADDITIONAL": "SFD",
    "NEW  CITY LOT": "SFD",
    "NEW CITY LOT": "SFD",
    "ORIGINAL": "SFD",
    "ADDITIONAL": "SFD",
    "SFR ATTACHED": "TH",
    "TOWNHOUSE": "TH",
    "DUPLEX": "U2",
    "COTTAGE": "DTQ",
    "NEW IN PARK": "OTHER",
    "REPLACEMENT  IN PARK": "OTHER",
    "GARAGE OR CARPORT": "OTHER",
    "STORAGE SHEDS OVER 200 SQFT": "OTHER",
    "STRUCTURES OTHER THAN BUILDINGS": "OTHER",
    "GUEST HOUSE WITHOUT KITCHEN": "OTHER",
}
NEW_TYPES = {
    "RESIDENTIAL NEW",
    "RESIDENTIAL NEW MASTER PERMIT",
    "RESIDENTIAL NEW DUPLEX MASTER PERMIT",
    "RESIDENTIAL NEW MASTER WITH ADU REDUCED SDC",
    "ADU REDUCED SDC MASTER",
    "MANUFACTURED HOME",
}
UNITS = {"SFD": 1, "TH": 1, "ADU": 1, "DTQ": 1, "U2": 2, "OTHER": 0}
WORK_KIND = {"RESIDENTIAL REMODEL": True, "RESIDENTIAL REMODEL ADD": True}  # alterations (is_conversion)
MASTER_WITH_ADU = "RESIDENTIAL NEW MASTER WITH ADU REDUCED SDC"

PROVENANCE = {
    "title": "City of Medford TRAKiT permit export (permits from 2020 to present)",
    "landing_url": LANDING_URL,
    "table": TABLE,
    "attribution": "City of Medford, Oregon",
    "cleaning": [
        "Server-side filter: residential, master, manufactured-home and demolition permit types; owner, "
        "applicant and contractor names and site addresses are not requested",
        "Issued permits only; voided and withdrawn dropped; Medford site city only (Central Point rows "
        "left out)",
        "ADU = Medford's ADU subtypes on a new-construction permit (field flag); remodels of an existing "
        "ADU are not ADUs; a house + ADU permit (incl. master permits with ADU) becomes two rows (#house "
        "SFD, #adu ADU)",
        "adu_type from the description by Cary's ADU rule, else unknown; the description is not kept",
        "Types from the subtype: SFR SFD, SFR ATTACHED/TOWNHOUSE TH, DUPLEX U2, COTTAGE DTQ (cottage "
        "cluster), "
        "manufactured homes OTHER; non-dwelling work OTHER with 0 units; units derived from the type",
        "Holdout filter applied (Oregon's V9 holdout, released 2026-11-05)",
    ],
    "limitations": [
        "Starts in 2020: no history before SB 1051's first full years",
        "No license stated; terms are a no-warranty disclaimer",
        "NO_UNITS is mostly blank, so units are derived from the subtype",
    ],
}


def _date(values: pd.Series) -> pd.Series:
    return (
        epoch_ms_to_timestamp(pd.to_numeric(values, errors="coerce")).dt.normalize().astype("datetime64[ns]")
    )


def _s(values: pd.Series) -> pd.Series:
    return values.astype("string").str.strip().str.upper()


def build(raw: pd.DataFrame, state: str = "OR") -> pd.DataFrame:
    df = raw.copy()
    df["issue_date"] = _date(df["ISSUED"])
    city = _s(df["SITE_CITY"]).fillna("")
    status = _s(df["STATUS"]).fillna("")
    df = df[df["issue_date"].notna() & ~status.isin(DROP_STATUS) & city.isin(["MEDFORD", ""])].copy()
    df = df.sort_values("OBJECTID").drop_duplicates("PERMIT_NO", keep="first")

    ptype, sub = _s(df["PermitType"]).fillna(""), _s(df["PermitSubType"]).fillna("")
    text = df["DESCRIPTION"].astype("string").fillna("")
    demo = ptype.eq("DEMOLITION") | sub.str.startswith("DEMO")
    remodel = ptype.str.startswith("RESIDENTIAL REMODEL")
    both = sub.isin(HOUSE_AND_ADU) | ptype.eq(MASTER_WITH_ADU)
    is_adu = (sub.isin(ADU_SUBTYPES) | ptype.eq("ADU REDUCED SDC MASTER")) & ~remodel & ~both
    btype = sub.map(SUBTYPES).astype("string")
    btype[ptype.eq("MANUFACTURED HOME")] = "OTHER"
    btype[is_adu] = "ADU"
    btype[both] = "SFD"
    new = ptype.isin(NEW_TYPES)
    btype[btype.isna() & new] = "UNKNOWN"
    btype = btype.fillna("OTHER")  # alterations and accessory work that create no home
    btype[demo] = "OTHER"
    conf = pd.Series("high", index=df.index).where(btype != "UNKNOWN", "unknown")

    reported = pd.to_numeric(df["NO_UNITS"], errors="coerce").astype("Int64")
    derived = btype.map(UNITS).astype("Int64")
    units_new = derived.copy()
    uconf = pd.Series("derived", index=df.index).where(derived.notna(), "unknown")
    fits = reported.notna() & derived.notna() & (reported == derived) & (derived > 0)
    uconf[fits] = "reported"
    units_new[~new & ~is_adu & ~demo] = units_new[~new & ~is_adu & ~demo].clip(
        upper=0
    )  # alterations add none
    units_removed = pd.Series(pd.NA, index=df.index, dtype="Int64")
    units_new[demo] = 0
    uconf[demo] = "unknown"

    kind = text.map(adu_from_text).astype("string").fillna("unknown")
    conversion = pd.Series(pd.NA, index=df.index, dtype="boolean")
    conversion[ptype.isin(list(WORK_KIND))] = True
    conversion[new] = False

    final = _date(df["FINALED"])
    out = pd.DataFrame(
        {
            "state": state,
            "permit_id": df["PERMIT_NO"].astype("string").str.strip(),
            "parcel_id": df["SITE_APN"].astype("string").str.strip().replace("", pd.NA),
            "jurisdiction_geoid": MEDFORD,
            "issue_year": df["issue_date"].dt.year.astype("Int64"),
            "issue_date": df["issue_date"],
            "date_precision": "day",
            "application_date": _date(df["APPLIED"]),
            "final_date": final,
            "final_date_type": pd.Series("final_inspection", index=df.index).where(final.notna()),
            "building_type_std": btype,
            "type_confidence": conf,
            "adu_type": kind.where(is_adu),
            "permit_class_raw": ptype + "|" + sub,
            "reform_flag_raw": pd.Series(pd.NA, index=df.index, dtype="string"),
            "units_new": units_new,
            "units_removed": units_removed,
            "units_confidence": uconf,
            "is_demolition": demo.astype("boolean"),
            "is_conversion": conversion,
            "floor_area_sqft": pd.to_numeric(df["BLDG_SF"], errors="coerce").where(lambda s: s > 0),
            "valuation_usd": pd.to_numeric(df["JOBVALUE"], errors="coerce").where(lambda s: s >= 0),
            "source": SOURCE,
        },
        index=df.index,
    )
    # a new house and its ADU on one permit: two rows
    pair = out[both.to_numpy()]
    house = pair.assign(permit_id=pair["permit_id"] + "#house")
    adu = pair.assign(
        permit_id=pair["permit_id"] + "#adu",
        building_type_std="ADU",
        adu_type=kind[both].to_numpy(),
        units_new=1,
    )
    out = pd.concat([out[~both.to_numpy()], house, adu])
    out["units_new"] = out["units_new"].astype("Int64")
    return out.sort_values("permit_id").reset_index(drop=True)


def download(store: DataStore, *, refresh: bool = False) -> pd.DataFrame:
    return download_layer(
        LAYER_URL,
        store=store,
        source=SOURCE,
        license=LICENSE,
        adapter=ADAPTER,
        adapter_version=VERSION,
        name="trakit_permits",
        where=WHERE,
        out_fields=",".join(FIELDS),
        refresh=refresh,
    )


def load(state: str, store: DataStore, *, refresh: bool = False, unblind: Iterable[str] = ()) -> pd.DataFrame:
    """Validated permits with Oregon's holdouts removed."""
    df = build(download(store, refresh=refresh), state=state)
    df = holdout.apply(
        df,
        state,
        unblind=unblind,
        geoid_col="jurisdiction_geoid",
        date_col="issue_date",
        year_col="issue_year",
    )
    return validate(df, TABLE)
