"""Choose an era's `adoption_date` and `effective_date` from its dated evidence (lessons register §2).

Rules, in order (each result says which rule fired, for `coding_notes`):

1. **Effective date found** (`effective`): use it. Two different effective dates are a conflict
   for the verifier.
2. **Adoption only** (`adopted` or `vote`): effective = adoption, note "effective date not found: coded as the
   adoption date" and tag `DATE UNCONFIRMED` (NC/OH convention; a computed "+30 days" is never used: Columbus
   was off by one day, LB-071).
3. **Only a bound** (`codified`, `first_seen`, `in_force_by`): effective = the earliest bound, tag
   `[earliest-known]` (a recodification or code edition inside the window is not a reform event; the
   first-allowed question goes to a human task). If the bound is on or before the window start, the era is
   in force at window start: dated `window_start` and tagged `[predates]` (WS-ADU-RULES convention 6).
4. Month or year precision is placed on the first day of the period and noted.

5. **Only `prior_to`** (the state before a dated reform, start unknown): dated at the window start (or the day
   before `prior_to` when that is earlier) and tagged `[predates]`.

`announced` dates feed `announced_date` only. Date-quality tags come only from here, never from a coder.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

from lotline.rule_agents.adu.coding import DateEvidence

WINDOW_START = dt.date(2016, 1, 1)  # WS-ADU-RULES convention 6; the fit window opens in 2016
FLOOR_2010 = dt.date(2010, 1, 1)  # older TX/OH convention, kept as an option


@dataclass
class ResolvedDates:
    effective: dt.date
    adoption: dt.date | None
    announced: dt.date | None
    rule: str
    tags: list[str] = field(default_factory=list)
    conflict: str | None = None


def _first_day(d: DateEvidence) -> dt.date:
    if d.precision == "year":
        return dt.date(d.date.year, 1, 1)
    if d.precision == "month":
        return d.date.replace(day=1)
    return d.date


def resolve(dates: list[DateEvidence], window_start: dt.date = WINDOW_START) -> ResolvedDates:
    if not dates:
        raise ValueError("an era needs at least one dated source")
    by = lambda *types: [d for d in dates if d.type in types]  # noqa: E731
    announced = min((_first_day(d) for d in by("announced")), default=None)
    adopted = by("adopted", "vote")
    adoption = min((_first_day(d) for d in by("adopted")), default=None) or min(
        (_first_day(d) for d in by("vote")), default=None
    )
    effective = by("effective")
    tags: list[str] = []
    rough = [d for d in dates if d.precision != "day" and d.type != "announced"]
    note = f"; {rough[0].type} date known to the {rough[0].precision} only" if rough else ""

    if effective:
        days = sorted({_first_day(d) for d in effective})
        conflict = None
        if len(days) > 1:
            conflict = "sources give different effective dates: " + ", ".join(map(str, days))
        return ResolvedDates(
            days[0], adoption, announced, "effective date from source" + note, tags, conflict
        )
    if adopted:
        tags.append("DATE UNCONFIRMED")
        return ResolvedDates(
            adoption, adoption, announced, "effective date not found: coded as the adoption date" + note, tags
        )
    bounds = by("codified", "first_seen", "in_force_by")
    if not bounds:
        prior = by("prior_to")
        if not prior:
            raise ValueError("only an announced date: not enough to date an era")
        until = min(_first_day(d) for d in prior)
        start = window_start if until > window_start else until - dt.timedelta(days=1)
        return ResolvedDates(
            start,
            None,
            announced,
            f"in force until {until}; start unknown: dated {start} and tagged [predates]" + note,
            ["[predates]"],
        )
    earliest = min(bounds, key=_first_day)
    day = _first_day(earliest)
    if day <= window_start:
        tags.append("[predates]")
        return ResolvedDates(
            window_start,
            None,
            announced,
            f"in force by {day} ({earliest.type}); first-allowed date unknown: dated at window start "
            f"{window_start} and tagged [predates]" + note,
            tags,
        )
    # A bound inside the window (a 2019 recodification, a 2021 code edition) is not a reform event by itself:
    # dated at the bound, tagged [earliest-known], and the first-allowed question goes to a human task.
    tags.append("[earliest-known]")
    return ResolvedDates(
        day,
        None,
        announced,
        f"earliest dated source ({earliest.type}) {day}; adoption not found, first-allowed date open" + note,
        tags,
    )
