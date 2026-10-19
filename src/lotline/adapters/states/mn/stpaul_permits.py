"""City of Saint Paul building permits → `permits` (St. Paul only, mid-2015 to mid-2025). Secondary source.

Source: City of Saint Paul open data, `Building_Permits_` feature layer. The layer was a **rolling 10-year
window**, so every fetch is written as a dated raw snapshot (the default vintage of `download_layer` is
today's date) and older snapshots are never overwritten. The layer's own metadata (`layer.json`,
`editingInfo`) says its data were last edited on 2025-07-01, so it has stopped rolling for now: it holds
permits issued from 2015-06-30. Met Council permits (`metc_permits`) stay the outcome source for St. Paul.

**V5 holdout.** St. Paul (2758000) outcomes 2024-2026 are hidden (V5-MN-STPAUL). `to_permits` converts issue
dates and calls `holdout.apply` before anything else is done with the rows; the raw snapshot keeps every row
for the day the test is unblinded, and nothing from 2024 on is ever opened, counted or summarized.

**What the layer can and can't say.** It has the permit type (`SUB_TYPE`: Single Family Dwelling,
2-Family/Duplex, Residential (Multi-Fam), Accessory Structure, Commercial, Institutional, Mixed) and the work
type (`WORK_TYPE`: New, Addition, Remodel, Repair, Express Repair), but **no unit counts and no ADU flag**.
Units are therefore derived only where the permit itself fixes them: a new single-family house adds 1 unit, a
new duplex 2, and a repair adds or removes none. Everything else (multifamily, mixed use, remodels, additions)
has unknown units (null). There are no demolition permits in the layer (all rows are "Building Permit").

**Personal data.** The layer carries the contractor's name and address and the street address. They are never
requested: `FIELDS` lists exactly what is read. `FOLDERDESCRIPTION` (the work description) is kept in the raw
snapshot for a later ADU reading, but it is free text that can name people, so it is never written to the
table.
"""

from __future__ import annotations

import httpx
import pandas as pd

from lotline.io import DataStore
from lotline.io.arcgis import download_layer, epoch_ms_to_timestamp
from lotline.schemas import validate
from lotline.validation import holdout

ADAPTER = "states.mn.stpaul_permits"
VERSION = "1.0"
SOURCE = "stpaul_permits"
TABLE = "permits"
LICENSE = "Public domain (City of Saint Paul item license; provided 'as is')"
LAYER_URL = (
    "https://services1.arcgis.com/9meaaHE3uiba0zr8/arcgis/rest/services/Building_Permits_/FeatureServer/0"
)
LANDING_URL = "https://www.arcgis.com/home/item.html?id=cb618c6b5f8f46b696674e74a3fb5b2d"

ST_PAUL = "2758000"  # place GEOID (state 27 + FIPS place 58000)
RAMSEY = "27123"  # county GEOID; St. Paul PINs are 12-digit Ramsey PINs
TIMEZONE = "America/Chicago"

# Exactly what is read. Never "*": ADDRESS, CONTRACTORNAME and CONTRACTORADDRESS are left out.
FIELDS = [
    "OBJECTID",
    "PERMITNUMBER",
    "PIN",
    "STATUS",
    "ISSUEDATE",
    "EXPIRATIONDATE",
    "FINALDATE",
    "FOLDER_TYPE",
    "SUB_TYPE",
    "WORK_TYPE",
    "FOLDERDESCRIPTION",
    "EST_VALUE_OF_WORK",
    "STATE_VALUATION",
    "LATITUE",
    "LONGITUTE",
]
PERSONAL = {"ADDRESS", "CONTRACTORNAME", "CONTRACTORADDRESS"}
FREE_TEXT = {"FOLDERDESCRIPTION"}  # raw snapshot only, never in the table

# SUB_TYPE → building_type_std. Multi-Fam can be 3-4 or 5+ units and Mixed may hold homes or not: no unit
# count says which, so both stay UNKNOWN rather than guessing a finer class.
SUB_TYPES = {
    "Single Family Dwelling": "SFD",
    "2-Family/Duplex": "U2",
    "Residential (Multi-Fam)": "UNKNOWN",
    "Mixed (Commercial/Residential)": "UNKNOWN",
    "Accessory Structure": "OTHER",
    "Commercial": "OTHER",
    "Institutional": "OTHER",
}
# Units fixed by the permit itself (new building of a known size); repairs change no units.
NEW_UNITS = {"Single Family Dwelling": 1, "2-Family/Duplex": 2}
REPAIR_WORK = {"Repair", "Express Repair"}

