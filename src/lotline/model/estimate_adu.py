"""ADU effect estimated with a staggered-adoption count model (analysis plan D-023, pre-registered).

    E[ADUs_it] = Eligible_it · exp( α_i + γ_t + Σ_{g,k} β_gk · D_it · 1[T_i = g, t − T_i = k]
                                    + Σ_m θ_m · (X_im − X̄_m) · 1[t ≥ T_i] + ρ · (r_t − r̄) · 1[t ≥ T_i]
                                    + δ · MM_it )

- **Poisson pseudo-maximum likelihood (PPML)** with log(eligible parcels) as the offset, place fixed effects
  α_i and year fixed effects γ_t, fitted by iteratively reweighted least squares (`ppml`). Places whose
  counts are
  all zero have no finite fixed effect and carry no information for the other coefficients under Poisson
  fixed effects, so they are dropped (and reported); so are columns that are zero on every place with counts.
- **Wooldridge's extended two-way fixed effects:** one coefficient per adoption cohort g and event time
  k = 0 … 5 (5 = 5 or more years), each scaling the dose D_it (rule grade × coverage, D-021). Not-yet-treated
  and never-treated places are the comparisons; there are no unit trends (protocol §5.6). Event-time effects
  β_k and the overall effect are averages of the cohort cells weighted by the counterfactual expected
  permits in each cell (`aggregate`), so they read as "log of additional permits per permit without the rule".
- **θ** (pre-adoption effect modifiers, centred on the treated places' mean), **ρ** (mortgage rate × treated)
  and **δ** (2–4 units legal by right on the same lot) as in D-023.
- **Inference:** a wild cluster score bootstrap by place (`score_bootstrap`; Kline & Santos 2012): each draw
  re-weights each place's score by a Webb six-point weight and takes one Newton step from the estimate, which
  is fast and valid with few clusters. Randomization inference (`randomization_inference`) permutes adoption
  years among treated places and re-fits.

Only NumPy and pandas. Every equation has a test against simulated panels with known coefficients
(tests/model/test_estimate_adu.py), including a pure common shock that must not be read as a reform effect.
"""

from __future__ import annotations

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
        H_inv = np.linalg.pinv(self.hessian)
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


def relu_separated(Z: np.ndarray, y: np.ndarray, tol: float = 1e-6, max_iter: int = 2000) -> np.ndarray:
    """Observations separated in the sense of Correia, Guimarães & Zylkin (2019), by their iterated
    rectifier: find z = Zγ with z = 0 where y > 0 and z >= 0 where y = 0; observations with z > 0 are
    separated (their MLE is at −∞). Weighted least squares with a large weight on y > 0, the target for y = 0
    observations replaced each round by max(fitted, 0). Returns a boolean mask of separated observations."""
    pos = y > 0
    if pos.all():
        return np.zeros(len(y), dtype=bool)
    sw = np.where(pos, 1e3, 1.0)
    pinv = np.linalg.pinv(Z * sw[:, None])
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
        H = np.linalg.pinv(fit.hessian)
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
# The D-023 design
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
    H_inv = np.linalg.pinv(fit.hessian)
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
    Vi = np.linalg.pinv(V)
    W = float(b @ Vi @ b)
    dev = D - b
    Wb = np.einsum("ij,jk,ik->i", dev, Vi, dev)
    return W, float(np.mean(Wb >= W))


def randomization_inference(panel: pd.DataFrame, permutations: int = 999, seed: int = 0, **design_kw):
    """Permute adoption years among treated places (each keeps its own dose path shifted with it), re-fit,
    and compare the overall effect: p = share of |att_perm| >= |att|."""
    rng = np.random.default_rng(seed)
    base = estimate(panel, **design_kw)
    att = aggregate(base).get("att", np.nan)
    treated = panel.loc[panel["T"].notna(), ["place", "T"]].drop_duplicates("place")
    places, Ts = treated["place"].to_numpy(), treated["T"].to_numpy()
    out = []
    for _ in range(permutations):
        perm = dict(zip(places, rng.permutation(Ts), strict=True))
        p = panel.copy()
        newT = p["place"].map(perm)
        p["T"] = newT.where(p["place"].isin(places), p["T"])
        out.append(aggregate(estimate(p, **design_kw)).get("att", np.nan))  # EstimationError propagates
    dist = np.array(out, dtype=float)
    dist = dist[~np.isnan(dist)]
    return att, float(np.mean(np.abs(dist) >= abs(att))) if len(dist) else np.nan, dist


# ---------------------------------------------------------------------------------------------------------
# Panel from the processed tables (D-023 data section)
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


