"""ADU effect, pooled hierarchical model (analysis plan D-025; statistical protocol §5.7).

    y_it ~ NegBin(mean μ_it, variance μ + κμ²)
    μ_it = Eligible_it · exp( a + u_i + γ_t + Σ_b β_b · D_it · 1[t − T_i in band b]
                              + Σ_m θ_m · z_im · 1[t ≥ T_i] + ρ · (r_t − r̄) · 1[t ≥ T_i] + δ · MM_it )
    u_i ~ Normal(0, σ²)   (place random effects: partial pooling)

- Event time pooled in three bands: k = 0–1, 2–3, 4+ (`BANDS`).
- Year fixed effects γ_t (first year 0) carry common shocks (rates, costs, COVID, the cycle).
- Modifiers z_im are z-scores over the treated places (θ per standard deviation), measured before adoption.
- Places whose counts are all zero stay in: their random effect is shrunk towards the mean rather than sent to
  −∞ as a fixed effect would be (D-023's failure).
- **Estimation:** maximum marginal likelihood. Each place's integral over u_i is computed by adaptive
  Gauss-Hermite quadrature (`QUAD_NODES` nodes, centred at the mode of the place's integrand found by Newton
  steps); the marginal likelihood is maximized by BFGS with analytic gradients (the posterior-weighted
  complete-data scores, `place_logliks(grad=True)`). A regressor that is zero wherever counts are positive
  (an event-time band with no ADU) cannot be estimated; it is dropped and reported, never silently.
- **Inference:** a wild cluster score bootstrap by place (Webb weights): the analytic per-place scores, one
  Newton step b* = b̂ + H⁻¹ Σ_g w_g S_g per draw, H the Hessian of the marginal log-likelihood (analytic, by
  Louis' identity; `hessian="numerical"` gives the first runs' central differences of the analytic gradient,
  equal to the finite-difference error). Randomization inference re-fits with adoption years permuted among
  treated places.
- **Speed** (D-025 implementation note, 2026-10-22; estimates unchanged): all quadrature nodes are evaluated
  at once with the same arithmetic in the same order (log-likelihoods and scores bit-identical to the first
  runs'), the Hessian is analytic, and the independent refits (randomization inference, leave-one-out) can
  run in parallel processes (`workers`) with the serial result. `WARM_START` (off) starts each refit's BFGS
  from the main fit's curvature: faster on easy refits, but its estimates differ from a cold start's at
  BFGS's stopping tolerance (~1e-4) and on hard synthetic panels more refits failed (41 vs 30 of 360), so it
  is not used. `RefitLog.timing` reports the refit times and BFGS iterations of a stage.
- **Guards:** the fit raises `EstimationError` (shared with `estimate_adu`) if BFGS doesn't converge, if a
  coefficient leaves ±20, if the Hessian is not negative definite, or if an SE is effectively zero.

Only NumPy and pandas.
"""

from __future__ import annotations

import math
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from numpy.polynomial.hermite import hermgauss

from lotline.model.estimate_adu import (
    COEF_BOUND,
    SE_FLOOR,
    WEBB,
    EstimationError,
    modifier_scale,
    permute_adoption,
    ppml,
    relu_separated,
)

BANDS = ((0, 1), (2, 3), (4, 10_000))  # event time k = 0-1, 2-3, 4+
BAND_NAMES = ("beta_0_1", "beta_2_3", "beta_4p")
QUAD_NODES = (
    31  # 15 was too few for places whose posterior is skewed (checked against brute-force integration)
)
_NODES, _WEIGHTS = hermgauss(QUAD_NODES)


# ---------------------------------------------------------------------------------------------------------
# Design
# ---------------------------------------------------------------------------------------------------------


@dataclass
class PooledDesign:
    X: np.ndarray  # fixed-effect regressors: intercept, year dummies, bands, θ, ρ, δ, leads
    names: list[str]
    place_idx: np.ndarray
    places: np.ndarray
    years: np.ndarray
    y: np.ndarray
    offset: np.ndarray
    dropped: list[str] = field(default_factory=list)

    @property
    def log_fact(self) -> np.ndarray:
        return np.array([math.lgamma(v + 1) for v in self.y])


def build_pooled_design(
    panel: pd.DataFrame,
    modifiers: Sequence[str] = (),
    leads: Sequence[int] = (),
    use_rate: bool = True,
    use_mm: bool = True,
    rate_ref: float | None = None,
    binary_dose: bool = False,
    controls: Sequence[str] = (),
) -> PooledDesign:
    """Regressors for the D-025 model from a panel with columns place, year, y, eligible, T, dose, rate, mm
    and the modifiers. Bands scale the dose (or 1[by right] with `binary_dose`). `controls` adds those
    panel columns unscaled as time-varying controls, named control_<column> (D-031 sensitivity run). A
    column with no non-zero entry, or whose non-zero rows all have zero counts (not estimable: the likelihood
    rises without bound as its coefficient falls), is dropped and listed in `dropped`; then separated rows
    (`relu_separated`)."""
    y = panel["y"].to_numpy(dtype=float)
    t = panel["year"].to_numpy()
    T = panel["T"].to_numpy(dtype=float)
    e = t - T
    post = np.nan_to_num((e >= 0).astype(float) * ~np.isnan(e))
    dose = (
        (panel["dose"].to_numpy(dtype=float) > 0).astype(float)
        if binary_dose
        else panel["dose"].to_numpy(float)
    )
    years = np.unique(t)
    cols = [np.ones(len(panel))]
    names = ["intercept"]
    for yr in years[1:]:
        cols.append((t == yr).astype(float))
        names.append(f"year_{int(yr)}")
    for (lo, hi), name in zip(BANDS, BAND_NAMES, strict=True):
        cols.append(dose * ((e >= lo) & (e <= hi)))
        names.append(name)
    for k in leads:
        cols.append((e == k).astype(float))
        names.append(f"lead_{-k}")
    treated = panel.loc[~np.isnan(T)].drop_duplicates("place")
    for m in modifiers:
        c, sd = modifier_scale(treated, m)
        cols.append(np.nan_to_num((panel[m].to_numpy(dtype=float) - c) / sd) * post)
        names.append(f"theta_{m}")
    if use_rate:
        r = panel["rate"].to_numpy(dtype=float)
        ref = float(np.mean(r)) if rate_ref is None else rate_ref
        cols.append((r - ref) * post)
        names.append("rho")
    if use_mm and "mm" in panel:
        cols.append(panel["mm"].to_numpy(dtype=float))
        names.append("delta")
    for c in controls:
        cols.append(panel[c].to_numpy(dtype=float))
        names.append(f"control_{c}")
    X = np.column_stack(cols)
    keep, dropped = [], []
    for j, n in enumerate(names):
        x = X[:, j]
        nz = x != 0
        if not nz.any():
            dropped.append(f"{n} (no non-zero value)")
        elif (
            j > 0
            and not n.startswith("year_")
            and y[nz].sum() == 0
            and (np.all(x[nz] > 0) or np.all(x[nz] < 0))
        ):
            dropped.append(f"{n} (all counts zero where it applies: not estimable)")
        else:
            keep.append(j)
    X = X[:, keep]
    names = [names[j] for j in keep]
    offset = np.log(panel["eligible"].to_numpy(dtype=float))
    place = panel["place"].to_numpy()
    # separation in the fixed part (random place effects don't prevent it): the iterated rectifier of
    # Correia, Guimarães & Zylkin (2019) on the fixed design; separated observations are dropped and listed
    sep = relu_separated(X, y)
    separated = [(place[i], int(t[i])) for i in np.where(sep)[0]]
    if sep.any():
        X, y, offset, place, t = X[~sep], y[~sep], offset[~sep], place[~sep], t[~sep]
        live = np.abs(X).sum(axis=0) > 0
        dropped += [
            f"{n} (no variation after dropping separated rows)"
            for n, v in zip(names, live, strict=True)
            if not v
        ]
        X, names = X[:, live], [n for n, v in zip(names, live, strict=True) if v]
    # dropping rows can leave columns collinear (e.g. a whole year separated: the intercept equals the sum of
    # the remaining year dummies); keep a linearly independent set, intercept first, and report the rest
    if np.linalg.matrix_rank(X) < X.shape[1]:
        kept, base, rank = [], np.zeros((X.shape[0], 0)), 0
        for j in range(X.shape[1]):
            trial = np.hstack([base, X[:, [j]]])
            r_ = np.linalg.matrix_rank(trial)
            if r_ > rank:
                kept.append(j)
                base, rank = trial, r_
        dropped += [
            f"{n} (collinear after dropping separated rows)" for j, n in enumerate(names) if j not in kept
        ]
        X, names = X[:, kept], [names[j] for j in kept]
    places, p_idx = np.unique(place, return_inverse=True)
    out = PooledDesign(X, names, p_idx, places, np.unique(t), y, offset, dropped)
    out.separated = separated
    out.row_year = t
    return out


