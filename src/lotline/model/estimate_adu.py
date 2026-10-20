"""ADU effect of a by-right rule: the D-026 imputation estimator (primary) and the D-023 extended two-way
fixed-effects PPML (robustness).

**D-026 (analysis plan; supersedes D-023's primary estimator).** Imputation (Borusyak, Jaravel & Spiess
2024) on the additive scale:

    untreated model, fitted on untreated place-years only:  E[y_it(0)] = Eligible_it · exp(α_i + γ_t + λ'Z_it)
    ATT_k = 1,000 · Σ_{t − T_i ∈ k} (y_it − μ̂0_it) / Σ_{t − T_i ∈ k} Eligible_it,   k ∈ {0–1, 2–3, 4+}

- Untreated place-years: never-treated places, and treated places before T_i. Places treated in or before
  the panel's first year, and treated places with no kept untreated year (e.g. no ADU before adoption), are
  excluded and listed (`impute`); they are never controls.
- Z: the replaced ADU rule's dose (carried forward from T − 1 in treated years), parking, process and
  missing-middle reforms.
- Inference: randomization inference that moves each place's dose path with its adoption year
  (`randomization_inference`, primary); a stratified place bootstrap for the range (`place_bootstrap`).
- Checks (`check_*`): held-out pre-trends, anticipation at the announcement year, placebo dates and outcome,
  excluding 2020–21, leave one treated place out, first ring of neighbours excluded.

**D-023 (kept as the robustness estimator, and to show its failing regimes in the tests).** PPML with place
and year fixed effects and cohort × event-time cells scaled by the dose (`build_design`, `estimate`,
`aggregate`), with a wild cluster score bootstrap (`score_bootstrap`). `ppml` (with separation handling and
numerical guards) is shared by both.

Only NumPy and pandas. Every equation has a test against simulated panels with known effects
(tests/model/test_estimate_adu.py), including each regime that broke the D-023 estimator.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

K_MAX = 5  # event time 5 = 5 or more years after adoption
WEBB = np.array([-np.sqrt(1.5), -1.0, -np.sqrt(0.5), np.sqrt(0.5), 1.0, np.sqrt(1.5)])


# ---------------------------------------------------------------------------------------------------------
# PPML with two-way fixed effects
# ---------------------------------------------------------------------------------------------------------


@dataclass
class PPMLFit:
    """A fitted PPML model. `coef` and `names` cover the regressors X; `alpha`, `gamma` the fixed effects."""

    names: list[str]
    coef: np.ndarray
    alpha: np.ndarray  # place effects (for kept places)
    gamma: np.ndarray  # year effects (first year = 0)
    mu: np.ndarray  # fitted means for the kept rows
    keep: np.ndarray  # boolean mask of kept rows in the input
    design: np.ndarray  # full design [X | place dummies | year dummies (drop first)] for kept rows
    y: np.ndarray
    cluster: np.ndarray
    dropped_places: list = field(default_factory=list)
    dropped_columns: list = field(default_factory=list)
    iterations: int = 0
    converged: bool = True

    def coef_of(self, name: str) -> float:
        return float(self.coef[self.names.index(name)])

    @property
    def hessian(self) -> np.ndarray:
        return self.design.T @ (self.mu[:, None] * self.design)

    def cluster_scores(self, adjust: str = "cr2") -> np.ndarray:
        """(clusters × parameters) Poisson scores X_g'(y_g − μ_g) per cluster.

        `adjust="cr2"` (default) rescales each cluster's Pearson residuals by (I − H_gg)^(−1/2), H_gg the
        cluster's block of the weighted hat matrix (Bell-McCaffrey / Pustejovsky-Tipton CR2), using a
        generalized inverse where a place's own fixed effect makes I − H_gg singular. Without it ("cr0") the
        sandwich runs ~10-15% low on simulated panels with one fixed effect per cluster.
        """
        codes, inv = np.unique(self.cluster, return_inverse=True)
        out = np.zeros((len(codes), self.design.shape[1]))
        if adjust == "cr0":
            np.add.at(out, inv, self.design * (self.y - self.mu)[:, None])
            return out
        H_inv = _pinv(self.hessian)
        sw = np.sqrt(self.mu)
        for g in range(len(codes)):
            rows = inv == g
            Xg = self.design[rows] * sw[rows, None]  # W^(1/2) X
            e = (self.y[rows] - self.mu[rows]) / sw[rows]  # Pearson residuals
            M = np.eye(rows.sum()) - Xg @ H_inv @ Xg.T
            vals, vecs = np.linalg.eigh((M + M.T) / 2)
            inv_sqrt = np.where(vals > 1e-8, 1 / np.sqrt(np.clip(vals, 1e-8, None)), 0.0)
            e_adj = vecs @ (inv_sqrt * (vecs.T @ e))
            out[g] = Xg.T @ e_adj
        return out


class EstimationError(RuntimeError):
    """The estimate is not usable (non-convergence, divergence, degenerate standard errors): fail loudly."""


ETA_BOUND = 30.0  # |η − offset| above this means a rate of e^30 per parcel: divergence
COEF_BOUND = 20.0  # |coefficient| above this on the log scale means divergence
SE_FLOOR = 1e-7  # an SE below SE_FLOOR × max(1, |b|) is effectively zero


def _pinv(A: np.ndarray) -> np.ndarray:
    """Pseudo-inverse; LAPACK's divide-and-conquer SVD occasionally fails to converge on a finite, full-rank
    matrix, and the transpose then usually succeeds (pinv(A) = pinv(Aᵀ)ᵀ)."""
    try:
        return np.linalg.pinv(A)
    except np.linalg.LinAlgError:
        return np.linalg.pinv(A.T).T


def relu_separated(Z: np.ndarray, y: np.ndarray, tol: float = 1e-6, max_iter: int = 2000) -> np.ndarray:
    """Observations separated in the sense of Correia, Guimarães & Zylkin (2019), by their iterated
    rectifier: find z = Zγ with z = 0 where y > 0 and z >= 0 where y = 0; observations with z > 0 are
    separated (their MLE is at −∞). Weighted least squares with a large weight on y > 0, the target for y = 0
    observations replaced each round by max(fitted, 0). Returns a boolean mask of separated observations."""
    pos = y > 0
    if pos.all():
        return np.zeros(len(y), dtype=bool)
    sw = np.where(pos, 1e3, 1.0)
    pinv = _pinv(Z * sw[:, None])
    u = np.where(pos, 0.0, 1.0)
    for _ in range(max_iter):
        z = Z @ (pinv @ (u * sw))
        z_pos_ok = np.all(np.abs(z[pos]) <= tol) if pos.any() else True
        if z_pos_ok and np.all(z[~pos] >= -tol):
            return (~pos) & (z > tol)
        new = np.where(pos, 0.0, np.maximum(z, 0.0))
        if np.max(np.abs(new - u)) < tol * 1e-2:
            break
        u = new
    z = Z @ (pinv @ (u * sw))
    return (~pos) & (z > 1e-3)


def ppml(
    y,
    X,
    offset,
    place,
    year,
    names: Sequence[str],
    tol: float = 1e-10,
    max_iter: int = 200,
    check: bool = True,
) -> PPMLFit:
    """Poisson pseudo-maximum likelihood with place and year fixed effects, by IRLS.

    E[y] = exp(offset + X b + α_place + γ_year). Before fitting, separation is removed (Correia, Guimarães &
    Zylkin 2019), repeating until nothing changes: places and years with all-zero outcomes are dropped; any
    regressor column of one sign whose non-zero rows all have zero outcomes is dropped with those rows (e.g. a
    cohort × event-time cell with no permits); the iterated-rectifier check (`relu_separated`) drops any
    remaining separated observations. Regressors collinear with the fixed effects are dropped. Every drop is
    recorded on the fit. With `check`, the fit fails loudly (`EstimationError`) if IRLS does not converge, if
    |η − offset| or a coefficient exceeds its bound, or if a coefficient's cluster-robust SE is effectively 0.
    By hand (no regressors): one place, two years, y = (2, 6), offset 0: α = log 2, γ_2 = log 3.
    """
    y0 = np.asarray(y, dtype=float)
    X0 = np.asarray(X, dtype=float).reshape(len(y0), -1)
    off0 = np.asarray(offset, dtype=float)
    place0 = np.asarray(place)
    year0 = np.asarray(year)
    names_all = list(names)
    keep = np.ones(len(y0), dtype=bool)
    cols = np.ones(X0.shape[1], dtype=bool)
    dropped_columns: list[str] = []
    separated: list[tuple] = []

    def fe_matrix(mask):
        _, p_idx = np.unique(place0[mask], return_inverse=True)
        _, y_idx = np.unique(year0[mask], return_inverse=True)
        P = np.eye(p_idx.max() + 1)[p_idx]
        Y = np.eye(y_idx.max() + 1)[y_idx][:, 1:]
        return np.hstack([X0[mask][:, cols], P, Y])

    for _ in range(50):
        changed = False
        for groups in (place0, year0):
            tot = pd.Series(y0[keep]).groupby(groups[keep]).transform("sum").to_numpy()
            zero = np.zeros(len(y0), dtype=bool)
            zero[np.where(keep)[0][tot <= 0]] = True
            if zero.any():
                keep &= ~zero
                changed = True
        for j in np.where(cols)[0]:
            x = X0[keep, j]
            nz = x != 0
            if not nz.any():
                cols[j] = False
                dropped_columns.append(f"{names_all[j]} (no variation left)")
                changed = True
                continue
            one_sign = np.all(x[nz] > 0) or np.all(x[nz] < 0)
            if one_sign and y0[keep][nz].sum() == 0:
                rows = np.where(keep)[0][nz]
                separated += [(place0[r], int(year0[r])) for r in rows]
                keep[rows] = False
                cols[j] = False
                dropped_columns.append(f"{names_all[j]} (all-zero outcome: separated)")
                changed = True
        if changed:
            continue
        sep = relu_separated(fe_matrix(keep), y0[keep])
        if sep.any():
            rows = np.where(keep)[0][sep]
            separated += [(place0[r], int(year0[r])) for r in rows]
            keep[rows] = False
            continue
        break
    dropped_places = sorted(set(place0[~keep]) - set(place0[keep]), key=str)

    y, offset, place, year = y0[keep], off0[keep], place0[keep], year0[keep]
    names = [n for n, c in zip(names_all, cols, strict=True) if c]
    places, p_idx = np.unique(place, return_inverse=True)
    years, y_idx = np.unique(year, return_inverse=True)
    Z = np.hstack([X0[keep][:, cols], np.eye(len(places))[p_idx], np.eye(len(years))[y_idx][:, 1:]])
    rank_cols = list(range(len(names)))
    if np.linalg.matrix_rank(Z) < Z.shape[1]:
        rank_cols = _independent_columns(Z, len(names))
    if len(rank_cols) < len(names):
        dropped_columns += [
            f"{n} (collinear with fixed effects)" for i, n in enumerate(names) if i not in rank_cols
        ]
        keep_cols = list(rank_cols) + list(range(len(names), Z.shape[1]))
        Z = Z[:, keep_cols]
        names = [names[i] for i in rank_cols]

    eta = offset + np.log(max(y.mean(), 1e-8) / np.exp(offset).mean())
    mu = np.exp(eta)
    b = np.zeros(Z.shape[1])
    converged, iterations = False, 0
    dev_old = np.inf
    for iterations in range(1, max_iter + 1):  # noqa: B007 (reported on the fit)
        z = eta - offset + (y - mu) / mu
        w = np.sqrt(mu)
        b, *_ = np.linalg.lstsq(Z * w[:, None], z * w, rcond=None)
        eta = offset + Z @ b
        if check and np.max(np.abs(eta - offset)) > ETA_BOUND:
            raise EstimationError(f"PPML diverged: |eta - offset| = {np.max(np.abs(eta - offset)):.1f}")
        mu = np.exp(np.clip(eta, -700, 700))
        dev = 2 * np.sum(np.where(y > 0, y * np.log(np.where(y > 0, y, 1) / mu), 0.0) - (y - mu))
        if abs(dev_old - dev) <= tol * (abs(dev) + 1):
            converged = True
            break
        dev_old = dev
    k = len(names)
    fit = PPMLFit(
        names,
        b[:k],
        b[k : k + len(places)],
        np.r_[0.0, b[k + len(places) :]],
        mu,
        keep,
        Z,
        y,
        place,
        dropped_places,
        dropped_columns,
        iterations,
        converged,
    )
    fit.years = years
    fit.separated = separated
    if check:
        check_fit(fit)
    return fit


def check_fit(fit: PPMLFit) -> None:
    """Fail loudly if the fit is not usable: no convergence, a coefficient beyond COEF_BOUND, a non-finite
    value, or a cluster-robust SE effectively 0 (SE < SE_FLOOR × max(1, |b|))."""
    if not fit.converged:
        raise EstimationError(f"PPML did not converge in {fit.iterations} iterations")
    if not np.all(np.isfinite(fit.coef)) or not np.all(np.isfinite(fit.mu)):
        raise EstimationError("PPML produced non-finite values")
    big = [(n, c) for n, c in zip(fit.names, fit.coef, strict=True) if abs(c) > COEF_BOUND]
    if big:
        raise EstimationError(f"coefficients beyond ±{COEF_BOUND}: {big}")
    if len(fit.names):
        H = _pinv(fit.hessian)
        S = fit.cluster_scores("cr0")
        se = np.sqrt(np.clip(np.diag(H @ (S.T @ S) @ H)[: len(fit.names)], 0, None))
        tiny = [
            (n, s_)
            for n, s_, c in zip(fit.names, se, fit.coef, strict=True)
            if s_ < SE_FLOOR * max(1, abs(c))
        ]
        if tiny:
            raise EstimationError(f"standard errors effectively zero: {tiny}")


def _independent_columns(Z: np.ndarray, n_test: int) -> list[int]:
    """Indices (< n_test) of the first n_test columns that are linearly independent of the fixed effects and
    of the earlier kept regressors (QR on [fixed effects | regressors])."""
    fe = Z[:, n_test:]
    kept: list[int] = []
    base = fe
    rank = np.linalg.matrix_rank(base)
    for i in range(n_test):
        trial = np.hstack([base, Z[:, [i]]])
        r = np.linalg.matrix_rank(trial)
        if r > rank:
            kept.append(i)
            base, rank = trial, r
    return kept


# ---------------------------------------------------------------------------------------------------------
# The D-023 design (robustness estimator since D-026)
# ---------------------------------------------------------------------------------------------------------


@dataclass
class Design:
    X: np.ndarray
    names: list[str]
    cells: list[tuple[int, int]]  # (cohort, event time) of each cell column, in order
    n_cells: int


def event_time(year, T):
    """t − T_i, NaN where the place is never treated."""
    return np.asarray(year, dtype=float) - np.asarray(T, dtype=float)


def build_design(
    panel: pd.DataFrame,
    modifiers: Sequence[str] = (),
    leads: Sequence[int] = (),
    cohort_cells: bool = True,
    rate_ref: float | None = None,
    use_rate: bool = True,
    use_mm: bool = True,
) -> Design:
    """Regressors for the D-023 model from a panel with columns place, year, T (adoption year, NaN if never),
    dose (D_it), rate (r_t), mm (MM_it) and the place-level `modifiers` (measured before adoption).

    Cohort cells: dose × 1[T = g, t − T = k], k = 0 … K_MAX (K_MAX pools later years); with
    Modifiers enter as z-scores over the treated places (θ per standard deviation).
    `cohort_cells=False`, one column per k pooled over cohorts. `leads` adds 1[t − T = k] for k < 0
    (unscaled), for the pre-trend check. θ: (X − mean over treated places) × 1[t ≥ T]; ρ: (r − r̄) × 1[t ≥
    T] with
    r̄ = `rate_ref` or the panel mean rate; δ: mm.
    """
    t = panel["year"].to_numpy(dtype=float)
    T = panel["T"].to_numpy(dtype=float)
    e = event_time(t, T)
    post = np.nan_to_num((e >= 0).astype(float) * ~np.isnan(e), nan=0.0)
    dose = panel["dose"].to_numpy(dtype=float)
    cols, names, cells = [], [], []
    kk = np.minimum(e, K_MAX)
    if cohort_cells:
        for g in sorted(np.unique(T[~np.isnan(T)])):
            for k in range(0, K_MAX + 1):
                ind = (T == g) & (kk == k)
                if ind.any():
                    cols.append(dose * ind)
                    names.append(f"cell_{int(g)}_{k}")
                    cells.append((int(g), k))
    else:
        for k in range(0, K_MAX + 1):
            ind = kk == k
            if ind.any():
                cols.append(dose * ind)
                names.append(f"beta_{k}")
                cells.append((-1, k))
    n_cells = len(cols)
    for k in leads:
        cols.append((e == k).astype(float))
        names.append(f"lead_{-k}")
    treated_places = panel.loc[~np.isnan(T)].drop_duplicates("place")
    for m in modifiers:
        centre, scale = modifier_scale(treated_places, m)
        x = (panel[m].to_numpy(dtype=float) - centre) / scale
        cols.append(np.nan_to_num(x) * post)
        names.append(f"theta_{m}")
    if use_rate:
        r = panel["rate"].to_numpy(dtype=float)
        ref = float(np.mean(r)) if rate_ref is None else rate_ref
        cols.append((r - ref) * post)
        names.append("rho")
    if use_mm and "mm" in panel:
        cols.append(panel["mm"].to_numpy(dtype=float))
        names.append("delta")
    X = np.column_stack(cols) if cols else np.zeros((len(panel), 0))
    return Design(X, names, cells, n_cells)


def modifier_scale(treated_places: pd.DataFrame, m: str) -> tuple[float, float]:
    """(mean, standard deviation) of a modifier over the treated places that have it: modifiers enter as
    z-scores, so θ is per standard deviation (1 if fewer than two values or no spread)."""
    v = treated_places[m].dropna().to_numpy(dtype=float)
    centre = float(v.mean()) if len(v) else 0.0
    sd = float(v.std(ddof=1)) if len(v) > 1 else 0.0
    return centre, (sd if sd > 0 else 1.0)


@dataclass
class Estimate:
    fit: PPMLFit
    design: Design
    panel: pd.DataFrame


def estimate(panel: pd.DataFrame, **design_kw) -> Estimate:
    """Fit the D-023 model on a panel (columns place, year, y, eligible, T, dose, rate, mm, modifiers)."""
    d = build_design(panel, **design_kw)
    fit = ppml(
        panel["y"],
        d.X,
        np.log(panel["eligible"].to_numpy(dtype=float)),
        panel["place"],
        panel["year"],
        d.names,
    )
    return Estimate(fit, d, panel)


def _cell_weights(est: Estimate, coef: np.ndarray | None = None) -> pd.DataFrame:
    """Counterfactual expected permits (treatment terms switched off) in each cohort-event cell."""
    fit, d = est.fit, est.design
    coef = fit.coef if coef is None else coef
    X = d.X[fit.keep]
    idx = [d.names.index(n) for n in fit.names]
    Xk = X[:, idx]
    treat_cols = [i for i, n in enumerate(fit.names) if n.startswith(("cell_", "beta_", "theta_", "rho"))]
    eta = np.log(fit.mu) - Xk[:, treat_cols] @ coef[treat_cols]
    mu0 = np.exp(eta)
    rows = []
    for j, n in enumerate(fit.names):
        if n.startswith(("cell_", "beta_")):
            on = Xk[:, j] != 0
            rows.append({"name": n, "k": int(n.rsplit("_", 1)[1]), "weight": float(mu0[on].sum())})
    return pd.DataFrame(rows, columns=["name", "k", "weight"])


def aggregate(est: Estimate, coef: np.ndarray | None = None) -> dict[str, float]:
    """Event-time effects β_k and the overall effect: cohort cells averaged with counterfactual-mean weights.

    Returns {'beta_0': …, …, 'beta_5': …, 'att': …} on the log scale (exp(att) − 1 = proportional effect).
    """
    fit = est.fit
    coef = fit.coef if coef is None else coef
    w = _cell_weights(est, coef)
    out = {}
    pos = {n: i for i, n in enumerate(fit.names)}
    for k, g in w.groupby("k"):
        b = np.array([coef[pos[n]] for n in g["name"]])
        out[f"beta_{k}"] = (
            float(np.average(b, weights=g["weight"])) if g["weight"].sum() > 0 else float(b.mean())
        )
    if len(w):
        b = np.array([coef[pos[n]] for n in w["name"]])
        out["att"] = float(np.average(b, weights=w["weight"])) if w["weight"].sum() > 0 else float(b.mean())
    return out


# ---------------------------------------------------------------------------------------------------------
# Inference
# ---------------------------------------------------------------------------------------------------------


def score_bootstrap(est: Estimate, draws: int = 999, seed: int = 0, adjust: str = "cr2") -> pd.DataFrame:
    """Wild cluster score bootstrap by place (Kline & Santos 2012), Webb six-point weights, CR2-adjusted
    cluster scores (`PPMLFit.cluster_scores`).

    Each draw: b* = b̂ + H⁻¹ Σ_g w_g S_g, with S_g place g's score and H the Poisson Hessian; regressor
    coefficients and the aggregated effects (`aggregate`) per draw. Returns one row per draw.
    """
    fit = est.fit
    rng = np.random.default_rng(seed)
    S = fit.cluster_scores(adjust)
    H_inv = _pinv(fit.hessian)
    k = len(fit.names)
    full = np.r_[fit.coef, fit.alpha, fit.gamma[1:]]
    rows = []
    for _ in range(draws):
        wts = rng.choice(WEBB, size=S.shape[0])
        b = full + H_inv @ (wts @ S)
        coef = b[:k]
        if not np.all(np.isfinite(coef)) or np.max(np.abs(coef), initial=0) > COEF_BOUND:
            raise EstimationError("bootstrap draw diverged (non-finite or beyond the coefficient bound)")
        rows.append({**dict(zip(fit.names, coef, strict=True)), **aggregate(est, coef)})
    return pd.DataFrame(rows)


def summarize(est: Estimate, boot: pd.DataFrame, level: float = 0.90) -> pd.DataFrame:
    """Point estimates with percentile-t-free (percentile) intervals from the bootstrap: centred on the
    estimate by reflecting the draws' deviations (basic bootstrap interval)."""
    point = {**dict(zip(est.fit.names, est.fit.coef, strict=True)), **aggregate(est)}
    a = (1 - level) / 2
    rows = []
    for name, v in point.items():
        if name not in boot:
            continue
        dev = boot[name].to_numpy() - v
        lo, hi = np.quantile(dev, [a, 1 - a])
        se = float(np.std(boot[name].to_numpy(), ddof=1))
        rows.append(
            {
                "term": name,
                "estimate": v,
                "se": se,
                "low": v - hi,
                "high": v - lo,
                "p_two_sided": float(np.mean(np.abs(dev) >= abs(v))),
            }
        )
    return pd.DataFrame(rows)