def nearest_roll(e: pd.DataFrame, y) -> float:
    """Eligible parcels of one place in year `y`: the latest roll at or before `y`, else the earliest roll
    after it (`e`: rows of `eligible_parcels` for one place, theme and rule version). NaN if there are none.
    By hand: rolls 2012 = 10, 2018 = 20; year 2015 -> 10, 2010 -> 10, 2020 -> 20."""
    if e.empty:
        return np.nan
    ey = e.assign(after=e["year"] > y, gap=(e["year"] - y).abs()).sort_values(["after", "gap"])
    return float(ey["eligible_parcels"].iloc[0])


@dataclass
class Panel:
    data: pd.DataFrame
    excluded_no_rule: list
    excluded_holdout: list
    notes: list


def build_panel(state: str, store, years=range(2016, 2026), geoids=None, source: str | None = None) -> Panel:
    """The D-023 estimation panel for one state from processed, holdout-filtered tables.

    Places: `geoids`, or every place in permit source `source` (Twin Cities: 'metc_residential_permits').
    St. Paul is excluded entirely; places with no dated ADU rule are left out (and listed). Columns: place,
    name, year, y (ADU permits; the larger source per year), eligible (ADU rule 1.1, nearest roll), T
    (adoption year: first year a rule with P(by right) >= 0.5 is in force on 1 July; NaN if never), dose
    (D_it), rate (national 30-year mean), mm, the pre-adoption modifiers (`MODIFIERS`, measured in year
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
                bps["units_1"].get((g, yy), np.nan) / nearest_roll(e, yy) * 1000
                for yy in (y0 - 2, y0 - 1, y0)
            ]
            pre = [x for x in pre if not np.isnan(x)]
            mods["pre_permits"] = float(np.mean(pre)) if pre else np.nan
            a, b = hh.get((geo, max(y0, 2015)), np.nan), hh.get((geo, max(y0, 2015) - 5), np.nan)
            mods["hh_growth"] = float(np.log(a / b)) if a and b and a > 0 and b > 0 else np.nan
            if y0 < 2010:
                notes.append(f"{g}: adopted {int(T)}; modifiers measured from 2010 on (after adoption)")
        for y, (dose, _) in zip(years, per_year, strict=True):
            rows.append(
                {
                    "place": g,
                    "name": juris["name"].get(g, g),
                    "year": int(y),
                    "y": int(counts.get((g, int(y)), 0)),
                    "eligible": nearest_roll(e, y),
                    "T": T,
                    "dose": dose,
                    "rate": float(rate.get(int(y), np.nan)),
                    "mm": mm_in_force(reforms, g, fips, pd.Timestamp(f"{int(y)}-07-01"), mm_share),
                    "units_5p": float(bps["units_5p"].get((g, int(y)), 0.0)),
                    **mods,
                }
            )
    data = pd.DataFrame(rows)
    return Panel(data, no_rule, held, notes)


# ---------------------------------------------------------------------------------------------------------
# Checks (D-023, causal diagram §5)
# ---------------------------------------------------------------------------------------------------------


def _att_interval(est_, draws, seed):
    s = summarize(est_, score_bootstrap(est_, draws=draws, seed=seed)).set_index("term")
    return s


def check_leads(panel, draws=999, seed=0, **kw) -> dict:
    """1. Pre-trend leads k = −3…−1 jointly zero at the 10% level (pass: p >= 0.10)."""
    e = estimate(panel, leads=(-3, -2, -1), **kw)
    boot = score_bootstrap(e, draws=draws, seed=seed)
    W, p = joint_wald(boot, e, ["lead_3", "lead_2", "lead_1"])
    return {"check": "pre-trend leads", "statistic": W, "p": p, "pass": bool(p >= 0.10)}


def check_placebo_dates(panel, shift=2, draws=999, seed=0, **kw) -> dict:
    """2. Adoption dates moved `shift` years early, using only years before the real adoption for treated
    places: the placebo overall effect's 90% interval contains 0 (pass)."""
    p = panel[(panel["T"].isna()) | (panel["year"] < panel["T"])].copy()
    p["T"] = p["T"] - shift
    p.loc[p["T"].notna(), "dose"] = 1.0
    s = _att_interval(estimate(p, **kw), draws, seed)
    lo, hi = s.loc["att", "low"], s.loc["att", "high"]
    return {
        "check": f"placebo dates (−{shift} years)",
        "estimate": s.loc["att", "estimate"],
        "low": lo,
        "high": hi,
        "pass": bool(lo <= 0 <= hi),
    }


