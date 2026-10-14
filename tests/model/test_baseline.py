"""V1 benchmarks (validation plan V1): last-k-year mean and linear trend, each checked by hand."""

import math

import pandas as pd
import pytest

from lotline.config import load_params
from lotline.model import baseline

PARAMS = load_params("baseline")
K = int(PARAMS["benchmark_mean_years"].value)
H = int(PARAMS["forecast_horizon_years"].value)


def test_config_matches_the_preregistered_benchmark():
    assert (K, H) == (3, 5)


def test_last_3_year_mean_by_hand():
    """Origin 2019, k = 3: mean(2017, 2018, 2019) = (20 + 30 + 50) / 3 = 33.33 for each of 2020-2024.
    The 2020 value (70) is after the origin and must not be used."""
    s = pd.Series({2016: 10, 2017: 20, 2018: 30, 2019: 50, 2020: 70})
    fc = baseline.last_k_mean(s, origin=2019, k=K, horizon=H)
    assert list(fc.index) == [2020, 2021, 2022, 2023, 2024]
    assert fc.tolist() == pytest.approx([100 / 3] * 5)


def test_last_k_mean_is_missing_when_a_window_year_is_missing():
    s = pd.Series({2017: 20, 2019: 50})
    assert baseline.last_k_mean(s, origin=2019, k=K, horizon=H).isna().all()


def test_linear_trend_by_hand():
    """Years 2015-2019, values 10, 12, 14, 13, 16. t̄ = 2017, ȳ = 13.
    Σ(t−t̄)(y−ȳ) = (−2)(−3) + (−1)(−1) + 0·1 + 1·0 + 2·3 = 13; Σ(t−t̄)² = 4 + 1 + 0 + 1 + 4 = 10; b = 1.3.
    ŷ(t) = 13 + 1.3 (t − 2017): 2020 → 16.9, 2021 → 18.2, 2022 → 19.5, 2023 → 20.8, 2024 → 22.1."""
    s = pd.Series({2015: 10, 2016: 12, 2017: 14, 2018: 13, 2019: 16})
    fc = baseline.linear_trend(s, origin=2019, horizon=H)
    assert fc.tolist() == pytest.approx([16.9, 18.2, 19.5, 20.8, 22.1])


def test_linear_trend_floors_at_zero():
    """10, 6, 2 over 2017-2019: b = −4, ŷ(2020) = 6 − 4·2 = −2 → 0. Permits can't be negative."""
    fc = baseline.linear_trend(pd.Series({2017: 10, 2018: 6, 2019: 2}), origin=2019, horizon=H)
    assert fc.tolist() == [0.0] * 5


def test_linear_trend_fit_window_and_minimum_points():
    """first_year = 2015 drops the 1990 outlier, leaving the hand-worked series above."""
    s = pd.Series({1990: 1000, 2015: 10, 2016: 12, 2017: 14, 2018: 13, 2019: 16})
    assert baseline.linear_trend(s, 2019, H, first_year=2015)[2020] == pytest.approx(16.9)
    assert baseline.linear_trend(pd.Series({2019: 5}), 2019, H).isna().all()


def test_benchmarks_never_see_years_after_the_origin():
    early = pd.Series({2015: 10, 2016: 12, 2017: 14, 2018: 13, 2019: 16})
    late = pd.concat([early, pd.Series({2020: 999, 2021: 0})])
    for fn in (lambda s: baseline.last_k_mean(s, 2019, K, H), lambda s: baseline.linear_trend(s, 2019, H)):
        pd.testing.assert_series_equal(fn(early), fn(late))


def test_benchmark_forecasts_for_a_panel():
    """Two places × two benchmarks × 5 years = 20 rows; place B's mean is (2 + 4 + 6) / 3 = 4, its trend
    is 2 per year, so 2020 → 8."""
    panel = pd.DataFrame(
        {
            "geoid": ["A"] * 5 + ["B"] * 3 + ["B"],
            "year": [2015, 2016, 2017, 2018, 2019, 2017, 2018, 2019, 2020],
            "units_1": [10, 12, 14, 13, 16, 2, 4, 6, 500],
        }
    )
    out = baseline.benchmark_forecasts(panel, "units_1", origin=2019, params=PARAMS)
    assert len(out) == 20
    b = out[out["geoid"] == "B"].set_index(["benchmark", "year"])["forecast"]
    assert b[("last_k_mean", 2020)] == pytest.approx(4.0)
    assert b[("linear_trend", 2020)] == pytest.approx(8.0)
    a = out[(out["geoid"] == "A") & (out["benchmark"] == "linear_trend")]
    assert a["forecast"].tolist() == pytest.approx([16.9, 18.2, 19.5, 20.8, 22.1])
    assert not any(math.isnan(x) for x in out["forecast"])