def joint_wald(boot: pd.DataFrame, est: Estimate, terms: Sequence[str]) -> tuple[float, float]:
    """Wald statistic for terms = 0 with the bootstrap covariance, and its p-value against the bootstrap
    distribution of the same statistic centred on the estimate."""
    terms = [t for t in terms if t in boot]
    if not terms:
        return np.nan, np.nan
    b = np.array([est.fit.coef_of(t) for t in terms])
    D = boot[terms].to_numpy()
    V = np.cov(D, rowvar=False).reshape(len(terms), len(terms))
    Vi = _pinv(V)
    W = float(b @ Vi @ b)
    dev = D - b
    Wb = np.einsum("ij,jk,ik->i", dev, Vi, dev)
    return W, float(np.mean(Wb >= W))


# ---------------------------------------------------------------------------------------------------------
# The D-026 design: imputation on the additive scale (primary estimator)
# ---------------------------------------------------------------------------------------------------------

BINS = {"k0_1": (0, 1), "k2_3": (2, 3), "k4p": (4, np.inf)}  # event-time bins of the ATT (D-026)
CONTROLS = ("parking", "process", "mm")  # time-varying non-ADU reforms, used as observed (D-026)
MIN_CONTRIBUTING = 3  # fewer treated places than this: the ATT is reported as not estimable (D-026)


