"""D-091, adopted 2026-11-15: a place's own ADU counts × drift set its no-reform rate; a bill scales it by the
mechanism's Handbook / current-rules ratio. Hand-worked checks of `own_rate_paths`, `own_rate_draws`,
`own_rate_central` and the switch."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from lotline.model.scenarios import adu

P = adu.central_params()


def _places(**cols):
    base = {
        "geoid": ["X"],
        "eligible_parcels": [2000.0],
        "rent": [1100.0],
        "home_value": [P["adu_ref_home_value_usd"] / 2],
        "mortgage_rate": [P["adu_ref_mortgage_rate"] + 2],
        "rule_class": ["none"],
        "rule_age": [np.nan],
        "observed_rate": [np.nan],
    }
    base.update({k: v if isinstance(v, list) else [v] for k, v in cols.items()})
    n = max(len(v) for v in base.values())
    return pd.DataFrame({k: v * n if len(v) == 1 else v for k, v in base.items()})


def test_own_rate_paths_by_hand():
    """Ratio where the mechanism's no-reform hazard is positive; its added hazard where it is 0; NaN keeps the
    mechanism."""
    cur, hb = adu.own_rate_paths([0.01, 0.001, np.nan], [0.02, 0.0, 0.02], [0.05, 0.03, 0.05])
    np.testing.assert_allclose(cur, [0.01, 0.001, 0.02])
    np.testing.assert_allclose(hb, [0.025, 0.031, 0.05])


def test_own_rate_paths_cap_at_one_and_add_nothing_when_the_mechanism_adds_nothing():
    cur, hb = adu.own_rate_paths([0.6, 0.3], [0.1, 0.2], [0.3, 0.2])
    np.testing.assert_allclose(cur, [0.6, 0.3])
    np.testing.assert_allclose(hb, [1.0, 0.3])  # 0.6 × 3 capped; ratio 1 adds nothing


def test_own_rate_central_by_hand():
    """Rate 0.01 on 100 lots over 3 years: Y 3, E 300, (3 + 0.5) / 300."""
    np.testing.assert_allclose(adu.own_rate_central([0.01, np.nan], [100.0, 100.0], 3), [3.5 / 300, np.nan])


def test_own_rate_draws_match_persistence_and_drift():
    """Without drift the draws are Gamma(Y + 0.5, E): mean (Y + 0.5) / E. With σ the log spread grows by σ²
    and the median of the drift factor stays 1."""
    n = 200_000
    flat = adu.own_rate_draws([0.01, np.nan], [100.0, 100.0], 3, 0.0, n, 1)
    assert np.isnan(flat[:, 1]).all()
    assert flat[:, 0].mean() == pytest.approx(3.5 / 300, rel=0.01)
    sigma = 1.025
    flat = adu.own_rate_draws([0.01], [100.0], 3, 0.0, n, 1)
    drifted = adu.own_rate_draws([0.01], [100.0], 3, sigma, n, 1)
    # same stream: the gamma draws are identical, so the ratio is the drift factor exp(σ z)
    log_d = np.log(drifted[:, 0] / flat[:, 0])
    assert np.median(log_d) == pytest.approx(0.0, abs=0.01)
    assert log_d.std() == pytest.approx(sigma, rel=0.01)


def test_mean_one_drift_is_the_median_one_drift_times_exp_minus_half_sigma_squared():
    """Same stream: every mean-1 draw is the median-1 draw × exp(−σ²/2) (σ 1.025: × 0.5914), and the drift
    factor's mean is 1 (its median exp(−σ²/2))."""
    n, sigma = 200_000, 1.025
    median_one = adu.own_rate_draws([0.01], [100.0], 3, sigma, n, 1)
    mean_one = adu.own_rate_draws([0.01], [100.0], 3, sigma, n, 1, mean_one=True)
    np.testing.assert_allclose(mean_one / median_one, np.exp(-(sigma**2) / 2))
    assert np.exp(-(sigma**2) / 2) == pytest.approx(0.5914, abs=1e-4)
    flat = adu.own_rate_draws([0.01], [100.0], 3, 0.0, n, 1)
    d = mean_one[:, 0] / flat[:, 0]
    assert d.mean() == pytest.approx(1.0, rel=0.02)
    assert np.median(d) == pytest.approx(np.exp(-(sigma**2) / 2), rel=0.02)
    # without drift the switch changes nothing
    np.testing.assert_allclose(adu.own_rate_draws([0.01], [100.0], 3, 0.0, 50, 2, mean_one=True),
                               adu.own_rate_draws([0.01], [100.0], 3, 0.0, 50, 2))  # fmt: skip


