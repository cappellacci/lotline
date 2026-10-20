"""scripts/dev/ordinance_records.py turns city-ordinance pipeline records into config/fees rows.

Synthetic records only; each expected amount is worked by hand in the comment beside it.
"""

import importlib.util
from pathlib import Path

import pytest

from lotline.config import load_fees

_spec = importlib.util.spec_from_file_location(
    "ordinance_records", Path(__file__).resolve().parents[2] / "scripts" / "dev" / "ordinance_records.py"
)
orc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(orc)

# Prototypes: single-family 2,000 sq ft, plex units 1,000 sq ft, ADU 500 sq ft, $150/sq ft.
# Valuations: SFD 300,000; U2 300,000; U3_4 600,000; ADU 75,000.
PARAMS = {"hard_cost_per_sqft_usd": 150, "single_family_sqft": 2000, "plex_unit_sqft": 1000, "adu_sqft": 500}


def item(fee_type, component, applies_to, amount, basis, quote="verbatim quote"):
    return {
        "fee_type": fee_type,
        "component": component,
        "applies_to": applies_to,
        "amount_usd": amount,
        "basis": basis,
        "quote": quote,
    }


def record(items, city="Rochester", read=True, fiscal_year="2026", effective="2026-01-01"):
    link = {"url": "https://example.gov/fees.pdf", "read": read}
    sched = {"fiscal_year": fiscal_year, "effective": effective, "link": link, "items": items}
    return {"city": city, "record": {"fee_schedules": [sched]}}


def rows(items, **kw):
    df, dropped = orc.convert([record(items, **kw)], PARAMS)
    return df, dropped


def one(df, fee_type, btype):
    hit = df[(df["fee_type"] == fee_type) & (df["building_type_std"] == btype)]
    assert len(hit) == 1, hit
    return hit.iloc[0]


VALUATION = item(
    "Building permit fee, valuation $100,001-$500,000",
    "permit",
    "per_unit_any",
    1000,
    "$1,000 for first $100,000 plus $5.00 per additional $1,000 of valuation",
)
VALUATION_BIG = item(
    "Building permit fee, valuation $500,001-$1,000,000",
    "permit",
    "duplex_to_fourplex",
    3000,
    "$3,000 for first $500,000 plus $4.00 per additional $1,000",
)
PLAN_REVIEW = item("Plan review", "permit", "per_unit_any", 0.65, "65% of the building permit fee (ratio)")


def test_only_read_and_quoted_items_are_kept():
    sac = item("SAC", "water_sewer", "per_unit_any", 2485, "per SAC unit")
    df, dropped = rows([sac, {**sac, "fee_type": "No quote", "quote": None}])
    assert list(df["fee_type"]) == ["SAC"]
    assert [d["reason"] for d in dropped] == ["no quote"]
    df, dropped = rows([sac], read=False)
    assert df.empty and dropped[0]["reason"] == "schedule link not read"


def test_totals_escrows_and_minimums_are_not_fees():
    items = [
        item("Estimated total", "other", "single_family", 13969, "city estimate"),
        item("New residential escrow (refundable)", "other", "single_family", 5000, "refundable"),
        item("Building permit minimum", "permit", "per_unit_any", 62, "Valuation $0 to $500"),
    ]
    df, dropped = rows(items)
    assert df.empty and len(dropped) == 3


def test_valuation_table_hand_worked():
    df, _ = rows([VALUATION, VALUATION_BIG])
    # SFD/OTHER: V = 2,000 x 150 = 300,000 -> 1,000 + 5 x ceil(200,000 / 1,000) = 2,000.
    assert one(df, VALUATION["fee_type"], "OTHER")["amount_per_unit_usd"] == 2000
    # Fourplex: V = 4 x 1,000 x 150 = 600,000 -> 3,000 + 4 x 100 = 3,400 per building = 850 per unit.
    assert one(df, VALUATION_BIG["fee_type"], "U3_4")["amount_per_unit_usd"] == 850
    # Duplex: V = 300,000 is below the 500,001 bracket -> not converted.
    assert pd_isna(one(df, VALUATION_BIG["fee_type"], "U2")["amount_per_unit_usd"])


def test_valuation_rounds_partial_thousands_up():
    # "or fraction thereof": V = 300,500 -> ceil(200.5) = 201 -> 1,000 + 5 x 201 = 2,005.
    df, _ = orc.convert([record([VALUATION])], {**PARAMS, "single_family_sqft": 2003.3333333333333})
    assert one(df, VALUATION["fee_type"], "OTHER")["amount_per_unit_usd"] == 2005


def test_ratio_uses_the_same_schedules_permit_fee():
    df, _ = rows([VALUATION, PLAN_REVIEW])
    # 0.65 x 2,000 = 1,300.
    r = one(df, "Plan review", "OTHER")
    assert r["amount_per_unit_usd"] == 1300 and r["basis"] == "other"
    # Without a converted permit fee in the schedule it stays blank.
    df, _ = rows([PLAN_REVIEW])
    assert pd_isna(one(df, "Plan review", "OTHER")["amount_per_unit_usd"])