def replaced_rule_dose(panel: pd.DataFrame) -> np.ndarray:
    """The control for the ADU rule a by-right rule replaced (D-026): the dose in force in untreated years,
    and for treated years (t >= T) the place's dose in year T − 1 carried forward, so the effect reads "by
    right versus the rule it replaced". By hand: dose path (0, 1/3, 1/3, 1, 1) over 2016-2020 with T = 2019
    gives (0, 1/3, 1/3, 1/3, 1/3); a never-treated place keeps its own path."""
    out = panel["dose"].to_numpy(dtype=float).copy()
    T = panel["T"].to_numpy(dtype=float)
    year = panel["year"].to_numpy(dtype=float)
    before = panel.loc[panel["year"] == panel["T"] - 1].set_index("place")["dose"]
    treated = ~np.isnan(T) & (year >= T)
    out[treated] = panel.loc[treated, "place"].map(before).fillna(0.0).to_numpy(dtype=float)
    return out


def _bin_of(e: np.ndarray) -> np.ndarray:
    out = np.full(len(e), "", dtype=object)
    for name, (lo, hi) in BINS.items():
        out[(e >= lo) & (e <= hi)] = name
    return out


@dataclass
class Imputation:
    """One D-026 imputation fit. `rows` is the panel (after exclusions) with mu0 (imputed counterfactual for
    treated and held-out rows), treated, held, used (enters the ATT) and bin; `att` holds the overall ATT
    ('att'), ATT_k ('att_k0_1', 'att_k2_3', 'att_k4p') per 1,000 eligible parcels a year, the proportional
    versions ('ratio', 'ratio_k…'), the zero-pre upper bound ('att_upper_zero_pre') and the held-out mean
    residual ('held'); `excluded` lists every excluded place with its reason."""

    fit: PPMLFit
    rows: pd.DataFrame
    att: dict
    excluded: pd.DataFrame
    contributing: list
    per_place: pd.DataFrame

    @property
    def estimable(self) -> bool:
        return len(self.contributing) >= MIN_CONTRIBUTING