PROVENANCE = {
    "title": "City of Saint Paul Building Permits (mid-2015 to mid-2025)",
    "landing_url": LANDING_URL,
    "table": TABLE,
    "attribution": "City of Saint Paul, Department of Safety and Inspections (open data)",
    "cleaning": [
        f"Download the Building_Permits_ feature layer ({LAYER_URL}) with the ArcGIS pager into a dated "
        f"snapshot, requesting only {', '.join(FIELDS)}. Street address, contractor name and contractor "
        "address are never requested; the work description is kept in the raw snapshot only",
        "ISSUEDATE / FINALDATE (epoch ms, UTC) → local St. Paul calendar dates; issue_year from issue_date; "
        "date_precision=day; permits never issued are dropped",
        "Held-out place-years removed (validation/holdout.py: V5-MN-STPAUL hides 2024-2026) right after the "
        "dates are read, before any other step",
        "permit_id: 'stp-' + PERMITNUMBER; parcel_id: '27123' (Ramsey) + the 12-digit PIN, else null",
        "building_type_std from SUB_TYPE: Single Family Dwelling→SFD, 2-Family/Duplex→U2, Accessory "
        "Structure, Commercial and Institutional→OTHER, Residential (Multi-Fam) and Mixed→UNKNOWN",
        "Units (derived): a New single-family permit adds 1, a New duplex 2; Repair and Express Repair add "
        "and remove 0; everything else null (unknown)",
        "final_date = FINALDATE for Finaled permits, final_date_type=final_inspection",
        "valuation_usd = STATE_VALUATION (the building valuation the permit fee is set on)",
        "permit_class_raw = SUB_TYPE:WORK_TYPE:STATUS",
    ],
    "limitations": [
        "No unit counts and no ADU flag: units are known only for new single-family houses and duplexes; "
        "use Met Council permits for St. Paul outcomes",
        "Rolling 10-year window: permits issued before 2015-06-30 had already dropped out at the first "
        "snapshot (2026-10-19); the layer was last edited on 2025-07-01 (layer metadata)",
        "No demolition or wrecking permits in the layer",
        "Multifamily and mixed-use permits can't be sized (UNKNOWN), so DTQ vs MF5 can't be told apart here",
        "St. Paul permits from 2024 on are held out (V5 blind test) and absent from the table",
        "About 1% of pre-2024 permits have no PIN",
    ],
}


def load(
    state: str, store: DataStore, *, refresh: bool = False, http: httpx.Client | None = None
) -> pd.DataFrame:
    if state.upper() != "MN":
        raise ValueError(f"{SOURCE} covers St. Paul, Minnesota only, not {state}")
    raw = download_layer(
        LAYER_URL,
        store=store,
        source=SOURCE,
        license=LICENSE,
        adapter=ADAPTER,
        adapter_version=VERSION,
        name="building_permits",
        out_fields=",".join(FIELDS),
        refresh=refresh,
        http=http,
    )
    return to_permits(raw)


def to_permits(raw: pd.DataFrame, state: str = "MN") -> pd.DataFrame:
    """Raw layer attributes → validated `permits`, holdouts removed first."""
    raw = raw.drop(columns=[c for c in raw.columns if c in PERSONAL | FREE_TEXT])
    issued = _local_date(raw["ISSUEDATE"])
    raw = raw.assign(jurisdiction_geoid=ST_PAUL, issue_date=issued, issue_year=issued.dt.year.astype("Int64"))
    # Before any other step: no held-out row is looked at, counted or carried further.
    raw = holdout.apply(
        raw, state, geoid_col="jurisdiction_geoid", date_col="issue_date", year_col="issue_year"
    )
    raw = raw[raw["issue_date"].notna()]

    sub = raw["SUB_TYPE"].astype("string").str.strip()
    work = raw["WORK_TYPE"].astype("string").str.strip()
    status = raw["STATUS"].astype("string").str.strip()
    btype = sub.map(SUB_TYPES).fillna("UNKNOWN")

    new_building = (work == "New").fillna(False)
    repair = work.isin(REPAIR_WORK).fillna(False)
    sized = new_building & sub.isin(NEW_UNITS.keys()).fillna(False)
    null = pd.Series(pd.NA, index=raw.index, dtype="Int64")
    units_new = null.mask(sized, sub.map(NEW_UNITS)).mask(repair, 0).astype("Int64")
    units_removed = null.mask(sized | repair, 0).astype("Int64")
    known = sized | repair

    finaled = status == "Finaled"
    final = _local_date(raw["FINALDATE"]).where(finaled.fillna(False))

    df = pd.DataFrame(
        {
            "state": state,
            "permit_id": "stp-" + raw["PERMITNUMBER"].astype("string").str.strip(),
            "parcel_id": clean_pin(raw["PIN"]),
            "jurisdiction_geoid": raw["jurisdiction_geoid"],
            "issue_year": raw["issue_year"],
            "issue_date": raw["issue_date"],
            "date_precision": "day",
            "final_date": final,
            "final_date_type": pd.Series(pd.NA, index=raw.index, dtype="string").mask(
                final.notna(), "final_inspection"
            ),
            "building_type_std": btype,
            "type_confidence": btype.map(lambda b: "unknown" if b == "UNKNOWN" else "high"),
            "permit_class_raw": sub.fillna("") + ":" + work.fillna("") + ":" + status.fillna(""),
            "units_new": units_new,
            "units_removed": units_removed,
            "units_confidence": pd.Series("unknown", index=raw.index).mask(known, "derived"),
            "is_demolition": pd.Series(pd.NA, index=raw.index, dtype="boolean"),
            "is_conversion": pd.Series(pd.NA, index=raw.index, dtype="boolean"),
            "valuation_usd": pd.to_numeric(raw["STATE_VALUATION"], errors="coerce").astype(float),
            "source": SOURCE,
        }
    )
    return validate(df.reset_index(drop=True), TABLE)


def clean_pin(pin: pd.Series) -> pd.Series:
    """'27123' + the 12-digit Ramsey PIN; anything else (blank, all zeros, wrong length) → null."""
    digits = pin.astype("string").str.replace(r"\D", "", regex=True)
    ok = digits.str.fullmatch(r"\d{12}").fillna(False) & ~digits.str.fullmatch(r"0+").fillna(True)
    return (RAMSEY + digits).where(ok).astype("string")


def _local_date(epoch_ms: pd.Series) -> pd.Series:
    """Epoch milliseconds (UTC) → the calendar date in St. Paul."""
    utc = epoch_ms_to_timestamp(epoch_ms)
    return utc.dt.tz_localize("UTC").dt.tz_convert(TIMEZONE).dt.tz_localize(None).dt.normalize()
