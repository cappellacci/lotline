"""D-083: screen the ADU model's place effects against place factors the fit does not use.

One factor at a time, the adopted Poisson-gamma form (D-079 Form A) is refitted with each place's exposure
scaled by exp(β z_i), where z is the factor standardized over the screened places:

    E[y_it | u_i] = θ_s · exp(β z_i) · u_i · k_it,   u_i ~ Gamma(mean 1, variance α)

θ_s is one rate per state ("within", the main read) or one rate for all places ("pooled"). The likelihood is
`calibrate_adu.frailty_loglik` at the scaled rate. Here it is vectorized over places and blank-field
combinations, so the nested profile fits are fast. Nothing here is written to config.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd

from lotline.model import calibrate_adu as cal

LOG_THETA = (-16.0, 2.0)
LOG_ALPHA = (math.log(1e-4), math.log(50.0))
BETA = (-4.0, 4.0)
CHI2_90 = 2.705543454095404  # χ²(1) 90th percentile: the 90% profile interval
TOL = 1e-5
_lgamma = np.vectorize(math.lgamma, otypes=[float])


@dataclass(frozen=True)
class Prepared:
    """Per place (rows) and blank-field combination (columns, padded): log weight, total exposure K = Σ_t k_t,
    head H = Σ_t y_t log k_t − Σ log y_t! (−inf where a year has y > 0 and k = 0), and the place's total Y."""

    geoids: tuple[str, ...]
    states: tuple[str, ...]
    log_w: np.ndarray
    K: np.ndarray
    H: np.ndarray
    Y: np.ndarray

    def subset(self, keep: np.ndarray) -> Prepared:
        keep = np.asarray(keep, dtype=bool)
        return Prepared(
            tuple(g for g, k in zip(self.geoids, keep, strict=True) if k),
            tuple(s for s, k in zip(self.states, keep, strict=True) if k),
            self.log_w[keep],
            self.K[keep],
            self.H[keep],
            self.Y[keep],
        )


def prepare_arrays(
    ys: Sequence[np.ndarray], ks: Sequence[np.ndarray], ws: Sequence[np.ndarray], geoids, states
):
    """ys[i]: (T,) counts; ks[i]: (C, T) exposure per combination; ws[i]: (C,) weights."""
    c_max = max(k.shape[0] for k in ks)
    n = len(ys)
    log_w = np.full((n, c_max), -np.inf)
    big_k = np.zeros((n, c_max))
    head = np.full((n, c_max), -np.inf)
    tot = np.zeros(n)
    for i, (y, k, w) in enumerate(zip(ys, ks, ws, strict=True)):
        y = np.asarray(y, dtype=float)
        k = np.asarray(k, dtype=float)
        lf = float(sum(math.lgamma(v + 1) for v in y))
        tot[i] = y.sum()
        for c in range(k.shape[0]):
            if w[c] <= 0:
                continue
            kc = k[c]
            if np.any((kc <= 0) & (y > 0)):
                h = -np.inf
            else:
                h = float(np.sum(np.where(kc > 0, y * np.log(np.where(kc > 0, kc, 1.0)), 0.0))) - lf
            log_w[i, c] = math.log(w[c])
            big_k[i, c] = kc.sum()
            head[i, c] = h
    return Prepared(tuple(geoids), tuple(states), log_w, big_k, head, tot)


def prepare(places: Sequence[cal.PlaceData], cvals: np.ndarray) -> Prepared:
    """Arrays from the fit's PlaceData at the model's rule shares (`cal._cvals(m_o, m_x)`)."""
    return prepare_arrays(
        [pl.y for pl in places],
        [pl.k(cvals) for pl in places],
        [np.asarray(pl.w, dtype=float) for pl in places],
        [pl.geoid for pl in places],
        [pl.state for pl in places],
    )


def place_loglik(p: Prepared, rate: np.ndarray, alpha: float) -> np.ndarray:
    """log P(y_i) per place at rate_i (θ_s e^{β z_i}), as `calibrate_adu.frailty_loglik_place`, mixed over the
    blank-field combinations as `frailty_loglik`.

    By hand (one place, one year): y = 2, k = 1, rate 1, α = 1 -> log(1/8)."""
    rate = np.asarray(rate, dtype=float)[:, None]
    y = p.Y[:, None]
    mu = rate * p.K
    with np.errstate(divide="ignore", invalid="ignore"):
        if alpha <= 1e-8:
            core = y * np.log(rate) + p.H - mu
        else:
            r = 1.0 / alpha
            core = (
                y * np.log(rate)
                + p.H
                + (_lgamma(y + r) - math.lgamma(r) + r * math.log(r))
                - (y + r) * np.log(r + mu)
            )
        a = np.where(np.isfinite(p.log_w), p.log_w + core, -np.inf)
    top = np.max(a, axis=1)
    safe = np.where(np.isfinite(top), top, 0.0)
    with np.errstate(divide="ignore"):
        out = safe + np.log(np.sum(np.exp(a - safe[:, None]), axis=1))
    return np.where(np.isfinite(top), out, -np.inf)


def _golden(f, lo: float, hi: float, tol: float = TOL) -> tuple[float, float]:
    """(argmax, max) of a unimodal f on [lo, hi]."""
    g = (math.sqrt(5) - 1) / 2
    a, b = lo, hi
    c, d = b - g * (b - a), a + g * (b - a)
    fc, fd = f(c), f(d)
    while b - a > tol:
        if fc >= fd:
            b, d, fd = d, c, fc
            c = b - g * (b - a)
            fc = f(c)
        else:
            a, c, fc = c, d, fd
            d = a + g * (b - a)
            fd = f(d)
    x = (a + b) / 2
    return x, f(x)