# ---------------------------------------------------------------------------------------------------------
# Marginal likelihood (adaptive Gauss-Hermite quadrature over the place effects)
# ---------------------------------------------------------------------------------------------------------


def _lgamma(x):
    return np.vectorize(math.lgamma, otypes=[float])(np.asarray(x, dtype=float))


def _nb_tables(y: np.ndarray, r: float, second: bool = False):
    """For integer counts y: log Γ(y + r) − log Γ(r) = Σ_{j<y} log(r + j), and its r-derivative
    ψ(y + r) − ψ(r) = Σ_{j<y} 1/(r + j), by cumulative sums (exact, no special functions). With `second`,
    also Σ_{j<y} 1/(r + j)² (minus the second r-derivative, for the analytic Hessian)."""
    yi = y.astype(int)
    top = int(yi.max()) if len(yi) else 0
    j = np.arange(top)
    lg = np.r_[0.0, np.cumsum(np.log(r + j))]
    dg = np.r_[0.0, np.cumsum(1.0 / (r + j))]
    if not second:
        return lg[yi], dg[yi]
    tg = np.r_[0.0, np.cumsum(1.0 / (r + j) ** 2)]
    return lg[yi], dg[yi], tg[yi]


def _cached(d: PooledDesign) -> dict:
    """Per-design constants reused by every likelihood evaluation: log y!, and the place index of each
    (node, row) pair flattened so one `bincount` sums all quadrature nodes at once (in the same row order as
    one `bincount` per node, so the sums are bit-identical)."""
    c = d.__dict__.get("_cache")
    if c is None or c["n"] != len(d.y) or c["G"] != len(d.places):
        G = len(d.places)
        c = {
            "n": len(d.y),
            "G": G,
            "log_fact": d.log_fact,
            "flat": (np.arange(QUAD_NODES)[:, None] * G + d.place_idx[None, :]).ravel(),
        }
        d._cache = c
    return c


_NODE_CONST = np.array([math.log(w) + x**2 for x, w in zip(_NODES, _WEIGHTS, strict=True)])


def place_logliks(
    params: np.ndarray, d: PooledDesign, newton_steps: int = 30, grad: bool = False, hess: bool = False
):
    """Marginal log-likelihood of each place: log ∫ Π_t NB(y_it; μ_it e^u) φ(u; 0, σ²) du, by adaptive
    Gauss-Hermite quadrature (the integrand's mode û_i by Newton steps, its curvature, `QUAD_NODES` nodes).

    params = (fixed coefficients…, log σ, log κ). With `grad`, also returns the places' scores (places ×
    parameters): the posterior-weighted (quadrature) sums of Σ_t X_it (y − μ) r/(r + μ) for the coefficients,
    u²/σ² − 1 for log σ, and −r [Σ_{j<y} 1/(r + j) + log(r/(r + μ)) + (μ − y)/(r + μ)] for log κ (r = 1/κ).
    With `hess` (implies `grad`), also the Hessian of the summed marginal log-likelihood by Louis' identity:
    Σ_i { E_i[∂²ℓ] + E_i[s sᵀ] − S_i S_iᵀ }, E_i the same posterior (quadrature) weights, ℓ the
    complete-data log density of place i at a node, s its derivative and S_i the place's score
    (`_complete_data_hessian`).
    All nodes are evaluated at once; the arithmetic, and its order, is that of one node at a time.
    """
    k = d.X.shape[1]
    b, log_s, log_k = params[:k], params[k], params[k + 1]
    sigma, kappa = math.exp(log_s), math.exp(log_k)
    r = 1.0 / kappa
    eta = d.offset + d.X @ b
    G = len(d.places)
    idx = d.place_idx
    y = d.y
    c = _cached(d)
    tables = _nb_tables(y, r, second=hess)
    lg, dg = tables[0], tables[1]
    const = lg - c["log_fact"]

    def mode_derivs(u):  # first and second u-derivatives of each place's log integrand
        mu = np.exp(np.clip(eta + u[idx], -700, 50))
        g = (y - mu) * r / (r + mu)
        h2 = -mu * r * (r + y) / (r + mu) ** 2
        dH = np.bincount(idx, g, G) - u / sigma**2
        d2H = np.bincount(idx, h2, G) - 1 / sigma**2
        return dH, d2H

    u = np.zeros(G)
    for _ in range(newton_steps):
        dH, d2H = mode_derivs(u)
        step = dH / d2H
        u = u - np.clip(step, -5, 5)
        if np.max(np.abs(step)) < 1e-10:
            break
    d2H = mode_derivs(u)[1]
    s = 1 / np.sqrt(-d2H)
    # all nodes at once: rows of UQ / MU are nodes
    UQ = u[None, :] + math.sqrt(2) * s[None, :] * _NODES[:, None]
    MU = np.exp(np.clip(eta[None, :] + UQ[:, idx], -700, 50))
    log_share = np.log(r / (r + MU))
    LL = const + r * log_share + y * np.log(np.where(MU > 0, MU, 1e-300) / (r + MU))
    flat, QG = c["flat"], QUAD_NODES * G
    HQ = np.bincount(flat, LL.ravel(), QG).reshape(QUAD_NODES, G)
    HQ = HQ - 0.5 * (UQ / sigma) ** 2 - 0.5 * math.log(2 * math.pi) - log_s
    vals = _NODE_CONST[:, None] + HQ
    total = np.logaddexp.reduce(vals, axis=0)
    ll = np.log(math.sqrt(2)) + np.log(s) + total
    if not (grad or hess):
        return ll
    omega = np.exp(vals - total[None, :])  # posterior weights of the nodes, per place
    GQ = (y - MU) * r / (r + MU)
    # per node, per place: Σ_t X_it g_it (one bincount per column over all nodes)
    A = np.empty((QUAD_NODES, G, k))
    for j in range(k):
        A[:, :, j] = np.bincount(flat, (d.X[:, j][None, :] * GQ).ravel(), QG).reshape(QUAD_NODES, G)
    DK = -r * (dg + log_share + (MU - y) / (r + MU))
    BK = np.bincount(flat, DK.ravel(), QG).reshape(QUAD_NODES, G)
    S = np.zeros((G, k + 2))
    for q in range(QUAD_NODES):
        wq = omega[q]
        S[:, :k] += wq[:, None] * A[q]
        S[:, k] += wq * (UQ[q] ** 2 / sigma**2 - 1)
        S[:, k + 1] += wq * BK[q]
    if not hess:
        return ll, S
    H = _complete_data_hessian(d, r, sigma, omega, UQ, MU, tables[2], A, BK) - S.T @ S
    return ll, S, H


def _complete_data_hessian(d, r, sigma, omega, UQ, MU, tg, A, BK) -> np.ndarray:
    """Σ_i Σ_q ω_iq (∂²ℓ_iq + s_iq s_iqᵀ) over places i and nodes q (the first two terms of Louis' identity),
    for (b, log σ, log κ). Per row, with g = (y − μ) r/(r + μ) and A_r = ∂ℓ/∂r:
      ∂²ℓ/∂η²       = −μ r (r + y)/(r + μ)²
      ∂²ℓ/∂η ∂log κ = −r (y − μ) μ/(r + μ)²
      ∂²ℓ/∂(log κ)² = r A_r + r² ∂A_r/∂r,   A_r = Σ_{j<y} 1/(r + j) + log(r/(r + μ)) + (μ − y)/(r + μ),
                      ∂A_r/∂r = −Σ_{j<y} 1/(r + j)² + 1/r − 1/(r + μ) − (μ − y)/(r + μ)²
    and for the place effect's prior, ∂²/∂(log σ)² = −2u²/σ² (no cross terms)."""
    k = d.X.shape[1]
    y, idx, X = d.y, d.place_idx, d.X
    W = omega[:, idx]  # node weights per row
    rm = r + MU
    h_eta = -MU * r * (r + y) / rm**2
    h_cross = -r * (y - MU) * MU / rm**2
    dg = _nb_tables(y, r)[1]
    a_r = dg + np.log(r / rm) + (MU - y) / rm
    da_r = -tg + 1 / r - 1 / rm - (MU - y) / rm**2
    h_kk = r * a_r + r**2 * da_r
    H = np.zeros((k + 2, k + 2))
    H[:k, :k] = (X * (W * h_eta).sum(axis=0)[:, None]).T @ X
    H[:k, k + 1] = H[k + 1, :k] = X.T @ (W * h_cross).sum(axis=0)
    H[k + 1, k + 1] = float((W * h_kk).sum())
    H[k, k] = float((omega * (-2 * UQ**2 / sigma**2)).sum())
    # E[s sᵀ]: per node, the place scores s_q (G × (k + 2)) weighted by ω_q
    for q in range(QUAD_NODES):
        sq = np.column_stack([A[q], UQ[q] ** 2 / sigma**2 - 1, BK[q]])
        H += (sq * omega[q][:, None]).T @ sq
    return H


