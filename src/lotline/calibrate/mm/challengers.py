"""Missing-middle D-092: standards events (dose class S), the level component L and its prior (challenger
C4), challengers C1 and C3, and the §5 rule for choosing between M and the challengers.

Part of `calibrate_mm`, split by method step (modularity step 3); `calibrate_mm` re-exports every name.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd

from lotline.model import rule_tags

from .capacity import CLASS_COLUMNS, outcome_classes, prior_cap, retarget
from .fit import Fit, fit
from .places import HALF_GRID, Place, feasibility_ratio

# ---------------------------------------------------------------------------------------------------------
# D-092 (proposed): standards events (dose class S), the level component L, challengers C1, C3, C4, and the
# §5 choosing rule. Code only: nothing here has been run on real data.
# ---------------------------------------------------------------------------------------------------------

DOSE_CLASSES = ("cap", "S")  # D-092 §1b: a cap rise (D-042) or a standards event


S_DOSE = 1 / 3  # D-092 §1b: a standards event's dose increase (the approval-grade step); config: mm.yaml


CLASS_SIZES = {"bldgs_2": (2, 2), "bldgs_3_4": (3, 4)}  # units per building in each BPS class


LEVEL_AGE = 1e3  # event age given to level places: the ramp is 1 (mature) at any half-way point


LEVEL_POOL_MIN = 3  # D-092 §1b (D-042's thin-pool rule): fewer "none" places in a band -> the pooled band


C4_WIDENING = 2.0  # D-092 §5: C4's prior log-SD = θ_L's profile log-SE × 2 (selection)


SE_MARGIN = 2.0  # D-092 §5: a challenger must beat M's held-out log score by more than 2 paired SE


@dataclass(frozen=True)
class Event:
    """One place's D-092 event: year, the cap in force the year before and after, and its dose class
    ('cap' = D-042's cap rise; 'S' = a standards event, §1b)."""

    year: int
    prior_cap: int
    new_cap: int
    dose_class: str = "cap"

    @property
    def classes(self) -> tuple[str, ...]:
        if self.dose_class == "S":
            return standards_classes(self.prior_cap, self.new_cap)
        return outcome_classes(self.prior_cap)


def standards_classes(prior_cap: int, cap: int) -> tuple[str, ...]:
    """BPS classes a standards route covers (D-092 §1b): the 2-4 unit classes whose smallest size is at or
    below the route's cap and, when the coded cap rose, above the prior cap.

    By hand: Houston's MUR, prior cap 2, route cap 4 -> 3-4 unit only; prior 1, cap 2 -> 2-unit only; a route
    that leaves the cap at 4 (prior 4, cap 4) -> both classes; prior 2, cap 2 -> 2-unit only."""
    lo = prior_cap if cap > prior_cap else 1
    return tuple(c for c in CLASS_COLUMNS if lo < CLASS_SIZES[c][0] <= cap)


def _new_rows(rows: pd.DataFrame, year: int) -> pd.DataFrame:
    """Rows in force on 1 July of `year` but not of the year before."""
    return rows[rule_tags.in_force_on(rows, year) & ~rule_tags.in_force_on(rows, year - 1)]


def standards_year(rows: pd.DataFrame, first: int = 2013, last: int = 2025) -> float:
    """The first year in [first, last] in which a `[standards]` row of the place comes into force on 1 July;
    NaN if none. By hand: a [standards] row effective 2023-11-27 -> 2024."""
    std = rows[rule_tags.flags(rows)["standards"]] if len(rows) else rows
    for y in range(first, last + 1):
        if len(std) and len(_new_rows(std, y)):
            return float(y)
    return np.nan


def classify_event(rows: pd.DataFrame, year: int, coverage: Mapping[str, float]) -> Event | None:
    """D-092's event for one place at `year` (`rows`: its in-force missing-middle rows after
    `rule_tags.apply`): class 'S' if a `[standards]` row comes into force that year (its cap is the route's
    cap), else 'cap' if `prior_cap` rises (D-042), else None.

    By hand: a [predates] cap-2 row and a [standards] cap-4 row effective 2023-11-27, event 2024 -> S, prior
    2, cap 4, classes 3-4 unit; the same row untagged -> 'cap', prior 2, classes 3-4 unit; a capless row ->
    None."""
    before, after = prior_cap(rows, year - 1, coverage), prior_cap(rows, year, coverage)
    new = _new_rows(rows, year)
    std = new[rule_tags.flags(new)["standards"]] if len(new) else new
    if len(std):
        caps = pd.to_numeric(std["unit_cap"], errors="coerce").dropna()
        cap = int(caps.max()) if len(caps) else max(after, before)
        return Event(int(year), int(before), cap, "S")
    if after > before:
        return Event(int(year), int(before), int(after), "cap")
    return None


def first_event(
    rows: pd.DataFrame,
    start: float,
    coverage: Mapping[str, float],
    last: int = 2025,
) -> tuple[Event | None, list[tuple[int, int, int]]]:
    """D-092 §1's event: the first year from `start` (D-042's `event_year`, or the first `[standards]` year
    if earlier) to `last` at which `classify_event` finds a cap rise or a standards row. Returns (event or
    None, misses), where misses holds (start, cap before, cap after) when `start` itself set no event.

    By hand (Bend-like): a [predates] cap-3 row, a cap-3 row of 2016-12-06 (the dose rises in 2017, the cap
    doesn't) and a cap-4 row of 2021-11-05 -> start 2017 -> event 2022, prior cap 3, classes 3-4 unit."""
    if pd.isna(start):
        return None, []
    misses = []
    for y in range(int(start), int(last) + 1):
        ev = classify_event(rows, y, coverage)
        if ev is not None:
            return ev, misses
        if y == int(start):
            misses.append((y, prior_cap(rows, y - 1, coverage), prior_cap(rows, y, coverage)))
    return None, misses


def standards_variant(events: Mapping[str, Event], variant: str = "main", s_dose: float = S_DOSE):
    """(events, S dose) for D-092 §1b's sensitivities: 'main' (S events at `s_dose`), 'exclude' (S events
    left out) or 'dose1' (S events at dose 1)."""
    if variant == "main":
        return dict(events), s_dose
    if variant == "exclude":
        return {g: e for g, e in events.items() if e.dose_class != "S"}, s_dose
    if variant == "dose1":
        return dict(events), 1.0
    raise ValueError(f"unknown standards variant {variant!r}")


def retarget_events(
    panel: pd.DataFrame, classes: pd.DataFrame, events: Mapping[str, Event], s_dose: float = S_DOSE
) -> pd.DataFrame:
    """`retarget` for D-092 events. A 'cap' event is exactly `retarget`'s (classes above the prior cap; dose =
    the increase over the year before the event). An 'S' event counts the classes its route covers
    (`Event.classes`) and takes dose `s_dose` from its event year on (0 before), whatever the coded dose.

    By hand: an S event in 2024 with dose 0.3 coded before and 0.9 after -> dose 0 to 2023, 1/3 from 2024."""
    cap_ev = {g: (e.year, e.prior_cap) for g, e in events.items() if e.dose_class == "cap"}
    out = [retarget(panel, classes, cap_ev)] if cap_ev else []
    for gid, e in events.items():
        if e.dose_class != "S":
            continue
        cols = list(e.classes)
        rows = panel[panel["place"] == gid].sort_values("year").copy()
        if rows.empty or not cols:
            continue
        c = classes.loc[gid, cols] if gid in classes.index.get_level_values(0) else None
        rows["y_buildings"] = [
            float(c.loc[y].sum()) if c is not None and y in c.index and c.loc[y].notna().all() else np.nan
            for y in rows["year"]
        ]
        rows["dose"] = np.where(rows["year"] >= e.year, float(s_dose), 0.0)
        rows["T"] = float(e.year)
        rows["prior_cap"] = e.prior_cap
        out.append(rows)
    return pd.concat(out, ignore_index=True) if out else panel.iloc[0:0]


# ---- Level component L (§1b) ----


def level_rate(none_rows: pd.DataFrame, state: str, band: int, min_places: int = LEVEL_POOL_MIN) -> dict:
    """The no-rule 2-4 rate per eligible parcel for a level place in (state, band): Σ y / Σ E over the coded
    "none" places' years (`none_rows`: panel rows with state, band, place, y_buildings, eligible). From the
    same state and band if it has at least `min_places` such places; else the band pooled over every state;
    else every none place. Returns {rate, pool, places}.

    By hand: state A band 2 has places with (y, E) (2, 1000) and (0, 1000) -> 2 places < 3 -> the band pool,
    adding B's (4, 1000) -> rate 6 / 3,000 = 0.002, pool 'band', 3 places."""
    d = none_rows[none_rows["y_buildings"].notna() & (none_rows["eligible"] > 0)]
    tiers = (
        ("state_band", d[(d["state"] == state) & (d["band"] == band)]),
        ("band", d[d["band"] == band]),
        ("all", d),
    )
    for name, g in tiers:
        n = g["place"].nunique()
        if n >= min_places or name == "all":
            rate = float(g["y_buildings"].sum() / g["eligible"].sum()) if len(g) else np.nan
            return {"rate": rate, "pool": name, "places": int(n)}
    raise AssertionError("unreachable")


def level_places(
    panel: pd.DataFrame,
    geoids: Sequence[str],
    none_rows: pd.DataFrame,
    margin: float,
    sigma: float,
    years: Sequence[int],
    min_places: int = LEVEL_POOL_MIN,
    feasibility: bool = True,
) -> list[Place]:
    """`Place` per always-allowed place for the level model (D-092 §1b):

        y_it ~ Poisson(b_it + θ_L u_i E_it d_i F_i / F(1)),   b_it = r(state, band) × E_it

    with r from `level_rate`, d_i the place's coded dose in each year and no ramp (age `LEVEL_AGE`). Stored as
    beta = r, g = E (so B = b_it), kr = E d F/F(1). Only years in `years` with an outcome and E > 0 are kept;
    places with no such year or a zero dose throughout are left out. `fit_level` estimates θ_L."""
    out = []
    years = set(int(y) for y in years)
    for gid in geoids:
        rows = panel[(panel["place"] == gid)].sort_values("year")
        rows = rows[rows["year"].isin(years) & rows["y_buildings"].notna() & (rows["eligible"] > 0)]
        if rows.empty or not (rows["dose"] > 0).any():
            continue
        r = level_rate(none_rows, rows["state"].iloc[0], int(rows["band"].iloc[0]), min_places)["rate"]
        pcr = float(rows["pcr"].dropna().iloc[0]) if rows["pcr"].notna().any() else np.nan
        fr = feasibility_ratio(pcr, margin, sigma) if feasibility and np.isfinite(pcr) else 1.0
        E = rows["eligible"].to_numpy(float)
        yrs = rows["year"].to_numpy(int)
        out.append(
            Place(
                geoid=gid,
                name=str(rows["name"].iloc[0]),
                T=int(yrs.min()),
                beta=r,
                years=yrs,
                y=rows["y_buildings"].to_numpy(float),
                g=E,
                kr=E * rows["dose"].to_numpy(float) * fr,
                age=np.full(len(yrs), LEVEL_AGE),
                eligible=E,
            )
        )
    return out


def fit_level(places: Sequence[Place]) -> Fit:
    """θ_L, α_L and their 90% profile-likelihood intervals for the level places (D-092 §1b): `fit` with the
    ramp at 1 (the half-way point is not estimated; `half` in the result is a placeholder)."""
    return fit(places, halves=(HALF_GRID[0],))


def level_prior(level: Fit, widening: float = C4_WIDENING) -> tuple[float, float]:
    """C4's lognormal prior on M's mature θ: (ln θ_L, widening × θ_L's profile log-SE).

    By hand: θ_L 0.001 with 90% interval 0.0005-0.002 -> log-SE ln 4 / 3.29 = 0.4214; doubled 0.8427."""
    return math.log(level.theta), widening * level.log_se


# ---- Challenger 1: Oregon's not-yet-treated growth index (§5) ----


def not_yet_treated_series(
    panel: pd.DataFrame,
    classes: pd.DataFrame,
    cols: Sequence[str],
    event_years: Mapping[str, float],
    state: str,
    exclude: Sequence[str] = (),
) -> dict[int, float]:
    """{year: Σ y / Σ E} over the state's places with no cap rise yet in that year (event year after it, or
    none; `event_years`: geoid -> event year or NaN, absent = none), in the classes `cols`, as a rate per
    eligible parcel so places leaving the set don't move it. `growth_index` of this series is C1's g.

    By hand: places a (event 2022) and b (none), E 1,000 each; 2021: a 4, b 2 -> 6 / 2,000 = 0.003; 2022: a
    leaves, b 3 -> 0.003."""
    d = panel[(panel["state"] == state) & ~panel["place"].isin(set(exclude)) & (panel["eligible"] > 0)]
    out = {}
    for y, g in d.groupby("year"):
        keep = [
            p
            for p in g["place"]
            if not (pd.notna(event_years.get(p, np.nan)) and event_years[p] <= y) and (p, y) in classes.index
        ]
        g = g[g["place"].isin(keep)].set_index("place")
        num = den = 0.0
        for p in g.index:
            v = classes.loc[(p, y), list(cols)]
            if v.notna().all():
                num += float(v.sum())
                den += float(g.at[p, "eligible"])
        if den > 0:
            out[int(y)] = num / den
    return out


# ---- Challenger 3: conditional place effect (§5) ----


def conditional_z(pace: Mapping[str, float], fit_ids: Sequence[str]) -> dict[str, float]:
    """C3's z_i = ln(1 + h_i) − its mean over the fit places (h: pre-reform 2-4 unit homes per 1,000 eligible
    parcels a year from BPS, as D-042), for every place in `pace` (held-out places are centred on the fit
    set's mean). Places with no pace get 0. By hand: fit {a: 0, b: e − 1}, held out c: e² − 1 -> mean 0.5;
    a −0.5, b 0.5, c 1.5.

    C3 sets ln E[u_i] = c z_i: u_i = e^(c z_i) v_i with v_i ~ Gamma(mean 1, variance α), which is the same
    likelihood as `fit_capacity`'s θ e^(b z_i), so C3 is fitted with `fit_capacity` on these z."""
    lz = {g: math.log1p(v) for g, v in pace.items() if pd.notna(v)}
    ref = [lz[g] for g in fit_ids if g in lz]
    m = float(np.mean(ref)) if ref else 0.0
    return {g: (lz[g] - m if g in lz else 0.0) for g in pace}


# ---- §5: choosing between M and the challengers ----


def paired_delta(scores: pd.DataFrame, a: str, b: str) -> dict:
    """Σ (a − b) over held-out places with both scores, its paired SE sd(a − b) √n, and n (as D-054)."""
    d = (scores[a] - scores[b]).dropna()
    se = float(d.std(ddof=1) * math.sqrt(len(d))) if len(d) > 1 else np.nan
    return {"delta": float(d.sum()), "paired_se": se, "n": int(len(d))}


def select_model(
    scores: pd.DataFrame,
    tests_passed: Mapping[str, int],
    main: str = "M",
    challengers: Sequence[str] = ("C1", "C3", "C4"),
    margin: float = SE_MARGIN,
) -> dict:
    """D-092 §5's rule. `scores`: one row per held-out place with columns `ls_<model>` (held-out log scores,
    leave one state out). `tests_passed`: model -> how many of tests A-C it passes. A challenger replaces M
    only if Σ(ls_C − ls_M) > `margin` × paired SE and it passes no fewer of tests A-C than M. If several
    qualify, the largest Σ wins. Returns {"chosen", "table"}.

    By hand: differences (1, 2, 3) -> Σ 6, SE 1 × √3 = 1.732, 6 > 3.46 -> beats; passes 2 against M's 3 ->
    does not replace."""
    rows = []
    for c in challengers:
        col = f"ls_{c}"
        if col not in scores:
            continue
        pd_ = paired_delta(scores, col, f"ls_{main}")
        beats = bool(np.isfinite(pd_["paired_se"]) and pd_["delta"] > margin * pd_["paired_se"])
        enough = tests_passed.get(c, -1) >= tests_passed.get(main, 0)
        rows.append(
            pd_
            | {"model": c, "beats_by_margin": beats, "tests_passed": tests_passed.get(c, np.nan),
               "tests_passed_main": tests_passed.get(main, np.nan), "replaces": beats and enough}
        )  # fmt: skip
    table = pd.DataFrame(rows)
    winners = table[table["replaces"]] if len(table) else table
    chosen = str(winners.loc[winners["delta"].idxmax(), "model"]) if len(winners) else main
    return {"chosen": chosen, "table": table}
