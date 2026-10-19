"""Repeated project totals counted once (analysis plan D-008), against a hand-worked example."""

import pandas as pd
import pytest

from lotline.build.permits import count_units, flag_repeated_totals, size_class
from lotline.config import Parameter, load_params

CITY = "3918000"


def _permits(rows):
    """rows: (permit_id, parcel_id, year, units_new, is_demolition)."""
    df = pd.DataFrame(rows, columns=["permit_id", "parcel_id", "issue_year", "units_new", "is_demolition"])
    return df.assign(
        jurisdiction_geoid=CITY,
        issue_year=df["issue_year"].astype("Int64"),
        units_new=df["units_new"].astype("Int64"),
        is_demolition=df["is_demolition"].astype("boolean"),
    )


@pytest.fixture
def example():
    rows = [(f"P{i}", "A", 2023, 198, False) for i in range(9, 0, -1)]  # 9 × 198 on parcel A
    rows += [(f"S{i}", "B", 2023, 12, False) for i in range(3)]  # 3 × 12: below 50 units
    rows += [("T1", "C", 2022, 280, False), ("T2", "C", 2022, 280, False)]  # 2 × 280: below 3 permits
    rows += [(f"N{i}", None, 2023, 150, False) for i in range(3)]  # no parcel: never grouped
    rows += [("Y1", "D", 2021, 100, False), ("Y2", "D", 2021, 100, False), ("Y3", "D", 2022, 100, False)]
    rows += [(f"X{i}", "E", 2023, 60, True) for i in range(3)]  # demolitions: never grouped
    rows += [("Z1", "F", 2023, 1, False)]
    return _permits(rows)


def test_params_load_with_range_and_source():
    p = load_params("permits")
    assert p["repeated_total_min_units"].value == 50
    assert (p["repeated_total_min_units"].low, p["repeated_total_min_units"].high) == (20, 100)
    assert p["repeated_total_min_permits"].value == 3
    assert "D-008" in p["repeated_total_min_permits"].source


def test_nine_repeats_keep_only_the_lowest_permit_id(example):
    flags = flag_repeated_totals(example)
    a = example["parcel_id"].eq("A")
    assert flags[a].sum() == 8
    assert example.loc[a & ~flags, "permit_id"].tolist() == ["P1"]


def test_everything_else_is_left_as_reported(example):
    flags = flag_repeated_totals(example)
    others = ~example["parcel_id"].eq("A")
    assert not flags[others].any()  # 12-unit, 2-permit, no-parcel, split-year and demolition groups


def test_count_units_hand_worked_totals(example):
    on = count_units(example).set_index(["issue_year", "size_class"])["units"]
    off = count_units(example, dedupe=False).set_index(["issue_year", "size_class"])["units"]
    # 2023, 5+: 198 (once) + 450 no-parcel; 3 × 12 = 36 also 5+. Demolitions report 60 new each = 180.
    assert on[(2023, "5p")] == 198 + 36 + 450 + 180
    assert off[(2023, "5p")] == 9 * 198 + 36 + 450 + 180
    assert on[(2022, "5p")] == off[(2022, "5p")] == 560 + 100
    assert on[(2021, "5p")] == 200
    assert on[(2023, "1")] == 1


def test_thresholds_come_from_params(example):
    strict = {
        "repeated_total_min_units": Parameter(value=50, low=20, high=100, unit="u", source="t"),
        "repeated_total_min_permits": Parameter(value=2, low=2, high=5, unit="p", source="t"),
    }
    flags = flag_repeated_totals(example, strict)
    assert flags[example["parcel_id"].eq("C")].sum() == 1  # 2 × 280 now counted once
    assert flags[example["parcel_id"].eq("D")].sum() == 1  # 2021 pair; 2022 alone untouched


def test_size_class_matches_bps_classes():
    s = size_class(pd.Series([0, 1, 2, 3, 4, 5, 198, None], dtype="Int64"))
    assert s.tolist()[1:7] == ["1", "2", "3_4", "3_4", "5p", "5p"]
    assert s.isna().tolist() == [True, False, False, False, False, False, False, True]
