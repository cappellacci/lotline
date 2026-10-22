"""Draft NC OneMap land-use crosswalks from a county's code inventory (helper for `onemap_parcels`).

Ninety NC counties send land-use codes no one has crosswalked by hand. Their labels mostly follow a few
county tax-system vocabularies ("1 Family Residential", "SINGLE FAMILY", "DOUBLE WIDE MH", "Unused Land",
"Exempt Religious" ...), so this module proposes a `land_use_std` for each label with a short list of
named keyword rules, and picks the fields to read:

1. **Fields.** A field is usable when it is not near free text (not truncated by the server and at most
   `MAX_CODES` distinct values) and the rules classify most of its parcels. Fields are read most-specific
   first: the field whose classified parcels are split over the most residential types comes first, so a
   building-type field ("Townhouse", "Duplex") wins over a broad class ("Residential").
2. **Labels.** Each code is matched against `RULES` in order; the first rule whose pattern matches names
   the category. Codes made only of digits or punctuation never match (no label to read).
3. **Vacant rule and tier.** `vacant_when_unimproved` is set when most single-family parcels carry a
   building value (otherwise a missing value would turn houses into lots); the built signal is `structyear`
   only when the county sends no building values. The data tier follows the brief (1: year built and use
   codes; 2: use codes; 3: neither), with the D-016 thresholds.

Every drafted row says which rule matched (`notes`), so a reviewer can check it; the drafts were reviewed
by hand before being committed (codes covering many parcels first). `scripts/dev/nc_onemap_crosswalks.py`
writes the files.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import pandas as pd

MAX_CODES = 800  # mechanics: more distinct values than this is free text (Alamance parusedsc2: 4,984)
MIN_FIELD_COVERAGE = 0.5  # mechanics: a field must classify at least half the county's parcels to be read
VACANT_FLAG_MIN_IMPROVED = 0.7  # mechanics: share of single-family parcels with a building value
TIER1_MIN_YEAR_BUILT = 0.8  # D-016 (config/params/tiers.yaml tier1_min_year_built_share)
TIER2_MIN_LAND_USE = 0.9  # D-016 (config/params/tiers.yaml tier2_min_land_use_share)

# (name, land_use_std, pattern). Order matters: the first match wins.
RULES: list[tuple[str, str, str]] = [
    ("mixed", "MIXED_USE", r"MIXED"),
    ("nonres_condo", "COMMERCIAL", r"(WAREHOUSE|OFFICE|COMM\w*|BUSINESS|MEDICAL|STORAGE) ?CONDO"),
    ("condo", "CONDO_UNIT", r"CONDO"),
    (
        "mobile",
        "MOBILE_HOME",
        r"\bMOBILE|MANUFACTURED|MANU?F\w* HOM|MFG HOM|DOUBLE ?WIDE|SINGLE ?WIDE|\bD/?W\b|"
        r"\bS/?W\b|\bMH\b|TRAILER",
    ),
    # A vacant lot is residential only when the label says so; a vacant commercial, industrial or exempt lot
    # keeps that use, and a bare "Vacant" stays unknown (the hand-coded counties' convention).
    ("vacant_commercial", "COMMERCIAL", r"(VACANT|UNUSED|UNIMPROVED).*\bCOM|\bCOM\w*.*(VACANT|UNUSED)"),
    ("vacant_industrial", "INDUSTRIAL", r"(VACANT|UNUSED|UNIMPROVED).*\bIND|\bIND\w*.*(VACANT|UNUSED)"),
    (
        "vacant_exempt",
        "INSTITUTIONAL",
        r"(VACANT|UNUSED|UNIMPROVED).*(INST|EXEMPT|GOV|RELIG|CHURCH)|"
        r"(INST|EXEMPT|GOV)\w*.*(VACANT|UNUSED)",
    ),
    ("vacant_ag", "AGRICULTURAL", r"(VACANT|UNUSED|UNIMPROVED).*(AG|FARM|TIMBER|FOREST|WOOD)|\bAG\b.*\bVAC"),
    (
        "special_lot",
        "OTHER",
        r"PARKING|DRAINAGE|WELL LOT|COMMON|OPEN SPACE|RESTRICT|AUXIL|ACCESSORY|"
        r"OTHER RES|MISC\w* RES|RES\w* OTHER|RES\w* MISC",
    ),
    (
        "vacant",
        "VACANT_RESIDENTIAL",
        r"\b(RES|SINGLE|SFR?|HOME|DWELL|SUBDIV)\w*.*\b(VACANT|VAC|LOT|UNUSED|UNIMPROVED)\b|"
        r"\b(VACANT|UNUSED|UNIMPROVED).*\b(RES|SF|HOME|DWELL|SUBDIV)|BUILDERS? LOT",
    ),
    (
        "townhouse",
        "SF_ATTACHED",
        r"TOWN ?HO|TOWNHOME|\bTH\b|\bTWN\b|PATIO HOME|ROW ?HOUSE|ATTACHED|ZERO LOT|TWIN ?HOME",
    ),
    ("tri_quad", "TRI_QUAD", r"TRI-?PLEX|QUAD|FOURPLEX|\b[34][ -]?FAM|THREE FAM|FOUR FAM|2-4|<4|2 TO 4"),
    ("duplex", "DUPLEX", r"DUPLEX|\b2[ -]?FAM|TWO[ -]?FAM|\bDOUBLE\b"),
    (
        "multifamily",
        "MULTIFAMILY_5P",
        r"APART|\bAPTS?\b|MULTI-? ?FAM|\bMF\b|5\+|OR MORE FAM|ROOMING|BOARDING",
    ),
    (
        "single_family",
        "SF_DETACHED",
        r"SINGLE[ -]?FAM|\b1[ -]?FAM|ONE[ -]?FAM|\bSFR?\b|\bSFD\b|DWELLING|"
        r"RESIDEN|\bRES\b|\bHOUSE\b|RANCH|COTTAGE|BUNGALOW|MODULAR|\bR-?1\b",
    ),
    (
        "agricultural",
        "AGRICULTURAL",
        r"FARM|AGRI|TIMBER|FOREST|CROP|PASTURE|ORCHARD|HORT|PRESENT USE|RURAL|"
        r"WOOD|POULTRY|DAIRY|LIVESTOCK|NURSERY|TOBACCO",
    ),
    (
        "utility",
        "OTHER",
        r"UTIL|RIGHT[ -]OF[ -]WAY|\bROW\b|ROAD|RAIL|EASEMENT|AIRPORT|CELL|TOWER|"
        r"WATER (SYS|PLANT|TREAT|TANK)|SEWER",
    ),
    (
        "institutional",
        "INSTITUTIONAL",
        r"CHURCH|RELIG|SCHOOL|EXEMPT|GOV|HOSPITAL|CEMET|INSTITU|\bINST\b|"
        r"PUBLIC|MUNICIPAL|COUNTY|\bSTATE\b|FEDERAL|COLLEGE|UNIVERS|CHARIT|NON-?PROFIT|FIRE|LIBRARY|EDUCA|"
        r"HEALTH|HCFAC|ASSIST|NURSING|GSERV",
    ),
    (
        "industrial",
        "INDUSTRIAL",
        r"INDUS|\bIND\b|MANUF|WAREHOUSE|PLANT|\bMILL\b|QUARR|MINING|FACTORY|"
        r"DISTRIBUT|STORAGE",
    ),
    ("other", "OTHER", r"\bHOA\b|ASSOC|RECREAT|GOLF|\bPARK\b|MARINA|CLUB|LAKE|POND"),
    (
        "commercial",
        "COMMERCIAL",
        r"COMMERC|\bCOMM?\b|RETAIL|OFFICE|STORE|SHOP|RESTAUR|BUSINESS|HOTEL|MOTEL|"
        r"BANK|SERVICE|GAS|AUTO|MEDICAL|MALL|CENTER|EATING|FOOD|DINING|BUSI|THEATER|CAR WASH|DEALER|"
        r"REPAIR|VEHICLE",
    ),
]
_COMPILED = [(n, s, re.compile(p)) for n, s, p in RULES]
_LABEL = re.compile(r"[A-Z]{2,}")


def classify(code: str) -> tuple[str | None, str | None]:
    """(land_use_std, rule name) for one code, or (None, None) when no rule matches or there is no label."""
    text = str(code).upper()
    if not _LABEL.search(text):
        return None, None
    for name, std, pat in _COMPILED:
        if pat.search(text):
            return std, name
    return None, None


RESIDENTIAL_TYPES = {"SF_DETACHED", "SF_ATTACHED", "DUPLEX", "TRI_QUAD", "MULTIFAMILY_5P", "CONDO_UNIT",
                     "MOBILE_HOME"}  # fmt: skip


@dataclass(frozen=True)
class Draft:
    rows: pd.DataFrame  # field, code, description, land_use_std, rule, n
    fields: tuple[str, ...]
    vacant_when_unimproved: bool
    built_signal: str
    data_tier: int
    land_use_share: float  # share of parcels the drafted crosswalk classifies (first matching field)
    year_built_share: float  # share of built parcels with a structure year
    tier_basis: str


def draft(inventory: pd.DataFrame) -> Draft:
    """Draft one county's crosswalk from `onemap_parcels.code_inventory` output."""
    inv = inventory.copy()
    total = int(inv.groupby("field")["n"].sum().max())
    std_rule = inv["code"].map(classify)
    inv["land_use_std"] = [s for s, _ in std_rule]
    inv["rule"] = [r for _, r in std_rule]
    usable = []
    for field, g in inv.groupby("field"):
        if g["truncated"].any() or len(g) > MAX_CODES or len(g) < 2:
            continue
        covered = g.loc[g["land_use_std"].notna(), "n"].sum() / max(total, 1)
        if covered < MIN_FIELD_COVERAGE:
            continue
        res = g.loc[g["land_use_std"].isin(RESIDENTIAL_TYPES)]
        usable.append((field, res["land_use_std"].nunique(), covered))
    usable.sort(key=lambda t: (-t[1], -t[2], t[0]))
    fields = tuple(f for f, _, _ in usable)
    rows = inv.loc[inv["field"].isin(fields) & inv["land_use_std"].notna()]
    rows = rows.assign(description=rows["code"])[
        ["field", "code", "description", "land_use_std", "rule", "n"]
    ]
    # Share of parcels classified when the fields are read in order is bounded by the best field's coverage
    # (the inventory has no cross-field joint counts): report the first field's share as the estimate.
    land_use_share = usable[0][2] if usable else 0.0
    sf = inv.loc[inv["field"].isin(fields[:1]) & (inv["land_use_std"] == "SF_DETACHED")]
    improved = sf["n_improved"].sum() / max(sf["n"].sum(), 1)
    no_values = inv["n_improved"].sum() == 0
    built_signal = "structyear" if no_values else "improvval"
    built = inv.loc[inv["field"] == (fields[0] if fields else inv["field"].iloc[0]), "n_improved"].sum()
    yb = inv.loc[inv["field"] == (fields[0] if fields else inv["field"].iloc[0]), "n_structyear"].sum()
    year_built_share = float(yb / built) if built else 0.0
    vacant_flag = bool(fields) and not no_values and improved >= VACANT_FLAG_MIN_IMPROVED
    if land_use_share >= TIER2_MIN_LAND_USE and year_built_share >= TIER1_MIN_YEAR_BUILT:
        tier, basis = (
            1,
            f"land-use codes for {land_use_share:.0%} of parcels; structyear {year_built_share:.0%}",
        )
    elif land_use_share >= TIER2_MIN_LAND_USE:
        tier, basis = (
            2,
            f"land-use codes for {land_use_share:.0%} of parcels; structyear {year_built_share:.0%}",
        )
    else:
        tier, basis = 3, f"land-use codes classify only {land_use_share:.0%} of parcels"
    return Draft(rows.reset_index(drop=True), fields, vacant_flag, built_signal, tier, float(land_use_share),
                 year_built_share, basis)  # fmt: skip
