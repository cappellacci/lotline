"""Missing-middle prediction and the V4 leave-one-place-out backtest (D-038): place totals drawn from the
fit, the benchmark, scores and the realized hazard.

Part of `calibrate_mm`, split by method step (modularity step 3); `calibrate_mm` re-exports every name.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import replace

import numpy as np
import pandas as pd

from .capacity import fit_capacity, scaled
from .fit import fit
from .places import ALPHA_POISSON, HALF_GRID, Place

# ---------------------------------------------------------------------------------------------------------
# Prediction and the V4 backtest
# ---------------------------------------------------------------------------------------------------------


def predict_total(place: Place, theta: float, log_se: float, alpha: float, half: float, draws=20_000, seed=0):
    """Predictive draws of the place's total buildings over its years: log θ normal, a new u, Poisson."""
    rng = np.random.default_rng(seed)
    th = np.exp(rng.normal(math.log(theta), log_se, size=draws)) if log_se > 0 else np.full(draws, theta)
    u = rng.gamma(1 / alpha, alpha, size=draws) if alpha >= ALPHA_POISSON else np.ones(draws)
    mu = place.B[None, :] + (th * u)[:, None] * place.k(half)[None, :]
    return rng.poisson(mu).sum(axis=1)


def benchmark_total(place: Place, rate: float, half: float, draws=20_000, seed=0):
    """Poisson draws of the total under a fixed hazard `rate` (0 = no effect), with no place effect."""
    rng = np.random.default_rng(seed)
    mu = place.B + rate * place.k(half)
    return rng.poisson(np.broadcast_to(mu, (draws, len(mu)))).sum(axis=1)


def score(place: Place, draws: np.ndarray) -> dict:
    """P10/P50/P90 of the total, whether the observed total is inside P10-P90, and the error of the median
    per 1,000 eligible parcels a year. By hand: observed 10 over 2 years on 1,000 parcels a year, median 14
    -> error (14 − 10) / 2 / 1,000 × 1,000 = 2.0."""
    p10, p50, p90 = np.percentile(draws, [10, 50, 90])
    obs = float(place.y.sum())
    per = float(np.mean(place.eligible)) * len(place.years) / 1000
    return {
        "observed": obs,
        "p10": float(p10),
        "p50": float(p50),
        "p90": float(p90),
        "covered": bool(p10 <= obs <= p90),
        "error_per_1000": float((p50 - obs) / per),
    }


def loo_backtest(
    places: Sequence[Place],
    outside_rate: float,
    outside_half: float,
    min_year: int = 2015,
    horizon: int = 5,
    halves=HALF_GRID,
    fit_fn=fit,
    hold_growth: bool = False,
    slopes=None,
) -> pd.DataFrame:
    """V4: for each place with T >= min_year, refit on the other places' years <= T − 1, predict its years
    T … T + horizon − 1, and score the fit against no effect and the outside rate (D-038). With `slopes`
    (D-042), the refit also profiles the capacity slope b and the target is predicted at θ exp(b z)."""
    rows = []
    for j, target in enumerate(places):
        if target.T < min_year:
            continue
        t = target.upto(target.T + horizon - 1)
        if hold_growth:  # a true forecast: the baseline stays at its pre-reform level
            t = replace(t, g=np.ones(len(t.g)))
        others = [p.upto(target.T - 1) for i, p in enumerate(places) if i != j]
        others = [p for p in others if len(p.years)]
        row = {"geoid": t.geoid, "name": t.name, "T": t.T, "years": len(t.years), "refit_places": len(others)}
        if len(others) >= 2:
            if slopes is None:
                f, b = fit_fn(others, halves), 0.0
            else:
                cf = fit_capacity(others, slopes, halves)
                f, b = cf.fit, cf.b
            tb = scaled([t], b)[0]
            s = score(tb, predict_total(tb, f.theta, f.log_se, f.alpha, f.half))
            row |= {"theta": f.theta, "half": f.half, "b": b} | {f"fit_{k}": v for k, v in s.items()}
        for name, rate in (("none", 0.0), ("outside", outside_rate)):
            s = score(t, benchmark_total(t, rate, outside_half))
            row |= {f"{name}_{k}": v for k, v in s.items() if k != "observed"}
        rows.append(row)
    return pd.DataFrame(rows)


def realized_hazard(places: Sequence[Place]) -> dict:
    """Exposure-weighted mean of (y − B) / (E × dose × F/F_ref) over the observed years, and the
    exposure-weighted distribution of event ages: what the data pin down without the ramp."""
    excess = sum(float((p.y - p.B).sum()) for p in places)
    expo = sum(float(p.kr.sum()) for p in places)
    ages = np.concatenate([p.age for p in places])
    w = np.concatenate([p.kr for p in places])
    order = np.argsort(ages)
    cw = np.cumsum(w[order]) / w.sum()
    pct = {q: float(ages[order][np.searchsorted(cw, q / 100)]) for q in (10, 50, 90)}
    return {
        "mean_hazard": excess / expo if expo else np.nan,
        "age_p10": pct[10],
        "age_p50": pct[50],
        "age_p90": pct[90],
    }
