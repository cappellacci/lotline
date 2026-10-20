"""V1 backtest harness: scoring by hand, no peeking past the fit end, exclusions, and the pass rules."""

import numpy as np
import pandas as pd
import pytest

from lotline.config import load_params
from lotline.model import backtest, baseline

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


def test_crps_by_hand():
    """Docstring example: draws 0, 2 and y = 1 -> 0.5. All draws at y -> 0. All at 3, y = 1 -> |3 − 1| = 2."""
    draws = np.array([[0, 2], [1, 1], [3, 3]])
    assert baseline.crps_from_draws(draws, np.array([1, 1, 1])) == pytest.approx([0.5, 0.0, 2.0])


def test_pit_histogram_by_hand():
    """Draws 0, 0, 0, 1 and y = 0: the PIT step is [0, 0.75], so each decile below 0.7 gets 0.1 / 0.75 =
    0.1333, 0.7-0.8 gets 0.05 / 0.75 = 0.0667 and the top two none. The masses sum to 1."""
    lo, hi = baseline.pit_step(np.array([[0, 0, 0, 1]]), np.array([0]))
    states = pd.DataFrame({"scope": ["year"], "pit_lo": lo, "pit_hi": hi})
    h = backtest.pit_histogram(states).drop(columns="scope").iloc[0].to_numpy()
    assert h == pytest.approx([0.4 / 3] * 7 + [0.2 / 3, 0.0, 0.0])
    assert h.sum() == pytest.approx(1.0)


def test_score_state_by_hand():
    """Two state-years: actual 100 and 200; P50 of the summed draws 110 and 150; means 120 and 180;
    last-k sums 90 and 260; trend sums 100 and 200. MAE model (10 + 50) / 2 = 30, last-k (10 + 60) / 2 = 35,
    trend 0; bias of the mean (20 − 20) / 2 = 0; ratio (120 + 180) / 300 = 1."""
    states = pd.DataFrame(
        {
            "state": "TX",
            "fit_end": 2020,
            "size_class": "1",
            "scope": "year",
            "actual": [100.0, 200.0],
            "p50": [110.0, 150.0],
            "mean": [120.0, 180.0],
            "fc_last_k_mean": [90.0, 260.0],
            "fc_linear_trend": [100.0, 200.0],
            "coverage_rand": [1.0, 0.5],
            "crps": [4.0, 6.0],
        }
    )
    s = backtest.score_state(states).iloc[0]
    assert (s["n"], s["mae_model"], s["mae_last_k_mean"], s["mae_linear_trend"]) == (2, 30.0, 35.0, 0.0)
    assert (s["coverage_rand"], s["crps"], s["bias_mean"], s["ratio_mean"]) == (0.75, 5.0, 0.0, 1.0)


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
    """Where nothing changes, the model's band should cover about 80% and its error should stay close to the
    3-year mean's and beat the trend's.

    Before D-026 the model never lost to the 3-year mean here. Since D-026 the cycle starts at the state's
    origin-year total, which in a world with no cycle is only that year's sampling noise (about ±3% for these
    40 places), so the model can lose by a few percent (2 of 3 windows, by up to 5%). That is the price of
    the random-walk start where there is no random walk; with a common cycle it is what makes the state
    totals calibrated (`test_state_totals_are_calibrated_under_a_common_cycle`)."""
    p = _panel(places=40)
    res = backtest.run({"TX": p}, ("1",), params=PARAMS, excluded=set())
    v = backtest.verdict(backtest.score(res, PARAMS), PARAMS)
    assert v["coverage_rand"].between(0.7, 0.95).all()
    assert (v["mae_model"] <= 1.1 * v["mae_last_k_mean"]).all()
    assert (v["mae_model"] < v["mae_linear_trend"]).all()


def test_state_window_sums_the_scored_places():
    """State totals are sums over exactly the scored place-years: observed counts, benchmark counts and
    (draw by draw) the model's draws; the window total is the sum of the five years."""
    panel = _panel()
    w = backtest.window(panel, "1", 2018, params=PARAMS, excluded=backtest.excluded_places())
    st = backtest.state_window(panel, "1", 2018, params=PARAMS, excluded=backtest.excluded_places())
    years = st[st["scope"] == "year"].set_index("year")
    model = w[w["method"] == "model"]
    counts = (model["actual"] * model["parcels"] / 1000).groupby(model["year"]).sum()
    assert years["actual"].to_numpy() == pytest.approx(counts.to_numpy())
    assert (years["places"] == 23).all()  # 24 places less the excluded reformer
    lk = w[w["method"] == "last_k_mean"]
    assert years["fc_last_k_mean"].to_numpy() == pytest.approx(
        (lk["forecast"] * lk["parcels"] / 1000).groupby(lk["year"]).sum().to_numpy()
    )
    total = st[st["scope"] == "total"].iloc[0]
    assert total["actual"] == pytest.approx(years["actual"].sum())
    assert total["mean"] == pytest.approx(years["mean"].sum(), rel=1e-9)  # draw-by-draw sums add up
    assert (st["p10"] <= st["p50"]).all() and (st["p50"] <= st["p90"]).all()
    assert st["coverage_rand"].between(0, 1).all() and (st["crps"] >= 0).all()
    assert (st["pit_lo"] <= st["pit_hi"]).all()
    places, states = backtest.run(
        {"TX": panel}, ("1",), params=PARAMS, excluded=backtest.excluded_places(), state_totals=True
    )
    assert set(states["fit_end"]) == {2016, 2018, 2020} and set(states["scope"]) == {"year", "total"}
    pd.testing.assert_frame_equal(
        states[states["fit_end"] == 2018].reset_index(drop=True), st.reset_index(drop=True)
    )


def test_places_below_the_minimum_size_are_forecast_but_not_scored():
    """Decision 5: a place with fewer than v1_min_eligible_parcels (20) eligible parcels at the origin is
    left out of scoring. Shrink one place to 10 parcels: it disappears from the window; others stay."""
    panel = _panel()
    small = panel["geoid"] == "4800003"
    panel.loc[small, "eligible_parcels"] = 10
    out = backtest.window(panel, "1", 2018, params=PARAMS, excluded=backtest.excluded_places())
    assert "4800003" not in set(out["geoid"]) and out["geoid"].nunique() == 22  # 24 - reformer - small one
    no_floor = PARAMS | {
        "v1_min_eligible_parcels": PARAMS["v1_min_eligible_parcels"].model_copy(update={"value": 0.0})
    }
    out0 = backtest.window(panel, "1", 2018, params=no_floor, excluded=backtest.excluded_places())
    assert "4800003" in set(out0["geoid"])
