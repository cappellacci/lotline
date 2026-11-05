"""Held-out log score (model/score.py, D-049): hand-worked and numerical checks. Synthetic inputs only."""

import math

import numpy as np
import pytest

from lotline.model import calibrate_adu as cal
from lotline.model import calibrate_shape as shp
from lotline.model import score


def _place(y, base, w=(1.0,), types=((4,),)):
    n = len(y)
    t = np.array([[list(row) for _ in range(n)] for row in types])
    return cal.PlaceData("MN", "X", "X", np.arange(n), np.asarray(y, float), np.asarray(base, float), t,
                         np.ones((n, t.shape[2])), np.asarray(w, float))  # fmt: skip


def _fit(theta, low, high, alpha):
    return cal.Fit3(theta, low, high, alpha, 0.5, 0.3, (0, 1), (0, 1), True, True, 0.0, 1, 1)


def test_score_without_theta_uncertainty_is_the_fit_likelihood():
    """se = 0: the score is `frailty_loglik` for the one place (blank-field mixture included)."""
    pl = _place([3, 1], [1000.0, 1000.0], w=(0.25, 0.75), types=((1,), (4,)))
    f = _fit(0.002, 0.002, 0.002, 0.5)
    want = cal.frailty_loglik([pl], 0.002, 0.5, cal._cvals(0.5, 0.3))
    assert score.place_log_score(pl, f) == pytest.approx(want)


def test_score_integrates_theta_like_monte_carlo():
    """θ with a 90% interval 0.001-0.004 (log-SE 0.421): Gauss-Hermite matches a 200,000-draw Monte Carlo
    average of the place likelihood."""
    pl = _place([4, 6, 2], [1000.0] * 3)
    f = _fit(0.002, 0.001, 0.004, 0.3)
    rng = np.random.default_rng(0)
    th = np.exp(rng.normal(math.log(0.002), f.log_se, size=200_000))
    lp = [cal.frailty_loglik_place(pl.y, pl.base, t, 0.3) for t in th[:20_000]]
    mc = math.log(np.mean(np.exp(lp)))
    assert score.place_log_score(pl, f) == pytest.approx(mc, abs=0.02)


def test_nb_panel_logpdf_matches_frailty_loglik_place():
    y = np.array([2.0, 0.0, 5.0])
    mu = np.array([[1.0, 2.0, 3.0], [0.5, 0.5, 6.0]])
    lf = sum(math.lgamma(v + 1) for v in y)
    got = score.nb_panel_logpdf(y, mu, 0.7, lf)
    want = [cal.frailty_loglik_place(y, m, 1.0, 0.7) for m in mu]
    assert got == pytest.approx(want)


def test_empirical_score_with_no_coefficient_uncertainty():
    """Σ = 0: every draw is β̂, so the score is P_NB at μ(β̂)."""
    n = 2
    extra = {"rent": np.full(n, 1500.0), "home_value": np.full(n, 300_000.0), "rate": np.full(n, 5.0),
             "parcels": np.full(n, 10_000.0), "report": np.ones(n), "cov": np.ones((n, 1)),
             "age": np.ones((n, 1)), "no_detached": np.zeros((1, n, 1), bool)}  # fmt: skip
    pl = cal.PlaceData("MN", "X", "X", np.arange(n), np.array([3.0, 7.0]), np.ones(n), np.full((1, n, 1), 4),
                       np.ones((n, 1)), np.array([1.0]), None, extra)  # fmt: skip
    beta = np.zeros(8)
    beta[0] = math.log(5e-4)
    f = shp.EmpFit(beta, 0.4, np.zeros((9, 9)), 0.0, 1)
    want = cal.frailty_loglik_place(pl.y, np.full(n, 5.0), 1.0, 0.4)
    assert score.empirical_log_score(pl, f, draws=50) == pytest.approx(want)


def test_paired_by_hand():
    s, se = score.paired([1, 2, 3])
    assert s == 6 and se == pytest.approx(math.sqrt(3))
