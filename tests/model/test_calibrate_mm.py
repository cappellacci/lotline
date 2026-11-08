"""D-038: the missing-middle uptake calibration does what the analysis plan says (hand-worked examples and
simulated places; no real data)."""

import math
from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from lotline.model import calibrate_adu as cal_adu
from lotline.model import calibrate_mm as cal


def test_centred_mean_and_growth_index_by_hand():
    assert cal.centred_mean({1: 2, 2: 4, 3: 9}, 2) == 5
    assert cal.centred_mean({1: 2, 2: 4, 3: 9}, 3) == 6.5
    homes = {2017: 100, 2018: 100, 2019: 100, 2020: 150, 2021: 200, 2022: 250}
    assert cal.growth_index(homes, 2021, [2017, 2018, 2019]) == pytest.approx(2.0)
    assert cal.growth_index({2018: 10, 2020: 100}, 2020, [2018]) == 4.0  # capped
    assert cal.growth_index({2020: 100}, 2020, [2017, 2018]) == 1.0  # no pre-reform data


def test_feasibility_ratio_by_hand():
    # F(1.15) = Φ(0) = 0.5; F(1) = Φ(ln(1 / 1.15) / 0.5) = Φ(−0.2795) = 0.38993
    assert cal.feasibility_ratio(1.15, 0.15, 0.5) == pytest.approx(0.5 / 0.38993, rel=1e-4)
    assert cal.feasibility_ratio(1.0, 0.15, 0.5) == pytest.approx(1.0)


def test_poisson_limit():
    y, B, k = np.array([3.0, 0.0]), np.array([1.0, 0.5]), np.array([100.0, 200.0])
    mu = B + 0.01 * k
    expected = float(np.sum(y * np.log(mu) - mu))
    assert cal.place_loglik(y, B, k, 0.01, 1e-9) == pytest.approx(expected)


@pytest.mark.parametrize("alpha", [0.01, 0.5, 5.0])
def test_no_baseline_one_year_is_negative_binomial(alpha):
    y, k, theta = 4, 300.0, 0.01  # mean 3
    nb = cal_adu.nb_loglik([y], [theta * k], alpha) + math.lgamma(y + 1)
    assert cal.place_loglik([y], [0.0], [k], theta, alpha) == pytest.approx(nb, abs=2e-3)


def test_no_baseline_several_years_is_the_closed_form_frailty():
    y, k, theta, alpha = np.array([0.0, 2.0, 5.0]), np.array([100.0, 200.0, 400.0]), 0.01, 0.8
    closed = cal_adu.frailty_loglik_place(y, k, theta, alpha) + sum(math.lgamma(v + 1) for v in y)
    assert cal.place_loglik(y, np.zeros(3), k, theta, alpha) == pytest.approx(closed, abs=2e-3)


def test_baseline_plus_effect_by_hand():
    # y = 2, B = 1, θk = 1, α = 1 (u exponential): E[(1 + u)² e^-(1+u)] = e^-1 (1/2 + 2/4 + 1/4) = 1.25 e^-1
    assert cal.place_loglik([2], [1.0], [1.0], 1.0, 1.0) == pytest.approx(-1 + math.log(1.25), abs=2e-3)


def _place(T=2020, years=(2020, 2021), y=(5, 7), beta=1.0, g=(1.0, 1.0), kr=(1000.0, 1000.0), elig=1000.0):
    years = np.array(years)
    return cal.Place(
        geoid="x",
        name="X",
        T=T,
        beta=beta,
        years=years,
        y=np.array(y, dtype=float),
        g=np.array(g),
        kr=np.array(kr),
        age=years - T + 0.5,
        eligible=np.full(len(years), elig),
    )


