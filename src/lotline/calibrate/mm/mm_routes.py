"""Adoption routes for missing middle's ramp (analysis plan D-100).

**Route** (`route_of`): a fit place is **state-required** if Oregon's HB 2001 (ORS 197.758) covers it: an
Oregon city of 10,000 people or more (2020 census), or a city or the unincorporated area of a county inside
the Portland Metro boundary (`config/crosswalks/or_hb2001_metro.csv`, cited there). Every other fit place,
in Oregon or elsewhere, is **locally adopted**.

**One half-way point per route** (`shift_ages`, `fit_routes`): the ramp is logistic in (age − half) / slope,
so ramp(age, h_local) = ramp(age + d, h) with d = h − h_local. Shifting the locally adopted places' ages by d
lets the D-038 fit profile one shared half-way point h (the state-required one) while the local places run
on h − d. `fit_routes` searches every pair on the half-way grid by the maximum likelihood at each pair, then
fits θ's interval at the best pair (`calibrate_mm.fit` with the shift held).
"""

from __future__ import annotations

import csv
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, replace
from pathlib import Path

from lotline.calibrate.mm import calibrate_mm as cal

REPO = Path(__file__).resolve().parents[4]
METRO_CSV = REPO / "config" / "crosswalks" / "or_hb2001_metro.csv"
HB2001_MIN_POP = (
    10_000  # ORS 197.758(1): a "medium city" has 10,000 to 25,000 people; larger ones are covered
)
STATE_REQUIRED, LOCAL = "state_required", "local"


def metro_geoids(path: Path = METRO_CSV) -> set[str]:
    with open(path) as f:
        return {r["geoid"] for r in csv.DictReader(f) if r["geoid"]}


def route_of(state: str, geoid: str, pop_2020: float | None, metro: Iterable[str]) -> str:
    """By hand: OR, Portland (Metro) -> state_required; OR, Bend (100k) -> state_required; OR, Dundee (3k,
    outside Metro) -> local; OR, Durham (2k, Metro) -> state_required; MN, St. Paul -> local."""
    if state.upper() != "OR":
        return LOCAL
    if geoid in set(metro):
        return STATE_REQUIRED
    return STATE_REQUIRED if (pop_2020 or 0) >= HB2001_MIN_POP else LOCAL


def shift_ages(places: Sequence[cal.Place], local_ids: set[str], d: float) -> list[cal.Place]:
    """Locally adopted places' ages + d, so their ramp runs at half-way h − d when the fit uses h.

    By hand: a local place at age 0.5 with d = 3 is at 3.5: ramp(3.5, h = 4) = ramp(0.5, h = 1)."""
    return [replace(p, age=p.age + d) if p.geoid in local_ids else p for p in places]


@dataclass(frozen=True)
class RouteFit:
    fit: cal.Fit  # θ, α and the state-required half-way point, with θ's interval at the best pair
    half_state: float
    half_local: float
    profile: dict  # {(h_state, h_local): loglik}
    local_low: float  # 90% set of the local half-way point (profile over pairs)
    local_high: float


def fit_routes(
    places: Sequence[cal.Place], local_ids: set[str], halves=cal.HALF_GRID, log_prior=None
) -> RouteFit:
    """Best (h_state, h_local) over the grid, then `calibrate_mm.fit` with the local shift held."""
    prof = {}
    for hs in halves:
        for hl in halves:
            st = cal.Stack.of(shift_ages(places, local_ids, hs - hl))
            prof[(float(hs), float(hl))] = cal._best_at_half(st, hs, log_prior=log_prior)[2]
    hs, hl = max(prof, key=prof.get)
    best = prof[(hs, hl)]
    f = cal.fit(shift_ages(places, local_ids, hs - hl), halves=(hs,), log_prior=log_prior)
    inside = [k for k, v in prof.items() if 2 * (best - v) <= cal.CHI2_90]
    return RouteFit(f, hs, hl, prof, min(k[1] for k in inside), max(k[1] for k in inside))
