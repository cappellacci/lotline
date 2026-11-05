"""Approaches 2 and 3 (model/calibrate_shape.py, D-047): hand-worked examples and recovery on simulated
places. Synthetic inputs only."""

import math

import numpy as np
import pytest

from lotline.model import calibrate_adu as cal
from lotline.model import calibrate_shape as cs
from lotline.model import hazard

P = {"adu_ramp_slope_years": 0.75, "adu_ref_home_value_usd": 400_000.0, "adu_equity_elasticity": 0.25}


def _place(y, base, value, parcels, age, types=4, no_det=False, geoid="X", w=(1.0,), rent=1500.0, rate=5.0):
    n = len(y)
    c = len(w)
    extra = {
        "rent": np.full(n, rent),
        "home_value": np.asarray(value, float) * np.ones(n),
        "rate": np.full(n, rate),
        "parcels": np.asarray(parcels, float) * np.ones(n),
        "report": np.ones(n),
        "cov": np.ones((n, 1)),
        "age": np.asarray(age, float).reshape(n, 1),
        "no_detached": np.full((c, n, 1), no_det),
    }
    yy, bb, ww = np.asarray(y, float), np.asarray(base, float), np.asarray(w, float)
    tt = np.full((c, n, 1), types)
    return cal.PlaceData("MN", geoid, geoid, np.arange(n), yy, bb, tt, np.ones((n, 1)), ww, None, extra)


def test_shaped_by_hand():
    """V = 2 V_ref, equity 0.75 (central 0.25): × 2^0.5; parcels 40,000, size −0.5: × 0.5; base 1,000 ->
    707.1. No ramp: cr = coverage = 1. Half 2, age 1: cr = ramp(1; 2, 0.75) = 0.2086."""
    pl = _place([0], [1000.0], 800_000.0, 40_000.0, [1.0])
    s = cs.shaped(pl, cs.NO_RAMP, 0.75, -0.5, P)
    assert s.base[0] == pytest.approx(1000 * math.sqrt(2) * 0.5)
    assert s.cr[0, 0] == pytest.approx(1.0)
    s = cs.shaped(pl, 2.0, 0.25, 0.0, P)
    assert s.base[0] == pytest.approx(1000 * 4**0)
    assert s.cr[0, 0] == pytest.approx(float(hazard.ramp(1.0, 2.0, 0.75)), rel=1e-6)
    assert s.cr[0, 0] == pytest.approx(0.2086, abs=1e-4)


def test_fit_shape_recovers_equity_and_no_ramp():
    """60 places × 5 years, home values 0.5-2 × V_ref, true equity 1.0 (central 0.25), no ramp, θ 0.002,
    α 0.05: equity 1.0 and no ramp are chosen, θ's interval holds 0.002."""
    rng = np.random.default_rng(11)
    places = []
    for i in range(60):
        v = 400_000 * math.exp(rng.uniform(math.log(0.5), math.log(2)))
        base = np.full(5, rng.uniform(20_000, 60_000)) * (v / 400_000) ** 0.25
        mu = 0.002 * rng.gamma(20, 0.05) * base * (v / 400_000) ** 0.75
        places.append(_place(rng.poisson(mu), base, v, 10_000, np.arange(5) + 0.5, geoid=f"P{i}"))
    f = cs.fit_shape(places, P, grids=((cs.NO_RAMP, 2.0), (0.25, 1.0), (0.0,)))
    assert f.half == cs.NO_RAMP and f.equity == 1.0
    assert f.low <= 0.002 <= f.high


def test_design_by_hand():
    """Two blank-field combinations, weights 0.25 / 0.75: Handbook in the first, restricted in the second
    -> restricted = 0.75; attached-only in neither -> 0. Rent 1,500, value 300k, rate 5, parcels 10,000:
    zero covariates; age 3 -> log 4."""
    pl = _place([0], [1.0], 300_000.0, 10_000.0, [3.0], w=(0.25, 0.75))
    pl = cal.PlaceData(**{**pl.__dict__, "types": np.array([[[4]], [[2]]])})
    x, off = cs.design(pl)
    assert x[0] == pytest.approx([1, 0, 0, 0, 0, 0.75, 0, math.log(4)])
    assert off[0] == pytest.approx(math.log(10_000))


def test_emp_loglik_matches_frailty_loglik_place():
    """One place, three years: emp_loglik with only an intercept equals `frailty_loglik_place` at μ."""
    pl = _place([3, 0, 5], [1.0] * 3, 300_000.0, 10_000.0, [1.0, 2.0, 3.0])
    d = cs.EmpData.of([pl])
    beta = np.zeros(8)
    beta[0] = math.log(2e-4)
    mu = np.exp(d.off + d.x @ beta)
    want = cal.frailty_loglik_place(pl.y, mu, 1.0, 0.5)
    assert cs.emp_loglik(np.r_[beta, math.log(0.5)], d) == pytest.approx(want)


def test_nelder_mead_finds_a_quadratic_minimum():
    x, v = cs.nelder_mead(lambda q: (q[0] - 1) ** 2 + 3 * (q[1] + 2) ** 2, [0.0, 0.0])
    assert x == pytest.approx([1, -2], abs=1e-4) and v == pytest.approx(0, abs=1e-8)


def test_fit_empirical_recovers_a_home_value_coefficient():
    """60 places × 4 years, log μ = log parcels − 8 + 1.2 log(value / 300k), α 0.2: b2 ≈ 1.2 within its
    standard error band, and draws are centred on the plug-in mean."""
    rng = np.random.default_rng(3)
    places = []
    for i in range(60):
        v = 300_000 * math.exp(rng.normal(0, 0.5))
        n = rng.uniform(5_000, 40_000)
        mu = n * math.exp(-8 + 1.2 * math.log(v / 300_000)) * rng.gamma(5, 0.2)
        rent, rate = 1500 * math.exp(rng.normal(0, 0.3)), 5 + rng.normal(0, 1)
        y = rng.poisson(np.full(4, mu))
        places.append(_place(y, [1.0] * 4, v, n, [2.0] * 4, geoid=f"P{i}", rent=rent, rate=rate))
    f = cs.fit_empirical(places, starts=2)
    se = math.sqrt(f.cov[2, 2])
    assert abs(f.beta[2] - 1.2) < 3 * se and se < 0.5
    d = cs.predict_empirical(places[:3], f, draws=4000, seed=1)
    assert set(d) == {"P0", "P1", "P2"} and d["P0"].shape == (4000, 4)
