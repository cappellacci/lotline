"""City of Columbus building permits (Building & Zoning Services, ArcGIS FeatureServer) → canonical `permits`.

One row per issued permit, 2010 to the present, refreshed nightly, released under CC0. The layer is the city's
Accela permit table (about 685,000 permits on 2026-10-15, most of them mechanical, electrical, plumbing and
repair permits). Only the permits that can add or remove dwellings are downloaded, with a server-side filter
(`WHERE`): new-structure building permits (`GENERAL_TYPE` "... - New Structure") and demolitions.

Trade and partial permits for a new building (electrical, plumbing, fire alarm, foundation only, advance
start) carry the project's Census code and often its unit count, so counting every permit with code 105 would
count one apartment building several times. Only the new-structure building permit counts as new dwellings.

**Building type** comes from `CONST_TYPE_CODE`, the Census Building Permits Survey (BPS) type code the city
assigns to each permit; `VALUE_DESC` holds the BPS label for the same code (101 "Single Family Houses
Detached", 102 "Single Family Houses Attached", 103 "Two Family Buildings", 104 "Three and Four Family
Buildings", 105 "Five or More Family Buildings", 106 manufactured home, 645-649 demolitions). Codes in the
300s and 400s are nonresidential buildings and additions/alterations: `OTHER`, units unknown.

**Units.** `UNITS` is kept where it fits the type code; otherwise the code supplies the count (`units_for`):

| Code | Plausible reported units | Derived when reported is missing or implausible |
|---|---|---|
| 101 SFD, 106 manufactured | 1 | 1 |
| 102 townhouse | 1 or more (a permit can cover a whole row) | 1 |
| 103 duplex | 2 | 2 |
| 104 three-or-four family | 3 or 4 | unknown (null) |
| 105 five-or-more family | 5 or more | unknown (null) |

Demolitions (645-649 or a "Demolition" permit type) get `units_new = 0` and `units_removed` from `UNITS` where
it fits the code, else from the code (645 → 1, 646 → 2); 649 (nonresidential) leaves units removed unknown.

**ADUs from the Franklin County Auditor's permit file.** The layer has no ADU flag and no work description,
and the city files most ADUs (carriage houses) as new single-family houses (code 101) or as additions and
alterations (434). The auditor's permit file carries the same permit numbers with the city's work description,
and `franklin_permits.adu_flags` reads ADUs from it with named rules. Every flagged permit number is also
downloaded from this layer (`B1_ALT_ID IN (...)`, whatever its type), and a permit whose number matches a
flag (and, for an all-digit legacy number, its parcel too) becomes `ADU` (1 unit, inferred; `adu_type` from
the flag). MEP (trade) permits are never relabelled, and a permit downloaded only because of a flag (outside
`WHERE`) stays out unless relabelled. A flag whose permit number is not in the layer (2015 permits under
legacy numbers) is not added. See PROVENANCE.

Only non-personal fields are requested: no applicant names, business names, site address, ZIP or
permit-portal links.
"""

from __future__ import annotations

import pandas as pd

from lotline.io import DataStore
from lotline.io.arcgis import download_layer, epoch_ms_to_timestamp
from lotline.schemas import validate
from lotline.validation import holdout

ADAPTER = "states.oh.columbus_permits"
VERSION = "1.0"
SOURCE = "columbus_permits"
TABLE = "permits"
LAYER_URL = (
    "https://services1.arcgis.com/9yy6msODkIBzkUXU/arcgis/rest/services/Building_Permits/FeatureServer/0"
)
LANDING_URL = "https://www.arcgis.com/home/item.html?id=f7a785b863454d96a0fe3f5aa5368e7d"
LICENSE = "CC0-1.0 (City of Columbus open data)"
COLUMBUS_GEOID = "3918000"  # Census place GEOID of the permit-issuing city

