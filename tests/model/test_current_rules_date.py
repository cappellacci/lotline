"""D-064: forward runs count as current every coded rule in force on 31 December of the window's first year.

With D-061's window (origin 2025, lead 1 -> 2027-2031) that is 2027-12-31, so a state law in force on
2027-01-15 (like NC S.L. 2026-59) is part of the baseline, not of the reform.
"""

import pandas as pd

from lotline.config import load_params
from lotline.model import baseline

PARAMS = load_params("baseline")


def _with(**values):
    out = dict(PARAMS)
    for name, v in values.items():
        out[name] = PARAMS[name].model_copy(update={"value": v})
    return out


def test_rules_date_by_hand():
    # first window year = 2025 + 1 + 1 = 2027; cutoff = 31 Dec of (2027 - 1 + 1)
    assert int(PARAMS["current_rules_window_years"].value) == 1
    assert baseline.rules_as_of(2025, PARAMS) == pd.Timestamp("2027-12-31")
    # the low value: rules in force on the window's first day
    assert baseline.rules_as_of(2025, _with(current_rules_window_years=0)) == pd.Timestamp("2026-12-31")
    # no lead (the old window 2026-2030): the end of 2026
    assert baseline.rules_as_of(2025, _with(forecast_lead_years=0)) == pd.Timestamp("2026-12-31")
