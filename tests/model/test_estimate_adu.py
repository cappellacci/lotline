"""ADU effect estimators (model/estimate_adu.py). Synthetic data only.

- D-023 extended TWFE PPML (now the robustness estimator): PPML by hand, recovery of known effects, a common
  shock, separation and numerical guards.
- D-026 imputation (primary): hand-worked examples, the four regimes that broke D-023 (each shown failing
  under D-023 and passing under D-026), randomization inference with the dose path moved, controls, checks,
  transport, and the household-growth and post-panel year-effect fixes."""

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
    # saturated: residuals are exactly 0, so the SE is 0 by construction; skip the degenerate-SE check
    fit = est.ppml(y, X, np.log([10, 10, 20, 20]), ["A", "A", "B", "B"], [1, 2, 1, 2], ["beta"], check=False)
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
        m = panel.loc[panel["T"].notna()].drop_duplicates("place")["m1"]
        truth = {f"beta_{k}": b + 0.5 * m.mean() for k, b in enumerate(beta)}
        # modifiers enter as z-scores over treated places, so θ per SD = 0.5 × SD(m1)
        truth |= {"theta_m1": 0.5 * m.std(ddof=1), "rho": -0.15, "delta": -0.3}
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


# ---- Separation and numerical guards (D-023 rerun fix) ----


def test_relu_finds_separated_observations_by_hand():
    """y = (0, 0, 1, 1) with an intercept and x = (1, 1, 0, 0): z = x is 0 where y > 0 and positive where
    y = 0, so observations 1 and 2 are separated. With x = (1, 0, 1, 0) and y = (0, 1, 1, 0) nothing is."""
    Z = np.column_stack([np.ones(4), [1, 1, 0, 0]])
    assert est.relu_separated(Z, np.array([0, 0, 1, 1.0])).tolist() == [True, True, False, False]
    Z2 = np.column_stack([np.ones(4), [1, 0, 1, 0]])
    assert not est.relu_separated(Z2, np.array([0, 1, 1, 0.0])).any()


def test_all_zero_cohort_cells_are_dropped_and_effects_still_recovered():
    """Cohort 2022 builds nothing in its first four post years (cells all zero): those cells are dropped as
    separated, PPML converges, and β_1 and θ are still covered by their 90% intervals in at least 15 of 20
    panels (over 20 other seeds in development θ: mean error 0.001, coverage 95%)."""
    beta = (0.3, 0.6, 0.9, 1.1, 1.2, 1.25)
    covered = covered_theta = 0
    for seed in range(200, 200 + N_SIMS):
        panel = simulate(seed=seed)
        zero = (panel["T"] == 2022) & (panel["year"] >= 2022)
        panel.loc[zero, "y"] = 0
        fit = est.estimate(panel, modifiers=["m1"])
        assert any(c.startswith("cell_2022_") and "separated" in c for c in fit.fit.dropped_columns)
        assert fit.fit.converged and np.max(np.abs(fit.fit.coef)) < est.COEF_BOUND
        summ = est.summarize(fit, est.score_bootstrap(fit, draws=199, seed=seed)).set_index("term")
        m_bar = panel.loc[panel["T"].notna()].drop_duplicates("place")["m1"]
        sd = m_bar.std(ddof=1)
        truth = beta[1] + 0.5 * m_bar.mean()  # β_1 at the treated mean (θ per SD is 0.5·sd)
        covered += summ.loc["beta_1", "low"] <= truth <= summ.loc["beta_1", "high"]
        covered_theta += summ.loc["theta_m1", "low"] <= 0.5 * sd <= summ.loc["theta_m1", "high"]
    assert covered >= MIN_COVERED and covered_theta >= MIN_COVERED


