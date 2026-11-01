"""City of Columbus Council variance ordinances (Legistar Web API) → ADU approvals as `permits` rows.

Before Ord. 2526-2025 (effective 2025-12-24) Title 33's residential districts had no ADU use: a second
dwelling on a lot (a carriage house, a dwelling above a garage, "two single-unit dwellings on one lot")
needed a Council use variance, passed as an ordinance. The city's permit layer has no work description and
the Franklin County Auditor's descriptions find 34 of the 57 ADU permits the city counted for 2019 to
Sep 2025 (Ord. 2526-2025's explanation; 14 before the recall rules of 2026-10-28), so this source adds the
variances themselves: one row per
passed ordinance that permits a new accessory dwelling. Ben asked (2026-10-28) to bias Columbus towards
counting more ADUs; `observed_adu_counts` keeps the larger of this and `columbus_permits` each year, never
the sum, so the two sources are not double-counted.

**What counts** (named rules on the title's purpose clause, "to permit ... (Council Variance #CV..)"):
`RULES`, first match wins: a carriage or coach house; an accessory dwelling / ADU / accessory apartment; a
dwelling or living space above a garage; a second dwelling; two single-unit dwellings on one lot; a rear
dwelling on a lot developed with a dwelling; and habitable space above a detached garage (kept because Ben
chose recall over precision: some of these are studios or offices, not dwellings; `permit_class_raw` names
the rule, so the panel can drop it).

**What does not:** an ordinance not passed (defeated, tabled, in committee) or later repealed; one that only
conforms (legalizes) an existing dwelling; a dwelling in a commercial, manufacturing or institutional district
(a house there is not an accessory unit); a multi-unit building ("a three-unit dwelling (carriage house)"),
or dwellings on two or more lots.

**Date.** The ordinance's passed date (Council approval), not a building permit date: construction follows,
and some approved ADUs are never built (the city reports 110 variances approved against 57 ADU permits).
Counts from this source are approvals, an upper bound on new ADUs.

Titles are read in memory: the output keeps the ordinance file number, the variance number, the passed date,
the zoning district and the rule that matched, never the title (it names the property and, on some clerk
items, the applicant).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

from lotline.io import DataStore
from lotline.io.http import fetch
from lotline.schemas import validate
from lotline.validation import holdout

ADAPTER = "states.oh.columbus_variances"
VERSION = "1.0"
SOURCE = "columbus_legistar"
NAME = "columbus_variances"
TABLE = "permits"
API_URL = "https://webapi.legistar.com/v1/columbus/matters"
LANDING_URL = "https://columbus.legistar.com/Legislation.aspx"
LICENSE = "City of Columbus public legislative records (Legistar Web API; no reuse terms stated)"
COLUMBUS_GEOID = "3918000"
VINTAGE = "2026-10-30"  # the download folder: a rerun reads the same pages unless refreshed
PAGE = 1000  # the API's maximum page size (mechanics)
FILTER = "substringof('Variance',MatterTitle) and MatterTypeName eq 'Ordinance'"
FIELDS = "MatterId,MatterFile,MatterTitle,MatterPassedDate,MatterStatusName"
PASSED = {"Passed", "Consent"}

_WS = re.compile(r"\s+")
PURPOSE = re.compile(
    r"\bto (?:permit|allow|construct|conform|legitimize|establish|create|convert|build)\b.*", re.I | re.S
)
_SINGLE = r"single[- ](?:family|unit)"
RULES = [  # (rule, adu_type, pattern on the purpose clause); the first match wins
    ("carriage_house", "detached", r"carriage[- ]house"),
    ("coach_house", "detached", r"coach house"),
    ("accessory_dwelling", "unknown", r"accessory dwelling|\bADU\b|accessory apartment"),
    (
        "above_garage_dwelling",
        "detached",
        r"(?:dwelling|apartment|living (?:unit|space|quarters))\s+(?:unit\s+)?(?:above|over)\s+"
        r"(?:a |an |the )?(?:detached |existing |new )?garage",
    ),
    (
        "second_dwelling",
        "unknown",
        rf"second (?:{_SINGLE} )?dwelling|second (?:residence|house)|additional (?:{_SINGLE} )?dwelling",
    ),
    (
        "two_houses_one_lot",
        "detached",
        rf"(?:two|2) (?:detached )?{_SINGLE} dwellings (?:\([^)]*\) )?"
        r"on (?:one|a single|the same) (?:lot|parcel)",
    ),
    (
        "rear_dwelling",
        "detached",
        rf"dwelling[^.;]{{0,40}}\bon the rear of a lot developed with|rear {_SINGLE} dwelling",
    ),
    (
        "habitable_space_above_garage",
        "detached",
        r"habitable space (?:above|over) (?:a |an |the )?(?:detached )?garage",
    ),
]
RULES = [(name, kind, re.compile(p, re.I)) for name, kind, p in RULES]
# conforming (legalizing) an existing dwelling adds nothing, unless the ordinance also permits a new one
LEGALIZE_ONLY = re.compile(
    r"^to (?:conform|legitimize)\b(?!.*\band (?:to )?(?:construct|permit|allow|build)\b)", re.I | re.S
)
NONRESIDENTIAL = re.compile(
    r"\b(?:C-[1-5]|CPD|M|M-1|M-2|L-M|LM|I|CC|DD)\b,?\s+(?:Commercial|Manufacturing|Institutional|Downtown)",
    re.I,
)
_COUNT = r"(?:three|four|five|six|seven|eight|nine|ten|\d{1,3})"
MULTI_UNIT = re.compile(
    rf"\b{_COUNT}[- ]unit dwelling\s*\(?(?:a )?carriage|\b{_COUNT} dwelling units\b", re.I
)
SPLIT_LOTS = re.compile(
    r"\bcontiguous lots\b|\bon (?:two|2|three|3) lots\b|\bnew lot\b(?!.*\bsame lot\b)", re.I
)
REPEALED = re.compile(r"\bREPEALED\b", re.I)
DISTRICT = re.compile(r"\b(R|RR|SR|R-1|R-1A|R-1B|R-2|R-2F|R-3|R-4|ARLD|AR-1|AR-2|AR-3|AR-4|AR-12|AR-O)\b,?\s")
VARIANCE_NO = re.compile(r"\bCV\s?(\d{2}-\d{3})\b", re.I)


def purpose(title: str) -> str:
    """The title's purpose clause, from "to permit/allow/..." on (single-spaced)."""
    m = PURPOSE.search(_WS.sub(" ", title or ""))
    return m.group(0) if m else ""