def _per_1000(resid, elig) -> float:
    s = float(np.sum(elig))
    return 1000.0 * float(np.sum(resid)) / s if s > 0 else np.nan


def impute(panel: pd.DataFrame, controls: Sequence[str] = CONTROLS, held: str | None = None) -> Imputation:
    """D-026 imputation estimator (Borusyak, Jaravel & Spiess 2024) with a Poisson untreated model.

    1. Places treated in or before the panel's first year have no untreated year: excluded (never controls).
    2. PPML on untreated rows only (never-treated places, treated places before T, minus rows flagged in the
       boolean column `held`): E[y(0)] = Eligible · exp(α_i + γ_t + λ'Z), Z = the replaced-rule dose
       (`replaced_rule_dose`) and the `controls` present in the panel. Separation, collinearity and guards as
       in `ppml`.
    3. μ̂0 for treated and held rows from α̂, γ̂, λ̂. Treated places with no α̂ (no kept untreated year, e.g. no
       ADU before adoption) are excluded and listed; treated rows in a year with no γ̂ are not used.
    4. ATT = 1,000 · Σ (y − μ̂0) / Σ Eligible over used treated rows, overall and by event-time bin; the
       ratio Σ (y − μ̂0) / Σ μ̂0; the upper bound that counts every permit of the zero-pre places as additional.

    By hand: untreated A (2, 4) and B (3, ·) over two years, B treated in year 2 with y = 9, eligible 1,000
    everywhere: α̂_B = log 3 − log 1,000, γ̂_2 = log 2 (from A), μ̂0 = 6, ATT = 1,000 · (9 − 6) / 1,000 = 3.
    """
    p = panel.reset_index(drop=True).copy()
    first = p["year"].min()
    T = p["T"].to_numpy(dtype=float)
    early = p.loc[~np.isnan(T) & (T <= first), "place"].unique()
    excluded = [
        {"place": pl, "reason": f"treated in or before {int(first)} (no untreated year in the panel)"}
        for pl in early
    ]
    p = p[~p["place"].isin(early)].reset_index(drop=True)
    e = event_time(p["year"], p["T"])
    treated = np.nan_to_num(e, nan=-1.0) >= 0
    held_mask = p[held].to_numpy(dtype=bool) & ~treated if held else np.zeros(len(p), dtype=bool)
    untreated = ~treated & ~held_mask
    p["z_rule"] = replaced_rule_dose(p)
    zcols = ["z_rule"] + [c for c in controls if c in p]
    Z = p[zcols].to_numpy(dtype=float)
    names = [f"lambda_{c}" for c in zcols]
    off = np.log(p["eligible"].to_numpy(dtype=float))
    fit = ppml(
        p.loc[untreated, "y"],
        Z[untreated],
        off[untreated],
        p.loc[untreated, "place"],
        p.loc[untreated, "year"],
        names,
    )
    alpha = dict(zip(np.unique(fit.cluster), fit.alpha, strict=True))
    gamma = dict(zip(fit.years, fit.gamma, strict=True))
    lam = np.array([fit.coef_of(n) if n in fit.names else 0.0 for n in names])
    a = p["place"].map(alpha).to_numpy(dtype=float)
    g = p["year"].map(gamma).to_numpy(dtype=float)
    mu0 = np.exp(off + a + g + Z @ lam)
    target = treated | held_mask
    p["mu0"] = np.where(target, mu0, np.nan)
    p["treated"], p["held"] = treated, held_mask
    p["bin"] = np.where(treated, _bin_of(np.nan_to_num(e, nan=-1.0)), "")
    p["used"] = treated & np.isfinite(p["mu0"].to_numpy())

    ever = p.loc[p["T"].notna(), "place"].unique()
    no_alpha = [pl for pl in ever if pl not in alpha]
    excluded += [
        {"place": pl, "reason": "no kept untreated year (e.g. no ADU permit before adoption)"}
        for pl in no_alpha
    ]
    u = p[p["used"]]
    att = {"att": _per_1000(u["y"] - u["mu0"], u["eligible"])}
    for b in BINS:
        ub = u[u["bin"] == b]
        att[f"att_{b}"] = _per_1000(ub["y"] - ub["mu0"], ub["eligible"]) if len(ub) else np.nan
        att[f"ratio_{b}"] = float((ub["y"] - ub["mu0"]).sum() / ub["mu0"].sum()) if len(ub) else np.nan
    att["ratio"] = float((u["y"] - u["mu0"]).sum() / u["mu0"].sum()) if len(u) else np.nan
    z = p[p["place"].isin(no_alpha) & treated]
    att["att_upper_zero_pre"] = _per_1000(
        np.r_[(u["y"] - u["mu0"]).to_numpy(), z["y"].to_numpy()], np.r_[u["eligible"], z["eligible"]]
    )
    h = p[held_mask & np.isfinite(p["mu0"].to_numpy())]
    att["held"] = _per_1000(h["y"] - h["mu0"], h["eligible"]) if len(h) else np.nan
    g_ = u.assign(resid=u["y"] - u["mu0"]).groupby("place")
    per_place = pd.DataFrame(
        {"att_i": 1000.0 * g_["resid"].sum() / g_["eligible"].sum(), "years": g_.size()}
    ).reset_index()
    contributing = sorted(u["place"].unique(), key=str)
    return Imputation(
        fit, p, att, pd.DataFrame(excluded, columns=["place", "reason"]), contributing, per_place
    )


