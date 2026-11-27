"""Missing-middle hazard fit (D-038, D-062): θ with α and the ramp's half-way point profiled out, its 90%
interval, and the five-year ramp profile (`ramp_mean`, `five_year_profile`).

Part of `calibrate_mm`, split by method step (modularity step 3); `calibrate_mm` re-exports every name.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd

from lotline.calibrate.adu.calibrate_adu import CHI2_90, LOG_ALPHA, Z_95, _golden_max
from lotline.model.hazard import ramp

from .likelihood import Stack, _interval, loglik
from .places import HALF_GRID, LOG_THETA, SLOPE, Place


@dataclass(frozen=True)
class Fit:
    theta: float
    low: float  # 90% profile-likelihood interval
    high: float
    alpha: float
    alpha_low: float
    alpha_high: float
    half: float
    half_low: float
    half_high: float
    loglik: float
    n_places: int
    n_years: int
    profile_half: dict  # half -> max log-likelihood

    @property
    def log_se(self) -> float:
        return (math.log(self.high) - math.log(self.low)) / (2 * Z_95)


def _best_alpha(places, theta, half, tol=1e-4):
    la, ll = _golden_max(lambda la: loglik(places, theta, math.exp(la), half), *LOG_ALPHA, tol=tol)
    return math.exp(la), ll


def log_prior_term(log_theta: float, log_prior: tuple[float, float] | None) -> float:
    """−(ln θ − m)² / (2 s²) for a lognormal prior (m, s) on θ (constant dropped); 0 without a prior (D-092
    C4). By hand: m = ln 0.001, s = 0.5, θ = 0.001 e -> −1 / 0.5 = −2."""
    if log_prior is None:
        return 0.0
    m, sd = log_prior
    return -((log_theta - m) ** 2) / (2 * sd**2)


def _best_at_half(places, half, log_theta=LOG_THETA, tol=1e-4, log_prior=None):
    lt, ll = _golden_max(
        lambda lt: _best_alpha(places, math.exp(lt), half)[1] + log_prior_term(lt, log_prior),
        *log_theta,
        tol=tol,
    )
    return math.exp(lt), _best_alpha(places, math.exp(lt), half)[0], ll


def _best_theta(places, alpha, half, tol=1e-4, log_prior=None) -> float:
    return _golden_max(
        lambda lt: loglik(places, math.exp(lt), alpha, half) + log_prior_term(lt, log_prior),
        *LOG_THETA,
        tol=tol,
    )[1]


def profile_theta(places, theta: float, halves=HALF_GRID, log_prior=None) -> float:
    """ℓ_p(θ) = max over the half-way grid and α (plus the log prior on θ when given)."""
    return max(_best_alpha(places, theta, h)[1] for h in halves) + log_prior_term(math.log(theta), log_prior)


def fit(places: Sequence[Place], halves=HALF_GRID, log_prior: tuple[float, float] | None = None) -> Fit:
    """Maximum likelihood (θ, α, half) with profile-likelihood 90% intervals (D-038).

    `log_prior` (m, s): a lognormal prior on θ, ln θ ~ N(m, s²) (D-092 challenger C4). The fit then maximizes
    the log-likelihood plus `log_prior_term` (a penalized likelihood, reported in `loglik`), and the
    intervals use the same χ² cut on that sum. None (the default) is the plain D-038 fit."""
    n_years = int(sum(len(p.years) for p in places))
    places = Stack.of(places)
    by_half = {h: _best_at_half(places, h, log_prior=log_prior) for h in halves}
    half = max(by_half, key=lambda h: by_half[h][2])
    theta, alpha, ll = by_half[half]
    lt_lo, lt_hi = _interval(
        lambda lt: profile_theta(places, math.exp(lt), halves, log_prior), math.log(theta), ll, *LOG_THETA
    )

    def profile_alpha(la):
        return max(_best_theta(places, math.exp(la), h, log_prior=log_prior) for h in halves)

    la_lo, la_hi = _interval(
        profile_alpha,
        math.log(alpha),
        ll,
        *LOG_ALPHA,
    )
    inside = [h for h in halves if 2 * (ll - by_half[h][2]) <= CHI2_90]
    return Fit(
        theta=theta,
        low=math.exp(lt_lo),
        high=math.exp(lt_hi),
        alpha=alpha,
        alpha_low=math.exp(la_lo),
        alpha_high=math.exp(la_hi),
        half=float(half),
        half_low=float(min(inside)),
        half_high=float(max(inside)),
        loglik=ll,
        n_places=places.n_places,
        n_years=n_years,
        profile_half={float(h): v[2] for h, v in by_half.items()},
    )


SCENARIO_AGES = (0.5, 1.5, 2.5, 3.5, 4.5)  # D-062: mid-year ages of the five scenario years


def ramp_mean(half: float, ages: Sequence[float] = SCENARIO_AGES, slope: float = SLOPE) -> float:
    """m(half): the mean ramp share over the scenario's five years (D-062).

    By hand, slope 0.75: half 0.5 -> (0.5 + 0.7914 + 0.9350 + 0.9820 + 0.9952) / 5 = 0.8407;
    half 6.0 -> (0.00065 + 0.00248 + 0.00932 + 0.03445 + 0.11920) / 5 = 0.0332.
    """
    return float(np.mean(ramp(np.asarray(ages, dtype=float), half, slope)))


@dataclass(frozen=True)
class FiveYearFit:
    r5: float  # θ × m(half) at the maximum: mean hazard per eligible parcel per year over the five years
    low: float  # 90% profile-likelihood interval
    high: float
    loglik: float
    by_half: pd.DataFrame  # half, m, theta, alpha, loglik, r5: the best fit at each half-way point


def five_year_profile(places, halves=HALF_GRID, ages: Sequence[float] = SCENARIO_AGES) -> FiveYearFit:
    """Profile likelihood of r5 = θ × m(half) (D-062): ℓ_p(r5) = max over half and α of ℓ(r5 / m(half), α,
    half), with its 90% interval by the χ² cut used for θ. Only a reparameterization: the maximum is the
    fit's, r5̂ = θ̂ × m(half̂)."""
    st = Stack.of(places)
    m = {h: ramp_mean(h, ages) for h in halves}
    rows = []
    for h in halves:
        theta, alpha, ll = _best_at_half(st, h)
        rows.append({"half": float(h), "m": m[h], "theta": theta, "alpha": alpha, "loglik": ll,
                     "r5": theta * m[h]})  # fmt: skip
    by_half = pd.DataFrame(rows)
    best = by_half.loc[by_half["loglik"].idxmax()]

    def prof(lr):
        r5 = math.exp(lr)
        return max(_best_alpha(st, r5 / m[h], h)[1] for h in halves)

    lo_b = LOG_THETA[0] + math.log(min(m.values()))
    hi_b = LOG_THETA[1] + math.log(max(m.values()))
    lo, hi = _interval(prof, math.log(best["r5"]), float(best["loglik"]), lo_b, hi_b)
    return FiveYearFit(float(best["r5"]), math.exp(lo), math.exp(hi), float(best["loglik"]), by_half)