PERSONAL = {"APPLICANT_BUS_NAME", "APPLICANT_FULL_NAME", "SITE_ADDRESS", "B1_SITUS_ZIP", "ACA_URL"}
OUT_FIELDS = [
    "OBJECTID",
    "B1_ALT_ID",
    "B1_PER_TYPE",
    "B1_PER_SUB_TYPE",
    "B1_PER_CATEGORY",
    "GENERAL_TYPE",
    "B1_PARCEL_NBR",
    "PERMIT_STATUS",
    "B1_APPL_STATUS",
    "SQFT",
    "G3_VALUE_TTL",
    "ISSUED_YEAR",
    "ISSUED_DT",
    "LAST_STATUS_DT",
    "CONST_TYPE_CODE",
    "VALUE_DESC",
    "UNITS",
]

# Census BPS building-type code -> (building_type_std, units per permit when derivable)
NEW_CODES: dict[str, tuple[str, int | None]] = {
    "101": ("SFD", 1),
    "102": ("TH", 1),
    "103": ("U2", 2),
    "104": ("U3_4", None),
    "105": ("MF5", None),
    "106": ("OTHER", 1),  # manufactured home: BPS excludes these, so they stay out of BPS-comparable types
}
DEMOLITION_CODES: dict[str, tuple[str, int | None]] = {
    "645": ("SFD", 1),
    "646": ("U2", 2),
    "647": ("U3_4", None),
    "648": ("MF5", None),
    "649": ("OTHER", None),  # all other buildings: no dwelling count can be read from the code
}
# The building permit for a new structure carries GENERAL_TYPE "<type> - New Structure". Trade and partial
# permits for the same project (electrical, plumbing, fire alarm, foundation-only, advance start) carry the
# project's Census code and often its unit count too, so a code alone never makes a permit a new dwelling.
NEW_STRUCTURE_SUFFIX = "New Structure"
# Server-side filter: new-structure and demolition permits only.
_DEMO_CODES = ",".join(f"'{c}'" for c in DEMOLITION_CODES)
WHERE = (
    f"GENERAL_TYPE LIKE '%{NEW_STRUCTURE_SUFFIX}' OR GENERAL_TYPE LIKE '%Demolition' "
    f"OR CONST_TYPE_CODE IN ({_DEMO_CODES})"
)
PLAUSIBLE = {
    "SFD": (1, 1),
    "TH": (1, None),
    "U2": (2, 2),
    "U3_4": (3, 4),
    "MF5": (5, None),
    "OTHER": (1, 1),  # only reached for manufactured homes (106)
}
# Application statuses that mean the permit was never validly issued (voided or withdrawn records).
DROP_STATUS_PREFIXES = ("void", "withdrawn")
FINAL_STATUS = {
    "certificate of occupancy issued": "certificate_of_occupancy",
    "final inspection approved": "final_inspection",
}