def test_place_upto_and_baseline():
    p = _place(years=(2020, 2021, 2022), y=(1, 2, 3), g=(1.0, 2.0, 3.0), kr=(1.0, 1.0, 1.0))
    assert list(p.B) == [1.0, 2.0, 3.0]
    q = p.upto(2021)
    assert list(q.years) == [2020, 2021] and list(q.y) == [1, 2] and list(q.B) == [1.0, 2.0]


def test_score_by_hand():
    p = _place(y=(4, 6))
    s = cal.score(p, np.full(101, 14))
    assert s["observed"] == 10 and s["covered"] is False
    assert s["error_per_1000"] == pytest.approx(2.0)  # (14 − 10) / 2 years / 1,000 parcels × 1,000


def _panel():
    """Two treated places and one uncoded comparison, 2014-2023."""
    rows = []
    for gid, T, ys in (("a", 2018, [2, 2, 2, 2, 8, 9, 10, 12, 12, 12]), ("b", 2020, [1] * 6 + [3, 4, 5, 5])):
        for i, yr in enumerate(range(2014, 2024)):
            rows.append(
                dict(
                    place=gid,
                    name=gid,
                    state="NC",
                    status="treated",
                    year=yr,
                    T=T,
                    y_buildings=ys[i],
                    eligible=1000.0,
                    dose=0.5 if yr >= T else 0.0,
                    pcr=1.15,
                    units_1=90.0,
                    units_5p=10.0,
                )
            )
    for yr in range(2014, 2024):
        rows.append(
            dict(
                place="c",
                name="c",
                state="NC",
                status="uncoded",
                year=yr,
                T=np.nan,
                y_buildings=10.0,
                eligible=500.0,
                dose=0.0,
                pcr=np.nan,
                units_1=1.0,
                units_5p=0.0,
            )
        )
    return pd.DataFrame(rows)


def test_place_inputs_from_a_panel():
    ps = cal.place_inputs(_panel(), ["a", "b", "c"], margin=0.15, sigma=0.5)
    assert [p.geoid for p in ps] == ["a", "b"]  # c has no adoption year
    a = ps[0]
    assert a.beta == 2.0 and list(a.years) == list(range(2018, 2024))
    assert list(a.g) == [1.0] * 6  # flat other homes
    assert a.age[0] == 0.5
    assert a.kr[0] == pytest.approx(1000 * 0.5 * 0.5 / 0.38993, rel=1e-4)
    flat = cal.place_inputs(_panel(), ["a"], margin=0.15, sigma=0.5, feasibility=False)[0]
    assert flat.kr[0] == 500.0


def test_placebo_shift_uses_pre_reform_years_only():
    a = cal.place_inputs(_panel(), ["a"], margin=0.15, sigma=0.5, shift=3)[0]
    assert a.T == 2015 and list(a.years) == [2015, 2016, 2017]
    assert a.beta == 2.0 and np.all(a.kr > 0)


def test_fit_recovers_a_known_hazard():
    rng = np.random.default_rng(7)
    theta, alpha, half = 0.002, 0.3, 2.0
    places = []
    for i in range(30):
        years = np.arange(2018, 2018 + rng.integers(2, 8))
        kr = np.full(len(years), float(rng.integers(2000, 20000)))
        u = rng.gamma(1 / alpha, alpha)
        p = cal.Place(
            geoid=str(i),
            name=str(i),
            T=2018,
            beta=2.0,
            years=years,
            y=np.zeros(len(years)),
            g=np.ones(len(years)),
            kr=kr,
            age=years - 2018 + 0.5,
            eligible=kr,
        )
        y = rng.poisson(p.B + theta * u * p.k(half))
        places.append(cal.Place(**{**p.__dict__, "y": y.astype(float)}))
    f = cal.fit(places, halves=(1.0, 2.0, 3.0))
    assert f.low < theta < f.high
    assert f.low < f.theta < f.high
    assert f.half in (1.0, 2.0, 3.0)


