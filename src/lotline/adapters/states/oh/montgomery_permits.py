"""Montgomery County Auditor CAMA permit table (`PERMIT.DAT`) → ADU `permits` (Dayton and the county).

The Treasurer's "Cama Characteristics" download (a zip of the Auditor's appraisal tables, fixed width,
downloaded in a browser and registered with `lotline manifest register --source montgomery_permits`) holds
a `PERMIT` table: the building permits that the county's cities, villages and townships report for
reappraisal, 1993 to now (254,376 rows on 2026-09-30). Like the Franklin County Auditor's file
(`franklin_permits`) it is not a complete record of building (Dayton reports about 16,000 permits for
2010-2026, the unincorporated county 75,000, and 44% carry no description), but it is the only Montgomery
source that names ADUs. So this adapter keeps **ADU permits only**; a jurisdiction with no ADU has no row (the
ADU panel's caller lists the places).

**Fields read** (`FIELDS`, AA407 layout positions): parcel ID, the issuing office's permit number, permit
date, the work category `Why` (DWLG, ADDN, DET GAR, ALT, ELECTRIC, AC …), the valuation and the three
80-character notes. Address fields in the same record are never read. The export repeats some records
exactly; repeats are dropped.

**ADU rules.** The notes go through Franklin's named, recall-first rules
(`franklin_permits.describes_new_adu`: an ADU noun with a creation word; a carriage house described as a
garage, work on an existing unit, a multi-unit or project building, a demolition are not new ADUs), plus
Montgomery's own:

- `CREATING_WHY`: a permit filed as a dwelling, addition, detached garage or new building needs no creation
  word in its note ("IN LAW SUITE ADDITION" under ADDN);
- `TRADE_WHY`: electrical, mechanical, plumbing, gas, fire and similar categories are never an ADU;
- `ADDITION_TO_EXISTING`: "addition to [a] 2 story carriage house" works on a unit that already stands;
- `GARAGE_WORDS`: a "FOUR-CAR carriage house" is a garage (Franklin's rule reads digits only);
- `MULTIFAMILY`: an apartment complex's "carriage house" buildings ("BLD 40; 2 UNITS; NEW MULTI-FAMILY");
- one ADU per parcel in any `ADU_REPEAT_DAYS`: a permit re-issued after expiring is the same unit.

**Place.** The parcel ID is matched to the statewide roll (`oh_parcels`, "39113" + PARID); a parcel not in it
takes its taxing district's jurisdiction (the PARID prefix, "R72" = Dayton) where at least `DISTRICT_SHARE` of
the district's roll parcels lie in one jurisdiction, else it is dropped.

Checked by hand on 2026-10-31 against every flagged permit and every rejected note that names an ADU.
"""

from __future__ import annotations

import re
import zipfile
from pathlib import Path

import pandas as pd

from lotline.adapters.states.oh import franklin_permits as fp
from lotline.io import DataStore
from lotline.schemas import validate
from lotline.validation import holdout

ADAPTER = "states.oh.montgomery_permits"
VERSION = "1.0"
SOURCE = "montgomery_permits"
NAME = "montgomery_permits"
TABLE = "permits"
LANDING_URL = "https://go.mcohio.org/applications/treasurer/search/filedownloads.cfm"
LICENSE = (
    "Montgomery County Auditor/Treasurer public records (disclaimer 'as is'; no reuse restrictions stated, "
    "no open-data license)"
)
COUNTY = "39113"
ADU_REPEAT_DAYS = 730  # one ADU per parcel in any two years (as in franklin_permits)
DISTRICT_SHARE = 0.95  # taxing district → jurisdiction, for parcels missing from the roll
MIN_RECORD = 150  # bytes: shorter lines are spill-over, not records
# PERMIT.DAT fields (1-based start, length), AA407 layout; the address fields are not listed
FIELDS = {
    "parid": (1, 30),
    "num": (37, 18),
    "permdt": (55, 9),
    "why": (64, 10),
    "amount": (145, 11),
    "note1": (157, 80),
    "note2": (237, 80),
    "note3": (317, 80),
}
CREATING_WHY = {"DWLG", "ADDN", "ADDITION", "DET GAR", "NEW DETACH", "NEW BUILDI", "GAR ADDN"}
TRADE_WHY = re.compile(
    r"^(?:ELECTRIC|AC|FURNACE|GAS LINE|PLUMBING|SPRINKLER|FIRE|ALARM|MEC|HVAC|SEWER|WATER|SIGNS|SOLAR)"
)
ADDITION_TO_EXISTING = re.compile(
    r"\bADD(?:ITION)?\s+TO\s+(?:AN?\s+|THE\s+|EXISTING\s+)?(?:\w+\s+){0,3}CARRIAGE"
)
GARAGE_WORDS = re.compile(r"\b(?:TWO|THREE|FOUR|FIVE|SIX)[- ]CAR\b")
# an apartment complex whose buildings are called carriage houses ("PARKVIEW APARTMENTS; BLD 40; CARRIAGE
# HOUSE; 2 UNITS; NEW MULTI-FAMILY HOUSING")
MULTIFAMILY = re.compile(r"MULTI[- ]?FAMILY|\bAPARTMENTS\b|\bBLD\s+\d+\b")


