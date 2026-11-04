"""Residual audit of the ADU calibration fit (analysis plan D-045).

Pure functions: expected counts from a fitted model, log ratios, the place effect's posterior mean, group
ratios, a within-state shape slope with a place bootstrap, and the noise floor of a predictive distribution.
The script `scripts/dev/fit_audit.py` reads the data and writes the tables.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from lotline.model import calibrate_adu as cal

Z_90 = 1.6448536269514722  # two-sided 90%


def expected_by_year(pl: cal.PlaceData, fit: cal.Fit3) -> np.ndarray:
    """E[y_t] = θ̂ Σ_c w_c k_ct (place effect at its mean 1, blank-field combinations by their weights)."""
    ks = pl.k(cal._cvals(fit.m_owner, fit.m_other))
    w = pl.w / pl.w.sum()
    return fit.theta * (w[:, None] * ks).sum(axis=0)


def log_ratio(y, e):
    """ln((Y + 0.5) / (E + 0.5)): finite at zero counts. By hand, Y = 9.5, E = 4.5: ln 2."""
    return np.log((np.asarray(y, dtype=float) + 0.5) / (np.asarray(e, dtype=float) + 0.5))


def posterior_u(y_total, e_total, alpha: float):
    """Posterior mean of the place effect u ~ Gamma(mean 1, variance α) given Y ~ Poisson(u E):
    (Y + r) / (r + E), r = 1/α. α = 0 gives 1. By hand, Y = 10, E = 4, α = 0.5: (10 + 2) / (2 + 4) = 2."""
    y, e = np.asarray(y_total, dtype=float), np.asarray(e_total, dtype=float)
    if alpha <= 0:
        return np.ones_like(e)
    r = 1.0 / alpha
    return (y + r) / (r + e)


def group_ratios(df: pd.DataFrame, by: str, obs: str = "observed", exp: str = "expected") -> pd.DataFrame:
    """ΣY / ΣE by group, with the counts behind it."""
    g = df.groupby(by, dropna=False).agg(places=(obs, "size"), observed=(obs, "sum"), expected=(exp, "sum"))
    return g.assign(ratio=g["observed"] / g["expected"]).reset_index()


def fe_slope(lr, x, groups, w) -> float:
    """Weighted least-squares slope of lr on x with one intercept per group (fixed effects): x and lr are
    demeaned within groups (weighted), then slope = Σ w x̃ l̃ / Σ w x̃². By hand, two groups each with
    x = (0, 1), lr = (0, 2) and (5, 7), equal weights: slope 2."""
    d = pd.DataFrame({"lr": lr, "x": x, "g": groups, "w": w}).astype({"lr": float, "x": float, "w": float})
    for c in ("lr", "x"):
        m = (d[c] * d["w"]).groupby(d["g"]).transform("sum") / d["w"].groupby(d["g"]).transform("sum")
        d[c] = d[c] - m
    den = float((d["w"] * d["x"] ** 2).sum())
    return float((d["w"] * d["x"] * d["lr"]).sum() / den) if den > 0 else float("nan")


def bootstrap_slope(lr, x, groups, w, n: int = 2000, seed: int = 0) -> tuple[float, float, float]:
    """(slope, 5th, 95th percentile) with places resampled within their group, `n` times."""
    d = pd.DataFrame({"lr": lr, "x": x, "g": groups, "w": w}).reset_index(drop=True)
    est = fe_slope(d["lr"], d["x"], d["g"], d["w"])
    rng = np.random.default_rng(seed)
    idx = [np.flatnonzero(d["g"].to_numpy() == g) for g in d["g"].unique()]
    out = np.empty(n)
    for b in range(n):
        take = np.concatenate([rng.choice(i, size=len(i), replace=True) for i in idx])
        s = d.iloc[take]
        out[b] = fe_slope(s["lr"], s["x"], s["g"], s["w"])
    lo, hi = np.nanpercentile(out, [5, 95])
    return est, float(lo), float(hi)


def iqr_effect(slope: float, x) -> float:
    """The ratio across the covariate's interquartile range: exp(slope × (Q3 − Q1))."""
    q1, q3 = np.percentile(np.asarray(x, dtype=float), [25, 75])
    return math.exp(slope * (q3 - q1))


def noise_floor(totals) -> tuple[float, float]:
    """For predictive draws of a state total, read as possible observed values under a correct model: the
    share of draws D-040 would call useful (inside the draws' P10-P90 and within ×2 of their P50), and the RMS
    of ln((draw + 0.5) / (P50 + 0.5)), the K1 a correct model gives for that state. By hand, draws 1, 2,
    ..., 10 (P10 1.9, P50 5.5, P90 9.1): useful are 3 to 9, so 0.7."""
    t = np.asarray(totals, dtype=float)
    lo, med, hi = np.percentile(t, [10, 50, 90])
    useful = (t >= lo) & (t <= hi) & (t > 0) & (t >= med / 2) & (t <= 2 * med)
    rms = float(np.sqrt(np.mean(log_ratio(t, med) ** 2)))
    return float(useful.mean()), rms