def shift_dose_path(years: np.ndarray, dose: np.ndarray, T_old: float, T_new: float) -> np.ndarray:
    """A place's dose path moved with its adoption year (D-026 randomization inference): dose_new(t) =
    dose_old(t − (T_new − T_old)), held at the first observed value before the panel and the last after it.
    By hand: years 2016-2021, dose (0, 0, 1/3, 1, 1, 1), T 2019 → 2020: (0, 0, 0, 1/3, 1, 1)."""
    order = np.argsort(years)
    y, d = np.asarray(years, dtype=float)[order], np.asarray(dose, dtype=float)[order]
    src = y - (T_new - T_old)
    idx = np.clip(np.searchsorted(y, src), 0, len(y) - 1)
    out = np.empty(len(y))
    out[order] = d[idx]
    return out


def _multiset_permutations(items: list) -> list[tuple]:
    """Distinct orderings of a multiset (e.g. adoption years shared by several places)."""
    if not items:
        return [()]
    out = []
    for v in sorted(set(items)):
        rest = list(items)
        rest.remove(v)
        out += [(v, *tail) for tail in _multiset_permutations(rest)]
    return out


def _n_distinct(items: list) -> int:
    n = math.factorial(len(items))
    for c in pd.Series(items).value_counts():
        n //= math.factorial(int(c))
    return n


@dataclass
class RIResult:
    att: float
    p: float
    dist: np.ndarray
    n_assignments: int
    enumerated: bool

    @property
    def p_min(self) -> float:
        return 1.0 / (self.n_assignments if self.enumerated else len(self.dist) + 1)


def permute_adoption(panel: pd.DataFrame, assignment: dict) -> pd.DataFrame:
    """Panel with new adoption years `assignment` {place: T_new}; each place's dose path moves with its T."""
    p = panel.copy()
    for pl, T_new in assignment.items():
        rows = p["place"] == pl
        T_old = float(p.loc[rows, "T"].iloc[0])
        p.loc[rows, "dose"] = shift_dose_path(
            p.loc[rows, "year"].to_numpy(), p.loc[rows, "dose"].to_numpy(), T_old, float(T_new)
        )
        p.loc[rows, "T"] = float(T_new)
    return p


def randomization_inference(
    panel: pd.DataFrame, permutations: int = 999, seed: int = 0, statistic=None, **kw
) -> RIResult:
    """D-026 primary inference: permute adoption years among the contributing treated places, moving each
    place's whole dose path with its T (`permute_adoption`), re-impute, and compare the overall ATT (or
    `statistic(Imputation)`). All distinct assignments are enumerated when there are at most `permutations`
    of them (p includes the observed one), else `permutations` are drawn and p = (1 + #{|stat*| ≥ |stat|}) /
    (1 + draws). Sharp null: the by-right rule changes no place's permits."""
    stat = statistic or (lambda r: r.att["att"])
    base = impute(panel, **kw)
    obs = stat(base)
    places = base.contributing
    Ts = [float(panel.loc[panel["place"] == pl, "T"].iloc[0]) for pl in places]
    n_assign = _n_distinct(Ts)
    if n_assign <= permutations:
        assigns, enumerated = _multiset_permutations(Ts), True
    else:
        rng = np.random.default_rng(seed)
        assigns, enumerated = [tuple(rng.permutation(Ts)) for _ in range(permutations)], False
    dist = np.array(
        [stat(impute(permute_adoption(panel, dict(zip(places, a, strict=True))), **kw)) for a in assigns],
        dtype=float,
    )
    hits = np.abs(dist[~np.isnan(dist)]) >= abs(obs) - 1e-12
    p = float(hits.mean()) if enumerated else float((1 + hits.sum()) / (1 + len(hits)))
    return RIResult(obs, p, dist, n_assign, enumerated)


def place_bootstrap(panel: pd.DataFrame, draws: int = 999, seed: int = 0, fn=None, **kw) -> pd.DataFrame:
    """Stratified place bootstrap (D-026 range): treated and untreated places resampled separately with
    replacement (each copy its own place), the whole imputation repeated; returns `fn(panel)` (default the
    `impute(...).att` dictionary) per draw."""
    fn = fn or (lambda p: impute(p, **kw).att)
    rng = np.random.default_rng(seed)
    first = panel["year"].min()
    T = panel.drop_duplicates("place").set_index("place")["T"]
    strata = [T.index[T.notna() & (T > first)].to_numpy(), T.index[T.isna()].to_numpy()]
    by_place = {pl: d for pl, d in panel.groupby("place", sort=False)}
    rows = []
    for _ in range(draws):
        parts = []
        for s in strata:
            for j, pl in enumerate(rng.choice(s, size=len(s), replace=True)):
                parts.append(by_place[pl].assign(place=f"{pl}#{j}"))
        rows.append(fn(pd.concat(parts, ignore_index=True)))
    return pd.DataFrame(rows)


def summarize_att(
    res: Imputation, boot: pd.DataFrame, ri: RIResult | None = None, level: float = 0.90
) -> pd.DataFrame:
    """ATT terms with bootstrap SEs and basic intervals (estimate reflected around the draws' deviations), and
    the randomization-inference p for the overall ATT."""
    a = (1 - level) / 2
    rows = []
    for term, v in res.att.items():
        if term not in boot or not np.isfinite(v):
            continue
        d = boot[term].dropna().to_numpy()
        lo, hi = np.quantile(d - v, [a, 1 - a]) if len(d) else (np.nan, np.nan)
        rows.append(
            {
                "term": term,
                "estimate": v,
                "se": float(np.std(d, ddof=1)) if len(d) > 1 else np.nan,
                "low": v - hi,
                "high": v - lo,
                "p_randomization": ri.p if (ri is not None and term == "att") else np.nan,
            }
        )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------------------------------------
# Panel from the processed tables (D-023 data section, D-026 controls)
# ---------------------------------------------------------------------------------------------------------

ST_PAUL = "2758000"  # V5 blind test: never used
MODIFIERS = ("pcr", "log_value", "pre_permits", "hh_growth")


