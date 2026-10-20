"""D-025 pooled model (model/pooled_adu.py): quadrature, recovery on sparse panels (~70% all-zero places),
a common shock, separation, guards, transport and the imputation robustness. Synthetic data only."""

import math

import numpy as np
import pandas as pd
import pytest

from lotline.model import pooled_adu as pa
from lotline.model.estimate_adu import EstimationError

YEARS = np.arange(2016, 2026)
RATE = np.interp(YEARS, [2016, 2020, 2021, 2022, 2025], [3.8, 3.1, 3.0, 5.3, 6.6])
BETA = (0.6, 1.0, 1.2)  # bands 0-1, 2-3, 4+
# Sparse panels (~70% all-zero places, ~50-130 ADU permits) make the intervals approximate: on 70 panels in
# development the overall effect's 90% interval covered 87-97%. Thresholds are set so that an estimator with
# 85% coverage fails a term with probability under 1%, while a broken interval (coverage ~50%) fails.
N_SIMS, MIN_COVERED = 30, 22


def sparse_panel(
    seed=0,
    n_places=160,
    beta=BETA,
    theta=0.4,
    rho=-0.15,
    delta=-0.3,
    shock=0.0,
    kappa=0.5,
    a_mean=-14.0,
    a_sd=1.2,
    share_treated=0.5,
):
    """Places with random effects u ~ N(0, a_sd²) around a low ADU rate, so most places never build one;
    staggered adoption 2017-2022; band effects, a modifier, rate × post, missing middle, year effects
    (with an optional common drop of `shock` from 2022) and negative-binomial counts."""
    rng = np.random.default_rng(seed)
    gamma = 0.05 * (YEARS - 2016) + np.where(YEARS >= 2022, shock, 0.0)
    rows = []
    for i in range(n_places):
        u = rng.normal(0, a_sd)
        eligible = rng.uniform(2_000, 40_000)
        treated = rng.random() < share_treated
        T = float(rng.integers(2017, 2023)) if treated else np.nan
        m1 = rng.normal(0, 1)
        mm_from = 2021 if i % 4 == 0 else 9999
        for y, r, g in zip(YEARS, RATE, gamma, strict=True):
            e = y - T if treated else -99
            band = next((b for b, (lo, hi) in enumerate(pa.BANDS) if lo <= e <= hi), None)
            post = float(treated and e >= 0)
            eta = a_mean + u + g + (beta[band] if band is not None else 0.0) + theta * m1 * post
            eta += rho * (r - RATE.mean()) * post + delta * (y >= mm_from)
            mu = eligible * math.exp(eta)
            lam = rng.gamma(1 / kappa, mu * kappa) if kappa > 0 else mu
            rows.append(
                {
                    "place": f"P{i:03d}",
                    "year": int(y),
                    "eligible": eligible,
                    "T": T,
                    "dose": 1.0,
                    "rate": r,
                    "mm": float(y >= mm_from),
                    "m1": m1,
                    "y": int(rng.poisson(lam)),
                    "units_5p": int(rng.poisson(eligible * 0.0005)),
                }
            )
    return pd.DataFrame(rows)


def test_sparse_panel_is_mostly_all_zero_places():
    p = sparse_panel(seed=0)
    share = (p.groupby("place")["y"].sum() == 0).mean()
    assert 0.6 <= share <= 0.85


