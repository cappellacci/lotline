"""D-089: state profiles, evidence flags, the town prior and statewide totals (synthetic data only)."""

import numpy as np
import pandas as pd
import pytest

from lotline.model.scenarios import adu
from lotline.validation import adu_profiles as pr


def test_weighted_median_hand_worked():
    assert pr.weighted_median([1, 2, 3], [1, 1, 3]) == 3
    assert pr.weighted_median([1, 2, 3], [3, 1, 1]) == 1
    assert pr.weighted_median([1, 2, 3, 4], [1, 1, 1, 1]) == 2
    assert pr.weighted_median([1, np.nan, 3], [1, 5, 2]) == 3
    assert np.isnan(pr.weighted_median([np.nan], [1]))


def test_profile_hand_worked():
    df = pd.DataFrame(
        {
            "state": ["X"] * 3,
            "type": ["core", "suburb", "suburb"],
            "pop": [100, 50, 30],
            "lots": [60.0, 30.0, 10.0],
            "home_value": [300, 200, 100],
            "rent": [1, 2, 3],
            "owner": [0.4, 0.7, 0.9],
        }
    )
    p = pr.profile(df).set_index("type")
    assert p.loc["core", "lot_share"] == pytest.approx(0.6)
    assert p.loc["suburb", "lot_share"] == pytest.approx(0.4)
    assert p.loc["suburb", "jurisdictions"] == 2 and p.loc["suburb", "pop"] == 80
    assert p.loc["suburb", "home_value"] == 200  # lot weights 30 vs 10


def test_outside_evidence_hand_worked():
    ranges = {"suburb": {"v": (10.0, 20.0)}}
    df = pd.DataFrame({"type": ["suburb", "suburb", "suburb", "town"], "v": [15, 25, np.nan, 15]})
    f = pr.outside_evidence(df, ranges, ["v"])
    assert list(f["beyond_range"]) == [False, True, False, False]
    assert list(f["is_town"]) == [False, False, False, True]
    assert list(f["outside"]) == [False, True, False, True]


def test_fit_ranges_quantiles():
    fit = pd.DataFrame({"type": ["suburb"] * 21, "v": np.arange(21.0)})
    assert pr.fit_ranges(fit, ["v"])["suburb"]["v"] == pytest.approx((1.0, 19.0))


def test_label_and_town_sd_hand_worked():
    assert pr.label(0.3) and not pr.label(0.25)
    assert pr.town_sd(1.199) == pytest.approx(0.729, abs=5e-4)
    assert pr.town_sd(-1.199) == pytest.approx(0.729, abs=5e-4)


def test_current_totals_matches_pool_paths():
    params = {"adu_ramp_share": 1.0}
    e = np.array([1000.0, 500.0, 200.0])
    c = np.array([1.0, 0.4, 0.0])
    floor = np.array([np.nan, 0.01, 0.002])
    age = np.array([3.0, np.nan, np.nan])
    hm = np.array([[0.002, 0.003, 0.004], [0.02, 0.01, 0.5]])
    got = pr.current_totals(e, hm, c, floor, age, params, horizon=5, lead=1)
    for d in range(2):
        want = adu.pool_paths(e, hm[d], floor, c, age, params, 5, enabled=False, lead=1).current.sum()
        assert got[d] == pytest.approx(want)
