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
    # the hand sums predate the 2026-11-09 permit lookup (permit_fees_2026_11_09.py), so its rows are left out
    new_permit = fees["notes"].str.contains("Permit lookup 2026-11-09", na=False)
    return local_fees(fees[~new_permit]).set_index("geoid")["local_fee_per_unit"]


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
    # Austin: one parkland tier (medium density, $6,009.04), not all three; the 2023 impact fees of the newest
    # plat cohort ($4,800 + $2,900) are in force through 2026, so they count next to the 2026 meter, tap and
    # inspection charges ($111.30 + $200.22 + $107.90; #247); building permit $334.74
    assert totals["4805000"] == pytest.approx(6009.04 + 4800 + 2900 + 111.30 + 200.22 + 107.90 + 334.74)


def test_dallas_has_no_utility_impact_fee(fees, totals):
    # the city says it "does not charge utility impact fees" (2023-12-04 minutes): an explicit $0 row
    d = fees[
        (fees["jurisdiction_geoid"] == "4819000")
        & fees["fee_type"].str.startswith("Water and wastewater impact")
    ]
    assert len(d) == 1 and d["amount_per_unit_usd"].iloc[0] == 0
    assert totals["4819000"] == pytest.approx(465.5 + 465.5)  # tap and inspection charges only
