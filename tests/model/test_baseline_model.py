"""The baseline model (validation plan V1, protocol §5.7): shrinkage, dispersion, cycle and ranges by hand."""

import math

import numpy as np
import pandas as pd
import pytest

from lotline.config import load_params
from lotline.model import baseline

PARAMS = load_params("baseline")


def _panel(rows, state="NC"):
    """rows: (geoid, county, year, units, eligible_parcels) -> a minimal panel for one state."""
    df = pd.DataFrame(rows, columns=["geoid", "county_geoid", "year", "units_1", "eligible_parcels"])
    return df.assign(state=state)


def test_fay_herriot_two_places_by_hand():
    """Docstring example: y = (10, 2), ḡ = (5, 5), v = (1, 9) -> A = 17 − 5 = 12, B = (1/13, 9/21)."""
    a, b = baseline.fay_herriot(np.array([10.0, 2.0]), np.array([1.0, 9.0]), np.array([5.0, 5.0]))
    assert a == pytest.approx(12.0)
    assert b == pytest.approx([1 / 13, 9 / 21])
    shrunk = (1 - b) * np.array([10.0, 2.0]) + b * 5.0
    assert shrunk == pytest.approx([9.615385, 3.285714], abs=1e-6)


def test_fay_herriot_all_noise_means_full_shrinkage():
    """Spread (1 + 1) / 2 = 1 is less than mean noise 4, so A = 0 and every place takes the group rate."""
    a, b = baseline.fay_herriot(np.array([6.0, 4.0]), np.array([4.0, 4.0]), np.array([5.0, 5.0]))
    assert a == 0.0
    assert b.tolist() == [1.0, 1.0]


def test_fay_herriot_handles_zero_noise_and_zero_spread():
    """v = 0 and A = 0 (a group of places that all built nothing): weight 0, nothing to divide."""
    a, b = baseline.fay_herriot(np.array([0.0, 0.0]), np.array([0.0, 0.0]), np.array([0.0, 0.0]))
    assert (a, b.tolist()) == (0.0, [0.0, 0.0])


def test_nb_inverse_dispersion_by_hand():
    """Place 1: 0, 4 -> mean 2, variance 8, excess 6. Place 2: 2, 2 -> mean 2, variance 0, excess −2.
    1/k = (6 − 2) / (2² + 2²) = 0.5. A place with mean 0 adds nothing."""
    assert baseline.nb_inverse_dispersion([np.array([0, 4]), np.array([2, 2]), np.array([0, 0])]) == 0.5


def test_nb_inverse_dispersion_floors_at_poisson():
    """Less spread than Poisson (excess (2 − 1) + (0 − 4) = −3 < 0) -> 0, i.e. Poisson."""
    assert baseline.nb_inverse_dispersion([np.array([0, 2]), np.array([4, 4])]) == 0.0


# Two places in one state, 2-year window ending 2020 (level_years = 2, group = state):
# A: 900 parcels, 9 and 9 units -> direct 1000·18/1800 = 10. B: 100 parcels, 0 and 0 -> direct 0.
# Group rate ḡ = 1000·18/2000 = 9. Counts: A has mean 9, variance 0 (excess −9), B has mean 0 -> 1/k = 0.
# λ_A = 9·900/1000 = 8.1, v_A = 10⁶/900² · 8.1 / 2 = 5; λ_B = 0.9, v_B = 10⁶/100² · 0.9 / 2 = 45.
# A = mean((10 − 9)², (0 − 9)²) − mean(5, 45) = 41 − 25 = 16. B_A = 5/21, B_B = 45/61.
# Levels: 10 − (5/21)·1 = 9.7619 and 0 + (45/61)·9 = 6.6393. Posterior variances (16/21)·5 and (16/61)·45.
TWO = _panel(
    [
        ("A", "C1", 2018, 500, 900),  # outside the window: ignored
        ("A", "C1", 2019, 9, 900),
        ("A", "C1", 2020, 9, 900),
        ("B", "C1", 2019, 0, 100),
        ("B", "C1", 2020, 0, 100),
    ]
)


def test_level_estimates_by_hand():
    out = baseline.level_estimates(TWO, "units_1", 2020, level_years=2, min_group_places=1, group="state")
    out = out.set_index("geoid")
    assert out["direct"].tolist() == pytest.approx([10.0, 0.0])
    assert out["group_rate"].tolist() == pytest.approx([9.0, 9.0])
    assert out["v"].tolist() == pytest.approx([5.0, 45.0])
    assert out["a"].iloc[0] == pytest.approx(16.0)
    assert out["b"].tolist() == pytest.approx([5 / 21, 45 / 61])
    assert out["level"].tolist() == pytest.approx([10 - 5 / 21, 9 * 45 / 61])
    assert out["level_var"].tolist() == pytest.approx([16 / 21 * 5, 16 / 61 * 45])
    assert out["parcels_origin"].tolist() == [900.0, 100.0]