def test_quadrature_is_accurate_for_a_skewed_place():
    """A place with many counts far from its prior (the case where 15 nodes were too few): 31-node adaptive
    quadrature matches brute-force integration to 1e-6."""
    p = sparse_panel(seed=1)
    d = pa.build_pooled_design(p, modifiers=["m1"])
    k = d.X.shape[1]
    params = np.r_[np.random.default_rng(0).normal(0, 0.1, k), -0.2, -1.0]
    params[0] = -11.0
    i = int(np.argmax(np.bincount(d.place_idx, d.y)))
    sigma, kappa = math.exp(params[k]), math.exp(params[k + 1])
    r = 1 / kappa
    rows = d.place_idx == i
    eta = d.offset[rows] + d.X[rows] @ params[:k]
    u = np.linspace(-15, 30, 400_001)
    tot = np.zeros_like(u)
    for yi, ei in zip(d.y[rows], eta, strict=True):
        mu = np.exp(ei + u)
        tot += (
            math.lgamma(yi + r)
            - math.lgamma(r)
            - math.lgamma(yi + 1)
            + r * np.log(r / (r + mu))
            + yi * np.log(mu / (r + mu))
        )
    dens = np.exp(tot - 0.5 * (u / sigma) ** 2) / (sigma * math.sqrt(2 * math.pi))
    assert pa.place_logliks(params, d)[i] == pytest.approx(math.log(np.trapezoid(dens, u)), abs=1e-6)


def test_quadrature_matches_brute_force_integration():
    """One place, three years: the adaptive Gauss-Hermite marginal equals a fine-grid integral of
    Π NB(y; μ e^u) φ(u; 0, σ²) to 1e-6."""
    p = pd.DataFrame(
        {
            "place": ["A"] * 3,
            "year": [2016, 2017, 2018],
            "eligible": [1000.0] * 3,
            "T": np.nan,
            "dose": 0.0,
            "rate": 4.0,
            "mm": 0.0,
            "y": [1, 3, 7],
        }
    )
    d = pa.build_pooled_design(p, use_rate=False, use_mm=False)
    k = d.X.shape[1]
    params = np.r_[-5.5, 0.2, 0.5, math.log(0.8), math.log(0.3)]
    assert k == 3
    ll = pa.place_logliks(params, d)[0]
    sigma, kappa = 0.8, 0.3
    r = 1 / kappa
    u = np.linspace(-8, 8, 200_001)
    eta = d.offset + d.X @ params[:k]
    tot = np.zeros_like(u)
    for yi, ei in zip(d.y, eta, strict=True):
        mu = np.exp(ei + u)
        tot += (
            math.lgamma(yi + r)
            - math.lgamma(r)
            - math.lgamma(yi + 1)
            + r * np.log(r / (r + mu))
            + yi * np.log(mu / (r + mu))
        )
    dens = np.exp(tot - 0.5 * (u / sigma) ** 2) / (sigma * math.sqrt(2 * math.pi))
    assert ll == pytest.approx(math.log(np.trapezoid(dens, u)), abs=1e-6)


def test_analytic_scores_match_numerical_derivatives():
    p = sparse_panel(seed=1)
    d = pa.build_pooled_design(p, modifiers=["m1"])
    k = d.X.shape[1]
    params = np.r_[np.random.default_rng(0).normal(0, 0.1, k), -0.2, -1.0]
    params[0] = -11.0
    _, S = pa.place_logliks(params, d, grad=True)
    num = pa._jacobian(lambda q: pa.place_logliks(q, d), params)
    assert np.max(np.abs(S - num)) < 1e-4 * (1 + np.max(np.abs(num)))


def test_recovers_pooled_effects_on_sparse_panels():
    """Band effects, θ (per SD, at the treated mean), ρ and δ inside their 90% intervals in at least 22 of
    30 panels where ~70% of places never record an ADU."""
    covered = {}
    for seed in range(N_SIMS):
        p = sparse_panel(seed=100 + seed)
        fit = pa.estimate_pooled(p, modifiers=["m1"], rate_ref=float(RATE.mean()))
        summ = pa.summarize(fit, pa.score_bootstrap(fit, draws=199, seed=seed)).set_index("term")
        m = p.loc[p["T"].notna()].drop_duplicates("place")["m1"]
        truth = {n: b + 0.4 * m.mean() for n, b in zip(pa.BAND_NAMES, BETA, strict=True)}
        truth |= {"theta_m1": 0.4 * m.std(ddof=1), "rho": -0.15, "delta": -0.3}
        for term, v in truth.items():
            covered[term] = covered.get(term, 0) + int(summ.loc[term, "low"] <= v <= summ.loc[term, "high"])
    for term, c in covered.items():
        assert c >= MIN_COVERED, (term, c)