def check_placebo_outcome(panel, draws=999, seed=0, **kw) -> dict:
    """3. Permits in 5+ unit buildings as the outcome: the overall effect's 90% interval contains 0 (pass)."""
    p = panel.assign(y=panel["units_5p"].round().astype(int))
    s = _att_interval(estimate(p, **kw), draws, seed)
    lo, hi = s.loc["att", "low"], s.loc["att", "high"]
    return {
        "check": "placebo outcome (5+ units)",
        "estimate": s.loc["att", "estimate"],
        "low": lo,
        "high": hi,
        "pass": bool(lo <= 0 <= hi),
    }


def check_excluding(panel, main: pd.DataFrame, years=(2020, 2021), draws=999, seed=0, **kw) -> dict:
    """4. Excluding `years`: every event-time effect and the overall effect stay inside the main 90%
    intervals (`main` = summarize() of the main fit)."""
    s = _att_interval(estimate(panel[~panel["year"].isin(years)], **kw), draws, seed)
    m = main.set_index("term")
    terms = [t for t in s.index if t.startswith("beta_") or t == "att"]
    outside = [
        t for t in terms if t in m.index and not (m.loc[t, "low"] <= s.loc[t, "estimate"] <= m.loc[t, "high"])
    ]
    return {"check": f"excluding {years}", "outside": outside, "pass": not outside}


def check_leave_one_out(panel, main: pd.DataFrame, **kw) -> dict:
    """5. Leaving out each treated place: the overall effect stays inside the main 90% interval."""
    m = main.set_index("term").loc["att"]
    moved = []
    for place in panel.loc[panel["T"].notna(), "place"].unique():
        att = aggregate(estimate(panel[panel["place"] != place], **kw)).get("att", np.nan)
        if not (m["low"] <= att <= m["high"]):
            moved.append((place, att))
    return {"check": "leave one treated place out", "moved": moved, "pass": not moved}


# ---------------------------------------------------------------------------------------------------------
# Transport test (D-023): predict places outside Minnesota from the Minnesota estimates
# ---------------------------------------------------------------------------------------------------------


def overdispersion(est_: Estimate) -> float:
    """Moment estimate of κ in Var(y) = μ + κμ² from the fitted model (0 = Poisson)."""
    f = est_.fit
    return max(0.0, float(np.sum((f.y - f.mu) ** 2 - f.y) / np.sum(f.mu**2)))