def test_county_group_falls_back_to_state_when_small():
    """With min_group_places = 2, county C1 (2 places) is a group; C2 (1 place) falls back to the state."""
    p = pd.concat([TWO, _panel([("D", "C2", 2019, 1, 100), ("D", "C2", 2020, 1, 100)])])
    out = baseline.level_estimates(p, "units_1", 2020, level_years=2, min_group_places=2).set_index("geoid")
    assert out.loc["A", "group"] == "county_geoid:C1"
    assert out.loc["D", "group"] == "state:NC"
    assert out.loc["A", "group_rate"] == pytest.approx(9.0)  # 18 / 2000 parcels
    assert out.loc["D", "group_rate"] == pytest.approx(1000 * 20 / 2200)  # whole state


def test_place_needs_every_window_year():
    p = TWO[~((TWO["geoid"] == "B") & (TWO["year"] == 2019))]
    out = baseline.level_estimates(p, "units_1", 2020, level_years=2, min_group_places=1, group="state")
    assert out["geoid"].tolist() == ["A"]


def test_direct_variance_counts_a_one_off_year_as_noise():
    """B builds 0 then 2 on 100 parcels: annual rates 0 and 20, sample variance 200, /2 years = 100.
    That beats the negative-binomial variance, so with use_direct_variance B is treated as noisier."""
    p = TWO.copy()
    p.loc[(p["geoid"] == "B") & (p["year"] == 2020), "units_1"] = 2
    kw = dict(level_years=2, min_group_places=1, group="state")
    on = baseline.level_estimates(p, "units_1", 2020, use_direct_variance=True, **kw).set_index("geoid")
    off = baseline.level_estimates(p, "units_1", 2020, use_direct_variance=False, **kw).set_index("geoid")
    assert on.loc["B", "v_direct"] == pytest.approx(100.0)
    assert off.loc["B", "v"] < 100.0
    assert on.loc["B", "v"] == pytest.approx(100.0)


def test_cycle_shocks_by_hand():
    """State totals 100 -> 200 -> 100 (same places): log changes ln 2 and −ln 2.
    Centred by log(mean(e^x)) = log((2 + 0.5) / 2) = log 1.25: shocks ln 2 − ln 1.25 = ln 1.6 and
    −ln 2 − ln 1.25 = ln 0.4, whose exponentials average (1.6 + 0.4) / 2 = 1.
    Place Z appears only in 2020: it is not in the 2019-2020 comparison, so it can't fake a boom."""
    p = _panel(
        [
            ("A", "C1", 2018, 60, 1),
            ("B", "C1", 2018, 40, 1),
            ("A", "C1", 2019, 150, 1),
            ("B", "C1", 2019, 50, 1),
            ("A", "C1", 2020, 50, 1),
            ("B", "C1", 2020, 50, 1),
            ("Z", "C1", 2020, 900, 1),
        ]
    )
    shocks = baseline.cycle_shocks(p, "units_1", 2020, history_years=3)
    assert shocks == pytest.approx([math.log(1.6), math.log(0.4)])
    series = baseline.cycle_shock_series(p, "units_1", 2020, history_years=3)
    assert list(series.index) == [2019, 2020]
    assert len(baseline.cycle_shocks(p, "units_1", 2020, history_years=2)) == 1  # only 2019 -> 2020


def test_cycle_shocks_are_demeaned():
    """Totals 100 -> 200 -> 400: both changes ln 2; centred they are 0 (a steady trend is not a cycle)."""
    p = _panel([("A", "C1", 2018, 100, 1), ("A", "C1", 2019, 200, 1), ("A", "C1", 2020, 400, 1)])
    assert baseline.cycle_shocks(p, "units_1", 2020, history_years=3) == pytest.approx([0.0, 0.0])


def test_interval_from_draws_by_hand():
    """Draws 0..10: P10 = 1, P50 = 5, P90 = 9 (linear interpolation), mean 5."""
    lo, mid, hi, mean = baseline.interval_from_draws(np.arange(11.0)[None, :], 0.1, 0.9)
    assert (lo[0], mid[0], hi[0], mean[0]) == pytest.approx((1.0, 5.0, 9.0, 5.0))