def _sum_by(idx: np.ndarray, M: np.ndarray, G: int) -> np.ndarray:
    """Row sums of M within groups idx (G groups): one `bincount` per column (much faster than np.add.at)."""
    return (
        np.column_stack([np.bincount(idx, M[:, j], G) for j in range(M.shape[1])])
        if M.shape[1]
        else np.zeros((G, 0))
    )


def place_effects(params: np.ndarray, d: PooledDesign) -> np.ndarray:
    """Posterior mode of each place's random effect u_i (empirical Bayes)."""
    k = d.X.shape[1]
    b, sigma, kappa = params[:k], math.exp(params[k]), math.exp(params[k + 1])
    r = 1 / kappa
    eta = d.offset + d.X @ b
    u = np.zeros(len(d.places))
    for _ in range(50):
        mu = np.exp(np.clip(eta + u[d.place_idx], -700, 50))
        dH = np.bincount(d.place_idx, (d.y - mu) * r / (r + mu), len(u)) - u / sigma**2
        d2H = np.bincount(d.place_idx, -mu * r * (r + d.y) / (r + mu) ** 2, len(u)) - 1 / sigma**2
        step = dH / d2H
        u -= np.clip(step, -5, 5)
        if np.max(np.abs(step)) < 1e-10:
            break
    return u


# ---------------------------------------------------------------------------------------------------------
# Optimization
# ---------------------------------------------------------------------------------------------------------


def _grad(f: Callable, x: np.ndarray, h: float = 1e-5) -> np.ndarray:
    g = np.zeros_like(x)
    for j in range(len(x)):
        e = np.zeros_like(x)
        e[j] = h
        g[j] = (f(x + e) - f(x - e)) / (2 * h)
    return g


def _jacobian(f: Callable, x: np.ndarray, h: float = 1e-5) -> np.ndarray:
    """(outputs × inputs) central-difference Jacobian of a vector function."""
    cols = []
    for j in range(len(x)):
        e = np.zeros_like(x)
        e[j] = h
        cols.append((f(x + e) - f(x - e)) / (2 * h))
    return np.column_stack(cols)


def bfgs_max(
    f: Callable,
    x0: np.ndarray,
    tol: float = 1e-6,
    max_iter: int = 500,
    grad: Callable | None = None,
    hinv0: np.ndarray | None = None,
    info: dict | None = None,
) -> tuple[np.ndarray, float, bool]:
    """Maximize f by BFGS (minimizing −f) with an Armijo backtracking line search and central-difference
    gradients (or `grad`). Converged when the largest gradient component is below `tol` × (1 + |f|).

    `hinv0` warm-starts the inverse-Hessian approximation (of −f; positive definite), e.g. a refit starting
    from the main model's curvature; default the scaled identity. A non-descent direction still resets to the
    scaled identity. `info`, if given, receives the iteration and evaluation counts."""

    counts = {"iterations": 0, "f_evals": 0, "g_evals": 0}
    if info is not None:
        info.update(counts)
        counts = info

    def F(x):
        counts["f_evals"] += 1
        v = f(x)
        return np.inf if not np.isfinite(v) else -v

    def dF(x):
        counts["g_evals"] += 1
        return -grad(x) if grad is not None else _grad(F, x)

    x = np.asarray(x0, dtype=float).copy()
    Fx = F(x)
    G = dF(x)
    Hinv = np.eye(len(x)) / max(1.0, np.max(np.abs(G))) if hinv0 is None else np.array(hinv0, dtype=float)
    for it in range(max_iter):
        counts["iterations"] = it
        if np.max(np.abs(G)) < tol * (1 + abs(Fx)):
            return x, -Fx, True
        p = -Hinv @ G
        if p @ G >= 0:  # not a descent direction: reset
            Hinv = np.eye(len(x)) / max(1.0, np.max(np.abs(G)))
            p = -Hinv @ G
        step, ok = 1.0, False
        for _ in range(60):
            xn = x + step * p
            Fn = F(xn)
            if Fn <= Fx + 1e-4 * step * (p @ G):
                ok = True
                break
            step *= 0.5
        if not ok:
            return x, -Fx, bool(np.max(np.abs(G)) < 1e3 * tol * (1 + abs(Fx)))
        Gn = dF(xn)
        s_, y_ = xn - x, Gn - G
        sy = s_ @ y_
        if sy > 1e-12:
            rho_ = 1.0 / sy
            eye = np.eye(len(x))
            Hinv = (eye - rho_ * np.outer(s_, y_)) @ Hinv @ (eye - rho_ * np.outer(y_, s_)) + rho_ * np.outer(
                s_, s_
            )
        x, Fx, G = xn, Fn, Gn
    counts["iterations"] = max_iter
    return x, -Fx, bool(np.max(np.abs(G)) < tol * (1 + abs(Fx)))


SIGMA_BOUND, KAPPA_BOUND = 6.0, 8.0  # |log σ| and |log κ| are kept inside these by a tanh map


def to_log(z: np.ndarray, k: int) -> np.ndarray:
    """Internal parameters -> (coefficients, log σ, log κ): log σ = 6 tanh(z/6), log κ = 8 tanh(z/8), so the
    variance parameters approach their limits (e.g. κ -> 0, the Poisson case) smoothly."""
    out = np.asarray(z, dtype=float).copy()
    out[k] = SIGMA_BOUND * math.tanh(out[k] / SIGMA_BOUND)
    out[k + 1] = KAPPA_BOUND * math.tanh(out[k + 1] / KAPPA_BOUND)
    return out


def from_log(p: np.ndarray, k: int) -> np.ndarray:
    out = np.asarray(p, dtype=float).copy()
    out[k] = SIGMA_BOUND * math.atanh(np.clip(out[k] / SIGMA_BOUND, -0.999, 0.999))
    out[k + 1] = KAPPA_BOUND * math.atanh(np.clip(out[k + 1] / KAPPA_BOUND, -0.999, 0.999))
    return out


@dataclass
class PooledFit:
    design: PooledDesign
    params: np.ndarray
    loglik: float
    converged: bool
    hessian: np.ndarray
    scores: np.ndarray  # places × parameters (internal scale)

    @property
    def names(self) -> list[str]:
        return [*self.design.names, "log_sigma", "log_kappa"]

    @property
    def log_params(self) -> np.ndarray:
        """Coefficients, log σ and log κ (the internal parameters mapped back)."""
        return to_log(self.params, self.design.X.shape[1])

    def value(self, name: str) -> float:
        return float(self.log_params[self.names.index(name)])

    @property
    def cov(self) -> np.ndarray:
        """Cluster-robust (sandwich) covariance by place."""
        Hi = np.linalg.inv(self.hessian)
        return Hi @ (self.scores.T @ self.scores) @ Hi


HESSIAN = "analytic"  # or "numerical": central differences of the analytic gradient (the first runs' method)


def warm_hinv(main: PooledFit, d: PooledDesign) -> np.ndarray:
    """Inverse-Hessian start for BFGS on design `d` from the main fit's curvature (internal scale), matched
    by name: −H⁻¹ of the main model for the shared parameters, the identity for a column the main model
    doesn't have, and for a variance parameter held at its bound."""
    names = [*d.names, "log_sigma", "log_kappa"]
    pos = {n: j for j, n in enumerate(main.names)}
    held = set(getattr(main, "at_bound", []))
    shared = [j for j, n in enumerate(names) if n in pos and n not in held]
    src = [pos[names[j]] for j in shared]
    free = [j for j, n in enumerate(main.names) if n not in held]
    Hm = -main.hessian[np.ix_(free, free)]
    Ci = np.linalg.inv(Hm)
    at = {j: i for i, j in enumerate(free)}
    out = np.eye(len(names))
    sel = [at[j] for j in src]
    out[np.ix_(shared, shared)] = Ci[np.ix_(sel, sel)]
    return out


