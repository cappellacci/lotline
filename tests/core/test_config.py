import pytest
from pydantic import ValidationError

from lotline.config import Holdout, Parameter, all_states, load_state


def test_four_states_configured_with_required_holdouts():
    assert all_states() == ["MN", "NC", "OH", "TX"]
    assert [h.test_id for h in load_state("MN").holdouts] == ["V5-MN-STPAUL"]
    assert [h.test_id for h in load_state("NC").holdouts] == ["V5-NC-CHARLOTTE"]
    charlotte = load_state("NC").holdouts[0]
    assert charlotte.geoid == "3712000" and str(charlotte.outcome_from) == "2023-06-01"


def test_holdout_window_must_be_ordered():
    with pytest.raises(ValidationError):
        Holdout(
            test_id="V5-MN-X",
            place="X",
            geoid="2700000",
            outcome_from="2025-01-01",
            outcome_until="2024-01-01",
            reason="r",
        )


def test_parameter_value_must_lie_in_range():
    Parameter(value=0.5, low=0.2, high=0.8, unit="share", source="E039")
    with pytest.raises(ValidationError):
        Parameter(value=0.9, low=0.2, high=0.8, unit="share", source="E039")