def test_randomized_coverage_by_hand():
    """Docstring example: draws 0, 0, 0, 1; y = 0 -> 0.65 / 0.75; y = 1 -> 0.15 / 0.25; y = 5 (never drawn,
    F = 1 outside the band) -> 0."""
    draws = np.array([[0, 0, 0, 1]] * 3)
    cov = baseline.randomized_coverage(draws, np.array([0, 1, 5]), 0.1, 0.9)
    assert cov == pytest.approx([0.65 / 0.75, 0.15 / 0.25, 0.0])


def test_randomized_coverage_is_80_percent_for_a_calibrated_count_forecast():
    """Outcomes drawn from the forecast distribution itself are covered 80% of the time on average."""
    rng = np.random.default_rng(1)
    draws = rng.poisson(0.7, size=(1, 20000)).repeat(4000, axis=0)
    observed = rng.poisson(0.7, size=4000)
    assert baseline.randomized_coverage(draws, observed, 0.1, 0.9).mean() == pytest.approx(0.8, abs=0.02)


def test_simulation_without_level_noise_or_cycle_is_poisson():
    """Level 10 per 1,000 on 500 parcels, no level uncertainty, 1/k = 0, no cycle: counts are Poisson(5),
    so P10 = 2, P50 = 5, P90 = 8 and the mean is 5."""
    places = pd.DataFrame({"level": [10.0], "level_var": [0.0], "parcels_origin": [500.0], "inv_k": [0.0]})
    draws = baseline._simulate(places, None, 2, 40000, np.random.default_rng(0))
    lo, mid, hi, mean = baseline.interval_from_draws(draws, 0.1, 0.9)
    assert (lo[0, 0], mid[0, 0], hi[0, 0]) == (2.0, 5.0, 8.0)
    assert mean[0, 1] == pytest.approx(5.0, abs=0.05)


def test_simulation_negative_binomial_variance():
    """With 1/k = 0.5 and λ = 4: Var = 4 + 0.5·16 = 12 (Poisson would be 4)."""
    places = pd.DataFrame({"level": [8.0], "level_var": [0.0], "parcels_origin": [500.0], "inv_k": [0.5]})
    draws = baseline._simulate(places, None, 1, 200000, np.random.default_rng(0))
    assert draws.mean() == pytest.approx(4.0, abs=0.05)
    assert draws.var() == pytest.approx(12.0, rel=0.03)


def test_cycle_widens_the_range_with_the_horizon():
    places = pd.DataFrame({"level": [10.0], "level_var": [0.0], "parcels_origin": [5000.0], "inv_k": [0.0]})
    shocks = pd.Series(np.linspace(-0.3, 0.3, 7), index=range(2014, 2021))
    years, u = baseline.cycle_years(1, "NC", 2020, 8, 5, 20000)
    cycle = baseline.cycle_factor(shocks, years, u)
    lo, _, hi, _ = baseline.interval_from_draws(
        baseline._simulate(places, cycle, 5, 20000, np.random.default_rng(0)), 0.1, 0.9
    )
    width = hi[0] - lo[0]
    assert width[0] < width[2] < width[4]


def test_cycle_factor_by_hand():
    """Docstring example: shocks {2019: 0.1, 2020: -0.3}; years [[2019], [2020]] -> e^0.1, e^(0.1 − 0.3).
    2018 has no shock: with u = 0.6 it takes available[floor(0.6 × 2)] = 2020's shock."""
    shocks = pd.Series([0.1, -0.3], index=[2019, 2020])
    f = baseline.cycle_factor(shocks, np.array([[2019], [2020]]), np.zeros((2, 1)))
    assert f[:, 0] == pytest.approx([math.exp(0.1), math.exp(-0.2)])
    f = baseline.cycle_factor(shocks, np.array([[2018]]), np.array([[0.6]]))
    assert f[0, 0] == pytest.approx(math.exp(-0.3))
    assert (baseline.cycle_factor(pd.Series(dtype=float), np.array([[2019]]), np.zeros((1, 1))) == 1).all()


def test_cycle_years_depend_only_on_seed_state_and_origin():
    a, ua = baseline.cycle_years(7, "NC", 2018, 25, 5, 100)
    b, ub = baseline.cycle_years(7, "NC", 2018, 25, 5, 100)
    assert (a == b).all() and (ua == ub).all()
    assert a.min() >= 2018 - 25 + 2 and a.max() <= 2018
    assert not (a == baseline.cycle_years(7, "OH", 2018, 25, 5, 100)[0]).all()


