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


# ---- D-025 convergence rule for repeated refits ----


class StubFitter:
    """Fails on chosen calls (by call number), else returns a fixed fit; records the `start` it got."""

    def __init__(self, fit, fail_calls):
        self.fit, self.fail_calls, self.calls, self.starts = fit, set(fail_calls), 0, []

    def __call__(self, panel, start=None, **kw):
        self.calls += 1
        self.starts.append(start)
        if self.calls in self.fail_calls:
            raise EstimationError("stub: did not converge")
        return self.fit


@pytest.fixture(scope="module")
def small_fit():
    p = sparse_panel(seed=50, n_places=60, a_mean=-9.5)
    return p, pa.estimate_pooled(p, modifiers=["m1"])


def test_a_refit_that_fails_once_succeeds_on_the_retry_from_the_main_estimates(small_fit):
    panel, main = small_fit
    stub = StubFitter(main, fail_calls={1})
    log = pa.RefitLog("stage")
    assert pa.refit(panel, main, log, stub) is main
    assert stub.starts == [None, main]  # the retry starts from the main model
    assert (log.refits, log.first, log.retried, log.failed) == (1, 0, 1, 0)


def test_a_refit_that_fails_twice_is_counted_and_excluded(small_fit):
    panel, main = small_fit
    log = pa.RefitLog("stage")
    assert pa.refit(panel, main, log, StubFitter(main, fail_calls={1, 2})) is None
    assert (log.refits, log.failed) == (1, 1)
    assert "0 of 1 refits converged" in log.summary


def test_randomization_inference_excludes_isolated_failures_and_reports_the_count(small_fit):
    """20 permutations, one fails twice: p is computed over 19 and the run carries on."""
    panel, main = small_fit
    stub = StubFitter(main, fail_calls={5, 6})  # the 5th refit fails, and its retry too
    obs, p, dist, log = pa.randomization_inference(panel, 20, main, seed=1, fitter=stub, modifiers=["m1"])
    assert len(dist) == 19 and log.failed == 1
    assert log.summary.startswith("randomization inference: 19 of 20 refits converged")


def test_a_stage_stops_when_failures_exceed_five_percent(small_fit):
    """2 of 20 permutations failing (10%) stops the stage with StageFailed."""
    panel, main = small_fit
    stub = StubFitter(main, fail_calls={3, 4, 9, 10})
    with pytest.raises(pa.StageFailed, match="more than 5%"):
        pa.randomization_inference(panel, 20, main, seed=1, fitter=stub, modifiers=["m1"])


def test_a_single_refit_check_is_reported_not_computed_and_the_run_continues(small_fit):
    panel, main = small_fit
    out = pa.check_placebo_outcome(
        panel, main, draws=50, fitter=StubFitter(main, fail_calls={1, 2}), modifiers=["m1"]
    )
    assert out["pass"] is None and out["note"].startswith("not computed")


def test_start_from_matches_by_name(small_fit):
    panel, main = small_fit
    d = pa.build_pooled_design(panel, modifiers=["m1"], leads=(-1,))
    s = pa.start_from(main, d)
    assert s[d.names.index("lead_1")] == 0.0
    assert s[d.names.index("theta_m1")] == pytest.approx(main.value("theta_m1"))
    assert s[-2] == pytest.approx(main.value("log_sigma"))


def test_score_accumulation_matches_the_previous_implementation():
    """The bincount accumulation equals the earlier np.add.at version to 1e-10 (sums and place scores)."""
    rng = np.random.default_rng(3)
    idx = rng.integers(0, 40, 900)
    M = rng.normal(size=(900, 23))
    old = np.zeros((40, 23))
    np.add.at(old, idx, M)
    assert np.max(np.abs(pa._sum_by(idx, M, 40) - old)) < 1e-10
    p = sparse_panel(seed=2, a_mean=-9.5)
    d = pa.build_pooled_design(p, modifiers=["m1"])
    k = d.X.shape[1]
    params = np.r_[rng.normal(0, 0.1, k), -0.3, -1.0]
    params[0] = -9.0
    _, S_new = pa.place_logliks(params, d, grad=True)

    def old_sum(i, A, G):
        out = np.zeros((G, A.shape[1]))
        np.add.at(out, i, A)
        return out

    saved = pa._sum_by
    try:
        pa._sum_by = old_sum
        _, S_old = pa.place_logliks(params, d, grad=True)
    finally:
        pa._sum_by = saved
    assert np.max(np.abs(S_new - S_old)) < 1e-10