def transport_predict(
    est_: Estimate,
    boot: pd.DataFrame,
    target: pd.DataFrame,
    draws: int = 4000,
    seed: int = 0,
    widening: float = 1.0,
    window: dict | None = None,
) -> pd.DataFrame:
    """Predicted ADU permits per year for places outside the estimation panel (D-023 transport test).

    For each target place: its own pre-adoption modifiers (centred on Minnesota's treated mean), event-time
    effects β_k (aggregated, per bootstrap draw) × its dose, θ, ρ and δ draws, Minnesota year effects γ_t, and
    a place level α: from the place's own pre-adoption years where it has any (given γ and offset), else a
    draw from the Minnesota places' α distribution. A level from the place's own years carries its sampling
    error (variance ≈ (1 + κ·mean count) / pre-period permits). Places outside the Minnesota modifier range
    get extra
    log-normal noise (sd = `widening` × summed distance outside the range, logs for pcr, pre_permits and
    value, Minnesota sd units for hh_growth). Counts: Poisson-gamma with the panel's overdispersion.
    Returns place, year, observed, mean, p10, p90, p05, p95, outside_range (distance).
    """
    rng = np.random.default_rng(seed)
    f = est_.fit
    years = {int(y): g for y, g in zip(sorted(est_.panel.loc[f.keep, "year"].unique()), f.gamma, strict=True)}
    kappa = overdispersion(est_)
    treated = est_.panel[est_.panel["T"].notna()].drop_duplicates("place")
    mods = [n.replace("theta_", "") for n in f.names if n.startswith("theta_")]
    scale = {m: modifier_scale(treated, m) for m in mods}
    rng_mod = {
        m: (float(treated[m].min()), float(treated[m].max()), float(treated[m].std(ddof=1))) for m in mods
    }
    rate_ref = float(est_.panel["rate"].mean())
    alphas = f.alpha
    b_idx = rng.integers(0, len(boot), size=draws)
    out = []
    for place, d in target.groupby("place", sort=False):
        d = d.sort_values("year")
        T = d["T"].iloc[0]
        e = d["year"].to_numpy() - T if not np.isnan(T) else np.full(len(d), -1.0)
        post = (e >= 0).astype(float)
        gam = np.array([years.get(int(y), max(years.values())) for y in d["year"]])
        dist = 0.0
        for m in mods:
            x = d[m].iloc[0]
            lo, hi, sd = rng_mod[m]
            if np.isnan(x):
                continue
            if m == "hh_growth":
                dist += max(0.0, (lo - x) / sd, (x - hi) / sd)
            else:
                xv, lov, hiv = (np.exp(x), np.exp(lo), np.exp(hi)) if m == "log_value" else (x, lo, hi)
                if xv > 0 and lov > 0:
                    dist += max(0.0, np.log(lov / xv), np.log(xv / hiv))
        pre = d[post == 0]
        if len(pre) and pre["y"].sum() > 0:
            a_hat = np.log(pre["y"].sum() / np.sum(pre["eligible"] * np.exp(gam[post == 0])))
            # sampling error of a level estimated from Y pre-period permits: var ≈ (1 + κ·mean μ) / Y
            y_pre = float(pre["y"].sum())
            mu_pre = y_pre / len(pre)
            a_draw = a_hat + rng.normal(0.0, np.sqrt((1 + kappa * mu_pre) / y_pre), size=draws)
        else:
            a_draw = rng.choice(alphas, size=draws)
        sims = np.zeros((draws, len(d)))
        for i in range(draws):
            row = boot.iloc[b_idx[i]]
            eta = a_draw[i] + gam + np.log(d["eligible"].to_numpy())
            for t in range(len(d)):
                if post[t]:
                    k = int(min(e[t], K_MAX))
                    eta[t] += row.get(f"beta_{k}", 0.0) * d["dose"].iloc[t]
                    for m in mods:
                        x = d[m].iloc[0]
                        c, sd = scale[m]
                        eta[t] += row.get(f"theta_{m}", 0.0) * (0.0 if np.isnan(x) else (x - c) / sd)
                    eta[t] += row.get("rho", 0.0) * (d["rate"].iloc[t] - rate_ref)
                eta[t] += row.get("delta", 0.0) * d["mm"].iloc[t]
            s = widening * dist
            log_rate = eta - np.log(d["eligible"].to_numpy())
            if not np.all(np.isfinite(log_rate)) or np.max(log_rate) > np.log(MAX_YEARLY_RATE):
                raise EstimationError(
                    f"transport for {place}: predicted ADU rate beyond {MAX_YEARLY_RATE:.0%} of "
                    "eligible parcels a year (or non-finite)"
                )
            mu = np.exp(eta + s * rng.standard_normal() - s**2 / 2)
            lam = rng.gamma(1 / kappa, mu * kappa) if kappa > 0 else mu
            sims[i] = rng.poisson(lam)
        lo_y, hi_y = (window or {}).get(place, (-np.inf, np.inf))
        scored = ((d["year"] >= lo_y) & (d["year"] <= hi_y)).to_numpy()
        for t, (_, r) in enumerate(d.iterrows()):
            if not scored[t]:
                continue
            col = sims[:, t]
            out.append(
                {
                    "place": place,
                    "name": r.get("name", place),
                    "year": int(r["year"]),
                    "observed": int(r["y"]),
                    "mean": col.mean(),
                    "p05": np.quantile(col, 0.05),
                    "p10": np.quantile(col, 0.10),
                    "p90": np.quantile(col, 0.90),
                    "p95": np.quantile(col, 0.95),
                    "outside_range": dist,
                }
            )
        tot = sims[:, scored].sum(axis=1)
        out.append(
            {
                "place": place,
                "name": d["name"].iloc[0] if "name" in d else place,
                "year": "total",
                "observed": int(d["y"].to_numpy()[scored].sum()),
                "mean": tot.mean(),
                "p05": np.quantile(tot, 0.05),
                "p10": np.quantile(tot, 0.10),
                "p90": np.quantile(tot, 0.90),
                "p95": np.quantile(tot, 0.95),
                "outside_range": dist,
            }
        )
    return pd.DataFrame(out)


MAX_YEARLY_RATE = 0.05  # a mean above 5% of eligible parcels adding an ADU in one year is absurd: fail


def transport_verdict(pred: pd.DataFrame) -> dict:
    """D-023 pass rule: every place's observed total inside its 80% interval (P10-P90), and the share of
    yearly observations inside their 80% intervals between 60% and 95%."""
    tot = pred[pred["year"] == "total"]
    yearly = pred[pred["year"] != "total"]
    totals_ok = bool(((tot["observed"] >= tot["p10"]) & (tot["observed"] <= tot["p90"])).all())
    cov = float(((yearly["observed"] >= yearly["p10"]) & (yearly["observed"] <= yearly["p90"])).mean())
    return {
        "totals_inside_80": totals_ok,
        "yearly_coverage_80": cov,
        "pass": bool(totals_ok and 0.60 <= cov <= 0.95),
    }
