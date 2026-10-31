"""Ben's rule for fees that vary by area or plat date (2026-10-30): one central row per group carries the
per-home amount, so the scenario's local total counts each fee once (config/fees/README.md)."""

import pytest

from lotline.config import load_fees
from lotline.model.scenarios.fees import local_fees


@pytest.fixture(scope="module")
def fees():
    return load_fees("TX")


@pytest.fixture(scope="module")
def totals(fees):
    return local_fees(fees).set_index("geoid")["local_fee_per_unit"]


@pytest.mark.parametrize(
    ("geoid", "year", "prefix"),
    [
        ("4865000", 2026, "SAWS water impact fee (flow + system development + water supply)"),
        ("4865000", 2026, "SAWS wastewater impact fee (collection + treatment)"),
        ("4805000", 2026, "Parkland dedication fee in lieu, single-family"),
        ("4805000", 2023, "Water impact fee, lots platted"),
        ("4805000", 2023, "Wastewater impact fee, lots platted"),
    ],
)
def test_one_central_row_per_group(fees, geoid, year, prefix):
    here = (fees["jurisdiction_geoid"] == geoid) & (fees["year"] == year)
    g = fees[here & fees["fee_type"].str.startswith(prefix)]
    assert len(g) >= 2
    assert g["amount_per_unit_usd"].notna().sum() == 1


def test_central_values_by_hand(totals):
    # SAWS: middle of three elevation areas ($4,749 / $4,908 / $5,097) + basin nearest the median of six
    # ($1,171 / $1,553 / $2,073 / $2,083 / $2,664 / $3,451: median $2,078, tie -> the lower, $2,073)
    assert totals["4865000"] == pytest.approx(4908 + 2073)
    # Fort Worth: newest plat cohort, collected from 2026-10-01, 5/8 x 3/4-inch meter
    assert totals["4827000"] == pytest.approx(2990 + 2838)
    # Austin: one parkland tier (medium density, $6,009.04), not all three
    assert totals["4805000"] < 10_000