def read_permits(path: Path) -> pd.DataFrame:
    """The `FIELDS` of PERMIT.DAT in a CAMA zip, exact repeats dropped."""
    with zipfile.ZipFile(path) as z:
        member = next(n for n in z.namelist() if re.split(r"[\\/]", n)[-1].upper() == "PERMIT.DAT")
        rows = []
        with z.open(member) as f:
            for line in f:
                if len(line) >= MIN_RECORD:
                    rows.append(
                        [line[s - 1 : s - 1 + n].decode("latin-1").strip() for s, n in FIELDS.values()]
                    )
    return pd.DataFrame(rows, columns=list(FIELDS)).drop_duplicates().reset_index(drop=True)


def describes_new_adu(note: str, why: str, num: str) -> bool:
    """True if a cleaned note (with its work category and permit number) creates an ADU (module docstring)."""
    if not note or TRADE_WHY.search(why) or MULTIFAMILY.search(note):
        return False
    if ADDITION_TO_EXISTING.search(note) or GARAGE_WORDS.search(note):
        return False
    if fp.describes_new_adu(note, num):
        return True
    # a dwelling, addition or detached-garage permit is the creation: no creation word needed in the note
    return why in CREATING_WHY and bool(fp.ADU_NOUN.search(note)) and fp.describes_new_adu(f"NEW {note}", num)


def adu_flags(raw: pd.DataFrame) -> pd.DataFrame:
    """ADU permits in the raw table: parcel_id, permit_no, issue_date, adu_type, amount, why."""
    df = raw.copy()
    date = pd.to_datetime(df["permdt"], format="%d-%b-%y", errors="coerce")
    date = date.where(date.dt.year.between(1990, pd.Timestamp.today().year))
    df["issue_date"] = date.dt.normalize().astype("datetime64[ns]")
    df = df.loc[df["issue_date"].notna() & df["num"].ne("") & df["parid"].ne("")]
    note = (df["note1"] + " " + df["note2"] + " " + df["note3"]).map(fp.clean_text)
    hit = [describes_new_adu(t, w, n) for t, w, n in zip(note, df["why"], df["num"], strict=True)]
    kind = note[hit].map(fp.adu_kind)
    # a detached-garage permit, or "garage with ADU above" (Franklin's rule reads "above ... garage" only)
    detached = df.loc[hit, "why"].eq("DET GAR") | note[hit].str.contains(r"GARAGE\b.{0,25}\bABOVE")
    adu = df.loc[hit].assign(adu_type=kind.mask(detached, "detached")).sort_values("issue_date")
    keep, last = [], {}
    for i, parcel, d in zip(adu.index, adu["parid"], adu["issue_date"], strict=True):
        if parcel in last and (d - last[parcel]).days < ADU_REPEAT_DAYS:
            continue
        last[parcel] = d
        keep.append(i)
    adu = adu.loc[keep]
    return pd.DataFrame(
        {
            "parcel_id": COUNTY + adu["parid"],
            "permit_no": adu["num"],
            "issue_date": adu["issue_date"],
            "adu_type": adu["adu_type"],
            "amount": pd.to_numeric(adu["amount"], errors="coerce"),
            "why": adu["why"],
        }
    ).reset_index(drop=True)


def jurisdiction_lookup(parcels: pd.DataFrame) -> tuple[dict[str, str], dict[str, str]]:
    """(parcel ID → jurisdiction, taxing district → jurisdiction) from the roll's Montgomery parcels."""
    mc = parcels.loc[parcels["county_geoid"] == COUNTY, ["parcel_id", "jurisdiction_geoid"]].dropna()
    mc = mc.drop_duplicates("parcel_id")
    by_parcel = dict(zip(mc["parcel_id"].astype(str), mc["jurisdiction_geoid"].astype(str), strict=True))
    district = mc["parcel_id"].astype(str).str[len(COUNTY) : len(COUNTY) + 3]
    shares = mc.groupby(district)["jurisdiction_geoid"].value_counts(normalize=True)
    top = shares.groupby(level=0).head(1)
    by_district = {d: j for (d, j), s in top.items() if s >= DISTRICT_SHARE}
    return by_parcel, by_district