def fit_pooled(
    d: PooledDesign,
    start: np.ndarray | None = None,
    check: bool = True,
    max_iter: int = 500,
    hessian: str | None = None,
    hinv0: np.ndarray | None = None,
) -> PooledFit:
    """Maximum marginal likelihood of the D-025 model; raises EstimationError if unusable (with the BFGS
    `iterations` and `seconds` attached to the error). `hessian`: "analytic" (Louis' identity,
    `place_logliks(hess=True)`; the default, `HESSIAN`) or "numerical" (central differences of the analytic
    gradient); they agree to the finite-difference error (tests). `hinv0`: BFGS warm start (`warm_hinv`); it
    changes the path, not the maximum (to BFGS's convergence tolerance; tests)."""
    t0 = time.perf_counter()
    hessian = hessian or HESSIAN
    if hessian not in ("analytic", "numerical"):
        raise ValueError(f"hessian must be 'analytic' or 'numerical', not {hessian!r}")
    k = d.X.shape[1]
    if start is None:
        start = np.zeros(k + 2)
        pos = d.y.sum() / np.exp(d.offset).sum()
        start[0] = math.log(max(pos, 1e-9))
        start[k], start[k + 1] = math.log(1.0), math.log(0.5)
    z0 = from_log(start, k)

    def f(z):
        if np.max(np.abs(z[:k])) > 60:
            return -np.inf
        return float(place_logliks(to_log(z, k), d).sum())

    def chain(z):  # d(log σ)/dz and d(log κ)/dz through the tanh map, and their z-derivatives
        cs, ck = 1 / math.cosh(z[k] / SIGMA_BOUND) ** 2, 1 / math.cosh(z[k + 1] / KAPPA_BOUND) ** 2
        return (
            cs,
            ck,
            -2 / SIGMA_BOUND * cs * math.tanh(z[k] / SIGMA_BOUND),
            (-2 / KAPPA_BOUND * ck * math.tanh(z[k + 1] / KAPPA_BOUND)),
        )

    def scores(z):
        _, S = place_logliks(to_log(z, k), d, grad=True)
        cs, ck, _, _ = chain(z)
        S[:, k] *= cs  # chain rule through the tanh map
        S[:, k + 1] *= ck
        return S

    def g(z):
        return scores(z).sum(axis=0)

    info: dict = {}
    x, fx, ok = bfgs_max(f, z0, grad=g, max_iter=max_iter, hinv0=hinv0, info=info)
    t1 = time.perf_counter()
    # a variance parameter at its limit (no place heterogeneity, or Poisson counts) is held there: its
    # curvature is ~0, so it is left out of the Hessian and scores (reported as at its bound)
    logs = to_log(x, k)
    at_bound = [j for j, lim in ((k, SIGMA_BOUND), (k + 1, KAPPA_BOUND)) if abs(logs[j]) > 0.95 * lim]
    free = [j for j in range(k + 2) if j not in at_bound]
    if hessian == "numerical":
        H = _jacobian(g, x, 1e-5)
        H = (H + H.T) / 2
        S = scores(x)
    else:  # the log-scale Hessian mapped to the internal scale: J H Jᵀ + diag(gradient × second derivative)
        _, S, H = place_logliks(logs, d, hess=True)
        cs, ck, ds, dk = chain(x)
        J = np.r_[np.ones(k), cs, ck]
        gl = S.sum(axis=0)
        H = H * np.outer(J, J)
        H[k, k] += gl[k] * ds
        H[k + 1, k + 1] += gl[k + 1] * dk
        S[:, k] *= cs
        S[:, k + 1] *= ck
    H_free = H[np.ix_(free, free)]
    H = np.full_like(H, 0.0)
    H[np.ix_(free, free)] = H_free
    for j in at_bound:
        H[j, j] = -1.0  # placeholder curvature; its score column is zeroed so it never moves in the bootstrap
        S[:, j] = 0.0
    fit = PooledFit(d, x, fx, ok, H, S)
    fit.at_bound = [("log_sigma" if j == k else "log_kappa") for j in at_bound]
    fit.iterations = info["iterations"]
    fit.evals = (info["f_evals"], info["g_evals"])
    fit.seconds = {"bfgs": t1 - t0, "hessian": time.perf_counter() - t1}
    if check:
        try:
            check_pooled(fit)
        except EstimationError as err:
            err.iterations, err.seconds = fit.iterations, time.perf_counter() - t0
            raise
    return fit


def check_pooled(fit: PooledFit) -> None:
    if not fit.converged:
        raise EstimationError("pooled model: BFGS did not converge")
    if not np.all(np.isfinite(fit.params)) or not np.isfinite(fit.loglik):
        raise EstimationError("pooled model: non-finite estimate")
    k = fit.design.X.shape[1]
    big = [
        (n, v)
        for n, v in zip(fit.design.names, fit.params[:k], strict=True)
        if abs(v) > COEF_BOUND and n != "intercept"
    ]
    if big:
        raise EstimationError(f"pooled model: coefficients beyond ±{COEF_BOUND}: {big}")
    free = [j for j, n in enumerate(fit.names) if n not in getattr(fit, "at_bound", [])]
    if np.max(np.linalg.eigvalsh(fit.hessian[np.ix_(free, free)])) >= 0:
        raise EstimationError(
            "pooled model: Hessian not negative definite (not a maximum, or not identified)"
        )
    se = np.sqrt(np.clip(np.diag(fit.cov), 0, None))
    bound = getattr(fit, "at_bound", [])
    tiny = [
        (n, s)
        for n, s, v in zip(fit.names, se, fit.params, strict=True)
        if n not in bound and s < SE_FLOOR * max(1, abs(v))
    ]
    if tiny:
        raise EstimationError(f"pooled model: standard errors effectively zero: {tiny}")


def estimate_pooled(
    panel: pd.DataFrame, check: bool = True, max_iter: int = 500, hessian: str | None = None, **design_kw
) -> PooledFit:
    return fit_pooled(
        build_pooled_design(panel, **design_kw), check=check, max_iter=max_iter, hessian=hessian
    )


# ---------------------------------------------------------------------------------------------------------
# Inference and summaries
# ---------------------------------------------------------------------------------------------------------


@dataclass
class RefitLog:
    """Convergence accounting for one stage (D-025 rule): refits tried, converged at first, converged on the
    retry from the main estimates, and failed (excluded); bootstrap draws tried and excluded."""

    stage: str
    refits: int = 0
    first: int = 0
    retried: int = 0
    failed: int = 0
    draws: int = 0
    draws_excluded: int = 0
    max_share: float = 0.05
    seconds: list = field(default_factory=list)  # per refit (both attempts), wall-clock
    iterations: list = field(default_factory=list)  # per refit, BFGS iterations summed over attempts
    boot_seconds: float = 0.0

    @property
    def timing(self) -> str:
        """Where the stage's time went: refits' median and slowest, the share taken by the slowest 5%."""
        if not self.seconds:
            return f"{self.stage}: no refits timed"
        t = np.sort(np.asarray(self.seconds))[::-1]
        top = t[: max(1, math.ceil(0.05 * len(t)))]
        it = np.asarray(self.iterations)
        return (
            f"{self.stage}: {len(t)} refits in {t.sum():.1f} s "
            f"(median {np.median(t):.2f} s, max {t[0]:.2f} s; "
            f"slowest 5% {top.sum() / t.sum():.0%} of the time); BFGS iterations median {np.median(it):.0f}, "
            f"max {it.max():.0f}" + (f"; bootstrap {self.boot_seconds:.2f} s" if self.boot_seconds else "")
        )

    @property
    def summary(self) -> str:
        parts = []
        if self.refits:
            ok = self.first + self.retried
            parts.append(
                f"{ok} of {self.refits} refits converged ({self.retried} on retry, {self.failed} excluded)"
            )
        if self.draws:
            parts.append(f"{self.draws - self.draws_excluded} of {self.draws} bootstrap draws kept")
        return f"{self.stage}: " + "; ".join(parts) if parts else f"{self.stage}: nothing refitted"

    def check(self) -> None:
        """Stop the stage (StageFailed) if failures exceed `max_share` of its refits or draws."""
        if self.refits and self.failed > self.max_share * self.refits:
            raise StageFailed(f"{self.summary}: more than {self.max_share:.0%} of refits failed")
        if self.draws and self.draws_excluded > self.max_share * self.draws:
            raise StageFailed(f"{self.summary}: more than {self.max_share:.0%} of bootstrap draws diverged")


class StageFailed(EstimationError):
    """A stage of the run could not be computed under the D-025 convergence rule."""


def start_from(main: PooledFit, d: PooledDesign) -> np.ndarray:
    """Starting values for a refit's design from the main model's estimates, matched by name (0 for a column
    the main model doesn't have), with its log σ and log κ."""
    mk = main.design.X.shape[1]
    lp = main.log_params
    by_name = dict(zip(main.design.names, lp[:mk], strict=True))
    return np.r_[[by_name.get(n, 0.0) for n in d.names], lp[mk], lp[mk + 1]]


WARM_START = (
    False  # True: refits start BFGS from the main model's inverse Hessian (`warm_hinv`); see the D-025 note
)


def _default_fitter(panel, start: PooledFit | None = None, warm: PooledFit | None = None, **kw) -> PooledFit:
    """Build the design and fit it. `start`: start from that fit's estimates (the D-025 retry). `warm`: the
    main fit whose curvature warm-starts BFGS (`WARM_START`); the starting point is unchanged."""
    d = build_pooled_design(panel, **kw)
    ref = start if start is not None else warm
    hinv0 = warm_hinv(ref, d) if WARM_START and ref is not None else None
    return fit_pooled(d, start=start_from(start, d) if start is not None else None, hinv0=hinv0)