def test_benchmark_none_is_the_baseline():
    p = _place(beta=3.0, y=(3, 3))
    draws = cal.benchmark_total(p, 0.0, 2.5, draws=20_000)
    assert draws.mean() == pytest.approx(6.0, rel=0.03)


@pytest.mark.parametrize("alpha", [1e-9, 0.01, 0.7])
def test_stacked_loglik_is_the_sum_over_places(alpha):
    a = _place(y=(5, 7), beta=1.0, kr=(1000.0, 1000.0))
    b = _place(years=(2021,), y=(0,), beta=0.0, g=(1.0,), kr=(500.0,))
    total = sum(cal.place_loglik(p.y, p.B, p.k(2.0), 0.003, alpha) for p in (a, b))
    assert cal.loglik([a, b], 0.003, alpha, 2.0) == pytest.approx(total)


# ---- D-042 ----


def _rules():
    return pd.DataFrame(
        {
            "reform_id": ["old", "big", "new"],
            "effective_date": ["2010-01-01", "2010-01-01", "2024-02-05"],
            "end_date": [None, None, None],
            "unit_cap": ["2", "3", "8"],
        }
    )


def test_prior_cap_by_hand():
    cov = {"old": 0.7, "big": 0.2, "new": 1.0}
    assert cal.prior_cap(_rules(), 2023, cov) == 2  # big covers under half; new not yet in force
    assert cal.prior_cap(_rules(), 2023, {"big": 0.2}) == 1
    assert cal.prior_cap(_rules(), 2024, cov) == 8
    assert cal.prior_cap(_rules().iloc[0:0], 2023, cov) == 1


def test_event_year_by_hand():
    assert cal.event_year(2020.0, {}) == 2020
    path = {y: 0.3 for y in range(2010, 2024)} | {2024: 0.5, 2025: 0.5}
    assert cal.event_year(1990.0, path) == 2024
    assert np.isnan(cal.event_year(1990.0, {y: 0.3 for y in range(2010, 2026)}))
    assert np.isnan(cal.event_year(np.nan, {}))


def test_outcome_classes():
    assert cal.outcome_classes(1) == ("bldgs_2", "bldgs_3_4")
    assert cal.outcome_classes(2) == ("bldgs_3_4",)
    assert cal.outcome_classes(4) == ()


def _classes():
    idx = pd.MultiIndex.from_product([["a", "c"], range(2014, 2024)], names=["geoid", "year"])
    return pd.DataFrame({"bldgs_2": 5.0, "bldgs_3_4": 1.0}, index=idx)


def test_retarget_counts_classes_above_the_prior_cap_and_the_dose_increase():
    p = _panel()
    p.loc[p["place"] == "a", "dose"] = np.where(p.loc[p["place"] == "a", "year"] >= 2018, 0.5, 0.2)
    r = cal.retarget(p, _classes(), {"a": (2018, 2)})
    assert set(r["place"]) == {"a"}
    assert (r["y_buildings"] == 1.0).all()  # 3-4 unit class only, every year
    assert (r["T"] == 2018).all()
    assert r.loc[r["year"] == 2019, "dose"].iloc[0] == pytest.approx(0.3)  # 0.5 − 0.2 in force in 2017
    assert r.loc[r["year"] == 2015, "dose"].iloc[0] == 0.0
    r1 = cal.retarget(p, _classes(), {"a": (2018, 1)})
    assert (r1["y_buildings"] == 6.0).all()


def test_comparison_series_sums_never_treated_places():
    by_state, pool = cal.comparison_series(_panel(), _classes(), ["bldgs_3_4"])
    assert by_state == {"NC": {y: 1.0 for y in range(2014, 2024)}}  # only c; a is treated
    assert pool == by_state["NC"]


def test_baseline_series_falls_back_to_the_pool():
    state, pool = {2019: 5, 2020: 10, 2021: 15}, {2019: 100, 2020: 100, 2021: 100}
    assert cal.baseline_series(state, pool, [2019, 2020, 2021]) == pool
    assert cal.baseline_series(state, pool, [2019, 2020, 2021], min_mean=10) == state


