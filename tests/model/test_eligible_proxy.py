"""D-056: the ACS-fallback proxy test and its per-draw scale step, against hand-worked examples."""

import math

import numpy as np
import pandas as pd
import pytest

from lotline.config import load_params
from lotline.model.eligible_proxy import ACS_SOURCE as ACS
from lotline.model.eligible_proxy import multipliers, proxy_states, proxy_test
from lotline.model.scenarios import adu


def _totals(ratios, acs=(1000, 2000, 4000)):
    return pd.DataFrame(
        {
            "state": ["AA", "BB", "CC"],
            "parcels": [r * a for r, a in zip(ratios, acs, strict=True)],
            "acs_homes": list(acs),
        }
    )


def test_three_states_failing_by_hand():
    # r = (0.5, 1, 2): log r = (-ln2, 0, ln2) -> k = 1, sigma = ln 2 (sample sd: sqrt((ln2^2 + ln2^2) / 2))
    res = proxy_test(_totals([0.5, 1.0, 2.0]))
    assert res.k == pytest.approx(1.0)
    assert res.sigma == pytest.approx(math.log(2))
    t = res.table.set_index("state")
    assert t.loc["AA", "k_loo"] == pytest.approx(math.sqrt(2))  # sqrt(1 * 2)
    assert t.loc["AA", "held_out"] == pytest.approx(0.5 / math.sqrt(2))  # 0.354
    assert t.loc["BB", "held_out"] == pytest.approx(1.0)  # 1 / sqrt(0.5 * 2)
    assert t.loc["CC", "held_out"] == pytest.approx(2.0 / math.sqrt(0.5))  # 2.83
    assert list(t["in_band"]) == [False, True, False]
    assert not res.passed


def test_three_states_passing_by_hand():
    # r = (0.8, 1, 1.25): k = 1; q = 0.8/sqrt(1.25) = 0.716, 1, 1.25/sqrt(0.8) = 1.398 -> all in [0.7, 1.4]
    res = proxy_test(_totals([0.8, 1.0, 1.25]))
    assert res.k == pytest.approx(1.0)
    assert res.sigma == pytest.approx(math.log(1.25))
    q = res.table["held_out"].to_numpy()
    assert q == pytest.approx([0.8 / math.sqrt(1.25), 1.0, 1.25 / math.sqrt(0.8)])
    assert res.passed


def test_k_is_the_geometric_mean_and_level_free():
    # a common factor in every ratio moves k but not q_s or sigma (a systematic ratio is what k absorbs)
    base = proxy_test(_totals([0.8, 1.0, 1.25]))
    shifted = proxy_test(_totals([0.4, 0.5, 0.625]))
    assert shifted.k == pytest.approx(0.5)
    assert shifted.sigma == pytest.approx(base.sigma)
    assert shifted.table["held_out"].to_numpy() == pytest.approx(base.table["held_out"].to_numpy())
    assert shifted.passed


def test_needs_three_positive_states():
    with pytest.raises(ValueError):
        proxy_test(_totals([1.0, 1.0, 1.0]).head(2))
    bad = _totals([1.0, 1.0, 1.0])
    bad.loc[0, "acs_homes"] = 0
    with pytest.raises(ValueError):
        proxy_test(bad)


def _rows():
    return pd.DataFrame(
        {
            "state": ["AA", "AA", "BB", "BB", "CC"],
            "geoid": ["1", "2", "3", "4", "5"],
            "eligible_parcels": [100.0, 300.0, 50.0, 10.0, 70.0],
            # AA: parcel-based; BB and CC: all ACS fallback (tier 3)
            "denominator_source": ["parcels", "parcels_scaled_acs", ACS, ACS, ACS],
        }
    )


def test_only_states_with_no_parcel_denominator_are_proxy_states():
    rows = _rows()
    rows.loc[4, "state"] = "AA"  # an ACS-fallback place inside a parcel-based state
    assert proxy_states(rows) == ["BB"]


def test_parcel_based_state_is_untouched():
    rows = _rows()
    rows.loc[4, "state"] = "AA"
    m = multipliers(rows, 50, np.random.default_rng(0), k=0.6, sigma=0.2)
    assert m.shape == (50, 5)
    assert (m[:, [0, 1, 4]] == 1.0).all()  # AA, including its own ACS-fallback place


def test_fallback_state_scaled_once_per_draw():
    m = multipliers(_rows(), 4000, np.random.default_rng(1), k=0.6, sigma=0.2)
    assert (m[:, 2] == m[:, 3]).all()  # BB's places share one scale in a draw
    assert np.exp(np.log(m[:, 2]).mean()) == pytest.approx(0.6, rel=0.02)  # median scale k
    assert np.log(m[:, 2]).std(ddof=1) == pytest.approx(0.2, rel=0.05)  # log-sd sigma
    assert not np.allclose(m[:, 2], m[:, 4])  # CC (all fallback too) gets its own z


def test_zero_sigma_is_a_fixed_scale_and_config_defaults_load():
    m = multipliers(_rows(), 3, np.random.default_rng(2), k=0.6, sigma=0.0)
    assert m[:, 2] == pytest.approx([0.6] * 3)
    p = load_params("eligible_proxy")
    assert p["eligible_proxy_scale"].low < p["eligible_proxy_scale"].value < p["eligible_proxy_scale"].high
    assert p["eligible_proxy_scale"].high == pytest.approx(
        p["eligible_proxy_scale"].value * math.exp(p["eligible_proxy_sd"].value), abs=1e-3
    )


def _adu_places():
    p = adu.central_params()
    return pd.DataFrame(
        {
            "geoid": ["1", "2", "3"],
            "state": ["MN", "MN", "WY"],
            "eligible_parcels": [2000.0, 500.0, 3000.0],
            "denominator_source": ["parcels", ACS, ACS],
            "rent": [1100.0] * 3,
            "home_value": [p["adu_ref_home_value_usd"] / 2] * 3,
            "mortgage_rate": [np.nan] * 3,
            "rule_class": ["none"] * 3,
            "rule_age": [np.nan] * 3,
            "observed_rate": [np.nan] * 3,
        }
    )


def test_adu_run_leaves_parcel_based_state_untouched():
    places = _adu_places()
    _, off = adu.run(places, 2025, draws=200)
    _, on = adu.run(places, 2025, draws=200, eligible_proxy=True)
    cols = [c for c in off.columns if c.startswith(("additional_homes", "adu_permits_added"))]
    mn = off["state"] == "MN"
    pd.testing.assert_frame_equal(off.loc[mn, cols], on.loc[mn, cols])  # bit-identical, incl. its ACS place
    assert not np.allclose(off.loc[~mn, cols].to_numpy(), on.loc[~mn, cols].to_numpy())  # WY is drawn
