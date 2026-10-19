"""The pro forma does what the method says (model/proforma.py; methods review §2a).

Hand-worked examples use round test parameters (below), one market and a $10,000 fee per unit:

    hard cost $200/sq ft; commercial-code step +10%; ADU premium +20%; soft cost 20% of hard;
    loan rate 8%; half of hard + soft borrowed on average; build time 1.0 yr (IRC) or 1.5 yr (IBC);
    fees paid at permit (carried); selling costs 5%; vacancy 5%; operating costs 35%; cap rate 5%;
    profit 15% of value (ADU 10%). Market: sale price $350/sq ft; rent $2.00/sq ft/month.

Per sq ft (S = total sq ft, F = total fees):
    for-sale value = 350 × 0.95 = 332.5 S            rental value = 2 × 12 × 0.95 × 0.65 / 0.05 = 296.4 S
    IRC: hard 200 S, soft 40 S, financing 0.08 × 1.0 × (120 S + F) = 9.6 S + 0.08 F
    IBC: hard 220 S, soft 44 S, financing 0.08 × 1.5 × (132 S + F) = 15.84 S + 0.12 F
    ADU: hard 240 S, soft 48 S, financing 0.08 × 1.0 × (144 S + F) = 11.52 S + 0.08 F

1. Single-family, for sale, S = 2,000, F = 10,000:
   665,000 − 400,000 − 80,000 − 10,000 − 20,000 − 99,750 (15% × 665,000) = 55,250
2. Duplex, for sale, S = 2 × 1,000, F = 20,000: 665,000 − 400,000 − 80,000 − 20,000 − 20,800 − 99,750 = 44,450
3. Triplex, for sale, IBC, S = 3,000, F = 30,000:
   997,500 − 660,000 − 132,000 − 30,000 − 51,120 (0.12 × 426,000) − 149,625 = −25,245
   Same triplex under the IRC: 997,500 − 600,000 − 120,000 − 30,000 − 31,200 − 149,625 = 66,675
4. Fourplex, rental, IBC, S = 4,000, F = 40,000:
   1,185,600 − 880,000 − 176,000 − 40,000 − 68,160 (0.12 × 568,000) − 177,840 = −156,400
5. Townhouse row (4 units), for sale, IRC, S = 4 × 1,500 = 6,000, F = 40,000:
   1,995,000 − 1,200,000 − 240,000 − 40,000 − 60,800 (0.08 × 760,000) − 299,250 = 154,950
6. 6-unit building, rental, IBC, S = 6,000, F = 60,000:
   1,778,400 − 1,320,000 − 264,000 − 60,000 − 102,240 (0.12 × 852,000) − 266,760 = −234,600
7. ADU, rental, S = 800, F = 10,000:
   237,120 − 192,000 − 38,400 − 10,000 − 10,016 (0.08 × 125,200) − 23,712 (10% × 237,120) = −37,008
"""

import pytest

from lotline.config import load_params
from lotline.model import proforma as pf

MARKET = pf.Market(sale_price_per_sqft=350, monthly_rent_per_sqft=2.0)
FEE = 10_000


@pytest.fixture
def params():
    p = pf.central_params()
    p.update(
        hard_cost_per_sqft_usd=200, code_step_premium=0.10, adu_hard_cost_premium=0.20, soft_cost_share=0.20,
        construction_loan_rate=0.08, average_draw_share=0.5, construction_years_irc=1.0,
        construction_years_ibc=1.5, fee_paid_at_permit=1.0, sale_cost_share=0.05, rental_vacancy_rate=0.05,
        operating_expense_share=0.35, cap_rate=0.05, developer_margin=0.15, adu_margin=0.10,
        adu_sqft=800, single_family_sqft=2000, plex_unit_sqft=1000, townhouse_sqft=1500, townhouse_units=4,
        small_multifamily_units=6, triplex_under_irc=0, existing_use_margin=0.10,
    )  # fmt: skip
    return p


@pytest.mark.parametrize(
    ("prototype", "tenure", "expected"),
    [
        ("single_family", "for_sale", 55_250),
        ("duplex", "for_sale", 44_450),
        ("triplex", "for_sale", -25_245),
        ("fourplex", "rental", -156_400),
        ("townhouse", "for_sale", 154_950),
        ("small_multifamily", "rental", -234_600),
        ("adu", "rental", -37_008),
    ],
)
def test_hand_worked_examples(params, prototype, tenure, expected):
    assert pf.residual_land_value(prototype, tenure, MARKET, FEE, params) == pytest.approx(expected)


def test_line_items_add_up(params):
    r = pf.pro_forma("single_family", "for_sale", MARKET, FEE, params)
    assert (r.value, r.hard_cost, r.soft_cost, r.fees, r.financing, r.profit) == pytest.approx(
        (665_000, 400_000, 80_000, 10_000, 20_000, 99_750)
    )
    assert r.residual_land_value_per_unit == pytest.approx(55_250)


