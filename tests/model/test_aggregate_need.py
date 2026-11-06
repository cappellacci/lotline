"""Share of housing need (model/aggregate.py, D-056) against hand-worked examples, plus checks on the
generated config/params/housing_need.yaml."""

import re

import numpy as np
import pytest

from lotline.config import Parameter, load_params
from lotline.model import aggregate


def _p(value, low, high):
    return Parameter(value=value, low=low, high=high, unit="homes", source="test")


PARAMS = {
    "household_growth_5y_aa": _p(500, 400, 600),
    "shortage_stock_aa": _p(1000, 800, 2000),
    "household_growth_5y_bb": _p(-50, -50, -50),  # falling projection
    "shortage_stock_bb": _p(300, 300, 300),
    "shortage_stock_cc": _p(1000, 800, 2000),  # shortage only (a tier-3 state)
}
# 0..500 in 1s: P10/P50/P90 = 50/250/450
DRAWS = np.arange(0, 501, dtype=float)


def test_shortage_share_by_hand():
    # P10/P50/P90 = 50/250/450 over 1,000 -> 0.05/0.25/0.45; median 250 / 2,000 = 0.125, 250 / 800 = 0.3125
    s = aggregate.share_of_need(DRAWS, "CC", params=PARAMS)
    assert s["denominator_kind"] == "shortage_stock"
    assert s["label"] == "of the state's estimated shortage"
    assert (s["share_p10"], s["share_p50"], s["share_p90"]) == pytest.approx((0.05, 0.25, 0.45))
    assert s["share_p50_at_need_high"] == pytest.approx(0.125)
    assert s["share_p50_at_need_low"] == pytest.approx(0.3125)


def test_growth_is_the_headline_where_positive_and_kind_always_carried():
    s = aggregate.share_of_need(DRAWS, "aa", params=PARAMS)
    assert s["denominator_kind"] == "household_growth_5y"
    assert s["share_p50"] == pytest.approx(250 / 500)
    assert s["share_p50_at_need_low"] == pytest.approx(250 / 400)
    other = aggregate.share_of_need(DRAWS, "AA", kind="shortage_stock", params=PARAMS)
    assert other["denominator_kind"] == "shortage_stock"
    assert other["share_p50"] == pytest.approx(0.25)


def test_falling_projection_falls_back_to_shortage():
    assert aggregate.headline_kind("BB", PARAMS) == "shortage_stock"
    with pytest.raises(ValueError):
        aggregate.share_of_need(DRAWS, "BB", kind="household_growth_5y", params=PARAMS)
    assert aggregate.share_of_need(DRAWS, "BB", params=PARAMS)["share_p50"] == pytest.approx(250 / 300)


def test_missing_state_raises():
    with pytest.raises(KeyError):
        aggregate.headline_kind("ZZ", PARAMS)
    with pytest.raises(KeyError):
        aggregate.share_of_need(DRAWS, "CC", kind="household_growth_5y", params=PARAMS)


# ---- the generated config ------------------------------------------------------------------------------

ONBOARDED = ("mn", "nc", "tx", "oh", "or")


def test_config_has_both_kinds_with_url_and_vintage():
    p = load_params("housing_need")
    shortage = [k for k in p if k.startswith("shortage_stock_")]
    assert len(shortage) == 51  # 50 states and DC
    for st in ONBOARDED:
        assert f"household_growth_5y_{st}" in p
    for key, par in p.items():
        kind = "household_growth_5y" if key.startswith("household_growth_5y_") else "shortage_stock"
        assert key.startswith(kind)
        assert re.search(r"https?://", par.source), f"{key}: no source URL"
        assert par.notes.startswith(f"kind: {kind}; vintage: "), (
            f"{key}: notes must open with kind and vintage"
        )


def test_config_reading_rules():
    p = load_params("housing_need")
    # shortage: Up for Growth is the value; Freddie Mac surplus states (e.g. Ohio) have no range
    assert p["shortage_stock_oh"].low == p["shortage_stock_oh"].high == p["shortage_stock_oh"].value
    assert p["shortage_stock_or"].low == p["shortage_stock_or"].value < p["shortage_stock_or"].high
    # Ohio's projection falls, so its headline is the shortage; the other onboarded states use growth
    assert p["household_growth_5y_oh"].value < 0
    assert aggregate.headline_kind("OH") == "shortage_stock"
    for st in ("MN", "NC", "TX", "OR"):
        assert aggregate.headline_kind(st) == "household_growth_5y"
    tx = p["household_growth_5y_tx"]
    assert tx.low < tx.value < tx.high  # Texas's migration scenarios