def refit(
    panel, main: PooledFit | None, log: RefitLog, fitter: Callable | None = None, **kw
) -> PooledFit | None:
    """One refit under the D-025 rule: try; if it doesn't converge, retry once starting from the main-model
    estimates; if it still fails, count it as excluded and return None. The refit's time and BFGS iterations
    (both attempts) are added to `log`. With the default fitter the main fit also warm-starts BFGS."""
    extra = {"warm": main} if fitter is None and main is not None else {}
    fitter = fitter or _default_fitter
    log.refits += 1
    t0, iters = time.perf_counter(), 0
    try:
        try:
            fit = fitter(panel, **extra, **kw)
            log.first += 1
            iters += getattr(fit, "iterations", 0)
            return fit
        except EstimationError as err:
            iters += getattr(err, "iterations", 0)
        try:
            fit = fitter(panel, start=main, **kw)
            log.retried += 1
            iters += getattr(fit, "iterations", 0)
            return fit
        except EstimationError as err:
            iters += getattr(err, "iterations", 0)
            log.failed += 1
            return None
    finally:
        log.seconds.append(time.perf_counter() - t0)
        log.iterations.append(iters)


# Independent refits across processes (randomization inference, leave-one-out). Every job is fixed before
# any runs (the permutations are drawn up front, in the serial order) and results are read back in job order,
# so the output, including where the 5% rule stops a stage, is that of the serial loop.

_SHARED: dict = {}


def _init_worker(panel, main, fitter, kw, settings=None) -> None:
    """Worker set-up: the shared inputs, and the parent's `WARM_START` and `HESSIAN` (a spawned process
    imports the module afresh)."""
    global WARM_START, HESSIAN
    _SHARED.update(panel=panel, main=main, fitter=fitter, kw=kw)
    if settings is not None:
        WARM_START, HESSIAN = settings


def _refit_job(job, shared: dict | None = None):
    """One refit of a modified panel: ("permute", {place: T}) or ("drop", place). Returns (overall effect or
    None, the job's RefitLog)."""
    sh = shared if shared is not None else _SHARED
    panel = sh["panel"]
    kind, arg = job
    p = permute_adoption(panel, arg) if kind == "permute" else panel[panel["place"] != arg]
    log = RefitLog(kind)
    f = refit(p, sh["main"], log, sh["fitter"], **sh["kw"])
    return (None if f is None else overall_effect(f)), log


def _absorb(log: RefitLog, part: RefitLog) -> None:
    log.refits += part.refits
    log.first += part.first
    log.retried += part.retried
    log.failed += part.failed
    log.seconds += part.seconds
    log.iterations += part.iterations


def _run_refits(panel, main, jobs, fitter, kw, workers: int = 1):
    """Yield (effect, job log) for each job, in job order; `workers` > 1 uses that many processes (the
    fitter must then be picklable: the default, or a module-level callable). Stopping early cancels the
    jobs not yet started."""
    if workers <= 1:
        shared = {"panel": panel, "main": main, "fitter": fitter, "kw": kw}
        for job in jobs:
            yield _refit_job(job, shared)
        return
    from concurrent.futures import ProcessPoolExecutor

    ex = ProcessPoolExecutor(
        max_workers=workers,
        initializer=_init_worker,
        initargs=(panel, main, fitter, kw, (WARM_START, HESSIAN)),
    )
    try:
        yield from ex.map(_refit_job, jobs)
    finally:
        ex.shutdown(wait=True, cancel_futures=True)


def score_bootstrap(
    fit: PooledFit, draws: int = 999, seed: int = 0, log: RefitLog | None = None
) -> pd.DataFrame:
    """Wild cluster score bootstrap by place (Webb weights): b* = b̂ − H⁻¹ Σ_g w_g S_g (H negative
    definite). A draw beyond the coefficient bound is excluded and counted in `log` (D-025 rule); without a
    log, any such draw raises."""
    t0 = time.perf_counter()
    rng = np.random.default_rng(seed)
    Hi = np.linalg.inv(fit.hessian)
    k = fit.design.X.shape[1]
    rows = []
    for _ in range(draws):
        w = rng.choice(WEBB, size=fit.scores.shape[0])
        b = fit.params - Hi @ (w @ fit.scores)
        bad = not np.all(np.isfinite(b)) or np.max(np.abs(b[:k][1:]), initial=0) > COEF_BOUND
        if log is not None:
            log.draws += 1
            if bad:
                log.draws_excluded += 1
                continue
        elif bad:
            raise EstimationError("pooled bootstrap draw diverged")
        rows.append(dict(zip(fit.names, to_log(b, k), strict=True)))
    if log is not None:
        log.boot_seconds += time.perf_counter() - t0
        log.check()
    return pd.DataFrame(rows)


def summarize(fit: PooledFit, boot: pd.DataFrame, level: float = 0.90, wide: float = 1.0) -> pd.DataFrame:
    """Estimates with sandwich SEs and basic-bootstrap intervals; `weakly_identified` flags an interval wider
    than `wide` on the log scale (a factor of e ≈ 2.7 between its ends)."""
    a = (1 - level) / 2
    k = fit.design.X.shape[1]
    se = np.sqrt(np.clip(np.diag(fit.cov), 0, None))
    z = fit.params
    se[k] *= 1 / math.cosh(z[k] / SIGMA_BOUND) ** 2  # delta method: d(log σ)/dz
    se[k + 1] *= 1 / math.cosh(z[k + 1] / KAPPA_BOUND) ** 2
    vals = fit.log_params
    rows = []
    for j, n in enumerate(fit.names):
        v = vals[j]
        dev = boot[n].to_numpy() - v
        lo, hi = np.quantile(dev, [a, 1 - a])
        rows.append(
            {
                "term": n,
                "estimate": v,
                "se": se[j],
                "low": v - hi,
                "high": v - lo,
                "p_two_sided": float(np.mean(np.abs(dev) >= abs(v))),
                "weakly_identified": bool((hi - lo) > wide)
                if n.startswith(("theta_", "beta_", "rho", "delta"))
                else False,
            }
        )
    return pd.DataFrame(rows)


def overall_effect(fit: PooledFit, params: np.ndarray | None = None) -> float:
    """Pooled effect over the bands, weighted by the treated place-years in each band (log scale)."""
    p = fit.params if params is None else params
    d = fit.design
    w, b = [], []
    for name in BAND_NAMES:
        if name in d.names:
            j = d.names.index(name)
            w.append(float((d.X[:, j] != 0).sum()))
            b.append(p[j])
    return float(np.average(b, weights=w)) if w else float("nan")


def randomization_inference(
    panel, permutations: int, main: PooledFit, seed: int = 0, fitter=None, workers: int = 1, **design_kw
):
    """Permute adoption years among treated places, each place's dose path moving with its T (D-031 (a)),
    re-fit (D-025 convergence rule), compare the overall
    pooled effect of `main` with the permutation distribution. Returns (observed, p over the converged
    refits, distribution, log). `workers` > 1 refits in parallel processes with the same result (the
    permutations are drawn up front in the serial order; `log.timing` has the refit times)."""
    rng = np.random.default_rng(seed)
    log = RefitLog("randomization inference")
    obs = overall_effect(main)
    treated = panel.loc[panel["T"].notna(), ["place", "T"]].drop_duplicates("place")
    jobs = [
        ("permute", dict(zip(treated["place"], rng.permutation(treated["T"].to_numpy()), strict=True)))
        for _ in range(permutations)
    ]  # D-031 (a): each dose path moves with its adoption year (`permute_adoption`)
    out = []
    for e, part in _run_refits(panel, main, jobs, fitter, design_kw, workers):
        _absorb(log, part)
        if e is not None:
            out.append(e)
        if log.failed > log.max_share * permutations:  # the 5% limit is already broken: stop now
            break
    log.check()
    dist = np.array(out)
    return obs, float(np.mean(np.abs(dist) >= abs(obs))), dist, log


# ---------------------------------------------------------------------------------------------------------
# Checks (D-023 §checks, applied to the D-025 model, under the D-025 convergence rule)
# ---------------------------------------------------------------------------------------------------------


def _not_computed(name: str, log: RefitLog, why: str = "did not converge after a retry") -> dict:
    return {
        "check": name,
        "pass": None,
        "note": f"not computed: {why}",
        "convergence": log.summary,
        "timing": log.timing,
    }


def _effect_interval(panel, draws, seed, main, log, fitter=None, **kw):
    fit = refit(panel, main, log, fitter, **kw)
    if fit is None:
        return None
    boot = score_bootstrap(fit, draws=draws, seed=seed, log=log)
    k = fit.design.X.shape[1]
    dist = np.array([overall_effect(fit, from_log(r.to_numpy(), k)) for _, r in boot[fit.names].iterrows()])
    est_ = overall_effect(fit)
    lo, hi = np.quantile(dist - est_, [0.05, 0.95])
    return fit, boot, est_, est_ - hi, est_ - lo


