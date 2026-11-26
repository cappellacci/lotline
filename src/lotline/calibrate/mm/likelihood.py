"""Missing-middle hazard likelihood (D-038, D-092 run 7 and 9): the Poisson-gamma place likelihood with
u integrated out on a log grid, the place multiplier w (κ) and the per-year negative binomial (φ) forms, and
`loglik` over stacked places.

Part of `calibrate_mm`, split by method step (modularity step 3); `calibrate_mm` re-exports every name.
"""

from __future__ import annotations

import functools
import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from lotline.model.calibrate_adu import CHI2_90
from lotline.model.hazard import ramp

from .places import _V, ALPHA_LOCAL, ALPHA_POISSON, SLOPE, Place

# ---------------------------------------------------------------------------------------------------------
# Likelihood
# ---------------------------------------------------------------------------------------------------------


@functools.lru_cache(maxsize=4096)
def _u_grid(alpha: float) -> tuple[np.ndarray, np.ndarray, float]:
    """(u values, weights summing to 1 − lump, lump mass at u = 0) for u ~ Gamma(mean 1, variance α)."""
    r = 1.0 / alpha
    if alpha < ALPHA_LOCAL:
        s = math.sqrt(alpha)
        v = np.linspace(-10 * s, 10 * s, 401)
        lump = 0.0
    else:
        v = _V
        # P(u < e^v0) ≈ (r x)^r / (r Γ(r)), the leading term of the lower incomplete gamma
        lump = min(1.0, math.exp(r * (math.log(r) + v[0]) - math.log(r) - math.lgamma(r)))
    ld = r * math.log(r) - math.lgamma(r) + r * v - r * np.exp(v)
    w = np.exp(ld - ld.max())
    w[0] *= 0.5
    w[-1] *= 0.5
    w = w / w.sum() * (1.0 - lump)
    return np.exp(v), w, lump


def _log_pois(y, mu):
    with np.errstate(divide="ignore"):
        return np.where(mu > 0, y * np.log(np.where(mu > 0, mu, 1.0)) - mu, np.where(y > 0, -np.inf, 0.0))


KAPPA_NONE = 1e-9  # below it the rate multiplier w is 1 (runs 4-5 exactly)


LOG_KAPPA = (-9.0, 3.0)  # κ searched from ~1e-4 to ~20


def _w_mixed(ylogmu, M, Y, kappa: float):
    """log ∫ Π_t Poisson(y_t; w μ_t) dGamma(w; mean 1, variance κ), Σ log y_t! dropped, from the sums a
    place's years give: ylogmu = Σ y_t ln μ_t, M = Σ μ_t, Y = Σ y_t (arrays broadcast). With r = 1/κ the
    integral is closed: Σ y ln μ + r ln r + lnΓ(r + Y) − lnΓ(r) − (r + Y) ln(r + M). κ below KAPPA_NONE
    gives the Poisson Σ y ln μ − M (D-092 deviation 2026-11-15).

    By hand: one year, μ = 2, y = 1, κ = 1 (r = 1): ln 2 + 0 + ln Γ(2) − 0 − 2 ln 3 = ln(2/9)."""
    if kappa < KAPPA_NONE:
        return ylogmu - M
    r = 1.0 / kappa
    Y = np.asarray(Y, dtype=float)
    lg = np.vectorize(math.lgamma, otypes=[float])(r + Y) - math.lgamma(r)
    with np.errstate(divide="ignore", invalid="ignore"):
        return ylogmu + r * math.log(r) + lg - (r + Y) * np.log(r + M)


def _ylogmu(y, mu):
    """Σ-ready y ln μ, 0 where y = 0 and −inf where μ = 0 < y."""
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(y > 0, y * np.log(np.where(mu > 0, mu, 1.0)), 0.0) + np.where(
            (mu <= 0) & (y > 0), -np.inf, 0.0
        )


def _place_loglik_w(y, B, k, theta: float, alpha: float, kappa: float) -> float:
    """`place_loglik` with the rate multiplier w (κ > 0): u on its grid, w in closed form."""
    if alpha < ALPHA_POISSON:
        mu = B + theta * k
        return float(_w_mixed(_ylogmu(y, mu).sum(), mu.sum(), y.sum(), kappa))
    u, wts, lump = _u_grid(alpha)
    mu = B[None, :] + theta * u[:, None] * k[None, :]
    ll = _w_mixed(_ylogmu(y[None, :], mu).sum(axis=1), mu.sum(axis=1), y.sum(), kappa)
    with np.errstate(divide="ignore"):
        terms = np.log(wts) + ll
        if lump > 0:
            terms = np.append(
                terms, math.log(lump) + float(_w_mixed(_ylogmu(y, B).sum(), B.sum(), y.sum(), kappa))
            )
    return float(np.logaddexp.reduce(terms))


