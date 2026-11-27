"""D-087 Form A″ (several place terms): each step against a hand-worked example, Form A or Form A′ (synthetic
data only)."""

import math

import numpy as np
import pytest

from lotline.calibrate.adu import adu_terms as at
from lotline.calibrate.adu import calibrate_adu as cal
from lotline.calibrate.adu import joint_refit as jr
from lotline.model import adu_owner as ao

T_OWNER, T_OTHER, T_HB = 1, 2, 4


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


def test_age_z_hand_worked():
    assert at.age_share_z(0.40, 0.2045, 0.1669) == pytest.approx(1.17136, abs=1e-5)


def test_scaled_folds_both_terms():
    pl = at.with_zv(_pl("a", [0, 0], [100, 200]), (1.0, 2.0))
    assert at.scaled(pl, np.array([math.log(2), 0.0])).base == pytest.approx([200, 400])
    # both terms: log 2 · 1 + log 3 · 2 = log 18
    assert at.offset(pl, np.array([math.log(2), math.log(3)])) == pytest.approx(math.log(18))


def test_two_term_loglik_hand_worked():
    # y 2, k 0.5, θ 1, β (log 2, log 3), z (1, 0): rate × k = 1 and α 1 -> log(1/8)
    pl = at.with_zv(_pl("a", [2], [0.5]), (1.0, 0.0))
    g = jr.GlobalsA(np.array([1.0]), 1.0, cal._cvals(1.0, 1.0), beta=np.array([[math.log(2), math.log(3)]]))
    assert jr.place_loglik(pl, g)[0] == pytest.approx(math.log(1 / 8))


def test_vector_draws_equal_form_a_on_scaled_places():
    pl = at.with_zv(_pl("a", [3, 0, 5], [2.0, 1.0, 4.0]), (-0.7, 1.2))
    cv = cal._cvals(1.0, 1.0)
    beta = np.array([[-0.5, 0.3], [0.0, 0.0], [0.9, -0.4]])
    scale = np.array([0.4, 1.1, 2.0])
    g = jr.GlobalsA(scale, 1.3, cv, beta=beta)
    for j in range(3):
        want = jr.place_loglik(at.scaled(pl, beta[j]), jr.GlobalsA(scale[j : j + 1], 1.3, cv))[0]
        assert jr.place_loglik(pl, g)[j] == pytest.approx(want)


def test_one_term_draws_unchanged():
    # D-084's scalar path still works next to the vector path
    pl = ao.with_z(_pl("a", [1], [1.0]), 2.0)
    g = jr.GlobalsA(np.array([1.0]), 1.0, cal._cvals(1.0, 1.0), beta=np.array([0.5]))
    assert g.place_scale(pl)[0] == pytest.approx(math.exp(1.0))


def _synthetic(b1, b2, n=60, years=5, alpha=0.4, seed=3, rho=-0.4):
    rng = np.random.default_rng(seed)
    out = []
    for i in range(n):
        z1 = float(rng.normal())
        z2 = float(rho * z1 + math.sqrt(1 - rho**2) * rng.normal())
        typ = T_OWNER if i % 2 else T_OTHER
        c = 1.0 if typ == T_OWNER else 0.4
        base = np.full(years, float(rng.uniform(500, 3000)))
        u = rng.gamma(1 / alpha, alpha)
        y = rng.poisson(0.02 * math.exp(b1 * z1 + b2 * z2) * u * c * base)
        pl = at.with_zv(_pl(str(i), y, base, typ), (z1, z2))
        out.append(ao.with_z(pl, z1))
    return out


GRID = (0.2, 0.4, 0.7, 1.0)


def test_no_terms_reproduces_fit3_term_form_a():
    places = _synthetic(0.0, 0.0, n=24)
    want = ao.fit3_term(places, estimate_beta=False, grid=GRID)
    got = at.fit3_terms(places, use=(), grid=GRID)
    assert (got.m_owner, got.m_other) == (want.m_owner, want.m_other)
    assert got.theta == pytest.approx(want.theta, rel=1e-3)
    assert got.loglik == pytest.approx(want.loglik, abs=1e-3)
    assert got.low == pytest.approx(want.low, rel=1e-2) and got.high == pytest.approx(want.high, rel=1e-2)
    assert at.beta_draws(got, 10, 1) is None


def test_one_term_reproduces_fit3_term_form_a_prime():
    places = _synthetic(-0.7, 0.0, n=40)
    want = ao.fit3_term(places, grid=GRID)
    got = at.fit3_terms(places, use=(0,), grid=GRID)
    assert (got.m_owner, got.m_other) == (want.m_owner, want.m_other)
    assert got.betas[0] == pytest.approx(want.beta, abs=2e-3)
    assert got.loglik == pytest.approx(want.loglik, abs=1e-3)
    assert got.theta == pytest.approx(want.theta, rel=1e-2)
    # Wald 90% from the Hessian against the profile interval: close for a well-identified β
    lo, hi = got.beta_interval[0]
    assert lo == pytest.approx(want.beta_low, abs=0.05) and hi == pytest.approx(want.beta_high, abs=0.05)


def test_two_terms_recover_planted_betas_and_beat_one():
    places = _synthetic(-0.6, 0.5, n=80)
    two = at.fit3_terms(places, use=(0, 1), grid=GRID)
    one = at.fit3_terms(places, use=(0,), grid=GRID)
    (lo1, hi1), (lo2, hi2) = two.beta_interval
    assert lo1 < -0.6 < hi1 and lo2 < 0.5 < hi2
    assert two.loglik > one.loglik
    cov = np.asarray(two.cov)
    assert cov[0, 1] > 0  # negatively correlated factors give positively correlated β's
    d = at.beta_draws(two, 20_000, 1)
    assert d.shape == (20_000, 2)
    assert np.cov(d.T)[0, 1] == pytest.approx(cov[0, 1], rel=0.1)


def test_unused_term_draws_are_zero():
    places = _synthetic(-0.6, 0.5, n=30)
    one = at.fit3_terms(places, use=(0,), grid=(0.4, 1.0))
    d = at.beta_draws(one, 100, 2)
    assert d.shape == (100, 2) and np.all(d[:, 1] == 0)