PROVENANCE = {
    "title": "City of Columbus Building Permits (Building & Zoning Services, nightly, 2010 to present)",
    "landing_url": LANDING_URL,
    "table": TABLE,
    "cleaning": [
        "Requested fields exclude applicant and business names, site address, ZIP and permit-portal links "
        "(no personal data); the layer has no free-text description field",
        "Server-side filter keeps only new-structure and demolition permits: GENERAL_TYPE '... - New "
        "Structure' or '... - Demolition', or CONST_TYPE_CODE 645-649 (29,183 of about 685,000 permits on "
        "2026-10-15); trade, partial (foundation-only, advance-start), repair and alteration permits are not "
        "downloaded because they repeat the project's Census code and unit count",
        "Permits without an issued date, and voided or withdrawn applications (B1_APPL_STATUS 'VOID ...', "
        "'Void ...', 'Withdrawn'), are dropped; expired permits are kept (BPS counts permits when issued)",
        "building_type_std from the Census BPS code in CONST_TYPE_CODE (101 SFD, 102 TH, 103 U2, 104 U3_4, "
        "105 MF5, 106 manufactured → OTHER); 3xx/4xx codes (nonresidential, additions, alterations) → OTHER "
        "with unknown units; a missing code → UNKNOWN",
        "Units: UNITS is kept only where it fits the code (1 for SFD/manufactured, 1+ for townhouse, 2 for "
        "duplex, 3-4 for 104, 5+ for 105); otherwise SFD/TH/manufactured → 1 and duplex → 2 "
        "(units_confidence=derived); 104 and 105 without a plausible count stay null",
        "Demolitions (645-649 or a Demolition permit type): is_demolition, units_new 0, units_removed from "
        "UNITS where it fits the code, else 645 → 1, 646 → 2; 649 and nonresidential demolitions unknown",
        "final_date is LAST_STATUS_DT when the status is 'Certificate of Occupancy Issued' or 'Final "
        "Inspection Approved' (a proxy: the date of the last status change)",
        "ADUs: permit numbers flagged by franklin_permits.adu_flags (Franklin County Auditor permit file, "
        "work descriptions) are also downloaded; a match on permit number (and parcel, for all-digit "
        "numbers) that is not an MEP permit becomes ADU (1 unit, inferred, adu_type from the flag)",
        "CONST_TYPE_CODE and GENERAL_TYPE copied to permit_class_raw",
        "Every row is assigned to Columbus (3918000), the permit-issuing city",
        "Holdout filter applied (Ohio has no holdouts; called for uniformity)",
    ],
    "limitations": [
        "ADUs are known only where the auditor's file has the permit and its description names the ADU "
        "(franklin_permits rules); flags under legacy permit numbers that the layer lacks (2015) are not "
        "added, so ADU counts before 2016 are low",
        "Five-or-more and three-or-four family permits without a plausible UNITS value have unknown units "
        "(null), not zero",
        "Nonresidential new buildings (3xx codes) often carry a UNITS value (e.g. mixed-use or hotel rooms); "
        "these are not counted as dwellings, matching the BPS, which classifies a building by its main use",
        "Conversions that add units inside existing buildings are not visible: alteration permits outside "
        "the filter are not downloaded, and 434 (residential additions/alterations) permits that fall inside "
        "it are OTHER with unknown units, because UNITS there holds the building's units, not units added",
        "final_date is the last status-change date, not a dated CO field",
        "UNITS is sometimes the whole project's count repeated on each building's permit (e.g. nine 2023 "
        "permits on one parcel each report the same 198-unit total) or a typo (a 2012 townhouse permit with "
        "433 units on 2,274 sq ft); these are kept as reported, so single years can exceed the Census BPS",
        "Pre-2010 permits are in separate 'Historic Building Permits' services, not loaded",
        "The city revises records in place (status changes); each pull is a dated raw snapshot",
    ],
}


def _dates(values: pd.Series) -> pd.Series:
    """ArcGIS epoch ms → day-precision timestamps in the schema's datetime64[ns]."""
    ms = pd.to_numeric(values, errors="coerce").astype("float64")
    return epoch_ms_to_timestamp(ms).dt.normalize().astype("datetime64[ns]")


def _text(values: pd.Series) -> pd.Series:
    return values.astype("string").str.strip().replace("", pd.NA)


def units_for(btype: str, reported, derived) -> tuple[object, str]:
    """(units, units_confidence): reported if it fits the type's plausible range, else derived, else null."""
    lo, hi = PLAUSIBLE.get(btype, (1, None))
    if pd.notna(reported) and lo <= reported and (hi is None or reported <= hi):
        return int(reported), "reported"
    if derived is not None:
        return int(derived), "derived"
    return pd.NA, "unknown"