def test_state_surcharge_is_pct_of_value():
    s = item(
        "State surcharge", "other", "per_unit_any", 0.0005, "0.0005 x valuation (amount_usd is the rate)"
    )
    r = one(rows([s])[0], "State surcharge", "OTHER")
    # 0.0005 x 300,000 = 150.
    assert (r["basis"], r["pct_of_value"], r["amount_per_unit_usd"]) == ("pct_of_value", 0.05, 150)


@pytest.mark.parametrize(
    ("basis", "rule", "per_unit"),
    [
        ("per SAC unit (1 unit per typical dwelling)", "per_lue", 700),
        ("$800 per Met Council SAC unit", "per_lue", 700),
        ("per tap (3/4-inch: $2,171)", "per_lue", 700),
        ("per dwelling unit", "per_unit", 700),
        ("per unit: 2.75 persons x 0.00955 acre x $75,000/acre", "per_unit", 700),
        ("flat per permit", "flat", 700),
        ("per acre; development cost", "land_based", None),
        ("per sq ft of plat area", "land_based", None),
        ("fee plus $5,000 escrow", "conditional", None),
        ("Per dwelling unit, charged on subdivisions", "conditional", None),
        ("lump sum, when the city installs the tap", "conditional", None),
    ],
)
def test_basis_rules(basis, rule, per_unit):
    r = one(rows([item("Fee", "impact", "single_family", 700, basis)])[0], "Fee", "SFD")
    assert f"rule {rule}" in r["notes"]
    assert pd_isna(r["amount_per_unit_usd"]) if per_unit is None else r["amount_per_unit_usd"] == per_unit


@pytest.mark.parametrize(
    ("applies_to", "text", "expected"),
    [
        ("single_family", "per unit", ["SFD"]),
        ("single_family", "single family/duplex/townhouse", ["SFD", "U2"]),
        ("adu", "flat", ["ADU"]),
        ("per_unit_any", "per unit", ["OTHER"]),
        ("duplex_to_fourplex", "multi-family dwelling (2+ units)", ["U2", "U3_4"]),
        ("duplex_to_fourplex", "park dedication (duplex) per unit", ["U2"]),
        ("duplex_to_fourplex", "multifamily with three units or more", ["U3_4"]),
        ("duplex_to_fourplex", "city sac, multiple (80% of single family)", ["U3_4"]),
    ],
)
def test_building_types(applies_to, text, expected):
    assert orc.building_types(applies_to, text) == expected


def test_size_band_counts_only_matching_prototype():
    small = item(
        "Thoroughfare fee, single family 1,000-1,999 sq ft", "impact", "single_family", 2180, "per unit"
    )
    big = item(
        "Thoroughfare fee, single family 2,000-2,999 sq ft", "impact", "single_family", 2417, "per unit"
    )
    df, _ = rows([small, big])
    assert pd_isna(one(df, small["fee_type"], "SFD")["amount_per_unit_usd"])  # prototype is 2,000 sq ft
    assert one(df, big["fee_type"], "SFD")["amount_per_unit_usd"] == 2417


def test_whole_building_amount_is_split_per_unit():
    caf = item("CAF, two-family dwelling", "water_sewer", "duplex_to_fourplex", 1880, "2 CAF units x $940")
    df, _ = rows([caf], city="Duluth")
    assert one(df, caf["fee_type"], "U2")["amount_per_unit_usd"] == 940


@pytest.mark.parametrize(
    ("label", "effective", "year"),
    [
        ("2026", None, 2026),
        ("2023-current (latest schedule posted)", "2023-02-25", 2023),
        ("FY2027 (current)", "2026-07-01 to 2027-06-30", 2026),
        ("current (handout, about Nov 2025)", None, 2025),
        ("current (Met Council SAC, regional)", None, orc.READ_YEAR),
    ],
)
def test_schedule_year(label, effective, year):
    assert orc.schedule_year(label, effective)[0] == year


def test_citation_and_dollar_year():
    df, _ = rows([item("SAC", "water_sewer", "per_unit_any", 2485, "per SAC unit", quote="x" * 400)])
    r = df.iloc[0]
    assert r["source"] == "https://example.gov/fees.pdf" and len(r["source_quote"]) == 300
    assert r["dollar_year"] == r["year"] == 2026 and r["effective_date"] == "2026-01-01"
    assert r["verified_by"] is None and orc.CHECKER_NOTE in r["notes"]


def test_written_csv_validates(tmp_path):
    (tmp_path / "fees").mkdir()
    df, _ = rows([VALUATION, PLAN_REVIEW, item("SAC", "water_sewer", "per_unit_any", 2485, "per SAC unit")])
    orc.write(df, tmp_path / "fees")
    assert len(load_fees("MN", tmp_path)) == 3


@pytest.mark.parametrize("state", ["MN", "NC", "TX"])
def test_committed_fee_tables_validate(state):
    assert load_fees(state) is not None


def pd_isna(x) -> bool:
    return x is None or x != x
