"""Date tags on coded rules, read the same way by the D-024 (`estimate_mm`) and D-025 (`estimate_adu`) panels.

The data threads mark how sure a rule's date is in free text in `coding_notes` (until WS-CORE adds a
`date_basis` field):

- `[predates]` (HANDOFF, 2026-11-01): the rule was in force before the window. **Never a reform event:** the
  panels put it in force from `ALWAYS_IN_FORCE`, before any panel year, whatever its coded date.
- `[earliest-known]`, or a blank `adoption_date`: the coded date is the earliest the sources show; the rule
  may be older. Main runs keep these rows as events; a sensitivity drops them (`dropped_places`). One dated
  on or before `WINDOW_START` is the data threads' placeholder for "allowed before the window" (the
  readiness counts' window starts 2010-01-02), so it is read like `[predates]`.
- `DATE UNCONFIRMED` (Ben, 2026-11-02): no signed ordinance or effective-date record. The row is an event at
  its coded date; a sensitivity drops it.
- A "none" row (ADU `adus_per_lot` = 0; missing middle `unit_cap` = 1) is a control on evidence, never an
  event.

"Dropping an event" leaves the whole place out of the panel (neither treated nor a comparison): its rule is
real, so it can't stand in for an untreated place, and its timing is what the sensitivity doubts. Only an
event that changes some panel year counts: one taking effect after 1 July of the year before the first panel
year and on or before 1 July of the last (rules are read on 1 July). Tests: tests/model/test_rule_tags.py.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

import pandas as pd

PREDATES = "[predates]"
EARLIEST_KNOWN = "[earliest-known]"
UNCONFIRMED = "DATE UNCONFIRMED"
# The adoption-year searches in both panels start in 1990, so a rule in force from here is treated in every
# panel year and its adoption year is never inside a panel.
ALWAYS_IN_FORCE = pd.Timestamp("1990-01-01")
WINDOW_START = pd.Timestamp("2010-01-01")  # an earliest-known date on or before this: "before the window"
SENSITIVITIES = ("earliest_known", "unconfirmed")  # the flags `dropped_places` can drop


def flags(reforms: pd.DataFrame) -> pd.DataFrame:
    """Per rule row (same index): `predates`, `earliest_known`, `before_window`, `unconfirmed`, `none_row`
    and `event`.

    `before_window` = earliest-known and effective on or before `WINDOW_START`. `event` = in force, not
    `[predates]`, not before the window and not a "none" row; the panel window is the caller's (see
    `dropped_places`). By hand: notes "[earliest-known] ... [predates]" -> predates and earliest-known, not an
    event; a blank adoption date -> earliest-known; the same effective 2010-01-01 -> before the window, not
    an event; `adus_per_lot` 0 on an ADU row -> a none row.
    """
    notes = reforms["coding_notes"].fillna("").astype(str)

    def num(col: str) -> pd.Series:
        return pd.to_numeric(reforms.get(col, pd.Series(index=reforms.index, dtype=float)), errors="coerce")

    out = pd.DataFrame(index=reforms.index)
    out["predates"] = notes.str.contains(PREDATES, regex=False)
    out["earliest_known"] = notes.str.contains(EARLIEST_KNOWN, regex=False) | reforms["adoption_date"].isna()
    out["before_window"] = out["earliest_known"] & (reforms["effective_date"] <= WINDOW_START)
    out["unconfirmed"] = notes.str.contains(UNCONFIRMED, regex=False)
    out["none_row"] = ((reforms["theme"] == "adu") & (num("adus_per_lot") == 0)) | (
        (reforms["theme"] == "missing_middle") & (num("unit_cap") == 1)
    )
    out["event"] = (
        (reforms["status"] == "in_force") & ~out["predates"] & ~out["before_window"] & ~out["none_row"]
    )
    return out


def apply(reforms: pd.DataFrame) -> pd.DataFrame:
    """The reforms with every `[predates]` or before-the-window row in force from `ALWAYS_IN_FORCE`: its
    effective and adoption dates move there and its announcement date is cleared (it announces nothing).
    Other rows are unchanged. By hand: a by-right row tagged `[predates]` and dated 2021-03-01, or an
    earliest-known one dated 2010-01-01 -> effective 1990-01-01, so a panel's adoption year is 1990, before
    its first year."""
    out = reforms.copy()
    f = flags(out)
    pre = f["predates"] | f["before_window"]
    for col in ("effective_date", "adoption_date"):
        out.loc[pre, col] = ALWAYS_IN_FORCE
    if "announced_date" in out:
        out.loc[pre, "announced_date"] = pd.NaT
    return out


def dropped_places(reforms: pd.DataFrame, years: Sequence[int], drop: Iterable[str] = ()) -> set[str]:
    """Jurisdictions a sensitivity leaves out: those with an event row carrying a flag in `drop` (a subset
    of `SENSITIVITIES`) that takes effect inside the panel, i.e. after 1 July of `min(years) − 1` and on or
    before 1 July of `max(years)`. By hand, panel 2016-2025, drop earliest-known: an earliest-known event
    effective 2018-05-01 -> dropped; one effective 2015-06-30 (in force all panel long) -> kept; a
    `[predates]` or a "none" row -> kept."""
    drop = list(drop)
    unknown = sorted(set(drop) - set(SENSITIVITIES))
    if unknown:
        raise ValueError(f"unknown tag sensitivity {unknown}; choose from {SENSITIVITIES}")
    if not drop or reforms.empty:
        return set()
    f = flags(reforms)
    lo = pd.Timestamp(f"{int(min(years)) - 1}-07-01")
    hi = pd.Timestamp(f"{int(max(years))}-07-01")
    eff = reforms["effective_date"]
    hit = f["event"] & (eff > lo) & (eff <= hi) & f[drop].any(axis=1)
    return set(reforms.loc[hit, "jurisdiction_geoid"].astype(str))
