"""D-084 Form A′: each step against a hand-worked example or Form A itself (synthetic data only)."""

import math

import numpy as np
import pytest

from lotline.model import adu_owner as ao
from lotline.model import calibrate_adu as cal
from lotline.model import joint_refit as jr

T_OWNER, T_OTHER, T_HB = 1, 2, 4  # adu.TYPES indices: owner occupancy, other partial rule, Handbook


def _pl(geoid, y, base, typ=T_HB, state="MN"):
    n = len(y)
    return cal.PlaceData(
        state,
        geoid,
        geoid,
        np.arange(2016, 2016 + n),
        np.asarray(y, dtype=float),
        np.asarray(base, dtype=float),
        np.full((1, n, 1), typ),
        np.ones((n, 1)),
        np.array([1.0]),
        None,
        {"parcels": np.full(n, 1000.0)},
    )


def test_owner_z_hand_worked():
    assert ao.owner_z(0.52, 0.6727, 0.1544) == pytest.approx(-0.98899, abs=1e-5)
    assert ao.owner_z(0.6727, 0.6727, 0.1544) == 0.0


def test_scaled_folds_the_term_into_exposure():
    pl = ao.with_z(_pl("a", [0, 0], [100, 200]), 1.0)
    assert ao.scaled(pl, math.log(2)).base == pytest.approx([200, 400])
    assert ao.place_z(_pl("b", [0], [1])) == 0.0  # no z: Form A


def test_form_a_prime_loglik_hand_worked():
    # y = 2, k = 0.5, θ = 1, β = log 2, z = 1: rate × k = 1, α = 1 -> the geometric case, log(1/8)
    pl = ao.with_z(_pl("a", [2], [0.5]), 1.0)
    g = jr.GlobalsA(np.array([1.0]), 1.0, cal._cvals(1.0, 1.0), beta=np.array([math.log(2)]))
    assert jr.place_loglik(pl, g)[0] == pytest.approx(math.log(1 / 8))


def test_form_a_prime_equals_form_a_on_scaled_places():
    pl = ao.with_z(_pl("a", [3, 0, 5], [2.0, 1.0, 4.0]), -0.7)
    cv = cal._cvals(1.0, 1.0)
    beta = np.array([-0.5, 0.0, 0.9])
    scale = np.array([0.4, 1.1, 2.0])
    g_p = jr.GlobalsA(scale, 1.3, cv, beta=beta)
    for j in range(3):
        g_a = jr.GlobalsA(scale[j : j + 1], 1.3, cv)
        want = jr.place_loglik(ao.scaled(pl, float(beta[j])), g_a)[0]
        assert jr.place_loglik(pl, g_p)[j] == pytest.approx(want)


def test_predict_mean_carries_the_term():
    pl = ao.with_z(_pl("a", [0, 0], [10.0, 10.0]), 1.0)
    n = 200_000
    g = jr.GlobalsA(np.full(n, 0.5), 0.5, cal._cvals(1.0, 1.0), beta=np.full(n, math.log(3)))
    d = jr.predict([pl], g, seed=1)["a"]
    assert d.mean() == pytest.approx(0.5 * 3 * 10, rel=0.02)  # θ e^{βz} k = 15 a year


def test_form_a_draws_unchanged_without_beta():
    fit = cal.Fit3(1e-3, 5e-4, 2e-3, 1.0, 1.0, 0.4, (1, 1), (0.4, 0.4), True, True, -1.0, 1, 1)
    a = jr.globals_a(fit, 0.3, 100, seed=5)
    b = jr.globals_a(fit, 0.3, 100, seed=5, beta=None)
    assert np.array_equal(a.scale, b.scale) and b.beta is None
    pl = ao.with_z(_pl("a", [1], [1.0]), 2.0)
    assert np.array_equal(a.place_scale(pl), a.scale)  # Form A ignores z


def _synthetic(beta, n=40, years=5, alpha=0.4, seed=3):
    rng = np.random.default_rng(seed)
    out = []
    for i in range(n):
        z = float(rng.normal())
        typ = T_OWNER if i % 2 else T_OTHER
        c = 1.0 if typ == T_OWNER else 0.4  # truth m_o 1.0, m_x 0.4
        base = np.full(years, float(rng.uniform(500, 3000)))
        u = rng.gamma(1 / alpha, alpha)
        y = rng.poisson(0.02 * math.exp(beta * z) * u * c * base)
        out.append(ao.with_z(_pl(str(i), y, base, typ), z))
    return out


GRID = (0.2, 0.4, 0.7, 1.0)


def test_fit3_term_without_beta_reproduces_fit3():
    places = _synthetic(beta=0.0, n=24)
    want = cal.fit3(places, grid=GRID)
    got = ao.fit3_term(places, estimate_beta=False, grid=GRID)
    assert (got.m_owner, got.m_other) == (want.m_owner, want.m_other)
    assert got.theta == pytest.approx(want.theta, rel=1e-3)
    assert got.alpha == pytest.approx(want.alpha, rel=1e-2)
    assert got.loglik == pytest.approx(want.loglik, abs=1e-3)
    assert got.low == pytest.approx(want.low, rel=1e-2) and got.high == pytest.approx(want.high, rel=1e-2)
    assert got.beta == 0.0 and not got.beta_estimated


def test_fit3_term_recovers_a_planted_beta():
    places = _synthetic(beta=-0.7, n=60)
    fit = ao.fit3_term(places, grid=GRID)
    assert fit.beta_low < -0.7 < fit.beta_high
    assert fit.beta_high < 0
    assert fit.theta == pytest.approx(0.02, rel=0.5)
    assert ao.beta_draws(fit, 1000, 1).std() == pytest.approx(fit.beta_se, rel=0.1)


def test_decision_rule_hand_worked():
    assert ao.decide(None, None, 10, 4, 1, 1).form == "A′"
    assert ao.decide(None, None, 7, 4, 1, 1).form == "A"
    assert ao.decide(None, None, 10, 4, 1, 0).form == "A"
    assert ao.decide(2, 1, -5, 4, 1, 1).form == "A′"
    assert ao.decide(1, None, 50, 1, 1, 1).form == "A"
    assert ao.decide(1, 1, 10, 4, 2, 2).form == "A′"


def test_vintage_share_hand_worked():
    rows = {2015: 0.6, 2020: 0.55, 2024: 0.5}
    assert ao.vintage_share(rows, 2022) == (0.55, 2020)
    assert ao.vintage_share(rows, 2010) == (None, None)
    assert ao.vintage_share({2015: 0.6, 2020: float("nan")}, 2024) == (0.6, 2015)
