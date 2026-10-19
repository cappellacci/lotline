"""Every parameter file loads, every value sits in its range, and every parameter names a source."""

import pytest

from lotline.config import CONFIG_DIR, load_params

FILES = sorted(p.stem for p in (CONFIG_DIR / "params").glob("*.yaml"))


@pytest.mark.parametrize("name", FILES)
def test_parameters_are_sourced(name):
    params = load_params(name)  # validates value within [low, high]
    assert params
    for key, p in params.items():
        assert p.source.strip() and "TBD" not in p.source, f"{name}.{key} has no source"
        assert p.unit.strip(), f"{name}.{key} has no unit"


def test_engine_parameters_from_the_research_docs():
    agg, fees = load_params("aggregate"), load_params("fees")
    assert (agg["adu_net_new_share"].low, agg["adu_net_new_share"].high) == (0.5, 0.8)
    assert (agg["displacement_share"].low, agg["displacement_share"].high) == (0.0, 0.5)
    assert agg["completion_factor_multifamily"].value < agg["completion_factor_single_family"].value
    for key in ("completion_factor_single_family", "completion_factor_multifamily", "completion_factor_all"):
        assert "scripts/dev/completion_factors.py" in agg[key].source  # reproducible from Census data
    cut = fees["handbook_fee_per_unit_usd"].value * fees["handbook_fee_cut_share"].value
    assert cut == 25_000  # Handbook: -50% of $50k = -$25k per unit


def test_fee_elasticity_range_includes_zero_and_stays_in_the_v6_band():
    """D-010: low case is no effect; the high case stays inside V6's 0 to +12% single-family band.

    By hand at the high end: 1.75 x 0.75 (1 - lambda low) x 25,000 / 350,000 (illustrative TDC) = 0.09375.
    """
    fees = load_params("fees")
    eps, lam = fees["fee_permit_elasticity"], fees["land_capture_share"]
    assert eps.low == 0.0
    assert eps.value == pytest.approx(0.3)  # E081 tract-level unit elasticity
    high_effect = eps.high * (1 - lam.low) * 25_000 / 350_000
    assert high_effect == pytest.approx(0.09375)
    assert 0.0 <= high_effect <= 0.12
