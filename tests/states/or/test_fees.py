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


def test_eugene_stays_on_the_handbook_prior_until_its_bill_is_complete():
    """Transportation (per trip) can't be priced per home from the order, so no Eugene row has a per-unit
    amount and the fees scenario falls back to the national prior instead of a partial bill."""
    from lotline.model.scenarios.fees import local_fees

    f = load_fees("OR")
    eugene = f[f["jurisdiction_geoid"] == EUGENE]
    assert len(eugene) > 20 and eugene["amount_per_unit_usd"].isna().all()
    assert EUGENE not in set(local_fees(f)["geoid"])
