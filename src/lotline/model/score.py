"""Held-out log score per place (analysis plan D-049).

A place's score is log P(its observed yearly counts) under a model fitted without its state: the gamma
place effect integrated in closed form (`calibrate_adu.frailty_loglik_place`), blank-field combinations
summed by their weights, and the model's parameter uncertainty integrated (θ by Gauss-Hermite for the
mechanism; coefficient draws for the empirical benchmark). Higher is better; it is a proper scoring rule.
"""

from __future__ import annotations

import math

import numpy as np

from lotline.model import calibrate_adu as cal
from lotline.model import calibrate_shape as shp

GH_THETA = 20  # Gauss-Hermite nodes over log θ (pre-registered)


def _logsumexp(v) -> float:
    v = np.asarray(v, dtype=float)
    m = float(np.max(v))
    return m if not math.isfinite(m) else m + math.log(float(np.exp(v - m).sum()))


def theta_nodes(theta: float, log_se: float, n: int = GH_THETA) -> tuple[np.ndarray, np.ndarray]:
    """(θ_j, log weights) with Σ exp(logw) = 1 so Σ_j w_j f(θ_j) ≈ E f(θ), log θ ~ N(log θ̂, se²).
    se = 0 gives the single node θ̂."""
    if log_se <= 0:
        return np.array([theta]), np.array([0.0])
    x, w = np.polynomial.hermite_e.hermegauss(n)
    return theta * np.exp(log_se * x), np.log(w / w.sum())


def place_log_score(pl: cal.PlaceData, fit, n: int = GH_THETA) -> float:
    """log ∫ Σ_c w_c P_NB(y | θ k_c, α) dN(log θ; log θ̂, se²) for a mechanism fit (`cal.Fit3` or `FitD`).
    `pl` is already shaped for the model (D-047 approach 2, D-048)."""
    ks = pl.k(cal._cvals(fit.m_owner, fit.m_other), getattr(fit, "m_detached", 1.0))
    lw_c = np.log(pl.w / pl.w.sum())
    lf = pl.log_fact
    thetas, lw_t = theta_nodes(fit.theta, fit.log_se, n)
    per_node = [
        _logsumexp(
            [
                lw + cal.frailty_loglik_place(pl.y, k, th, fit.alpha, lf)
                for lw, k in zip(lw_c, ks, strict=True)
            ]
        )
        for th in thetas
    ]
    return _logsumexp(np.asarray(per_node) + lw_t)


def nb_panel_logpdf(y: np.ndarray, mu: np.ndarray, alpha: float, log_fact: float) -> np.ndarray:
    """`frailty_loglik_place` vectorized over rows of mu (draws × years) at θ = 1."""
    big_y = float(y.sum())
    head = (y[None, :] * np.log(np.maximum(mu, 1e-300))).sum(axis=1) - log_fact
    big_m = mu.sum(axis=1)
    if alpha <= 1e-8:
        return head - big_m
    r = 1.0 / alpha
    return head + math.lgamma(big_y + r) - math.lgamma(r) + r * math.log(r) - (big_y + r) * np.log(r + big_m)


def empirical_log_score(pl: cal.PlaceData, fit: shp.EmpFit, draws: int = 4000, seed: int = 49) -> float:
    """log mean over coefficient draws β ~ N(β̂, Σ) of P_NB(y | μ(β), α) for the empirical benchmark."""
    rng = np.random.default_rng(seed)
    k = len(fit.beta)
    betas = rng.multivariate_normal(fit.beta, fit.cov[:k, :k], size=draws, check_valid="ignore")
    x, off = shp.design(pl)
    mu = np.exp(np.clip(off[None, :] + betas @ x.T, None, 30))
    lp = nb_panel_logpdf(pl.y, mu, fit.alpha, pl.log_fact)
    return _logsumexp(lp) - math.log(draws)


def paired(delta) -> tuple[float, float]:
    """(Σ Δ_i, paired SE = sd(Δ_i) × √n). By hand, Δ = (1, 2, 3): sum 6, sd 1, SE √3."""
    d = np.asarray(delta, dtype=float)
    return float(d.sum()), float(d.std(ddof=1) * math.sqrt(len(d)))
