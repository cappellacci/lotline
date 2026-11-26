"""The arithmetic behind the ADU calibration steps (D-030, D-088, D-096, D-097, D-099), in library code.

Moved from `scripts/dev/adu_mx_grid.py` and `scripts/dev/adu_types_slopes.py` so `lotline calibrate` and the
scripts share one copy:

- `fit_at_mx`: A + place types with θ, α and β_core maximized at fixed rule shares (m_o, m_x).
- `grid_table` (D-097): the all-states fit at each m_x on the grid, and the draw weight of each m_x, the mean
  over the leave-one-state-out folds of each fold's normalized profile likelihood (`grid_weights`).
- `slope_bounds` and `log_slope` (D-030): central differences at the central value ± 10% of the parameter's
  range, clipped to the range.
- `with_ramp` and `ramp_profile` (D-048, phase 5): the D-096 fit at each ramp half-life on D-047's grid.
- `typed_for_state_effect` (D-043/D-044, phase 5): the D-096 places with the core multiplier folded in, as the
  state-effect likelihood reads them.
- `drift_sigmas` (D-091, phase 5): σ from the persistence forecaster's log scores on the drift grid.
"""

from __future__ import annotations

import math
from dataclasses import replace

import numpy as np
import pandas as pd

from lotline.model import adu_forecast as af
from lotline.model import adu_screen as scr
from lotline.model import adu_types as ty
from lotline.model import calibrate_adu as cal
from lotline.model import hazard

SLOPE_STEP = 0.1  # central ± this share of a parameter's range (as calibrate_adu.py --draw-terms)


def type_columns(places) -> np.ndarray:
    """The type indicator columns some place has (a column no place has is dropped)."""
    d = np.array([ty.type_d(p) for p in places])
    return d[:, [j for j in range(d.shape[1]) if d[:, j].any()]]


def fit_at_mx(places, m_o: float, m_x: float) -> dict:
    """θ, α, β_core and the log-likelihood with the rule shares held at (m_o, m_x)."""
    f = ty._maximize(scr.prepare(places, cal._cvals(m_o, m_x)), type_columns(places))
    return {"theta": math.exp(f.lt), "alpha": math.exp(f.la), "core": float(f.b[0]), "loglik": f.loglik}


