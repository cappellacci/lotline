"""Spec C (analysis plan D-006): the two demand signals, the Poisson fit and the multiplier, by hand."""

import numpy as np
import pandas as pd
import pytest

from lotline.config import load_params
from lotline.model import backtest, baseline, demand

PARAMS = load_params("baseline")


def _households(values):
    """{(county 5-digit, end year): estimate} -> the households series."""
    idx = pd.MultiIndex.from_tuples([(f"county:{c}", y) for c, y in values], names=["geo", "end_year"])
    return pd.Series(list(values.values()), index=idx, dtype=float)


def _hpi(values):
    idx = pd.MultiIndex.from_tuples(list(values), names=["geo", "year"])
    return pd.Series(list(values.values()), index=idx, dtype=float)


def test_household_growth_by_hand():
    """10,000 households (estimate ending 2020) vs 8,000 (ending 2015): 1.25^(1/5) − 1 = 0.04564."""
    hh = _households({("27001", 2020): 10_000, ("27001", 2015): 8_000, ("27003", 2020): 500})
    rows = pd.DataFrame({"county_geoid": ["27001", "27003", "27001"], "year": [2020, 2020, 2019]})
    g = demand.household_growth(rows, hh, 5)
    assert g[0] == pytest.approx(1.25**0.2 - 1) and g[0] == pytest.approx(0.045640, abs=1e-6)
    assert np.isnan(g[1]) and np.isnan(g[2])  # no estimate 5 years earlier / none ending 2019


def test_price_change_walks_the_chain_without_mixing_geographies():
    """County index 200 (2020) and 160 (2017): 1.25^(1/3) − 1 = 0.07722. A county with no 2017 value
    falls to its metro area (150 -> 120, also 1.25), never county 2020 over metro 2017."""
    hpi = _hpi(
        {
            ("county:27001", 2020): 200.0,
            ("county:27001", 2017): 160.0,
            ("county:27003", 2020): 999.0,  # no 2017: skipped
            ("cbsa:11111", 2020): 150.0,
            ("cbsa:11111", 2017): 120.0,
            ("state:27", 2020): 110.0,
            ("state:27", 2017): 100.0,
        }
    )
    rows = pd.DataFrame(
        {
            "geoid": ["2700001", "2700002", "2700003", "2700004"],
            "county_geoid": ["27001", "27003", "27001", "27005"],
            "cbsa_code": ["11111", "11111", "11111", None],
            "year": [2020, 2020, 2020, 2020],
            "hpi_geo": ["county:27001", "county:27003", "cbsa:11111", None],
        }
    )
    q = demand.price_change(rows, hpi, 3)
    assert q[0] == pytest.approx(1.25 ** (1 / 3) - 1) and q[0] == pytest.approx(0.077217, abs=1e-6)
    assert q[1] == pytest.approx(1.25 ** (1 / 3) - 1)  # county lacks 2017 -> metro
    assert q[2] == pytest.approx(1.25 ** (1 / 3) - 1)  # hpi_geo is the metro: county not used
    assert q[3] == pytest.approx(1.1 ** (1 / 3) - 1)  # no county, no metro: state


def test_irls_two_groups_by_hand():
    """With one 0/1 covariate the Poisson MLE has a closed form: exp(β_0) = Σy/ΣE in group 0, and
    exp(β_0 + β_1) = Σy/ΣE in group 1. Group 0: y 2, 4 on E 2, 2 -> 6/4 = 1.5. Group 1: y 9, 3 on E 3, 1 ->
    12/4 = 3. So β_0 = log 1.5 = 0.405465, β_1 = log 2 = 0.693147."""
    y = np.array([2, 4, 9, 3])
    x = np.column_stack([np.ones(4), [0, 0, 1, 1]])
    beta, ok = demand.poisson_irls(y, x, np.log([2.0, 2.0, 3.0, 1.0]), tol=1e-12, max_iter=100)
    assert ok
    assert beta == pytest.approx([np.log(1.5), np.log(2.0)], abs=1e-9)


def test_irls_recovers_known_betas():
    rng = np.random.default_rng(7)
    n = 40_000
    g, q = rng.normal(0.01, 0.015, n), rng.normal(0.03, 0.04, n)
    e = rng.uniform(0.5, 5.0, n)
    true = np.array([0.1, 12.0, 4.0])
    x = np.column_stack([np.ones(n), g, q])
    y = rng.poisson(e * np.exp(x @ true))
    beta, ok = demand.poisson_irls(y, x, np.log(e), tol=1e-10, max_iter=100)
    assert ok
    assert beta == pytest.approx(true, abs=0.6)  # standard errors here: about 0.2 (β_h) and 0.08 (β_p)
    assert abs(beta[1] - 12.0) < 3 * 0.25 and abs(beta[2] - 4.0) < 3 * 0.1


def test_irls_with_no_permits_fails_safely():
    beta, ok = demand.poisson_irls(np.zeros(3), np.ones((3, 1)), np.zeros(3), tol=1e-10, max_iter=10)
    assert not ok and beta.tolist() == [0.0]
    f = demand.fit(pd.DataFrame({"y": [0.0], "e": [1.0], "g": [0.1], "q": [0.1]}), PARAMS)
    assert (f.beta_h, f.beta_p, f.converged) == (0.0, 0.0, False)


