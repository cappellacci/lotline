"""V9 Oregon transfer prediction (analysis plan D-046): the pieces do what the method says, on hand-worked and
synthetic inputs. No real data."""

import numpy as np
import pytest

from lotline.model.scenarios import adu
from lotline.validation import v9

HB, PARTIAL, BLANK = v9.CLASS_CODE["handbook"], v9.CLASS_CODE["partial"], v9.CLASS_CODE["blank"]


def _adu_inputs(cls, age, q, cov, eligible=(1000.0,), years=(2018, 2019)):
    p = adu.central_params()
    n_p, n_y = len(eligible), len(years)
    shape = (n_p, n_y, 1)
    return v9.AduInputs(
        geoids=[f"41{i:05d}" for i in range(n_p)],
        names=[f"place {i}" for i in range(n_p)],
        years=np.array(years),
        eligible=np.array(eligible, dtype=float),
        rent=np.full((n_p, n_y), p["adu_ref_rent_usd"]),
        value=np.full((n_p, n_y), p["adu_ref_home_value_usd"]),
        rate=np.full(n_y, p["adu_ref_mortgage_rate"]),
        cls=np.full(shape, cls, dtype=int),
        age=np.full(shape, age, dtype=float),
        q=np.full(shape, q, dtype=float),
        cov=np.full(shape, cov, dtype=float),
    )


def test_rule_factor_by_hand():
    # half 2, slope 0.75: ramp(2) = 0.5. Handbook, full coverage -> 0.5; partial share 0.3 -> 0.15;
    # coverage 0.75 scales it; no rule (coverage 0) -> 0
    flag = np.array([False])
    assert v9.rule_factor(_adu_inputs(HB, 2.0, 0, 1.0), 0.3, flag, 2.0, 0.75)[0, 0] == pytest.approx(0.5)
    assert v9.rule_factor(_adu_inputs(PARTIAL, 2.0, 0, 1.0), 0.3, flag, 2.0, 0.75)[0, 0] == pytest.approx(
        0.15
    )
    assert v9.rule_factor(_adu_inputs(HB, 2.0, 0, 0.75), 0.3, flag, 2.0, 0.75)[0, 0] == pytest.approx(0.375)
    assert v9.rule_factor(_adu_inputs(HB, 2.0, 0, 0.0), 0.3, flag, 2.0, 0.75)[0, 0] == 0.0


def test_blank_rule_is_partial_only_when_the_draw_says_so():
    inp = _adu_inputs(BLANK, 2.0, 0.6, 1.0)
    assert v9.rule_factor(inp, 0.3, np.array([False]), 2.0, 0.75)[0, 0] == pytest.approx(0.5)
    assert v9.rule_factor(inp, 0.3, np.array([True]), 2.0, 0.75)[0, 0] == pytest.approx(0.15)


def test_adu_draws_mean_matches_the_hand_formula_at_the_reference_place():
    # at the reference rent, value and rate, h_m = θ; α = 0 and no widening (distance 0): mean per year
    # = parcels × θ × ramp × c, with the pool shrinking by the expected count
    theta = 0.002
    inp = _adu_inputs(HB, 2.0, 0, 1.0, eligible=(10_000.0,))
    fixed = {
        "adu_mature_hazard_ref": theta,
        "adu_place_effect_variance": 0.0,
        "adu_ramp_half_years": 2.0,
        "adu_ramp_slope_years": 0.75,
    }
    d = v9.adu_draws(inp, draws=4000, seed=1, params=fixed)
    first = 10_000 * theta * 0.5
    second = (10_000 - first) * theta * 0.5
    assert d[:, 0, 0].mean() == pytest.approx(first, rel=0.03)
    assert d[:, 0, 1].mean() == pytest.approx(second, rel=0.03)


def test_no_rule_or_no_parcels_means_no_adus():
    fixed = {"adu_place_effect_variance": 0.0}
    assert v9.adu_draws(_adu_inputs(HB, 2.0, 0, 0.0), 50, 1, fixed).sum() == 0
    assert v9.adu_draws(_adu_inputs(HB, 2.0, 0, 1.0, eligible=(0.0,)), 50, 1, fixed).sum() == 0


def _mm_inputs():
    return v9.MmInputs(
        geoids=["4100001", "4100002"],
        names=["a", "b"],
        years=np.array([2020, 2021, 2022]),
        T=np.array([2021.0, 2025.0]),
        B=np.array([3.0, 1.0]),
        kr=np.array([[100.0, 100.0, 100.0], [0.0, 0.0, 0.0]]),
    )


def test_mm_k_is_zero_before_adoption_and_ramps_after():
    k = v9.mm_k(_mm_inputs(), 2.0, 0.75)
    from lotline.model.hazard import ramp

    assert k[0, 0] == 0.0  # 2020, before T = 2021
    assert k[0, 1] == pytest.approx(100 * float(ramp(0.5, 2.0, 0.75)))
    assert k[0, 2] == pytest.approx(100 * float(ramp(1.5, 2.0, 0.75)))
    assert (k[1] == 0).all()


def test_mm_draws_mean_is_baseline_plus_theta_k():
    inp = _mm_inputs()
    d = v9.mm_draws(inp, draws=20_000, seed=3, params={"theta": 0.01, "alpha": 0.0})
    from lotline.config import load_params

    sp = load_params("mm_hazard")
    k = v9.mm_k(inp, sp["mm_ramp_half_years"].value, sp["mm_ramp_slope_years"].value)
    np.testing.assert_allclose(d.mean(axis=0), inp.B[:, None] + 0.01 * k, rtol=0.05)


def test_summaries_sum_draw_by_draw():
    draws = np.array([[1.0, 2.0, 3.0], [10.0, 0.0, 0.0]])  # 2 draws, years 2021-2023
    s = v9.summarize(draws, np.array([2021, 2022, 2023]), "x")["by_period"]
    assert s["2021-2023"]["mean"] == pytest.approx(8.0)  # (6 + 10) / 2
    assert s["2021-2022"]["mean"] == pytest.approx(6.5)  # subtotal to SUBTOTAL_LAST: (3 + 10) / 2
    assert s["2022"]["p50"] == pytest.approx(1.0)


def test_freeze_is_written_once(tmp_path):
    payload = {"test_id": v9.TEST_ID}
    path = v9.write_freeze(payload, tmp_path)
    assert path == tmp_path / "results" / "frozen" / "V9-OR-TRANSFER.json"
    with pytest.raises(FileExistsError):
        v9.write_freeze(payload, tmp_path)
