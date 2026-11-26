"""Missing-middle statewide backtest (D-054): joint draws per place, state totals, the D-040 verdict, the
held-out log score and the state spread τ.

Part of `calibrate_mm`, split by method step (modularity step 3); `calibrate_mm` re-exports every name.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence

import numpy as np
import pandas as pd

from lotline.model.calibrate_adu import CHI2_90, LOG_ALPHA, _golden_max, gh_log_nodes

from .likelihood import KAPPA_NONE, Stack, _log_pois, _w_mixed, _ylogmu, loglik, place_loglik
from .places import ALPHA_POISSON, LOG_THETA, Place
from .year_spread import nb_year_terms

# ---------------------------------------------------------------------------------------------------------
# D-054: statewide backtest (joint draws, verdicts, held-out log score) and the state spread τ
# ---------------------------------------------------------------------------------------------------------

GH_NODES_STATE = 40  # Gauss-Hermite nodes over ln v_s (D-054, as D-043)


GH_THETA = 20  # Gauss-Hermite nodes over ln θ for the held-out log score (D-049, D-054)


TAU_GRID = tuple(np.round(np.arange(0.0, 2.5001, 0.05), 2))  # τ profile grid (D-054, as D-044)


def predict_places(
    places: Sequence[Place],
    theta: float,
    log_se: float,
    alpha: float,
    half: float,
    b: float = 0.0,
    draws: int = 20_000,
    seed: int = 0,
) -> dict[str, np.ndarray]:
    """Joint predictive counts {geoid: draws × years} (D-054, as `calibrate_adu.predict_places`): one θ per
    draw shared by every place (drawn first, so a seed gives the same θ draws in every refit); an independent
    u ~ Gamma(mean 1, variance α) per place from a stream keyed by (seed, geoid), so a place draws alike
    whichever places it is predicted with; Poisson counts on B + θ u exp(b z) k."""
    import zlib

    rng = np.random.default_rng(seed)
    th = np.exp(rng.normal(math.log(theta), log_se, size=draws)) if log_se > 0 else np.full(draws, theta)
    out = {}
    for p in places:
        r = np.random.default_rng([seed, zlib.crc32(p.geoid.encode())])
        u = r.gamma(1 / alpha, alpha, size=draws) if alpha >= ALPHA_POISSON else np.ones(draws)
        k = p.k(half) * math.exp(b * p.z)
        mu = p.B[None, :] + (th * u)[:, None] * k[None, :]
        out[p.geoid] = r.poisson(mu * _w_draws(p, seed, draws)[:, None] * _year_draws(p, seed, draws))
    return out


def benchmark_places(places: Sequence[Place], rate: float, half: float, draws: int = 20_000, seed: int = 0):
    """{geoid: draws × years} of Poisson counts on B + rate × k (0 = no effect), no place effect."""
    import zlib

    out = {}
    for p in places:
        r = np.random.default_rng([seed, zlib.crc32(p.geoid.encode())])
        mu = p.B + rate * p.k(half)
        m = (
            np.broadcast_to(mu, (draws, len(mu)))
            * _w_draws(p, seed, draws)[:, None]
            * _year_draws(p, seed, draws)
        )
        out[p.geoid] = r.poisson(m)
    return out


def _year_draws(p: Place, seed: int, draws: int) -> np.ndarray | float:
    """Per-year Gamma(mean 1, variance φ) multipliers (draws × years), so each year is NB(μ_t, φ) given the
    rest, from the place's own stream keyed by (seed, geoid, 2); 1.0 when φ = 0 (draws unchanged)."""
    import zlib

    if p.phi < KAPPA_NONE:
        return 1.0
    r = np.random.default_rng([seed, zlib.crc32(p.geoid.encode()), 2])
    return r.gamma(1 / p.phi, p.phi, size=(draws, len(p.years)))


def _w_draws(p: Place, seed: int, draws: int) -> np.ndarray:
    """The place's rate multiplier w ~ Gamma(mean 1, variance κ) per draw, from its own stream keyed by
    (seed, geoid, 1) so u and the Poisson draws are unchanged; all ones when κ = 0 (runs 4-5 exactly)."""
    import zlib

    if p.kappa < KAPPA_NONE:
        return np.ones(draws)
    r = np.random.default_rng([seed, zlib.crc32(p.geoid.encode()), 1])
    return r.gamma(1 / p.kappa, p.kappa, size=draws)


def state_total(draws_by_place: Mapping[str, np.ndarray], geoids: Sequence[str]) -> np.ndarray:
    """Per-draw total over the given places and their years."""
    return sum(draws_by_place[g].sum(axis=1) for g in geoids)


def verdict(observed: float, p10: float, p50: float, p90: float) -> str:
    """D-040's bar: 'useful' if inside P10-P90 and P50 / 2 <= observed <= 2 P50 (both 0 counts as met);
    'inside only' if inside but off by more than 2x; 'missed' otherwise.

    By hand (D-040's rows): 50 in 13-193 with P50 57 -> useful; 519 in 52-781 with P50 213 -> inside only;
    2,785 above 1,420 -> missed; 0 in 0-3 with P50 0 -> useful."""
    if not (p10 <= observed <= p90):
        return "missed"
    return "useful" if p50 / 2 <= observed <= 2 * p50 else "inside only"


