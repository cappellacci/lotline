"""The shortfall view of housing need against its hand-worked example (model/shortfall.py docstring)."""

import pytest

from lotline.model import shortfall


def test_homes_lost_by_hand():
    assert shortfall.homes_lost(5_000_000, 0.003) == pytest.approx(75_000)


def test_gap_by_hand():
    g = shortfall.gap(
        (40_000, 40_000, 160_000), (200_000, 200_000, 200_000), 5_000_000, (0.002, 0.003, 0.005),
        (240_000, 370_000, 520_000),
    )  # fmt: skip
    assert (g["lost_low"], g["lost"], g["lost_high"]) == pytest.approx((50_000, 75_000, 125_000))
    assert (g["need_low"], g["need"], g["need_high"]) == pytest.approx((290_000, 315_000, 485_000))
    assert (g["gap_low"], g["gap"], g["gap_high"]) == pytest.approx((-230_000, -55_000, 245_000))


def test_falling_households_lower_the_need():
    up = shortfall.gap((60_000,) * 3, (0.0,) * 3, 1e6, (0.003,) * 3, (100_000,) * 3)
    down = shortfall.gap((60_000,) * 3, (-30_000.0,) * 3, 1e6, (0.003,) * 3, (100_000,) * 3)
    assert down["need"] == pytest.approx(up["need"] - 30_000)
