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
  steps); the marginal likelihood is maximized by BFGS with central-difference gradients. A regressor that is
  zero wherever counts are positive (an event-time band with no ADU) cannot be estimated; it is dropped and
  reported, never silently.
- **Inference:** a wild cluster score bootstrap by place (Webb weights): per-place score contributions by
  central differences, one Newton step b* = b̂ + H⁻¹ Σ_g w_g S_g per draw, H the numerical Hessian of the
  marginal log-likelihood. Randomization inference re-fits with adoption years permuted among treated places.
- **Guards:** the fit raises `EstimationError` (shared with `estimate_adu`) if BFGS doesn't converge, if a
  coefficient leaves ±20, if the Hessian is not negative definite, or if an SE is effectively zero.

Only NumPy and pandas.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
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
) -> PooledDesign:
    """Regressors for the D-025 model from a panel with columns place, year, y, eligible, T, dose, rate, mm
    and the modifiers. Bands scale the dose (or 1[by right] with `binary_dose`). A column with no non-zero
    entry, or whose non-zero rows all have zero counts (not estimable: the likelihood rises without bound as
    its coefficient falls), is dropped and listed in `dropped`; then separated rows (`relu_separated`)."""
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


def _nb_tables(y: np.ndarray, r: float) -> tuple[np.ndarray, np.ndarray]:
    """For integer counts y: log Γ(y + r) − log Γ(r) = Σ_{j<y} log(r + j), and its r-derivative
    ψ(y + r) − ψ(r) = Σ_{j<y} 1/(r + j), by cumulative sums (exact, no special functions)."""
    yi = y.astype(int)
    top = int(yi.max()) if len(yi) else 0
    j = np.arange(top)
    lg = np.r_[0.0, np.cumsum(np.log(r + j))]
    dg = np.r_[0.0, np.cumsum(1.0 / (r + j))]
    return lg[yi], dg[yi]


def place_logliks(params: np.ndarray, d: PooledDesign, newton_steps: int = 30, grad: bool = False):
    """Marginal log-likelihood of each place: log ∫ Π_t NB(y_it; μ_it e^u) φ(u; 0, σ²) du, by adaptive
    Gauss-Hermite quadrature (the integrand's mode û_i by Newton steps, its curvature, `QUAD_NODES` nodes).

    params = (fixed coefficients…, log σ, log κ). With `grad`, also returns the places' scores (places ×
    parameters): the posterior-weighted (quadrature) sums of Σ_t X_it (y − μ) r/(r + μ) for the coefficients,
    u²/σ² − 1 for log σ, and −r [Σ_{j<y} 1/(r + j) + log(r/(r + μ)) + (μ − y)/(r + μ)] for log κ (r = 1/κ).
    """
    k = d.X.shape[1]
    b, log_s, log_k = params[:k], params[k], params[k + 1]
    sigma, kappa = math.exp(log_s), math.exp(log_k)
    r = 1.0 / kappa
    eta = d.offset + d.X @ b
    G = len(d.places)
    idx = d.place_idx
    y = d.y
    lg, dg = _nb_tables(y, r)
    const = lg - d.log_fact

    def h_and_derivs(u):
        mu = np.exp(np.clip(eta + u[idx], -700, 50))
        ll = const + r * np.log(r / (r + mu)) + y * np.log(np.where(mu > 0, mu, 1e-300) / (r + mu))
        g = (y - mu) * r / (r + mu)
        h2 = -mu * r * (r + y) / (r + mu) ** 2
        H = np.bincount(idx, ll, G) - 0.5 * (u / sigma) ** 2 - 0.5 * math.log(2 * math.pi) - log_s
        dH = np.bincount(idx, g, G) - u / sigma**2
        d2H = np.bincount(idx, h2, G) - 1 / sigma**2
        return H, dH, d2H, mu, g

    u = np.zeros(G)
    for _ in range(newton_steps):
        _, dH, d2H, _, _ = h_and_derivs(u)
        step = dH / d2H
        u = u - np.clip(step, -5, 5)
        if np.max(np.abs(step)) < 1e-10:
            break
    d2H = h_and_derivs(u)[2]
    s = 1 / np.sqrt(-d2H)
    vals = np.empty((QUAD_NODES, G))
    nodes = []
    for q, (x, w) in enumerate(zip(_NODES, _WEIGHTS, strict=True)):
        uq = u + math.sqrt(2) * s * x
        Hq, _, _, mu, g = h_and_derivs(uq)
        vals[q] = math.log(w) + x**2 + Hq
        nodes.append((uq, mu, g))
    total = np.logaddexp.reduce(vals, axis=0)
    ll = np.log(math.sqrt(2)) + np.log(s) + total
    if not grad:
        return ll
    omega = np.exp(vals - total[None, :])  # posterior weights of the nodes, per place
    S = np.zeros((G, k + 2))
    for q, (uq, mu, g) in enumerate(nodes):
        wq = omega[q]
        S[:, :k] += wq[:, None] * _sum_by(idx, d.X * g[:, None], G)
        S[:, k] += wq * (uq**2 / sigma**2 - 1)
        dk = -r * (dg + np.log(r / (r + mu)) + (mu - y) / (r + mu))
        S[:, k + 1] += wq * np.bincount(idx, dk, G)
    return ll, S


