"""Franklin County Auditor permit file (`Permit.xlsx`, appraisal "Outside User Files") → ADU `permits`.

The auditor collects the building permits that the cities, villages and townships of Franklin County report
for reappraisal: one row per permit and parcel, with the issuing office's permit number and its free-text work
description. Each monthly appraisal snapshot carries a rolling window: the 2022-12-15 snapshot holds
1990–2022 and the 2026-10-15 one 2020 to now, so the two together (`SNAPSHOTS`) cover 1990 to the present.

**ADUs only.** The file is the only Ohio source that names ADUs outside Cincinnati (Columbus's own layer has
no description, and no suburb publishes permits). It is *not* a complete record of new houses: for 2014–2025
it holds about a tenth of the single-family units Census BPS counts for Columbus and more than BPS for Grove
City, because a new subdivision lot has no parcel yet when its permit is issued. An ADU goes on an existing
parcel, which is what the auditor tracks, so this adapter keeps **ADU permits only**:

- every Franklin County jurisdiction except Columbus becomes `source = "franklin_permits"`;
- Columbus's own layer stays the permit-of-record: `columbus_permits` reads `adu_flags` and relabels the
  matching permits as ADUs, so no Columbus permit is counted twice.

A jurisdiction with no ADU here has no row: the ADU panel's caller lists the Franklin County places it uses.

**Trade permits.** Electrical, plumbing, HVAC and fire permits for a project repeat its words ("WIRE NEW
CARRIAGE HOUSE"). A permit is a trade permit if its description cites another permit number ("BUILDING
PERMIT/PLAN REVIEW: NEWR2006370"), starts with a trade word (`TRADE`) or carries an amperage, Columbus's "MLS"
(minor limited scope) suffix, a licence or a scope item (`TRADE_ANYWHERE`). A trade permit is never an ADU
itself; one that describes a new ADU marks the permit it cites.

**ADU rules (recall first, since 2026-10-28).** The shared parser (`lotline.parse.permit_text`) reads any
ADU noun as a new ADU ("REPL A/C - CARRIAGE HOUSE"), so this adapter uses its own named rules on the
description. Ben chose recall over precision for Columbus's undercount (2026-10-28), so the rules accept vague
creation cases and keep only the clear exclusions:

- `ADU_NOUN`: accessory dwelling (unit), ADU, carriage house, garage apartment, apartment above a garage,
  (mother-)in-law suite;
- `ADU_CREATE`: build, construct, erect, new, create, add(ing), convert ... to/into, to become, within
  `ADU_WINDOW` characters before the noun; not needed on a Columbus new residential building permit
  (`NEW_BUILDING_PERMIT`: RBLD, NEWR, CBLD);
- `GARAGE_ONLY`: a carriage house described as a garage ("CARRIAGE HOUSE (DETACHED GARAGE)", "3-CAR
  CARRIAGE HOUSE") needs rooms, a dwelling unit or a Council variance (`CARRIAGE_LIVING`); any other new
  carriage house counts, and so does any new in-law suite;
- `CITED_PROJECT`: a trade permit doing ADU work ("NEWR2449412 GAS LINES FOR NEW CARRIAGE HOUSE") marks the
  new-building or addition permit it cites (RBLD, NEWR, CBLD, ADDR) as the ADU, unless it works on what
  already stands (`TRADE_EXISTING`: existing, rewire, renovate); a cited permit missing from the file is
  flagged from its earliest citing trade permit (`permit_type` "cited project permit");
- `EXISTING_WORK`: renovating, remodelling, repairing, replacing, altering or "existing" right before the
  noun, or roofing, windows, siding or a remodel right after it, or "carriage home style": not a new ADU
  unless a conversion's result is the ADU (`CONVERSION`, "turning it into an in-law suite");
- `TRADE_PERMIT_NO`: Columbus repair and trade permits (EMEP, MMEP, PMEP, MMLS, FUEL, ROOF, RSWD) are not
  ADUs themselves unless they carry the project's own building description ("BUILD ...");
- `MULTI_UNIT_ADU`: a "3 family" or "4 unit" carriage house is a multi-unit building, not an ADU;
- `PROJECT_BUILDING`: "BUILDING 3 SUITE 102 … CARRIAGE HOUSE" or "LOT 95" is a home in a new development;
- a description that starts with a demolition word is not an ADU.

An ADU permit is one dwelling (`units_new` 1, inferred). `adu_type` is detached (carriage house, detached,
above a garage), attached (an addition), internal_conversion (basement, attic, part of the house) or unknown.
A parcel gets at most one ADU in any `ADU_REPEAT_DAYS`: revisions and re-issued permits are not new ADUs.

Checked by hand on 2026-10-23 against every flagged permit (36 → 35 after fixes, about 9 in 10 read as new
ADUs) and 50 rejected candidates (about 6 missed ADUs, since fixed, and 9 too vague to call): see the PR. The
recall rules (2026-10-28) raise the flags from 35 to 72; each of the 39 added was read by hand, and the five
clear false positives found (repair permits, multi-unit buildings) became the guards above.

**Place.** The auditor's parcel number ("010-000002-00") is matched to the statewide roll (`oh_parcels`,
"39049010-000002"); a parcel not in the roll (split after 2023) takes its taxing district's jurisdiction where
at least `DISTRICT_SHARE` of the district's parcels lie in one jurisdiction, else the row is dropped.

Descriptions are read in memory and never stored.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from lotline.io import DataStore
from lotline.io.http import fetch
from lotline.schemas import validate
from lotline.validation import holdout

ADAPTER = "states.oh.franklin_permits"
VERSION = "1.0"
SOURCE = "franklin_auditor"
NAME = "franklin_permits"
TABLE = "permits"
BASE_URL = "https://apps.franklincountyauditor.com/Outside_User_Files"
LANDING_URL = "https://auditor.franklincountyohio.gov/Auditor/FTP"
LICENSE = "Franklin County Auditor public records (disclaimer: 'as is'; no reuse terms stated)"
COUNTY = "39049"
COLUMBUS_GEOID = "3918000"
# Appraisal snapshots read together: 1990–2022 and 2020 to 2026-10 (overlaps deduplicated). A newer snapshot
# is added here, so a rerun reads the same files.
SNAPSHOTS = ("2022-12-15", "2026-10-15")
ADU_REPEAT_DAYS = 730  # one ADU per parcel in any two years
ADU_WINDOW = 160  # characters before an ADU noun searched for a creation verb
DISTRICT_SHARE = 0.95  # taxing district → jurisdiction, for parcels missing from the roll

# Columbus plan-review boilerplate ("USE/OCCUPANCY GROUP: 1, 2, 3 FAMILY DWELLING") names the code's use
# group, not the building: only the text after "DESCRIPTION OF WORK:" describes the work.
WORK = re.compile(r"DESCRIPTION OF WORK\s*:\s*")
USE_GROUP = re.compile(r"USE/OCCUPANCY GROUP\s*:\s*1,\s*2,\s*3 FAMILY DWELLING")

_PERMIT_NO = r"[A-Z]{2,6}\d{6,9}"
REF = re.compile(rf"(?:PLAN REVIEW|PERMIT)\s*[:#/]?\s*#?\s*({_PERMIT_NO})|\b({_PERMIT_NO})\b")
TRADE = re.compile(
    r"^\W*(?:[\d-]+\s+[A-Z0-9 .]+?\s+(?:ST|AVE|RD|DR|BLVD|CT|PL|LN|WAY)\b\W*)?"  # optional leading address
    r"(?:REPLACE|REPLACING|REPL|INSTALL|INSTALLATION|WIRE|WIRING|ELECTRIC|ELECTRICAL|ELEC|PLUMBING|PLUMB|"
    r"HVAC|MECHANICAL|GAS|FURNACE|SEWER|WATER|DRIVEWAY|ZONING|FENCE|ROOF|SIGN|SERVICE|STATUS CHANGE|FIRE|"
    r"SPRINKLER|TEMP|SIDEWALK|CURB|GRADING|REVISION|REVISED|RUNNING|FINAL|INSPECTION|\*+\s*REVISION)\b"
)
TRADE_ANYWHERE = re.compile(r"\b\d+\s*AMP\b|\bMLS\b|LICENSE NUMBER|SCOPE ITEM")

_NOUN = (
    r"(?:ACCESSORY DWELLING(?: UNIT)?|\bADU\b|CARRIAGE HOUSE|GARAGE APARTMENT|GARAGE APT"
    r"|(?:MOTHER[- ]?)?IN[- ]LAW SUITE)"
)
ADU_NOUN = re.compile(rf"{_NOUN}|APARTMENT (?:ABOVE|OVER) (?:THE |A |AN )?(?:\w+ )?GARAGE")
ADU_CREATE = re.compile(
    r"\b(?:BUILD|BUILDING A|CONSTRUCT\w*|ERECT\w*|NEW|CREATE\w*|ADD|ADDING|TO BECOME|INTO|"
    r"CONVER\w*\b.{0,60}?\b(?:TO|INTO))\b"
)
NEW_BUILDING_PERMIT = re.compile(r"^(?:RBLD|NEWR|CBLD)\d")
CARRIAGE_LIVING = re.compile(
    r"KITCHEN|\bKIT\b|LIVING|SLEEPING|BEDROOM|BDRM|\b(?:1|ONE|2|TWO) FAM(?:ILY)?\b|CARRIAGE HOUSE DWELLING|"
    r"DWELLING (?:UNIT|ON TOP|ABOVE)|APARTMENT|\bAPT\b|TENANT|COUNCIL VARIANCE|\bCV\d|\bLQ\b|LIVING QUARTERS"
)
GARAGE_ONLY = re.compile(
    r"CARRIAGE HOUSE\s*\(DETACHED GARAGE\)|GARAGE\s*/\s*CARRIAGE HOUSE|CARRIAGE HOUSE\s*/\s*GARAGE"
    r"|\b\d[- ]CAR CARRIAGE HOUSE"
)
# Columbus repair and trade permits (electrical, mechanical, plumbing, minor limited scope, fuel, roofing,
# siding/windows/doors) are not an ADU themselves, unless they carry the project's own building description
# ("BUILD 2 STORY FRAME, 1 FAMILY CARRIAGE HOUSE ...", copied onto some MEP permits)
TRADE_PERMIT_NO = re.compile(r"^(?:[EMP]MEP|MMLS|FUEL|ROOF|RSWD)")
BUILDING_DESCRIPTION = re.compile(r"^\W*(?:BUILD|CONSTRUCT)\b")
# a "3 family carriage house" or "4 unit carriage house" is a multi-unit building, not an accessory unit
MULTI_UNIT_ADU = re.compile(rf"\b(?:[3-9]|THREE|FOUR|FIVE|SIX)[- ]?(?:UNIT|FAMILY)\s+{_NOUN}")
# trade work on a structure that already stands is not the project that created the ADU
TRADE_EXISTING = re.compile(r"\bEXISTING\b|\bREWIR\w*|\bRENOVAT\w*")
# a trade permit citing one of these (new residential building, addition) for ADU work marks it an ADU
CITED_PROJECT = re.compile(r"^(?:RBLD|NEWR|CBLD|ADDR)\d")
CONVERSION = re.compile(
    rf"(?:CONVER\w*|TURNING|TURN)\b.{{0,80}}?\b(?:TO|INTO)\b.{{0,30}}?{_NOUN}|TO BECOME\b.{{0,30}}?{_NOUN}"
)
EXISTING_WORK = re.compile(
    rf"(?:RENOVAT\w*|REMODEL\w*|REPAIR\w*|REPLAC\w*|ALTER\w*|EXISTING)\W+(?:\w+\W+){{0,4}}?{_NOUN}"
    rf"|{_NOUN}\W+(?:\w+\W+){{0,4}}?"
    r"(?:SHINGLES?|ROOF\w*|WINDOWS?|SIDING|REMODEL\w*|RENOVAT\w*|REPAIR\w*|NEW FINISHES)"
    r"|CARRIAGE HOME STYLE"
)
PROJECT_BUILDING = re.compile(r"\b(?:BUILDING|BLDG)\s+\d+\b|\bLOT\s+\d+\b")
DEMO_START = re.compile(r"^\W*(?:DEMO\b|DEMOLI|RAZE|WRECK)")
ATTACHED = re.compile(r"ADDITION|\bADDING\b|\bADD\b|ATTACHED")
ABOVE_GARAGE = re.compile(r"(?:ABOVE|OVER) (?:THE |A |AN )?(?:\w+ )?GARAGE|GARAGE AP")
INTERNAL = re.compile(r"BASEMENT|ATTIC|CONVER\w*\b.{0,40}?\b(?:PART|PORTION|SECTION) OF")

PROVENANCE = {
    "title": "Franklin County Auditor permit file (Outside User Files, appraisal snapshots)",
    "landing_url": LANDING_URL,
    "table": TABLE,
    "cleaning": [
        f"Snapshots {', '.join(SNAPSHOTS)} read together (1990 to the present); a permit repeated across "
        "snapshots or parcels is kept once per permit number and taxing district",
        "Rows without a permit number (auditor field notes) or with an impossible date are dropped",
        "ADU permits only, from named description rules favouring recall (ADU noun + creation verb; a "
        "carriage house described as a garage needs living space; work on existing units, repair and trade "
        "permit numbers and multi-unit buildings excluded); trade permits mark the new-building or addition "
        "permit they cite, flagged from the earliest trade permit when the project permit is not in the "
        "file; one ADU per parcel in any two years",
        "Parcel matched to oh_parcels for the jurisdiction; parcels not in the roll take their taxing "
        f"district's jurisdiction where ≥{DISTRICT_SHARE:.0%} of its parcels lie in one",
        "Columbus permits are not written here: columbus_permits relabels its own matching permits as ADUs",
        "Work descriptions are read in memory and never stored",
        "Holdout filter applied (Ohio has no holdouts)",
    ],
    "limitations": [
        "Only permits the issuing office reports to the auditor; not a complete record of new houses, so "
        "only ADU permits are kept",
        "ADU flags are read from free text (inferred) and favour recall: an ADU described without one of the "
        "named nouns is missed, and some flagged carriage houses or in-law suites may be garages or rooms",
        "No permit status: a flagged ADU may have been withdrawn or never built",
        "Issue date is the auditor's permit date (PERMDT), which may be the application or issue date "
        "depending on the office",
        "A jurisdiction with no ADU permit has no row",
    ],
}


def snapshot_url(snapshot: str) -> str:
    return f"{BASE_URL}/{snapshot[:4]}/{snapshot}%20Appraisal/Permit.xlsx"


def clean_text(text) -> str:
    """Upper-case, single-spaced work description, without Columbus's plan-review header."""
    if pd.isna(text):
        return ""
    t = re.sub(r"\s+", " ", str(text)).strip().upper()
    m = WORK.search(t)
    if m:
        t = t[m.end() :]
    return USE_GROUP.sub(" ", t).strip()


