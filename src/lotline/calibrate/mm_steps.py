"""Missing-middle calibration runners (calibration design, phase 3).

One function per step in `steps.py`, each taking a `RunContext` and returning
{params file: {key: value or {value, low, high}}}. The fit sets come from `calibrate.mm.mm_fitsets`, the
likelihoods from `calibrate.mm.calibrate_mm` and `mm_routes`. Every fit here is deterministic (grid and
golden-section search, no random draws), so a full run reproduces config exactly when the data and rule rows
are unchanged.

A quick run profiles the ramp's half-way point on a coarse grid and searches φ with a looser tolerance: it
shows the chain runs end to end in minutes, but its numbers are not config's and it can't write. Values are
rounded half up to the precision config writes them at (the half-way points are grid values, unrounded).
"""

from __future__ import annotations

import math

from lotline.calibrate.data_steps import _r
from lotline.calibrate.mm import calibrate_mm as cal
from lotline.calibrate.mm import mm_fitsets as fs

QUICK_HALVES = (0.5, 1.0, 2.0, 4.0, 6.0)  # a quick run's half-way-point grid (the full grid is cal.HALF_GRID)
FILE = "mm_hazard"


def _sig(x: float, n: int) -> float:
    """Round half up to n significant figures, as config writes the small fitted rates (0.0010387 is 5)."""
    return float(_r(x, n - 1 - math.floor(math.log10(abs(x))))) if x else 0.0


def _halves(ctx) -> tuple[float, ...]:
    return QUICK_HALVES if ctx.quick else cal.HALF_GRID


def _config(key: str):
    from lotline.config import load_params

    return load_params(FILE)[key]


def mm_units_per_project(ctx) -> dict:
    """D-038: Census BPS homes per 2-4 unit building on D-038's named places, 2016-2025."""
    u = fs.d038_units(ctx.store)
    return {FILE: {"mm_units_per_project": {k: _r(v, 2) for k, v in u.items()}}}


def year_spread_places(store, p=None) -> list[cal.Place]:
    """Run 9's pseudo-forecasts: the kept uncoded places at both origins."""
    p = p or fs.params()
    panel = fs.panel(store)
    ids, _ = fs.spread_ids(panel, fs.rule_rows(store), fs.franklin_places(store))
    return [q for o in fs.SPREAD_ORIGINS for q in fs.pseudo_places(panel, ids, o, p)]


def mm_year_spread(ctx) -> dict:
    """D-092 run 9 (deviation (b)): the per-year negative-binomial φ over no-reform pseudo-forecasts."""
    f = cal.fit_noise(year_spread_places(ctx.store), "year", tol=1e-3 if ctx.quick else 1e-5)
    return {
        FILE: {"mm_year_spread_phi": {"value": _r(f.kappa, 2), "low": _r(f.low, 2), "high": _r(f.high, 2)}}
    }


def c4_inputs(store, phi: float, include=()) -> dict:
    """What C4 and D-100 fit on: M's fit places with year noise φ, the test places, the level places, the
    events and the panel."""
    p = fs.params()
    panel = fs.panel(store, include=include)
    rules = fs.rule_rows(store)
    classes = fs.bps_classes(store, set(panel["place"]))
    events, _ = fs.events_d092(panel, rules)
    fit_events, test_events = fs.split_events(events)
    m_fit, _ = fs.build_m(panel, classes, fit_events, p, p["s_dose"])
    m_test, _ = fs.build_m(panel, classes, test_events, p, p["s_dose"])
    lv, _, _ = fs.level_set(panel, rules, events, p)
    prior = cal.level_prior(cal.fit_level(lv), p["widening"])
    return {"fit": cal.with_phi(m_fit, phi), "test": cal.with_phi(m_test, phi), "prior": prior,
            "events": events, "panel": panel}  # fmt: skip


def mm_c4(ctx) -> dict:
    """D-092 run 10, challenger C4: M's likelihood with φ, the C0 baseline and the θ_L lognormal prior."""
    x = c4_inputs(ctx.store, _config("mm_year_spread_phi").value)
    f = cal.fit(x["fit"], halves=_halves(ctx), log_prior=x["prior"])
    return {
        FILE: {
            # config's precision: theta to 5 significant figures (its range to 4), alpha to 2 (its high to 3)
            "mm_mature_hazard_ref": {
                "value": _sig(f.theta, 5),
                "low": _sig(f.low, 4),
                "high": _sig(f.high, 4),
            },
            "mm_place_effect_variance": {
                "value": _sig(f.alpha, 2),
                "low": _sig(f.alpha_low, 2),
                "high": _sig(f.alpha_high, 3),
            },
            "mm_ramp_half_years": {"value": f.half, "low": f.half_low, "high": f.half_high},
        }
    }


ST_PAUL = "2758000"


def local_route_ids(store, places, panel) -> set[str]:
    """D-100's locally adopted places among `places` (`mm_routes.route_of`)."""
    from lotline.calibrate.mm import mm_routes as mr

    metro = mr.metro_geoids()
    pop = {}
    for st in fs.STATES:
        j = store.read(st.lower(), "jurisdictions")
        pop |= dict(zip(j["geoid"].astype(str), j["pop_2020"], strict=True))
    state_of = panel.groupby("place")["state"].first().to_dict()
    return {
        q.geoid
        for q in places
        if mr.route_of(state_of[q.geoid], q.geoid, pop.get(q.geoid), metro) == mr.LOCAL
    }


def mm_fast_ramp(ctx) -> dict:
    """D-100 run 1, R2: one half-way point per adoption route on C4's places plus St. Paul. The value and
    low are the locally adopted route's half-way point and its 90% set's floor; the high is C4's low end
    (D-100's cheaper alternative), read from config."""
    from lotline.calibrate.mm import mm_routes as mr

    x = c4_inputs(ctx.store, _config("mm_year_spread_phi").value, include=(ST_PAUL,))
    if ST_PAUL not in {q.geoid for q in x["fit"]}:
        raise ValueError("St. Paul has no usable D-092 event: check its rule row and panel years")
    local = local_route_ids(ctx.store, x["fit"] + x["test"], x["panel"])
    rf = mr.fit_routes(x["fit"], local, halves=_halves(ctx), log_prior=x["prior"])
    high = _config("mm_ramp_half_years").low
    return {FILE: {"mm_ramp_half_years_fast": {"value": rf.half_local, "low": rf.local_low, "high": high}}}
