import pandas as pd
import pytest

from lotline.adapters.national import fred


def _monthly(year, values):
    idx = pd.date_range(f"{year}-01-01", periods=len(values), freq="MS")
    return pd.Series(values, index=idx, dtype=float)


def test_parse_marks_dot_as_missing():
    s = fred.parse("observation_date,CPIAUCSL\n2025-09-01,324.245\n2025-10-01,.\n2025-11-01,325.063\n")
    assert s.isna().tolist() == [False, True, False]


def test_complete_year_mean():
    out = fred.annual_mean(_monthly(2024, range(1, 13)), "monthly")
    assert out.loc[2024] == pytest.approx(6.5)


def test_partial_year_left_missing():
    out = fred.annual_mean(_monthly(2026, [1.0] * 8), "monthly")
    assert pd.isna(out.loc[2026])


def test_single_interior_gap_interpolated():
    # Oct 2025 CPI was never published (federal shutdown): fill from Sep and Nov, then average 12 months
    vals = [
        318.961,
        319.679,
        319.785,
        320.302,
        320.620,
        321.435,
        322.169,
        323.291,
        324.245,
        None,
        325.063,
        326.031,
    ]
    out = fred.annual_mean(_monthly(2025, vals), "monthly")
    filled = 324.245 + (325.063 - 324.245) * 30 / 61  # time-weighted: Sep 1 -> Oct 1 -> Nov 1
    expected = (sum(v for v in vals if v is not None) + filled) / 12
    assert out.loc[2025] == pytest.approx(expected)


def test_two_consecutive_gaps_stay_missing():
    vals = [1.0] * 9 + [None, None, 1.0]
    assert pd.isna(fred.annual_mean(_monthly(2025, vals), "monthly").loc[2025])
