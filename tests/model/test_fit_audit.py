"""Residual audit (model/fit_audit.py, D-045): each function against a hand-worked example. Synthetic only."""

import math

import numpy as np
import pandas as pd
import pytest

from lotline.model import calibrate_adu as cal
from lotline.model import fit_audit as fa


def _fit(theta=0.002, alpha=0.5, m_owner=0.5, m_other=0.3):
    return cal.Fit3(theta, theta / 2, theta * 2, alpha, m_owner, m_other, (0, 1), (0, 1), True, True,
                    0.0, 1, 1)  # fmt: skip


def test_expected_by_year_by_hand():
    """Two blank-field combinations, weights 3:1; base 1,000 a year for two years; combination 0 is a Handbook
    rule (c = 1), combination 1 owner-restricted (c = m_owner = 0.5); coverage × ramp 0.4 then 0.8.
    k = 1,000 × (0.75 × 1 + 0.25 × 0.5) × (0.4, 0.8) = (350, 700); × θ 0.002 = (0.7, 1.4)."""
    types = np.array([[[4], [4]], [[1], [1]]])
    years, y, base = np.array([2020, 2021]), np.array([1.0, 2.0]), np.array([1000.0, 1000.0])
    pl = cal.PlaceData("MN", "X", "X", years, y, base, types, np.array([[0.4], [0.8]]), np.array([3.0, 1.0]))
    assert fa.expected_by_year(pl, _fit()) == pytest.approx([0.7, 1.4])


def test_log_ratio_and_posterior_u_by_hand():
    assert fa.log_ratio(9.5, 4.5) == pytest.approx(math.log(2))
    assert fa.log_ratio(0, 0) == 0
    assert fa.posterior_u(10, 4, 0.5) == pytest.approx(2.0)
    assert fa.posterior_u(10, 4, 0.0) == pytest.approx(1.0)


def test_group_ratios_sum_before_dividing():
    df = pd.DataFrame({"g": ["a", "a", "b"], "observed": [1, 3, 5], "expected": [2, 2, 10]})
    r = fa.group_ratios(df, "g").set_index("g")
    assert r.loc["a", "ratio"] == pytest.approx(1.0) and r.loc["b", "ratio"] == pytest.approx(0.5)
    assert r.loc["a", "places"] == 2


def test_fe_slope_removes_group_levels_by_hand():
    """Two groups, x = (0, 1) in each, lr = (0, 2) and (5, 7): within each group lr rises 2 per unit of x, so
    the slope is 2 although the groups' levels differ by 5; a pooled slope without groups would be 2 too only
    by symmetry, so a third check shifts x in group b: x = (10, 11) still gives 2."""
    assert fa.fe_slope([0, 2, 5, 7], [0, 1, 0, 1], ["a", "a", "b", "b"], [1, 1, 1, 1]) == pytest.approx(2)
    assert fa.fe_slope([0, 2, 5, 7], [0, 1, 10, 11], ["a", "a", "b", "b"], [1, 1, 1, 1]) == pytest.approx(2)


def test_bootstrap_slope_recovers_a_known_slope():
    rng = np.random.default_rng(1)
    g = np.repeat(["a", "b", "c"], 40)
    x = rng.normal(size=120)
    lr = 0.5 * x + np.repeat([0.0, 1.0, -1.0], 40) + rng.normal(0, 0.2, size=120)
    est, lo, hi = fa.bootstrap_slope(lr, x, g, np.ones(120), n=300, seed=2)
    assert est == pytest.approx(0.5, abs=0.06) and lo < 0.5 < hi and hi - lo < 0.3


def test_iqr_effect_by_hand():
    """x = 1..5: Q1 2, Q3 4; slope ln 2 / 2 gives exp(ln 2) = 2 across the IQR."""
    assert fa.iqr_effect(math.log(2) / 2, [1, 2, 3, 4, 5]) == pytest.approx(2.0)


def test_noise_floor_by_hand():
    """Draws 1..10: P10 1.9, P50 5.5, P90 9.1. Useful needs 2.75 <= d <= 9.1: 3 to 9, 7 of 10."""
    useful, rms = fa.noise_floor(np.arange(1, 11))
    assert useful == pytest.approx(0.7)
    expect = np.sqrt(np.mean(np.log((np.arange(1, 11) + 0.5) / 6.0) ** 2))
    assert rms == pytest.approx(expect)
