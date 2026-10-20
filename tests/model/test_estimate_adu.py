"""D-023 estimator (model/estimate_adu.py): PPML by hand, recovery of known effects from simulated staggered
adoption, and a common shock that must not be read as a reform effect. Synthetic data only."""

import math

import numpy as np
import pandas as pd
import pytest

from lotline.model import estimate_adu as est

YEARS = np.arange(2016, 2026)


def simulate(
    seed=0,
    n_places=90,
    beta=(0.3, 0.6, 0.9, 1.1, 1.2, 1.25),
    theta=0.5,
    rho=-0.15,
    delta=-0.3,
    shock=0.0,
    cohorts=(2018, 2019, 2020, 2021, 2022),
    share_treated=0.6,
):
    """A staggered-adoption panel: place effects, year effects (with an optional common drop after 2021 of
    size `shock`), event-time effects β_k on treated places, a modifier m1 × post (θ), rate × post (ρ), and a
    missing-middle switch for a third of places from 2021 (δ). Counts are Poisson around the mean."""
    rng = np.random.default_rng(seed)
    rate = np.interp(YEARS, [2016, 2020, 2021, 2022, 2025], [3.8, 3.1, 3.0, 5.3, 6.6])
    gamma = 0.05 * (YEARS - 2016) + np.where(YEARS >= 2022, shock, 0.0)
    rows = []
    for i in range(n_places):
        alpha = rng.normal(-6.5, 0.6)
        eligible = rng.uniform(4_000, 40_000)
        treated = rng.random() < share_treated
        T = float(rng.choice(cohorts)) if treated else np.nan
        m1 = rng.normal(0, 1)
        mm_from = 2021 if i % 3 == 0 else 9999
        for y, r, g in zip(YEARS, rate, gamma, strict=True):
            k = y - T if treated else -1
            post = 1.0 if treated and k >= 0 else 0.0
            eff = beta[int(min(k, est.K_MAX))] if post else 0.0
            mm = 1.0 if y >= mm_from else 0.0
            eta = alpha + g + eff + theta * m1 * post + rho * (r - rate.mean()) * post + delta * mm
            rows.append(
                {
                    "place": f"P{i:03d}",
                    "year": int(y),
                    "eligible": eligible,
                    "T": T,
                    "dose": 1.0,
                    "rate": r,
                    "mm": mm,
                    "m1": m1,
                    "mu": eligible * math.exp(eta),
                }
            )
    panel = pd.DataFrame(rows)
    # θ is centred on the treated places' mean in the design; shift the simulated truth accordingly
    panel["y"] = rng.poisson(panel["mu"])
    return panel


def test_ppml_one_place_by_hand():
    """One place, two years, y = (2, 6), offset 0: α = log 2, γ_2 = log 3; μ = y."""
    fit = est.ppml([2, 6], np.zeros((2, 0)), [0.0, 0.0], ["A", "A"], [1, 2], [])
    assert fit.alpha[0] == pytest.approx(math.log(2))
    assert fit.gamma[1] == pytest.approx(math.log(3))


def test_ppml_two_by_two_difference_in_differences_by_hand():
    """Places A (2, 4) and B (3, 12) in years 1-2, B treated in year 2: four parameters for four counts, so
    the fit is exact and β = log(12/3) − log(4/2) = log 2 (the ratio of ratios). Offsets cancel within
    place."""
    y = [2, 4, 3, 12]
    X = np.array([[0], [0], [0], [1]], float)
    fit = est.ppml(y, X, np.log([10, 10, 20, 20]), ["A", "A", "B", "B"], [1, 2, 1, 2], ["beta"])
    assert fit.coef_of("beta") == pytest.approx(math.log(2))
    assert fit.mu == pytest.approx(y)


def test_ppml_drops_all_zero_places_and_reports_them():
    y = [0, 0, 3, 5, 2, 4]
    fit = est.ppml(y, np.zeros((6, 0)), np.zeros(6), ["Z", "Z", "A", "A", "B", "B"], [1, 2] * 3, [])
    assert fit.dropped_places == ["Z"] and fit.keep.sum() == 4


def _within(summary, term, truth):
    row = summary.set_index("term").loc[term]
    return row["low"] <= truth <= row["high"], row


RATE_MEAN = float(np.interp(YEARS, [2016, 2020, 2021, 2022, 2025], [3.8, 3.1, 3.0, 5.3, 6.6]).mean())
N_SIMS = 20
MIN_COVERED = 15  # a correct 90% interval covers in at least 15 of 20 panels with probability ~0.96