def cited_permits(text: str, own: str) -> list[str]:
    """Permit numbers a description cites, other than the permit's own."""
    found = (m.group(1) or m.group(2) for m in REF.finditer(text))
    return [n for n in found if n and n != own.upper()]


def is_trade(text: str, own: str) -> bool:
    return bool(TRADE.search(text) or TRADE_ANYWHERE.search(text) or cited_permits(text, own))


def existing_work(text: str) -> bool:
    return bool(EXISTING_WORK.search(text)) and not CONVERSION.search(text)


def describes_new_adu(text: str, permit_no: str = "") -> bool:
    """True if the description (of permit `permit_no`) creates an ADU under the named rules, trade or not."""
    if DEMO_START.search(text) or PROJECT_BUILDING.search(text) or MULTI_UNIT_ADU.search(text):
        return False
    if TRADE_PERMIT_NO.search(permit_no.upper()) and not BUILDING_DESCRIPTION.search(text):
        return False
    builds = bool(NEW_BUILDING_PERMIT.search(permit_no.upper()))
    hit = next(
        (
            m
            for m in ADU_NOUN.finditer(text)
            if builds or ADU_CREATE.search(text[max(0, m.start() - ADU_WINDOW) : m.start()])
        ),
        None,
    )
    if hit is None:
        return False
    noun = hit.group(0)
    if "CARRIAGE" in noun and GARAGE_ONLY.search(text) and not CARRIAGE_LIVING.search(text):
        return False
    return not existing_work(text)


