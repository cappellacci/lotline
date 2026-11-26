"""D-099: the first-years term's pieces against hand-worked examples."""

import numpy as np
import pandas as pd
import pytest

from lotline.calibrate.adu import adu_new_rule as nr
from lotline.calibrate.adu import calibrate_adu as cal


def _rows():
    return pd.DataFrame(
        {
            "theme": ["adu"] * 5,
            "jurisdiction_geoid": ["A", "A", "B", "C", "C"],
            "effective_date": ["2016-01-01", "2019-05-20", "2016-01-01", "2016-01-01", "2020-01-01"],
            "adus_per_lot": [0, 1, 1, 0, 1],
            "coding_notes": ["", "", "", "", "x UNKNOWN-PLACEHOLDER"],
        }
    )


def test_first_allowing_year_hand_worked():
    assert nr.first_allowing_year(_rows()) == {"A": 2019}


def test_new_rule_flags_hand_worked():
    assert list(nr.new_rule_flags(range(2018, 2024), 2019, 3)) == [False, True, True, True, False, False]
    assert not nr.new_rule_flags(range(2018, 2024), None).any()
    assert nr.K == 5


def _pl(base, years=(2018, 2019, 2020)):
    n = len(base)
    return cal.PlaceData(
        "MN", "A", "A", np.array(years), np.zeros(n), np.asarray(base, dtype=float), np.full((1, n, 1), 4),
        np.ones((n, 1)), np.array([1.0]), None, {},
    )  # fmt: skip


def test_scaled_hand_worked():
    pl = _pl([10, 10, 10])
    out = nr.scaled(pl, 0.5, np.array([False, True, True]))
    assert out.base == pytest.approx([10, 5, 5])
    assert nr.scaled(pl, 1.0, np.array([True, True, True])) is pl
    s = nr.scaled_all([pl], 0.5, {"A": 2019})
    assert s[0].base == pytest.approx([10, 5, 5])
    # the expected count in a flagged year is ν times the unflagged one
    cv = cal._cvals(1.0, 1.0)
    assert s[0].k(cv)[0, 1] == pytest.approx(0.5 * pl.k(cv)[0, 1])


def test_nu_grid():
    assert nr.NU_GRID[0] == 0.05 and nr.NU_GRID[-1] == 1.5 and 1.0 in nr.NU_GRID and len(nr.NU_GRID) == 30