def test_a_separating_modifier_is_caught_and_the_fit_stays_bounded():
    """Three treated places build nothing after adoption and are the only ones with modifier m2 = 1: their
    post-adoption observations are separated through a combination of the cells and θ·post (no single column
    shows it); the iterated rectifier finds them, PPML converges and θ stays bounded."""
    panel = simulate(seed=21)
    treated = panel.loc[panel["T"].notna(), "place"].unique()[:3]
    panel["m2"] = panel["place"].isin(treated).astype(float)
    post = panel["year"] >= panel["T"]
    panel.loc[panel["place"].isin(treated) & post, "y"] = 0
    fit = est.estimate(panel, modifiers=["m1", "m2"])
    seps = {pl for pl, _ in fit.fit.separated}
    assert seps >= set(treated)
    assert fit.fit.converged and np.max(np.abs(fit.fit.coef)) < est.COEF_BOUND


def test_diagnostics_fail_loudly():
    panel = simulate(seed=22)
    d = est.build_design(panel, modifiers=["m1"])
    with pytest.raises(est.EstimationError, match="did not converge"):
        est.ppml(
            panel["y"], d.X, np.log(panel["eligible"]), panel["place"], panel["year"], d.names, max_iter=1
        )
    with pytest.raises(est.EstimationError, match="standard errors effectively zero"):
        X = np.array([[0], [0], [0], [1]], float)
        est.ppml([2, 4, 3, 12], X, np.zeros(4), ["A", "A", "B", "B"], [1, 2, 1, 2], ["beta"])


# =========================================================================================================
# D-026: imputation on the additive scale
# =========================================================================================================


def simulate_d026(seed=0, treated=(), n_never=20, alpha_never=-8.0, effect=None, trend=0.06, dose_pre=0.0):
    """A panel for D-026: `treated` is a list of (T, α) per treated place (T may be before 2016); untreated
    counts are Poisson(Eligible · exp(α + γ_t)), treated ones multiplied by exp(effect(k)). Keeps the true
    means (mu0_true, mu) so the true additive ATT on any set of rows is known. The dose is 1 from T and
    `dose_pre` (a permit rule) in the two years before T."""
    effect = effect or (lambda k: math.log(2.0))
    rng = np.random.default_rng(seed)
    gamma = trend * (YEARS - 2016)
    specs = [(np.nan, rng.normal(alpha_never, 0.4)) for _ in range(n_never)]
    specs += [(float(T), a + rng.normal(0, 0.2)) for T, a in treated]
    rows = []
    for i, (T, a) in enumerate(specs):
        elig = rng.uniform(5_000, 30_000)
        for y, g in zip(YEARS, gamma, strict=True):
            k = y - T if not np.isnan(T) else -99
            mu0 = elig * math.exp(a + g)
            rows.append(
                {
                    "place": f"P{i:03d}",
                    "year": int(y),
                    "eligible": elig,
                    "T": T,
                    "dose": 1.0 if k >= 0 else (dose_pre if -2 <= k < 0 else 0.0),
                    "rate": 4.0,
                    "mm": 0.0,
                    "mu0_true": mu0,
                    "mu": mu0 * math.exp(effect(k)) if k >= 0 else mu0,
                }
            )
    panel = pd.DataFrame(rows)
    panel["y"] = rng.poisson(panel["mu"])
    return panel


def true_att(res, panel):
    """(additive ATT per 1,000 parcels, log of the proportional effect) on the rows the estimate used."""
    u = res.rows[res.rows["used"]]
    m = panel.set_index(["place", "year"]).loc[list(zip(u["place"], u["year"], strict=True))]
    diff = (m["mu"] - m["mu0_true"]).sum()
    return 1000 * diff / u["eligible"].sum(), math.log(m["mu"].sum() / m["mu0_true"].sum())


def d023_att(panel):
    e = est.estimate(panel, modifiers=[], use_rate=False, use_mm=False)
    return est.aggregate(e)["att"]


def test_impute_by_hand():
    """Untreated A (2, 4) and B (3, ·) over two years, B treated in year 2 with y = 9, eligible 1,000: γ̂_2 =
    log 2 from A, α̂_B from B's year 1, μ̂0 = 3 · 2 = 6, ATT = 1,000 · (9 − 6) / 1,000 = 3; ratio 3 / 6."""
    panel = pd.DataFrame(
        {
            "place": ["A", "A", "B", "B"],
            "year": [1, 2, 1, 2],
            "y": [2, 4, 3, 9],
            "eligible": 1000.0,
            "T": [np.nan, np.nan, 2, 2],
            "dose": [0, 0, 0, 1.0],
        }
    )
    r = est.impute(panel, controls=())
    assert r.rows.loc[3, "mu0"] == pytest.approx(6.0)
    assert r.att["att"] == pytest.approx(3.0) and r.att["ratio"] == pytest.approx(0.5)
    assert r.att["att_k0_1"] == pytest.approx(3.0) and np.isnan(r.att["att_k2_3"])
    assert not r.estimable  # one contributing place is below the D-026 floor of 3