def cites_project_for_adu(text: str, own: str) -> list[str]:
    """Project permits (`CITED_PROJECT`) that a trade permit doing ADU work cites ("NEWR2006370 INSTALL GAS
    LINES ... TO GARAGE (CARRIAGE HOUSE)"): the trade needs no creation verb, the project is the new ADU."""
    if not ADU_NOUN.search(text) or existing_work(text) or DEMO_START.search(text):
        return []
    if TRADE_EXISTING.search(text) or MULTI_UNIT_ADU.search(text) or PROJECT_BUILDING.search(text):
        return []
    return [c for c in cited_permits(text, own) if CITED_PROJECT.search(c)]


def adu_kind(text: str) -> str:
    if re.search(r"CARRIAGE HOUSE|DETACHED", text):
        return "detached"
    if ATTACHED.search(text):
        return "attached"
    if ABOVE_GARAGE.search(text):
        return "detached"
    if INTERNAL.search(text):
        return "internal_conversion"
    return "unknown"


def adu_flags(raw: pd.DataFrame) -> pd.DataFrame:
    """ADU permits in the raw file: district, permit_no, parcel, issue_date, adu_type, amount, permit_type.

    No geography: `build` places them; `columbus_permits` matches the permit numbers to its own layer.
    """
    df = raw.loc[raw["PERMITNUM"].notna()].copy()
    df["permit_no"] = df["PERMITNUM"].astype(str).str.strip()
    df["district"] = df["PARCEL ID"].astype("string").str.strip().str[:3]
    date = pd.to_datetime(df["PERMDT"], errors="coerce")
    date = date.where(date.dt.year.between(1970, pd.Timestamp.today().year))  # typos such as 3020, 1019
    df["issue_date"] = date.dt.normalize().astype("datetime64[ns]")
    df = df.loc[df["permit_no"].ne("") & df["issue_date"].notna()]
    df = df.drop_duplicates(["district", "permit_no", "PARCEL ID", "DESCRIPTION"])
    text = df["DESCRIPTION"].map(clean_text)
    pairs = list(zip(text, df["permit_no"], strict=True))
    new = pd.Series([describes_new_adu(t, n) for t, n in pairs], index=df.index)
    trade = pd.Series([is_trade(t, n) for t, n in pairs], index=df.index)
    parents = {
        (d, c)
        for d, (t, n), x in zip(df["district"], pairs, new, strict=True)
        if x
        for c in cited_permits(t, n)
    } | {(d, c) for d, (t, n) in zip(df["district"], pairs, strict=True) for c in cites_project_for_adu(t, n)}
    cited = pd.Series(
        [k in parents for k in zip(df["district"], df["permit_no"], strict=True)], index=df.index
    )
    is_adu = (new & ~trade) | (cited & ~text.map(existing_work))
    adu = df.loc[is_adu].assign(adu_type=text[is_adu].map(adu_kind))

    # a cited project permit missing from the file: its earliest citing trade permit stands in for it
    present = set(zip(df["district"], df["permit_no"], strict=True))
    citing = []
    for i, d, (t, n) in zip(df.index, df["district"], pairs, strict=True):
        cites = cited_permits(t, n) if new[i] else cites_project_for_adu(t, n)
        citing += [(i, c) for c in cites if (d, c) in parents and (d, c) not in present]
    if citing:
        idx, nos = zip(*citing, strict=True)
        stand = df.loc[list(idx)].assign(permit_no=list(nos), PERMITTYPE="cited project permit")
        stand = stand.assign(adu_type=text[list(idx)].map(adu_kind).to_numpy())
        stand = stand.sort_values("issue_date").drop_duplicates(["district", "permit_no"])
        adu = pd.concat([adu, stand])
    adu = adu.sort_values("issue_date")
    keep, last = [], {}
    for i, parcel, d in zip(adu.index, adu["PARCEL ID"], adu["issue_date"], strict=True):
        if parcel in last and (d - last[parcel]).days < ADU_REPEAT_DAYS:
            continue
        last[parcel] = d
        keep.append(i)
    adu = adu.loc[keep]
    return pd.DataFrame(
        {
            "district": adu["district"],
            "permit_no": adu["permit_no"],
            "parcel": adu["PARCEL ID"].astype("string").str.strip(),
            "issue_date": adu["issue_date"],
            "adu_type": adu["adu_type"],
            "amount": pd.to_numeric(adu["AMOUNT"], errors="coerce"),
            "permit_type": adu["PERMITTYPE"].astype("string").str.strip(),
        }
    ).reset_index(drop=True)