def test_own_rate_draws_take_one_row_per_draw():
    """Each draw's undercount-scaled observed rate (`observed_rate_draws`) sets that draw's counts."""
    obs = np.array([[0.0], [1.0]])
    out = adu.own_rate_draws(obs, [100.0], 3, 0.0, 2, 3)
    assert out.shape == (2, 1)
    assert out[1, 0] > out[0, 0]


def test_switch_off_is_the_mechanism_with_the_floor():
    """adu_own_rate_drift 0 gives the pre-D-091 engine exactly."""
    pl = _places(observed_rate=0.002, rule_class="partial", rule_age=5.0)
    off = adu.central_path(pl, params={"adu_own_rate_drift": 0})
    hm = off["mature_hazard"]
    floors = adu.pool_paths(pl["eligible_parcels"], hm, pl["observed_rate"],
                            adu.expected_rule_share(adu.with_rule_probs(pl, P), P), [5.0], P,
                            off["added"].shape[1], True, adu.baseline.window(0)[0])  # fmt: skip
    np.testing.assert_allclose(off["added"], floors.added)


def test_pool_paths_use_own_counts_for_the_no_reform_rate_by_hand():
    """No rule (c 0), h_m 0.01, floor 0.002: mechanism no-reform 0.002, Handbook 0.01, ratio 5.
    Own rate 0.003:
    year 1 no-reform 2000 × 0.003 = 6, Handbook 2000 × 0.015 = 30; year 2 on the shrunken pools."""
    paths = adu.pool_paths([2000.0], [0.01], [0.002], [0.0], [np.nan], P, 2, True, 0, [0.003])
    np.testing.assert_allclose(paths.current[0], [6.0, 1994 * 0.003])
    np.testing.assert_allclose(paths.handbook[0], [30.0, 1970 * 0.015])
    off = adu.pool_paths([2000.0], [0.01], [0.002], [0.0], [np.nan], P, 2, False, 0, [0.003])
    np.testing.assert_allclose(off.added, 0.0)


def test_lead_years_deplete_the_pool_at_the_own_rate():
    paths = adu.pool_paths([1000.0], [0.01], [0.002], [0.0], [np.nan], P, 1, True, 2, [0.1])
    assert paths.current[0, 0] == pytest.approx(1000 * 0.9 * 0.9 * 0.1)


def test_central_path_uses_the_persistence_mean():
    pl = _places(observed_rate=0.002)
    on = adu.central_path(pl, horizon=1)
    off = adu.central_path(pl, horizon=1, params={"adu_own_rate_drift": 0})
    own = (0.002 * 6000 + 0.5) / 6000
    assert on["current"][0, 0] > off["current"][0, 0]  # own mean sits above the floor by 0.5 / E
    assert on["current"][0, 0] == pytest.approx(off["current"][0, 0] * own / 0.002, rel=0.01)


def test_run_marks_the_no_reform_basis():
    pl = _places(geoid=["A", "B"], observed_rate=[0.002, np.nan])
    _, totals = adu.run(pl, 2025, draws=50)
    assert list(totals["no_reform_basis"]) == ["own ADU counts with drift", "model"]
    lo, hi = totals["current_rules_adus_p10"][0], totals["current_rules_adus_p90"][0]
    assert hi / lo > 3  # σ 1.025 over one place: P90 / P10 of exp(σ z) alone is exp(2.56 σ) ≈ 14
