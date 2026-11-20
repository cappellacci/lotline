"""The coder's per-place output (a "finding") and the checks it must pass.

One JSON file per place and coder: `findings/<geoid>.<coder>.json` in the run folder. A finding lists every
missing-middle rule the coder found for the place (zero or more `RuleFinding`s), plus any `Blocker`s: sources
the coder needed but could not read. A place with no rule allowing 2-4 homes on single-family lots gets one
"none" rule (`unit_cap` = 1), with evidence, so it can serve as an untreated comparison; a place the coder
could not settle gets no rule and at least one blocker.

**Evidence rule:** every coded field in `EVIDENCED_FIELDS` that is not blank has at least one `Evidence`
entry naming it, with a URL, a verbatim quote of at most 300 characters and the retrieval date. The quote
must appear in the stored document (`docs quote`); the verifier agent re-checks this. The evidence and
blocker models and the text helpers live in the shared core (`lotline.rule_agents.common`).
"""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from lotline.rule_agents.common.dates import ALL_TAGS, DATE_BASES
from lotline.rule_agents.common.evidence import (  # noqa: F401 - re-exported for the MM agents and tests
    BLOCKER_KINDS,
    CONFIDENCE,
    LEAD_ONLY,
    QUOTE_MAX,
    Blocker,
    Evidence,
)
from lotline.rule_agents.common.text import draft_markers, verify_quote, visible_text  # noqa: F401

# Fields that, when coded, must each be backed by a quote. Dates count through `effective_date` (and
# `adoption_date` when given): a coder may cite one passage for both.
EVIDENCED_FIELDS = (
    "adoption_date",
    "effective_date",
    "unit_cap",
    "by_right",
    "owner_occ",
    "min_lot_sqft",
    "lot_split",
    "parking_min_per_unit",
    "coverage_zones",
    "end_date",
    "prior_cap",
)
# The fields two coders are compared on (`reconcile`) and the dry run checks (`compare`).
KEY_FIELDS = (
    "effective_date",
    "adoption_date",
    "date_basis",
    "unit_cap",
    "prior_cap",
    "by_right",
    "coverage_zones",
)


class RuleFinding(BaseModel):
    component: str  # plain-language name: "Ord. 2019-048: up to 3 units in R1-R2B"
    status: Literal["in_force", "suspended", "repealed", "opted_out", "pending"] = "in_force"
    announced_date: date | None = None
    adoption_date: date | None = None
    effective_date: date
    end_date: date | None = None
    date_basis: Literal[DATE_BASES]  # type: ignore[valid-type]
    date_precision: Literal["day", "month", "year"] = "day"
    unit_cap: int | None = Field(default=None, ge=1)  # most homes per single-family lot; 1 = "none" row
    by_right: bool | None = None  # False: needs a special/conditional use permit or rezoning
    owner_occ: bool | None = None
    min_lot_sqft: float | None = Field(default=None, ge=0)
    lot_split: bool | None = None
    max_stories: float | None = Field(default=None, ge=0)
    far_cap: float | None = Field(default=None, ge=0)
    parking: str | None = None
    parking_min_per_unit: float | None = Field(default=None, ge=0)
    # The MM-specific check (NC/TX second coding, 2026-11-11): what the code allowed on these lots just
    # before this rule. An event needs prior_cap < unit_cap, with evidence from the predecessor code (often
    # a Wayback copy plus the new code's district-conversion table). Equal caps mean a recodification:
    # code the rule `predates` instead (League City 2020, Wake Forest, Morrisville).
    prior_cap: int | None = Field(default=None, ge=1)
    standards_only: bool = False  # [standards]: the cap doesn't rise, the by-right route gets easier
    coverage: str  # plain-language area: "Citywide R1, R1A, R2, R2B"
    coverage_zones: list[str] = Field(default_factory=list)
    supersedes_effective: date | None = None  # effective date of the earlier rule this amends, if any
    confidence: Literal[CONFIDENCE] = "medium"  # type: ignore[valid-type]
    evidence: list[Evidence]
    notes: str = ""


class PlaceFinding(BaseModel):
    state: str = Field(pattern=r"^[A-Z]{2}$")
    jurisdiction_geoid: str = Field(pattern=r"^(\d{2}|\d{5}|\d{7}|\d{10})$")
    place: str
    coder: str  # e.g. "rules-mm-coder-a"
    coded_on: date
    rules: list[RuleFinding] = Field(default_factory=list)
    blockers: list[Blocker] = Field(default_factory=list)
    searched: list[str] = Field(default_factory=list)  # URLs and queries tried, for the audit trail
    notes: str = ""


