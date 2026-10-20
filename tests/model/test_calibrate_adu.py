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


def test_mixture_loglik_by_hand():
    """y = 2, μ_a = 1, μ_b = 2, q = 0.5, Poisson:
    log(0.5·e^-1·1/2 + 0.5·e^-2·4/2) = log(0.091970 + 0.135335) = −1.4814."""
    expected = math.log(0.5 * math.exp(-1) / 2 + 0.5 * math.exp(-2) * 4 / 2)
    assert cal.mix_loglik([2], [1.0], [2.0], [0.5], 0.0) == pytest.approx(expected)
    assert expected == pytest.approx(-1.4814, abs=1e-4)
    # q = 0 is the plain likelihood at μ_b; q = 1 at μ_a
    assert cal.mix_loglik([2], [1.0], [2.0], [0.0], 0.7) == pytest.approx(cal.nb_loglik([2], [2.0], 0.7))
    assert cal.mix_loglik([2], [1.0], [2.0], [1.0], 0.7) == pytest.approx(cal.nb_loglik([2], [1.0], 0.7))


def test_mixture_fit_reduces_to_the_plain_fit_and_recovers_theta():
    rng = np.random.default_rng(11)
    k = rng.uniform(2_000, 40_000, 200)
    y = rng.poisson(0.003 * k)
    plain = cal.fit_anchor(y, k)
    mixed = cal.fit_anchor(y, k, k_b=k, q=np.full(200, 0.4))  # both components equal: same fit
    assert mixed.theta == pytest.approx(plain.theta, rel=1e-4)
    # half the places are restricted (k × 0.3) with known probability 0.5: θ is still recovered
    restricted = rng.random(200) < 0.5
    y2 = rng.poisson(0.003 * np.where(restricted, 0.3 * k, k))
    fit = cal.fit_anchor(y2, 0.3 * k, k_b=k, q=np.full(200, 0.5))
    assert fit.low <= 0.003 <= fit.high


def test_k_paths_by_hand():
    """parcels 1,000, h1 0.5, s 0.3: a rule with blanks fully ramped (ramp_blank 1), none other.
    A (blank restricts): 500 × 0.3 = 150; B (it doesn't): 500 × 1 = 500."""
    rows = {
        "eligible_parcels": np.array([1000.0]),
        "h1": np.array([0.5]),
        "ramp_partial": np.array([0.0]),
        "ramp_handbook": np.array([0.0]),
        "ramp_blank": np.array([1.0]),
    }
    a, b = cal.k_paths(rows, 0.3)
    assert (a[0], b[0]) == pytest.approx((150, 500))


def test_place_years_keeps_observed_counts(monkeypatch):
    """Regression (fit 2's first run): the observed ADU counts must reach the fit rows, not be overwritten."""
    import pandas as pd

    from lotline.model.scenarios import adu

    class Store:
        def read(self, state, table):
            return {
                "market_geo_year": pd.DataFrame(
                    {
                        "geo": ["national:US"] * 2,
                        "year": [2024, 2025],
                        "cpi_u": [100.0, 100.0],
                        "mortgage_rate": [6.0, 6.0],
                    }
                ),
                "acs_geo_year": pd.DataFrame(
                    {
                        "geo": ["place:9900001"] * 2,
                        "end_year": [2024, 2024],
                        "variable": ["B25064_001", "B25077_001"],
                        "estimate": [1500.0, 400_000.0],
                    }
                ),
                "jurisdictions": pd.DataFrame(
                    {"geoid": ["9900001"], "name": ["Test city"], "kind": ["place"]}
                ),
                "eligible_parcels": pd.DataFrame(
                    {
                        "jurisdiction_geoid": ["9900001"],
                        "year": [2024],
                        "theme": ["adu"],
                        "rule_version": [__import__("lotline.build.eligible", fromlist=["x"]).RULE_VERSION],
                        "eligible_parcels": [10_000],
                    }
                ),
                "permits": pd.DataFrame(
                    {
                        "jurisdiction_geoid": ["9900001"] * 3,
                        "source": ["city"] * 3,
                        "issue_year": [2025] * 3,
                        "building_type_std": ["ADU", "ADU", "SFD"],
                        "adu_type": [None] * 3,
                    }
                ),
            }[table]

    reforms = pd.DataFrame(
        {
            "reform_id": ["T1"],
            "state": ["MN"],
            "jurisdiction_geoid": ["9900001"],
            "theme": ["adu"],
            "status": ["in_force"],
            "effective_date": pd.to_datetime(["2020-01-01"]),
            "end_date": pd.NaT,
            "supersedes": [None],
            "by_right": [True],
            "owner_occ": [False],
            "adu_detached_allowed": [True],
            "adu_max_sqft": [800.0],
            "parking": ["none"],
            "parking_min_per_unit": [0.0],
            "adus_per_lot": [1],
            "coverage": ["Citywide"],
        }
    )
    monkeypatch.setattr(adu, "load_reforms", lambda st: reforms if st == "MN" else reforms.iloc[0:0])
    rows = cal.place_years("MN", Store(), ["9900001"], [2025])
    assert rows["adu_permits"].tolist() == [2]