def check_leads(panel, main: PooledFit, draws=999, seed=0, fitter=None, **kw) -> dict:
    """Pre-trend leads k = −3…−1 jointly zero at the 10% level (Wald with the bootstrap covariance)."""
    name, log = "pre-trend leads", RefitLog("pre-trend leads")
    try:
        fit = refit(panel, main, log, fitter, leads=(-3, -2, -1), **kw)
        if fit is None:
            return _not_computed(name, log)
        boot = score_bootstrap(fit, draws=draws, seed=seed, log=log)
    except StageFailed as err:
        return _not_computed(name, log, str(err))
    terms = [t for t in ("lead_3", "lead_2", "lead_1") if t in fit.names]
    if not terms:
        return {
            "check": name,
            "p": np.nan,
            "pass": False,
            "note": "no lead estimable",
            "convergence": log.summary,
            "timing": log.timing,
        }
    b = np.array([fit.value(t) for t in terms])
    D = boot[terms].to_numpy()
    Vi = np.linalg.pinv(np.cov(D, rowvar=False).reshape(len(terms), len(terms)))
    W = float(b @ Vi @ b)
    dev = D - b
    p = float(np.mean(np.einsum("ij,jk,ik->i", dev, Vi, dev) >= W))
    return {
        "check": name,
        "statistic": W,
        "p": p,
        "pass": bool(p >= 0.10),
        "convergence": log.summary,
        "timing": log.timing,
    }


def _interval_check(name, p, main, draws, seed, fitter, **kw) -> dict:
    log = RefitLog(name)
    try:
        r = _effect_interval(p, draws, seed, main, log, fitter, **kw)
    except StageFailed as err:
        return _not_computed(name, log, str(err))
    if r is None:
        return _not_computed(name, log)
    _, _, e, lo, hi = r
    return {
        "check": name,
        "estimate": e,
        "low": lo,
        "high": hi,
        "pass": bool(lo <= 0 <= hi),
        "convergence": log.summary,
        "timing": log.timing,
    }


def check_placebo_dates(panel, main: PooledFit, shift=2, draws=999, seed=0, fitter=None, **kw) -> dict:
    p = panel[(panel["T"].isna()) | (panel["year"] < panel["T"])].copy()
    p["T"] = p["T"] - shift
    p.loc[p["T"].notna(), "dose"] = 1.0
    return _interval_check(f"placebo dates (−{shift} years)", p, main, draws, seed, fitter, **kw)


def check_placebo_outcome(panel, main: PooledFit, draws=999, seed=0, fitter=None, **kw) -> dict:
    p = panel.assign(y=panel["units_5p"].round().astype(int))
    return _interval_check("placebo outcome (5+ units)", p, main, draws, seed, fitter, **kw)


def check_excluding(
    panel,
    main: PooledFit,
    main_summary: pd.DataFrame,
    years=(2020, 2021),
    draws=999,
    seed=0,
    fitter=None,
    **kw,
) -> dict:
    name, log = f"excluding {years}", RefitLog(f"excluding {years}")
    try:
        r = _effect_interval(panel[~panel["year"].isin(years)], draws, seed, main, log, fitter, **kw)
    except StageFailed as err:
        return _not_computed(name, log, str(err))
    if r is None:
        return _not_computed(name, log)
    fit, _, e, _, _ = r
    m = main_summary.set_index("term")
    outside = [
        n
        for n in BAND_NAMES
        if n in fit.names and n in m.index and not (m.loc[n, "low"] <= fit.value(n) <= m.loc[n, "high"])
    ]
    if "overall" in m.index and not (m.loc["overall", "low"] <= e <= m.loc["overall", "high"]):
        outside.append("overall")
    return {
        "check": name,
        "estimate": e,
        "outside": outside,
        "pass": not outside,
        "convergence": log.summary,
        "timing": log.timing,
    }


def check_leave_one_out(
    panel, main: PooledFit, main_summary: pd.DataFrame, fitter=None, workers: int = 1, **kw
) -> dict:
    name, log = "leave one treated place out", RefitLog("leave one treated place out")
    m = main_summary.set_index("term").loc["overall"]
    moved, effects = [], {}
    places = panel.loc[panel["T"].notna(), "place"].unique()
    jobs = [("drop", place) for place in places]
    for place, (e, part) in zip(places, _run_refits(panel, main, jobs, fitter, kw, workers), strict=True):
        _absorb(log, part)
        if e is None:
            continue
        effects[place] = e
        if not (m["low"] <= e <= m["high"]):
            moved.append((place, e))
    try:
        log.check()
    except StageFailed as err:
        return _not_computed(name, log, str(err))
    return {
        "check": name,
        "moved": moved,
        "pass": not moved,
        "convergence": log.summary,
        "timing": log.timing,
        "effects": effects,
    }


def run_parallel(calls: Sequence[tuple[Callable, tuple, dict]], workers: int = 1) -> list:
    """Run independent calls (function, args, kwargs), e.g. the single-refit checks, in `workers` processes;
    results in call order, as if run one after another (functions must be module-level)."""
    if workers <= 1:
        return [fn(*a, **k) for fn, a, k in calls]
    from concurrent.futures import ProcessPoolExecutor

    with ProcessPoolExecutor(
        max_workers=min(workers, len(calls)),
        initializer=_init_worker,
        initargs=(None, None, None, {}, (WARM_START, HESSIAN)),
    ) as ex:
        futs = [ex.submit(fn, *a, **k) for fn, a, k in calls]
        return [f.result() for f in futs]


def summarize_main(fit: PooledFit, boot: pd.DataFrame, level: float = 0.90) -> pd.DataFrame:
    """`summarize` plus the overall pooled effect (bands weighted by treated place-years)."""
    out = summarize(fit, boot, level)
    k = fit.design.X.shape[1]
    dist = np.array([overall_effect(fit, from_log(r.to_numpy(), k)) for _, r in boot[fit.names].iterrows()])
    e = overall_effect(fit)
    a = (1 - level) / 2
    lo, hi = np.quantile(dist - e, [a, 1 - a])
    row = {
        "term": "overall",
        "estimate": e,
        "se": float(np.std(dist, ddof=1)),
        "low": e - hi,
        "high": e - lo,
        "p_two_sided": float(np.mean(np.abs(dist - e) >= abs(e))),
        "weakly_identified": bool(hi - lo > 1.0),
    }
    return pd.concat([out, pd.DataFrame([row])], ignore_index=True)


SENSITIVITY_CONTROLS = ("parking", "process")


def sensitivity_runs(
    panel, main: PooledFit, main_summary: pd.DataFrame, draws=999, seed=0, fitter=None, **kw
) -> list[dict]:
    """The D-031 (c) sensitivity runs of the D-025 model, each one refit under the D-025 convergence rule with
    a score-bootstrap 90% interval of the overall effect, reported beside the main estimate (`inside_main`:
    inside the main 90% interval), not used to choose:

    1. places treated before the panel's first year excluded (no untreated year in the panel);
    2. T at the announcement year (`T_announce`; places without one keep T), each dose path moved with its T;
    3. parking and process reforms as time-varying controls (`SENSITIVITY_CONTROLS`; a control with no
       variation is dropped by the design and listed).
    """
    first = panel["year"].min()
    m = main_summary.set_index("term").loc["overall"]
    early = panel.loc[panel["T"] < first, "place"].unique()
    Ta = panel.drop_duplicates("place").set_index("place")["T_announce"] if "T_announce" in panel else None
    moved = {}
    if Ta is not None:
        T = panel.drop_duplicates("place").set_index("place")["T"]
        moved = {
            pl: float(Ta[pl]) for pl in T.index if pd.notna(T[pl]) and pd.notna(Ta[pl]) and Ta[pl] < T[pl]
        }
    present = [c for c in SENSITIVITY_CONTROLS if c in panel]
    runs = [
        (
            "excluding places treated before the panel",
            panel[~panel["place"].isin(early)],
            {},
            f"{len(early)} places excluded",
        ),
        (
            "T at the announcement year (C29)",
            permute_adoption(panel, moved),
            {},
            f"{len(moved)} places re-dated"
            + ("" if Ta is not None else "; no announcement dates in the panel"),
        ),
        (
            "parking and process controls (C08, C21)",
            panel,
            {"controls": present},
            f"controls: {present or 'none in the panel'}",
        ),
    ]
    out = []
    for name, p, extra, note in runs:
        log = RefitLog(name)
        try:
            r = _effect_interval(p, draws, seed, main, log, fitter, **kw, **extra)
        except StageFailed as err:
            out.append({**_not_computed(name, log, str(err)), "note_sample": note})
            continue
        if r is None:
            out.append({**_not_computed(name, log), "note_sample": note})
            continue
        fit, _, e, lo, hi = r
        out.append(
            {
                "check": name,
                "estimate": e,
                "low": lo,
                "high": hi,
                **{b: fit.value(b) for b in BAND_NAMES if b in fit.design.names},
                "inside_main": bool(m["low"] <= e <= m["high"]),
                "dropped": fit.design.dropped,
                "note_sample": note,
                "convergence": log.summary,
                "timing": log.timing,
            }
        )
    return out