@dataclass(frozen=True)
class ScreenFit:
    beta: float
    alpha: float
    theta: dict[str, float]
    loglik: float


def _groups(p: Prepared, within: bool) -> list[np.ndarray]:
    if not within:
        return [np.arange(len(p.Y))]
    st = np.array(p.states)
    return [np.flatnonzero(st == s) for s in sorted(set(p.states))]


def _profile(p: Prepared, z: np.ndarray, beta: float, within: bool) -> ScreenFit:
    """Maximize over θ_s (separable by group given α, β) and α, at fixed β."""
    groups = _groups(p, within)
    scale = np.exp(beta * np.asarray(z, dtype=float))

    def at_alpha(la: float):
        alpha = math.exp(la)
        thetas, total = {}, 0.0
        for idx in groups:
            sub = p.subset(np.isin(np.arange(len(p.Y)), idx))
            sc = scale[idx]

            def f(lt, sub=sub, sc=sc):
                return float(np.sum(place_loglik(sub, math.exp(lt) * sc, alpha)))

            lt, ll = _golden(f, *LOG_THETA)
            thetas["all" if not within else p.states[idx[0]]] = math.exp(lt)
            total += ll
        return total, thetas

    la, _ = _golden(lambda la: at_alpha(la)[0], *LOG_ALPHA)
    ll, thetas = at_alpha(la)
    return ScreenFit(beta, math.exp(la), thetas, ll)


def fit(p: Prepared, z: np.ndarray, within: bool = True, beta: float | None = None) -> ScreenFit:
    """Maximum likelihood over β (unless fixed), α and θ_s."""
    if beta is not None:
        return _profile(p, z, beta, within)
    b, _ = _golden(lambda b: _profile(p, z, b, within).loglik, *BETA, tol=1e-4)
    return _profile(p, z, b, within)


def beta_interval(p: Prepared, z: np.ndarray, best: ScreenFit, within: bool = True) -> tuple[float, float]:
    """90% profile-likelihood interval on β (an edge at the search bound means it is open there)."""

    def gap(b):
        return 2 * (best.loglik - _profile(p, z, b, within).loglik) - CHI2_90

    def edge(far):
        lo, hi = best.beta, far
        if gap(far) < 0:
            return far
        for _ in range(30):
            mid = (lo + hi) / 2
            if gap(mid) < 0:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2

    return edge(BETA[0]), edge(BETA[1])


def lr_p(stat: float) -> float:
    """p of a χ²(1) likelihood-ratio statistic. By hand: 2.7055 -> 0.10; 3.8415 -> 0.05."""
    return math.erfc(math.sqrt(max(stat, 0.0) / 2))


def holm(pvals: Mapping[str, float]) -> dict[str, float]:
    """Holm-adjusted p-values. By hand: (0.01, 0.04, 0.03) -> (0.03, 0.06, 0.06)."""
    order = sorted(pvals, key=pvals.get)
    m, out, run = len(order), {}, 0.0
    for i, key in enumerate(order):
        run = max(run, min(1.0, (m - i) * pvals[key]))
        out[key] = run
    return out


def posterior_mean(p: Prepared, rate: np.ndarray, alpha: float) -> np.ndarray:
    """E[u_i | y_i] = (1 + α Y) / (1 + α rate K̄), with K̄ the weight-averaged exposure over combinations.
    By hand: α 1, Y 2, rate·K 1 -> 1.5."""
    w = np.where(np.isfinite(p.log_w), np.exp(p.log_w), 0.0)
    kbar = np.sum(w * p.K, axis=1) / np.sum(w, axis=1)
    return (1 + alpha * p.Y) / (1 + alpha * np.asarray(rate, dtype=float) * kbar)


def standardize(x: pd.Series) -> pd.Series:
    return (x - x.mean()) / x.std(ddof=0)


def screen_one(p: Prepared, z: np.ndarray, within: bool, loso_min: int = 3) -> dict:
    """One factor, one version: β and its interval, the likelihood-ratio test against β = 0 on the same
    places, the change in α, and β's sign in each leave-one-state-out refit (states with at least `loso_min`
    places)."""
    null = fit(p, z, within, beta=0.0)
    best = fit(p, z, within)
    lo, hi = beta_interval(p, z, best, within)
    stat = 2 * (best.loglik - null.loglik)
    signs = {}
    st = np.array(p.states)
    for s in sorted(set(p.states)):
        if (st == s).sum() < loso_min:
            continue
        keep = st != s
        zk = np.asarray(z)[keep]
        signs[s] = float(np.sign(fit(p.subset(keep), zk, within).beta))
    same = all(v == np.sign(best.beta) for v in signs.values()) if signs else None
    return {
        "places": len(p.Y),
        "beta": best.beta,
        "beta_low": lo,
        "beta_high": hi,
        "lr": stat,
        "p": lr_p(stat),
        "alpha_null": null.alpha,
        "alpha": best.alpha,
        "alpha_drop": 1 - best.alpha / null.alpha if null.alpha > 0 else float("nan"),
        "loso_signs": signs,
        "sign_stable": same,
    }


def verdict(row: Mapping, alpha_drop_min: float = 0.10, p_max: float = 0.10) -> str:
    """D-083's bar on the within-state version: 'candidate' if Holm p < p_max, α falls ≥ alpha_drop_min and
    the sign holds in every leave-one-state-out refit; 'weak' if only the p-value bar is met; else 'no'."""
    if not row["p_holm"] < p_max:
        return "no"
    if row["alpha_drop"] >= alpha_drop_min and row["sign_stable"] is not False:
        return "candidate"
    return "weak"