def heldout_log_score(
    place: Place, theta: float, log_se: float, alpha: float, half: float, b: float = 0.0, n: int = GH_THETA
) -> float:
    """log ∫ P(y | B, θ k, α) dN(ln θ; ln θ̂, se²) by n-node Gauss-Hermite (D-049), with P = `place_loglik`
    (u integrated out, Σ log y! dropped). With se = 0 it is `place_loglik` at θ̂.

    By hand: Poisson (α ≈ 0), B = 0, one year, k = 1, y = 1, θ = 2, se = 0 -> ln 2 − 2."""
    k = place.k(half) * math.exp(b * place.z)
    if log_se <= 0:
        return place_loglik(place.y, place.B, k, theta, alpha, place.kappa, place.phi)
    x, lw = gh_log_nodes(log_se, n)
    terms = [
        w + place_loglik(place.y, place.B, k, theta * math.exp(xi), alpha, place.kappa, place.phi)
        for xi, w in zip(x, lw, strict=True)
    ]
    return float(np.logaddexp.reduce(terms))


def no_effect_log_score(place: Place) -> float:
    """Σ_t log Poisson(y_t; B_t), Σ log y! dropped (the no-effect benchmark's held-out log score); with the
    place's κ > 0, w integrated out (`_w_mixed`)."""
    if place.kappa >= KAPPA_NONE:
        y, B = np.asarray(place.y, float), np.asarray(place.B, float)
        return float(_w_mixed(_ylogmu(y, B).sum(), B.sum(), y.sum(), place.kappa))
    if place.phi >= KAPPA_NONE:
        return float(np.sum(nb_year_terms(place.y, place.B, place.phi)))
    return float(np.sum(_log_pois(place.y, place.B)))


def state_loglik(
    places: Sequence[Place],
    states: Sequence[str],
    theta: float,
    alpha: float,
    half: float,
    tau: float,
    n: int = GH_NODES_STATE,
) -> float:
    """Σ_s log ∫ Π_{i in s} P(y_i | B_i, θ v k_i, α) dN(ln v; 0, τ²) (D-054, as D-043): one multiplier per
    state, integrated by n-node Gauss-Hermite; τ = 0 is `loglik`.

    By hand (n = 2, nodes ln v = ±τ, weights 1/2): one state, one place, Poisson, B = 0, one year, k = 1,
    y = 0 -> log(½ e^(−θ e^τ) + ½ e^(−θ e^(−τ)))."""
    if tau <= 0:
        return loglik(places, theta, alpha, half)
    x, lw = gh_log_nodes(tau, n)
    total = 0.0
    for s in sorted(set(states)):
        mine = [p for p, st in zip(places, states, strict=True) if st == s]
        st = Stack.of(mine)
        terms = [w + loglik(st, theta * math.exp(xi), alpha, half) for xi, w in zip(x, lw, strict=True)]
        total += float(np.logaddexp.reduce(terms))
    return total


def tau_profile(
    places: Sequence[Place], states: Sequence[str], half: float, taus=TAU_GRID, tol: float = 1e-4
) -> pd.DataFrame:
    """ℓ_p(τ) = max over θ and α at each τ on the grid, with the half-way point held (D-054)."""
    rows = []
    for tau in taus:

        def best_alpha(lt, tau=tau):
            return _golden_max(
                lambda la: state_loglik(places, states, math.exp(lt), math.exp(la), half, tau),
                *LOG_ALPHA,
                tol=tol,
            )

        lt, ll = _golden_max(lambda lt: best_alpha(lt)[1], *LOG_THETA, tol=tol)
        rows.append(
            {"tau": float(tau), "theta": math.exp(lt), "alpha": math.exp(best_alpha(lt)[0]), "ll": ll}
        )
    return pd.DataFrame(rows)


def tau_summary(profile: pd.DataFrame, draws: int = 20_000, seed: int = 0) -> dict:
    """τ̂ and its 90% profile set on the grid; D-044's flat-prior distribution (p ∝ exp ℓ_p): median, P90,
    share at 0; and the unseen-state multiplier exp(τ z), P10-P90."""
    ll = profile["ll"].to_numpy(float)
    tau = profile["tau"].to_numpy(float)
    i = int(np.argmax(ll))
    inside = tau[2 * (ll[i] - ll) <= CHI2_90]
    p = np.exp(ll - ll.max())
    p = p / p.sum()
    rng = np.random.default_rng(seed)
    t = rng.choice(tau, size=draws, p=p)
    m = np.exp(t * rng.standard_normal(draws))
    return {
        "tau_hat": float(tau[i]),
        "tau_low": float(inside.min()),
        "tau_high": float(inside.max()),
        "estimable": bool(inside.max() < tau.max()),
        "tau_median": float(np.median(t)),
        "tau_p90": float(np.percentile(t, 90)),
        "share_at_0": float(np.mean(t == 0)),
        "multiplier_p10": float(np.percentile(m, 10)),
        "multiplier_p50": float(np.percentile(m, 50)),
        "multiplier_p90": float(np.percentile(m, 90)),
    }