def test_capacity_z_by_hand():
    z = cal.capacity_z({"a": 0.0, "b": math.e - 1})
    assert z["a"] == pytest.approx(-0.5) and z["b"] == pytest.approx(0.5)


def test_given_series_is_the_growth_index():
    series = {y: 10.0 for y in range(2014, 2024)} | {2021: 40.0, 2022: 40.0, 2023: 40.0}
    a = cal.place_inputs(_panel(), ["a"], 0.15, 0.5, growth="given", series_by_place={"a": series})[0]
    assert a.g[list(a.years).index(2022)] == pytest.approx(4.0)  # (40 + 40 + 40) / 3 over 10, at the cap
    assert a.g[0] == pytest.approx(1.0)


def test_fit_capacity_recovers_a_known_slope():
    rng = np.random.default_rng(11)
    theta, b, half = 0.002, 1.0, 2.0
    places = []
    for i in range(40):
        years = np.arange(2018, 2018 + rng.integers(3, 8))
        kr = np.full(len(years), float(rng.integers(3000, 20000)))
        z = float(rng.normal(0, 1))
        p = cal.Place(str(i), str(i), 2018, 1.0, years, np.zeros(len(years)), np.ones(len(years)), kr,
                      years - 2018 + 0.5, kr, z)  # fmt: skip
        mu = p.B + theta * math.exp(b * z) * p.k(half)
        places.append(replace(p, y=rng.poisson(mu).astype(float)))
    cf = cal.fit_capacity(places, slopes=(0.0, 0.5, 1.0, 1.5), halves=(2.0,))
    assert cf.b_low <= b <= cf.b_high
    assert cf.fit.low < theta < cf.fit.high
    assert cf.b in (0.5, 1.0, 1.5)


def test_scaled_folds_the_slope_into_exposure():
    p = replace(_place(), z=0.5)
    assert cal.scaled([p], 2.0)[0].kr[0] == pytest.approx(1000.0 * math.e)


# ---------------------------------------------------------------------------------------------------------
# D-054: statewide backtest and the state spread
# ---------------------------------------------------------------------------------------------------------


def _simple(geoid, y=(1,), B=(0.0,), kr=(1.0,), z=0.0):
    n = len(y)
    return cal.Place(
        geoid=geoid,
        name=geoid,
        T=2020,
        beta=1.0,
        years=np.arange(2020, 2020 + n),
        y=np.array(y, float),
        g=np.array(B, float),  # beta 1, so B = g
        kr=np.array(kr, float),
        age=np.full(n, 50.0),  # ramp ≈ 1
        eligible=np.full(n, 1000.0),
        z=z,
    )


def test_verdict_by_hand():
    assert cal.verdict(50, 13, 57, 193) == "useful"
    assert cal.verdict(519, 52, 213, 781) == "inside only"
    assert cal.verdict(2785, 45, 319, 1420) == "missed"
    assert cal.verdict(0, 0, 0, 3) == "useful"
    assert cal.verdict(0, 0, 1, 3) == "inside only"


def test_predict_places_shares_theta_and_keys_place_draws():
    a, b = _simple("a", kr=(1000.0,)), _simple("b", kr=(1000.0,))
    one = cal.predict_places([a], 0.002, 0.5, 1e-9, 2.0, draws=4000, seed=7)
    two = cal.predict_places([a, b], 0.002, 0.5, 1e-9, 2.0, draws=4000, seed=7)
    np.testing.assert_array_equal(one["a"], two["a"])  # a draws alike whichever places it is with
    # θ is shared: the two places' totals are positively correlated through θ alone (u ≡ 1 here)
    assert np.corrcoef(two["a"][:, 0], two["b"][:, 0])[0, 1] > 0.3
    # no θ uncertainty, Poisson: mean θ k = 2
    flat = cal.predict_places([a], 0.002, 0.0, 1e-9, 2.0, draws=20000, seed=1)["a"]
    assert flat.mean() == pytest.approx(2.0, rel=0.03)


