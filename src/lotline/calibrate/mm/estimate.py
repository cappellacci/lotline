"""Missing-middle D-024 and D-025 estimators: the event-time design, PPML, the negative binomial fit, the
random-effects fallback, the bootstrap and the summaries.

Part of `estimate_mm`, split by method step (modularity step 3); `estimate_mm` re-exports every name.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .panel import EVENT_BINS, STATES

# ---------------------------------------------------------------------------------------------------------
# Estimation (D-024): design, PPML with place and state × year effects, and the pre-specified fallback
# ---------------------------------------------------------------------------------------------------------

MAIN_MODIFIERS = ("pcr", "log_value")


BIN_NAMES = ("beta_0", "beta_2", "beta_4")  # k = 0-1, 2-3, 4+ (the number is the bin's first year)


LEADS = (-3, -2, -1)


def year_code(panel: pd.DataFrame) -> np.ndarray:
    """State × year group as one integer (state's position in STATES × 10,000 + year), so the year effects
    γ_st are one fixed effect per state and year. By hand: NC 2020 -> 12020."""
    s = panel["state"].map({st: i for i, st in enumerate(STATES)}).to_numpy(dtype=int)
    return s * 10_000 + panel["year"].to_numpy(dtype=int)


def build_design(
    panel: pd.DataFrame,
    modifiers: Sequence[str] = MAIN_MODIFIERS,
    leads: Sequence[int] = (),
    binary_dose: bool = False,
    use_rate: bool = True,
    use_adu: bool = True,
    scale_from: pd.DataFrame | None = None,
):
    """Regressors of the D-024 model from a panel (place, state, year, T, dose, rate, adu, modifiers).

    - β_b: dose × 1[t − T in bin b], b = 0-1, 2-3, 4+ (`binary_dose`: 1 instead of the dose);
    - leads: 1[t − T = k] for k < 0 (pre-trend check);
    - θ_m: z-score of the modifier over the treated places (of `scale_from`, default the panel) × post;
    - ρ: (rate − panel mean rate) × post; δ: adu.
    Returns an `estimate_adu.Design` whose bin columns are named beta_0 / beta_2 / beta_4, so the D-023
    aggregation (`estimate_adu.aggregate`) weights them by counterfactual expected homes.
    """
    from lotline.calibrate.adu.estimate_adu import Design, modifier_scale

    e = panel["year"].to_numpy(dtype=float) - panel["T"].to_numpy(dtype=float)
    post = np.nan_to_num((e >= 0).astype(float) * ~np.isnan(e))
    dose = panel["dose"].to_numpy(dtype=float)
    if binary_dose:
        dose = (dose > 0).astype(float)
    cols, names, cells = [], [], []
    for (lo, hi), name in zip(EVENT_BINS, BIN_NAMES, strict=True):
        ind = (e >= lo) & (e <= (np.inf if hi is None else hi))
        if ind.any():
            cols.append(dose * ind)
            names.append(name)
            cells.append((-1, lo))
    n_cells = len(cols)
    for k in leads:
        cols.append((e == k).astype(float))
        names.append(f"lead_{-k}")
    ref = panel if scale_from is None else scale_from
    treated = ref.loc[ref["T"].notna()].drop_duplicates("place")
    for m in modifiers:
        centre, sd = modifier_scale(treated, m)
        cols.append(np.nan_to_num((panel[m].to_numpy(dtype=float) - centre) / sd) * post)
        names.append(f"theta_{m}")
    if use_rate:
        r = panel["rate"].to_numpy(dtype=float)
        cols.append((r - float(ref["rate"].mean())) * post)
        names.append("rho")
    if use_adu:
        cols.append(panel["adu"].to_numpy(dtype=float))
        names.append("delta")
    X = np.column_stack(cols) if cols else np.zeros((len(panel), 0))
    return Design(X, names, cells, n_cells)


def estimate(panel: pd.DataFrame, method: str = "ppml", **design_kw):
    """Fit the D-024 model on the place-years with an outcome. `method`: 'ppml' (main: place and state ×
    year fixed effects, `estimate_adu.ppml` with its separation removal and guards), 'nb' (the pre-specified
    fallback: D-025's negative binomial with normal place random effects, `fit_nb`) or 're' (Poisson-gamma
    place random effects, `fit_re`; a robustness model). Returns an `estimate_adu.Estimate`."""
    from lotline.calibrate.adu.estimate_adu import Estimate, ppml

    p = panel[panel["y"].notna()].reset_index(drop=True)
    d = build_design(p, **design_kw)
    off = np.log(p["eligible"].to_numpy(dtype=float))
    if method == "ppml":
        fit = ppml(p["y"], d.X, off, p["place"], year_code(p), d.names)
    elif method == "re":
        fit = fit_re(p["y"], d.X, off, p["place"], year_code(p), d.names)
    elif method == "nb":
        fit = fit_nb(p, d, **design_kw)
    else:
        raise ValueError(f"unknown method {method!r}")
    return Estimate(fit, d, p)


NB_NAMES = {"beta_0_1": "beta_0", "beta_2_3": "beta_2", "beta_4p": "beta_4"}  # D-025 bands -> D-024 bins


@dataclass
class NBFit:
    """A D-025 negative-binomial fit (`pooled_adu.fit_pooled`) seen through D-024's names, with the attributes
    `estimate_adu.aggregate` / `summarize` and `transport_predict` use."""

    names: list
    coef: np.ndarray
    mu: np.ndarray  # fitted means at each place's posterior-mode random effect
    keep: np.ndarray
    y: np.ndarray
    cluster: np.ndarray
    alpha: np.ndarray  # intercept + random effect, per place
    gamma: np.ndarray  # state-year effects (reference = 0)
    years: np.ndarray
    pooled: object
    iterations: int = 0
    converged: bool = True
    dropped_places: list = field(default_factory=list)
    dropped_columns: list = field(default_factory=list)
    separated: list = field(default_factory=list)

    def coef_of(self, name: str) -> float:
        return float(self.coef[self.names.index(name)])


NB_MAX_ITER = 3000  # BFGS iterations for the D-025 fit: dozens of state-year dummies need more than its 500


def poisson_start(X: np.ndarray, y: np.ndarray, offset: np.ndarray, iters: int = 25) -> np.ndarray:
    """Start values for the D-025 fit: a pooled Poisson regression (no place effects) on the same fixed
    design, by IRLS. Only where BFGS starts; the estimate is D-025's maximum. By hand: intercept only, y = (2,
    6), offset 0 -> log 4."""
    b = np.zeros(X.shape[1])
    b[0] = math.log(max(y.sum(), 1e-9) / np.exp(offset).sum())
    for _ in range(iters):
        eta = np.clip(offset + X @ b, -50, 50)
        mu = np.exp(eta)
        w = np.sqrt(mu)
        z = eta - offset + (y - mu) / mu
        b_new = np.linalg.lstsq(X * w[:, None], z * w, rcond=None)[0]
        if np.max(np.abs(b_new - b)) < 1e-8:
            return np.clip(b_new, -15, 15)
        b = b_new
    return np.clip(b, -15, 15)


def pooled_panel(p: pd.DataFrame) -> pd.DataFrame:
    """The D-024 panel relabelled for D-025's design builder, which is used unchanged: `year` becomes the
    state × year code (`year_code`), so its year dummies are D-024's state × year effects; `T` is shifted by
    the same state offset, so event time t − T is unchanged; `mm` (D-025's δ column) carries D-024's ADU
    term. By hand: NC 2021 with T = 2020 -> year 12021, T 12020, event time 1."""
    shift = p["state"].map({st: i for i, st in enumerate(STATES)}).to_numpy(dtype=float) * 10_000
    return p.assign(year=year_code(p), T=p["T"].to_numpy(dtype=float) + shift, mm=p["adu"])


def fit_nb(p: pd.DataFrame, d, modifiers=MAIN_MODIFIERS, leads=(), binary_dose=False, use_rate=True,
           use_adu=True, scale_from=None) -> NBFit:  # fmt: skip
    """D-025's estimator (`pooled_adu.build_pooled_design` and `fit_pooled`, unchanged) on the D-024 panel
    (`pooled_panel`); its guards raise `EstimationError`. `d` is the D-024 design of the same rows."""
    from lotline.calibrate.adu import pooled_adu as pa

    if scale_from is not None:
        raise ValueError("the D-025 design scales modifiers on its own panel")
    pp = pooled_panel(p)
    pd_ = pa.build_pooled_design(pp, modifiers=modifiers, leads=leads, use_rate=use_rate, use_mm=use_adu,
                                 binary_dose=binary_dose)  # fmt: skip
    k = pd_.X.shape[1]
    start = np.r_[poisson_start(pd_.X, pd_.y, pd_.offset), 0.0, math.log(0.5)]  # σ = 1, κ = 0.5 as in D-025
    pf = pa.fit_pooled(pd_, start=start, max_iter=NB_MAX_ITER)
    lp = pf.log_params
    u = pa.place_effects(lp, pd_)
    mu = np.exp(pd_.offset + pd_.X @ lp[:k] + u[pd_.place_idx])
    sep = set(getattr(pd_, "separated", []))
    keep = np.array([(pl, int(c)) not in sep for pl, c in zip(p["place"], pp["year"], strict=True)])
    names, coef = [], []
    for j, n in enumerate(pd_.names):
        if n == "intercept" or n.startswith("year_"):
            continue
        names.append(NB_NAMES.get(n, n))
        coef.append(lp[j])
    gam = {int(n.split("_", 1)[1]): lp[j] for j, n in enumerate(pd_.names) if n.startswith("year_")}
    years = np.asarray(pd_.years)
    a0 = lp[pd_.names.index("intercept")] if "intercept" in pd_.names else 0.0
    fit = NBFit(
        names=names, coef=np.asarray(coef), mu=mu, keep=keep, y=pd_.y, cluster=pd_.places[pd_.place_idx],
        alpha=a0 + u, gamma=np.array([gam.get(int(c), 0.0) for c in years]), years=years, pooled=pf,
        dropped_columns=list(pd_.dropped), separated=sorted(sep),
    )  # fmt: skip
    fit.at_bound = getattr(pf, "at_bound", [])
    fit.sigma, fit.kappa = math.exp(lp[k]), math.exp(lp[k + 1])
    return fit


def treated_dropped(est_) -> list:
    """Treated places the fit dropped (all their rows removed): D-024's trigger for the fallback."""
    p = est_.panel
    treated = set(p.loc[p["T"].notna(), "place"])
    kept = set(p.loc[est_.fit.keep, "place"])
    return sorted(treated - kept)


@dataclass
class REFit:
    """A Poisson-gamma random-effects fit, with the attributes `estimate_adu.aggregate` / `summarize` use."""

    names: list
    coef: np.ndarray
    params: np.ndarray  # [regressors | intercept | state-year effects (drop first) | log a]
    info: np.ndarray  # minus the Hessian of the log likelihood
    scores: np.ndarray  # clusters × params
    mu: np.ndarray  # fitted means, including each place's posterior multiplier
    keep: np.ndarray
    y: np.ndarray
    cluster: np.ndarray
    alpha: np.ndarray  # intercept + log posterior multiplier, per place
    gamma: np.ndarray  # state-year effects (first = 0)
    years: np.ndarray
    a: float  # gamma shape: var(u) = 1 / a
    iterations: int = 0
    converged: bool = True
    dropped_places: list = field(default_factory=list)
    dropped_columns: list = field(default_factory=list)
    separated: list = field(default_factory=list)

    def coef_of(self, name: str) -> float:
        return float(self.coef[self.names.index(name)])


def _re_parts(theta, Z, y, off, cl, n_cl):
    """Log likelihood, per-cluster scores and the pieces of the Poisson-gamma random-effects model.

    u_i ~ Gamma(a, 1/a) (mean 1, variance 1/a), y_it | u_i ~ Poisson(u_i μ_it), μ = exp(off + Z b). With
    Y_i = Σ_t y_it, M_i = Σ_t μ_it: ll_i = Σ_t [y log μ − log y!] + lgamma(Y_i + a) − lgamma(a) + a log a −
    (Y_i + a) log(M_i + a). Scores: ∂/∂b = Σ_t y z − (Y + a)/(M + a) Σ_t μ z;
    ∂/∂log a = a [ψ(Y + a) − ψ(a) + log a + 1 − log(M + a) − (Y + a)/(M + a)].
    """
    import math

    b, la = theta[:-1], theta[-1]
    if not np.isfinite(la) or abs(la) > 50:
        raise ValueError("diverged")
    a = math.exp(la)
    eta = off + Z @ b
    if np.max(np.abs(eta - off)) > 30:
        raise ValueError("diverged")
    mu = np.exp(eta)
    Y = np.bincount(cl, weights=y, minlength=n_cl)
    M = np.bincount(cl, weights=mu, minlength=n_cl)
    ratio = (Y + a) / (M + a)
    lg = np.array([math.lgamma(v + a) for v in Y]) - math.lgamma(a)
    ll = float(np.sum(y * eta) + lg.sum() + n_cl * a * la - np.sum((Y + a) * np.log(M + a)))
    sz = np.zeros((n_cl, Z.shape[1]))
    np.add.at(sz, cl, Z * (y - ratio[cl] * mu)[:, None])
    psi = np.array([np.sum(1.0 / (a + np.arange(int(round(v))))) for v in Y])  # ψ(Y + a) − ψ(a)
    sa = a * (psi + la + 1 - np.log(M + a) - ratio)
    return ll, np.hstack([sz, sa[:, None]]), mu, ratio


def _damped_newton_step(theta, g, H, ll_old, loglik, max_damping: int = 20):
    """(step, step length, new log likelihood) for a safeguarded Newton ascent: solve (−H + λI) step = g with
    λ = 0 first and then rising (Levenberg damping, scaled by the largest |H_jj|), accepting the first
    direction that goes uphill (g·step > 0) and, after halving the step at most 30 times, raises the log
    likelihood. Returns (None, 0, ll_old) if no damping finds an increase. By hand: ll = −(x − 1)², x = 0,
    g = 2, H = −2: the plain Newton step 1 lands on the maximum."""
    scale = max(1.0, float(np.max(np.abs(np.diag(H)))))
    n = len(theta)
    for i in range(max_damping):
        lam = 0.0 if i == 0 else scale * 10.0 ** (i - 8)
        step = np.linalg.lstsq(-H + lam * np.eye(n), g, rcond=None)[0]
        if not np.all(np.isfinite(step)) or float(g @ step) <= 0:
            continue
        s = 1.0
        for _ in range(30):
            try:
                ll_new = loglik(theta + s * step)
            except ValueError:
                ll_new = -np.inf
            if ll_new > ll_old:
                return step, s, ll_new
            s /= 2
    return None, 0.0, ll_old


LOG_A_BOUND = 15.0  # log of the gamma shape: var(u) = e^-15 is no place heterogeneity (held at the bound)


def fit_re(y, X, offset, place, year, names, tol: float = 1e-9, max_iter: int = 100) -> REFit:
    """Poisson-gamma place random effects with state × year fixed effects (the negative binomial panel model
    of Hausman, Hall & Griliches 1984; D-024's fallback, protocol §5.7), by Newton's method on the closed-
    form marginal likelihood (`_re_parts`) with a finite-difference Hessian of the analytic score. Keeps
    places whose counts are all zero (they inform a and the year effects). Regressors collinear with the
    year effects and intercept are dropped. log a is held at `LOG_A_BOUND` when the data show no place
    heterogeneity (Poisson counts), and left out of the step test there. Fails loudly (`EstimationError`) on
    non-convergence or a coefficient beyond ±20."""
    from lotline.calibrate.adu.estimate_adu import COEF_BOUND, EstimationError, _independent_columns

    y = np.asarray(y, dtype=float)
    X = np.asarray(X, dtype=float).reshape(len(y), -1)
    off = np.asarray(offset, dtype=float)
    places, cl = np.unique(np.asarray(place), return_inverse=True)
    years, yi = np.unique(np.asarray(year), return_inverse=True)
    G = np.eye(len(years))[yi][:, 1:]
    base = np.hstack([np.ones((len(y), 1)), G])
    names = list(names)
    Z = np.hstack([X, base])
    dropped = []
    if np.linalg.matrix_rank(Z) < Z.shape[1]:
        keep_cols = _independent_columns(Z, len(names))
        dropped = [f"{n} (collinear with year effects)" for i, n in enumerate(names) if i not in keep_cols]
        names = [names[i] for i in keep_cols]
        Z = np.hstack([X[:, keep_cols], base])
    k = len(names)
    theta = np.zeros(Z.shape[1] + 1)
    theta[k] = np.log(max(y.sum(), 1e-8) / np.exp(off).sum())
    n_cl = len(places)

    def grad(t):
        return _re_parts(t, Z, y, off, cl, n_cl)[1].sum(axis=0)

    ll, converged, it = -np.inf, False, 0
    for it in range(1, max_iter + 1):  # noqa: B007 (reported on the fit)
        try:
            g = grad(theta)
        except ValueError as err:  # |η − offset| > 30 at the current step
            raise EstimationError(f"random-effects fit diverged at iteration {it}") from err
        H = np.empty((len(theta), len(theta)))
        for j in range(len(theta)):
            h = 1e-5 * max(1.0, abs(theta[j]))
            tp, tm = theta.copy(), theta.copy()
            tp[j] += h
            tm[j] -= h
            try:
                H[:, j] = (grad(tp) - grad(tm)) / (2 * h)
            except ValueError as err:
                raise EstimationError(f"random-effects fit diverged at iteration {it}") from err
        H = (H + H.T) / 2
        ll_old = _re_parts(theta, Z, y, off, cl, n_cl)[0]
        step, s, ll_new = _damped_newton_step(
            theta, g, H, ll_old, lambda t: _re_parts(t, Z, y, off, cl, n_cl)[0]
        )
        if step is None:  # no direction raises the likelihood: at a maximum to numerical precision
            converged = abs(float(g @ np.linalg.pinv(-H) @ g)) < 1e-6 * (abs(ll_old) + 1)
            ll = ll_old
            break
        theta = theta + s * step
        at_bound = theta[-1] >= LOG_A_BOUND  # no place heterogeneity left (Poisson counts): hold log a there
        theta[-1] = min(theta[-1], LOG_A_BOUND)
        ll = _re_parts(theta, Z, y, off, cl, n_cl)[0] if at_bound else ll_new
        moved = np.abs(s * step)[:-1] if at_bound else np.abs(s * step)
        if np.max(moved) < tol * 1e3 or abs(ll - ll_old) < tol * (abs(ll) + 1):
            converged = True
            break
    if not converged:
        raise EstimationError(f"random-effects fit did not converge in {it} iterations")
    _, S, mu, ratio = _re_parts(theta, Z, y, off, cl, n_cl)
    info = -H
    coef = theta[:k]
    if not np.all(np.isfinite(theta)) or np.max(np.abs(coef), initial=0) > COEF_BOUND:
        raise EstimationError(f"random-effects coefficients beyond ±{COEF_BOUND} or non-finite")
    return REFit(
        names=names,
        coef=coef,
        params=theta,
        info=info,
        scores=S,
        mu=mu * ratio[cl],
        keep=np.ones(len(y), dtype=bool),
        y=y,
        cluster=np.asarray(place),
        alpha=theta[k] + np.log(ratio),
        gamma=np.r_[0.0, theta[k + 1 : -1]],
        years=years,
        a=float(np.exp(theta[-1])),
        iterations=it,
        converged=True,
        dropped_columns=dropped,
    )


def bootstrap(est_, draws: int = 999, seed: int = 0) -> pd.DataFrame:
    """Wild cluster score bootstrap by place (Webb weights): `estimate_adu.score_bootstrap` for PPML (CR2
    scores), the same one-step draw b* = b̂ + I⁻¹ Σ_g w_g S_g with the random-effects scores otherwise."""
    from lotline.calibrate.adu.estimate_adu import (
        COEF_BOUND,
        WEBB,
        EstimationError,
        aggregate,
        score_bootstrap,
    )

    fit = est_.fit
    if isinstance(fit, NBFit):
        from lotline.calibrate.adu import pooled_adu as pa

        raw = pa.score_bootstrap(fit.pooled, draws=draws, seed=seed).rename(columns=NB_NAMES)
        rows = []
        for _, r in raw.iterrows():
            coef = r[fit.names].to_numpy(dtype=float)
            rows.append({**dict(zip(fit.names, coef, strict=True)), **aggregate(est_, coef)})
        return pd.DataFrame(rows)
    if not isinstance(fit, REFit):
        return score_bootstrap(est_, draws=draws, seed=seed)
    rng = np.random.default_rng(seed)
    I_inv = np.linalg.pinv(fit.info)
    k = len(fit.names)
    rows = []
    for _ in range(draws):
        b = fit.params + I_inv @ (rng.choice(WEBB, size=fit.scores.shape[0]) @ fit.scores)
        coef = b[:k]
        if not np.all(np.isfinite(coef)) or np.max(np.abs(coef), initial=0) > COEF_BOUND:
            raise EstimationError("bootstrap draw diverged (non-finite or beyond the coefficient bound)")
        rows.append({**dict(zip(fit.names, coef, strict=True)), **aggregate(est_, coef)})
    return pd.DataFrame(rows)


def summary(est_, draws: int = 999, seed: int = 0, level: float = 0.90) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(summary table with 90% basic bootstrap intervals, bootstrap draws) for one fit."""
    from lotline.calibrate.adu.estimate_adu import summarize

    boot = bootstrap(est_, draws=draws, seed=seed)
    return summarize(est_, boot, level=level), boot


def overall(est_) -> float:
    from lotline.calibrate.adu.estimate_adu import aggregate

    return aggregate(est_).get("att", np.nan)
