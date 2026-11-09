import pandas as pd
import pandera.errors
import pytest

from lotline.config import load_fees


def _write(tmp_path, rows):
    (tmp_path / "fees").mkdir()
    pd.DataFrame(rows).to_csv(tmp_path / "fees" / "zz.csv", index=False)


ROW = {
    "state": "NC",
    "jurisdiction_geoid": "3710740",
    "year": 2026,
    "effective_date": "2025-07-01",
    "fee_component": "water_sewer",
    "fee_type": "Water capacity fee",
    "building_type_std": "SFD",
    "basis": "per_unit",
    "amount_usd": 1500.0,
    "amount_per_unit_usd": 1500.0,
    "dollar_year": 2026,
    "source": "https://example.test/fees.pdf",
    "source_section": "p. 4",
    "source_quote": "Water capacity fee, single-family: $1,500",
    "verified_by": "checker",
    "verified_date": "2026-10-20",
}


def test_a_state_without_a_fee_file_returns_none(tmp_path):
    assert load_fees("zz", tmp_path) is None


def test_fee_rows_validate_with_citations(tmp_path):
    _write(tmp_path, [ROW])
    df = load_fees("zz", tmp_path)
    assert df.loc[0, "amount_per_unit_usd"] == 1500.0 and df.loc[0, "source_section"] == "p. 4"


def test_long_quotes_and_bad_components_are_rejected(tmp_path):
    _write(
        tmp_path, [{**ROW, "source_quote": "x" * 301}, {**ROW, "fee_type": "Other", "fee_component": "bogus"}]
    )
    with pytest.raises((pandera.errors.SchemaError, pandera.errors.SchemaErrors)):
        load_fees("zz", tmp_path)


def test_range_and_in_force_columns_are_checked(tmp_path):
    ok = {
        **ROW,
        "amount_per_unit_low_usd": 1200.0,
        "amount_per_unit_high_usd": 1800.0,
        "in_force_through": 2027,
    }
    _write(tmp_path, [ok])
    df = load_fees("zz", tmp_path)
    assert df.loc[0, "amount_per_unit_high_usd"] == 1800.0 and df.loc[0, "in_force_through"] == 2027


@pytest.mark.parametrize(
    "bad",
    [
        {"amount_per_unit_low_usd": 1600.0},  # low above the central 1,500
        {"amount_per_unit_high_usd": 1400.0},  # high below it
        {"in_force_through": 2025},  # in force through a year before the row's own year (2026)
    ],
)
def test_bad_ranges_and_in_force_years_are_rejected(tmp_path, bad):
    _write(tmp_path, [{**ROW, **bad}])
    with pytest.raises((pandera.errors.SchemaError, pandera.errors.SchemaErrors)):
        load_fees("zz", tmp_path)