def place_loglik(y, B, k, theta: float, alpha: float, kappa: float = 0.0, phi: float = 0.0) -> float:
    """log ∫∫ Π_t Poisson(y_t; w (B_t + θ u k_t)) dGamma(u; mean 1, var α) dGamma(w; mean 1, var κ), dropping
    Σ log y_t! (a constant). w (D-092 deviation 2026-11-15) is integrated in closed form (`_w_mixed`); κ = 0
    is the run-4 likelihood.

    Poisson (α -> 0) at u = 1. With B = 0 and one year it is the negative binomial with mean θk and
    Var = μ + αμ² (`calibrate_adu.nb_loglik`, plus log y!).
    """
    y, B, k = (np.asarray(a, dtype=float) for a in (y, B, k))
    if kappa >= KAPPA_NONE and phi >= KAPPA_NONE:
        raise ValueError("use one noise form: kappa (per place) or phi (per year), not both")
    if kappa >= KAPPA_NONE:
        return _place_loglik_w(y, B, k, theta, alpha, kappa)
    if phi >= KAPPA_NONE:
        return _place_loglik_y(y, B, k, theta, alpha, phi)
    if alpha < ALPHA_POISSON:
        return float(np.sum(_log_pois(y, B + theta * k)))
    u, w, lump = _u_grid(alpha)
    ll = _log_pois(y[None, :], B[None, :] + theta * u[:, None] * k[None, :]).sum(axis=1)
    with np.errstate(divide="ignore"):
        terms = np.log(w) + ll
        if lump > 0:
            terms = np.append(terms, math.log(lump) + float(np.sum(_log_pois(y, B))))
    return float(np.logaddexp.reduce(terms))


@dataclass(frozen=True)
class Stack:
    """Every place's years laid end to end, so the likelihood is computed in one array (`starts` marks where
    each place begins)."""

    y: np.ndarray
    B: np.ndarray
    kr: np.ndarray
    age: np.ndarray
    starts: np.ndarray
    n_places: int
    kappa: float = 0.0
    phi: float | np.ndarray = 0.0  # one φ, or one per year-row when places carry φ by type (deviation (c))

    @classmethod
    def of(cls, places: Sequence[Place]) -> Stack:
        if isinstance(places, Stack):
            return places
        kappas, phis = {p.kappa for p in places}, {p.phi for p in places}
        mixed_phi = len(phis) > 1 and min(phis) >= KAPPA_NONE and max(kappas, default=0.0) < KAPPA_NONE
        if len(kappas) > 1 or (len(phis) > 1 and not mixed_phi):
            raise ValueError(
                f"places carry different noise values: kappa {sorted(kappas)}, phi {sorted(phis)}"
            )
        lens = [len(p.years) for p in places]
        if mixed_phi:  # D-092 deviation (c): every place has its own φ > 0 (its type's)
            phi_rows = np.concatenate([np.full(len(p.years), p.phi) for p in places])
        return cls(
            y=np.concatenate([p.y for p in places]),
            B=np.concatenate([p.B for p in places]),
            kr=np.concatenate([p.kr for p in places]),
            age=np.concatenate([p.age for p in places]),
            starts=np.concatenate([[0], np.cumsum(lens)[:-1]]).astype(int),
            n_places=len(places),
            kappa=kappas.pop() if kappas else 0.0,
            phi=phi_rows if mixed_phi else (phis.pop() if phis else 0.0),
        )


def loglik(places, theta: float, alpha: float, half: float, slope: float = SLOPE) -> float:
    """Σ over places of `place_loglik`, computed on the stacked years."""
    st = Stack.of(places)
    k = st.kr * ramp(st.age, half, slope)
    if st.kappa >= KAPPA_NONE and _phi_on(st.phi):
        raise ValueError("use one noise form: kappa (per place) or phi (per year), not both")
    if st.kappa >= KAPPA_NONE:
        return _loglik_w(st, k, theta, alpha)
    if _phi_on(st.phi):
        return _loglik_y(st, k, theta, alpha)
    if alpha < ALPHA_POISSON:
        return float(np.sum(_log_pois(st.y, st.B + theta * k)))
    u, w, lump = _u_grid(alpha)
    ll = np.add.reduceat(
        _log_pois(st.y[None, :], st.B[None, :] + theta * u[:, None] * k[None, :]), st.starts, axis=1
    )  # (grid, places)
    with np.errstate(divide="ignore"):
        terms = np.log(w)[:, None] + ll
        if lump > 0:
            base = np.add.reduceat(_log_pois(st.y, st.B), st.starts)
            terms = np.vstack([terms, math.log(lump) + base[None, :]])
    return float(np.logaddexp.reduce(terms, axis=0).sum())


