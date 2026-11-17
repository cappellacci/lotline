"""Records the fees rule agents write: fee items (one line of a fee schedule, with its evidence).

An item stays close to the source and holds no derived numbers. `build.py` turns items into `fees` rows.
See docs/build/rule-agents/fees/DESIGN.md ("The unit of work: a fee item").
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import date
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

BodyKind = Literal["city", "county", "utility", "regional", "special_district", "school_district", "state"]
BuildingType = Literal["SFD", "U2", "U3_4", "ADU", "OTHER"]
BasisKind = Literal[
    "per_unit",
    "per_building",
    "per_sqft",
    "per_lue",
    "per_meter",
    "valuation_table",
    "pct_of_value",
    "share_of",
    "per_bedroom",
    "per_fixture",
    "per_trip",
    "per_acre",
    "conditional",
    "excluded",
]
QuoteStatus = Literal["verbatim", "image_read", "summariser", "none"]
Confidence = Literal["high", "medium", "low"]
GroupKind = Literal["area", "plat_date"]

# basis kinds that carry a number the helper prices (so they need evidence)
PRICED = {
    "per_unit",
    "per_building",
    "per_sqft",
    "per_lue",
    "per_meter",
    "valuation_table",
    "pct_of_value",
    "share_of",
    "per_bedroom",
    "per_fixture",
    "per_trip",
}


class FeeItem(BaseModel):
    """One fee line from one source, as a coder (agent or person) read it."""

    model_config = ConfigDict(extra="forbid")

    item_id: str
    state: str = Field(pattern=r"^[A-Z]{2}$")
    place_geoid: str
    place_name: str
    levying_body: str
    body_kind: BodyKind
    fee_type: str  # the source's own name
    pays_for: str  # what the fee funds, e.g. "water", "parks", "building_permit" (classify.PAYS_FOR)
    building_type: BuildingType
    basis_kind: BasisKind
    amount: float | None = Field(default=None, ge=0)
    # valuation table bracket: fee = base + rate_per_1000 * ceil((V - start) / 1000), for start <= V <= end
    bracket_base: float | None = Field(default=None, ge=0)
    bracket_start: float | None = Field(default=None, ge=0)
    bracket_end: float | None = Field(default=None, ge=0)
    rate_per_1000: float | None = Field(default=None, ge=0)
    pct: float | None = Field(default=None, ge=0, le=100)  # pct_of_value and share_of
    share_of: str | None = None  # item_id of the parent fee (share_of)
    units_per_dwelling: float | None = Field(default=None, ge=0)  # per_lue: LUE/EDU/SAC units per dwelling
    quantity_per_unit: float | None = Field(default=None, ge=0)  # per_fixture / per_trip assumption
    master_meter_amount: float | None = Field(
        default=None, ge=0
    )  # per_meter: one shared meter, whole building
    group_id: str | None = None
    group_kind: GroupKind | None = None
    cohort_start: date | None = None  # plat-date groups: start of the cohort
    schedule_label: str | None = None  # e.g. "FY2027"
    adopted_date: date | None = None
    effective_date: date | None = None
    fiscal_year_start: date | None = None
    in_force_through: int | None = None
    payment_timing: str | None = None
    url: str | None = None
    local_path: str | None = None  # path under LOTLINE_DATA_DIR
    sha256: str | None = None
    retrieved_at: date | None = None
    page_or_section: str | None = None
    quote: str | None = Field(default=None, max_length=300)
    quote_status: QuoteStatus = "none"
    source_kind: Literal["official", "mirror", "draft", "guide", "wayback"] = "official"
    applies_when: str | None = None  # conditions (conditional / excluded) or the column/tier read
    confidence: Confidence | None = None
    coder: str
    verified_by: str | None = None  # set by reconcile when the blind second coder read the same value
    verified_date: date | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def _numbers_for_basis(self) -> FeeItem:
        need = {
            "valuation_table": ("bracket_base", "bracket_start", "rate_per_1000"),
            "pct_of_value": ("pct",),
            "share_of": ("pct", "share_of"),
        }.get(self.basis_kind)
        if need is None and self.basis_kind in PRICED:
            need = ("amount",)
        missing = [f for f in need or () if getattr(self, f) is None]
        if missing:
            raise ValueError(f"{self.item_id}: basis_kind {self.basis_kind} needs {', '.join(missing)}")
        if self.group_id and not self.group_kind:
            raise ValueError(f"{self.item_id}: group_id without group_kind")
        return self

    def has_evidence(self) -> bool:
        """URL, retrieval date, page/section and a quote that was read (not summarised)."""
        return bool(
            self.url
            and self.retrieved_at
            and self.page_or_section
            and self.quote
            and self.quote_status in ("verbatim", "image_read")
        )


def read_items(path: Path) -> list[FeeItem]:
    """Items from a JSON-lines file (blank lines skipped)."""
    lines = Path(path).read_text().splitlines()
    return [FeeItem.model_validate_json(line) for line in lines if line.strip()]


def write_items(items: Iterable[FeeItem], path: Path) -> None:
    Path(path).write_text("".join(i.model_dump_json(exclude_none=True) + "\n" for i in items))


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]