def test_a_common_shock_is_not_read_as_a_reform_effect():
    """No reform effect and a −0.7 year shock from 2022 for everyone: the overall pooled effect's 90%
    interval contains 0 in at least 14 of 20 sparse panels (development, 70 panels: coverage 87-97%; a small
    negative lean of about −0.15, a third of the estimate's spread, with ~50 ADU permits per panel)."""
    hits = 0
    for seed in range(20):
        p = sparse_panel(seed=300 + seed, beta=(0, 0, 0), theta=0, rho=0, delta=0, shock=-0.7)
        fit = pa.estimate_pooled(p, modifiers=["m1"])
        main = pa.summarize_main(fit, pa.score_bootstrap(fit, draws=199, seed=seed)).set_index("term")
        hits += main.loc["overall", "low"] <= 0 <= main.loc["overall", "high"]
    assert hits >= 14


def test_a_band_with_no_adu_is_dropped_and_reported():
    p = sparse_panel(seed=7)
    e = p["year"] - p["T"]
    p.loc[(e >= 2) & (e <= 3), "y"] = 0
    fit = pa.estimate_pooled(p, modifiers=["m1"])
    assert any(x.startswith("beta_2_3") for x in fit.design.dropped)
    assert "beta_2_3" not in fit.names and fit.converged


def test_a_separating_modifier_is_caught():
    """Three treated places, the only ones with m2 = 1, build nothing after adoption (but did before):
    the rectifier drops their post-adoption rows; the fit converges with bounded coefficients."""
    p = sparse_panel(seed=8, a_mean=-9.5)
    treated = p.loc[p["T"].notna()].groupby("place")["y"].sum().sort_values().index[-3:]
    p["m2"] = p["place"].isin(treated).astype(float)
    p.loc[p["place"].isin(treated) & (p["year"] >= p["T"]), "y"] = 0
    fit = pa.estimate_pooled(p, modifiers=["m1", "m2"])
    assert {pl for pl, _ in fit.design.separated} >= set(treated)
    assert fit.converged


def test_guards_fail_loudly():
    p = sparse_panel(seed=9)
    with pytest.raises(EstimationError, match="did not converge"):
        pa.estimate_pooled(p, modifiers=["m1"], max_iter=2)


def test_transport_covers_held_out_places():
    p = sparse_panel(seed=10, n_places=260, a_mean=-9.8)
    treated = p.loc[p["T"].notna(), "place"].unique()
    held = set(treated[:20])
    fit_panel = p[~p["place"].isin(held)]
    fit = pa.estimate_pooled(fit_panel, modifiers=["m1"])
    boot = pa.score_bootstrap(fit, draws=199, seed=10)
    pred = pa.transport_predict(
        fit, boot, fit_panel, p[p["place"].isin(held)].assign(name="x"), draws=400, seed=10
    )
    yearly = pred[pred["year"] != "total"]
    cov = ((yearly["observed"] >= yearly["p10"]) & (yearly["observed"] <= yearly["p90"])).mean()
    tot = pred[pred["year"] == "total"]
    assert cov >= 0.6
    assert ((tot["observed"] >= tot["p05"]) & (tot["observed"] <= tot["p95"])).mean() >= 0.8


def test_imputation_robustness_recovers_the_effect_on_a_dense_panel():
    """Borusyak-style imputation on a denser panel: band effects within 0.15 of the truth (θ = ρ = δ = 0)."""
    p = sparse_panel(seed=11, n_places=300, a_mean=-8.5, theta=0, rho=0, delta=0, kappa=0.1)
    eff = pa.imputation_effects(p)
    for name, b in zip(pa.BAND_NAMES, BETA, strict=True):
        assert eff[name] == pytest.approx(b, abs=0.15)