def grid_weights(folds: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """(weight, weight_fold_max) by m_x from leave-one-state-out profile rows (`fold`, `m_x`, `loglik`).

    weight: each fold's likelihood exp(ll - max) normalized to sum 1 over the grid, averaged over folds.
    weight_fold_max: 1 / folds on each fold's maximizing m_x.

    By hand, two folds on m_x 0.1 and 0.2: fold a has ll (0, ln 3) -> (0.25, 0.75); fold b has (ln 3, 0) ->
    (0.75, 0.25); weight (0.5, 0.5); fold maxima 0.2 and 0.1 -> weight_fold_max (0.5, 0.5)."""
    f = folds.copy()
    f["rel"] = f.groupby("fold")["loglik"].transform(lambda x: np.exp(x - x.max()))
    f["norm"] = f.groupby("fold")["rel"].transform(lambda x: x / x.sum())
    w = f.groupby("m_x")["norm"].mean()
    tops = f.loc[f.groupby("fold")["loglik"].idxmax(), "m_x"]
    return w, tops.value_counts() / len(tops)


def grid_table(prof: pd.DataFrame, m_o: float, places: int, place_years: int) -> pd.DataFrame:
    """config/params/adu_partial_share_grid.csv from the profile rows (fold "all" and "without XX")."""
    folds = prof[prof["fold"] != "all"]
    w, wmax = grid_weights(folds)
    grid = prof[prof["fold"] == "all"].set_index("m_x")[["theta", "alpha", "core", "loglik"]]
    grid["weight"] = w.reindex(grid.index).fillna(0.0)
    grid["weight_fold_max"] = wmax.reindex(grid.index).fillna(0.0)
    grid = grid.reset_index()
    grid["source"] = (
        f"D-097: A + P at m_x held, m_o {m_o}, {places} places, {place_years} place-years "
        "(scripts/dev/adu_mx_grid.py on the D-096 rows); weight = mean of the leave-one-state-out folds' "
        "normalized profile likelihoods"
    )
    return grid


def grid_csv(grid: pd.DataFrame) -> str:
    """The grid as the config file holds it (6 significant figures)."""
    return grid.to_csv(index=False, float_format="%.6g")


def folds_of(places) -> list[tuple[str, list]]:
    """[("all", places), ("without XX", places outside XX), ...] in state order."""
    states = sorted({p.state for p in places})
    return [("all", list(places))] + [(f"without {s}", [p for p in places if p.state != s]) for s in states]


def slope_bounds(value: float, low: float, high: float, step: float = SLOPE_STEP) -> tuple[float, float]:
    """(lo, hi) for a central difference: value ± step × (high - low), clipped to [low, high]. By hand: value
    0.5 on [0, 1] -> (0.4, 0.6); value 0.95 -> (0.85, 1.0)."""
    d = step * (high - low)
    return max(low, value - d), min(high, value + d)


def log_slope(f_lo: float, f_hi: float, lo: float, hi: float) -> float:
    """d log f / dp by a central difference. By hand: f 1 at p 0 and e at p 2 -> 0.5."""
    return (math.log(f_hi) - math.log(f_lo)) / (hi - lo)


# ---------------------------------------------------------------------------------------------------------
# Phase 5: the three steps fitted on older forms
# ---------------------------------------------------------------------------------------------------------

NO_RAMP = -1.0  # half-life code for "no ramp" (as calibrate_shape.NO_RAMP)
RAMP_HALVES = (NO_RAMP, 0.5, 1.0, 2.0, 3.5, 6.0)  # D-047's pre-registered grid of half-lives
RAMP_SLOPE = 0.75  # D-047 held the slope at its then-central value


def with_ramp(pl, half: float, slope: float = RAMP_SLOPE):
    """The place with each rule's coverage × ramp(age) in place of coverage × 1 (D-048's form). NO_RAMP gives
    coverage alone where a rule is in force. By hand: coverage 0.5 at age 2, half 2 -> 0.5 × 0.5 = 0.25."""
    age, cov = pl.extra["age"], pl.extra["cov"]
    live = ~np.isnan(age)
    r = np.ones_like(age) if half == NO_RAMP else hazard.ramp(np.nan_to_num(age), half, slope)
    return replace(pl, cr=np.where(live, cov * r, 0.0))


def ramp_profile(places, cvals, halves=RAMP_HALVES) -> pd.DataFrame:
    """θ, α, β_core and the log-likelihood at each half-life, rule shares held at `cvals` (D-096's form)."""
    zm = type_columns(places)
    rows = []
    for h in halves:
        f = ty._maximize(scr.prepare([with_ramp(p, h) for p in places], cvals), zm)
        rows.append({"half": h, "theta": math.exp(f.lt), "alpha": math.exp(f.la), "core": float(f.b[0]),
                     "loglik": f.loglik})  # fmt: skip
    return pd.DataFrame(rows)


def typed_for_state_effect(places, core: float):
    """Each place's exposure × exp(β_core × core), the town term at 0 (as `adu_joint`'s information SEs)."""
    return [ty.typed_scaled(p, 0.0, np.array([core, 0.0])) for p in places]


def drift_grids(places, states) -> dict[str, tuple[str, np.ndarray]]:
    """{geoid: (state, F0 log scores on `adu_forecast.LOGD_GRID`)} for the places with history (D-090's class)
    in `states`: fit 2016-2019, window 2021-2025."""
    out = {}
    for p in places:
        if p.state in states and af.place_class(p) == "history":
            fp, wp = af.split(p)
            out[p.geoid] = (p.state, np.array([af.f0_log_score(fp, wp, ld) for ld in af.LOGD_GRID]))
    return out


def drift_sigmas(grids: dict, states) -> dict[str, float]:
    """D-091's σ (F0): {"all": every state's places, "without XX": leaving XX out}."""
    out = {"all": af.fit_sigma([g for _, g in grids.values()])}
    for s in states:
        out[f"without {s}"] = af.fit_sigma([g for st, g in grids.values() if st != s])
    return out