def test_transport_guard_is_on_the_predicted_mean_not_single_draws(small_fit):
    """A wide place-effect distribution (σ = e^0.7 ≈ 2, as estimated) gives long-tailed single draws but a
    sane mean: no error. Raising the intercept by 12 makes the mean absurd (> 5% of parcels a year): error."""
    panel, main = small_fit
    boot = pa.score_bootstrap(main, draws=50, seed=1)
    target = panel[panel["T"].notna()].groupby("place").head(10)
    target = target[target["place"] == target["place"].iloc[0]].assign(name="x", y=0)
    wide = boot.assign(log_sigma=0.7)
    pa.transport_predict(main, wide, panel, target, draws=300, seed=1)
    absurd = boot.assign(intercept=boot["intercept"] + 12)
    with pytest.raises(EstimationError, match="predicted mean"):
        pa.transport_predict(main, absurd, panel, target, draws=100, seed=1)


# ---- D-031 ports to the D-025 path ----


class RecordingFitter(StubFitter):
    """Never fails; records the panels and design keywords it was asked to fit."""

    def __init__(self, fit):
        super().__init__(fit, set())
        self.panels, self.kws = [], []

    def __call__(self, panel, start=None, **kw):
        self.panels.append(panel)
        self.kws.append(kw)
        return super().__call__(panel, start, **kw)


def _with_rule_history(panel):
    """Treated places: a permit rule (dose 1/3) in the two years before T, by right (1) from T, 0 before."""
    k = panel["year"] - panel["T"]
    dose = np.where(k >= 0, 1.0, np.where(k >= -2, 1 / 3, 0.0))
    return panel.assign(dose=np.where(panel["T"].notna(), dose, 0.0))


def test_randomization_inference_moves_the_dose_path_with_adoption(small_fit):
    """D-031 (a): in every permuted panel each treated place's dose is 1 from its new T on and 1/3 in the two
    years before; the D-025 code moved T only, leaving the dose where the old adoption year put it."""
    panel, main = small_fit
    panel = _with_rule_history(panel)
    rec = RecordingFitter(main)
    pa.randomization_inference(panel, 10, main, seed=2, fitter=rec, modifiers=["m1"])
    assert len(rec.panels) == 10
    changed = 0
    for p in rec.panels:
        t = p[p["T"].notna()]
        k = t["year"] - t["T"]
        assert (t.loc[k >= 0, "dose"] == 1.0).all()
        inside = (k < 0) & (k >= -2) & (t["year"] >= YEARS.min())
        assert t.loc[inside, "dose"].to_numpy() == pytest.approx(1 / 3)
        changed += int((p["T"] != panel["T"]).any())
    assert changed >= 8  # the permutations really move adoption years


def test_controls_enter_the_design_unscaled():
    panel = sparse_panel(seed=3, n_places=40, a_mean=-9.5)
    panel["parking"] = (panel["year"] >= 2020).astype(float) * (panel["place"] < "P020")
    d = pa.build_pooled_design(panel, controls=["parking"])
    j = d.names.index("control_parking")
    assert d.X[:, j] == pytest.approx(panel["parking"].to_numpy())
    zero = pa.build_pooled_design(panel.assign(process=0.0), controls=["process"])
    assert "control_process (no non-zero value)" in zero.dropped


def test_sensitivity_runs_build_the_declared_panels(small_fit):
    """D-031 (c): (1) places treated before the panel are dropped; (2) T moves to the announcement year with
    the dose path; (3) parking and process enter as controls. Each run is reported beside the main
    estimate."""
    panel, main = small_fit
    panel = _with_rule_history(panel)
    treated = panel.loc[panel["T"].notna(), "place"].unique()
    early = treated[0]
    panel.loc[panel["place"] == early, "T"] = 2012.0
    ann = treated[1]
    T_ann = float(panel.loc[panel["place"] == ann, "T"].iloc[0]) - 1
    panel["T_announce"] = np.where(panel["place"] == ann, T_ann, np.nan)
    panel["parking"] = 0.0
    panel["process"] = 0.0
    boot = pa.score_bootstrap(main, draws=50, seed=1)
    main_summary = pa.summarize_main(main, boot)
    rec = RecordingFitter(main)
    out = pa.sensitivity_runs(panel, main, main_summary, draws=50, fitter=rec, modifiers=["m1"])
    assert [o["check"].split(" (")[0] for o in out] == [
        "excluding places treated before the panel",
        "T at the announcement year",
        "parking and process controls",
    ]
    assert early not in set(rec.panels[0]["place"])
    re = rec.panels[1]
    r = re[re["place"] == ann]
    assert (r["T"] == T_ann).all() and (r.loc[r["year"] == T_ann, "dose"] == 1.0).all()
    assert rec.kws[2]["controls"] == ["parking", "process"]
    assert all("inside_main" in o for o in out)