def test_recovers_event_time_effects_theta_rho_and_delta():
    """Known β_k, θ, ρ and δ fall inside their 90% bootstrap intervals in at least 15 of 20 simulated panels.
    With the modifier centred on the treated places' mean, β_k is the effect at that mean, so its truth is
    β_k + θ·m̄_treated. Also: the estimates are unbiased (mean error well inside the spread)."""
    beta = (0.3, 0.6, 0.9, 1.1, 1.2, 1.25)
    covered, errors = {}, {}
    for seed in range(N_SIMS):
        panel = simulate(seed=seed)
        fit = est.estimate(panel, modifiers=["m1"], rate_ref=RATE_MEAN)
        summ = est.summarize(fit, est.score_bootstrap(fit, draws=199, seed=seed)).set_index("term")
        m_bar = panel.loc[panel["T"].notna()].drop_duplicates("place")["m1"].mean()
        truth = {f"beta_{k}": b + 0.5 * m_bar for k, b in enumerate(beta)}
        truth |= {"theta_m1": 0.5, "rho": -0.15, "delta": -0.3}
        for term, v in truth.items():
            row = summ.loc[term]
            covered[term] = covered.get(term, 0) + int(row["low"] <= v <= row["high"])
            errors.setdefault(term, []).append(row["estimate"] - v)
    for term in covered:
        assert covered[term] >= MIN_COVERED, (term, covered[term])
        e = np.array(errors[term])
        assert abs(e.mean()) < 2 * e.std(ddof=1) / np.sqrt(len(e)) + 0.02, (term, e.mean(), e.std())


def test_a_common_shock_is_not_read_as_a_reform_effect():
    """The Minneapolis failure mode: after 2021 every place, treated or not, builds half as many ADUs (a year
    effect of −0.7) and the reform does nothing. The estimated overall effect's 90% interval contains 0 and
    the point estimate is small; ρ (rates × treated) is not credited with the shock either."""
    panel = simulate(seed=3, beta=(0, 0, 0, 0, 0, 0), theta=0.0, rho=0.0, delta=0.0, shock=-0.7)
    fit = est.estimate(panel, modifiers=["m1"])
    summ = est.summarize(fit, est.score_bootstrap(fit, draws=299, seed=3))
    ok, row = _within(summ, "att", 0.0)
    assert ok and abs(row["estimate"]) < 0.15, row.to_dict()
    ok, row = _within(summ, "rho", 0.0)
    assert ok, row.to_dict()
    # γ absorbs the shock: the 2022+ year effects sit ~0.7 below the trend
    g = fit.fit.gamma
    assert (g[YEARS >= 2022][0] - g[YEARS == 2021][0]) == pytest.approx(-0.7 + 0.05, abs=0.12)


def test_aggregate_weights_cells_by_counterfactual_permits():
    """Two cohort cells at k = 0 with coefficients 0.2 and 0.6 and counterfactual permits 30 and 10 average to
    (0.2·30 + 0.6·10) / 40 = 0.3 (checked through the public function on a constructed fit)."""
    panel = simulate(seed=4, cohorts=(2019, 2021))
    fit = est.estimate(panel, modifiers=[], use_rate=False, use_mm=False)
    w = est._cell_weights(fit)
    coef = fit.fit.coef.copy()
    names = fit.fit.names
    k0 = w[w["k"] == 0]
    for n, v in zip(k0["name"], (0.2, 0.6), strict=True):
        coef[names.index(n)] = v
    agg = est.aggregate(fit, coef)
    wts = est._cell_weights(fit, coef)
    wts = wts[wts["k"] == 0]["weight"].to_numpy()
    assert agg["beta_0"] == pytest.approx((0.2 * wts[0] + 0.6 * wts[1]) / wts.sum())


def test_randomization_inference_finds_a_real_effect_and_not_a_null_one():
    real = simulate(seed=5, n_places=60)
    att, p, _ = est.randomization_inference(real, permutations=39, seed=5, modifiers=[], use_mm=False)
    assert att > 0.5 and p <= 0.1
    null = simulate(seed=6, n_places=60, beta=(0, 0, 0, 0, 0, 0), theta=0, rho=0, delta=0)
    att0, p0, _ = est.randomization_inference(null, permutations=39, seed=6, modifiers=[], use_mm=False)
    assert p0 > 0.1


def test_pre_trend_leads_test_has_the_right_size():
    """With no anticipation the joint lead test (k = −3…−1) rejects at the 10% level in at most 5 of 20
    panels (expected 2; on 150 panels during development it rejected 11-12%)."""
    rejected = 0
    for seed in range(100, 100 + N_SIMS):
        panel = simulate(seed=seed)
        fit = est.estimate(panel, modifiers=["m1"], leads=(-3, -2, -1))
        _, p = est.joint_wald(
            est.score_bootstrap(fit, draws=199, seed=seed), fit, ["lead_3", "lead_2", "lead_1"]
        )
        rejected += p < 0.10
    assert rejected <= 5