def rule_dose(rubric, coverage: float, field_probs, grades) -> tuple[float, float]:
    """(expected dose, P(by right)) of one coded ADU rule (D-023 grades × coverage, D-021; blanks per D-022).

    Grades: not by right (permit or conditional use) g_p; by right with owner occupancy g_o; by right without
    it g_b. A blank by_right / owner_occ field restricts with its coded share. By hand: by right blank
    (P restricts 0.2), owner occupancy known False, g = (1/3, 2/3, 1), coverage 0.75:
    (0.2·1/3 + 0.8·1)·0.75 = 0.65; P(by right) = 0.8.
    """
    import pandas as pd

    from lotline.model.scenarios import adu

    if adu._no_adus(rubric):
        return 0.0, 0.0
    g_p, g_o, g_b = grades

    def p_restricts(field, restricted_value):
        v = rubric.get(field)
        if v is None or pd.isna(v):
            return field_probs[field]
        return 1.0 if str(v).lower() == str(restricted_value).lower() else 0.0

    p_nbr = p_restricts("by_right", False)
    p_own = p_restricts("owner_occ", True)
    grade = p_nbr * g_p + (1 - p_nbr) * (p_own * g_o + (1 - p_own) * g_b)
    return float(grade * coverage), float(1 - p_nbr)


def _rules_by_year(reforms, all_reforms, geoid, fips, years, coverage, field_probs, grades):
    """Per year: (dose, by-right, any coded row) for one place from its dated ADU rules in force on 1 July."""
    import pandas as pd

    from lotline.model.scenarios import adu

    adu_rows = reforms[(reforms["theme"] == "adu") & (reforms["status"] == "in_force")]
    mine = adu_rows[adu_rows["jurisdiction_geoid"].isin([geoid, fips])]
    out = []
    for y in years:
        mid = pd.Timestamp(f"{int(y)}-07-01")
        live = mine[(mine["effective_date"] <= mid) & (mine["end_date"].isna() | (mine["end_date"] > mid))]
        best_dose, best_br = 0.0, 0.0
        for r in live.itertuples():
            rubric = adu.with_parking(adu._resolved(adu_rows, r.reform_id), all_reforms, geoid, mid)
            d, br = rule_dose(rubric, coverage.get(r.reform_id, 1.0), field_probs, grades)
            best_dose, best_br = max(best_dose, d), max(best_br, br)
        out.append((best_dose, best_br))
    return out, not mine.empty


def mm_in_force(reforms, geoid, fips, date, by_right_share: float) -> float:
    """1 if a coded missing-middle rule allowing 2+ units in single-family zones (unit cap 2+ or blank) is in
    force on `date` and by right (a blank `by_right` counts when coded missing-middle rows are mostly by
    right, `by_right_share` >= 0.5), else 0."""
    import pandas as pd

    r = reforms[(reforms["theme"] == "missing_middle") & (reforms["status"] == "in_force")]
    r = r[r["jurisdiction_geoid"].isin([geoid, fips]) & (r["effective_date"] <= date)]
    r = r[r["end_date"].isna() | (r["end_date"] > date)]
    for row in r.itertuples():
        cap = pd.to_numeric(row.unit_cap, errors="coerce")
        if pd.notna(cap) and cap < 2:
            continue
        br = row.by_right
        if pd.isna(br):
            if by_right_share >= 0.5:
                return 1.0
        elif str(br).lower() == "true":
            return 1.0
    return 0.0


def household_growth(hh: pd.Series, geo: str, T: int) -> float:
    """log(households at T − 1 / households at T − 6) from ACS vintages (Series indexed by (geo, end_year)),
    missing when either vintage is absent: never measured from a later year (D-026, defect 8; D-023 used
    max(T − 1, 2015), so 2011-15 adopters got post-adoption growth). By hand: 1,100 at 2019 over 1,000 at
    2014 for T = 2020 gives log 1.1."""
    a, b = hh.get((geo, T - 1), np.nan), hh.get((geo, T - 6), np.nan)
    return float(np.log(a / b)) if np.isfinite(a) and np.isfinite(b) and a > 0 and b > 0 else np.nan


def announcement_year(reforms, geoid, fips, T: float) -> float:
    """Year a place's first by-right ADU rule was announced (D-026 anticipation check): among ADU rows taking
    effect in the year before 1 July of T, the earliest coded `announced_date`, else `adoption_date`; capped
    at T. NaN if never treated or neither date is coded."""
    if np.isnan(T):
        return np.nan
    r = reforms[(reforms["theme"] == "adu") & reforms["jurisdiction_geoid"].isin([geoid, fips])]
    lo, hi = pd.Timestamp(f"{int(T) - 1}-07-01"), pd.Timestamp(f"{int(T)}-07-01")
    r = r[(r["effective_date"] > lo) & (r["effective_date"] <= hi)]
    dates = []
    for row in r.itertuples():
        d = getattr(row, "announced_date", pd.NaT)
        d = getattr(row, "adoption_date", pd.NaT) if pd.isna(d) else d
        if pd.notna(d):
            dates.append(d)
    return float(min(min(dates).year, int(T))) if dates else np.nan


def process_in_force(reforms, geoid, fips, date) -> float:
    """1 if a coded `process` reform (C21) is in force for the place on `date`, else 0 (D-026 control)."""
    r = reforms[(reforms["theme"] == "process") & (reforms["status"] == "in_force")]
    r = r[r["jurisdiction_geoid"].isin([geoid, fips]) & (r["effective_date"] <= date)]
    return float((r["end_date"].isna() | (r["end_date"] > date)).any())


@dataclass
class Panel:
    data: pd.DataFrame
    excluded_no_rule: list
    excluded_holdout: list
    notes: list


