"""D-090's within-state forecast test: each step against a hand-worked example (synthetic data only)."""

import math

import numpy as np
import pytest

from lotline.model import adu_forecast as af
from lotline.model import calibrate_adu as cal
from lotline.model import joint_refit as jr

T_NONE, T_OWNER, T_HB = 0, 1, 4
CV = cal._cvals(1.0, 1.0)


def _pl(y, base=None, years=None, types=None, w=(1.0,), lots=None, geoid="a", state="MN"):
    n = len(y)
    years = np.arange(2016, 2016 + n) if years is None else np.asarray(years)
    base = np.ones(n) if base is None else np.asarray(base, dtype=float)
    types = np.full((len(w), n, 1), T_HB) if types is None else np.asarray(types)
    lots = np.full(n, 1000.0) if lots is None else np.asarray(lots, dtype=float)
    return cal.PlaceData(
        state, geoid, geoid, years, np.asarray(y, dtype=float), base, types, np.ones((n, 1)),
        np.asarray(w, dtype=float), None, {"parcels": lots},
    )  # fmt: skip


# --- the split ------------------------------------------------------------------------------------------


def test_split_leaves_out_the_lead_year():
    f, w = af.split(_pl(np.arange(10)))
    assert list(f.years) == [2016, 2017, 2018, 2019]
    assert list(w.years) == [2021, 2022, 2023, 2024, 2025]
    assert list(w.y) == [5, 6, 7, 8, 9]


def test_place_classes():
    assert af.place_class(_pl([1] * 10)) == "history"
    assert af.place_class(_pl([1] * 4, years=[2018, 2019, 2020, 2021])) == "history"
    assert af.place_class(_pl([1] * 3, years=[2019, 2020, 2021])) == "thin"
    assert af.place_class(_pl([1] * 3, years=[2021, 2022, 2023])) == "new"
    assert af.place_class(_pl([1] * 5, years=[2016, 2017, 2018, 2019, 2020])) == "none"


def test_rule_change_years():
    types = np.array([[[T_NONE], [T_NONE], [T_NONE], [T_NONE], [T_OWNER], [T_OWNER], [T_HB]]])
    pl = _pl([0] * 7, years=range(2016, 2023), types=types)
    # counted from the lead year: 2020 owner, 2021 owner, 2022 by right -> [2022]
    assert af.rule_change_years(pl) == [2022]


# --- F0 -------------------------------------------------------------------------------------------------


def test_f0_posterior_hand_worked():
    assert af.f0_posterior(_pl([2, 3], lots=[100, 100])) == (5.5, 200.0)


def test_f0_log_score_hand_worked():
    # a = 0.5 + 0.5 = 1, b = 1; one window year y 0 on 1 lot: ∫ e^-λ e^-λ dλ = 1/2
    fit, win = _pl([0.5], lots=[1.0]), _pl([0], years=[2021], lots=[1.0])
    assert af.f0_log_score(fit, win) == pytest.approx(math.log(0.5))
    # y 1: a b^a Γ(a+1)/Γ(a) / (b+1)^(a+1) = 1 · 1 / 4
    assert af.f0_log_score(fit, _pl([1], years=[2021], lots=[1.0])) == pytest.approx(math.log(0.25))


def test_f0_draws_match_the_gamma_mean():
    fit = _pl([3, 5], lots=[1000, 1000])  # rate mean 8.5 / 2000
    win = _pl([0, 0, 0], years=[2021, 2022, 2023], lots=[1000, 2000, 1000])
    d = af.f0_draws(fit, win, 200_000, 1)
    assert d.mean(axis=0) == pytest.approx([4.25, 8.5, 4.25], rel=0.02)


# --- F1: the own-history update -------------------------------------------------------------------------


def test_own_log_score_hand_worked():
    # α 1 (r 1), scale 1, fit y 2 on k 1 -> u ~ Gamma(3, rate 2); P(window 0 on k 1) = E e^-u = (2/3)^3
    g = jr.GlobalsA(np.array([1.0]), 1.0, CV)
    fit, win = _pl([2]), _pl([0], years=[2021])
    assert af.own_log_score(fit, win, g) == pytest.approx(math.log(8 / 27))


def test_predict_own_posterior_mean():
    # u ~ Gamma(3, rate 2), mean 1.5; window k 2 -> mean count 3
    g = jr.GlobalsA(np.ones(200_000), 1.0, CV)
    d = af.predict_own(_pl([2]), _pl([0], years=[2021], base=[2.0]), g, 5)
    assert d.mean() == pytest.approx(3.0, rel=0.02)


def test_predict_own_updates_the_combination():
    # two equally weighted combinations: rules none (k 0) and by right (k 1). A fit count of 1 rules out
    # "none", so every draw takes "by right"; window base 100 would give 0 under "none".
    types = np.array([[[T_NONE]], [[T_HB]]])
    fit = _pl([1], types=types, w=(0.5, 0.5))
    win = _pl([0], years=[2021], base=[100.0], types=types, w=(0.5, 0.5))
    g = jr.GlobalsA(np.ones(20_000), 1e-9, CV)  # α ~ 0: u = 1
    d = af.predict_own(fit, win, g, 2)
    assert (d > 0).mean() > 0.99
    assert d.mean() == pytest.approx(100, rel=0.03)


