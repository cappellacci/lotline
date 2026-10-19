"""Austin V0 comparisons (reports/tx/V0.md) against hand-worked synthetic examples."""

from __future__ import annotations

import pandas as pd
import pytest

from lotline.adapters.states.tx import v0_austin as v


def _permit(pid, year, btype, units, code, parcel="48453P1", demo=False, conv=False):
    return {
        "permit_id": pid,
        "issue_year": year,
        "building_type_std": btype,
        "units_new": units,
        "permit_class_raw": f"R- {code} x|New",
        "parcel_id": parcel,
        "jurisdiction_geoid": "4805000",
        "is_demolition": demo,
        "is_conversion": conv,
    }


@pytest.fixture
def permits() -> pd.DataFrame:
    rows = [
        _permit("A1", 2020, "SFD", 1, "101", "484530000001"),
        _permit("A2", 2020, "SFD", 1, "101", "484530000002"),
        _permit("A3", 2020, "ADU", 1, "102", "R654373"),
        _permit("A4", 2020, "U2", 1, "103", None),  # one duplex side
        _permit("A5", 2020, "U3_4", 4, "104", "484530000003"),
        # three permits on one parcel repeating a 100-unit project total: counted once with D-008
        _permit("M1", 2020, "MF5", 100, "105", "48453PX"),
        _permit("M2", 2020, "MF5", 100, "105", "48453PX"),
        _permit("M3", 2020, "MF5", 100, "105", "48453PX"),
        _permit("M4", 2020, "MF5", 10, "105", "484530000004"),
        _permit("X1", 2020, "OTHER", 20, "106", "484530000005"),  # mixed use
        _permit("C1", 2020, "OTHER", 2, "436", "484530000006", conv=True),  # conversion: not mixed use
        _permit("D1", 2020, "SFD", 0, "645", "484530000007", demo=True),
        _permit("S1", 2021, "SFD", 1, "101", "484530000001"),
    ]
    df = pd.DataFrame(rows)
    df["units_new"] = df["units_new"].astype("Int64")
    return df


def test_permit_code(permits):
    assert v.permit_code(permits).tolist()[:5] == ["101", "101", "102", "103", "104"]


def test_new_units_by_line(permits):
    lines = v.new_units_by_line(permits)
    y = lines.loc[2020]
    assert (y.sf, y.adu, y.duplex, y.u3_4) == (2, 1, 1, 4)
    assert y.u5p == 110  # 100 once + 10
    assert y.u5p_reported == 310  # 3 x 100 + 10
    assert y.mixed_use == 20  # the 436 conversion is not mixed use
    assert lines.loc[2021].sf == 1


def test_compare_with_bps_and_gaps(permits):
    bps = pd.DataFrame(
        {
            "year": [2020, 2021],
            "units_1": [4, 1],
            "units_2": [0, 0],
            "units_3_4": [4, 0],
            "units_5p": [100, 0],
        }
    )
    cmp = v.compare_with_bps(v.new_units_by_line(permits), bps, years=[2020, 2021])
    r = cmp.loc[2020]
    assert (r["1_2_austin"], r["1_2_bps"], r["1_2_ratio"]) == (4, 4, 1.0)  # 2 SF + 1 ADU + 1 duplex side
    assert r["sf_ratio"] == 0.5
    assert r["5p_ratio"] == 1.1 and r["5p_reported_ratio"] == 3.1 and r["5p_mixed_ratio"] == 1.3
    assert v.gap_years(cmp, "1_2") == []
    assert v.gap_years(cmp, "sf") == [2020]
    assert v.gap_years(cmp, "3_4") == [2021]  # 0 / 0: not computable, so listed
    s = v.summarize(cmp, "1_2", [2020, 2021])
    assert s["pooled"] == 1.0
    fp = v.five_plus_periods(cmp, periods=((2020, 2021),))
    assert fp.iloc[0]["ratio (rule on)"] == 1.1


def test_adu_check_filters_and_matches(permits):
    raw = pd.DataFrame(
        {
            "permit_number": ["A3", "Z9", "Z8"],
            "issue_date": ["2020-03-01T00:00:00.000", "2020-05-01T00:00:00.000", "2020-06-01T00:00:00.000"],
            "jurisdiction": ["AUSTIN FULL PURPOSE", "AUSTIN 2 MILE ETJ", "AUSTIN LTD"],
            "status_current": ["Final", "Final", "VOID"],
        }
    )
    out = v.adu_check(permits, raw, years=[2020]).set_index("year")
    assert (out.loc[2020, "r102_ours"], out.loc[2020, "adu_dataset"], out.loc[2020, "in_both"]) == (1, 1, 1)
    assert out.loc[2020, "status"] == "match"


def test_parcel_links(permits):
    parcels = pd.DataFrame({"parcel_id": ["484530000001", "484530000003"]})
    out = v.parcel_links(permits, parcels).set_index("period")
    row = out.loc["2020–2025"]
    # 12 new-home permits (D1 is a demolition): 1 with no ID, 1 Williamson/Hays, 3 found in the roll
    assert row["permits"] == 12
    assert row["no parcel ID"] == "8.33%"
    assert row["Williamson/Hays account"] == "8.33%"
    assert row["in 2026 TCAD roll"] == "25.00%"  # A1, A5 and S1 (2021)


def test_acs_stock_check():
    parcels = pd.DataFrame(
        {
            "jurisdiction_geoid": ["4805000"] * 4,
            "land_use_std": ["SF_DETACHED", "SF_DETACHED", "CONDO_UNIT", "DUPLEX"],
        }
    )
    acs = pd.DataFrame(
        {
            "geo": ["place:4805000"] * 4,
            "end_year": [2023, 2024, 2024, 2024],
            "table_id": ["B25024"] * 4,
            "variable": ["B25024_002", "B25024_002", "B25024_003", "B25003_001"],
            "estimate": [99.0, 4.0, 1.0, 50.0],
        }
    )
    out = v.acs_stock_check(parcels, acs)
    assert out["ratio"].tolist() == [0.5, 0.75, 0.6]  # 2/4, 3/4, 3/(4+1); the 2023 estimate is ignored
