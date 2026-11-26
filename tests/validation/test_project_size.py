"""Buildings per project (D-092 deviation 2026-11-15 (d)): hand-worked examples."""

from __future__ import annotations

import math

import pandas as pd
import pytest

from lotline.validation import project_size as ps


def _p(**cols):
    n = len(next(iter(cols.values())))
    base = {"source": ["s"] * n, "type_confidence": ["high"] * n, "is_demolition": [False] * n,
            "is_conversion": [False] * n, "n_buildings": [None] * n,
            "date_precision": ["day"] * n}  # fmt: skip
    return pd.DataFrame(base | cols)


def test_buildings_filters_and_counts():
    p = _p(building_type_std=["U2", "U3_4", "SFD", "U2"], n_buildings=[None, 2, None, None],
           is_demolition=[False, False, False, True])  # fmt: skip
    b = ps.buildings(p)
    assert b["building_type_std"].tolist() == ["U2", "U3_4"]
    assert b["bldgs"].tolist() == [1.0, 2.0]


def test_buildings_drops_unknown_type():
    p = _p(building_type_std=["U2", "U2"], type_confidence=["high", "unknown"])
    assert len(ps.buildings(p)) == 1


def test_same_lot_by_hand():
    b = _p(parcel_id=["A", "A", "A", "B", None],
           issue_date=["2020-01-01", "2020-06-01", "2021-03-01", "2020-01-01", "2020-01-01"],
           building_type_std=["U2"] * 5).assign(bldgs=[1.0, 1.0, 1.0, 2.0, 5.0])  # fmt: skip
    assert sorted(ps.same_lot(b).tolist()) == [1.0, 2.0, 2.0]


def test_same_lot_window_is_from_first_permit():
    # 2020-01-01, 2020-09-01, 2021-02-01: the third is 397 days after the first -> a new project
    b = _p(parcel_id=["A"] * 3, issue_date=["2020-01-01", "2020-09-01", "2021-02-01"],
           building_type_std=["U2"] * 3).assign(bldgs=[1.0] * 3)  # fmt: skip
    assert ps.same_lot(b).tolist() == [2.0, 1.0]


def test_same_day_by_hand():
    b = _p(issue_date=["2020-01-01", "2020-01-01", "2020-01-02", "2020-01-05"],
           date_precision=["day", "day", "day", "month"],
           building_type_std=["U2"] * 4).assign(bldgs=[1.0, 1.0, 3.0, 9.0])  # fmt: skip
    assert sorted(ps.same_day(b).tolist()) == [2.0, 3.0]


def test_inflation_by_hand():
    assert ps.inflation(pd.Series([1, 1, 2])) == pytest.approx(1.5)
    assert ps.inflation(pd.Series([1, 1, 1])) == 1.0
    assert math.isnan(ps.inflation(pd.Series([], dtype=float)))


def test_share_in_big_by_hand():
    assert ps.share_in_big(pd.Series([1, 1, 2, 3])) == pytest.approx(3 / 7)