def _loglik_w(st: Stack, k: np.ndarray, theta: float, alpha: float) -> float:
    """`loglik` with the rate multiplier w (κ = st.kappa > 0): per place, u on its grid and w in closed
    form."""
    Y = np.add.reduceat(st.y, st.starts)
    if alpha < ALPHA_POISSON:
        mu = st.B + theta * k
        ll = _w_mixed(
            np.add.reduceat(_ylogmu(st.y, mu), st.starts), np.add.reduceat(mu, st.starts), Y, st.kappa
        )
        return float(np.sum(ll))
    u, wts, lump = _u_grid(alpha)
    mu = st.B[None, :] + theta * u[:, None] * k[None, :]
    ll = _w_mixed(
        np.add.reduceat(_ylogmu(st.y[None, :], mu), st.starts, axis=1),
        np.add.reduceat(mu, st.starts, axis=1),
        Y[None, :],
        st.kappa,
    )  # (grid, places)
    with np.errstate(divide="ignore"):
        terms = np.log(wts)[:, None] + ll
        if lump > 0:
            base = _w_mixed(
                np.add.reduceat(_ylogmu(st.y, st.B), st.starts), np.add.reduceat(st.B, st.starts), Y, st.kappa
            )
            terms = np.vstack([terms, math.log(lump) + base[None, :]])
    return float(np.logaddexp.reduce(terms, axis=0).sum())


def _phi_on(phi) -> bool:
    """True when φ (a number, or one per year-row) is in use; `Stack.of` refuses a mix of on and off."""
    return bool(np.all(np.asarray(phi) >= KAPPA_NONE))


def _nb_core(y, mu, phi, lg):
    """`nb_year_terms` with the μ-free part lg = lnΓ(y + r) − lnΓ(r) passed in (it is fixed for a fit, so it
    is computed once per call, not once per u node)."""
    r = 1.0 / phi
    with np.errstate(divide="ignore", invalid="ignore"):
        ymu = np.where(y > 0, y * np.log(np.where(mu > 0, mu, 1.0) / (r + mu)), 0.0)
        ymu = ymu + np.where((mu <= 0) & (y > 0), -np.inf, 0.0)
    return lg + r * np.log(r / (r + mu)) + ymu


def _lg(y, phi):
    """lnΓ(y + r) − lnΓ(r), r = 1/φ; φ a number or one per element of y."""
    r = 1.0 / np.asarray(phi, dtype=float)
    lgam = np.vectorize(math.lgamma, otypes=[float])
    return lgam(np.asarray(y, dtype=float) + r) - lgam(r)


def _place_loglik_y(y, B, k, theta: float, alpha: float, phi: float) -> float:
    """`place_loglik` with per-year NB noise (φ > 0): Π_t NB(y_t; B_t + θ u k_t, φ), u on its grid."""
    lg = _lg(y, phi)
    if alpha < ALPHA_POISSON:
        return float(np.sum(_nb_core(y, B + theta * k, phi, lg)))
    u, wts, lump = _u_grid(alpha)
    ll = _nb_core(y[None, :], B[None, :] + theta * u[:, None] * k[None, :], phi, lg[None, :]).sum(axis=1)
    with np.errstate(divide="ignore"):
        terms = np.log(wts) + ll
        if lump > 0:
            terms = np.append(terms, math.log(lump) + float(np.sum(_nb_core(y, B, phi, lg))))
    return float(np.logaddexp.reduce(terms))


def _loglik_y(st: Stack, k: np.ndarray, theta: float, alpha: float) -> float:
    """`loglik` with per-year NB noise (φ = st.phi > 0), per place, u on its grid."""
    lg = _lg(st.y, st.phi)
    if alpha < ALPHA_POISSON:
        return float(np.sum(_nb_core(st.y, st.B + theta * k, st.phi, lg)))
    u, wts, lump = _u_grid(alpha)
    mu = st.B[None, :] + theta * u[:, None] * k[None, :]
    ll = np.add.reduceat(_nb_core(st.y[None, :], mu, st.phi, lg[None, :]), st.starts, axis=1)
    with np.errstate(divide="ignore"):
        terms = np.log(wts)[:, None] + ll
        if lump > 0:
            base = np.add.reduceat(_nb_core(st.y, st.B, st.phi, lg), st.starts)
            terms = np.vstack([terms, math.log(lump) + base[None, :]])
    return float(np.logaddexp.reduce(terms, axis=0).sum())


def _interval(f, x_hat: float, f_hat: float, lo: float, hi: float, iters: int = 25) -> tuple[float, float]:
    """{x : 2(f̂ − f(x)) <= CHI2_90} by bisection on each side of x̂ (returns the bound if never crossed)."""
    cut = f_hat - CHI2_90 / 2

    def side(a, b):  # a inside, b the outer bound
        if f(b) >= cut:
            return b
        for _ in range(iters):
            m = (a + b) / 2
            a, b = (m, b) if f(m) >= cut else (a, m)
        return (a + b) / 2

    return side(x_hat, lo), side(x_hat, hi)