def test_replaced_rule_dose_by_hand():
    """Dose (0, 1/3, 1/3, 1, 1) over 2016-2020, T = 2019 → (0, 1/3, 1/3, 1/3, 1/3); a never-treated place
    keeps its own path."""
    panel = pd.DataFrame(
        {
            "place": ["A"] * 5 + ["N"] * 5,
            "year": list(range(2016, 2021)) * 2,
            "T": [2019.0] * 5 + [np.nan] * 5,
            "dose": [0, 1 / 3, 1 / 3, 1, 1, 0, 0, 1 / 3, 1 / 3, 1 / 3],
        }
    )
    assert est.replaced_rule_dose(panel) == pytest.approx(
        [0, 1 / 3, 1 / 3, 1 / 3, 1 / 3, 0, 0, 1 / 3, 1 / 3, 1 / 3]
    )


def test_shift_dose_path_by_hand():
    """Years 2016-2021, dose (0, 0, 1/3, 1, 1, 1), T 2019 → 2020: (0, 0, 0, 1/3, 1, 1); → 2017: the path moves
    two years earlier and holds its last value at the end: (1/3, 1, 1, 1, 1, 1)."""
    years = np.arange(2016, 2022)
    dose = np.array([0, 0, 1 / 3, 1, 1, 1])
    assert est.shift_dose_path(years, dose, 2019, 2020) == pytest.approx([0, 0, 0, 1 / 3, 1, 1])
    assert est.shift_dose_path(years, dose, 2019, 2017) == pytest.approx([1 / 3, 1, 1, 1, 1, 1])


# ---- The four regimes that broke D-023 (review 2026-10-20): each fails under D-023, passes under D-026 ----


def test_regime_zero_pre_periods():
    """Six treated places (cohorts 2021-22) have no ADU before adoption and a log-50 effect; six others
    (2019-20) have permits before. D-023 drops the zero places' pre-years as separated and their cells add
    near-zero contrasts, so its overall log effect lands far below log 50. D-026 excludes them (listed, with
    an upper bound over all treated places that counts their permits as additional) and recovers the
    additive ATT on the rest within 10%."""
    for seed in range(3):
        treated = [(2019, -8.5)] * 3 + [(2020, -8.5)] * 3 + [(2021, -12.5)] * 3 + [(2022, -12.5)] * 3
        panel = simulate_d026(seed, treated, effect=lambda k: math.log(50))
        zero = panel["place"].isin(panel.loc[panel["T"] >= 2021, "place"]) & (panel["year"] < panel["T"])
        panel.loc[zero, "y"] = 0
        assert d023_att(panel) < math.log(50) - 0.5  # D-023 fails
        r = est.impute(panel)
        truth, _ = true_att(r, panel)
        assert abs(r.att["att"] - truth) < 0.10 * truth
        excl = r.excluded.set_index("place")["reason"]
        assert set(panel.loc[panel["T"] >= 2021, "place"]) <= set(excl.index)
        assert excl.str.contains("no kept untreated year").sum() == 6
        # upper bound over all treated places: the zero places' permits all count as additional (μ̂0 = 0)
        u, z = r.rows[r.rows["used"]], r.rows[r.rows["treated"] & ~r.rows["used"]]
        bound = (
            1000 * ((u["y"] - u["mu0"]).sum() + z["y"].sum()) / (u["eligible"].sum() + z["eligible"].sum())
        )
        assert r.att["att_upper_zero_pre"] == pytest.approx(bound)


