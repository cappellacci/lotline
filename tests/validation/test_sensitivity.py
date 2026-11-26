import numpy as np
import pytest

from lotline.validation import sensitivity as sens


def test_first_order_by_hand():
    """The module docstring's example: a step at X = 4.5, two bins, raw share 1, chance 1/7 -> 1."""
    x = np.arange(1, 9)
    y = (x > 4).astype(float)
    assert sens.first_order(x, y, bins=2) == pytest.approx(1.0)


def test_first_order_matches_the_analytic_shares():
    """Y = X1 + 0.5 X2, X1 and X2 independent standard normal: Var Y = 1.25, so S1 = 0.8 and S2 = 0.2."""
    rng = np.random.default_rng(1)
    x1, x2 = rng.standard_normal(20_000), rng.standard_normal(20_000)
    y = x1 + 0.5 * x2
    assert sens.first_order(x1, y) == pytest.approx(0.8, abs=0.02)
    assert sens.first_order(x2, y) == pytest.approx(0.2, abs=0.02)


def test_an_input_that_does_nothing_scores_about_zero():
    """With n = 1,000 and 20 bins, pure noise scores near 0 after the chance level is removed."""
    rng = np.random.default_rng(2)
    shares = [sens.first_order(rng.standard_normal(1000), rng.standard_normal(1000)) for _ in range(50)]
    assert np.mean(shares) < 0.01 and max(shares) < 0.05


def test_drivers_skip_constants_and_report_other():
    rng = np.random.default_rng(3)
    x1, x2 = rng.standard_normal(5000), rng.standard_normal(5000)
    y = x1 + x2
    d = sens.drivers({"a": x1, "held": np.ones(5000), "b": x2}, y)
    assert "held" not in d
    assert d["a"] == pytest.approx(0.5, abs=0.03) and d["b"] == pytest.approx(0.5, abs=0.03)
    assert d["other"] == pytest.approx(0.0, abs=0.05)