def test_predict_places_capacity_scaling():
    p = _simple("a", kr=(1000.0,), z=1.0)
    d = cal.predict_places([p], 0.001, 0.0, 1e-9, 2.0, b=math.log(3.0), draws=20000, seed=2)["a"]
    assert d.mean() == pytest.approx(3.0, rel=0.03)  # θ k exp(b z) = 1 × 3


def test_state_total_and_benchmarks():
    a, b = _simple("a", y=(1, 2), B=(2.0, 2.0), kr=(0.0, 0.0)), _simple("b", B=(1.0,))
    none = cal.benchmark_places([a, b], 0.0, 2.5, draws=20000, seed=3)
    assert cal.state_total(none, ["a", "b"]).mean() == pytest.approx(5.0, rel=0.03)


def test_heldout_log_score_by_hand():
    p = _simple("a", y=(1,), B=(0.0,), kr=(1.0,))
    assert cal.heldout_log_score(p, 2.0, 0.0, 1e-9, 2.0) == pytest.approx(math.log(2.0) - 2.0, abs=1e-6)
    # with θ uncertainty: E over ln θ ~ N(ln 2, 0.3²) of θ e^-θ, by brute-force quadrature
    xs = np.linspace(-8, 8, 20001)
    th = 2.0 * np.exp(0.3 * xs)
    dens = np.exp(-(xs**2) / 2) / math.sqrt(2 * math.pi)
    expected = math.log(np.trapezoid(th * np.exp(-th) * dens, xs))
    assert cal.heldout_log_score(p, 2.0, 0.3, 1e-9, 2.0) == pytest.approx(expected, abs=1e-6)
    assert cal.no_effect_log_score(_simple("b", y=(2,), B=(1.5,))) == pytest.approx(2 * math.log(1.5) - 1.5)


def test_state_loglik_by_hand():
    p = _simple("a", y=(0,), B=(0.0,), kr=(1.0,))
    theta, tau = 0.7, 0.4
    by_hand = math.log(0.5 * math.exp(-theta * math.exp(tau)) + 0.5 * math.exp(-theta * math.exp(-tau)))
    assert cal.state_loglik([p], ["S"], theta, 1e-9, 2.0, tau, n=2) == pytest.approx(by_hand, abs=1e-6)
    # τ = 0 is the ordinary likelihood; two states add
    q = _simple("b", y=(3,), B=(1.0,), kr=(2.0,))
    base = cal.loglik([p, q], theta, 0.5, 2.0)
    assert cal.state_loglik([p, q], ["S", "T"], theta, 0.5, 2.0, 0.0) == pytest.approx(base)
    two = cal.state_loglik([p], ["S"], theta, 0.5, 2.0, tau) + cal.state_loglik(
        [q], ["T"], theta, 0.5, 2.0, tau
    )
    assert cal.state_loglik([p, q], ["S", "T"], theta, 0.5, 2.0, tau) == pytest.approx(two)


def test_tau_profile_recovers_no_spread_and_summary():
    rng = np.random.default_rng(0)
    places, states = [], []
    for s in "ABCD":  # four states, same θ, Poisson places: τ̂ should sit at or near 0
        for j in range(4):
            k = np.full(3, 2000.0)
            places.append(_simple(f"{s}{j}", y=rng.poisson(0.001 * k), B=(0.0,) * 3, kr=k))
            states.append(s)
    prof = cal.tau_profile(places, states, 2.0, taus=(0.0, 0.5, 1.0, 2.5))
    assert prof.loc[prof["ll"].idxmax(), "tau"] <= 0.5
    s = cal.tau_summary(prof, draws=5000, seed=1)
    assert s["tau_low"] == 0.0 and s["multiplier_p10"] <= 1 <= s["multiplier_p90"]