def test_multiplier_scales_the_level_and_its_variance():
    """Multiplier 2 on one place: its level doubles, its level variance quadruples, others unchanged."""
    panel = _panel()
    origin = 2020
    b, _ = baseline.forecast_draws(panel, "units_1", origin, params=PARAMS)
    target = sorted(panel["geoid"].unique())[0]
    c, _ = baseline.forecast_draws(
        panel, "units_1", origin, params=PARAMS, multiplier=pd.Series({target: 2.0})
    )
    one_b, one_c = b[b["geoid"] == target].iloc[0], c[c["geoid"] == target].iloc[0]
    assert one_c["level"] == pytest.approx(2 * one_b["level"])
    assert one_c["demand"] == 2.0 and (c.loc[c["geoid"] != target, "demand"] == 1.0).all()
    other = b["geoid"] != target
    assert np.allclose(b.loc[other, "level"], c.loc[other, "level"])
    assert c.loc[c["geoid"] == target, "mean"].mean() > 1.6 * b.loc[b["geoid"] == target, "mean"].mean()


# A synthetic state: 3 counties growing at 0%, 2% and 4% a year in households, prices rising 1%, 3%, 5%.
# Places permit Poisson(rate × parcels / 1000 × exp(BETA_H·g + BETA_P·q)) with g, q as of each year.
BETA_H, BETA_P = 15.0, 5.0
# Price growth must not be a linear function of household growth, or (1, g, q) is singular and no fit can
# separate β_h from β_p (the earlier 0.01/0.03/0.05 was g + 0.01 exactly: it failed on CI, PR #95).
COUNTIES = {"48001": (0.0, 0.03), "48003": (0.02, 0.01), "48005": (0.04, 0.05)}


def _inputs(years=range(2000, 2026)):
    hh, hpi = {}, {}
    for c, (gr, pr) in COUNTIES.items():
        for y in years:
            hh[(c, y)] = 10_000 * (1 + gr) ** (y - 2000)
            hpi[(f"county:{c}", y)] = 100 * (1 + pr) ** (y - 2000)
    return demand.DemandInputs(households=_households(hh), hpi=_hpi(hpi))


def _panel(seed=3, per_county=12, years=range(2000, 2026)):
    rng = np.random.default_rng(seed)
    rows = []
    for c, (gr, pr) in COUNTIES.items():
        for i in range(per_county):
            geoid = f"48{c[2:]}{i:02d}"
            parcels = 500 + 100 * i
            for y in years:
                lam = 20.0 * parcels / 1000 * np.exp(BETA_H * gr + BETA_P * pr)
                rows.append(("TX", geoid, c, None, y, int(rng.poisson(lam)), parcels, f"county:{c}"))
    cols = ["state", "geoid", "county_geoid", "cbsa_code", "year", "units_1", "eligible_parcels", "hpi_geo"]
    df = pd.DataFrame(rows, columns=cols)
    return df.assign(units_1_rep=df["units_1"])  # the backtest scores reported units


def test_fit_sample_uses_only_fit_years_with_signals():
    s = demand.fit_sample(_panel(), "units_1", 2016, _inputs(), PARAMS)
    # level needs 2000..t−1 (t >= 2005); g needs households 5 years back (data from 2000) -> t in 2005..2016
    assert s["year"].min() == 2005 and s["year"].max() == 2016
    assert (s["e"] > 0).all() and s[["g", "q"]].notna().all().all()


def test_multipliers_by_construction():
    """Signals are constant over time per county, so spec B's level already carries each county's demand
    and the betas only separate counties through the shrinkage. Check the multiplier formula and the
    fallback, not the size of β."""
    panel = _panel()
    table, fits = demand.multipliers(panel, "units_1", 2018, _inputs(), params=PARAMS)
    f = fits["TX"]
    assert f.converged and f.n > 0
    # centred at the fit sample's own means (D-026), computed here independently of `fit`
    sample = demand.fit_sample(panel[panel["year"] <= 2018], "units_1", 2018, _inputs(), PARAMS)
    g_bar, q_bar = sample["g"].mean(), sample["q"].mean()
    assert (f.g_mean, f.q_mean) == pytest.approx((g_bar, q_bar))
    expect = np.exp(f.beta_h * (table["g"] - g_bar) + f.beta_p * (table["q"] - q_bar))
    assert np.allclose(table["multiplier"], expect)
    assert not table["fallback"].any()
    # a county with no household estimates: those places fall back to multiplier 1
    inputs = _inputs()
    hh = inputs.households[~inputs.households.index.get_level_values(0).isin(["county:48005"])]
    table2, _ = demand.multipliers(panel, "units_1", 2018, demand.DemandInputs(hh, inputs.hpi), params=PARAMS)
    gone = table2["geoid"].str.startswith("4805")
    assert table2.loc[gone, "fallback"].all() and (table2.loc[gone, "multiplier"] == 1.0).all()


