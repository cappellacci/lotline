"""The AMI strip's arithmetic against hand-worked examples (docs/research/lotline-ami-method.md)."""

import numpy as np
import pandas as pd
import pytest

from lotline.model import affordability as a
from lotline.model import proforma


def test_rent_to_income_hand_example():
    assert a.rent_to_income(1500) == pytest.approx(60_000)


def test_household_size_is_one_and_a_half_per_bedroom():
    assert a.household_size(1) == 1.5 and a.household_size(2) == 3.0 and a.household_size(3) == 4.5
    assert a.household_size(0) == 1.0  # a studio


def test_size_factor_means_the_two_sizes_around_a_fraction():
    f = a.size_factors()  # HUD's published factors
    assert a.size_factor(1.5, f) == pytest.approx(0.75)
    assert a.size_factor(3, f) == pytest.approx(0.90)
    assert a.size_factor(4.5, f) == pytest.approx(1.04)


def test_size_factors_come_from_the_file_where_present():
    f = a.size_factors({1: 46_350, 2: 52_950, 3: 59_550, 4: 66_150, 5: 71_450})
    assert f[1] == pytest.approx(46_350 / 66_150) and f[4] == 1.0


def test_ami_share_hand_example():
    # $60,000 on a 4-person MFI of $132,300: 1 bedroom (0.75) -> 60%; 2 bedrooms (0.90) -> 50%
    assert a.ami_share(60_000, 132_300, 0.75) == pytest.approx(0.6047, abs=1e-4)
    assert a.ami_share(60_000, 132_300, 0.90) == pytest.approx(0.5039, abs=1e-4)


def test_break_even_adu_hand_worked_pro_forma():
    # hard 165 x 1.15 x 800 = 151,800; soft 30,360; interest 0.085 x 0.75 x 0.5 x 182,160 = 5,806.35
    cost = 151_800 + 30_360 + 5_806.35
    per_dollar = 12 * 0.95 * 0.65 / 0.055
    assert a.break_even("adu", 0.0) == pytest.approx(cost / per_dollar)
    assert a.break_even("adu", 0.0) == pytest.approx(1395.16, abs=0.01)


def test_break_even_value_equals_cost_in_the_pro_forma():
    for home_type, fee in (("adu", 0.0), ("plex_unit", 20_000.0), ("house", 30_000.0)):
        v = float(a.break_even(home_type, fee))
        proto = a.PROTOTYPE[home_type]
        p = proforma.central_params()
        size = p[proforma.PROTOTYPES[proto][1]]
        if home_type == "house":
            pf = proforma.pro_forma(proto, "for_sale", proforma.Market(v / size, 0.0), fee)
        else:
            pf = proforma.pro_forma(proto, "rental", proforma.Market(0.0, v / size), fee)
        assert pf.value == pytest.approx(pf.hard_cost + pf.soft_cost + pf.fees + pf.financing)


def test_break_even_moves_with_the_fee():
    lo, hi = a.break_even("plex_unit", 10_000.0), a.break_even("plex_unit", 30_000.0)
    assert hi > lo
    # per $1 of fee per unit: 1 + rate x years (paid at permit), over the value of $1 a month
    per_dollar = 12 * 0.95 * 0.65 / 0.055
    assert hi - lo == pytest.approx(20_000 * (1 + 0.085 * 0.75) / per_dollar)


def test_mortgage_and_owner_cost_hand_examples():
    assert float(a.monthly_payment(300_000, 6.0)) == pytest.approx(1798.65, abs=0.01)
    p = {"down_payment_share": 0.10, "mortgage_term_years": 30, "property_tax_rate": 0.01,
         "home_insurance_rate": 0.004}  # fmt: skip
    assert float(a.owner_monthly_cost(400_000, 6.0, p)) == pytest.approx(2158.38 + 333.33 + 133.33, abs=0.02)


def test_weighted_mean_hand_example():
    assert a.weighted_mean([1, 3], [3, 1]) == pytest.approx(1.5)


def test_fee_cases_follow_the_fee_scenario():
    places = pd.DataFrame({"fee_plex": [20_000.0], "fee_house": [40_000.0]})
    p = {"handbook_fee_per_unit_usd": 50_000.0, "handbook_fee_cut_share": 0.5, "land_capture_share": 0.2}
    assert a.fee_for_case("house", "current", places, p)[0] == 40_000
    assert a.fee_for_case("house", "fees_local_half", places, p)[0] == pytest.approx(40_000 - 0.8 * 20_000)
    assert a.fee_for_case("plex_unit", "fees", places, p)[0] == pytest.approx(50_000 - 0.8 * 25_000)
    assert a.fee_for_case("adu", "fees", places, p)[0] == 0  # the fee scenario does not touch ADUs


def _places():
    return pd.DataFrame(
        {
            "geoid": ["1", "2", "3"],
            "place_type": ["core", "suburb", "suburb"],
            "rent": [1500.0, 1200.0, 1000.0],
            "home_value": [400_000.0, 300_000.0, 250_000.0],
            "mfi": [132_300.0, 132_300.0, 100_000.0],
            **{f"l50_{n}": [np.nan] * 3 for n in a.SIZES},
            "fee_house": [30_000.0, 20_000.0, 10_000.0],
            "fee_plex": [20_000.0, 15_000.0, 8_000.0],
            "weight_adu": [10.0, 5.0, 0.0],
            "weight_mm": [0.0, 0.0, 0.0],
        }
    )


def test_table_rows_ranges_and_weights():
    t = a.table("NC", _places(), n=200, seed=1)
    assert set(t["home_type"]) == set(a.HOME_TYPES)
    assert set(t["fee_case"][t["rent_kind"] == "market"]) == {"current"}
    assert ((t["value_p10"] <= t["value"]) & (t["value"] <= t["value_p90"])).all()
    assert ((t["ami_share_p10"] <= t["ami_share"]) & (t["ami_share"] <= t["ami_share_p90"])).all()
    core = t.query("home_type == 'adu' and place_type == 'core' and rent_kind == 'market'").iloc[0]
    # one core place at $1,500 x ratio (median 1.0): income ~ $60,000, ~60% AMI at the 1.5-person factor
    assert core["value"] == pytest.approx(1500, rel=0.05)
    assert core["ami_share"] == pytest.approx(0.6047, rel=0.05)
    # the suburb's ADU weight sits all on place 2 (place 3 adds none); MM weights are all zero -> equal
    sub = t.query("home_type == 'adu' and place_type == 'suburb' and rent_kind == 'market'").iloc[0]
    assert sub["value"] == pytest.approx(1200, rel=0.05) and sub["weighting"] == "homes_added"
    plex = t.query("home_type == 'plex_unit' and place_type == 'state' and rent_kind == 'market'").iloc[0]
    assert plex["weighting"] == "places_equal"


def test_table_break_even_falls_when_fees_are_cut():
    t = a.table("NC", _places(), n=100, seed=1).set_index(
        ["home_type", "place_type", "rent_kind", "fee_case"]
    )
    now = t.loc[("house", "state", "break_even", "current"), "value"]
    cut = t.loc[("house", "state", "break_even", "fees_local_half"), "value"]
    assert cut < now
    assert t.loc[("adu", "state", "break_even", "current"), "value"] == pytest.approx(
        t.loc[("adu", "state", "break_even", "fees_local_half"), "value"]
    )


def test_table_without_mfi_is_empty():
    assert a.table("NC", _places().assign(mfi=np.nan), n=10).empty
