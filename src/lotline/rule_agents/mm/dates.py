"""Date parsing and date-basis tags for missing-middle rule rows.

Ordinances state dates many ways ("adopted November 8, 2019", "Ord. 2019-048, eff. 1/1/20", "FY2024"). The
coder copies the source's own wording into evidence; `parse_date` turns it into an ISO date, refusing
anything it cannot read to the day unless the caller accepts month or year precision.

`date_basis` says how sure the coded date is. It maps one-to-one onto the free-text tags that
`lotline.model.rule_tags` reads from `coding_notes` (the engine has no `date_basis` column yet):

- `dated` (no tag): an event at its effective date.
- `predates` -> `[predates]`: in force before the panel; never an event (an always-allowed place).
- `earliest_known` -> `[earliest-known]`: the earliest date the sources show; a sensitivity drops it.
- `unconfirmed` -> `DATE UNCONFIRMED`: no signed ordinance or effective-date record; a sensitivity drops it.

`standards_only` adds `[standards]` (D-092 §1b): the cap does not rise but the by-right route gets cheaper,
e.g. Houston's 2023 MUR route. Such rows stay in the fit; they are not "no change" rows.
"""

from __future__ import annotations

import re
from datetime import date

DATE_BASES = ("dated", "predates", "earliest_known", "unconfirmed")
TAGS = {
    "predates": "[predates]",
    "earliest_known": "[earliest-known]",
    "unconfirmed": "DATE UNCONFIRMED",
}
STANDARDS_TAG = "[standards]"
ALL_TAGS = (*TAGS.values(), STANDARDS_TAG)

_MONTHS = {
    m: i + 1
    for i, names in enumerate(
        [
            ("jan", "january"),
            ("feb", "february"),
            ("mar", "march"),
            ("apr", "april"),
            ("may",),
            ("jun", "june"),
            ("jul", "july"),
            ("aug", "august"),
            ("sep", "sept", "september"),
            ("oct", "october"),
            ("nov", "november"),
            ("dec", "december"),
        ]
    )
    for m in names
}
_ISO = re.compile(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b")
_US = re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{2}|\d{4})\b")
_LONG = re.compile(r"\b([A-Za-z]{3,9})\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})\b")
_DAY_FIRST = re.compile(r"\b(\d{1,2})\s+([A-Za-z]{3,9})\.?,?\s+(\d{4})\b")
_MONTH_YEAR = re.compile(r"\b([A-Za-z]{3,9})\.?,?\s+(\d{4})\b")
_YEAR = re.compile(r"\b(19[5-9]\d|20\d\d)\b")


class DateParseError(ValueError):
    """The text holds no date at the precision the caller asked for."""


def _two_digit_year(y: int) -> int:
    # Ordinance dates in this project run 1950-2049: "1/1/20" is 2020, "6/3/98" is 1998.
    return 2000 + y if y < 50 else 1900 + y


def parse_date(text: str, *, precision: str = "day") -> tuple[date, str]:
    """The first date in `text` and its precision ("day", "month" or "year").

    `precision` is the coarsest precision accepted: "day" (default) refuses "March 2021" and "2021";
    "month" accepts "March 2021" (read as the 1st); "year" also accepts a bare year (read as 1 January).
    A coarse date must be coded `earliest_known` or `unconfirmed`, never `dated` (`findings.check`).

    By hand: "adopted November 8, 2019" -> 2019-11-08 day; "eff. 1/1/20" -> 2020-01-01 day; "2019-11-08" ->
    day; "8 Nov 2019" -> day; "March 2021" (precision month) -> 2021-03-01 month.
    """
    if precision not in ("day", "month", "year"):
        raise ValueError(f"precision must be day, month or year, not {precision!r}")
    s = str(text)
    found: list[tuple[int, date, str]] = []
    for m in _ISO.finditer(s):
        found.append((m.start(), date(int(m[1]), int(m[2]), int(m[3])), "day"))
    for m in _US.finditer(s):
        y = int(m[3])
        y = _two_digit_year(y) if len(m[3]) == 2 else y
        found.append((m.start(), date(y, int(m[1]), int(m[2])), "day"))
    for m in _LONG.finditer(s):
        mon = _MONTHS.get(m[1].lower())
        if mon:
            found.append((m.start(), date(int(m[3]), mon, int(m[2])), "day"))
    for m in _DAY_FIRST.finditer(s):
        mon = _MONTHS.get(m[2].lower())
        if mon:
            found.append((m.start(), date(int(m[3]), mon, int(m[1])), "day"))
    if found:
        return min(found, key=lambda t: t[0])[1:]
    if precision in ("month", "year"):
        for m in _MONTH_YEAR.finditer(s):
            mon = _MONTHS.get(m[1].lower())
            if mon:
                return date(int(m[2]), mon, 1), "month"
    if precision == "year":
        m = _YEAR.search(s)
        if m:
            return date(int(m[1]), 1, 1), "year"
    raise DateParseError(f"no {precision}-precision date in {s[:80]!r}")


def tags_for(date_basis: str, *, standards_only: bool = False) -> list[str]:
    """The `coding_notes` tags for a row. By hand: ("predates") -> ["[predates]"]; ("dated", standards) ->
    ["[standards]"]; ("earliest_known") -> ["[earliest-known]"]."""
    if date_basis not in DATE_BASES:
        raise ValueError(f"date_basis must be one of {DATE_BASES}, not {date_basis!r}")
    out = [TAGS[date_basis]] if date_basis in TAGS else []
    if standards_only:
        out.append(STANDARDS_TAG)
    return out


def basis_from_notes(notes: str | None, adoption_date: object = None) -> str:
    """Read a row's date basis back from its notes (for comparing with already-coded rows), as
    `rule_tags.flags` does: `[predates]` wins; then `DATE UNCONFIRMED`; then `[earliest-known]` or a blank
    adoption date; else `dated`."""
    n = "" if notes is None else str(notes)
    if TAGS["predates"] in n:
        return "predates"
    if TAGS["unconfirmed"] in n:
        return "unconfirmed"
    blank = adoption_date is None or str(adoption_date).strip() in ("", "nan", "NaT", "None")
    if TAGS["earliest_known"] in n or blank:
        return "earliest_known"
    return "dated"