def parcel_key(parcel: pd.Series) -> pd.Series:
    """Auditor parcel number '010-000002-00' → the roll's '39049010-000002'."""
    core = parcel.astype("string").str.strip().str.extract(r"^(\d{3}-\d{6})", expand=False)
    return (COUNTY + core).where(core.notna())


def jurisdiction_lookup(parcels: pd.DataFrame) -> tuple[dict[str, str], dict[str, str]]:
    """(parcel key → jurisdiction, taxing district → jurisdiction) from the statewide roll for the county."""
    fr = parcels.loc[parcels["county_geoid"] == COUNTY, ["parcel_id", "jurisdiction_geoid"]].dropna()
    by_parcel = dict(zip(fr["parcel_id"].astype(str), fr["jurisdiction_geoid"].astype(str), strict=True))
    district = fr["parcel_id"].astype(str).str[len(COUNTY) : len(COUNTY) + 3]
    shares = fr.groupby(district)["jurisdiction_geoid"].value_counts(normalize=True)
    top = shares.groupby(level=0).head(1)
    by_district = {d: j for (d, j), s in top.items() if s >= DISTRICT_SHARE}
    return by_parcel, by_district


def build(raw: pd.DataFrame, parcels: pd.DataFrame, state: str = "OH") -> pd.DataFrame:
    """Raw permit rows (snapshots stacked) → canonical ADU permits outside Columbus."""
    adu = adu_flags(raw)
    by_parcel, by_district = jurisdiction_lookup(parcels)
    key = parcel_key(adu["parcel"])
    juris = key.map(by_parcel).fillna(adu["district"].map(by_district))
    out = pd.DataFrame(
        {
            "state": state,
            "permit_id": "FRA-" + adu["district"].fillna("") + "-" + adu["permit_no"],
            "parcel_id": key,
            "jurisdiction_geoid": juris,
            "issue_year": adu["issue_date"].dt.year.astype("Int64"),
            "issue_date": adu["issue_date"],
            "date_precision": "day",
            "adu_type": adu["adu_type"].astype("string"),
            "permit_class_raw": adu["permit_type"],
            "is_demolition": pd.Series(False, index=adu.index, dtype="boolean"),
            "is_conversion": pd.Series(pd.NA, index=adu.index, dtype="boolean"),
            "valuation_usd": adu["amount"].where(adu["amount"] > 0),
            "source": NAME,
            "building_type_std": "ADU",
            "type_confidence": "inferred",
            "units_new": pd.Series(1, index=adu.index, dtype="Int64"),
            "units_removed": pd.Series(pd.NA, index=adu.index, dtype="Int64"),
            "units_confidence": "inferred",
        }
    )
    out = out.loc[out["jurisdiction_geoid"].notna() & out["jurisdiction_geoid"].ne(COLUMBUS_GEOID)]
    return out.drop_duplicates(["state", "permit_id"]).reset_index(drop=True)


def download(store: DataStore, *, refresh: bool = False) -> pd.DataFrame:
    frames = []
    for snap in SNAPSHOTS:
        path = fetch(
            snapshot_url(snap),
            Path(store.root) / "raw" / SOURCE / snap / "appraisal" / "Permit.xlsx",
            store=store,
            source=SOURCE,
            license=LICENSE,
            adapter=ADAPTER,
            adapter_version=VERSION,
            refresh=refresh,
        )
        frames.append(pd.read_excel(path, dtype={"PERMITNUM": "string", "PARCEL ID": "string"}))
    return pd.concat(frames, ignore_index=True)


def load(state: str, store: DataStore, *, refresh: bool = False) -> pd.DataFrame:
    parcels = store.read(state, "parcels")
    if parcels is None:
        raise RuntimeError(
            "franklin_permits needs `parcels`: run `lotline fetch --state OH --source oh_parcels`"
        )
    df = build(download(store, refresh=refresh), parcels, state=state)
    df = holdout.apply(
        df, state, geoid_col="jurisdiction_geoid", date_col="issue_date", year_col="issue_year"
    )
    return validate(df, TABLE)