def build(raw: pd.DataFrame, parcels: pd.DataFrame, state: str = "OH") -> pd.DataFrame:
    """Raw PERMIT rows → canonical ADU permits."""
    adu = adu_flags(raw)
    by_parcel, by_district = jurisdiction_lookup(parcels)
    juris = (
        adu["parcel_id"]
        .map(by_parcel)
        .fillna(adu["parcel_id"].str[len(COUNTY) : len(COUNTY) + 3].map(by_district))
    )
    n = len(adu)
    out = pd.DataFrame(
        {
            "state": state,
            "permit_id": "MONT-" + adu["permit_no"],
            "parcel_id": adu["parcel_id"].astype("string"),
            "jurisdiction_geoid": juris,
            "issue_year": adu["issue_date"].dt.year.astype("Int64"),
            "issue_date": adu["issue_date"],
            "date_precision": "day",
            "adu_type": adu["adu_type"].astype("string"),
            "permit_class_raw": adu["why"].astype("string"),
            "is_demolition": pd.Series([False] * n, index=adu.index, dtype="boolean"),
            "is_conversion": pd.Series(pd.NA, index=adu.index, dtype="boolean"),
            "valuation_usd": adu["amount"].where(adu["amount"] > 0),
            "source": NAME,
            "building_type_std": "ADU",
            "type_confidence": "inferred",
            "units_new": pd.Series([1] * n, index=adu.index, dtype="Int64"),
            "units_removed": pd.Series(pd.NA, index=adu.index, dtype="Int64"),
            "units_confidence": "inferred",
        }
    )
    out = out.loc[out["jurisdiction_geoid"].notna()]
    return out.drop_duplicates(["state", "permit_id"]).reset_index(drop=True)


def registered_file(store: DataStore) -> Path:
    """The latest CAMA zip registered for this source."""
    files = sorted(Path(store.root) / e.path for e in store.registered(SOURCE))
    if not files:
        raise RuntimeError(
            "No Montgomery CAMA zip is registered. Download 'Cama Characteristics' from "
            f"{LANDING_URL} in a browser, then run: uv run lotline manifest register <zip> --source {SOURCE} "
            f"--url {LANDING_URL} --license '<terms>' --vintage <YYYY-MM-DD>"
        )
    return files[-1]


def load(state: str, store: DataStore, *, refresh: bool = False) -> pd.DataFrame:
    parcels = store.read(state, "parcels")
    if parcels is None:
        raise RuntimeError(
            "montgomery_permits needs `parcels`: run `lotline fetch --state OH --source oh_parcels`"
        )
    df = build(read_permits(registered_file(store)), parcels, state=state)
    df = holdout.apply(
        df, state, geoid_col="jurisdiction_geoid", date_col="issue_date", year_col="issue_year"
    )
    return validate(df, TABLE)


PROVENANCE = {
    "title": "Montgomery County Auditor CAMA permit table (Treasurer 'Cama Characteristics' download)",
    "landing_url": LANDING_URL,
    "table": TABLE,
    "cleaning": [
        "Downloaded in a browser and registered with `lotline manifest register` (the site sits behind a bot "
        "check); the latest registered zip is read",
        "PERMIT.DAT: only parcel ID, permit number, date, work category, valuation and the three notes are "
        "read (no address fields); exact repeated records dropped; dates 1990 to today",
        "ADU permits only, from Franklin's recall-first named rules plus Montgomery's (a dwelling, addition "
        "or detached-garage permit needs no creation word; trade categories, multi-family buildings, "
        "additions to an existing carriage house and N-car carriage houses excluded); one ADU per parcel in "
        "any two years",
        "Jurisdiction from the parcel's roll record, else its taxing district's (>= "
        f"{DISTRICT_SHARE:.0%} of the district in one jurisdiction), else dropped",
        "Holdout filter applied (Ohio has no holdouts)",
    ],
    "limitations": [
        "Only permits the issuing offices report to the Auditor, 44% without a description: an undercount "
        "of ADUs (Dayton reports about 16,000 permits for 2010-2026)",
        "ADU flags are read from free text (inferred) and favour recall",
        "No permit status: a flagged ADU may never have been built",
        "A jurisdiction with no ADU permit has no row",
    ],
}
