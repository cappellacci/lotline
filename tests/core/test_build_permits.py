"""Repeated project totals counted once (analysis plan D-008 and D-036), against hand-worked examples."""

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


# D-036: permits with no parcel, grouped by day, collapsed only where floor area per unit is implausible.
DAY = pd.Timestamp("2023-05-04")


def _no_parcel(rows):
    """rows: (permit_id, units_new, floor_area_sqft, issue_date, application_date); all 2023, no parcel."""
    df = pd.DataFrame(
        rows, columns=["permit_id", "units_new", "floor_area_sqft", "issue_date", "application_date"]
    )
    return _permits([(r[0], None, 2023, r[1], False) for r in rows]).assign(
        floor_area_sqft=df["floor_area_sqft"].astype(float),
        issue_date=pd.to_datetime(df["issue_date"]),
        application_date=pd.to_datetime(df["application_date"]),
    )


def _total(df, **kw):
    return int(count_units(df, **kw)["units"].sum())


def test_no_parcel_repeated_total_with_tiny_floor_area_counts_once():
    # Dallas 2023: each permit says 471 units in 8,036 sq ft (17 sq ft per unit): one project total.
    df = _no_parcel([(f"D{i}", 471, 8036, DAY, None) for i in (3, 1, 2)])
    assert flag_repeated_totals(df).tolist() == [True, False, True]  # kept on the lowest permit_id, D1
    assert _total(df) == 471
    assert _total(df, dedupe=False) == 3 * 471


def test_no_parcel_identical_real_buildings_stay_as_reported():
    # 60 units in 60,000 sq ft = 1,000 sq ft per unit: three real buildings.
    df = _no_parcel([(f"B{i}", 60, 60000, DAY, None) for i in range(3)])
    assert _total(df) == 180


def test_no_parcel_small_buildings_are_never_grouped():
    # Ten same-day fourplexes with no floor area: below the 50-unit floor.
    df = _no_parcel([(f"F{i}", 4, None, DAY, None) for i in range(10)])
    assert _total(df) == 40


def test_no_parcel_missing_area_counts_as_implausible_and_plausible_permits_stay():
    # One same-day group of four 100-unit permits: two tiny, one missing area, one real (900 sq ft per unit).
    rows = [("A1", 100, 5000, DAY, None), ("A2", 100, None, DAY, None), ("A3", 100, 90000, DAY, None)]
    rows += [("A4", 100, 4000, DAY, None)]
    df = _no_parcel(rows)
    assert flag_repeated_totals(df).tolist() == [False, True, False, True]
    assert _total(df) == 100 + 100  # the total once (A1) plus the real building (A3)


def test_no_parcel_day_falls_back_to_application_date_and_splits_groups():
    other = pd.Timestamp("2023-05-05")
    filed = [(f"W{i}", 404, 9000, None, DAY) for i in range(3)]  # Fort Worth: filing date only
    split = [("V1", 302, None, DAY, None), ("V2", 302, None, DAY, None), ("V3", 302, None, other, None)]
    undated = [(f"U{i}", 150, None, None, None) for i in range(3)]  # no date at all: never grouped
    df = _no_parcel(filed + split + undated)
    assert _total(df) == 404 + 3 * 302 + 3 * 150


def test_no_parcel_demolitions_are_never_grouped():
    df = _no_parcel([(f"X{i}", 471, 8036, DAY, None) for i in range(3)]).assign(
        is_demolition=pd.array([True] * 3, dtype="boolean")
    )
    assert not flag_repeated_totals(df).any()


def test_no_parcel_area_floor_comes_from_params():
    p = load_params("permits")
    assert p["repeated_total_max_sqft_per_unit"].value == 300
    assert (p["repeated_total_max_sqft_per_unit"].low, p["repeated_total_max_sqft_per_unit"].high) == (
        200,
        500,
    )
    assert "D-036" in p["repeated_total_max_sqft_per_unit"].source
    df = _no_parcel([(f"B{i}", 60, 15000, DAY, None) for i in range(3)])  # 250 sq ft per unit
    assert _total(df) == 60
    loose = dict(
        p, repeated_total_max_sqft_per_unit=Parameter(value=200, low=200, high=500, unit="sf", source="t")
    )
    assert _total(df, params=loose) == 180


def test_parcel_rule_unchanged_when_dates_and_areas_are_present(example):
    # Same-day dates and tiny areas on the parcel example change nothing: parcels use D-008's rule.
    dated = example.assign(issue_date=DAY, floor_area_sqft=1.0).assign(
        issue_date=lambda d: d["issue_date"].where(d["parcel_id"].notna())
    )
    assert flag_repeated_totals(dated).tolist() == flag_repeated_totals(example).tolist()
    assert count_units(dated).equals(count_units(example))
