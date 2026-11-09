"""V5 Charlotte blind forecast (analysis plan D-071): the pieces do what the method says, on hand-worked and
synthetic inputs. No real data."""

import numpy as np
import pandas as pd
import pytest

from lotline.config import Parameter, load_params
from lotline.validation import v5


def _p(value, low=None, high=None):
    return Parameter(value=value, low=value if low is None else low, high=value if high is None else high,
                     unit="x", source="test")  # fmt: skip


def _inputs(**kw):
    base = dict(
        n1_lots=10_000, share_low=0.8, share_value=0.8, share_high=0.8, dose_pre=0.0, dose_udo=0.5,
        rent=1500.0, cost_index=1.0, pcr=1.0, f_ratio=1.0,
        baseline_buildings={2020: 30.0, 2021: 20.0, 2022: 40.0},
        baseline_homes={2020: 60.0, 2021: 50.0, 2022: 80.0},
    )  # fmt: skip
    return v5.Inputs(**(base | kw))


def _params(theta=0.001, alpha=1e-9, units=2.0, half=0.5, slope=0.75):
    return {
        "mm_mature_hazard_ref": _p(theta),
        "mm_place_effect_variance": _p(alpha),
        "mm_units_per_project": _p(units),
        "mm_ramp_half_years": _p(half),
        "mm_ramp_slope_years": _p(slope),
    }


def test_eligible_share_sums_each_end_by_hand():
    sp = load_params("v5_charlotte")
    low, value, high = v5.eligible_share(sp["n1_sf_share"], sp["n1_vacant_share"])
    assert (low, value, high) == pytest.approx((0.582, 0.851, 0.961))


def test_baseline_is_buildings_and_homes_in_2_4_unit_buildings():
    bps = pd.DataFrame(
        {
            "geoid": ["37119"] * 3 + ["3700000"],
            "year": [2020, 2021, 2022, 2021],
            "bldgs_2": [10, 5, 40, 99],
            "bldgs_3_4": [1, 2, 0, 99],
            "units_2": [20, 10, 80, 99],
            "units_3_4": [4, 8, 0, 99],
        }
    )
    bld, hom = v5.baseline(bps)
    assert bld == {2020: 11.0, 2021: 7.0, 2022: 40.0}
    assert hom == {2020: 24.0, 2021: 18.0, 2022: 80.0}
    with pytest.raises(ValueError, match="no rows"):
        v5.baseline(bps[bps["year"] != 2021])
    with pytest.raises(ValueError, match="end by 2022"):
        v5.baseline(bps, years=(2021, 2022, 2023))


def test_inputs_gap_baseline_and_homes_per_building_by_hand():
    inp = _inputs(dose_pre=0.1, dose_udo=0.5)
    assert inp.gap == pytest.approx(0.4)
    assert inp.B == pytest.approx(30.0)  # (30 + 20 + 40) / 3
    assert inp.homes_per_baseline_building == pytest.approx(190 / 90)
    assert _inputs(dose_pre=0.6, dose_udo=0.5).gap == 0.0  # a weaker rule adds nothing


def test_ramp_shape_by_hand():
    # half 0.5, slope 0.75, ages 0.5, 1.5, 2.5:
    # 1/(1+e^0) = 0.5, 1/(1+e^-1.333) = 0.7914, 1/(1+e^-2.667) = 0.9350
    np.testing.assert_allclose(v5.ramp_shape(0.5, 0.75), [0.5, 0.79139, 0.93504], atol=1e-4)