def build_panel(state: str, store, years=range(2016, 2026), geoids=None, source: str | None = None) -> Panel:
    """The D-023/D-026 estimation panel for one state from processed, holdout-filtered tables.

    Places: `geoids`, or every place in permit source `source` (Twin Cities: 'metc_residential_permits').
    St. Paul is excluded entirely; places with no dated ADU rule are left out (and listed). Columns: place,
    name, year, y (ADU permits; the larger source per year), eligible (ADU rule 1.1, nearest roll), T
    (adoption year: first year a rule with P(by right) >= 0.5 is in force on 1 July; NaN if never), dose
    (D_it), rate (national 30-year mean), mm, parking and process (D-026 controls), T_announce
    (`announcement_year`), the pre-adoption modifiers (`MODIFIERS`, measured in year
    T − 1) and units_5p (BPS units in 5+ unit buildings, the placebo outcome).
    """
    from lotline.build import eligible as eligible_rule
    from lotline.config import load_params, load_state
    from lotline.model import hazard, money
    from lotline.model.scenarios import adu

    years = list(years)
    fips = load_state(state).fips
    p = {k: v.value for k, v in load_params("adu").items()}
    grades = (p["adu_dose_grade_permit"], p["adu_dose_grade_owner"], p["adu_dose_grade_by_right"])
    every = pd.concat([adu.load_reforms(st).assign(state=st) for st in adu.REFORM_STATES], ignore_index=True)
    fcounts = adu.field_restrict_counts(every, pd.Timestamp(f"{max(years)}-12-31"))
    fp = adu.field_probabilities(fcounts, state, int(p["adu_rule_min_coded"]))
    mm_rows = every.loc[every["theme"] == "missing_middle", "by_right"].dropna().astype(str).str.lower()
    mm_share = float((mm_rows == "true").mean()) if len(mm_rows) else 0.5
    reforms = adu.load_reforms(state)
    coverage = adu.coverage_map(state, store, reforms, p).set_index("reform_id")["coverage"].to_dict()

    permits = store.read(state, "permits")
    if geoids is None:
        geoids = sorted(permits.loc[permits["source"] == source, "jurisdiction_geoid"].dropna().unique())
    held = [g for g in geoids if g == ST_PAUL]
    geoids = [g for g in geoids if g != ST_PAUL]
    counts = adu.observed_adu_counts(permits, min(years), max(years)).set_index(["geoid", "year"])[
        "adu_permits"
    ]
    juris = store.read(state, "jurisdictions").set_index("geoid")
    elig = store.read(state, "eligible_parcels")
    elig = elig[(elig["theme"] == "adu") & (elig["rule_version"] == eligible_rule.RULE_VERSION)]
    bps = store.read(state, "bps_place_year")
    bps = bps[bps["geoid"].notna()].groupby(["geoid", "year"])[["units_1", "units_5p"]].sum()
    market = store.read(state, "market_geo_year")
    cpi = money.index_by_year(market, "cpi_u")
    rate = market[market["geo"] == money.NATIONAL].set_index("year")["mortgage_rate"]
    cost = hazard.cost_index_by_year(market)
    acs = store.read(state, "acs_geo_year")
    hh = acs[acs["variable"] == "B25003_001"].set_index(["geo", "end_year"])["estimate"]
    central = adu.central_params()

    def eligible_at(e, y):
        if e.empty:
            return np.nan
        ey = e.assign(after=e["year"] > y, gap=(e["year"] - y).abs()).sort_values(["after", "gap"])
        return float(ey["eligible_parcels"].iloc[0])

    rows, no_rule, notes = [], [], []
    for g in geoids:
        per_year, coded = _rules_by_year(reforms, reforms, g, fips, years, coverage, fp, grades)
        if not coded:
            no_rule.append(g)
            continue
        e = elig[elig["jurisdiction_geoid"] == g]
        if e.empty:
            notes.append(f"{g}: no eligible parcels, left out")
            continue
        by_right_years = [y for y, (_, br) in zip(years, per_year, strict=True) if br >= 0.5]
        # adoption year from the full rule history (a by-right rule before the panel's first year counts)
        T = np.nan
        for y in range(1990, max(years) + 1):
            _, br_y = _rules_by_year(reforms, reforms, g, fips, [y], coverage, fp, grades)[0][0]
            if br_y >= 0.5:
                T = float(y)
                break
        if not by_right_years and not np.isnan(T) and T > max(years):
            T = np.nan
        kind = juris["kind"].get(g, "place")
        geo = f"{adu.ACS_PREFIX.get(kind, 'place')}:{g}"
        mods = {m: np.nan for m in MODIFIERS}
        if not np.isnan(T):
            y0 = int(T) - 1
            v = adu.acs_values(acs, pd.Series([geo]), max(y0, 2010), cpi)
            if not v.empty and v[["rent", "home_value"]].notna().all(axis=None):
                v = v.iloc[0]
                ci = cost.get(max(y0, min(cost)), 1.0)
                mods["pcr"] = float(hazard.adu_price_to_cost(v["rent"], params=central, cost_index=ci))
                mods["log_value"] = float(np.log(v["home_value"]))
            pre = [
                bps["units_1"].get((g, yy), np.nan) / eligible_at(e, yy) * 1000 for yy in (y0 - 2, y0 - 1, y0)
            ]
            pre = [x for x in pre if not np.isnan(x)]
            mods["pre_permits"] = float(np.mean(pre)) if pre else np.nan
            mods["hh_growth"] = household_growth(hh, geo, int(T))
            if y0 < 2010:
                notes.append(f"{g}: adopted {int(T)}; modifiers measured from 2010 on (after adoption)")
        T_ann = announcement_year(reforms, g, fips, T)
        for y, (dose, _) in zip(years, per_year, strict=True):
            mid = pd.Timestamp(f"{int(y)}-07-01")
            rows.append(
                {
                    "place": g,
                    "name": juris["name"].get(g, g),
                    "year": int(y),
                    "y": int(counts.get((g, int(y)), 0)),
                    "eligible": eligible_at(e, y),
                    "T": T,
                    "T_announce": T_ann,
                    "dose": dose,
                    "rate": float(rate.get(int(y), np.nan)),
                    "mm": mm_in_force(reforms, g, fips, mid, mm_share),
                    "parking": float(adu.parking_waived(reforms, g, mid)),
                    "process": process_in_force(reforms, g, fips, mid),
                    "units_5p": float(bps["units_5p"].get((g, int(y)), 0.0)),
                    **mods,
                }
            )
    data = pd.DataFrame(rows)
    return Panel(data, no_rule, held, notes)


# ---------------------------------------------------------------------------------------------------------
# Checks (D-026; causal diagram §5)
# ---------------------------------------------------------------------------------------------------------


def _interval(panel, stat: str, draws: int, seed: int, held: str | None = None, **kw) -> dict:
    """Point estimate and basic 90% bootstrap interval of one entry of `impute(...).att`."""
    v = impute(panel, held=held, **kw).att[stat]
    boot = place_bootstrap(panel, draws=draws, seed=seed, fn=lambda p: impute(p, held=held, **kw).att)
    lo, hi = np.quantile(boot[stat].dropna() - v, [0.05, 0.95])
    return {"estimate": v, "low": v - hi, "high": v - lo}


def _contains_zero(name: str, r: dict) -> dict:
    return {"check": name, **r, "pass": bool(r["low"] <= 0 <= r["high"])}


def check_pretrends(panel, leads=(-3, -2, -1), draws=999, seed=0, **kw) -> dict:
    """1. Treated rows at k in `leads` held out of the untreated fit and imputed: their mean y − μ̂0 per 1,000
    parcels has a 90% interval containing 0."""
    e = event_time(panel["year"], panel["T"])
    p = panel.assign(holdout=np.isin(e, leads))
    return _contains_zero(
        "pre-trends (held-out leads)", _interval(p, "held", draws, seed, held="holdout", **kw)
    )


def check_anticipation(panel, main: pd.DataFrame, draws=999, seed=0, **kw) -> dict:
    """2. Anticipation (C29): rows with T_announce <= t < T are held out of the untreated fit and imputed.
    Pass: their mean y − μ̂0 has a 90% interval containing 0, and the overall ATT with the window held out
    stays inside the main 90% interval. (Re-dating T to T_announce would mix zero-effect years into the post
    bins and dilute the ATT mechanically, so the window is held out instead.)"""
    if "T_announce" not in panel:
        return {"check": "anticipation", "pass": None, "note": "not run: no announcement dates"}
    Ta = panel["T_announce"].fillna(panel["T"])
    p = panel.assign(holdout=(panel["year"] >= Ta) & (panel["year"] < panel["T"]))
    if not p["holdout"].any():
        return {"check": "anticipation", "pass": None, "note": "no announcement before the effective year"}
    win = _interval(p, "held", draws, seed, held="holdout", **kw)
    att_held = impute(p, held="holdout", **kw).att["att"]
    m = main.set_index("term").loc["att"]
    inside = bool(m["low"] <= att_held <= m["high"])
    return {
        "check": "anticipation",
        **win,
        "att_window_held_out": att_held,
        "pass": bool(win["low"] <= 0 <= win["high"]) and inside,
    }


def check_placebo_dates(panel, shift=2, draws=999, seed=0, **kw) -> dict:
    """3. Adoption moved `shift` years early on pre-adoption rows only: overall ATT interval contains 0."""
    p = panel[panel["T"].isna() | (panel["year"] < panel["T"])].copy()
    p["T"] = p["T"] - shift
    return _contains_zero(f"placebo dates (−{shift} years)", _interval(p, "att", draws, seed, **kw))


def check_placebo_outcome(panel, draws=999, seed=0, **kw) -> dict:
    """4. Permits in 5+ unit buildings as the outcome: overall ATT interval contains 0."""
    p = panel.assign(y=panel["units_5p"].round().astype(int))
    return _contains_zero("placebo outcome (5+ units)", _interval(p, "att", draws, seed, **kw))