def test_cycle_keeps_the_mean_flat_over_the_horizon():
    """No change in the level and a strongly cyclical history: the mean cycle factor stays 1 in every year.

    Shocks ±0.4: with the old centring (subtract mean(x) = 0) E[e^x] = cosh 0.4 = 1.081 a year, so the year-5
    mean would be 1.081^5 = 1.48. Centred by log(mean(e^x)) each step averages 1, so every year's mean is 1.
    """
    p = _panel([("A", "C1", y, 100 if y % 2 else 149, 1) for y in range(1995, 2021)])
    shocks = baseline.cycle_shock_series(p, "units_1", 2020, history_years=25)
    assert np.mean(np.exp(shocks)) == pytest.approx(1.0)
    years, u = baseline.cycle_years(3, "NC", 2020, 25, 5, 200_000)
    mean_by_year = baseline.cycle_factor(shocks, years, u).mean(axis=1)
    assert mean_by_year == pytest.approx(np.ones(5), abs=0.01)


def _big_place_panel():
    """One large place with a strong cycle and a small place Z in the same state that never builds.

    units_2 is 3 × units_1 (the same cycle), but Z has no units_2 record, so the two size classes are run
    with different sets of places, as happens with real data.
    """
    rows = []
    for y in range(1992, 2019):
        units = 2000 if y % 3 == 0 else 1200 if y % 3 == 1 else 700
        rows += [("A", "C1", y, units, 200_000), ("Z", "C1", y, 0, 300)]
    df = _panel(rows)
    return df.assign(units_2=(df["units_1"] * 3).where(df["geoid"] == "A"))


def _year5_draws(panel, value):
    table, draws = baseline.forecast_draws(panel, value, 2018, group="state", params=PARAMS)
    row = table.index[(table["geoid"] == "A") & (table["horizon"] == 5)][0]
    return draws[row].astype(float)


def test_cycle_coupling_does_not_depend_on_which_places_are_present():
    """MS-06: draw j is the same run of cycle years for every size class, whichever places are present.

    Place A is large and its draws are mostly cycle. units_1 is run with places A and Z, units_2 with A only.
    Before D-011 the cycle was drawn after the per-place gamma draws, whose number depends on the places, so
    A's year-5 draws for the two classes were unrelated (correlation −0.02 when checked). Now the cycle years
    are shared (0.77; the rest is A's own level and count noise). Same places in both classes: ~1.
    """
    panel = _big_place_panel()
    ones = _year5_draws(panel, "units_1")
    twos = _year5_draws(panel, "units_2")
    assert np.corrcoef(ones, twos)[0, 1] > 0.5
    only_a = _year5_draws(panel[panel["geoid"] == "A"], "units_1")
    assert np.corrcoef(only_a, twos)[0, 1] > 0.99


def _stationary_panel(seed=0, places=30, years=range(1992, 2026)):
    """A synthetic state where nothing changes: each place builds Poisson(rate · parcels / 1000) a year."""
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(places):
        parcels = int(rng.integers(50, 5000))
        rate = float(rng.gamma(2.0, 5.0))
        for y in years:
            rows.append((f"P{i:02d}", f"C{i % 3}", y, int(rng.poisson(rate * parcels / 1000)), parcels))
    return _panel(rows)


def test_baseline_forecast_shape_and_order():
    fc = baseline.baseline_forecast(_stationary_panel(), "units_1", 2018, params=PARAMS)
    assert len(fc) == 30 * 5
    assert fc["year"].min() == 2019 and fc["year"].max() == 2023
    assert (fc["p10"] <= fc["p50"]).all() and (fc["p50"] <= fc["p90"]).all()


def test_baseline_forecast_never_sees_years_after_the_origin():
    p = _stationary_panel()
    late = p.copy()
    late.loc[late["year"] > 2018, "units_1"] *= 50
    a = baseline.baseline_forecast(p, "units_1", 2018, params=PARAMS)
    b = baseline.baseline_forecast(late, "units_1", 2018, params=PARAMS)
    pd.testing.assert_frame_equal(a, b)


def test_baseline_forecast_reproducible_from_config():
    p = _stationary_panel()
    a = baseline.baseline_forecast(p, "units_1", 2018, params=PARAMS)
    b = baseline.baseline_forecast(p, "units_1", 2018, params=PARAMS)
    pd.testing.assert_frame_equal(a, b)


def test_outcome_column():
    assert baseline.outcome_column("5p", reported_only=True) == "units_5p_rep"
    assert baseline.outcome_column("1", reported_only=False) == "units_1"
    with pytest.raises(ValueError):
        baseline.outcome_column("6", reported_only=True)