def _sum_by(idx: np.ndarray, M: np.ndarray, G: int) -> np.ndarray:
    out = np.zeros((G, M.shape[1]))
    np.add.at(out, idx, M)
    return out


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
    f: Callable, x0: np.ndarray, tol: float = 1e-6, max_iter: int = 500, grad: Callable | None = None
) -> tuple[np.ndarray, float, bool]:
    """Maximize f by BFGS (minimizing −f) with an Armijo backtracking line search and central-difference
    gradients. Converged when the largest gradient component is below `tol` × (1 + |f|)."""

    def F(x):
        v = f(x)
        return np.inf if not np.isfinite(v) else -v

    def dF(x):
        return -grad(x) if grad is not None else _grad(F, x)

    x = np.asarray(x0, dtype=float).copy()
    Fx = F(x)
    G = dF(x)
    Hinv = np.eye(len(x)) / max(1.0, np.max(np.abs(G)))
    for _ in range(max_iter):
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


def fit_pooled(
    d: PooledDesign, start: np.ndarray | None = None, check: bool = True, max_iter: int = 500
) -> PooledFit:
    """Maximum marginal likelihood of the D-025 model; raises EstimationError if unusable."""
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

    def scores(z):
        _, S = place_logliks(to_log(z, k), d, grad=True)
        S[:, k] *= 1 / math.cosh(z[k] / SIGMA_BOUND) ** 2  # chain rule through the tanh map
        S[:, k + 1] *= 1 / math.cosh(z[k + 1] / KAPPA_BOUND) ** 2
        return S

    def g(z):
        return scores(z).sum(axis=0)

    x, fx, ok = bfgs_max(f, z0, grad=g, max_iter=max_iter)
    # a variance parameter at its limit (no place heterogeneity, or Poisson counts) is held there: its
    # curvature is ~0, so it is left out of the Hessian and scores (reported as at its bound)
    logs = to_log(x, k)
    at_bound = [j for j, lim in ((k, SIGMA_BOUND), (k + 1, KAPPA_BOUND)) if abs(logs[j]) > 0.95 * lim]
    free = [j for j in range(k + 2) if j not in at_bound]
    H = _jacobian(g, x, 1e-5)
    H = (H + H.T) / 2
    S = scores(x)
    H_free = H[np.ix_(free, free)]
    H = np.full_like(H, 0.0)
    H[np.ix_(free, free)] = H_free
    for j in at_bound:
        H[j, j] = -1.0  # placeholder curvature; its score column is zeroed so it never moves in the bootstrap
        S[:, j] = 0.0
    fit = PooledFit(d, x, fx, ok, H, S)
    fit.at_bound = [("log_sigma" if j == k else "log_kappa") for j in at_bound]
    if check:
        check_pooled(fit)
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


def estimate_pooled(panel: pd.DataFrame, check: bool = True, max_iter: int = 500, **design_kw) -> PooledFit:
    return fit_pooled(build_pooled_design(panel, **design_kw), check=check, max_iter=max_iter)


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


def _default_fitter(panel, start: PooledFit | None = None, **kw) -> PooledFit:
    d = build_pooled_design(panel, **kw)
    return fit_pooled(d, start=start_from(start, d) if start is not None else None)