# ---------------------------------------------------------------------------------------------------------
# Transport test (D-023 rule) with the pooled model
# ---------------------------------------------------------------------------------------------------------

MAX_YEARLY_RATE = 0.05


def transport_predict(
    fit: PooledFit,
    boot: pd.DataFrame,
    panel: pd.DataFrame,
    target: pd.DataFrame,
    draws: int = 4000,
    seed: int = 0,
    widening: float = 1.0,
    window: dict | None = None,
    **design_kw,
) -> pd.DataFrame:
    """Predicted ADU permits for places outside the estimation panel.

    Coefficients and year effects from bootstrap draws; each target place's own pre-adoption modifiers
    (z-scored on the estimation panel's treated places); its random effect from its pre-adoption years
    (posterior mode and curvature, drawn normal) when it has any, else u ~ Normal(0, σ²); negative-binomial
    counts with κ. Out-of-range modifiers widen the place's predictive (as hazard.widen). Raises
    EstimationError on non-finite predictions or a predicted MEAN above 5% of eligible parcels a year (single
    draws may exceed it: with a large place-effect σ the predictive tail is long)."""
    rng = np.random.default_rng(seed)
    d = fit.design
    k = d.X.shape[1]
    names = d.names
    treated = panel[panel["T"].notna()].drop_duplicates("place")
    mods = [n.replace("theta_", "") for n in names if n.startswith("theta_")]
    scale = {m: modifier_scale(treated, m) for m in mods}
    lims = {
        m: (float(treated[m].min()), float(treated[m].max()), float(treated[m].std(ddof=1))) for m in mods
    }
    rate_ref = float(panel["rate"].mean())
    rows_b = boot[fit.names].to_numpy()
    out = []
    for place, g in target.groupby("place", sort=False):
        g = g.sort_values("year")
        T = g["T"].iloc[0]
        e = g["year"].to_numpy() - T if not np.isnan(T) else np.full(len(g), -99.0)
        post = (e >= 0).astype(float)
        dist = 0.0
        for m in mods:
            x = g[m].iloc[0]
            lo, hi, sd = lims[m]
            if np.isnan(x):
                continue
            if m == "hh_growth":
                dist += max(0.0, (lo - x) / sd, (x - hi) / sd)
            else:
                xv, lv, hv = (np.exp(x), np.exp(lo), np.exp(hi)) if m == "log_value" else (x, lo, hi)
                if xv > 0 and lv > 0:
                    dist += max(0.0, np.log(lv / xv), np.log(xv / hv))
        Xg = np.zeros((len(g), k))
        for j, n in enumerate(names):
            if n == "intercept":
                Xg[:, j] = 1
            elif n.startswith("year_"):
                Xg[:, j] = (g["year"].to_numpy() == int(n[5:])).astype(float)
            elif n in BAND_NAMES:
                lo_k, hi_k = BANDS[BAND_NAMES.index(n)]
                Xg[:, j] = g["dose"].to_numpy() * ((e >= lo_k) & (e <= hi_k))
            elif n.startswith("theta_"):
                m = n[6:]
                c, sd = scale[m]
                x = g[m].iloc[0]
                Xg[:, j] = (0.0 if np.isnan(x) else (x - c) / sd) * post
            elif n == "rho":
                Xg[:, j] = (g["rate"].to_numpy() - rate_ref) * post
            elif n == "delta":
                Xg[:, j] = g["mm"].to_numpy()
        years_fit = {int(n[5:]) for n in names if n.startswith("year_")} | {int(d.years.min())}
        if not set(g["year"].astype(int)) <= years_fit:
            raise EstimationError(f"transport for {place}: years outside the estimation years")
        off = np.log(g["eligible"].to_numpy(dtype=float))
        pre = post == 0
        sims = np.zeros((draws, len(g)))
        mus = np.zeros((draws, len(g)))
        lp = fit.log_params
        for i in range(draws):
            b = to_log(rows_b[rng.integers(len(rows_b))], k)
            sigma, kappa = math.exp(b[k]), math.exp(b[k + 1])
            eta = off + Xg @ b[:k]
            if pre.any() and g["y"].to_numpy()[pre].sum() > 0:
                yy = g["y"].to_numpy(dtype=float)[pre]
                r = 1 / kappa
                u = 0.0
                for _ in range(50):
                    mu = np.exp(eta[pre] + u)
                    dH = np.sum((yy - mu) * r / (r + mu)) - u / sigma**2
                    d2H = np.sum(-mu * r * (r + yy) / (r + mu) ** 2) - 1 / sigma**2
                    u -= np.clip(dH / d2H, -5, 5)
                u_draw = u + rng.standard_normal() / math.sqrt(-d2H)
            else:
                u_draw = rng.normal(0, sigma)
            s = widening * dist
            if not np.all(np.isfinite(eta + u_draw)):
                raise EstimationError(f"transport for {place}: non-finite prediction")
            mu = np.exp(np.minimum(eta + u_draw + s * rng.standard_normal() - s**2 / 2, 700))
            mus[i] = mu
            lam = rng.gamma(1 / kappa, mu * kappa) if kappa > 1e-6 else mu
            sims[i] = rng.poisson(lam)
        _ = lp
        # D-025 guard on the predicted MEAN (not single draws, whose tails are wide when σ is large)
        mean_rate = mus.mean(axis=0) / g["eligible"].to_numpy(dtype=float)
        if not np.all(np.isfinite(mean_rate)) or np.max(mean_rate) > MAX_YEARLY_RATE:
            raise EstimationError(
                f"transport for {place}: predicted mean ADU rate {np.max(mean_rate):.1%} of eligible parcels "
                f"a year (limit {MAX_YEARLY_RATE:.0%}) or non-finite"
            )
        lo_y, hi_y = (window or {}).get(place, (-np.inf, np.inf))
        scored = ((g["year"] >= lo_y) & (g["year"] <= hi_y)).to_numpy()
        for t in np.where(scored)[0]:
            col = sims[:, t]
            out.append(
                {
                    "place": place,
                    "name": g["name"].iloc[0] if "name" in g else place,
                    "year": int(g["year"].iloc[t]),
                    "observed": int(g["y"].iloc[t]),
                    "mean": col.mean(),
                    "p05": np.quantile(col, 0.05),
                    "p10": np.quantile(col, 0.10),
                    "p50": np.quantile(col, 0.5),
                    "p90": np.quantile(col, 0.90),
                    "p95": np.quantile(col, 0.95),
                    "outside_range": dist,
                }
            )
        tot = sims[:, scored].sum(axis=1)
        out.append(
            {
                "place": place,
                "name": g["name"].iloc[0] if "name" in g else place,
                "year": "total",
                "observed": int(g["y"].to_numpy()[scored].sum()),
                "mean": tot.mean(),
                "p05": np.quantile(tot, 0.05),
                "p10": np.quantile(tot, 0.10),
                "p50": np.quantile(tot, 0.5),
                "p90": np.quantile(tot, 0.90),
                "p95": np.quantile(tot, 0.95),
                "outside_range": dist,
            }
        )
    return pd.DataFrame(out)


# ---------------------------------------------------------------------------------------------------------
# HonestDiD bounds (D-025 dated note, 2026-10-21; Rambachan & Roth 2023)
# ---------------------------------------------------------------------------------------------------------

RM_GRID = (0.5, 1.0, 1.5, 2.0)
SD_GRID = (0.0, 0.05, 0.1, 0.2)


def honest_set(theta: float, leads, omega, kind: str, m: float) -> tuple[float, float]:
    """Identified set for the pooled post-adoption effect θ under a bound on how the pre-trend continues.

    `leads` = (δ_−3, δ_−2, δ_−1) relative to δ_−4 = 0; `omega[k]` = share of treated place-years at event time
    k = 0, 1, … (sums to 1). Bias B = Σ_k ω_k δ_k.
    - 'rm' (relative magnitudes, M̄ = m): |δ_k − δ_{k−1}| ≤ m · M_pre, M_pre the largest pre-period step:
      B in δ_−1 ± m · M_pre · Σ ω_k (k + 1).
    - 'sd' (smoothness, M = m): second differences at most m, extending the slope δ_−1 − δ_−2:
      B in Σ ω_k [δ_−1 + (k + 1)(δ_−1 − δ_−2)] ± m · Σ ω_k (k + 1)(k + 2) / 2.
    Returns (θ − B_max, θ − B_min). By hand: θ 0.9, leads (0.1, 0.2, 0.3), ω = (0.5, 0.5), 'rm' m = 1:
    M_pre 0.1, Σ ω (k + 1) = 1.5, B in 0.3 ± 0.15 -> (0.45, 0.75).
    """
    d3, d2, d1 = (float(x) for x in leads)
    w = np.asarray(omega, dtype=float)
    k1 = np.arange(1, len(w) + 1)
    if kind == "rm":
        mpre = max(abs(d3), abs(d2 - d3), abs(d1 - d2))
        centre, half = d1, m * mpre * float(w @ k1)
    elif kind == "sd":
        centre = d1 + (d1 - d2) * float(w @ k1)
        half = m * float(w @ (k1 * (k1 + 1) / 2))
    else:
        raise ValueError(kind)
    return theta - centre - half, theta - centre + half


