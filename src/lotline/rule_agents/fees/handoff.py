# ruff: noqa: E501  (plain-language strings and notes)
"""Human lookup tasks: what a person must open when the swarm cannot (docs/build/rule-agents/fees/HANDOFF_FORMAT.md).

One task per (place, levying body, component). A task says where to start, why the swarm stopped, what to look
for, the exact columns to fill and when it counts as done. Answered tasks come back as fee items
(`answers_to_items`) so the same build and checks apply.
"""

from __future__ import annotations

import csv
from collections.abc import Iterable
from datetime import date
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from lotline.rule_agents.fees.records import FeeItem

REASONS = {
    "robots_disallow": "the site's robots.txt asks automated readers not to open this page",
    "http_403_waf": "the site refuses automated readers (HTTP 403 or a bot check); it usually opens in a browser",
    "login_required": "the page is behind a login",
    "scanned_pdf": "the schedule is a scanned PDF the swarm could not read reliably",
    "buried_document": "the fees are inside a long budget book or ordinance the swarm could not locate within budget",
    "not_found": "no official schedule was found within the search budget",
    "summariser_only": "the page was read only through a summarising tool, so the numbers and quote need a check",
    "coders_disagree": "the two coders read different values and the page did not settle it",
    "verify_low": "a value rests on a mirror, draft or guide, not the adopted schedule",
    "budget_exhausted": "the place used up its request or reading budget",
}
# Closed without a task (Ben does not file records requests or email staff): R9
CLOSED = {"records_request_only": "only available on request: closed as no usable source"}

# Columns a person fills; their names match the FeeItem fields they become
ANSWER_FIELDS = [
    "answer_fee_type",
    "answer_building_type",
    "answer_basis_kind",
    "answer_amount",
    "answer_units_per_dwelling",
    "answer_effective_date",
    "answer_url",
    "answer_page_or_section",
    "answer_quote",
    "answered_by",
    "answered_date",
    "answer_notes",
]


class HumanTask(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str  # FEES-<ST>-<geoid>-<nn>
    state: str
    place_name: str
    place_geoid: str
    levying_body: str
    body_kind: Literal[
        "city", "county", "utility", "regional", "special_district", "school_district", "state"
    ] = "city"
    component: Literal["water_sewer", "impact", "permit", "planning", "other"]
    pays_for: str
    building_types: str = "SFD U2 U3_4 ADU"
    reason: str
    start_url: str
    other_urls: str = ""
    look_for: str  # plain words: what to find on the page
    fields_to_fill: str = (
        "answer_amount, answer_basis_kind, answer_effective_date, answer_page_or_section, answer_quote"
    )
    done_when: str = (
        "The amount is copied from the adopted schedule (not a guide or news), the quote is word for word and at most "
        "300 characters, and the effective date is the date the schedule took effect (not adopted). If the place "
        "charges no such fee, enter 0 and quote the line that says so."
    )
    priority: int = Field(ge=1, le=3)  # 1 = moves the place's total most
    est_minutes: int = 10
    status: Literal["open", "done", "no_usable_source"] = "open"
    answer_fee_type: str | None = None
    answer_building_type: str | None = None
    answer_basis_kind: str | None = None
    answer_amount: float | None = None
    answer_units_per_dwelling: float | None = None
    answer_effective_date: date | None = None
    answer_url: str | None = None
    answer_page_or_section: str | None = None
    answer_quote: str | None = Field(default=None, max_length=300)
    answered_by: str | None = None
    answered_date: date | None = None
    answer_notes: str | None = None


def make_task(n: int, **kw) -> HumanTask:
    """A task with id FEES-<ST>-<geoid>-<nn>. Refuses closed reasons (records requests are never tasks)."""
    reason = kw["reason"]
    if reason in CLOSED:
        raise ValueError(f"{reason}: {CLOSED[reason]}; record it in the run report, not as a task")
    if reason not in REASONS:
        raise ValueError(f"unknown reason {reason!r}; expected one of {sorted(REASONS)}")
    return HumanTask(task_id=f"FEES-{kw['state']}-{kw['place_geoid']}-{n:02d}", **kw)


def write_csv(tasks: Iterable[HumanTask], path: Path) -> None:
    fields = list(HumanTask.model_fields)
    with Path(path).open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for t in tasks:
            w.writerow({k: ("" if v is None else v) for k, v in t.model_dump().items()})


def read_csv(path: Path) -> list[HumanTask]:
    with Path(path).open(newline="") as f:
        # a blank cell means "not filled": leave it out so the field's default applies
        return [HumanTask.model_validate({k: v for k, v in r.items() if v != ""}) for r in csv.DictReader(f)]


def to_markdown(tasks: list[HumanTask]) -> str:
    """A checklist a person can work through, highest priority first."""
    out = [
        "# Fee lookups for a person",
        "",
        "Fill the `answer_*` columns of `human_tasks.csv` (same task id).",
        "",
    ]
    for t in sorted(tasks, key=lambda t: (t.priority, t.place_name, t.task_id)):
        out += [
            f"## {t.task_id} · {t.place_name} · {t.levying_body} · {t.component} (priority {t.priority}, ~{t.est_minutes} min)",
            f"- **Open:** {t.start_url}" + (f" (also: {t.other_urls})" if t.other_urls else ""),
            f"- **Why a person:** {REASONS[t.reason]}.",
            f"- **Look for:** {t.look_for}",
            f"- **Building types:** {t.building_types}",
            f"- **Fill:** {t.fields_to_fill}",
            f"- **Done when:** {t.done_when}",
            "",
        ]
    return "\n".join(out)


def answers_to_items(tasks: Iterable[HumanTask]) -> list[FeeItem]:
    """Answered tasks (status done, amount and quote filled) as fee items coded by the person."""
    items = []
    for t in tasks:
        if t.status != "done" or t.answer_amount is None or not t.answer_quote:
            continue
        items.append(
            FeeItem(
                item_id=f"{t.task_id}-ans",
                state=t.state,
                place_geoid=t.place_geoid,
                place_name=t.place_name,
                levying_body=t.levying_body,
                body_kind=t.body_kind,
                fee_type=t.answer_fee_type or f"{t.levying_body} {t.pays_for} fee",
                pays_for=t.pays_for,
                building_type=t.answer_building_type or "SFD",
                basis_kind=t.answer_basis_kind or "per_unit",
                amount=t.answer_amount,
                units_per_dwelling=t.answer_units_per_dwelling,
                effective_date=t.answer_effective_date,
                url=t.answer_url or t.start_url,
                retrieved_at=t.answered_date,
                page_or_section=t.answer_page_or_section,
                quote=t.answer_quote,
                quote_status="verbatim",  # a person read the page
                coder=f"human:{t.answered_by or 'unknown'}",
                notes=t.answer_notes,
            )
        )
    return items
