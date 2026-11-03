"""scripts/dev/calibrate_adu.py --statewide (D-040): the verdict bar and the state totals by hand."""

import importlib.util
from pathlib import Path

import numpy as np
import pytest

from lotline.model import calibrate_adu as cal

_spec = importlib.util.spec_from_file_location(
    "calibrate_adu_script", Path(__file__).resolve().parents[2] / "scripts" / "dev" / "calibrate_adu.py"
)
script = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(script)


@pytest.mark.parametrize(
    "obs, p10, p50, p90, want",
    [
        (100, 50, 80, 200, "useful"),  # inside, 100 / 80 = 1.25
        (100, 10, 40, 200, "inside only"),  # inside, 100 / 40 = 2.5 > 2
        (100, 10, 0, 200, "inside only"),  # median 0: no ratio
        (300, 50, 200, 250, "missed"),  # above P90
        (50, 50, 100, 200, "useful"),  # on P10, ratio exactly 0.5
    ],
)
def test_verdict_bar(obs, p10, p50, p90, want):
    assert script.verdict(obs, p10, p50, p90) == want


def _pl(geoid, y):
    y = np.asarray(y, float)
    t = len(y)
    return cal.PlaceData("MN", geoid, geoid, np.arange(t), y, np.ones(t), np.full((1, t, 1), 4),
                         np.ones((t, 1)), np.ones(1))  # fmt: skip


def test_state_totals_sum_places_and_years_per_draw():
    """Two places; draws (3 draws × years). Totals per draw: A (1+2, 0+0, 5+5) + B (4, 0, 10) = 7, 0, 20.
    Observed 3 + 6 = 9; P50 of (7, 0, 20) = 7; P10 = 1.4, P90 = 17.4; Portland 2 + 3 = 5."""
    a, b = _pl("A", [1, 2]), _pl("B", [6])
    draws = {"A": np.array([[1, 2], [0, 0], [5, 5]]), "B": np.array([[4], [0], [10]])}
    portland = {"A": np.array([1.0, 1.0]), "B": np.array([3.0])}
    row = script.state_totals("t", {"MN": [a, b]}, draws, portland).iloc[0]
    assert (row["observed"], row["places"], row["place_years"]) == (9, 2, 3)
    assert (row["p10"], row["p50"], row["p90"]) == pytest.approx((1.4, 7.0, 17.4))
    assert row["portland"] == 5.0 and row["obs_over_p50"] == pytest.approx(9 / 7)
    assert row["verdict"] == "useful"
