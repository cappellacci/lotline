"""The app's "what builders pay today" block (dashboard/fees.py): hand-worked checks on a synthetic table."""

import pandas as pd
import pytest

from lotline.dashboard import fees as fs
from lotline.model import pencil_out

COLS = [
    "state",
    "jurisdiction_geoid",
    "year",
    "in_force_through",
    "fee_component",
    "building_type_std",
    "amount_per_unit_usd",
    "amount_per_unit_low_usd",
    "amount_per_unit_high_usd",
    "dollar_year",
]


def table():
    """Five MN places, permit 1,000·i and water/sewer 1,000·(i+1); place 6 has only an impact fee of 700;
    place 1 has its own ADU water/sewer charge of 500."""
    out = []
    for i in range(1, 6):
        out.append(("MN", str(i), 2026, None, "permit", "SFD", 1000.0 * i, None, None, 2026))
        out.append(("MN", str(i), 2026, None, "water_sewer", "SFD", 1000.0 * (i + 1), None, None, 2026))
    out.append(("MN", "6", 2026, None, "impact", "SFD", 700.0, None, None, 2026))
    out.append(("MN", "1", 2026, None, "water_sewer", "ADU", 500.0, None, None, 2026))
    df = pd.DataFrame(out, columns=COLS)
    df["in_force_through"] = df["in_force_through"].astype("Int64")
    return df


def test_house_fee_parts_fill_and_per_lot():
    s = fs.fee_sample("MN", table(), names={"1": "One city"})
    by = {p["geoid"]: p for p in s["places"]}
    one = by["1"]
    assert one["name"] == "One city" and by["2"]["name"] == "2"  # name from the lookup, else the geoid
    # place 1: permit 1,000 + water/sewer 2,000 = 3,000, all coded
    assert one["types"]["house"]["fee"] == 3000 and one["types"]["house"]["filled"] is None
    assert one["components"] == {"permit": 1000, "water_sewer": 2000}
    # a fourplex pays on each of its 4 homes: per lot = 4 x per unit (here the house fee, from SFD)
    four = one["types"]["fourplex"]
    assert four["units"] == 4 and four["per_lot"] == pytest.approx(4 * four["fee"])
    assert four["from_house"] is True
    # place 6: impact 700 coded; permit and water/sewer filled from the state medians (3,000 and 4,000)
    six = by["6"]
    assert six["types"]["house"]["fee"] == pytest.approx(700 + 3000 + 4000)
    assert six["components"] == {"impact": 700, "filled": 7000}
    assert six["types"]["house"]["filled"].startswith("local + filled")
    # ADU: place 1's own water/sewer charge replaces the house's (1,000 permit from SFD + 500)
    assert one["types"]["adu"]["fee"] == 1500 and by["2"]["types"]["adu"]["fee"] == 5000
    # sorted by house fee, highest first; summary over places
    # houses: 3,000 5,000 7,000 9,000 11,000 and place 6's 7,700 -> median (7,000 + 7,700) / 2 = 7,350
    assert [p["geoid"] for p in s["places"]][:3] == ["5", "4", "6"]
    assert s["summary"]["house"] == {"places": 6, "min": 3000, "median": 7350, "max": 11000}
    assert s["dollars"] == "nominal" and s["handbook_fee"] == 50000 and s["handbook_cut_share"] == 0.5


def test_cost_share_is_fee_per_lot_over_building_cost():
    """Share of cost = fee per lot / (hard + soft + fees + interest); it does not depend on home value."""
    p = pencil_out.central_params()
    a = fs.cost_shares(8000, p)
    for t, units in (("SFD", 1), ("U2", 2), ("U3_4", 4)):
        assert a[t]["units"] == units and a[t]["per_lot"] == pytest.approx(8000 * units)
        r = pencil_out.row(t, "for_sale", "now", pencil_out.market(900_000, 4_000, p), 8000, None, p)
        assert a[t]["share"] == pytest.approx(r["fee_share_of_cost"])
    assert a["U3_4"]["share"] > a["SFD"]["share"]


def test_state_with_no_rows_is_none():
    assert fs.fee_sample("TX", table()) is None
