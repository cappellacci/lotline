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
