"""V1 backtest harness: scoring by hand, no peeking past the fit end, exclusions, and the pass rules."""

import numpy as np
import pandas as pd
import pytest

from lotline.config import load_params
from lotline.model import backtest

PARAMS = load_params("baseline")


def test_v1_windows_from_config():
    assert backtest.fit_ends(PARAMS) == [2016, 2018, 2020]


def test_placeholder_exclusions_are_the_known_reformers():
    assert backtest.excluded_places() == {"2743000", "2758000", "3755000", "3719000", "3712000", "4805000"}


def _results(rows):
    cols = ["state", "fit_end", "size_class", "year", "method", "actual", "forecast", "mean", "p10", "p90"]
    df = pd.DataFrame(rows, columns=cols)
    return df.assign(coverage_rand=np.where(df["method"] == "model", 0.5, np.nan))


# One state, fit end 2020, two place-years (2021 and 2023), rates per 1,000 parcels:
#   actual            4,  10
#   model P50         5,   6   (P10-P90 [2, 8] and [7, 12]; mean 6, 8)
#   last_k_mean       0,  10
#   linear_trend     10,  20
# MAE: model (1 + 4) / 2 = 2.5; last_k (4 + 0) / 2 = 2; trend (6 + 10) / 2 = 8.
# Coverage (inclusive): 4 in [2, 8] yes, 10 in [7, 12] yes -> 1.0. Randomized coverage: mean 0.5.
# Post-2022 (2023 only): model bias 6 − 10 = −4 on the P50, 8 − 10 = −2 on the mean; MAE 4.
TOY = _results(
    [
        ("NC", 2020, "1", 2021, "model", 4, 5, 6, 2, 8),
        ("NC", 2020, "1", 2023, "model", 10, 6, 8, 7, 12),
        ("NC", 2020, "1", 2021, "last_k_mean", 4, 0, np.nan, np.nan, np.nan),
        ("NC", 2020, "1", 2023, "last_k_mean", 10, 10, np.nan, np.nan, np.nan),
        ("NC", 2020, "1", 2021, "linear_trend", 4, 10, np.nan, np.nan, np.nan),
        ("NC", 2020, "1", 2023, "linear_trend", 10, 20, np.nan, np.nan, np.nan),
    ]
)


def test_score_by_hand():
    s = backtest.score(TOY, PARAMS).set_index("method")
    assert s["mae"].to_dict() == pytest.approx({"model": 2.5, "last_k_mean": 2.0, "linear_trend": 8.0})
    assert s.loc["model", "coverage"] == 1.0
    assert s.loc["model", "coverage_rand"] == 0.5
    assert np.isnan(s.loc["last_k_mean", "coverage"])
    assert s.loc["model", "bias_post"] == -4.0
    assert s.loc["model", "bias_post_mean"] == -2.0
    assert s.loc["model", "mae_post"] == 4.0
    assert s.loc["last_k_mean", "bias_post"] == 0.0


def test_verdict_by_hand():
    """Model MAE 2.5 loses to last_k 2.0; randomized coverage 0.5 < 0.70; |−2| > 0.25 × 4 = 1."""
    v = backtest.verdict(backtest.score(TOY, PARAMS), PARAMS).iloc[0]
    flags = ["beats_benchmarks", "coverage_ok", "bias_ok", "passes"]
    assert v[flags].tolist() == [False] * 4
    better = TOY.copy()
    better.loc[better["method"] == "last_k_mean", "forecast"] = [0, 0]  # MAE (4 + 10) / 2 = 7
    better["coverage_rand"] = better["coverage_rand"].where(better["method"] != "model", 0.8)
    better.loc[better["method"] == "model", "mean"] = [6, 9]  # post-2022 bias −1, |−1| <= 1
    v = backtest.verdict(backtest.score(better, PARAMS), PARAMS).iloc[0]
    assert v[flags].tolist() == [True] * 4


def test_no_post_2022_years_is_not_a_bias_failure():
    early = TOY[TOY["year"] < 2023]
    v = backtest.verdict(backtest.score(early, PARAMS), PARAMS).iloc[0]
    assert bool(v["bias_ok"])


def _panel(seed=0, places=24, years=range(1992, 2026)):
    """A stationary synthetic state: Poisson permits at a fixed rate per place. Includes 4805000 (excluded
    as a placeholder reformer)."""
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(places):
        geoid = "4805000" if i == 0 else f"48{i:05d}"
        parcels = int(rng.integers(50, 5000))
        rate = float(rng.gamma(2.0, 5.0))
        for y in years:
            n = int(rng.poisson(rate * parcels / 1000))
            rows.append((geoid, f"C{i % 3}", y, n, n, parcels))
    cols = ["geoid", "county_geoid", "year", "units_1", "units_1_rep", "eligible_parcels"]
    return pd.DataFrame(rows, columns=cols).assign(state="TX")


def test_window_rows_methods_and_exclusion():
    w = backtest.window(_panel(), "1", 2020, params=PARAMS, excluded=backtest.excluded_places())
    assert set(w["method"]) == set(backtest.METHODS)
    assert "4805000" not in set(w["geoid"])
    assert w["year"].min() == 2021 and w["year"].max() == 2025  # 2025 cap
    assert (w.groupby(["geoid", "year"]).size() == 3).all()  # same place-years for every method
    assert set(w["tercile"]) == set(backtest.TERCILES)
    model = w[w["method"] == "model"]
    assert model["coverage_rand"].between(0, 1).all()


def test_window_caps_at_last_outcome_year():
    w = backtest.window(_panel(), "1", 2016, params=PARAMS, excluded=set())
    assert w["year"].max() == 2021  # 2016 + 5
    w = backtest.window(_panel(years=range(1992, 2023)), "1", 2020, params=PARAMS, excluded=set())
    assert w["year"].max() == 2022  # no outcomes after 2022


def test_window_forecasts_never_see_outcomes():
    """Changing every outcome after the fit end changes `actual`, never a forecast."""
    p = _panel()
    late = p.copy()
    late.loc[late["year"] > 2018, ["units_1", "units_1_rep"]] *= 7
    a = backtest.window(p, "1", 2018, params=PARAMS, excluded=set())
    b = backtest.window(late, "1", 2018, params=PARAMS, excluded=set())
    for col in ("forecast", "mean", "p10", "p90"):
        pd.testing.assert_series_equal(a[col], b[col])
    assert not a["actual"].equals(b["actual"])


def test_model_is_calibrated_and_competitive_in_a_stationary_world():
    """Where nothing changes, the model's band should cover about 80% and its error should not lose to the
    3-year mean (it averages more years and shrinks noisy places)."""
    p = _panel(places=40)
    res = backtest.run({"TX": p}, ("1",), params=PARAMS, excluded=set())
    v = backtest.verdict(backtest.score(res, PARAMS), PARAMS)
    assert v["coverage_rand"].between(0.7, 0.95).all()
    assert (v["mae_model"] <= v["mae_last_k_mean"]).all()
    assert (v["mae_model"] < v["mae_linear_trend"]).all()