def classify(code, general_type) -> tuple[str, str, int | None, bool]:
    """(building_type_std, type_confidence, derived units, is_demolition) for one permit."""
    is_demo = code in DEMOLITION_CODES or (pd.notna(general_type) and general_type.endswith("Demolition"))
    if code in DEMOLITION_CODES:
        btype, derived = DEMOLITION_CODES[code]
        return btype, "high", derived, True
    if is_demo:  # a demolition permit without a demolition code: units removed unknown
        return ("OTHER", "high", None, True) if pd.notna(code) else ("UNKNOWN", "unknown", None, True)
    new_structure = pd.notna(general_type) and general_type.endswith(NEW_STRUCTURE_SUFFIX)
    if code in NEW_CODES and new_structure:
        btype, derived = NEW_CODES[code]
        return btype, "high", derived, False
    if pd.notna(code) and code not in ("", "000", "025"):  # 000 "NA", 025 "Expired Permits"
        return "OTHER", "high", None, False
    return "UNKNOWN", "unknown", None, False


def _parcel_digits(values: pd.Series) -> pd.Series:
    """'010-191395-00' and '010191395' → '010191395' (district + parcel number)."""
    return values.astype("string").str.replace(r"\D", "", regex=True).str[:9].replace("", pd.NA)


def build(raw: pd.DataFrame, state: str = "OH", adu: pd.DataFrame | None = None) -> pd.DataFrame:
    """Raw layer attributes → canonical permits rows (before the holdout filter).

    `adu`: flags from `franklin_permits.adu_flags` (permit_no, parcel, adu_type); None leaves ADUs unknown.
    """
    df = raw.copy()
    df["issue_date"] = _dates(df["ISSUED_DT"])
    status = _text(df["B1_APPL_STATUS"]).str.lower()
    void = status.str.startswith(DROP_STATUS_PREFIXES).fillna(False).astype(bool)
    df = df.loc[df["issue_date"].notna() & ~void].copy()
    code = _text(df["CONST_TYPE_CODE"])
    general = _text(df["GENERAL_TYPE"])
    reported = pd.to_numeric(df["UNITS"], errors="coerce")

    rows = []
    for i in df.index:
        c = code.at[i]
        btype, conf_t, derived, is_demo = classify(None if pd.isna(c) else c, general.at[i])
        if is_demo:
            if btype in PLAUSIBLE and btype != "OTHER":
                removed, conf_u = units_for(btype, reported.at[i], derived)
            else:
                removed, conf_u = pd.NA, "unknown"
            rows.append((btype, conf_t, 0, removed, conf_u, True))
        elif derived is not None or btype in ("U3_4", "MF5"):  # new dwellings (incl. manufactured homes)
            units, conf_u = units_for(btype, reported.at[i], derived)
            rows.append((btype, conf_t, units, pd.NA, conf_u, False))
        else:  # nonresidential or alteration: UNITS is not a count of new dwellings
            rows.append((btype, conf_t, pd.NA, pd.NA, "unknown", False))
    parts = pd.DataFrame(
        rows,
        index=df.index,
        columns=[
            "building_type_std",
            "type_confidence",
            "units_new",
            "units_removed",
            "units_confidence",
            "is_demolition",
        ],
    )
    final_type = _text(df["PERMIT_STATUS"]).str.lower().map(FINAL_STATUS).astype("string")
    last_status = _dates(df["LAST_STATUS_DT"])
    out = pd.DataFrame(
        {
            "state": state,
            "permit_id": _text(df["B1_ALT_ID"]),
            "parcel_id": _text(df["B1_PARCEL_NBR"]),
            "jurisdiction_geoid": COLUMBUS_GEOID,
            "issue_year": df["issue_date"].dt.year.astype("Int64"),
            "issue_date": df["issue_date"],
            "date_precision": "day",
            "final_date": last_status.where(final_type.notna()),
            "final_date_type": final_type,
            "adu_type": pd.Series(pd.NA, index=df.index, dtype="string"),
            "permit_class_raw": code.fillna("") + "|" + general.fillna(""),
            "is_conversion": pd.Series(pd.NA, index=df.index, dtype="boolean"),
            "floor_area_sqft": pd.to_numeric(df["SQFT"], errors="coerce").where(lambda s: s > 0),
            "valuation_usd": pd.to_numeric(df["G3_VALUE_TTL"], errors="coerce").where(lambda s: s >= 0),
            "source": SOURCE,
        },
        index=df.index,
    ).join(parts)
    out["units_new"] = out["units_new"].astype("Int64")
    out["units_removed"] = out["units_removed"].astype("Int64")
    out["is_demolition"] = out["is_demolition"].astype("boolean")
    is_adu = pd.Series(False, index=out.index)
    if adu is not None and len(adu):
        flags = (
            adu.assign(digits=_parcel_digits(adu["parcel"]))
            .drop_duplicates("permit_no")
            .set_index("permit_no")
        )
        hit = out["permit_id"].map(flags["digits"])
        parcel = _parcel_digits(out["parcel_id"])
        mep = _text(df["B1_PER_SUB_TYPE"]).eq("MEP").fillna(False).astype(bool)
        # All-digit legacy numbers can repeat across offices, so they must also match the parcel; lettered
        # Columbus numbers (NEWR2006425) are unique, and their parcel may differ after a split or combination.
        lettered = out["permit_id"].str.contains(r"[A-Za-z]", regex=True).fillna(False).astype(bool)
        same_parcel = (parcel.isna() | parcel.eq(hit)).fillna(False).astype(bool)
        is_adu = hit.notna() & (lettered | same_parcel) & ~mep
        out.loc[is_adu, ["building_type_std", "type_confidence", "units_new", "units_confidence"]] = [
            "ADU",
            "inferred",
            1,
            "inferred",
        ]
        out.loc[is_adu, "units_removed"] = pd.NA
        out.loc[is_adu, "is_demolition"] = False
        out.loc[is_adu, "adu_type"] = out.loc[is_adu, "permit_id"].map(flags["adu_type"])
    only_for_flag = df["_adu_only"].fillna(False).astype(bool) if "_adu_only" in df else False
    out = out.loc[out["permit_id"].notna() & ~(only_for_flag & ~is_adu)]
    # Guard: if a permit number repeats, keep the latest issue (none repeated on 2026-10-15).
    out = out.sort_values(["permit_id", "issue_date"]).drop_duplicates(["state", "permit_id"], keep="last")
    return out.reset_index(drop=True)


