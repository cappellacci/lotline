"""ADU anchor estimation (model/calibrate_adu.py): likelihood by hand and recovery on synthetic counts."""

import math

import numpy as np
import pytest

from lotline.model import calibrate_adu as cal


def test_nb_loglik_by_hand():
    """y = 2, μ = 1. Poisson: log(e^-1 · 1² / 2!) = −1 − log 2 = −1.6931. NB with α = 1 (r = 1, geometric
    with p = r/(r+μ) = 1/2): Γ(3)/(Γ(1)·2!) · (1/2)^1 · (1/2)^2 = 1/8 -> log = −2.0794."""
    assert cal.nb_loglik([2], [1.0], 0.0) == pytest.approx(-1 - math.log(2))
    assert cal.nb_loglik([2], [1.0], 1.0) == pytest.approx(math.log(1 / 8))
    assert cal.nb_loglik([2], [1.0], 1e-9) == pytest.approx(-1 - math.log(2), abs=1e-6)  # α -> 0 is Poisson


def test_poisson_mle_by_hand():
    """Poisson with μ = θ k has MLE θ = Σy / Σk: y = (3, 5), k = (100, 300) -> θ = 8 / 400 = 0.02.
    Equidispersed data, so α is profiled to 0 (or near it)."""
    fit = cal.fit_anchor([3, 5], [100, 300])
    assert fit.theta == pytest.approx(0.02, rel=1e-4)
    assert fit.low < 0.02 < fit.high


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_recovers_a_known_anchor(seed):
    """Simulate 300 place-years from θ = 0.003 and α = 0.4; the 90% interval contains 0.003 and the estimate
    is within 25% of it."""
    rng = np.random.default_rng(seed)
    k = rng.uniform(2_000, 60_000, 300)
    mu = 0.003 * k
    y = rng.poisson(rng.gamma(1 / 0.4, mu * 0.4))
    fit = cal.fit_anchor(y, k)
    assert fit.low <= 0.003 <= fit.high
    assert fit.theta == pytest.approx(0.003, rel=0.25)
    assert fit.alpha == pytest.approx(0.4, rel=0.5)


def test_interval_coverage_on_repeated_simulation():
    """Across 60 simulated data sets the 90% profile interval covers the true θ in roughly 90% of them."""
    hits = 0
    for seed in range(60):
        rng = np.random.default_rng(100 + seed)
        k = rng.uniform(500, 20_000, 40)
        y = rng.poisson(rng.gamma(1 / 0.5, 0.002 * k * 0.5))
        fit = cal.fit_anchor(y, k)
        hits += fit.low <= 0.002 <= fit.high
    assert 0.78 <= hits / 60 <= 0.98


def test_predictive_counts_center_on_theta_k():
    fit = cal.Fit(theta=0.002, low=0.0018, high=0.0022, alpha=0.1, loglik=0.0, n=10)
    draws = cal.predictive([10_000, 50_000], fit, draws=20_000)
    assert draws.mean(axis=0) == pytest.approx([20, 100], rel=0.05)


def test_k_of_share_by_hand():
    """k = max(s × k_partial, k_handbook): s = 0.3, k_partial (100, 0), k_handbook (10, 50) -> (30, 50)."""
    assert cal.k_of_share([10, 50], [100, 0], 0.3) == pytest.approx([30, 50])


def test_partial_share_is_recovered_when_the_data_identify_it():
    """Many partial-rule and many Handbook-rule place-years with Poisson counts from θ = 0.002 and s = 0.25:
    the profile interval for s contains 0.25 and is narrower than the judgment range (0.1-0.6)."""
    rng = np.random.default_rng(7)
    n = 120
    kp = np.r_[rng.uniform(20_000, 80_000, n), np.zeros(n)]
    kh = np.r_[np.zeros(n), rng.uniform(20_000, 80_000, n)]
    y = rng.poisson(0.002 * cal.k_of_share(kh, kp, 0.25))
    grid = np.round(np.arange(0.05, 1.0001, 0.05), 2)
    _, ll, (lo, hi) = cal.profile_share(y, kh, kp, grid)
    assert lo <= 0.25 <= hi and hi - lo < 0.5
