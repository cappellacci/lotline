"""Pencil-out table (model/pencil_out.py): hand-worked pro formas for a duplex and a fourplex."""

import numpy as np
import pytest

from lotline.model import pencil_out as po

# Round numbers so every line can be checked by hand.
P = {
    "single_family_sqft": 2000.0,
    "plex_unit_sqft": 1000.0,
    "adu_sqft": 800.0,
    "townhouse_sqft": 1500.0,
    "townhouse_units": 4.0,
    "small_multifamily_units": 6.0,
    "hard_cost_per_sqft_usd": 200.0,
    "code_step_premium": 0.10,
    "triplex_under_irc": 0.0,
    "adu_hard_cost_premium": 0.0,
    "soft_cost_share": 0.20,
    "construction_loan_rate": 0.08,
    "average_draw_share": 0.5,
    "construction_years_irc": 1.0,
    "construction_years_ibc": 1.5,
    "fee_paid_at_permit": 1.0,
    "sale_cost_share": 0.05,
    "rental_vacancy_rate": 0.05,
    "operating_expense_share": 0.35,
    "cap_rate": 0.06,
    "developer_margin": 0.15,
    "adu_margin": 0.10,
    "existing_use_margin": 0.10,
    "handbook_fee_per_unit_usd": 50000.0,
    "handbook_fee_cut_share": 0.5,
}


def test_market_by_hand():
    m = po.market(800_000, 2_000, P)
    assert m.sale_price_per_sqft == 400  # 800,000 / 2,000 sq ft
    assert m.monthly_rent_per_sqft == 2  # 2,000 a month / 1,000 sq ft


def test_case_fees():
    assert [po.case_fee(c, 10_000, P) for c in po.CASES] == [10_000, 5_000, 50_000, 25_000]
    with pytest.raises(ValueError):
        po.case_fee("double", 10_000, P)


def test_duplex_for_sale_by_hand():
    # 2 × 1,000 sq ft, residential code, $400 a sq ft, fee $10,000 a unit.
    # value 400 × 2,000 × 0.95 = 760,000; hard 200 × 2,000 = 400,000; soft 80,000; fees 20,000;
    # interest 0.08 × 1 yr × (0.5 × 480,000 + 20,000) = 20,800; profit 0.15 × 760,000 = 114,000.
    # residual land value = 760,000 − 400,000 − 80,000 − 20,000 − 20,800 − 114,000 = 125,200.
    r = po.row("U2", "for_sale", "now", po.market(800_000, 2_000, P), 10_000, 100_000, P)
    assert r["fee_per_lot"] == 20_000
    assert r["rlv_per_lot"] == pytest.approx(125_200) and r["rlv_per_unit"] == pytest.approx(62_600)
    assert r["cost_per_unit"] == pytest.approx((400_000 + 80_000 + 20_000 + 20_800) / 2)  # 260,400
    assert r["fee_share_of_cost"] == pytest.approx(20_000 / 520_800)
    assert r["pencils"] is True  # 125,200 >= 100,000 × 1.10


def test_cutting_the_fee_raises_land_value_by_the_cut_plus_interest():
    t = po.table(800_000, 2_000, {"SFD": 10_000, "U2": 10_000, "U3_4": 10_000}, 100_000, P)
    d = t[(t["building_type"] == "U2") & (t["tenure"] == "for_sale")].set_index("case")
    # fee 5,000 a unit: fees 10,000, interest 0.08 × (240,000 + 10,000) = 20,000 -> RLV 136,000.
    assert d.loc["local_half", "rlv_per_lot"] == pytest.approx(136_000)
    # the $10,000 cut per lot plus the $800 of interest on it
    assert d.loc["local_half", "rlv_per_lot"] - d.loc["now", "rlv_per_lot"] == pytest.approx(10_800)


def test_fourplex_pays_four_fees_under_the_commercial_code():
    # 4 × 1,000 sq ft, commercial code: $220 a sq ft, 1.5 years. hard 880,000; soft 176,000; fees 40,000;
    # interest 0.08 × 1.5 × (0.5 × 1,056,000 + 40,000) = 68,160; value 1,520,000; profit 228,000.
    t = po.table(800_000, 2_000, {"U3_4": 10_000}, None, P)
    r = t[(t["building_type"] == "U3_4") & (t["tenure"] == "for_sale") & (t["case"] == "now")].iloc[0]
    assert r["fee_per_lot"] == 40_000 and r["units"] == 4
    assert r["rlv_per_lot"] == pytest.approx(1_520_000 - 880_000 - 176_000 - 40_000 - 68_160 - 228_000)
    assert np.isnan(r["lot_value"]) and r["pencils"] is None


def test_rental_value_by_hand():
    # house for rent at $2 a sq ft a month: 2 × 12 × 2,000 × 0.95 = 45,600; × 0.65 = 29,640; / 0.06 = 494,000.
    t = po.table(800_000, 2_000, {"SFD": 0.0}, None, P, cases=("now",))
    r = t[(t["building_type"] == "SFD") & (t["tenure"] == "rental")].iloc[0]
    assert r["value_per_unit"] == pytest.approx(494_000)


def test_type_without_a_local_fee_shows_only_the_handbook_cases():
    t = po.table(800_000, 2_000, {"SFD": 9_000}, None, P)
    assert set(t.loc[t["building_type"] == "SFD", "case"]) == set(po.CASES)
    assert set(t.loc[t["building_type"] == "U2", "case"]) == {"handbook_50k", "handbook_25k"}
    assert len(t) == 3 * 2 * 4 - 2 * 2 * 2  # houses: 8 rows; duplex and fourplex: 4 each
