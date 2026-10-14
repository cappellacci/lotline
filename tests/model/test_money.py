"""Real dollars (protocol §5.9): real = nominal × index[base] / index[dollar_year], checked by hand."""

import pandas as pd
import pytest

from lotline.model import money

# CPI-U annual means from LB-030 (FRED CPIAUCSL; October 2025 interpolated): 2024 = 313.70, 2025 = 322.19.
CPI = pd.Series({2024: 313.70, 2025: 322.19})


def test_base_year_comes_from_config():
    assert money.base_year() == 2025


def test_deflate_2024_dollars_to_2025_by_hand():
    """$10,000 of 2024 in 2025 dollars: 10,000 × 322.19 / 313.70 = 10,000 × 1.0270641 = $10,270.64.
    A 2025 amount is unchanged: 50,000 × 322.19 / 322.19 = 50,000."""
    out = money.deflate(pd.Series([10_000.0, 50_000.0]), pd.Series([2024, 2025]), CPI, 2025)
    assert out[0] == pytest.approx(10_270.64, abs=0.01)
    assert out[1] == pytest.approx(50_000.0)


def test_deflate_with_a_synthetic_cost_index():
    """PPI-style index 100 (2020) -> 125 (2025): $80 of 2020 costs 80 × 125 / 100 = $100 in 2025."""
    ppi = pd.Series({2020: 100.0, 2025: 125.0})
    assert money.deflate(80.0, 2020, ppi, 2025)[0] == pytest.approx(100.0)


def test_year_missing_from_index_gives_missing_not_nominal():
    out = money.deflate(pd.Series([1_000.0, 1_000.0]), pd.Series([2024, 2019]), CPI, 2025)
    assert out[0] == pytest.approx(1_027.06, abs=0.01)
    assert pd.isna(out[1])


def test_missing_base_year_raises():
    with pytest.raises(ValueError, match="base year 2026"):
        money.deflate(1.0, 2024, CPI, 2026)


def test_index_by_year_reads_national_cpi_from_market_table():
    market = pd.DataFrame(
        {
            "geo": ["national:US", "national:US", "county:27053"],
            "year": [2024, 2025, 2025],
            "cpi_u": [313.70, 322.19, None],
        }
    )
    assert money.index_by_year(market).to_dict() == {2024: 313.70, 2025: 322.19}
    with pytest.raises(ValueError, match="ppi_resid_inputs"):
        money.index_by_year(market, "ppi_resid_inputs")