# ---------------------------------------------------------------------------------------------------------
# HonestDiD bounds (D-025 note 2026-10-21)
# ---------------------------------------------------------------------------------------------------------


def test_honest_set_by_hand():
    """θ 0.9, leads (0.1, 0.2, 0.3), ω (0.5, 0.5). RM, M̄ 1: M_pre 0.1, Σω(k+1) = 1.5, bias 0.3 ± 0.15 ->
    (0.45, 0.75). SD, M 0: slope 0.1, bias 0.3 + 0.1 × 1.5 = 0.45 -> 0.45; M 0.1: ± 0.1 × (0.5·1 + 0.5·3)
    = ± 0.2."""
    assert pa.honest_set(0.9, (0.1, 0.2, 0.3), [0.5, 0.5], "rm", 1.0) == pytest.approx((0.45, 0.75))
    assert pa.honest_set(0.9, (0.1, 0.2, 0.3), [0.5, 0.5], "sd", 0.0) == pytest.approx((0.45, 0.45))
    assert pa.honest_set(0.9, (0.1, 0.2, 0.3), [0.5, 0.5], "sd", 0.1) == pytest.approx((0.25, 0.65))


def test_honest_bounds_recover_the_effect_under_a_known_linear_violation():
    """True effect 0.5 at every event time; a linear pre-trend δ_k = 0.1 (k + 4) continues after adoption.
    The naive pooled estimate is biased upward; smoothness with M = 0 recovers 0.5 exactly, and the
    relative-magnitudes set with M̄ = 1 has 0.5 at its edge (the violation's steps equal the pre-period's)."""
    omega = np.array([0.3, 0.3, 0.2, 0.1, 0.1])
    k = np.arange(len(omega))
    tau, delta = 0.5, lambda kk: 0.1 * (kk + 4)
    theta = float(omega @ (tau + delta(k)))
    leads = (delta(-3), delta(-2), delta(-1))
    assert theta > 0.5 + 0.3
    sd0 = pa.honest_set(theta, leads, omega, "sd", 0.0)
    assert sd0 == pytest.approx((0.5, 0.5))
    lo, hi = pa.honest_set(theta, leads, omega, "rm", 1.0)
    assert lo == pytest.approx(0.5) and hi > 0.5
    lo_half, _ = pa.honest_set(theta, leads, omega, "rm", 0.5)
    assert lo_half > 0.5  # M̄ below the true ratio excludes the truth: the restriction is binding
    # noisy draws: the robust interval contains the truth and the identified set
    rng = np.random.default_rng(0)
    th = theta + 0.05 * rng.standard_normal(999)
    ld = [tuple(np.array(leads) + 0.02 * rng.standard_normal(3)) for _ in range(999)]
    tab = pa.honest_bounds(theta, leads, th, ld, omega)
    row = tab[(tab["restriction"] == "smoothness") & (tab["m"] == 0.0)].iloc[0]
    assert row["ci_low"] < 0.5 < row["ci_high"]
    assert (tab["ci_low"] <= tab["set_low"] + 1e-12).all() and (
        tab["ci_high"] >= tab["set_high"] - 1e-12
    ).all()


def test_honest_bounds_collapse_without_a_pre_trend_and_breakdown_is_found():
    omega = np.array([0.5, 0.5])
    assert pa.honest_set(0.8, (0.0, 0.0, 0.0), omega, "rm", 2.0) == pytest.approx((0.8, 0.8))
    # leads (0, 0, 0.2): M_pre 0.2, Σω(k+1) 1.5; set 0.6 ± 0.3 M̄ includes 0 from M̄ = 2 (no noise)
    th, ld = np.full(50, 0.8), [(0.0, 0.0, 0.2)] * 50
    assert pa.rm_breakdown(th, ld, omega) == pytest.approx(2.0)
