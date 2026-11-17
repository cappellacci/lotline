"""Score the first coder's work so the second look goes only where the evidence is weak (Ben, 2026-11-17).

The blind second coder used to recode every field of every place (about 40% of a run's tokens in the NC dry
run). Now a single coder runs, every value is scored, and only weak values (plus eras the scout found but the
coder did not code) get a blind, targeted second look. A small, fixed sample of places is still second-coded
in full (`AUDIT_RATE`) so the run can report how often a "strong" value turned out wrong.

A value is **strong** when all of these hold, and **weak** otherwise (the reasons are listed):

- confidence is `high`;
- at least one primary source (official code, ordinance, staff report, minutes, state law, human-primary);
- that source's quote was **checked by machine**: verbatim, and found in the cached text copy (HTML, or a
  text PDF on the page the coder named). An image-read or unchecked quote is never strong.

Dates are scored on the resolved date: weak when `dates.resolve` tags it `DATE UNCONFIRMED` or
`[earliest-known]`, or when no date evidence of the deciding type passes the checks above (confidence is not
recorded for dates; a primary, machine-checked source stands in for it).

A core field (`CORE_FIELDS`) the coder did not address at all (no entry, no blocked source) is also weak: the
coder found nothing and said nothing, so a second look may find it. A deliberate blank (an entry with a note,
e.g. a floor-not-cap size rule) is not, and neither is a blank that a blocked source covers (a human task).
`coverage_zones` and `min_lot_sqft` are blank by rule when citywide or absent, so they are never "missing".

**Amendment leads.** An ordinance the scout listed (`sources/<geoid>.json`, kind `ordinance`, or a `what`
naming an ordinance or amendment) dated 2016 or later whose year matches no coded era is an `uncoded
amendment`: both NC dry-run coders missed such amendments (Raleigh 2022, Wilmington 2022).
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from lotline.rule_agents.adu import dates as D
from lotline.rule_agents.adu.coding import RUBRIC_FIELDS, Era, Evidence, FieldValue, PlaceCoding
from lotline.rule_agents.adu.fetch import quote_in_text, quote_page

AUDIT_RATE = 0.10  # share of places second-coded in full, chosen by a hash of the GEOID (reproducible)
DATE_FIELDS = ("effective_date", "adoption_date")
SCORED_FIELDS = tuple(f for f in RUBRIC_FIELDS if f not in ("parking", "coverage"))  # free text: not compared
CORE_FIELDS = (
    "adus_per_lot",
    "by_right",
    "owner_occ",
    "adu_detached_allowed",
    "adu_max_sqft",
    "parking_min_per_unit",
)
_AMENDMENT = re.compile(r"\b(ord(inance)?\.?|amend\w*|TC-\d|text (change|amendment))", re.I)
_YEAR = re.compile(r"\b(20[12]\d)\b")


def quote_check(e: Evidence, root: Path) -> tuple[str, int | None]:
    """('found' | 'missing' | 'unchecked', page). `unchecked`: image-read or human quote, no cached copy,
    or no text copy (scanned or unparseable PDF)."""
    if e.quote_status != "verbatim" or not e.cache_path:
        return "unchecked", None
    src = root / e.cache_path
    txt = src.with_suffix(".txt")
    if not txt.exists():
        return "unchecked", None
    text = txt.read_text()
    if src.suffix == ".pdf":
        page = quote_page(e.quote, text)
        if page is None or (e.page is not None and e.page != page):
            return "missing", page
        return "found", page
    return ("found" if quote_in_text(e.quote, text) else "missing"), None


def _evidence_problems(evs: list[Evidence], root: Path) -> list[str]:
    primary = [e for e in evs if e.primary]
    if not primary:
        return ["no primary source"]
    checks = [quote_check(e, root)[0] for e in primary]
    if "found" in checks:
        return []
    if "missing" in checks:
        return ["quote not found in the cached source"]
    return ["quote not machine-checked (image-read, no text copy or no cache)"]


def value_problems(fv: FieldValue, root: Path) -> list[str]:
    out = [] if fv.confidence == "high" else [f"confidence {fv.confidence}"]
    return out + _evidence_problems(fv.evidence, root)


def date_problems(era: Era, which: str, root: Path) -> list[str]:
    r = D.resolve(era.dates)
    if which == "adoption_date" and r.adoption is None:
        return []  # nothing coded; the effective date carries the era
    out = [t for t in r.tags if t in ("DATE UNCONFIRMED", "[earliest-known]")]
    deciding = {"effective_date": ("effective",), "adoption_date": ("adopted", "vote")}[which]
    evs = [e for d in era.dates if d.type in deciding for e in d.evidence]
    if not evs:  # the date came from a bound or adoption date: judge the evidence that fired the rule
        evs = [e for d in era.dates if d.type != "announced" for e in d.evidence]
    return out + _evidence_problems(evs, root)


@dataclass
class Look:
    """One value the second coder must code blind: an era (named by its resolved effective date) + field."""

    era_key: str
    field: str
    reasons: list[str]


@dataclass
class Scorecard:
    geoid: str
    name: str
    mode: str  # "none" (all strong, or nothing coded) | "targeted" | "full" (audit sample)
    strong: int = 0
    weak: int = 0
    looks: list[Look] = field(default_factory=list)
    uncoded_amendments: list[str] = field(default_factory=list)

    @property
    def fields(self) -> list[str]:
        """Field names the targeted second coder codes (dates always, so its eras can be matched)."""
        return sorted({lk.field for lk in self.looks} | set(DATE_FIELDS))


def in_audit(geoid: str, rate: float = AUDIT_RATE) -> bool:
    return int(hashlib.sha256(geoid.encode()).hexdigest()[:8], 16) / 0xFFFFFFFF < rate


def uncoded_amendments(coding: PlaceCoding, sources: dict | None) -> list[str]:
    if not sources:
        return []
    years = set()
    for era in coding.eras:
        years |= {d.date.year for d in era.dates}
    out = []
    for s in sources.get("sources", []):
        what = s.get("what", "")
        if s.get("kind") != "ordinance" and not _AMENDMENT.search(what):
            continue
        seen = {int(y) for txt in [what, *s.get("dates_seen", [])] for y in _YEAR.findall(txt)}
        seen = {y for y in seen if y >= D.WINDOW_START.year}
        if seen and not seen & years:
            out.append(f"{what} ({', '.join(map(str, sorted(seen)))}) {s.get('url', '')}".strip())
    return out


def score(
    coding: PlaceCoding, root: Path, sources: dict | None = None, audit_rate: float = AUDIT_RATE
) -> Scorecard:
    card = Scorecard(coding.geoid, coding.name, "none")
    covered = {f for b in coding.blocked for f in (b.fields or [])}
    for era in coding.eras:
        key = str(D.resolve(era.dates).effective)
        for f in DATE_FIELDS:
            probs = date_problems(era, f, root)
            if probs:
                card.looks.append(Look(key, f, probs))
        for f in SCORED_FIELDS:
            fv = era.fields.get(f)
            if fv is None:
                silent = f in CORE_FIELDS and not covered & {f, "all"} and era.value("adus_per_lot") != 0
                if silent:
                    card.looks.append(Look(key, f, ["not addressed and no blocked source"]))
                continue
            if fv.value is None:
                continue  # deliberate blank, explained in its note
            probs = value_problems(fv, root)
            if probs:
                card.looks.append(Look(key, f, probs))
            else:
                card.strong += 1
    card.weak = sum(1 for lk in card.looks if lk.reasons != ["not addressed and no blocked source"])
    card.uncoded_amendments = uncoded_amendments(coding, sources)
    if not coding.eras:
        card.mode = "none"  # nothing coded: the blocked sources go straight to human tasks
    elif in_audit(coding.geoid, audit_rate):
        card.mode = "full"
    elif card.looks or card.uncoded_amendments:
        card.mode = "targeted"
    return card


def to_json(card: Scorecard) -> str:
    d = asdict(card)
    d["second_coder_fields"] = (
        card.fields if card.mode == "targeted" else ("all" if card.mode == "full" else [])
    )
    return json.dumps(d, indent=1)