def test_regime_2016_cohort():
    """Four places adopt in 2016, the panel's first year, with an effect that ramps up. D-023 keeps their
    cells, which only have a contrast against one another, and their paths pull the year effects up: its
    overall effect is near zero against a true log effect near 0.9. D-026 excludes the 2016 cohort and
    recovers the additive ATT (mean error over 5 panels within 15% of the truth)."""
    errs, truths = [], []
    for seed in range(5):
        treated = [(2016, -8)] * 4 + [(2019, -8)] * 3 + [(2021, -8)] * 3
        panel = simulate_d026(seed, treated, effect=lambda k: 0.3 + 0.2 * min(k, 5))
        r = est.impute(panel)
        truth, log_truth = true_att(r, panel)
        assert d023_att(panel) < log_truth - 0.5  # D-023 fails
        assert (r.excluded["reason"].str.contains("in or before 2016")).sum() == 4
        assert not r.rows["place"].isin(panel.loc[panel["T"] == 2016, "place"]).any()
        errs.append(r.att["att"] - truth)
        truths.append(truth)
    assert abs(np.mean(errs)) < 0.15 * np.mean(truths)


def test_regime_pre_panel_adopters_whose_effect_keeps_growing():
    """Six places adopted in 2008-10 and their effect keeps growing past k = 5 (0.15 a year). Under D-023 the
    pooled 5+ cell is constant within place, so it is absorbed by the place effect and the growth loads onto
    the year effects: already-treated places act as controls and the in-panel effect is read as ~0.
    D-026 excludes them and recovers the additive ATT (mean error over 5 panels within 15%)."""
    errs, truths = [], []
    for seed in range(5):
        treated = [(2008, -8)] * 3 + [(2010, -8)] * 3 + [(2019, -8)] * 3 + [(2021, -8)] * 3
        panel = simulate_d026(seed, treated, effect=lambda k: 0.15 * k)
        r = est.impute(panel)
        truth, log_truth = true_att(r, panel)
        assert d023_att(panel) < log_truth - 0.25  # D-023 fails
        assert (r.excluded["reason"].str.contains("in or before 2016")).sum() == 6
        errs.append(r.att["att"] - truth)
        truths.append(truth)
    assert abs(np.mean(errs)) < 0.15 * np.mean(truths)


def test_regime_singleton_cohorts():
    """Six treated places, each its own cohort (2017-22), and a doubling of permits. Under D-023 the modifier
    term θ is collinear with the cohort cells (dropped), and the CR2 score-bootstrap 90% interval of the
    overall effect covers the truth in under 70% of panels (37% over 30 panels in development). D-026 has no
    θ, its ATT is unbiased (mean error well inside the spread) and its place-bootstrap interval covers more
    often (77% over 30 panels in development; still below 90%, which is why D-026 makes randomization
    inference primary)."""
    old_cover = new_cover = 0
    errs = []
    n = 12
    for seed in range(1000, 1000 + n):
        panel = simulate_d026(seed, [(T, -8.0) for T in range(2017, 2023)])
        panel["m1"] = np.random.default_rng(seed).normal(size=len(panel))
        panel["m1"] = panel.groupby("place")["m1"].transform("first")
        old = est.estimate(panel, modifiers=["m1"], use_rate=False, use_mm=False)
        assert "theta_m1 (collinear with fixed effects)" in old.fit.dropped_columns
        s_old = (
            est.summarize(old, est.score_bootstrap(old, draws=199, seed=seed)).set_index("term").loc["att"]
        )
        old_cover += s_old["low"] <= math.log(2) <= s_old["high"]
        r = est.impute(panel)
        truth, _ = true_att(r, panel)
        s_new = est.summarize_att(r, est.place_bootstrap(panel, draws=99, seed=seed)).set_index("term")
        new_cover += s_new.loc["att", "low"] <= truth <= s_new.loc["att", "high"]
        errs.append(r.att["att"] - truth)
    assert old_cover <= 0.7 * n  # D-023 fails
    assert new_cover > old_cover
    e = np.array(errs)
    assert abs(e.mean()) < 2 * e.std(ddof=1) / np.sqrt(n) + 0.02


