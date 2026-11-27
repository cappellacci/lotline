"""Missing-middle year spread (D-092 run 7 and 9): attach φ or κ to places and fit them on the uncoded
places' pseudo-forecasts (`fit_noise`, `fit_kappa`).

Part of `calibrate_mm`, split by method step (modularity step 3); `calibrate_mm` re-exports every name.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace

import numpy as np

from lotline.calibrate.adu.calibrate_adu import _golden_max

from .likelihood import KAPPA_NONE, LOG_KAPPA, Stack, _interval, _log_pois, _w_mixed, _ylogmu
from .places import Place


def with_phi(places: Sequence[Place], phi: float) -> list[Place]:
    """The places with the per-year NB overdispersion φ set (D-092 deviation (b)); κ is cleared."""
    return [replace(p, phi=float(phi), kappa=0.0) for p in places]


def with_phi_by(places: Sequence[Place], phi_of: Mapping[str, float]) -> list[Place]:
    """The places each with their own φ (D-092 deviation (c): φ by place type), keyed by geoid; κ is cleared.
    Every place must be in `phi_of`."""
    return [replace(p, phi=float(phi_of[p.geoid]), kappa=0.0) for p in places]


def with_kappa(places: Sequence[Place], kappa: float) -> list[Place]:
    """The places with the rate-multiplier variance κ set (D-092 deviation 2026-11-15)."""
    return [replace(p, kappa=float(kappa), phi=0.0) for p in places]


@dataclass(frozen=True)
class KappaFit:
    kappa: float
    low: float  # 90% profile-likelihood interval
    high: float
    loglik: float
    loglik_poisson: float  # κ = 0, for the likelihood-ratio
    n_places: int
    n_years: int


def nb_year_terms(y, mu, phi: float):
    """Per-year log NB(y; mean μ, variance μ + φ μ²), log y! dropped (as `_log_pois`), D-092 deviation (b)'s
    form Ny. φ below KAPPA_NONE gives the Poisson y ln μ − μ.

    By hand: y = 1, μ = 2, φ = 1 (r = 1): lnΓ(2) − lnΓ(1) + 1·ln(1/3) + 1·ln(2/3) = ln(2/9)."""
    y, mu = np.asarray(y, dtype=float), np.asarray(mu, dtype=float)
    if phi < KAPPA_NONE:
        return _log_pois(y, mu)
    r = 1.0 / phi
    lg = np.vectorize(math.lgamma, otypes=[float])(y + r) - math.lgamma(r)
    with np.errstate(divide="ignore", invalid="ignore"):
        ymu = np.where(y > 0, y * np.log(np.where(mu > 0, mu, 1.0) / (r + mu)), 0.0)
        ymu = ymu + np.where((mu <= 0) & (y > 0), -np.inf, 0.0)
    return lg + r * np.log(r / (r + mu)) + ymu


def baseline_scores(places: Sequence[Place], form: str, param: float) -> np.ndarray:
    """Per place: log P(y | B) under a baseline noise form, Σ log y! dropped (D-092 deviation (b)): 'w' (one
    multiplier per place, variance `param`, `_w_mixed`) or 'year' (independent NB per year, φ = `param`)."""
    st = places if isinstance(places, Stack) else Stack.of(with_kappa(places, 0.0))
    if form == "w":
        return _w_mixed(
            np.add.reduceat(_ylogmu(st.y, st.B), st.starts),
            np.add.reduceat(st.B, st.starts),
            np.add.reduceat(st.y, st.starts),
            param,
        )
    if form == "year":
        return np.add.reduceat(nb_year_terms(st.y, st.B, param), st.starts)
    raise ValueError(f"unknown noise form {form!r}")


def fit_noise(places: Sequence[Place], form: str = "w", tol: float = 1e-5) -> KappaFit:
    """The maximum-likelihood noise parameter of `baseline_scores` (κ for 'w', φ for 'year'), with its 90%
    profile interval; 0 when the Poisson fits as well. Uses only B: pass places with no reform in their
    years."""
    st = Stack.of(with_kappa(places, 0.0))

    def ll(lk):
        return float(np.sum(baseline_scores(st, form, math.exp(lk))))

    lk, best = _golden_max(ll, *LOG_KAPPA, tol=tol)
    pois = float(np.sum(baseline_scores(st, form, 0.0)))
    if pois >= best:
        hi = _interval(ll, LOG_KAPPA[0], pois, *LOG_KAPPA)[1]
        return KappaFit(0.0, 0.0, math.exp(hi), pois, pois, st.n_places, len(st.y))
    lo, hi = _interval(ll, lk, best, *LOG_KAPPA)
    return KappaFit(math.exp(lk), math.exp(lo), math.exp(hi), best, pois, st.n_places, len(st.y))


def fit_kappa(places: Sequence[Place], tol: float = 1e-5) -> KappaFit:
    """κ̂: the maximum-likelihood variance of w in y_t ~ Poisson(w B_t), w ~ Gamma(mean 1, variance κ), one w
    per place, over no-reform pseudo-forecasts (D-092 deviation 2026-11-15). Only B is used: any reform
    term (k) is ignored, so pass places with no reform in their years.

    By hand: two places, one year each, B = 1, y = 0 and 2: mean ratio 1, sample variance of y/B 2 -> above
    the Poisson's 1, so κ̂ > 0 (and κ̂ = 0 when y = 1, 1)."""
    st = Stack.of(with_kappa(places, 0.0))
    Y = np.add.reduceat(st.y, st.starts)
    ylm = np.add.reduceat(_ylogmu(st.y, st.B), st.starts)
    M = np.add.reduceat(st.B, st.starts)

    def ll(lk):
        return float(np.sum(_w_mixed(ylm, M, Y, math.exp(lk))))

    lk, best = _golden_max(ll, *LOG_KAPPA, tol=tol)
    pois = float(np.sum(_w_mixed(ylm, M, Y, 0.0)))
    if pois >= best:  # no extra spread: κ̂ = 0, with the upper bound from the profile
        lo, hi = LOG_KAPPA[0], _interval(ll, LOG_KAPPA[0], pois, *LOG_KAPPA)[1]
        return KappaFit(0.0, 0.0, math.exp(hi), pois, pois, st.n_places, len(st.y))
    lo, hi = _interval(ll, lk, best, *LOG_KAPPA)
    return KappaFit(math.exp(lk), math.exp(lo), math.exp(hi), best, pois, st.n_places, len(st.y))