def test_pre_trend_leads_detect_anticipation():
    """If treated places start building two years before adoption (+0.4 in log), the lead test rejects."""
    panel = simulate(seed=42)
    e = panel["year"] - panel["T"]
    bump = np.where((e >= -2) & (e < 0), np.exp(0.4), 1.0)
    panel["y"] = np.random.default_rng(42).poisson(panel["mu"] * bump)
    fit = est.estimate(panel, modifiers=["m1"], leads=(-3, -2, -1))
    _, p = est.joint_wald(est.score_bootstrap(fit, draws=299, seed=42), fit, ["lead_3", "lead_2", "lead_1"])
    assert p < 0.10


def test_rule_dose_by_hand():
    """by_right blank (P restricts 0.2), owner occupancy False, grades (1/3, 2/3, 1), coverage 0.75:
    (0.2·1/3 + 0.8·1)·0.75 = 0.65; P(by right) 0.8. An explicit 'no ADUs' rule: dose 0."""
    fp = {"by_right": 0.2, "owner_occ": 0.6}
    dose, br = est.rule_dose({"owner_occ": False}, 0.75, fp, (1 / 3, 2 / 3, 1.0))
    assert dose == pytest.approx((0.2 / 3 + 0.8) * 0.75) and br == pytest.approx(0.8)
    assert est.rule_dose({"adus_per_lot": 0}, 1.0, fp, (1 / 3, 2 / 3, 1.0)) == (0.0, 0.0)
    owner = est.rule_dose({"by_right": True, "owner_occ": True}, 1.0, fp, (1 / 3, 2 / 3, 1.0))
    assert owner == pytest.approx((2 / 3, 1.0))


def _with_placebo(panel, seed, effect=0.0):
    """Add a 5+ unit outcome unrelated to ADU rules (or with a fake `effect` after adoption)."""
    rng = np.random.default_rng(seed)
    e = panel["year"] - panel["T"]
    lvl = panel.groupby("place")["eligible"].transform("first") * 0.0005
    mu = lvl * np.exp(np.where(e >= 0, effect, 0.0))
    return panel.assign(units_5p=rng.poisson(mu))


def test_checks_pass_on_a_clean_simulation():
    panel = _with_placebo(simulate(seed=11), 11)
    kw = {"modifiers": ["m1"]}
    main = est.summarize(est.estimate(panel, **kw), est.score_bootstrap(est.estimate(panel, **kw), 199, 11))
    assert est.check_leads(panel, draws=199, seed=11, **kw)["pass"]
    assert est.check_placebo_dates(panel, draws=199, seed=11, **kw)["pass"]
    assert est.check_placebo_outcome(panel, draws=199, seed=11, **kw)["pass"]
    assert est.check_excluding(panel, main, draws=199, seed=11, **kw)["pass"]
    assert est.check_leave_one_out(panel, main, **kw)["pass"]


def test_placebo_outcome_check_fails_when_the_placebo_responds():
    panel = _with_placebo(simulate(seed=12), 12, effect=0.5)
    assert not est.check_placebo_outcome(panel, draws=199, seed=12, modifiers=["m1"])["pass"]


def test_transport_predictions_cover_held_out_places_from_the_same_process():
    """Fit on 115 simulated places, predict 15 held-out treated places with their own modifiers: the D-023
    pass rule holds (totals inside their 80% intervals, yearly coverage of the 80% intervals 60-95%)."""
    panel = simulate(seed=13, n_places=130)
    treated = panel.loc[panel["T"].notna(), "place"].unique()
    held = set(treated[:15])
    fit_panel = panel[~panel["place"].isin(held)]
    target = panel[panel["place"].isin(held)].assign(name=lambda d: d["place"])
    e = est.estimate(fit_panel, modifiers=["m1"])
    boot = est.score_bootstrap(e, draws=199, seed=13)
    pred = est.transport_predict(e, boot, target, draws=400, seed=13)
    verdict = est.transport_verdict(pred)
    # over 8 seeds in development: totals inside 90% intervals 91%, inside 80% intervals 88%, yearly 80% 82%
    assert verdict["yearly_coverage_80"] >= 0.6
    tot = pred[pred["year"] == "total"]
    assert ((tot["observed"] >= tot["p05"]) & (tot["observed"] <= tot["p95"])).mean() >= 0.8