# ---- Randomization inference (D-026 primary): the dose path moves with T (D-023 defect 6) ----


def test_randomization_inference_moves_the_dose_path_with_adoption():
    """Every treated place has a permit rule (dose 1/3) in the two years before T and a by-right rule (1) from
    T. In each permuted panel, each place's dose must be 1 from its new T on and 1/3 in the two years before
    (the replaced-rule control then stays 1/3 after adoption). D-023's version moved T only, leaving the old
    dose path behind."""
    panel = simulate_d026(7, [(2018, -8), (2019, -8), (2020, -8), (2022, -8)], n_never=8, dose_pre=1 / 3)
    seen = []

    def stat(res):
        seen.append(res.rows)
        return res.att["att"]

    ri = est.randomization_inference(panel, statistic=stat)
    assert ri.enumerated and ri.n_assignments == 24 and len(ri.dist) == 24
    assert ri.p_min == pytest.approx(1 / 24)
    for rows in seen[1:]:
        t = rows[rows["T"].notna()]
        k = t["year"] - t["T"]
        assert (t.loc[k >= 0, "dose"] == 1.0).all()
        assert t.loc[(k == -1) | (k == -2), "dose"].to_numpy() == pytest.approx(1 / 3)
        assert t.loc[k >= 0, "z_rule"].to_numpy() == pytest.approx(1 / 3)


def test_randomization_inference_finds_a_real_effect_and_not_a_null_one():
    """Five treated places with distinct adoption years (120 assignments, all enumerated): a doubling of
    permits gives p <= 0.10; no effect gives p > 0.10."""
    treated = [(T, -7.5) for T in range(2018, 2023)]
    real = simulate_d026(5, treated, effect=lambda k: math.log(2.0))
    ri = est.randomization_inference(real)
    assert ri.enumerated and ri.n_assignments == 120 and ri.att > 0 and ri.p <= 0.10
    null = simulate_d026(6, treated, effect=lambda k: 0.0)
    assert est.randomization_inference(null).p > 0.10


def test_randomization_inference_has_the_right_size():
    """With no effect the RI p-value is below 0.10 in at most 3 of 12 panels (expected 1.2; P(>3) ≈ 0.03 for
    a correct test; draws mode, 39 permutations)."""
    rejected = 0
    for seed in range(300, 312):
        panel = simulate_d026(
            seed, [(T, -8.0) for T in (2018, 2019, 2019, 2020, 2021, 2022, 2023)], effect=lambda k: 0.0
        )
        rejected += est.randomization_inference(panel, permutations=39, seed=seed).p < 0.10
    assert rejected <= 3


# ---- Controls (D-026): parking and process reforms; the replaced ADU rule ----


def test_a_parking_reform_is_not_read_as_the_adu_effect():
    """Half the never-treated places and every treated place drop parking minimums in 2020 (+0.5 log on
    permits); the by-right ADU rule adds a doubling. With the parking control the ATT matches the ADU-only
    truth; without it the ATT absorbs part of the parking effect. λ_parking is recovered."""
    errs_with, errs_without, lams = [], [], []
    for seed in range(5):
        treated = [(T, -8.0) for T in (2019, 2020, 2021, 2022, 2023) for _ in range(2)]
        panel = simulate_d026(seed, treated, n_never=20)
        idx = panel["place"].str[1:].astype(int)
        parking = ((idx % 2 == 0) | panel["T"].notna()) & (panel["year"] >= 2020)
        panel["parking"] = parking.astype(float)
        panel["mu0_true"] *= np.where(parking, math.exp(0.5), 1.0)
        panel["mu"] *= np.where(parking, math.exp(0.5), 1.0)
        panel["y"] = np.random.default_rng(seed).poisson(panel["mu"])
        r = est.impute(panel)
        truth, _ = true_att(r, panel)
        errs_with.append((r.att["att"] - truth) / truth)
        lams.append(r.fit.coef_of("lambda_parking"))
        r0 = est.impute(panel, controls=())
        errs_without.append((r0.att["att"] - truth) / truth)
    assert abs(np.mean(errs_with)) < 0.10
    assert np.mean(errs_without) > 0.15
    assert np.mean(lams) == pytest.approx(0.5, abs=0.1)