def test_multiplier_by_hand():
    """Docstring example (D-026): β_h = 10 and β_p = 2 around ḡ = 0.02, q̄ = 0.05. β_0 is never applied."""
    f = demand.DemandFit(0.3, 10.0, 2.0, 100, True, g_mean=0.02, q_mean=0.05)
    assert f.multiplier(0.03, 0.05) == pytest.approx(np.exp(0.1))
    assert f.multiplier(0.02, 0.05) == pytest.approx(1.0)
    assert f.multiplier(0.02, 0.10) == pytest.approx(np.exp(0.1))


def test_average_demand_keeps_spec_b():
    """D-026: on the fit sample, the log multiplier averages exactly 0, whatever β is: a place at average
    demand keeps spec B's level. Before, the signals were uncentred while β_0 was dropped, so the average
    log multiplier was β_h ḡ + β_p q̄, not 0 (here 0.011; with real data's |β| up to 66, D-007, far more)."""
    panel = _panel()
    sample = demand.fit_sample(panel, "units_1", 2018, _inputs(), PARAMS)
    f = demand.fit(sample, PARAMS)
    assert f.converged
    assert np.log(f.multiplier(sample["g"], sample["q"])).mean() == pytest.approx(0.0, abs=1e-12)
    assert abs(f.beta_h * sample["g"].mean() + f.beta_p * sample["q"].mean()) > 0.005  # the bias it removes


def test_multipliers_never_see_after_the_origin():
    panel, inputs = _panel(), _inputs()
    a, fa = demand.multipliers(panel, "units_1", 2018, inputs, params=PARAMS)
    late = panel.copy()
    late.loc[late["year"] > 2018, "units_1"] *= 50
    hh = inputs.households.copy()
    hh[hh.index.get_level_values(1) > 2018] *= 3
    b, fb = demand.multipliers(late, "units_1", 2018, demand.DemandInputs(hh, inputs.hpi), params=PARAMS)
    assert fa == fb
    pd.testing.assert_frame_equal(a, b)


def test_fit_recovers_a_time_varying_demand_effect():
    """Households in one county jump from flat to 6% a year growth in 2010: the fit, which compares each
    year's count to the trailing 5-year level, sees the counts rise with g and gets β_h > 0."""
    rng = np.random.default_rng(11)
    hh, hpi, rows = {}, {}, []
    for k, c in enumerate(["48001", "48003", "48005", "48007"]):
        level = 10_000.0
        for y in range(2000, 2021):
            growth = 0.06 if (k % 2 == 0 and y >= 2010) else 0.0
            level *= 1 + growth
            hh[(c, y)] = level
            hpi[(f"county:{c}", y)] = 100.0
    inputs = demand.DemandInputs(_households(hh), _hpi(hpi))
    for c in ["48001", "48003", "48005", "48007"]:
        for i in range(15):
            geoid = f"48{c[2:]}{i:02d}"
            for y in range(2000, 2021):
                row = pd.DataFrame({"county_geoid": [c], "year": [y]})
                g = demand.household_growth(row, inputs.households, 5)[0]
                lam = 30.0 * np.exp(BETA_H * (0.0 if np.isnan(g) else g))
                rows.append(("TX", geoid, c, None, y, int(rng.poisson(lam)), 1000, f"county:{c}"))
    cols = ["state", "geoid", "county_geoid", "cbsa_code", "year", "units_1", "eligible_parcels", "hpi_geo"]
    panel = pd.DataFrame(rows, columns=cols)
    sample = demand.fit_sample(panel, "units_1", 2020, inputs, PARAMS)
    # q is 0 everywhere, so (1, g, q) is singular: the fit reports failure rather than inventing β_p
    assert not demand.fit(sample, PARAMS).converged
    x = np.column_stack([np.ones(len(sample)), sample["g"]])
    beta, ok = demand.poisson_irls(sample["y"], x, np.log(sample["e"]), tol=1e-10, max_iter=100)
    assert ok and beta[1] > 0


def test_window_spec_c_runs_and_reports_the_demand_term():
    panel = _panel()
    with pytest.raises(ValueError, match="demand_inputs"):
        backtest.window(panel, "1", 2018, params=PARAMS, excluded=set(), spec="C")
    b = backtest.window(panel, "1", 2018, params=PARAMS, excluded=set())
    assert (b["multiplier"] == 1.0).all() and b["beta_h"].isna().all() and (b["spec"] == "B").all()
    c = backtest.window(panel, "1", 2018, params=PARAMS, excluded=set(), spec="C", demand_inputs=_inputs())
    assert (c["spec"] == "C").all() and c["beta_h"].notna().all()
    bench = c["method"] != "model"
    bm = b[b["method"] != "model"].reset_index(drop=True)
    assert np.allclose(c.loc[bench, "forecast"].to_numpy(), bm["forecast"].to_numpy())  # benchmarks unchanged
    res = backtest.run(
        {"TX": panel}, ("1",), params=PARAMS, excluded=set(), spec="C", demand_inputs={"TX": _inputs()}
    )
    assert set(res["fit_end"]) == {2016, 2018, 2020}
