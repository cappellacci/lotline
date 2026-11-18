# ruff: noqa: E501  (hand-worked examples)
"""Prototype pricing, hand-worked (DESIGN.md table of basis kinds)."""

import pytest
from pydantic import ValidationError

from lotline.rule_agents.fees.prototype import price, prototypes


def test_valuations_match_ordinance_records(protos):
    # 2,150 x $165; 2 x 1,000 x $165; 4 x 1,000 x $165; 800 x $165
    assert protos["SFD"].valuation == 354_750
    assert protos["U2"].valuation == 330_000
    assert protos["U3_4"].valuation == 660_000
    assert protos["ADU"].valuation == 132_000
    assert protos["OTHER"] == protos["OTHER"] and protos["OTHER"].valuation == 354_750


def test_config_prototypes_load():
    # the real proforma.yaml has the keys the helper needs
    assert set(prototypes()) == {"SFD", "U2", "U3_4", "ADU", "OTHER"}


def test_valuation_table_apple_valley(protos, make_item):
    # "$1,302.50 for the first $100,000.00, plus $7.40 for each additional $1,000.00": house
    # 1,302.50 + 7.40 x ceil((354,750 - 100,000) / 1,000) = 1,302.50 + 7.40 x 255 = 3,189.50 (as in mn.csv)
    it = make_item(
        basis_kind="valuation_table",
        amount=None,
        bracket_base=1302.5,
        bracket_start=100_000,
        bracket_end=500_000,
        rate_per_1000=7.40,
    )
    assert price(it, protos["SFD"]).amount_per_unit == pytest.approx(3189.50)
    # duplex: 1,302.50 + 7.40 x 230 = 3,004.50 for the building, 1,502.25 per unit
    assert price(it, protos["U2"]).amount_per_unit == pytest.approx(1502.25)
    # fourplex valuation $660,000 is outside the bracket: not priced
    assert price(it, protos["U3_4"]).amount_per_unit is None


def test_share_and_pct(protos, make_item):
    # plan review 65% of $3,189.50 = $2,073.175; MN surcharge 0.05% x $354,750 = $177.375
    share = make_item(basis_kind="share_of", amount=None, pct=65, share_of="permit")
    assert price(share, protos["SFD"], 3189.50).amount_per_unit == pytest.approx(2073.175)
    assert price(share, protos["SFD"]).amount_per_unit is None
    pct = make_item(basis_kind="pct_of_value", amount=None, pct=0.05)
    assert price(pct, protos["SFD"]).amount_per_unit == pytest.approx(177.375)


def test_meter_lue_sqft_building(protos, make_item):
    # one meter per unit central (D-069): $3,677; master meter $9,192 for a fourplex = $2,298 per unit (low)
    m = price(make_item(basis_kind="per_meter", amount=3677, master_meter_amount=9192), protos["U3_4"])
    assert (m.amount_per_unit, m.low, m.high) == (3677, 2298, 3677)
    # SAC $2,485 x 0.75 SAC units per fourplex unit = $1,863.75
    assert price(
        make_item(basis_kind="per_lue", amount=2485, units_per_dwelling=0.75), protos["U3_4"]
    ).amount_per_unit == pytest.approx(1863.75)
    assert price(make_item(basis_kind="per_lue", amount=2485), protos["SFD"]).amount_per_unit is None
    # $0.50 per sq ft x 2,150 = $1,075; $85 per building / 4 units = $21.25
    assert price(
        make_item(basis_kind="per_sqft", amount=0.5), protos["SFD"]
    ).amount_per_unit == pytest.approx(1075)
    assert price(
        make_item(basis_kind="per_building", amount=85), protos["U3_4"]
    ).amount_per_unit == pytest.approx(21.25)


def test_bedroom_and_trip(protos, make_item):
    # Brunswick County: $3,282 per bedroom -> 3-bedroom house $9,846, 2-bedroom plex unit $6,564 (plex-utility pass)
    b = make_item(basis_kind="per_bedroom", amount=3282)
    assert price(b, protos["SFD"]).amount_per_unit == 9846
    assert price(b, protos["U2"]).amount_per_unit == 6564
    # Eugene transportation SDC: $3,759.31 per trip x 0.52 trips for an ADU = $1,954.84
    t = make_item(basis_kind="per_trip", amount=3759.31, quantity_per_unit=0.52, building_type="ADU")
    assert round(price(t, protos["ADU"]).amount_per_unit, 2) == 1954.84


def test_unpriced_kinds(protos, make_item):
    for kind in ("conditional", "per_acre", "excluded"):
        assert price(make_item(basis_kind=kind, amount=None), protos["SFD"]).amount_per_unit is None


def test_item_requires_numbers_for_its_basis(make_item):
    with pytest.raises(ValidationError):
        make_item(basis_kind="valuation_table", amount=None)
    with pytest.raises(ValidationError):
        make_item(basis_kind="per_unit", amount=None)
    with pytest.raises(ValidationError):
        make_item(group_id="g1")  # a group needs its kind
