"""The JSON a coder writes for one place, and the checks every coding must pass.

A place's ADU history is a list of **eras**: the first rule (or an explicit "no ADUs" rule) and each later
version that changed a coded field. Each era carries the rubric fields of the `reforms` schema plus dated
evidence. Every non-blank value cites at least one source: URL, retrieval date, verbatim quote (<= 300
characters, the schema's `source_quote` limit; coders aim for <= 25 words) and, where the source has one, a
section number. Blank means "not found", never "no restriction" (D-022).

The checks are deterministic so the orchestrator can refuse a coding before it reaches reconciliation.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Source kinds. Primary sources can carry "high" confidence on their own; the rest cap a value at "medium"
# (lessons L-R4, L-S3: a mirror, city guide, draft or news report is at most "partly" for a second coder).
PRIMARY_KINDS = {"official_code", "ordinance", "staff_report", "minutes", "state_law", "human_primary"}
SECONDARY_KINDS = {"city_page", "mirror", "news", "draft", "human_secondary"}
SourceKind = Literal[
    "official_code",
    "ordinance",
    "staff_report",
    "minutes",
    "state_law",
    "human_primary",
    "city_page",
    "mirror",
    "news",
    "draft",
    "human_secondary",
]
Confidence = Literal["high", "medium", "low"]
# What a dated source says about the date. Only `effective` and `adopted` are treatment dates; the others
# bound it (lesson L-D3: a recodification or code-edition date is not a first-allowed date).
DateType = Literal["effective", "adopted", "vote", "codified", "first_seen", "in_force_by", "announced"]

BOOL_FIELDS = ("by_right", "owner_occ", "adu_detached_allowed")
NUM_FIELDS = ("adu_max_sqft", "parking_min_per_unit", "min_lot_sqft")
INT_FIELDS = ("adus_per_lot",)
TEXT_FIELDS = ("parking", "coverage", "coverage_zones")
RUBRIC_FIELDS = INT_FIELDS + BOOL_FIELDS + NUM_FIELDS + TEXT_FIELDS
# Tags carried into coding_notes (existing conventions, docs/research/ordinances/README.md).
TAGS = {
    "[predates]",  # in force at window start, first date unknown or only a recodification date
    "[earliest-known]",  # date is the earliest dated source found, not a confirmed first-allowed date
    "[detached-conditional]",  # attached by right, detached needs a CUP/SUP/IUP
    "[moratorium]",
    "DATE UNCONFIRMED",  # no signed ordinance or effective-date record
}


class Evidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str
    retrieved: dt.date
    quote: str = Field(min_length=1, max_length=300)
    section: str | None = None
    kind: SourceKind
    archived_from: str | None = None  # the live URL when `url` is a Wayback copy
    cache_path: str | None = None  # path under LOTLINE_DATA_DIR of the copy the quote was read from

    @field_validator("url")
    @classmethod
    def _https(cls, v: str) -> str:
        if not v.startswith("https://"):
            raise ValueError(f"source URL must be https (use a Wayback https copy for http-only pages): {v}")
        return v

    @property
    def primary(self) -> bool:
        return self.kind in PRIMARY_KINDS


class FieldValue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: Any = None
    evidence: list[Evidence] = []
    confidence: Confidence = "medium"
    note: str | None = None


class DateEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date: dt.date
    type: DateType
    precision: Literal["day", "month", "year"] = "day"
    evidence: list[Evidence] = Field(min_length=1)
    note: str | None = None


class Era(BaseModel):
    """One rule version. `fields` keys are RUBRIC_FIELDS; a missing key is the same as blank."""

    model_config = ConfigDict(extra="forbid")

    era_id: str
    component: str
    # A moratorium is an in-force "no ADUs" era tagged [moratorium], never `suspended`: every engine
    # filter drops suspended rows, so the place would read as unrestricted (lessons register L-F4).
    status: Literal["in_force", "repealed"] = "in_force"
    dates: list[DateEvidence] = Field(min_length=1)
    fields: dict[str, FieldValue] = {}
    tags: list[str] = []
    end_date: dt.date | None = None

    def value(self, field: str) -> Any:
        fv = self.fields.get(field)
        return None if fv is None else fv.value


class BlockedSource(BaseModel):
    """A source the coder could not read; becomes a human lookup task (handoff.py)."""

    model_config = ConfigDict(extra="forbid")

    url: str
    reason: str  # handoff.REASONS key
    era_id: str | None = None
    fields: list[str] = []
    what_to_look_for: str
    note: str | None = None


class PlaceCoding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    state: str = Field(pattern=r"^[A-Z]{2}$")
    geoid: str = Field(pattern=r"^\d{2}(\d{3}|\d{5})?$")
    name: str
    coder: str
    coded_at: dt.date
    outcome: Literal["coded", "partial", "no_usable_source"]
    eras: list[Era] = []
    blocked: list[BlockedSource] = []
    notes: str | None = None


def load(path: str | Path) -> PlaceCoding:
    return PlaceCoding.model_validate(json.loads(Path(path).read_text()))


def dump(coding: PlaceCoding, path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(coding.model_dump_json(indent=2, exclude_none=True) + "\n")


def _type_problem(field: str, v: Any) -> str | None:
    if field in BOOL_FIELDS and not isinstance(v, bool):
        return f"{field} must be true/false, got {v!r}"
    if field in INT_FIELDS and (isinstance(v, bool) or not isinstance(v, int) or v < 0):
        return f"{field} must be a whole number >= 0, got {v!r}"
    if field in NUM_FIELDS and (isinstance(v, bool) or not isinstance(v, (int, float)) or v < 0):
        return f"{field} must be a number >= 0, got {v!r}"
    if field in TEXT_FIELDS and not isinstance(v, str):
        return f"{field} must be text, got {v!r}"
    return None


def check(coding: PlaceCoding) -> list[str]:
    """Every problem that blocks a coding from reconciliation (empty list = passes)."""
    out: list[str] = []
    seen: set[str] = set()
    if coding.outcome == "coded" and not coding.eras:
        out.append("outcome 'coded' needs at least one era")
    if coding.outcome == "no_usable_source" and coding.eras:
        out.append("outcome 'no_usable_source' must not carry eras")
    for era in coding.eras:
        where = f"era {era.era_id}"
        if era.era_id in seen:
            out.append(f"{where}: duplicate era_id")
        seen.add(era.era_id)
        for tag in era.tags:
            if tag not in TAGS:
                out.append(f"{where}: unknown tag {tag!r} (allowed: {sorted(TAGS)})")
        for field, fv in era.fields.items():
            if field not in RUBRIC_FIELDS:
                out.append(f"{where}: unknown field {field!r}")
                continue
            if fv.value is None:
                continue
            problem = _type_problem(field, fv.value)
            if problem:
                out.append(f"{where}: {problem}")
            if not fv.evidence:
                out.append(f"{where}: {field} = {fv.value!r} has no evidence (blank it or cite a source)")
            elif fv.confidence == "high" and not any(e.primary for e in fv.evidence):
                out.append(f"{where}: {field} is 'high' confidence on secondary sources only (cap at medium)")
        if era.value("adus_per_lot") == 0:
            for f in ("by_right", "adu_detached_allowed"):
                if era.value(f) is True:
                    out.append(f"{where}: a 'no ADUs' era (adus_per_lot = 0) cannot have {f} = true")
        if "[moratorium]" in era.tags and era.value("adus_per_lot") != 0:
            out.append(f"{where}: a [moratorium] era is coded as 'no ADUs' (adus_per_lot = 0)")
        if not any(fv.value is not None for fv in era.fields.values()):
            out.append(f"{where}: no field coded (a dateless or valueless era is not a rule; drop it)")
    return out