def download(store: DataStore, *, refresh: bool = False, adu_ids: list[str] | None = None) -> pd.DataFrame:
    common = dict(
        store=store,
        source=SOURCE,
        license=LICENSE,
        adapter=ADAPTER,
        adapter_version=VERSION,
        out_fields=",".join(OUT_FIELDS),
        refresh=refresh,
    )
    main = download_layer(LAYER_URL, name="building_permits", where=WHERE, **common)
    if not adu_ids:
        return main
    ids = ",".join("'" + i.replace("'", "''") + "'" for i in sorted(set(adu_ids)))
    extra = download_layer(LAYER_URL, name="adu_permits", where=f"B1_ALT_ID IN ({ids})", **common)
    extra = extra.loc[~extra["OBJECTID"].isin(main["OBJECTID"])].assign(_adu_only=True)
    return pd.concat([main, extra], ignore_index=True)


def load(state: str, store: DataStore, *, refresh: bool = False) -> pd.DataFrame:
    from lotline.adapters.states.oh import franklin_permits

    adu = franklin_permits.adu_flags(franklin_permits.download(store, refresh=refresh))
    raw = download(store, refresh=refresh, adu_ids=adu["permit_no"].tolist())
    df = build(raw, state=state, adu=adu)
    df = holdout.apply(
        df, state, geoid_col="jurisdiction_geoid", date_col="issue_date", year_col="issue_year"
    )
    return validate(df, TABLE)
