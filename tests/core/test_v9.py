"""V9 Oregon transfer prediction (analysis plan D-051): the pieces do what the method says, on hand-worked and
synthetic inputs. No real data."""

import numpy as np
import pytest

from lotline.model.scenarios import adu
from lotline.validation import v9

HB, PARTIAL, BLANK = v9.CLASS_CODE["handbook"], v9.CLASS_CODE["partial"], v9.CLASS_CODE["blank"]
NO_SPREAD = {"adu_state_tau_prob__0": 1.0}  # τ = 0 in every draw: no state multiplier


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


OLD_RAMP = {"adu_ramp_half_years": 2.0, "adu_ramp_slope_years": 0.75}  # hazard.PRE_D048_RAMP


def test_rule_factor_with_no_ramp_d048():
    # D-048: ramp 1, so a Handbook rule at full coverage gives 1 at any age; partial share 0.3 -> 0.3
    flag, p = np.array([False]), {"adu_ramp_share": 1.0}
    assert v9.rule_factor(_adu_inputs(HB, 0.5, 0, 1.0), 0.3, flag, p)[0, 0] == pytest.approx(1.0)
    assert v9.rule_factor(_adu_inputs(PARTIAL, 0.5, 0, 1.0), 0.3, flag, p)[0, 0] == pytest.approx(0.3)


def test_rule_factor_by_hand():
    # pre-D-048 ramp, half 2, slope 0.75: ramp(2) = 0.5. Handbook, full coverage -> 0.5; partial share 0.3 ->
    # 0.15;
    # coverage 0.75 scales it; no rule (coverage 0) -> 0
    flag = np.array([False])
    assert v9.rule_factor(_adu_inputs(HB, 2.0, 0, 1.0), 0.3, flag, OLD_RAMP)[0, 0] == pytest.approx(0.5)
    assert v9.rule_factor(_adu_inputs(PARTIAL, 2.0, 0, 1.0), 0.3, flag, OLD_RAMP)[0, 0] == pytest.approx(0.15)
    assert v9.rule_factor(_adu_inputs(HB, 2.0, 0, 0.75), 0.3, flag, OLD_RAMP)[0, 0] == pytest.approx(0.375)
    assert v9.rule_factor(_adu_inputs(HB, 2.0, 0, 0.0), 0.3, flag, OLD_RAMP)[0, 0] == 0.0


def test_blank_rule_is_partial_only_when_the_draw_says_so():
    inp = _adu_inputs(BLANK, 2.0, 0.6, 1.0)
    assert v9.rule_factor(inp, 0.3, np.array([False]), OLD_RAMP)[0, 0] == pytest.approx(0.5)
    assert v9.rule_factor(inp, 0.3, np.array([True]), OLD_RAMP)[0, 0] == pytest.approx(0.15)


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
    d = v9.adu_draws(inp, draws=4000, seed=1, params=fixed, states_spec=NO_SPREAD)
    first = 10_000 * theta * 0.5
    second = (10_000 - first) * theta * 0.5
    assert d[:, 0, 0].mean() == pytest.approx(first, rel=0.03)
    assert d[:, 0, 1].mean() == pytest.approx(second, rel=0.03)


def test_no_rule_or_no_parcels_means_no_adus():
    fixed = {"adu_place_effect_variance": 0.0}
    assert v9.adu_draws(_adu_inputs(HB, 2.0, 0, 0.0), 50, 1, fixed, states_spec=NO_SPREAD).sum() == 0
    assert (
        v9.adu_draws(_adu_inputs(HB, 2.0, 0, 1.0, eligible=(0.0,)), 50, 1, fixed, states_spec=NO_SPREAD).sum()
        == 0
    )


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


# ---- own-history variant (D-052) ------------------------------------------------------------------------


def test_posterior_u_by_hand():
    # α = 0.5: prior Gamma(shape 2, rate 2). Counts 10 + 20 (one year unpublished) against 4 + 6 expected:
    # posterior Gamma(shape 32, rate 12), mean 32/12, variance 32/144
    rng = np.random.default_rng(0)
    obs = np.array([[10.0, np.nan, 20.0]])
    exp = np.array([[4.0, 99.0, 6.0]])  # the unpublished year's expectation is ignored
    u = np.array([v9.posterior_u(0.5, obs, exp, rng)[0] for _ in range(20_000)])
    assert u.mean() == pytest.approx(32 / 12, rel=0.02)
    assert u.var() == pytest.approx(32 / 144, rel=0.06)
    assert (v9.posterior_u(0.0, obs, exp, rng) == 1.0).all()


def _history(counts, years=(2014, 2015, 2016, 2017), eligible=10_000.0):
    inp = _adu_inputs(HB, 2.0, 0, 1.0, eligible=(eligible,), years=years)
    return v9.AduHistory(
        inputs=inp,
        eligible=np.full((1, len(years)), eligible),
        counts=np.array([counts], dtype=float),
    )


