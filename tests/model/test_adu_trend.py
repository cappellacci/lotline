"""D-085 Form T and test D: each step against a hand-worked example or the base form (synthetic data only)."""

import math

import numpy as np
import pytest

from lotline.model import adu_owner as ao
from lotline.model import adu_screen as scr
from lotline.model import adu_trend as at
from lotline.model import calibrate_adu as cal
from lotline.model import joint_refit as jr

T_OWNER, T_OTHER, T_HB = 1, 2, 4
GRID = (0.2, 0.4, 0.7, 1.0)


def _pl(geoid, y, base, typ=T_HB, start=2016, parcels=1000.0):
    n = len(y)
    return cal.PlaceData(
        "MN",
        geoid,
        geoid,
        np.arange(start, start + n),
        np.asarray(y, dtype=float),
        np.asarray(base, dtype=float),
        np.full((1, n, 1), typ),
        np.ones((n, 1)),
        np.array([1.0]),
        None,
        {"parcels": np.full(n, parcels)},
    )


def test_trend_factor_hand_worked():
    assert at.trend_factor([2019, 2020, 2022], math.log(2), 2020) == pytest.approx([0.5, 1, 4])
    assert at.trend_factor([2019, 2020, 2022], math.log(2), 2020, cap=2020) == pytest.approx([0.5, 1, 1])


def test_trend_prep_matches_prepare_on_trended_places():
    places = [_pl("a", [1, 0, 3], [2.0, 1.0, 4.0]), _pl("b", [0, 2], [1.0, 3.0], T_OWNER, start=2019)]
    cv = cal._cvals(0.7, 0.4)
    tp = at.trend_prep(places, cv, 2020)
    for g in (0.0, 0.3, -0.5):
        want = scr.prepare([at.trended(p, g, 2020) for p in places], cv)
        got = tp.at(g)
        assert (
            got.K == pytest.approx(want.K)
            and got.H == pytest.approx(want.H)
            and got.Y == pytest.approx(want.Y)
        )


def test_year_scale_hand_worked():
    pl = _pl("a", [0, 0, 0], [1, 1, 1], start=2019)
    g = jr.GlobalsA(np.array([2.0]), 1.0, cal._cvals(1, 1), gamma=np.array([math.log(2)]))
    assert g.year_scale(pl)[0] == pytest.approx([1.0, 2.0, 4.0])
    g2 = jr.GlobalsA(np.array([2.0]), 1.0, cal._cvals(1, 1), gamma=np.array([math.log(2)]), trend_cap=2020)
    assert g2.year_scale(pl)[0] == pytest.approx([1.0, 2.0, 2.0])
    g0 = jr.GlobalsA(np.array([2.0]), 1.0, cal._cvals(1, 1))
    assert g0.year_scale(pl)[0] == pytest.approx([2.0, 2.0, 2.0])


def test_form_t_loglik_equals_base_on_trended_places():
    pl = _pl("a", [3, 0, 5], [2.0, 1.0, 4.0], start=2019)
    cv = cal._cvals(1.0, 1.0)
    gam, scale = np.array([-0.4, 0.0, 0.6]), np.array([0.4, 1.1, 2.0])
    g_t = jr.GlobalsA(scale, 1.3, cv, gamma=gam)
    for j in range(3):
        want = jr.place_loglik(at.trended(pl, float(gam[j]), 2020), jr.GlobalsA(scale[j : j + 1], 1.3, cv))[0]
        assert jr.place_loglik(pl, g_t)[j] == pytest.approx(want)


def _synthetic(gamma, beta=0.0, n=40, years=8, alpha=0.4, seed=3):
    rng = np.random.default_rng(seed)
    out = []
    for i in range(n):
        z = float(rng.normal())
        typ = T_OWNER if i % 2 else T_OTHER
        c = 1.0 if typ == T_OWNER else 0.4
        base = np.full(years, float(rng.uniform(500, 3000)))
        u = rng.gamma(1 / alpha, alpha)
        t = np.arange(2016, 2016 + years)
        y = rng.poisson(0.02 * math.exp(beta * z) * np.exp(gamma * (t - 2020)) * u * c * base)
        out.append(ao.with_z(_pl(str(i), y, base, typ), z))
    return out