def check(f: PlaceFinding, *, today: date | None = None) -> list[str]:
    """Problems that stop a finding from going on to reconciliation (empty list: it passes).

    By hand: a rule with unit_cap 3 and no evidence naming unit_cap -> "unit_cap has no evidence"; a
    `dated` rule with month precision -> must be earliest_known or unconfirmed; effective before adoption ->
    flagged; a place with no rules and no blockers -> flagged (nothing settled, nothing handed off).
    """
    today = today or date.today()
    out: list[str] = []
    if not f.rules and not f.blockers:
        out.append("no rules and no blockers: code a 'none' rule (unit_cap 1) with evidence or hand off")
    seen_eff: set[date] = set()
    for i, r in enumerate(f.rules):
        tag = f"rule {i} ({r.effective_date})"
        cited = {e.field for e in r.evidence}
        for fld in EVIDENCED_FIELDS:
            v = getattr(r, fld)
            if v not in (None, [], "") and fld not in cited:
                if fld == "adoption_date" and "effective_date" in cited:
                    continue  # one passage may give both dates
                out.append(f"{tag}: {fld} has no evidence")
        if not r.evidence:
            out.append(f"{tag}: no evidence at all")
        if any(t in r.notes for t in ALL_TAGS):
            out.append(f"{tag}: notes contain an engine tag: set date_basis/standards_only instead")
        if r.date_basis == "dated" and r.date_precision != "day":
            out.append(f"{tag}: a {r.date_precision}-precision date must be earliest_known or unconfirmed")
        if r.date_basis == "dated" and r.adoption_date is None:
            out.append(f"{tag}: dated rule needs an adoption_date (else code earliest_known)")
        if r.adoption_date and r.effective_date < r.adoption_date:
            out.append(f"{tag}: effective_date before adoption_date")
        if r.end_date and r.end_date <= r.effective_date:
            out.append(f"{tag}: end_date not after effective_date")
        if r.effective_date > today and r.status == "in_force":
            out.append(f"{tag}: effective in the future: status should be 'pending'")
        if r.unit_cap is None and not r.standards_only:
            out.append(f"{tag}: unit_cap blank: code the cap (1 for a 'none' row) or mark standards_only")
        is_event = r.status == "in_force" and r.date_basis != "predates" and (r.unit_cap or 0) > 1
        if is_event and not r.standards_only and r.effective_date.year >= 2010:
            handed_off = any("prior_cap" in b.fields for b in f.blockers)
            if r.prior_cap is None and not handed_off:
                out.append(
                    f"{tag}: event with no prior_cap: check what the code allowed just before, or hand off "
                    "the predecessor code as a Blocker naming prior_cap"
                )
            elif r.prior_cap is not None and r.unit_cap is not None and r.prior_cap >= r.unit_cap:
                out.append(
                    f"{tag}: prior_cap {r.prior_cap} >= unit_cap {r.unit_cap}: no cap rise; code it "
                    "'predates' (recodification) or 'standards_only' (cheaper route, same cap)"
                )
        for fld in cited:
            kinds = {e.source_kind for e in r.evidence if e.field == fld}
            if kinds and kinds <= set(LEAD_ONLY):
                out.append(f"{tag}: {fld} rests only on {sorted(kinds)}: a lead, not evidence")
            if kinds == {"mirror"} and r.confidence == "high":
                out.append(f"{tag}: {fld} read on a mirror only: confidence cannot be high")
        if r.unit_cap == 1 and r.standards_only:
            out.append(f"{tag}: a 'none' row (unit_cap 1) cannot be standards_only")
        if r.unit_cap == 1 and r.date_basis != "predates" and r.by_right:
            out.append(f"{tag}: unit_cap 1 with by_right=True: a 'none' row allows no extra homes")
        if r.effective_date in seen_eff:
            out.append(f"{tag}: two rules share an effective date: merge them or split by zone in coverage")
        seen_eff.add(r.effective_date)
        for e in r.evidence:
            if e.retrieved > today:
                out.append(f"{tag}: evidence retrieved in the future ({e.retrieved})")
    for b in f.blockers:
        if b.kind != "records_request_only" and not b.fields:
            out.append(f"blocker {b.url}: name the field(s) it would settle")
    return out