def test_history_pulls_the_prediction_toward_the_place():
    # reference place, θ = 0.002, ramp 0.5: 10 expected permits a year at u = 1. Four years of 20 published:
    # Y = 80, M = 40, α = 0.5 -> E[u | history] = (2 + 80) / (2 + 40) = 1.952, so 2018's mean is 19.5,
    # against 10 for the transfer variant
    fixed = {
        "adu_mature_hazard_ref": 0.002,
        "adu_place_effect_variance": 0.5,
        "adu_ramp_half_years": 2.0,
        "adu_ramp_slope_years": 0.75,
    }
    inp = _adu_inputs(HB, 2.0, 0, 1.0, eligible=(10_000.0,))
    plain = v9.adu_draws(inp, 6000, 3, fixed, states_spec=NO_SPREAD)
    hist = v9.adu_draws(inp, 6000, 3, fixed, history=_history([20, 20, 20, 20]), states_spec=NO_SPREAD)
    assert plain[:, 0, 0].mean() == pytest.approx(10.0, rel=0.05)
    assert hist[:, 0, 0].mean() == pytest.approx(10.0 * 82 / 42, rel=0.04)
    # and the history narrows the range: the prior's u has variance 0.5, the posterior's 82/42² = 0.046
    assert np.percentile(hist[:, 0, 0], 90) - np.percentile(hist[:, 0, 0], 10) < np.percentile(
        plain[:, 0, 0], 90
    ) - np.percentile(plain[:, 0, 0], 10)


def test_zero_history_pulls_down_and_missing_history_changes_nothing():
    fixed = {"adu_mature_hazard_ref": 0.002, "adu_place_effect_variance": 0.5}
    inp = _adu_inputs(HB, 2.0, 0, 1.0, eligible=(10_000.0,))
    plain = v9.adu_draws(inp, 3000, 4, fixed, states_spec=NO_SPREAD)
    none = v9.adu_draws(inp, 3000, 4, fixed, history=_history([np.nan] * 4), states_spec=NO_SPREAD)
    zero = v9.adu_draws(inp, 3000, 4, fixed, history=_history([0, 0, 0, 0]), states_spec=NO_SPREAD)
    assert (none == plain).all()  # no counts: the prior draw is kept, so the variants are identical
    assert zero.mean() < 0.2 * plain.mean()


def test_history_file_refuses_window_years_and_unsourced_counts(tmp_path):
    head = "geoid,year,adu_permits,source_url,source_section,quote\n"
    ok = tmp_path / "ok.csv"
    ok.write_text(head + "4159000,2016,10,https://x,p.1,q\n")
    assert v9.load_history(ok)["geoid"].iloc[0] == "4159000"
    late = tmp_path / "late.csv"
    late.write_text(head + "4159000,2018,10,https://x,p.1,q\n")
    with pytest.raises(ValueError, match="V9 outcome"):
        v9.load_history(late)
    bare = tmp_path / "bare.csv"
    bare.write_text(head + "4159000,2016,10,,p.1,q\n")
    with pytest.raises(ValueError, match="source"):
        v9.load_history(bare)


def test_history_for_one_place_leaves_the_others_draws_alone():
    # written with the pre-D-048 ramp (0.5 at age 2), which the "more than double" check assumes
    fixed = {"adu_mature_hazard_ref": 0.002, "adu_place_effect_variance": 0.5}
    fixed |= OLD_RAMP
    inp = _adu_inputs(HB, 2.0, 0, 1.0, eligible=(10_000.0, 5_000.0))
    years = (2014, 2015, 2016, 2017)
    hist = v9.AduHistory(
        inputs=_adu_inputs(HB, 2.0, 0, 1.0, eligible=(10_000.0, 5_000.0), years=years),
        eligible=np.full((2, 4), 10_000.0),
        counts=np.array([[40, 40, 40, 40], [np.nan] * 4]),
    )
    plain = v9.adu_draws(inp, 500, 6, fixed, states_spec=NO_SPREAD)
    with_hist = v9.adu_draws(inp, 500, 6, fixed, history=hist, states_spec=NO_SPREAD)
    assert (with_hist[:, 1, :] == plain[:, 1, :]).all()
    assert with_hist[:, 0, :].mean() > 2 * plain[:, 0, :].mean()


def test_oregon_gets_one_state_multiplier_per_draw_from_the_tau_grid():
    # τ fixed at 0.5 (grid of one point): log s_d ~ N(0, 0.5²), the same for every Oregon place in a draw
    # (D-044, as scenarios.adu.run). With α = 0, the reference place and no ramp (D-048), each draw's mean
    # is s_d × 10,000 × 0.002 = s_d × 20.
    fixed = {"adu_mature_hazard_ref": 0.002, "adu_place_effect_variance": 0.0}
    inp = _adu_inputs(HB, 2.0, 0, 1.0, eligible=(10_000.0, 10_000.0), years=tuple(range(2018, 2026)))
    d = v9.adu_draws(inp, 4000, 8, fixed, states_spec={"adu_state_tau_prob__0_5": 1.0})
    per_draw = d.sum(axis=(1, 2)) / (2 * 8 * 20.0)  # ≈ s_d, Poisson noise averaged over 16 place-years
    assert np.median(np.log(per_draw[per_draw > 0])) == pytest.approx(0.0, abs=0.04)
    assert np.std(np.log(per_draw[per_draw > 0])) == pytest.approx(0.5, rel=0.12)
    a, b = d[:, 0, :].sum(axis=1), d[:, 1, :].sum(axis=1)
    assert np.corrcoef(a, b)[0, 1] > 0.8  # shared, not independent per place
    # a fitted state gets no multiplier
    spec = {"adu_state_tau_prob__0_5": 1.0, "adu_state_effect_fitted__OR": 1.0}
    flat = v9.adu_draws(inp, 4000, 8, fixed, states_spec=spec)
    assert np.std(flat.sum(axis=(1, 2)) / 320.0) < 0.1