def refit(
    panel, main: PooledFit | None, log: RefitLog, fitter: Callable | None = None, **kw
) -> PooledFit | None:
    """One refit under the D-025 rule: try; if it doesn't converge, retry once starting from the main-model
    estimates; if it still fails, count it as excluded and return None."""
    fitter = fitter or _default_fitter
    log.refits += 1
    try:
        fit = fitter(panel, **kw)
        log.first += 1
        return fit
    except EstimationError:
        pass
    try:
        fit = fitter(panel, start=main, **kw)
        log.retried += 1
        return fit
    except EstimationError:
        log.failed += 1
        return None


def score_bootstrap(
    fit: PooledFit, draws: int = 999, seed: int = 0, log: RefitLog | None = None
) -> pd.DataFrame:
    """Wild cluster score bootstrap by place (Webb weights): b* = b̂ − H⁻¹ Σ_g w_g S_g (H negative
    definite). A draw beyond the coefficient bound is excluded and counted in `log` (D-025 rule); without a
    log, any such draw raises."""
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
    panel, permutations: int, main: PooledFit, seed: int = 0, fitter=None, **design_kw
):
    """Permute adoption years among treated places, re-fit (D-025 convergence rule), compare the overall
    pooled effect of `main` with the permutation distribution. Returns (observed, p over the converged
    refits, distribution, log)."""
    rng = np.random.default_rng(seed)
    log = RefitLog("randomization inference")
    obs = overall_effect(main)
    treated = panel.loc[panel["T"].notna(), ["place", "T"]].drop_duplicates("place")
    out = []
    for _ in range(permutations):
        perm = dict(zip(treated["place"], rng.permutation(treated["T"].to_numpy()), strict=True))
        p = panel.copy()
        p["T"] = p["place"].map(perm).where(p["place"].isin(perm), p["T"])
        f = refit(p, main, log, fitter, **design_kw)
        if f is not None:
            out.append(overall_effect(f))
        if log.failed > log.max_share * permutations:  # the 5% limit is already broken: stop now
            break
    log.check()
    dist = np.array(out)
    return obs, float(np.mean(np.abs(dist) >= abs(obs))), dist, log


# ---------------------------------------------------------------------------------------------------------
# Checks (D-023 §checks, applied to the D-025 model, under the D-025 convergence rule)
# ---------------------------------------------------------------------------------------------------------


def _not_computed(name: str, log: RefitLog, why: str = "did not converge after a retry") -> dict:
    return {"check": name, "pass": None, "note": f"not computed: {why}", "convergence": log.summary}


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
        }
    b = np.array([fit.value(t) for t in terms])
    D = boot[terms].to_numpy()
    Vi = np.linalg.pinv(np.cov(D, rowvar=False).reshape(len(terms), len(terms)))
    W = float(b @ Vi @ b)
    dev = D - b
    p = float(np.mean(np.einsum("ij,jk,ik->i", dev, Vi, dev) >= W))
    return {"check": name, "statistic": W, "p": p, "pass": bool(p >= 0.10), "convergence": log.summary}


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
    return {"check": name, "estimate": e, "outside": outside, "pass": not outside, "convergence": log.summary}


def check_leave_one_out(panel, main: PooledFit, main_summary: pd.DataFrame, fitter=None, **kw) -> dict:
    name, log = "leave one treated place out", RefitLog("leave one treated place out")
    m = main_summary.set_index("term").loc["overall"]
    moved, effects = [], {}
    for place in panel.loc[panel["T"].notna(), "place"].unique():
        f = refit(panel[panel["place"] != place], main, log, fitter, **kw)
        if f is None:
            continue
        e = overall_effect(f)
        effects[place] = e
        if not (m["low"] <= e <= m["high"]):
            moved.append((place, e))
    try:
        log.check()
    except StageFailed as err:
        return _not_computed(name, log, str(err))
    return {"check": name, "moved": moved, "pass": not moved, "convergence": log.summary, "effects": effects}


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
    EstimationError on non-finite or absurd means (> 5% of eligible parcels a year)."""
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
            log_rate = eta - off + u_draw
            if not np.all(np.isfinite(log_rate)) or np.max(log_rate) > math.log(MAX_YEARLY_RATE):
                raise EstimationError(
                    f"transport for {place}: predicted ADU rate beyond {MAX_YEARLY_RATE:.0%} of "
                    "eligible parcels a year (or non-finite)"
                )
            mu = np.exp(eta + u_draw + s * rng.standard_normal() - s**2 / 2)
            lam = rng.gamma(1 / kappa, mu * kappa) if kappa > 1e-6 else mu
            sims[i] = rng.poisson(lam)
        _ = lp
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