def test_a_place_with_a_permit_rule_is_an_untreated_place_with_a_control():
    """D-023 defect 5: a permit rule (dose 1/3) raises permits by 0.4 log. A third of the never-treated places
    get one in 2019, and every treated place has one in the two years before its by-right rule. The rule is
    a control estimated on untreated rows (λ ≈ 0.4 × 3 = 1.2 per unit dose), and treated places keep 1/3 in
    the counterfactual, so the ATT is "by right versus the permit rule" (the true counterfactual includes
    the 0.4)."""
    errs, lams = [], []
    for seed in range(5):
        treated = [(T, -8.0) for T in (2019, 2020, 2021, 2022) for _ in range(2)]
        panel = simulate_d026(seed, treated, n_never=30, dose_pre=1 / 3)
        idx = panel["place"].str[1:].astype(int)
        k = panel["year"] - panel["T"]
        permit = (panel["T"].isna() & (idx % 3 == 0) & (panel["year"] >= 2019)) | (k >= -2)
        panel.loc[panel["T"].isna() & permit, "dose"] = 1 / 3
        panel.loc[permit, ["mu", "mu0_true"]] *= math.exp(0.4)
        panel["y"] = np.random.default_rng(seed).poisson(panel["mu"])
        r = est.impute(panel)
        lams.append(r.fit.coef_of("lambda_z_rule"))
        truth, _ = true_att(r, panel)
        errs.append((r.att["att"] - truth) / truth)
    assert np.mean(lams) == pytest.approx(1.2, abs=0.25)
    assert abs(np.mean(errs)) < 0.10


# ---- Checks (D-026) ----


def _with_extras(panel, seed, effect_5p=0.0):
    rng = np.random.default_rng(seed)
    e = panel["year"] - panel["T"]
    lvl = panel["eligible"] * 0.0005
    return panel.assign(
        units_5p=rng.poisson(lvl * np.exp(np.where(e >= 0, effect_5p, 0.0))), T_announce=panel["T"] - 1
    )


def test_checks_pass_on_a_clean_simulation():
    treated = [(T, -7.5) for T in (2019, 2020, 2021, 2022) for _ in range(3)]
    panel = _with_extras(simulate_d026(11, treated, n_never=20), 11)
    r = est.impute(panel)
    main = est.summarize_att(r, est.place_bootstrap(panel, draws=99, seed=11))
    kw = {"draws": 99, "seed": 11}
    assert est.check_pretrends(panel, **kw)["pass"]
    assert est.check_anticipation(panel, main, **kw)["pass"]
    assert est.check_placebo_dates(panel, **kw)["pass"]
    assert est.check_placebo_outcome(panel, **kw)["pass"]
    assert est.check_excluding(panel, main)["pass"]
    assert est.check_leave_one_out(panel, main)["pass"]
    never = sorted(panel.loc[panel["T"].isna(), "place"].unique())
    neighbors = {never[0]: {r.contributing[0]}, never[1]: {never[2]}}
    ring = est.check_first_ring(panel, main, neighbors)
    assert ring["dropped"] == [never[0]] and ring["pass"]
    assert est.check_first_ring(panel, main, None)["pass"] is None


def test_checks_catch_anticipation_and_a_responding_placebo():
    """Treated places build 50% more in the two years before adoption (announced two years early): the
    held-out pre-trend and anticipation checks fail. A 5+ unit outcome that responds to adoption fails the
    placebo."""
    treated = [(T, -7.5) for T in (2019, 2020, 2021, 2022) for _ in range(3)]
    panel = simulate_d026(12, treated, n_never=20)
    k = panel["year"] - panel["T"]
    panel["y"] = np.random.default_rng(12).poisson(panel["mu"] * np.where((k >= -2) & (k < 0), 1.5, 1.0))
    panel = _with_extras(panel, 12, effect_5p=0.6).assign(T_announce=lambda d: d["T"] - 2)
    main = est.summarize_att(est.impute(panel), est.place_bootstrap(panel, draws=99, seed=12))
    assert not est.check_pretrends(panel, draws=99, seed=12)["pass"]
    assert not est.check_anticipation(panel, main, draws=99, seed=12)["pass"]
    assert not est.check_placebo_outcome(panel, draws=99, seed=12)["pass"]