def classify(title: str, status: str | None, passed: str | None) -> tuple[str, str] | None:
    """(rule, adu_type) if the ordinance approves a new ADU, else None (see the module docstring)."""
    if status not in PASSED or pd.isna(passed) or not passed or REPEALED.search(title or ""):
        return None
    clause = purpose(title)
    hit = next(((name, kind) for name, kind, rx in RULES if rx.search(clause)), None)
    if hit is None or LEGALIZE_ONLY.search(clause):
        return None
    if NONRESIDENTIAL.search(clause) or MULTI_UNIT.search(clause) or SPLIT_LOTS.search(clause):
        return None
    return hit


def build(raw: pd.DataFrame, state: str = "OH") -> pd.DataFrame:
    """Legistar matters (MatterId, MatterFile, MatterTitle, MatterPassedDate, MatterStatusName) → ADU rows."""
    rows = []
    for m in raw.itertuples(index=False):
        hit = classify(m.MatterTitle, m.MatterStatusName, m.MatterPassedDate)
        if hit is None:
            continue
        clause = purpose(m.MatterTitle)
        cv = VARIANCE_NO.search(m.MatterTitle or "")
        district = DISTRICT.search(clause)
        rows.append(
            {
                "permit_id": f"CV-{cv.group(1)}" if cv else f"ORD-{m.MatterFile}",
                "issue_date": pd.Timestamp(m.MatterPassedDate).normalize(),
                "adu_type": hit[1],
                "permit_class_raw": f"council variance: {hit[0]} (Ord. {m.MatterFile})",
                "zoning_raw": district.group(1) if district else None,
            }
        )
    df = pd.DataFrame(rows, columns=["permit_id", "issue_date", "adu_type", "permit_class_raw", "zoning_raw"])
    # an ordinance that repeals and re-passes a variance keeps its variance number: keep the first passage
    df = df.sort_values("issue_date").drop_duplicates("permit_id")
    n = len(df)
    out = pd.DataFrame(
        {
            "state": state,
            "permit_id": df["permit_id"].astype(str),
            "parcel_id": pd.Series(pd.NA, index=df.index, dtype="string"),
            "jurisdiction_geoid": COLUMBUS_GEOID,
            "issue_year": df["issue_date"].dt.year.astype("Int64"),
            "issue_date": df["issue_date"].astype("datetime64[ns]"),
            "date_precision": "day",
            "building_type_std": "ADU",
            "type_confidence": "inferred",
            "adu_type": df["adu_type"],
            "permit_class_raw": df["permit_class_raw"],
            "units_new": pd.Series([1] * n, index=df.index, dtype="Int64"),
            "units_removed": pd.Series([0] * n, index=df.index, dtype="Int64"),
            "units_confidence": "inferred",
            "is_demolition": pd.Series([False] * n, index=df.index, dtype="boolean"),
            "is_conversion": pd.Series(pd.NA, index=df.index, dtype="boolean"),
            "zoning_raw": df["zoning_raw"].astype("string"),
            "source": NAME,
        }
    )
    return out.reset_index(drop=True)


