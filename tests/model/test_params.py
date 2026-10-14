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
    assert (agg["completion_factor"].low, agg["completion_factor"].high) == (0.85, 0.95)
    cut = fees["handbook_fee_per_unit_usd"].value * fees["handbook_fee_cut_share"].value
    assert cut == 25_000  # Handbook: -50% of $50k = -$25k per unit