def test_code_step_at_three_units(params):
    codes = {name: pf.building_code(name, params) for name in pf.PROTOTYPES}
    assert codes == {
        "adu": "IRC", "single_family": "IRC", "duplex": "IRC", "townhouse": "IRC",
        "triplex": "IBC", "fourplex": "IBC", "small_multifamily": "IBC",
    }  # fmt: skip
    ibc = pf.residual_land_value("triplex", "for_sale", MARKET, FEE, params)
    params["triplex_under_irc"] = 1  # e.g. Austin PM2024-0002
    assert pf.building_code("triplex", params) == "IRC"
    irc = pf.residual_land_value("triplex", "for_sale", MARKET, FEE, params)
    assert irc - ibc == pytest.approx(66_675 - -25_245)


@pytest.mark.parametrize("prototype", list(pf.PROTOTYPES))
@pytest.mark.parametrize("tenure", pf.TENURES)
def test_fee_cut_moves_rlv_by_fee_times_units(params, prototype, tenure):
    """Handbook: −50% of $50,000 = −$25,000 per unit. Fees paid at completion: exactly $25,000 × units.
    Paid at permit: plus a year (IRC) or 1.5 years (IBC) of interest on it at 8%."""
    cut = 50_000 * 0.5
    units = pf.pro_forma(prototype, tenure, MARKET, FEE, params).units
    params["fee_paid_at_permit"] = 0
    gain = pf.residual_land_value(prototype, tenure, MARKET, 50_000 - cut, params) - pf.residual_land_value(
        prototype, tenure, MARKET, 50_000, params
    )
    assert gain == pytest.approx(cut * units)
    params["fee_paid_at_permit"] = 1
    years = 1.5 if pf.building_code(prototype, params) == "IBC" else 1.0
    gain = pf.residual_land_value(prototype, tenure, MARKET, 50_000 - cut, params) - pf.residual_land_value(
        prototype, tenure, MARKET, 50_000, params
    )
    assert gain == pytest.approx(cut * units * (1 + 0.08 * years))


def test_land_capture_shrinks_the_builders_saving():
    assert pf.builder_fee_saving(25_000, land_capture_share=0.5) == 12_500
    assert pf.builder_fee_saving(25_000, land_capture_share=0.0) == 25_000
    lam = load_params("fees")["land_capture_share"].value
    assert pf.builder_fee_saving(25_000) == pytest.approx((1 - lam) * 25_000)


@pytest.mark.parametrize("prototype", list(pf.PROTOTYPES))
@pytest.mark.parametrize("tenure", pf.TENURES)
def test_monotone_in_price_rent_and_fees(params, prototype, tenure):
    def rlv(price=350, rent=2.0, fee=FEE):
        return pf.residual_land_value(prototype, tenure, pf.Market(price, rent), fee, params)

    assert rlv(price=400, rent=2.5) > rlv()
    assert rlv(fee=20_000) < rlv()


def test_feasibility_against_existing_use(params):
    assert pf.is_feasible(55_250, existing_use_value=50_000, params=params)  # needs 55,000
    assert not pf.is_feasible(54_999, existing_use_value=50_000, params=params)
    assert pf.is_feasible(0, existing_use_value=0, params=params)  # ADU: the house stays


def test_parameters_load_with_sources_and_ranges():
    specs = load_params("proforma")
    needed = {key for _, key, _ in pf.PROTOTYPES.values()} | {"hard_cost_per_sqft_usd", "cap_rate"}
    assert needed <= specs.keys()
    assert (specs["adu_sqft"].low, specs["adu_sqft"].high) == (600, 1000)  # brief; Handbook ADU >= 600
    assert specs["triplex_under_irc"].value == 0  # commercial code is the general rule
    assert all(s.low < s.high for k, s in specs.items() if k not in pf.NOT_SAMPLED)


def test_central_run_uses_the_config():
    r = pf.pro_forma("duplex", "for_sale", MARKET, FEE)
    assert r.hard_cost == pytest.approx(load_params("proforma")["hard_cost_per_sqft_usd"].value * r.sqft)


def test_uncertainty_range_is_ordered_and_reproducible():
    a = pf.rlv_range("duplex", "for_sale", MARKET, FEE, draws=300, seed=1)
    assert a["p10"] < a["p50"] < a["p90"]
    assert a == pf.rlv_range("duplex", "for_sale", MARKET, FEE, draws=300, seed=1)


def test_unknown_prototype_is_an_error(params):
    with pytest.raises(ValueError):
        pf.residual_land_value("tower", "for_sale", MARKET, FEE, params)