# ---- Transport (D-026), year effects after the panel (D-023 defect 7), household growth (defect 8) ----


def test_year_effect_after_the_panel_is_the_last_years():
    """Year effects peak in 2020 and fall after: for 2026-27 the 2025 effect is used (D-023 used the largest
    one, 2020's), and a no-effect target's predicted mean follows it."""
    panel = simulate_d026(14, [(2020, -8.0)] * 4, n_never=30, trend=0.0)
    bump = np.where(panel["year"] == 2020, math.exp(0.8), 1.0)
    panel["y"] = np.random.default_rng(14).poisson(panel["mu"] * bump)
    r = est.impute(panel)
    g = dict(zip(r.fit.years, r.fit.gamma, strict=True))
    assert max(g, key=g.get) == 2020
    assert est.year_effect(r.fit, 2027) == pytest.approx(g[2025])
    assert est.year_effect(r.fit, 2010) == pytest.approx(g[2016])
    # adopts in 2026 with a zero effect: 2024-25 set its level, 2026-27 are predicted
    target = pd.DataFrame(
        {
            "place": "X",
            "name": "X",
            "year": [2024, 2025, 2026, 2027],
            "y": [10, 10, 0, 0],
            "eligible": 10_000.0,
            "T": 2026.0,
            "dose": [0.0, 0.0, 1.0, 1.0],
            "mm": 0.0,
        }
    )
    boot = pd.DataFrame({f"att_{b}": [0.0] for b in est.BINS})
    pred = est.transport_predict(r, boot, target, draws=4000, seed=1).set_index("year")
    lvl = 20 / (10_000 * (math.exp(g[2024]) + math.exp(g[2025])))
    assert pred.loc[2027, "mean"] == pytest.approx(10_000 * lvl * math.exp(g[2025]), rel=0.1)


def test_household_growth_is_never_measured_after_adoption():
    """T = 2020: log(households 2019 / 2014). T = 2013: the 2007 vintage does not exist, so missing (D-023
    used 2015 over 2010, after adoption)."""
    hh = pd.Series({("place:1", y): 1000.0 * 1.02 ** (y - 2010) for y in range(2010, 2025)})
    assert est.household_growth(hh, "place:1", 2020) == pytest.approx(5 * math.log(1.02))
    assert np.isnan(est.household_growth(hh, "place:1", 2013))


def test_transport_predictions_cover_held_out_places_from_the_same_process():
    """Fit on simulated places, predict 12 held-out treated places from their own pre-adoption years: totals
    inside their 90% intervals for at least 80% of places, yearly 80% coverage at least 60%."""
    treated = [(T, -7.5) for T in (2018, 2019, 2020, 2021, 2022) for _ in range(6)]
    panel = simulate_d026(13, treated, n_never=30)
    held = panel.loc[panel["T"].notna(), "place"].unique()[::2][:12]
    fit_panel = panel[~panel["place"].isin(held)]
    r = est.impute(fit_panel)
    boot = est.place_bootstrap(fit_panel, draws=99, seed=13)
    pred = est.transport_predict(r, boot, panel[panel["place"].isin(held)], draws=1000, seed=13)
    assert est.transport_verdict(pred)["yearly_coverage_80"] >= 0.6
    tot = pred[pred["year"] == "total"]
    assert ((tot["observed"] >= tot["p05"]) & (tot["observed"] <= tot["p95"])).mean() >= 0.8


def test_transport_fails_loudly_on_an_absurd_rate():
    panel = simulate_d026(15, [(T, -8.0) for T in (2019, 2020, 2021)], n_never=10)
    r = est.impute(panel)
    boot = pd.DataFrame({f"att_{b}": [500.0] for b in est.BINS})  # 50% of parcels a year
    with pytest.raises(est.EstimationError, match="beyond"):
        est.transport_predict(r, boot, panel[panel["T"].notna()], draws=20, seed=1)