def test_tau_summary_by_hand():
    # equal profile at τ 0 and 1, far lower elsewhere: half the draws at 0, the 90% set is {0, 1}
    prof = pd.DataFrame({"tau": [0.0, 1.0, 2.5], "ll": [0.0, 0.0, -50.0]})
    s = cal.tau_summary(prof, draws=20000, seed=2)
    assert (s["tau_hat"], s["tau_low"], s["tau_high"], s["estimable"]) == (0.0, 0.0, 1.0, True)
    assert s["share_at_0"] == pytest.approx(0.5, abs=0.02)
    # multiplier: 0.5 × point mass at 1 + 0.5 × lognormal(0, 1); P90 solves 0.5 + 0.5 Φ(ln m) = 0.9
    assert s["multiplier_p90"] == pytest.approx(math.exp(0.8416), rel=0.05)


# ---------------------------------------------------------------------------------------------------------
# D-058: stability test, widened baseline, zero floor
# ---------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(("x", "df"), [(3.841, 1), (5.991, 2), (11.070, 5), (18.307, 10)])
def test_chi2_sf_at_the_5pct_critical_values(x, df):
    assert cal.chi2_sf(x, df) == pytest.approx(0.05, abs=2e-4)


def test_chi2_sf_by_hand():
    assert cal.chi2_sf(0.0, 3) == 1.0
    assert cal.chi2_sf(2.0, 2) == pytest.approx(math.exp(-1.0))  # 2 df: P(χ² >= x) = e^(-x/2)
    assert cal.chi2_sf(60.0, 2) == pytest.approx(math.exp(-30.0), rel=1e-6)


def test_dispersion_test_by_hand():
    assert cal.dispersion_test([10, 10, 10]) | {} == {
        "n": 3, "stat": 0.0, "p": 1.0, "testable": True, "unstable": False
    }  # fmt: skip
    t = cal.dispersion_test([0, 0, 30])
    assert t["stat"] == pytest.approx(60.0) and t["unstable"]
    assert not cal.dispersion_test([4, 6])["testable"]  # fewer than 3 years
    assert not cal.dispersion_test([0, 0, 0, 0])["testable"]  # mean 0
    # a Poisson-like pace: (8, 12, 10, 9, 11, 10) -> D = (4 + 4 + 0 + 1 + 1 + 0) / 10 = 1.0 on 5 df: stable
    assert cal.dispersion_test([8, 12, 10, 9, 11, 10])["stat"] == pytest.approx(1.0)
    assert not cal.dispersion_test([8, 12, 10, 9, 11, 10])["unstable"]


def _pre_post_panel(pre, post, T=2020, place="p1"):
    """One place: outcome `pre` over the years before T (ending T − 1) and `post` from T; other homes flat."""
    years = list(range(T - len(pre), T + len(post)))
    y = list(pre) + list(post)
    return pd.DataFrame(
        {
            "place": place,
            "name": "P",
            "state": "TX",
            "status": "coded",
            "year": years,
            "T": float(T),
            "y_buildings": [float(v) for v in y],
            "units_1": 100.0,
            "units_5p": 0.0,
            "eligible": 1000.0,
            "dose": [0.0] * len(pre) + [1.0] * len(post),
            "pcr": 1.0,
        }
    )


