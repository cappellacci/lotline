"""Phase 2 runners on small synthetic stores: config's rounding and range rule, worked by hand."""

from __future__ import annotations

import pandas as pd

from lotline.calibrate import RunContext, data_steps


class FakeStore:
    def __init__(self, tables):
        self.tables = tables

    def read(self, state, table):
        return self.tables[(state, table)]


def _permits(source, adu, sfd):
    rows = [("ADU", "detached")] * adu + [("SFD", None)] * sfd
    df = pd.DataFrame(rows, columns=["building_type_std", "adu_type"])
    return df.assign(source=source, issue_year=2020)


def test_baseline_adu_share_by_hand():
    """MN 1 ADU of 100 one-unit permits (0.01), TX 9 of 100 (0.09): pooled 10/200 = 0.05; range 0.01-0.09."""
    store = FakeStore(
        {
            ("MN", "permits"): _permits("metc_residential_permits", 1, 99),
            ("TX", "permits"): _permits("austin_permits", 9, 91),
        }
    )
    out = data_steps.baseline_adu_share(RunContext(store, False, None, None))
    assert out == {
        "aggregate": {"baseline_adu_share_of_one_unit": {"value": 0.05, "low": 0.01, "high": 0.09}}
    }


def test_mortgage_rate_forecast_by_hand():
    """2025 annual mean as the value; lowest and highest annual means 2015-2025 as the stress range."""
    years = list(range(2014, 2026))
    rates = [9.9, 4.0, 3.6, 4.0, 4.5, 3.9, 3.1, 2.96, 5.3, 6.81, 6.7, 6.595]
    market = pd.DataFrame({"geo": "national:US", "year": years, "mortgage_rate": rates})
    out = data_steps.mortgage_rate_forecast(
        RunContext(FakeStore({("MN", "market_geo_year"): market}), False, None, None)
    )
    assert out == {"market": {"mortgage_rate_forecast": {"value": 6.6, "low": 2.96, "high": 6.81}}}
