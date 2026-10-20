"""The ADU hazard (model/hazard.py): ramp, share that pencils, transport, calibration range, all by hand."""

import math

import numpy as np
import pytest

from lotline.model import hazard

P = hazard.central_params()
# hand examples use the old anchor and a reference at 2025 costs; the method does not depend on either
P4 = dict(P, adu_mature_hazard_ref=0.004, adu_ref_cost_index=1.0)


def _phi(z):
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def test_ramp_by_hand():
    """half 2, slope 0.75: t = 1 -> 1 / (1 + e^(1/0.75)) = 0.2086; t = 2 -> 0.5; t = 5 -> 1 / (1 + e^-4)."""
    r = hazard.ramp([1, 2, 5], 2.0, 0.75)
    assert r == pytest.approx([1 / (1 + math.exp(4 / 3)), 0.5, 1 / (1 + math.exp(-4))])
    assert r[0] == pytest.approx(0.2086, abs=1e-4)
    assert np.all(np.diff(hazard.ramp(np.arange(0, 10), 2.0, 0.75)) > 0)  # never falls


def test_feasible_share_by_hand():
    """PCR = 1 + margin -> exactly half the lots pencil; one σ above -> Φ(1) = 0.8413; PCR 0 -> none."""
    assert hazard.feasible_share(1.1, 0.10, 0.5) == pytest.approx(0.5)
    assert hazard.feasible_share(1.1 * math.exp(0.5), 0.10, 0.5) == pytest.approx(0.841345, abs=1e-6)
    assert hazard.feasible_share(0.0, 0.10, 0.5) == 0.0


def test_adu_price_to_cost_by_hand():
    """Central parameters, 800 sq ft ADU rented out, rent $1,100 a month, no fee:
    value = 12 × 1,100 × 0.95 (vacancy) × 0.65 (operating costs) / 0.055 (cap rate) = 148,200;
    hard = 165 × 1.15 (small-building premium) × 800 = 151,800; soft = 20% = 30,360;
    interest = 0.085 × 0.75 years × 0.5 × 182,160 = 5,806.35; cost = 187,966.35; PCR = 0.78844."""
    assert hazard.adu_price_to_cost(1100, params=P) == pytest.approx(148_200 / 187_966.35)
    assert hazard.adu_price_to_cost(1100, params=P) == pytest.approx(0.78844, abs=1e-5)


def test_mature_hazard_equals_the_anchor_at_the_reference_place():
    h = hazard.adu_mature_hazard(
        P["adu_ref_rent_usd"],
        P["adu_ref_home_value_usd"],
        P["adu_ref_mortgage_rate"],
        cost_index=P.get("adu_ref_cost_index", 1.0),
    )
    assert float(h) == pytest.approx(P["adu_mature_hazard_ref"])


def test_mature_hazard_one_place_by_hand():
    """Rent $1,100, home value half the reference's, mortgage rate 2 points above the reference's mean.
    PCR 0.78844 -> F = Φ((ln 0.78844 − ln 1.1) / 0.5) = Φ(−0.6660) = 0.25270.
    Reference: rent 1,573 -> PCR 1.12747 -> F_ref = Φ(0.04934) = 0.51967; u = 0.004 / 0.51967 = 0.0076972.
    Equity 0.5^0.25 = 0.84090; rate e^(−0.07 × 2) = 0.86936.
    h = 0.0076972 × 0.25270 × 0.84090 × 0.86936 = 0.0014219 (1.42 per 1,000 parcels a year)."""
    f = _phi((math.log(148_200 / 187_966.35) - math.log(1.1)) / 0.5)
    ref_value = 12 * 1573 * 0.95 * 0.65 / 0.055
    f_ref = _phi((math.log(ref_value / 187_966.35) - math.log(1.1)) / 0.5)
    by_hand = 0.004 / f_ref * f * 0.5**0.25 * math.exp(-0.07 * 2)
    h = hazard.adu_mature_hazard(1100, P["adu_ref_home_value_usd"] / 2, P["adu_ref_mortgage_rate"] + 2, P4)
    assert float(h) == pytest.approx(by_hand)
    assert float(h) == pytest.approx(0.0014219, abs=1e-7)


@pytest.mark.parametrize("seed", range(5))
def test_more_profit_never_lowers_uptake(seed):
    """Higher rent (higher price-to-cost) never lowers the hazard, for any parameter draw in range."""
    rng = np.random.default_rng(seed)
    params = dict(P)
    for name in ("adu_feasibility_dispersion", "adu_equity_elasticity", "adu_rate_semi_elasticity"):
        spec = hazard.load_params("hazard")[name]
        params[name] = float(rng.uniform(spec.low, spec.high))
    rents = np.linspace(300, 4000, 200)
    pcr = hazard.adu_price_to_cost(rents, params=params)
    h = hazard.adu_mature_hazard(rents, 400_000, 6.5, params)
    assert np.all(np.diff(pcr) > 0)
    assert np.all(np.diff(h) >= 0)


def test_hazard_is_a_probability():
    params = dict(P, adu_mature_hazard_ref=0.9)  # absurd anchor: still capped at 1
    h = hazard.adu_mature_hazard([100, 1573, 50_000], 5_000_000, 0.0, params)
    assert np.all((h >= 0) & (h <= 1)) and h[-1] == 1.0
    assert float(hazard.adu_mature_hazard(0, 300_000, 6.0)) == 0.0


def test_calibration_distance_by_hand():
    """Rent range 1,573-2,034: rent 1,100 -> log(1,573 / 1,100) = 0.3577; rent 1,800 -> 0; rent 2,500 ->
    log(2,500 / 2,034). Value and rate inside -> total = rent part."""
    d = hazard.calibration_distance([1100, 1800, 2500], 600_000, 5.0)
    assert d["rent"] == pytest.approx([math.log(1573 / 1100), 0.0, math.log(2500 / 2034)])
    assert d["home_value"] == pytest.approx([0, 0, 0]) and d["total"] == pytest.approx(d["rent"])


def test_widen_keeps_the_mean_and_does_nothing_inside_the_range():
    z = np.random.default_rng(0).standard_normal(400_000)
    assert hazard.widen(0.002, 0.0, z) == pytest.approx(np.full(z.shape, 0.002))
    wide = hazard.widen(0.002, 0.5, z)  # s = 1.0 × 0.5: log-sd 0.5
    assert wide.mean() == pytest.approx(0.002, rel=0.01)
    assert np.std(np.log(wide)) == pytest.approx(0.5, rel=0.01)


def test_cost_index_by_hand():
    """Hard cost × 1.1: cost = 1.1 × 187,966.35 (hard, soft and interest all scale) -> PCR falls by 1/1.1."""
    base = hazard.adu_price_to_cost(1100, params=P)
    assert hazard.adu_price_to_cost(1100, params=P, cost_index=1.1) == pytest.approx(base / 1.1)
    # with a reference priced at an earlier cost era (index 0.88), a place at that era's cost and the
    # reference's rent, value and rate gets exactly the anchor
    ref = dict(P, adu_ref_cost_index=0.88)
    h = hazard.adu_mature_hazard(
        1573, P["adu_ref_home_value_usd"], P["adu_ref_mortgage_rate"], ref, cost_index=0.88
    )
    assert float(h) == pytest.approx(P["adu_mature_hazard_ref"])
    # higher costs never raise the hazard
    lo = hazard.adu_mature_hazard(1400, 400_000, 6.0, P, cost_index=0.9)
    hi = hazard.adu_mature_hazard(1400, 400_000, 6.0, P, cost_index=1.1)
    assert float(hi) < float(lo)