def test_baseline_rule_widens_only_unstable_places():
    surge = _pre_post_panel(pre=(10, 10, 10, 100, 110, 120), post=(20, 20))  # recent years 11x the earlier
    steady = _pre_post_panel(pre=(9, 11, 10, 10, 9, 11), post=(20, 20), place="p2")
    panel = pd.concat([surge, steady], ignore_index=True)
    fixed = cal.place_inputs(panel, ["p1", "p2"], 0.15, 0.5)
    stab = cal.place_inputs(panel, ["p1", "p2"], 0.15, 0.5, baseline_rule="stability")
    long = cal.place_inputs(panel, ["p1", "p2"], 0.15, 0.5, baseline_rule="long")
    assert fixed[0].beta == pytest.approx(110.0) and not fixed[0].unstable
    assert stab[0].beta == pytest.approx(60.0) and stab[0].unstable  # mean of all six years
    assert stab[1].beta == pytest.approx(10.0) and not stab[1].unstable  # steady place unchanged
    assert long[1].beta == pytest.approx(10.0) and long[0].beta == pytest.approx(60.0)
    assert list(stab[0].g) == [1.0, 1.0]  # other homes flat: the growth index stays 1 on either window


def test_zero_floor():
    p = _pre_post_panel(pre=(0, 0, 0), post=(3,))
    assert cal.place_inputs(p, ["p1"], 0.15, 0.5)[0].beta == 0.0
    assert cal.place_inputs(p, ["p1"], 0.15, 0.5, zero_floor=True)[0].beta == pytest.approx(0.5 / 3)
    # the floor makes no effect's log score finite: log Poisson(3; 1/6)
    q = cal.place_inputs(p, ["p1"], 0.15, 0.5, zero_floor=True)[0]
    assert cal.no_effect_log_score(q) == pytest.approx(3 * math.log(0.5 / 3) - 0.5 / 3)


# ---- D-062: the five-year rate ----


def test_ramp_mean_by_hand():
    # slope 0.75, ages 0.5 ... 4.5: half 0.5 -> (0.5 + 0.7914 + 0.9350 + 0.9820 + 0.9952) / 5
    assert cal.ramp_mean(0.5) == pytest.approx(0.8407, abs=1e-4)
    # half 6.0 -> (0.00065 + 0.00248 + 0.00932 + 0.03445 + 0.11920) / 5
    assert cal.ramp_mean(6.0) == pytest.approx(0.0332, abs=1e-4)
    assert cal.ramp_mean(2.0, ages=(2.0,)) == pytest.approx(0.5)


def _synthetic_places(seed=7, n=30, theta=0.002, alpha=0.3, half=2.0):
    rng = np.random.default_rng(seed)
    places = []
    for i in range(n):
        years = np.arange(2018, 2018 + rng.integers(2, 8))
        kr = np.full(len(years), float(rng.integers(2000, 20000)))
        p = cal.Place(str(i), str(i), 2018, 2.0, years, np.zeros(len(years)), np.ones(len(years)), kr,
                      years - 2018 + 0.5, kr)  # fmt: skip
        y = rng.poisson(p.B + theta * rng.gamma(1 / alpha, alpha) * p.k(half))
        places.append(replace(p, y=y.astype(float)))
    return places


def test_five_year_profile_with_one_half_is_theta_times_m():
    places = _synthetic_places()
    f = cal.fit(places, halves=(2.0,))
    p = cal.five_year_profile(places, halves=(2.0,))
    m = cal.ramp_mean(2.0)
    assert p.r5 == pytest.approx(f.theta * m, rel=1e-3)
    assert p.low == pytest.approx(f.low * m, rel=1e-2)
    assert p.high == pytest.approx(f.high * m, rel=1e-2)
    assert p.loglik == pytest.approx(f.loglik, abs=1e-6)


def test_five_year_profile_maximum_is_the_fit():
    places = _synthetic_places()
    halves = (1.0, 2.0, 3.0)
    f = cal.fit(places, halves=halves)
    p = cal.five_year_profile(places, halves=halves)
    assert p.r5 == pytest.approx(f.theta * cal.ramp_mean(f.half), rel=1e-3)
    assert p.low < p.r5 < p.high
    assert list(p.by_half["half"]) == list(halves)
    for h, ll in f.profile_half.items():
        assert p.by_half.set_index("half").loc[h, "loglik"] == pytest.approx(ll, abs=1e-6)
