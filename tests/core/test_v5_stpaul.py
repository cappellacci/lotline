"""V5 St. Paul (D-098): hand-worked checks on synthetic inputs."""

from types import SimpleNamespace as NS

import numpy as np
import pandas as pd
import pytest

from lotline.validation import v5_stpaul as v


def _inp(eligible=10_000, B_years=(9.0, 4.0, 6.0), f=0.7, gap=1.0):
    return v.Inputs(eligible=eligible, dose_pre=0.0, dose_post=gap, rent=1300.0, cost_index=1.0, pcr=0.85,
                    f_ratio=f, baseline_buildings=dict(zip((2021, 2022, 2023), B_years, strict=True)),
                    baseline_homes={2021: 23.0, 2022: 10.0, 2023: 12.0})  # fmt: skip


def _params(theta=0.001, phi=1e9, half=0.5):
    fixed = lambda x: NS(value=x, low=x, high=x)  # noqa: E731
    return {"mm_mature_hazard_ref": fixed(theta), "mm_place_effect_variance": fixed(1e-9),
            "mm_units_per_project": fixed(2.0), "mm_year_spread_phi": fixed(phi),
            "mm_ramp_half_years": fixed(half), "mm_ramp_slope_years": fixed(0.75)}  # fmt: skip


def test_inputs_by_hand():
    i = _inp()
    # B = (9 + 4 + 6) / 3 = 6.333; homes per building = 45 / 19 = 2.368
    assert i.B == pytest.approx(19 / 3)
    assert i.homes_per_baseline_building == pytest.approx(45 / 19)
    assert i.gap == 1.0


def test_baseline_refuses_window_years():
    bps = pd.DataFrame({"geoid": ["2758000"] * 2, "year": [2023, 2024], "bldgs_2": [1, 1],
                        "bldgs_3_4": [0, 0], "units_2": [2, 2], "units_3_4": [0, 0]})  # fmt: skip
    with pytest.raises(ValueError):
        v.baseline(bps, years=(2022, 2023, 2024))


def test_ramp_shape_c4_by_hand():
    # half 4.0, slope 0.75, ages 0.5, 1.5, 2.5: 0.0093, 0.0344, 0.1192
    assert v.ramp_shape(4.0, 0.75) == pytest.approx([0.0093, 0.0344, 0.1192], abs=1e-4)


def test_draws_mean_by_hand():
    # half 0.5: shape 0.5, 0.7914, 0.9350. Added mean per year = 0.001 × 10,000 × 1 × 0.7 × shape
    # = 3.5, 5.540, 6.545; plus B 6.333 each year
    d = v.draws(_inp(), 200_000, 1, _params())
    assert d["added"].mean(0) == pytest.approx([3.5, 5.540, 6.545], rel=0.01)
    assert d["baseline"].mean(0) == pytest.approx([19 / 3] * 3, rel=0.01)
    assert np.array_equal(d["buildings"], d["baseline"] + d["added"])


def test_draws_negative_binomial_variance_by_hand():
    # no reform (gap 0): buildings ~ NB(mean 6.333, φ 2): variance 6.333 + 6.333² / 2 = 26.39
    d = v.draws(_inp(gap=0.0), 300_000, 2, _params(phi=2.0))
    y = d["buildings"][:, 0]
    assert y.mean() == pytest.approx(19 / 3, rel=0.01)
    assert y.var() == pytest.approx(19 / 3 + (19 / 3) ** 2 / 2, rel=0.03)


def test_summarize_has_pass_and_full_spans():
    d = {"buildings": np.ones((10, 3))}
    s = v.summarize(d)["buildings"]
    assert s["2024-2025"]["p50"] == 2.0 and s["2024-2026"]["p50"] == 3.0


def test_write_freeze_refuses_overwrite(tmp_path):
    p = v.write_freeze({"x": 1}, tmp_path)
    assert p.exists()
    with pytest.raises(FileExistsError):
        v.write_freeze({"x": 2}, tmp_path)