def honest_bounds(
    theta_hat: float,
    leads_hat,
    theta_draws,
    lead_draws,
    omega,
    level: float = 0.90,
    rm_grid=RM_GRID,
    sd_grid=SD_GRID,
) -> pd.DataFrame:
    """Identified sets (`honest_set`) at the estimates and robust intervals from the bootstrap: the
    (1 − level)/2 quantile of the draws' lower bounds to the (1 + level)/2 quantile of their upper bounds."""
    a = (1 - level) / 2
    rows = []
    for kind, grid in (("rm", rm_grid), ("sd", sd_grid)):
        for m in grid:
            lo, hi = honest_set(theta_hat, leads_hat, omega, kind, m)
            sets = np.array(
                [honest_set(t, d, omega, kind, m) for t, d in zip(theta_draws, lead_draws, strict=True)]
            )
            rows.append(
                {
                    "restriction": "relative magnitudes" if kind == "rm" else "smoothness",
                    "m": m,
                    "set_low": lo,
                    "set_high": hi,
                    "ci_low": float(np.quantile(sets[:, 0], a)),
                    "ci_high": float(np.quantile(sets[:, 1], 1 - a)),
                }
            )
    out = pd.DataFrame(rows)
    return out.assign(ci_includes_0=(out["ci_low"] <= 0) & (out["ci_high"] >= 0))


def rm_breakdown(theta_draws, lead_draws, omega, level: float = 0.90, step: float = 0.01, top: float = 10.0):
    """Smallest M̄ (relative magnitudes, on a grid of `step`) whose robust interval includes 0 (NaN if none
    up to `top`)."""
    a = (1 - level) / 2
    for m in np.arange(0.0, top + step / 2, step):
        sets = np.array(
            [honest_set(t, d, omega, "rm", m) for t, d in zip(theta_draws, lead_draws, strict=True)]
        )
        if np.quantile(sets[:, 0], a) <= 0 <= np.quantile(sets[:, 1], 1 - a):
            return float(round(m, 6))
    return float("nan")


def event_study_inputs(fit: PooledFit, boot: pd.DataFrame, panel: pd.DataFrame):
    """From the pre-trend-leads refit: θ (mean of β_band(k) × dose over treated place-years with k >= 0),
    the leads (δ_−3, δ_−2, δ_−1), each also per bootstrap draw, and ω_k (shares of those place-years by k).
    Raises `EstimationError` if a lead or band was dropped from the refit: a term dropped because every count
    where it applies is zero has its estimate at −∞, not 0, so the bias chain δ_−4 = 0 → δ_−1 (and θ) is not
    identified (D-031 HonestDiD note, 2026-10-21; the first version counted it as 0)."""
    missing = [n for n in (*BAND_NAMES, "lead_3", "lead_2", "lead_1") if n not in fit.names]
    if missing:
        why = [d for d in fit.design.dropped if d.split(" ")[0] in missing]
        raise EstimationError(f"HonestDiD inputs not identified: {missing} not estimated ({why})")
    post = panel[panel["T"].notna() & (panel["year"] >= panel["T"])]
    k = (post["year"] - post["T"]).to_numpy(dtype=int)
    dose = post["dose"].to_numpy(dtype=float)
    band = _band_of(k)
    omega = np.bincount(k, minlength=k.max() + 1) / len(k)

    def theta(values: Mapping) -> float:
        b = np.array([float(values.get(n, 0.0)) for n in BAND_NAMES])
        return float(np.mean(b[band] * dose))

    def leads(values: Mapping) -> tuple[float, float, float]:
        return tuple(float(values.get(f"lead_{j}", 0.0)) for j in (3, 2, 1))

    est_ = dict(zip(fit.names, fit.log_params, strict=True))
    draws = boot.to_dict("records")
    return (
        theta(est_),
        leads(est_),
        np.array([theta(r) for r in draws]),
        [leads(r) for r in draws],
        omega,
    )


# ---------------------------------------------------------------------------------------------------------
# Robustness (D-025): Borusyak imputation, D-023's fixed-effects PPML, binary dose
# ---------------------------------------------------------------------------------------------------------


def _band_of(e: np.ndarray) -> np.ndarray:
    out = np.full(len(e), -1)
    for b, (lo, hi) in enumerate(BANDS):
        out[(e >= lo) & (e <= hi)] = b
    return out


def imputation_effects(panel: pd.DataFrame) -> dict[str, float]:
    """Borusyak-Jaravel-Spiess imputation for counts: PPML with place and year effects on untreated
    place-years only (never treated, and treated places before adoption), then for treated place-years the
    imputed untreated mean μ̂0. Effect per band (log) = log(Σ y / Σ μ̂0); overall over all treated rows.
    Treated places with no untreated permits can't be imputed and are left out (counted)."""
    e = (panel["year"] - panel["T"]).to_numpy(dtype=float)
    treated_row = (e >= 0) & ~np.isnan(e)
    un = panel[~treated_row]
    fit = ppml(
        un["y"], np.zeros((len(un), 0)), np.log(un["eligible"]), un["place"], un["year"], [], check=False
    )
    alpha = dict(zip(np.unique(un["place"][fit.keep]), fit.alpha, strict=True))
    gamma = dict(zip(fit.years, fit.gamma, strict=True))
    tr = panel[treated_row].copy()
    tr["mu0"] = [
        r.eligible * math.exp(alpha[r.place] + gamma[r.year])
        if r.place in alpha and r.year in gamma
        else np.nan
        for r in tr.itertuples()
    ]
    tr["band"] = _band_of((tr["year"] - tr["T"]).to_numpy())
    ok = tr["mu0"].notna()
    out = {"imputed_rows": int(ok.sum()), "not_imputable_rows": int((~ok).sum())}
    for b, name in enumerate(BAND_NAMES):
        sel = ok & (tr["band"] == b)
        out[name] = (
            float(np.log(tr.loc[sel, "y"].sum() / tr.loc[sel, "mu0"].sum()))
            if tr.loc[sel, "y"].sum() > 0
            else -np.inf
        )
    out["overall"] = (
        float(np.log(tr.loc[ok, "y"].sum() / tr.loc[ok, "mu0"].sum()))
        if tr.loc[ok, "y"].sum() > 0
        else -np.inf
    )
    return out


def imputation_bootstrap(panel: pd.DataFrame, draws: int = 999, seed: int = 0) -> pd.DataFrame:
    """Place-cluster (pairs) bootstrap of `imputation_effects`: resample places with replacement."""
    rng = np.random.default_rng(seed)
    places = panel["place"].unique()
    rows = []
    for _ in range(draws):
        pick = rng.choice(places, size=len(places), replace=True)
        parts = [panel[panel["place"] == p].assign(place=f"{p}#{i}") for i, p in enumerate(pick)]
        rows.append(imputation_effects(pd.concat(parts, ignore_index=True)))
    return pd.DataFrame(rows)


def fe_ppml_pooled(panel: pd.DataFrame, **design_kw) -> dict:
    """D-023's fixed-effects PPML with the pooled bands (robustness). Returns its estimates with
    cluster-robust SEs, or the EstimationError message if it does not estimate."""
    d = build_pooled_design(panel, **design_kw)
    keep = [j for j, n in enumerate(d.names) if n != "intercept" and not n.startswith("year_")]
    try:
        f = ppml(d.y, d.X[:, keep], d.offset, d.places[d.place_idx], d.row_year, [d.names[j] for j in keep])
    except EstimationError as err:
        return {"estimated": False, "reason": str(err)}
    H = np.linalg.pinv(f.hessian)
    S = f.cluster_scores("cr2")
    se = np.sqrt(np.clip(np.diag(H @ (S.T @ S) @ H)[: len(f.names)], 0, None))
    return {
        "estimated": True,
        **{n: v for n, v in zip(f.names, f.coef, strict=True)},
        **{f"se_{n}": v for n, v in zip(f.names, se, strict=True)},
        "dropped": f.dropped_columns,
        "kept_rows": int(f.keep.sum()),
    }
