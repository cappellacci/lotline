"""D-061: the five-year window starts `forecast_lead_years` after the data origin.

Origin 2025 (the last full BPS year) with lead 1 gives 2027-2031. The lead year is simulated as baseline only
and is not reported; the backtest keeps its own pre-registered lead (`v1_lead_years` = 0).
"""

import numpy as np
import pandas as pd
import pytest

from lotline.config import load_params
from lotline.model import baseline
from lotline.model.scenarios import adu

PARAMS = load_params("baseline")


def _with(params, **values):
    """A copy of the baseline params with some values replaced (no range check: a test-only override)."""
    out = dict(params)
    for name, v in values.items():
        out[name] = params[name].model_copy(
            update={"value": v, "low": min(v, params[name].low), "high": max(v, params[name].high)}
        )
    return out


def test_config_window_is_2027_to_2031_from_a_2025_origin():
    assert int(PARAMS["forecast_lead_years"].value) == 1
    assert int(PARAMS["v1_lead_years"].value) == 0  # the registered V1 lead is unchanged
    assert baseline.window(2025, PARAMS) == (1, 5, 2027)
    assert baseline.window_label(2025, PARAMS) == "2027-2031"


def test_window_with_no_lead_is_the_old_window():
    p = _with(PARAMS, forecast_lead_years=0)
    assert baseline.window(2025, p) == (0, 5, 2026)
    assert baseline.window_label(2025, p) == "2026-2030"


def test_benchmarks_skip_the_lead_years_by_hand():
    """Same hand example as test_baseline: years 2015-2019, values 10, 12, 14, 13, 16, b = 1.3, origin 2019.
    With lead 1 the window is 2021-2025: ŷ = 13 + 1.3 (t − 2017) -> 18.2, 19.5, 20.8, 22.1, 23.4.
    The last-3 mean, (14 + 13 + 16) / 3 = 14.33, is the same number, now on 2021-2025."""
    s = pd.Series({2015: 10, 2016: 12, 2017: 14, 2018: 13, 2019: 16})
    trend = baseline.linear_trend(s, origin=2019, horizon=5, lead=1)
    assert list(trend.index) == [2021, 2022, 2023, 2024, 2025]
    assert trend.tolist() == pytest.approx([18.2, 19.5, 20.8, 22.1, 23.4])
    mean = baseline.last_k_mean(s, origin=2019, k=3, horizon=5, lead=1)
    assert list(mean.index) == [2021, 2022, 2023, 2024, 2025]
    assert mean.tolist() == pytest.approx([43 / 3] * 5)


def _panel(n_places=12, years=range(2000, 2021), seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(n_places):
        parcels = 500 + 100 * i
        for y in years:
            rows.append(
                {
                    "geoid": f"27{i:05d}",
                    "state": "MN",
                    "county_geoid": "27001" if i < 6 else "27003",
                    "year": y,
                    "eligible_parcels": parcels,
                    "units_1": int(rng.poisson(parcels * 0.01 * (1 + 0.2 * np.sin(y)))),
                }
            )
    return pd.DataFrame(rows)


def test_lead_year_is_simulated_then_dropped():
    """Lead 1, horizon 5 simulates six years and reports the last five: its draws equal years 2-6 of a
    lead-0, six-year run from the same origin and seed (same random streams), so the cycle really walks
    through the lead year and the band is that of a forecast two to six years out."""
    panel = _panel()
    lead1 = _with(PARAMS, forecast_lead_years=1, use_state_momentum=0)
    six = _with(PARAMS, forecast_lead_years=0, forecast_horizon_years=6, use_state_momentum=0)
    t1, d1 = baseline.forecast_draws(panel, "units_1", 2020, group="county_geoid", params=lead1)
    t6, d6 = baseline.forecast_draws(panel, "units_1", 2020, group="county_geoid", params=six)
    assert sorted(t1["year"].unique()) == [2022, 2023, 2024, 2025, 2026]
    assert sorted(t1["horizon"].unique()) == [1, 2, 3, 4, 5]
    keep = (t6["year"] >= 2022).to_numpy()
    assert (
        t1[["geoid", "year"]]
        .reset_index(drop=True)
        .equals(t6.loc[keep, ["geoid", "year"]].reset_index(drop=True))
    )
    np.testing.assert_array_equal(d1, d6[keep])


def test_adu_pool_shrinks_under_current_rules_in_the_lead_year_by_hand():
    """1,000 parcels, mature hazard 0.1, current rule share c = 0.5, no floor, ramp 1 (D-048).
    Lead year: current rules only, hazard 0.5 × 0.1 = 0.05, so 50 ADUs and 950 parcels left; nothing added.
    Window year 1: current 950 × 0.05 = 47.5; Handbook 950 × (0.05 + 0.5 × 0.1) = 95; added 47.5.
    Without the lead it would be 50, 100 and 50."""
    p = adu.central_params()
    args = ([1000.0], [0.1], [np.nan], [0.5], [np.nan], p, 5)
    with_lead = adu.pool_paths(*args, enabled=True, lead=1)
    no_lead = adu.pool_paths(*args, enabled=True, lead=0)
    assert with_lead.current[0, 0] == pytest.approx(47.5)
    assert with_lead.handbook[0, 0] == pytest.approx(95.0)
    assert with_lead.added[0, 0] == pytest.approx(47.5)
    assert (no_lead.current[0, 0], no_lead.handbook[0, 0]) == pytest.approx((50.0, 100.0))
    assert with_lead.handbook.shape == (1, 5)