def test_own_log_score_matches_predict_own():
    # the score's predictive and the draws agree on P(window = 0)
    g = jr.GlobalsA(np.array([0.5, 2.0]).repeat(50_000), 0.7, CV)
    fit, win = _pl([1, 3], base=[1.0, 2.0]), _pl([0], years=[2021], base=[1.5])
    d = af.predict_own(fit, win, g, 9)
    assert math.exp(af.own_log_score(fit, win, g)) == pytest.approx((d[:, 0] == 0).mean(), abs=0.01)


# --- F1's fit -------------------------------------------------------------------------------------------


def _two_states(theta=(0.002, 0.02), alpha=0.3, n=40, years=4, seed=11):
    rng = np.random.default_rng(seed)
    out = []
    for s, th in zip(("MN", "OR"), theta, strict=True):
        for i in range(n):
            base = np.full(years, float(rng.uniform(500, 3000)))
            u = rng.gamma(1 / alpha, alpha)
            y = rng.poisson(th * u * base)
            out.append(_pl(y, base=base, geoid=f"{s}{i}", state=s))
    return out


def test_fit_within_recovers_state_rates():
    f = af.fit_within(_two_states(), cell=(1.0, 1.0))
    assert f.theta["MN"] == pytest.approx(0.002, rel=0.25)
    assert f.theta["OR"] == pytest.approx(0.02, rel=0.25)
    for s in ("MN", "OR"):
        assert f.low[s] < f.theta[s] < f.high[s]
    assert f.low["OR"] > f.high["MN"]


def test_state_globals_spread():
    f = af.StateFit(
        {"MN": 0.01}, {"MN": 0.01}, {"MN": 0.01}, 0.5, 1.0, 1.0, (1, 1), (1, 1), False, False, 0, 1, 1
    )
    g = af.state_globals(f, "MN", 10, 1)
    assert np.allclose(g.scale, 0.01)  # a zero-width interval draws θ exactly
    f2 = af.StateFit({"MN": 0.01}, {"MN": 0.01 / math.e}, {"MN": 0.01 * math.e}, 0.5, 1.0, 1.0,
                     (1, 1), (1, 1), False, False, 0, 1, 1)  # fmt: skip
    g2 = af.state_globals(f2, "MN", 200_000, 1)
    assert np.log(g2.scale).std() == pytest.approx(1 / cal.Z_95, rel=0.01)


def test_read_shares_judgment_when_flat():
    flat = {(a, b): 0.0 for a in (0.1, 0.5, 1.0) for b in (0.1, 0.5, 1.0)}
    m, _, est = af.read_shares(flat)
    assert m == (0.5, 0.3) and est == (False, False)
    peaked = {(a, b): -10 * (a - 0.5) ** 2 * 100 - 10 * (b - 0.1) ** 2 * 100 for a, b in flat}
    m, _, est = af.read_shares(peaked)
    assert m == (0.5, 0.1) and est == (True, True)


# --- trend and the rule ---------------------------------------------------------------------------------


def test_with_trend_hand_worked():
    pl = af.with_trend(_pl([0, 0, 0], years=[2018, 2019, 2020]), math.log(2))
    assert pl.base == pytest.approx([0.5, 1.0, 2.0])


def test_fit_trend_recovers_growth():
    rng = np.random.default_rng(4)
    pls = []
    for i in range(60):
        base = np.full(4, 2000.0) * np.exp(0.3 * (np.arange(2016, 2020) - 2019))
        pls.append(_pl(rng.poisson(0.01 * base), base=np.full(4, 2000.0), geoid=str(i)))
    f = af.fit_within(pls, cell=(1.0, 1.0), intervals=False)
    gamma, theta = af.fit_trend(pls, f, "MN")
    assert gamma == pytest.approx(0.3, abs=0.05)
    assert theta == pytest.approx(0.01, rel=0.1)  # the rate at the origin year


def test_decide_hand_worked():
    v = af.decide({"MN": 1, "NC": 1, "TX": 1, "OR": 0}, {"MN": 1, "NC": 1, "TX": 1, "OR": 1}, 10, 4, 5, 3)
    assert (v.own_history_enough, v.useful_states_f1, v.mechanism_beats_persistence, v.f2_replaces_f1) == (
        True, 3, True, False,
    )  # fmt: skip
    v = af.decide({"MN": 1, "NC": 0, "TX": 1, "OR": 0}, {"MN": 1, "NC": 0, "TX": 1, "OR": 0}, 7, 4, 7, 3)
    assert (v.own_history_enough, v.mechanism_beats_persistence, v.f2_replaces_f1) == (False, False, True)
