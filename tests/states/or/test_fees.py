"""config/fees/or.csv: Oregon SDCs for Portland, Bend, Eugene (water only) and Salem validate and add up.

Totals per unit are the sums of each component's `amount_per_unit_usd` (the fees scenario's rule), checked
against the hand sums in the fee notes (WS-OR, 2026-11-04): a 2,000 sq ft house, an 800 sq ft ADU and one
1,000 sq ft unit of a fourplex.
"""

import pytest

from lotline.config import load_fees

PORTLAND, BEND, EUGENE, SALEM = "4159000", "4105800", "4123850", "4164900"


@pytest.fixture(scope="module")
def totals():
    f = load_fees("OR")
    return f.groupby(["jurisdiction_geoid", "building_type_std"])["amount_per_unit_usd"].sum()


def test_file_validates_with_a_source_on_every_row():
    f = load_fees("OR")
    assert f["source"].str.startswith("https://").all()
    assert f["source_quote"].notna().all()
    assert set(f["jurisdiction_geoid"]) == {PORTLAND, BEND, EUGENE, SALEM}


@pytest.mark.parametrize(
    "geoid, btype, expected",
    [
        (PORTLAND, "SFD", 35885),  # water 5,483 + sewer 5,981 + storm 1,160 + transport 6,841 + parks 16,420
        (PORTLAND, "ADU", 0),  # ADU SDC waiver (10-year no-short-term-rental covenant)
        (BEND, "SFD", 34598),  # water 6,775 + sewer 6,157 + transport 10,230 + parks 11,436
        (SALEM, "SFD", 23798),
        (SALEM, "ADU", 0),  # "Accessory Dwelling Units are exempt from System Development Charges."
    ],
)
def test_per_unit_totals_match_the_hand_sums(totals, geoid, btype, expected):
    assert totals[(geoid, btype)] == pytest.approx(expected, abs=1)


def test_every_coded_total_is_under_the_handbook_50k(totals):
    assert (totals < 50000).all()


def test_eugene_house_is_its_known_sdcs_with_stormwater_in_the_range():
    """D-066 option (a): the known SDCs for a 2,000 sq ft house; the LID stormwater charge is the high end."""
    from lotline.model import fee_levels

    r = fee_levels.coded_fees(load_fees("OR")).set_index("geoid").loc[EUGENE]
    # water 2,276 + local wastewater 546.97 + 0.1325 x 2,000 + MWMC 1,990 + parks 7,880.61
    # + transportation 3,759.31 + stormwater general 789.99
    central = 2276 + (546.97 + 0.1325 * 2000) + 1990 + 7880.61 + 3759.31 + 789.99
    # high: upper-zone water 3,063 and stormwater general + LID (789.99 + 7,070.29)
    high = central - 2276 + 3063 - 789.99 + (789.99 + 7070.29)
    assert r["local_fee_per_unit"] == pytest.approx(central) == pytest.approx(17507.88)
    assert r["local_fee_low"] == pytest.approx(central)
    assert r["local_fee_high"] == pytest.approx(high) == pytest.approx(25365.17)
    assert r["local_fee_low"] > 14441.89  # above the 2026-11-04 partial lower bound