def test_fit3_trend_without_gamma_reproduces_fit3_term():
    places = _synthetic(gamma=0.0, beta=-0.5, n=24)
    want = ao.fit3_term(places, estimate_beta=True, grid=GRID)
    got = at.fit3_trend(places, estimate_beta=True, estimate_gamma=False, grid=GRID)
    assert (got.m_owner, got.m_other) == (want.m_owner, want.m_other)
    assert got.loglik == pytest.approx(want.loglik, abs=1e-3)
    assert got.theta == pytest.approx(want.theta, rel=1e-3)
    assert got.alpha == pytest.approx(want.alpha, rel=1e-2)
    assert got.beta == pytest.approx(want.beta, abs=1e-3)
    assert got.beta_low == pytest.approx(want.beta_low, abs=5e-3)
    assert got.low == pytest.approx(want.low, rel=1e-2) and got.high == pytest.approx(want.high, rel=1e-2)
    assert got.gamma == 0.0 and not got.gamma_estimated


def test_fit3_trend_recovers_a_planted_gamma():
    places = _synthetic(gamma=-0.15, n=50)
    fit = at.fit3_trend(places, estimate_beta=False, grid=GRID)
    assert fit.gamma_low < -0.15 < fit.gamma_high and fit.gamma_high < 0
    assert fit.theta == pytest.approx(0.02, rel=0.5)
    assert at.gamma_draws(fit, 2000, 1).std() == pytest.approx(fit.gamma_se, rel=0.1)
    flat = at.fit3_trend(places, estimate_beta=False, estimate_gamma=False, grid=GRID)
    assert fit.loglik > flat.loglik
    assert at.gamma_draws(flat, 10, 1) is None


def test_forecast_log_score_hand_worked():
    # One draw, α -> 0 (Poisson): the late years are independent of the early ones: P(y_l) = Poisson.
    early, late = _pl("a", [1, 2], [1.0, 1.0]), _pl("a", [0, 3], [1.0, 2.0], start=2018)
    g = jr.GlobalsA(np.array([1.0]), 0.0, cal._cvals(1, 1))
    want = -1.0 + (3 * math.log(2) - 2 - math.log(6))
    assert at.forecast_log_score(early, late, g) == pytest.approx(want)
    # α = 1 (geometric), one early year y 0 at mean 1, one late year y 0 at mean 1:
    # u | early ~ Gamma(1, rate 2), P(late 0) = 2 / 3.
    g1 = jr.GlobalsA(np.array([1.0]), 1.0, cal._cvals(1, 1))
    e1, l1 = _pl("b", [0], [1.0]), _pl("b", [0], [1.0], start=2017)
    assert at.forecast_log_score(e1, l1, g1) == pytest.approx(math.log(2 / 3))


def test_forecast_draws_follow_the_posterior():
    # α 1, early y = 4 over mean 2: u | early ~ Gamma(5, rate 3); late mean 3 -> E[y_l] = 3 × 5/3 = 5.
    n = 200_000
    e, late = _pl("a", [4], [2.0]), _pl("a", [0], [3.0], start=2017)
    g = jr.GlobalsA(np.ones(n), 1.0, cal._cvals(1, 1))
    d = at.forecast(e, late, g, seed=2)
    assert d.mean() == pytest.approx(5.0, rel=0.02)


def test_persistence_hand_worked():
    e, late = _pl("a", [2], [1.0], parcels=4.0), _pl("a", [0], [1.0], start=2017, parcels=2.0)
    _, ll = at.persistence(e, late, 10, seed=1, prior=0.0)
    assert ll == pytest.approx(math.log(4 / 9))


def test_extrapolation_and_decision_hand_worked():
    assert at.choose_extrapolation(5, 2) == "continue" and at.choose_extrapolation(3, 2) == "flat"
    u = {0: 1, 1: 1, 2: 1}
    assert at.decide(10, 3, -0.3, -0.1, u, {0: 1, 1: 2, 2: 1}, 1, 1).trend
    assert not at.decide(5, 3, -0.3, -0.1, u, u, 1, 1).trend
    assert not at.decide(10, 3, -0.2, 0.1, u, u, 1, 1).trend
    assert not at.decide(10, 3, -0.3, -0.1, u, {0: 1, 1: 1, 2: 0}, 1, 1).trend
    assert not at.decide(10, 3, -0.3, -0.1, u, u, 1, 0).trend


def test_rule_age_hand_worked():
    pl = _pl("a", [0, 0, 0], [1, 1, 1])
    pl.extra["age"] = np.array([[1, np.nan], [2, 0.5], [12, 1]])
    assert at.rule_age(pl) == pytest.approx([1, 2, 10])
