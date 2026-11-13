"""D-082 §7 pass rules (`lotline.model.mm_tests`), each against a hand-worked example."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from lotline.model import mm_tests as mt


def test_params_are_the_d082_section_7_values():
    p = {k: mt._p(k) for k in ("mm_test_a_coverage", "mm_test_a_ratio", "mm_test_c_coverage",
                               "mm_loso_min_places", "mm_placebo_shift_years", "mm_place_coverage_low",
                               "mm_place_coverage_high", "mm_test_c_first_year")}  # fmt: skip
    assert p == {"mm_test_a_coverage": 0.6, "mm_test_a_ratio": 2.0, "mm_test_c_coverage": 0.7,
                 "mm_loso_min_places": 3, "mm_placebo_shift_years": 3, "mm_place_coverage_low": 0.6,
                 "mm_place_coverage_high": 0.95, "mm_test_c_first_year": 2021}  # fmt: skip


def test_a_hand_worked():
    rows = pd.DataFrame(
        {
            "observed": [10, 3, 40, 0, 6],
            "p10": [5, 4, 10, 0, 2],
            "p50": [8, 9, 20, 1, 6],
            "p90": [12, 15, 30, 3, 9],
        }
    )
    # inside: 10 in 5-12 yes; 3 in 4-15 no; 40 in 10-30 no; 0 in 0-3 yes; 6 in 2-9 yes -> 3/5 = 0.6 (passes,
    # inclusive). Ratios: 1.25, 0.333, 2.0, 0.0, 1.0 -> median 1.0, inside [0.5, 2].
    r = mt.test_a(rows)
    assert r["share_inside"] == pytest.approx(0.6) and r["median_ratio"] == pytest.approx(1.0) and r["pass"]
    # Same coverage but every observed far above P50: median ratio 3 -> fails.
    far = rows.assign(observed=rows["p50"] * 3, p90=rows["p50"] * 4)
    assert not mt.test_a(far)["pass"]


def test_ratio_to_median_zero_cases():
    assert mt.ratio_to_median(0, 0) == 1.0 and mt.ratio_to_median(2, 0) == float("inf")


def test_c_hand_worked():
    rows = pd.DataFrame({"observed": [1, 2, 3, 9], "p10": [0, 0, 1, 0], "p90": [2, 3, 4, 5]})
    # 3 of 4 inside = 0.75 >= 0.7; but state TX's total 30 is outside 10-25 -> fails.
    states = pd.DataFrame({"state": ["MN", "TX"], "observed": [6, 30], "p10": [2, 10], "p90": [9, 25]})
    r = mt.test_c(rows, states)
    assert r["share_inside"] == pytest.approx(0.75) and r["states_missed"] == ["TX"] and not r["pass"]
    ok = states.assign(observed=[6, 20])
    assert mt.test_c(rows, ok)["pass"]


def test_loso_only_states_with_three_fit_places_count():
    states = pd.DataFrame(
        {
            "state": ["OR", "MN", "TX"],
            "fit_places": [80, 1, 3],
            "observed": [500, 100, 50],
            "p10": [300, 10, 10],
            "p50": [450, 20, 40],
            "p90": [700, 40, 90],
        }
    )
    # OR useful; MN missed but only 1 fit place; TX useful -> pass.
    r = mt.loso(states)
    assert r["verdicts"] == {"OR": "useful", "MN": "missed", "TX": "useful"} and r["pass"]
    # TX observed 200 above P90 90 -> missed with 3 fit places -> fail.
    assert mt.loso(states.assign(observed=[500, 100, 200]))["failed_states"] == ["TX"]


def test_placebo():
    assert mt.placebo(0.05, 0.09)["pass"] and not mt.placebo(0.10, 0.09)["pass"]


def test_randomized_pit_between_the_two_cdf_values():
    rng = np.random.default_rng(1)
    u = [mt.randomized_pit(np.array([0, 1, 1, 2]), 1, rng) for _ in range(200)]
    assert min(u) >= 0.25 and max(u) <= 0.75
    # observed above every draw -> F(y-1) = F(y) = 1
    assert mt.randomized_pit(np.array([0, 1]), 5, rng) == 1.0


def test_place_coverage_flags_outside_target():
    # PITs: 0.05 out, 0.5 in, 0.95 out, 0.3 in -> 0.5 coverage < 0.6 -> flagged
    r = mt.place_coverage([0.05, 0.5, 0.95, 0.3])
    assert r["coverage"] == pytest.approx(0.5) and r["flag"]
    assert not mt.place_coverage([0.5, 0.3, 0.2, 0.05])["flag"]  # 0.75
