"""Missing-middle D-042 inputs: newly allowed building classes above the prior cap, the comparison-place
baseline and builder capacity (`fit_capacity`).

Part of `calibrate_mm`, split by method step (modularity step 3); `calibrate_mm` re-exports every name.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace

import numpy as np
import pandas as pd

from lotline.calibrate.adu.calibrate_adu import CHI2_90

from .fit import Fit, _best_at_half, fit, profile_theta
from .likelihood import Stack, _interval
from .places import HALF_GRID, LOG_THETA, Place

# ---------------------------------------------------------------------------------------------------------
# D-042: newly allowed classes, comparison-place baseline, builder capacity
# ---------------------------------------------------------------------------------------------------------

CAPACITY_SLOPES = tuple(np.round(np.arange(-2.0, 2.0001, 0.25), 2))  # b grid (D-042)


POOL_MIN = 20.0  # a state's comparison sum below this (mean over T − 3 … T − 1) -> the four-state pool


CLASS_COLUMNS = ("bldgs_2", "bldgs_3_4")


def prior_cap(rows: pd.DataFrame, year: int, coverage: Mapping[str, float]) -> int:
    """The unit cap in force on 1 July of `year` on most of a place's eligible parcels (D-042): the largest
    `unit_cap` of the in-force rows whose coverage is at least 0.5; 1 if none.

    By hand: a cap-2 row covering 0.7 and a cap-3 row covering 0.2, both in force -> 2; only the cap-3 row
    -> 1 (it covers under half)."""
    mid = pd.Timestamp(f"{int(year)}-07-01")
    eff = pd.to_datetime(rows["effective_date"], errors="coerce")
    end = (
        pd.to_datetime(rows["end_date"], errors="coerce")
        if "end_date" in rows
        else pd.Series(pd.NaT, rows.index)
    )
    live = rows[(eff <= mid) & (end.isna() | (end > mid))]
    caps = [
        int(c)
        for rid, c in zip(live["reform_id"], pd.to_numeric(live["unit_cap"], errors="coerce"), strict=True)
        if pd.notna(c) and coverage.get(rid, 0.0) >= 0.5
    ]
    return max(caps) if caps else 1


def event_year(T: float, dose_by_year: Mapping[int, float], first: int = 2013, last: int = 2025) -> float:
    """D-042's event: T when first <= T <= last; for a rule in force before the window, the first year in
    [first, last] whose dose is above the year before; else NaN.

    By hand: T 2020 -> 2020; T 1990 with dose 0.3 to 2023 and 0.5 from 2024 -> 2024; T 1990, flat -> NaN."""
    if pd.isna(T):
        return np.nan
    if first <= T <= last:
        return float(T)
    if T < first:
        for y in range(first, last + 1):
            if dose_by_year.get(y, 0.0) > dose_by_year.get(y - 1, 0.0) + 1e-12:
                return float(y)
    return np.nan


def outcome_classes(cap: int) -> tuple[str, ...]:
    """BPS building classes above the prior cap: 1 -> 2-unit and 3-4 unit; 2 or 3 -> 3-4 unit; 4+ -> none."""
    if cap <= 1:
        return CLASS_COLUMNS
    return ("bldgs_3_4",) if cap <= 3 else ()


def retarget(
    panel: pd.DataFrame, classes: pd.DataFrame, events: Mapping[str, tuple[int, int]]
) -> pd.DataFrame:
    """The panel rows of the event places, recast for D-042: T = the event year, `y_buildings` = buildings in
    the classes above the prior cap (every year, so the baseline uses the same classes), and `dose` = the
    increase over the dose in force the year before the event (floored at 0).

    `classes`: BPS buildings by class, indexed (geoid, year). `events`: geoid -> (event year, prior cap)."""
    out = []
    for gid, (E, cap) in events.items():
        rows = panel[panel["place"] == gid].sort_values("year").copy()
        cols = list(outcome_classes(cap))
        if rows.empty or not cols:
            continue
        c = classes.loc[gid, cols] if gid in classes.index.get_level_values(0) else None
        rows["y_buildings"] = [
            float(c.loc[y].sum()) if c is not None and y in c.index and c.loc[y].notna().all() else np.nan
            for y in rows["year"]
        ]
        d0 = rows.loc[rows["year"] == E - 1, "dose"]
        d0 = float(d0.iloc[0]) if len(d0) else 0.0
        rows["dose"] = (rows["dose"] - d0).clip(lower=0.0)
        rows["T"] = float(E)
        rows["prior_cap"] = cap
        out.append(rows)
    return pd.concat(out, ignore_index=True) if out else panel.iloc[0:0]


def comparison_series(
    panel: pd.DataFrame, classes: pd.DataFrame, cols: Sequence[str], statuses=("coded_not_treated", "uncoded")
) -> tuple[dict[str, dict[int, float]], dict[int, float]]:
    """({state: {year: buildings}}, {year: four-state buildings}) summed over comparison places: the given
    statuses, never any dose above 0. A place-year missing from BPS adds nothing."""
    never = panel.groupby("place")["dose"].max().fillna(0.0) <= 0
    comp = panel[panel["status"].isin(statuses) & panel["place"].map(never)][
        ["state", "place"]
    ].drop_duplicates()
    c = classes.reset_index()
    c = c[c["geoid"].isin(set(comp["place"]))].merge(comp, left_on="geoid", right_on="place")
    c["v"] = c[list(cols)].sum(axis=1, min_count=len(cols))
    by_state = {st: g.groupby("year")["v"].sum().to_dict() for st, g in c.groupby("state")}
    return by_state, c.groupby("year")["v"].sum().to_dict()


def baseline_series(
    state_series: Mapping[int, float], pool: Mapping[int, float], pre_years, min_mean=POOL_MIN
):
    """The state's comparison series, or the four-state pool when the state's mean over the pre-reform years
    is under `min_mean` (D-042). By hand: state {2019: 5, 2020: 10, 2021: 15}, pre 2019-21 -> mean 10 < 20 ->
    the pool."""
    vals = [state_series.get(y, np.nan) for y in pre_years]
    vals = [v for v in vals if pd.notna(v)]
    return dict(state_series) if vals and np.mean(vals) >= min_mean else dict(pool)


def capacity_z(h: Mapping[str, float]) -> dict[str, float]:
    """z_i = ln(1 + h_i) − its mean over the given places (h: 2-4 unit homes per 1,000 eligible parcels a year
    before the event). By hand: h 0 and e − 1 -> ln 1 = 0, ln e = 1, mean 0.5 -> −0.5, 0.5."""
    lz = {g: math.log1p(v) for g, v in h.items() if pd.notna(v)}
    m = float(np.mean(list(lz.values()))) if lz else 0.0
    return {g: v - m for g, v in lz.items()}


def scaled(places: Sequence[Place], b: float) -> list[Place]:
    """Places with kr × exp(b z): θ_i = θ exp(b z_i) folded into the exposure."""
    return [replace(p, kr=p.kr * math.exp(b * p.z)) for p in places]


@dataclass(frozen=True)
class CapacityFit:
    fit: Fit  # θ (at z = 0), α, half: with θ's interval profiled over the b values inside b's 90% set
    b: float
    b_low: float
    b_high: float
    profile_b: dict  # b -> max log-likelihood


def fit_capacity(places: Sequence[Place], slopes=CAPACITY_SLOPES, halves=HALF_GRID) -> CapacityFit:
    """D-042: b profiled on its grid (θ, α and the half-way point maximized at each b), θ's 90% interval the
    profile over (half, α, b) restricted to the b grid points inside b's 90% set."""
    by_b = {}
    for b in slopes:
        st = Stack.of(scaled(places, b))
        by_b[float(b)] = max(_best_at_half(st, h)[2] for h in halves)
    b_hat = max(by_b, key=by_b.get)
    inside = [b for b in by_b if 2 * (by_b[b_hat] - by_b[b]) <= CHI2_90]
    f = fit(scaled(places, b_hat), halves)
    stacks = {b: Stack.of(scaled(places, b)) for b in inside}
    lt_lo, lt_hi = _interval(
        lambda lt: max(profile_theta(stacks[b], math.exp(lt), halves) for b in inside),
        math.log(f.theta),
        by_b[b_hat],
        *LOG_THETA,
    )
    f = replace(f, low=math.exp(lt_lo), high=math.exp(lt_hi))
    return CapacityFit(f, b_hat, min(inside), max(inside), by_b)
