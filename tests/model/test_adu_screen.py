"""D-083 screen: each step against a hand-worked or brute-force example (synthetic data only)."""

import math

import numpy as np
import pytest

from lotline.model import adu_screen as scr
from lotline.model import calibrate_adu as cal


def _one(y, k, w=(1.0,), geoid="g", state="MN"):
    return scr.prepare_arrays(
        [np.array(y)], [np.atleast_2d(np.array(k, dtype=float))], [np.array(w)], [geoid], [state]
    )


def test_place_loglik_hand_worked():
    # y = 2, rate·k = 1, α = 1: the geometric case, log(1/8) (calibrate_adu.frailty_loglik_place docstring)
    p = _one([2], [1.0])
    assert scr.place_loglik(p, np.array([1.0]), 1.0)[0] == pytest.approx(math.log(1 / 8))


def test_place_loglik_matches_calibrate_adu_with_combinations():
    y = np.array([0, 3, 1])
    k = np.array([[0.5, 2.0, 1.0], [1.0, 1.0, 0.2]])
    w = np.array([0.3, 0.7])
    p = _one(y, k, w)
    theta, alpha = 0.8, 1.7
    want = math.log(
        sum(wc * math.exp(cal.frailty_loglik_place(y, kc, theta, alpha)) for wc, kc in zip(w, k, strict=True))
    )
    assert scr.place_loglik(p, np.array([theta]), alpha)[0] == pytest.approx(want)
    # Poisson limit
    want0 = math.log(
        sum(wc * math.exp(cal.frailty_loglik_place(y, kc, theta, 0.0)) for wc, kc in zip(w, k, strict=True))
    )
    assert scr.place_loglik(p, np.array([theta]), 0.0)[0] == pytest.approx(want0)


def test_zero_exposure_with_a_count_is_impossible():
    p = _one([1], [0.0])
    assert scr.place_loglik(p, np.array([1.0]), 1.0)[0] == -math.inf


def test_lr_p_and_holm_hand_worked():
    assert scr.lr_p(2.705543) == pytest.approx(0.10, abs=1e-5)
    assert scr.lr_p(3.841459) == pytest.approx(0.05, abs=1e-5)
    adj = scr.holm({"a": 0.01, "b": 0.04, "c": 0.03})
    assert adj == pytest.approx({"a": 0.03, "b": 0.06, "c": 0.06})


def test_posterior_mean_hand_worked():
    p = _one([2], [1.0])
    assert scr.posterior_mean(p, np.array([1.0]), 1.0)[0] == pytest.approx(1.5)


def _synthetic(beta, n=80, years=6, alpha=0.3, seed=7):
    rng = np.random.default_rng(seed)
    z = rng.normal(size=n)
    states = np.where(np.arange(n) < n // 2, "AA", "BB")
    theta = np.where(states == "AA", 0.02, 0.05)
    lots = rng.uniform(500, 3000, size=n)
    u = rng.gamma(1 / alpha, alpha, size=n)
    ys, ks = [], []
    for i in range(n):
        k = np.full((1, years), lots[i])
        ys.append(rng.poisson(theta[i] * math.exp(beta * z[i]) * u[i] * k[0]))
        ks.append(k)
    p = scr.prepare_arrays(ys, ks, [np.array([1.0])] * n, [str(i) for i in range(n)], list(states))
    return p, z


def test_fit_recovers_a_planted_effect_and_its_alpha_drop():
    p, z = _synthetic(beta=0.7)
    row = scr.screen_one(p, z, within=True)
    assert row["beta_low"] < 0.7 < row["beta_high"]
    assert row["p"] < 0.01
    assert row["alpha_drop"] > 0.10
    assert row["sign_stable"] is True


def test_fit_finds_nothing_when_nothing_is_planted():
    p, z = _synthetic(beta=0.0, seed=11)
    row = scr.screen_one(p, z, within=True)
    assert row["beta_low"] < 0 < row["beta_high"]


def test_verdict_rules():
    base = {"p_holm": 0.05, "alpha_drop": 0.2, "sign_stable": True}
    assert scr.verdict(base) == "candidate"
    assert scr.verdict(base | {"alpha_drop": 0.05}) == "weak"
    assert scr.verdict(base | {"sign_stable": False}) == "weak"
    assert scr.verdict(base | {"p_holm": 0.2}) == "no"


def test_influence_reading_rules():
    import pandas as pd

    d = pd.DataFrame({"beta": [-0.5, -0.6, -0.4], "p": [0.01, 0.02, 0.03]})
    assert scr.influence_reading(-0.7, d) == "robust"
    assert scr.influence_reading(-0.7, d.assign(p=[0.01, 0.2, 0.03])) == "leaning on"
    assert scr.influence_reading(-0.7, d.assign(beta=[-0.5, 0.1, -0.4])) == "carried by one place"
    assert (
        scr.influence_reading(
            -0.7,
            d.assign(
                p=[
                    0.2,
                    0.2,
                    0.2,
                ][:3]
            ).iloc[:3],
        )
        == "leaning on"
    )


def test_drop_one_has_a_row_per_place():
    p, z = _synthetic(beta=0.7, n=12, seed=3)
    d = scr.drop_one(p, z)
    assert len(d) == 12 and set(d["dropped"]) == set(p.geoids)