def check_excluding(panel, main: pd.DataFrame, years=(2020, 2021), **kw) -> dict:
    """5. Excluding `years`: the overall ATT and each ATT_k stay inside their main 90% intervals."""
    r = impute(panel[~panel["year"].isin(years)], **kw).att
    m = main.set_index("term")
    terms = ["att"] + [f"att_{b}" for b in BINS]
    outside = [
        t
        for t in terms
        if t in m.index and np.isfinite(r[t]) and not (m.loc[t, "low"] <= r[t] <= m.loc[t, "high"])
    ]
    return {"check": f"excluding {years}", "outside": outside, "pass": not outside}


def check_leave_one_out(panel, main: pd.DataFrame, **kw) -> dict:
    """6. Leaving out each treated place: the overall ATT stays inside the main 90% interval."""
    m = main.set_index("term").loc["att"]
    moved = []
    for pl in impute(panel, **kw).contributing:
        att = impute(panel[panel["place"] != pl], **kw).att["att"]
        if not (m["low"] <= att <= m["high"]):
            moved.append((pl, att))
    return {"check": "leave one treated place out", "moved": moved, "pass": not moved}


def check_first_ring(panel, main: pd.DataFrame, neighbors: dict | None, **kw) -> dict:
    """7. Spillovers (C26): never-treated places sharing a boundary with a treated place (`neighbors`: place →
    set of adjacent places) dropped from the untreated fit; the overall ATT stays inside the main 90%
    interval.
    Not run without adjacency data."""
    if neighbors is None:
        return {"check": "first ring excluded", "pass": None, "note": "not run: no adjacency data"}
    treated = set(panel.loc[panel["T"].notna(), "place"])
    never = set(panel.loc[panel["T"].isna(), "place"])
    ring = {pl for pl in never if set(neighbors.get(pl, ())) & treated}
    att = impute(panel[~panel["place"].isin(ring)], **kw).att["att"]
    m = main.set_index("term").loc["att"]
    return {
        "check": "first ring excluded",
        "dropped": sorted(ring, key=str),
        "att": att,
        "pass": bool(m["low"] <= att <= m["high"]),
    }


# ---------------------------------------------------------------------------------------------------------
# Transport test (D-026): predict places outside Minnesota from the Minnesota estimates
# ---------------------------------------------------------------------------------------------------------

MAX_YEARLY_RATE = 0.05  # a mean above 5% of eligible parcels adding an ADU in one year is absurd: fail


def overdispersion(fit: PPMLFit) -> float:
    """Moment estimate of κ in Var(y) = μ + κμ² from a fitted model (0 = Poisson)."""
    return max(0.0, float(np.sum((fit.y - fit.mu) ** 2 - fit.y) / np.sum(fit.mu**2)))


def year_effect(fit: PPMLFit, year: int) -> float:
    """γ̂ for `year`; outside the panel, the nearest panel year's (2025's for 2026+, D-026; the D-023 code
    used the largest year effect instead)."""
    years = [int(y) for y in fit.years]
    y = min(max(int(year), min(years)), max(years))
    return float(fit.gamma[years.index(y)])


def transport_predict(
    res: Imputation,
    boot: pd.DataFrame,
    target: pd.DataFrame,
    draws: int = 4000,
    seed: int = 0,
    window: dict | None = None,
) -> pd.DataFrame:
    """Predicted ADU permits per year for places outside the estimation panel (D-026 transport test).

    Counterfactual: μ0 = Eligible · exp(α + γ_t + λ'Z), γ_t from Minnesota (`year_effect`), λ the Minnesota
    control coefficients, α from the place's own pre-adoption years (with its sampling error, variance ≈
    (1 + κ·mean count) / pre-period permits) or, with no pre-adoption permits, a draw from the Minnesota α̂.
    Effect: ATT_k (a bootstrap draw) × Eligible / 1,000 in treated years. Counts: Poisson-gamma with the
    untreated fit's overdispersion. Returns place, year, observed, mean, p05, p10, p90, p95 (yearly rows
    within `window` and one 'total' row per place).
    """
    rng = np.random.default_rng(seed)
    f = res.fit
    kappa = overdispersion(f)
    lam = {n.replace("lambda_", ""): c for n, c in zip(f.names, f.coef, strict=True)}
    b_idx = rng.integers(0, len(boot), size=draws)
    att_draws = {b: boot[f"att_{b}"].to_numpy()[b_idx] for b in BINS}
    out = []
    for place, d in target.groupby("place", sort=False):
        d = d.sort_values("year").assign(z_rule=lambda x: replaced_rule_dose(x))
        e = np.nan_to_num(event_time(d["year"], d["T"]), nan=-1.0)
        post = e >= 0
        elig = d["eligible"].to_numpy(dtype=float)
        lin = np.array([year_effect(f, y) for y in d["year"]])
        for c, v in lam.items():
            if c in d:
                lin = lin + v * d[c].to_numpy(dtype=float)
        y_pre = float(d.loc[~post, "y"].sum())
        if y_pre > 0:
            a_hat = np.log(y_pre / np.sum(elig[~post] * np.exp(lin[~post])))
            a_draw = a_hat + rng.normal(0.0, np.sqrt((1 + kappa * y_pre / (~post).sum()) / y_pre), size=draws)
        else:
            a_draw = rng.choice(f.alpha, size=draws)
        mu0 = elig * np.exp(a_draw[:, None] + lin[None, :])
        eff = np.zeros((draws, len(d)))
        bins = _bin_of(e)
        for t in np.where(post)[0]:
            eff[:, t] = att_draws[bins[t]] * elig[t] / 1000.0
        mu = np.clip(mu0 + eff, 0.0, None)
        if not np.all(np.isfinite(mu)) or np.max(mu / elig) > MAX_YEARLY_RATE:
            raise EstimationError(
                f"transport for {place}: predicted ADU rate beyond {MAX_YEARLY_RATE:.0%} of "
                "eligible parcels a year (or non-finite)"
            )
        lam_ = rng.gamma(1 / kappa, mu * kappa) if kappa > 0 else mu
        sims = rng.poisson(lam_)
        lo_y, hi_y = (window or {}).get(place, (-np.inf, np.inf))
        scored = ((d["year"] >= lo_y) & (d["year"] <= hi_y)).to_numpy()
        name = d["name"].iloc[0] if "name" in d else place

        def row(year, observed, col, place=place, name=name):
            q = np.quantile(col, [0.05, 0.10, 0.90, 0.95])
            return {
                "place": place,
                "name": name,
                "year": year,
                "observed": int(observed),
                "mean": col.mean(),
                "p05": q[0],
                "p10": q[1],
                "p90": q[2],
                "p95": q[3],
            }

        out += [
            row(int(y), obs, sims[:, t])
            for t, (y, obs) in enumerate(zip(d["year"], d["y"], strict=True))
            if scored[t]
        ]
        out.append(row("total", d["y"].to_numpy()[scored].sum(), sims[:, scored].sum(axis=1)))
    return pd.DataFrame(out)


def transport_verdict(pred: pd.DataFrame) -> dict:
    """Pass rule (D-023, unchanged by D-026): every place's observed total inside its 80% interval (P10-P90),
    and the share of yearly observations inside their 80% intervals between 60% and 95%."""
    tot = pred[pred["year"] == "total"]
    yearly = pred[pred["year"] != "total"]
    totals_ok = bool(((tot["observed"] >= tot["p10"]) & (tot["observed"] <= tot["p90"])).all())
    cov = float(((yearly["observed"] >= yearly["p10"]) & (yearly["observed"] <= yearly["p90"])).mean())
    return {
        "totals_inside_80": totals_ok,
        "yearly_coverage_80": cov,
        "pass": bool(totals_ok and 0.60 <= cov <= 0.95),
    }