def test_draws_mean_is_baseline_plus_theta_e_gap_f_ramp():
    inp = _inputs()
    d = v5.draws(inp, 40_000, seed=1, params=_params())
    # added per year = 0.001 × 10,000 × 0.8 × 0.5 × 1 × ramp = 4 × (0.5, 0.7914, 0.9350)
    expected = v5.expected_added(inp, 0.001, 0.5, 0.75)
    np.testing.assert_allclose(expected, 4 * v5.ramp_shape(0.5, 0.75))
    np.testing.assert_allclose(d["added"].mean(axis=0), expected, rtol=0.03)
    np.testing.assert_allclose(d["baseline"].mean(axis=0), 30.0, rtol=0.02)
    np.testing.assert_array_equal(d["buildings"], d["baseline"] + d["added"])
    np.testing.assert_allclose(d["homes"], d["baseline"] * 190 / 90 + d["added"] * 2.0)


def test_no_gap_means_baseline_only():
    d = v5.draws(_inputs(dose_udo=0.0), 2_000, seed=2, params=_params())
    assert (d["added"] == 0).all()


def test_summaries_sum_draw_by_draw():
    a = np.array([[1.0, 2.0, 3.0], [10.0, 0.0, 0.0]])
    s = v5.summarize({"buildings": a})["buildings"]
    assert s["2023-2025"]["mean"] == pytest.approx(8.0)  # (6 + 10) / 2
    assert s["2024"]["p50"] == pytest.approx(1.0)


def test_charlotte_dose_is_zero_before_the_udo_and_the_coded_rule_after():
    from lotline.model import estimate_mm as mm
    from lotline.model import rule_tags
    from lotline.model.scenarios import adu

    blanks = (0.8, 0.5)  # P(by right) for a blank field, units grade for a blank cap
    pre, post = v5.charlotte_dose(blanks)
    assert pre == 0.0
    permit = load_params("mm")["mm_dose_grade_permit"].value
    row = rule_tags.apply(adu.load_reforms("NC")).set_index("reform_id").loc[v5.UDO_REFORM]
    assert pd.isna(row["by_right"]) and row["unit_cap"] == 3  # cap 3 -> grade 2/3; blank by_right -> 0.8
    assert post == pytest.approx(2 / 3 * (0.8 + 0.2 * permit))
    assert mm.units_grade(3) == pytest.approx(2 / 3)


def test_freeze_is_written_once(tmp_path):
    path = v5.write_freeze({"test_id": v5.TEST_ID}, tmp_path)
    assert path == tmp_path / "results" / "frozen" / "V5-NC-CHARLOTTE.json"
    with pytest.raises(FileExistsError):
        v5.write_freeze({"test_id": v5.TEST_ID}, tmp_path)


def test_config_files_named_in_the_freeze_exist():
    from lotline.validation.holdout import REPO_ROOT

    for p in v5.CONFIG_FILES:
        assert (REPO_ROOT / p).exists(), p


def test_verdict_by_hand():
    assert v5.verdict(100, 80, 100, 170) == "useful"
    assert v5.verdict(79, 80, 100, 170) == "missed (over)"
    assert v5.verdict(171, 80, 100, 170) == "missed (under)"
    assert v5.verdict(30, 10, 14, 40) == "inside only"  # 30 / 14 > 2


def test_score_pass_rule_and_percentile():
    draws = np.arange(1, 101, dtype=float)  # P10 10.9, P90 90.1
    s = v5.score(draws, 50.0, bench=np.full(100, 50.0))
    assert s["pass"] and s["percentile"] == pytest.approx(49.5)  # 49 below, 1 tie
    assert s["crps_no_reform"] == 0.0
    assert not v5.score(draws, 95.0)["pass"]


def test_observed_needs_every_window_year():
    bps = pd.DataFrame({"geoid": ["37119"] * 2, "year": [2023, 2024], "bldgs_2": [5, 6], "bldgs_3_4": [1, 0],
                        "units_2": [10, 12], "units_3_4": [3, 0]})  # fmt: skip
    with pytest.raises(ValueError, match="2025"):
        v5.observed(bps)
    bld, hom = v5.observed(bps, years=(2023, 2024))
    assert bld == {2023: 6.0, 2024: 6.0} and hom == {2023: 13.0, 2024: 12.0}
