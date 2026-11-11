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
- `[standards]` (D-082 §1b, proposed): the row's cap doesn't rise, but its by-right route gets cheaper or
  simpler (Houston's 2023 MUR route). `calibrate_mm.classify_event` makes it a dose-class "S" event.

D-082 §1 (proposed) reads the date tags on the event-setting row only (`dropped_places(rule=
"event_setting_row")`): a tag on a row that sets no cap (Oregon's SB 458 land-division rows) no longer drops
its place. The D-024 / D-025 reading (`rule="any_event_row"`) stays the default.

"Dropping an event" leaves the whole place out of the panel (neither treated nor a comparison): its rule is
real, so it can't stand in for an untreated place, and its timing is what the sensitivity doubts. Only an
event that changes some panel year counts: one taking effect after 1 July of the year before the first panel
year and on or before 1 July of the last (rules are read on 1 July). Tests: tests/model/test_rule_tags.py.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence

import numpy as np
import pandas as pd

PREDATES = "[predates]"
EARLIEST_KNOWN = "[earliest-known]"
UNCONFIRMED = "DATE UNCONFIRMED"
# D-082 §1b: the cap doesn't rise, but the by-right route gets cheaper (dose class S)
STANDARDS = "[standards]"
# The adoption-year searches in both panels start in 1990, so a rule in force from here is treated in every
# panel year and its adoption year is never inside a panel.
ALWAYS_IN_FORCE = pd.Timestamp("1990-01-01")
WINDOW_START = pd.Timestamp("2010-01-01")  # an earliest-known date on or before this: "before the window"
SENSITIVITIES = ("earliest_known", "unconfirmed")  # the flags `dropped_places` can drop
DROP_RULES = ("any_event_row", "event_setting_row")  # D-082 §1: which rows' tags count (see `dropped_places`)


def flags(reforms: pd.DataFrame) -> pd.DataFrame:
    """Per rule row (same index): `predates`, `earliest_known`, `before_window`, `unconfirmed`, `standards`,
    `none_row` and `event`.

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
    out["standards"] = notes.str.contains(STANDARDS, regex=False)
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


def dropped_places(
    reforms: pd.DataFrame,
    years: Sequence[int],
    drop: Iterable[str] = (),
    rule: str = "any_event_row",
    coverage: Mapping[str, float] | None = None,
) -> set[str]:
    """Jurisdictions a sensitivity leaves out, for the flags in `drop` (a subset of `SENSITIVITIES`).

    rule 'any_event_row' (the D-024 / D-025 reading, the default): a place is dropped if any of its event rows
    carrying a flag takes effect inside the panel, i.e. after 1 July of `min(years) − 1` and on or before 1
    July of `max(years)`. By hand, panel 2016-2025, drop earliest-known: an earliest-known event effective
    2018-05-01 -> dropped; one effective 2015-06-30 (in force all panel long) -> kept; a `[predates]` or a
    "none" row -> kept.

    rule 'event_setting_row' (D-082 §1, missing middle): only the rows that set the place's event count. The
    event is the first year in `years` whose cap in force on 1 July (`cap_path`) is above the year before;
    the event-setting rows are those in force on 1 July of that year but not of the year before whose cap
    reaches the new cap. The place is dropped if any of them carries a flag in `drop`. A row with no cap
    (Oregon's SB 458 land-division rows: blank `unit_cap`, blank adoption date) never sets an event, so its
    tags never drop a place. By hand, events 2013-2025, drop earliest-known: a dated cap-4 row effective
    2021-08-01 and a blank-dated, capless land-division row effective 2022-06-30 -> kept (the old rule drops
    it); a blank-dated cap-4 row effective 2021-08-01 -> dropped. `coverage` (reform_id -> share of eligible
    parcels) applies `calibrate_mm.prior_cap`'s half-coverage rule; without it every row counts.
    """
    drop = list(drop)
    unknown = sorted(set(drop) - set(SENSITIVITIES))
    if unknown:
        raise ValueError(f"unknown tag sensitivity {unknown}; choose from {SENSITIVITIES}")
    if rule not in DROP_RULES:
        raise ValueError(f"unknown drop rule {rule!r}; choose from {DROP_RULES}")
    if not drop or reforms.empty:
        return set()
    f = flags(reforms)
    if rule == "event_setting_row":
        out = set()
        for g, idx in reforms.groupby(reforms["jurisdiction_geoid"].astype(str)).groups.items():
            rows = reforms.loc[idx]
            setting = event_setting_rows(rows, years, coverage)
            if len(setting) and f.loc[setting, drop].any(axis=None):
                out.add(g)
        return out
    lo = pd.Timestamp(f"{int(min(years)) - 1}-07-01")
    hi = pd.Timestamp(f"{int(max(years))}-07-01")
    eff = reforms["effective_date"]
    hit = f["event"] & (eff > lo) & (eff <= hi) & f[drop].any(axis=1)
    return set(reforms.loc[hit, "jurisdiction_geoid"].astype(str))


def _cap_column(rows: pd.DataFrame) -> pd.Series:
    """The row's cap: `unit_cap` for missing middle, `adus_per_lot` for ADU rows (NaN if blank)."""
    cap = pd.to_numeric(rows.get("unit_cap", pd.Series(np.nan, index=rows.index)), errors="coerce")
    if "adus_per_lot" in rows:
        adu_cap = pd.to_numeric(rows["adus_per_lot"], errors="coerce")
        cap = cap.where(rows["theme"] != "adu", adu_cap)
    return cap


def in_force_on(rows: pd.DataFrame, year: int) -> pd.Series:
    """Rows with status in force whose effective date is on or before 1 July of `year` and whose end date
    (if any) is after it."""
    mid = pd.Timestamp(f"{int(year)}-07-01")
    eff = pd.to_datetime(rows["effective_date"], errors="coerce")
    end = (
        pd.to_datetime(rows["end_date"], errors="coerce")
        if "end_date" in rows
        else pd.Series(pd.NaT, rows.index)
    )
    return (rows["status"] == "in_force") & (eff <= mid) & (end.isna() | (end > mid))


def cap_in_force(rows: pd.DataFrame, year: int, coverage: Mapping[str, float] | None = None) -> float:
    """The largest cap of one place's rows in force on 1 July of `year` (only rows covering at least half
    the eligible parcels when `coverage` is given, as `calibrate_mm.prior_cap`); 1 if none. By hand: a
    cap-2 row from 2010 and a cap-4 row from 2021-08-01 -> 2 in 2021, 4 in 2022."""
    live = rows[in_force_on(rows, year)]
    caps = _cap_column(live)
    if coverage is not None:
        caps = caps[[coverage.get(r, 0.0) >= 0.5 for r in live["reform_id"]]]
    caps = caps.dropna()
    return float(max(caps.max(), 1.0)) if len(caps) else 1.0


def event_setting_rows(
    rows: pd.DataFrame, years: Sequence[int], coverage: Mapping[str, float] | None = None
) -> list:
    """Index labels of the rows that set one place's first cap rise inside `years` (D-082 §1): the rows newly
    in force on 1 July of the first year whose `cap_in_force` is above the year before, whose own cap is at
    least the new cap (and that pass the coverage rule when `coverage` is given). [] if the cap never rises.
    By hand: cap-2 row 2010, cap-4 row 2021-08-01, capless row 2022-06-30, years 2013-2025 -> the cap-4 row.
    """
    years = sorted(int(y) for y in years)
    if not years:
        return []
    caps = _cap_column(rows)
    prev = cap_in_force(rows, years[0] - 1, coverage)
    for y in years:
        now = cap_in_force(rows, y, coverage)
        if now > prev:
            new = in_force_on(rows, y) & ~in_force_on(rows, y - 1) & (caps >= now)
            if coverage is not None:
                new &= pd.Series([coverage.get(r, 0.0) >= 0.5 for r in rows["reform_id"]], index=rows.index)
            return list(rows.index[new])
        prev = now
    return []


def always_allowed_places(reforms: pd.DataFrame) -> set[str]:
    """Places whose missing-middle rule predates the window (D-082 §1b's level set, before removing event
    places): an in-force missing-middle row tagged `[predates]`, or read as before the window, with
    `unit_cap` at least 2. Pass the coded rows *before* `apply` (it moves the dates that `before_window`
    reads). By hand: a `[predates]` cap-2 row -> in; a before-window earliest-known cap-3 row -> in; a
    `[predates]` cap-1 ("none") row -> out; a dated cap-4 row of 2021 -> out."""
    if reforms.empty:
        return set()
    f = flags(reforms)
    cap = pd.to_numeric(reforms["unit_cap"], errors="coerce")
    hit = (
        (reforms["theme"] == "missing_middle")
        & (reforms["status"] == "in_force")
        & (f["predates"] | f["before_window"])
        & (cap >= 2)
    )
    return set(reforms.loc[hit, "jurisdiction_geoid"].astype(str))


def none_places(reforms: pd.DataFrame) -> set[str]:
    """Coded "none" places (D-082 §1b's comparison set for the no-rule level b): every in-force
    missing-middle row of the place has `unit_cap` 1. Fixed from rule rows, before any count. By hand: a
    place with one cap-1 row -> in; a cap-1 row and a later cap-2 row -> out; a blank cap -> out."""
    mm = reforms[(reforms["theme"] == "missing_middle") & (reforms["status"] == "in_force")]
    if mm.empty:
        return set()
    cap = pd.to_numeric(mm["unit_cap"], errors="coerce")
    ok = (cap == 1).groupby(mm["jurisdiction_geoid"].astype(str)).all()
    return set(ok.index[ok])
