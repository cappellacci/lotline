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