def page_url(skip: int) -> str:
    from urllib.parse import urlencode

    query = {"$filter": FILTER, "$select": FIELDS, "$orderby": "MatterId", "$top": PAGE, "$skip": skip}
    return f"{API_URL}?{urlencode(query)}"


def download(store: DataStore, *, refresh: bool = False) -> pd.DataFrame:
    """Every Columbus variance ordinance, one cached JSON page of `PAGE` matters at a time."""
    frames, skip = [], 0
    while True:
        path = fetch(
            page_url(skip),
            Path(store.root) / "raw" / SOURCE / VINTAGE / f"variances_{skip:05d}.json",
            store=store,
            source=SOURCE,
            license=LICENSE,
            adapter=ADAPTER,
            adapter_version=VERSION,
            refresh=refresh,
        )
        page = json.loads(Path(path).read_text())
        frames.append(pd.DataFrame(page, columns=FIELDS.split(",")))
        if len(page) < PAGE:
            return pd.concat(frames, ignore_index=True)
        skip += PAGE


def load(state: str, store: DataStore, *, refresh: bool = False) -> pd.DataFrame:
    df = build(download(store, refresh=refresh), state=state)
    df = holdout.apply(
        df, state, geoid_col="jurisdiction_geoid", date_col="issue_date", year_col="issue_year"
    )
    return validate(df, TABLE)


PROVENANCE = {
    "title": "City of Columbus Council variance ordinances (Legistar Web API)",
    "landing_url": LANDING_URL,
    "table": TABLE,
    "cleaning": [
        f"Every ordinance with 'Variance' in its title ({FILTER}), paged {PAGE} at a time; only the id, file "
        "number, title, passed date and status are requested",
        "ADU approvals only, from named rules on the title's purpose clause (carriage or coach house, ADU, a "
        "dwelling above a garage, a second dwelling, two single-unit dwellings on one lot, a rear dwelling, "
        "habitable space above a detached garage)",
        "Dropped: not passed or later repealed; conforming an existing dwelling only; commercial, "
        "manufacturing or institutional districts; multi-unit buildings; dwellings on two or more lots",
        "One row per variance number (CV..), dated by the ordinance's passed date; titles are read in memory "
        "and never stored",
        "Holdout filter applied (Ohio has no holdouts)",
    ],
    "limitations": [
        "Approvals, not construction: the city reports 110 variances approved against 57 ADU permits for "
        "2019 to Sep 2025, so counts here are an upper bound on new ADUs",
        "Council approval precedes the building permit by months; the year can differ from the permit's",
        "'Habitable space above a detached garage' is counted (recall over precision) although some are "
        "studios or offices; its rows are labelled in permit_class_raw",
        "No parcel: the title's address is not matched, so a variance and the later permit for the same "
        "ADU are not linked (observed_adu_counts keeps the larger source per year, never the sum)",
        "Ends with Ord. 2526-2025 (effective 2025-12-24): ADUs need no variance after that",
    ],
}
