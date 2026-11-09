"""Local fee levels (model/fee_levels.py): hand-worked checks of each rule in the module docstring."""

import numpy as np
import pandas as pd
import pytest

from lotline.model import fee_levels as fl

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


def rows(*r):
    df = pd.DataFrame(list(r), columns=COLS)
    df["in_force_through"] = df["in_force_through"].astype("Int64")
    return df


def one(df, geoid):
    return df.set_index("geoid").loc[geoid]


def test_older_row_in_force_still_counts():
    # Austin-like: 2023 impact fees ($4,800 + $2,900) in force through 2026, next to 2026 meter fees ($400).
    f = rows(
        ("TX", "1", 2023, 2026, "water_sewer", "SFD", 4800.0, None, None, 2023),
        ("TX", "1", 2023, 2026, "water_sewer", "SFD", 2900.0, None, None, 2023),
        ("TX", "1", 2026, None, "water_sewer", "SFD", 400.0, None, None, 2026),
        # A plain older row with no in-force year is superseded by the 2026 row.
        ("TX", "2", 2023, None, "water_sewer", "SFD", 5000.0, None, None, 2023),
        ("TX", "2", 2026, None, "water_sewer", "SFD", 400.0, None, None, 2026),
    )
    out = fl.coded_fees(f)
    assert one(out, "1")["local_fee_per_unit"] == 8100  # 4,800 + 2,900 + 400
    assert one(out, "2")["local_fee_per_unit"] == 400


def test_range_sums_rows_lows_and_highs():
    # Water $4,908 (4,749-5,097) + wastewater $2,073 (1,171-3,451) + permit $1,000 (no range).
    f = rows(
        ("TX", "1", 2026, None, "water_sewer", "SFD", 4908.0, 4749.0, 5097.0, 2026),
        ("TX", "1", 2026, None, "water_sewer", "SFD", 2073.0, 1171.0, 3451.0, 2026),
        ("TX", "1", 2026, None, "permit", "OTHER", 1000.0, None, None, 2026),
    )
    r = one(fl.coded_fees(f), "1")
    assert (r["local_fee_low"], r["local_fee_per_unit"], r["local_fee_high"]) == (6920, 7981, 9548)


def test_deflation_to_2025_dollars_and_newer_years_capped():
    index = pd.Series({2020: 100.0, 2025: 125.0})
    f = rows(
        ("MN", "1", 2020, None, "permit", "SFD", 1000.0, None, None, 2020),  # 1,000 × 125 / 100 = 1,250
        ("MN", "1", 2026, None, "water_sewer", "SFD", 2000.0, None, None, 2026),  # past the index: as 2025
    )
    r = one(fl.coded_fees(f, index=index, to_year=2025), "1")
    assert r["local_fee_per_unit"] == pytest.approx(3250) and r["fee_dollars"] == "2025 dollars"
    assert one(fl.coded_fees(f), "1")["fee_dollars"] == "nominal"


def test_building_type_own_rows_then_other_then_own_sfd():
    f = rows(
        ("MN", "1", 2026, None, "permit", "OTHER", 3000.0, None, None, 2026),
        ("MN", "1", 2026, None, "water_sewer", "SFD", 2800.0, None, None, 2026),
        ("MN", "1", 2026, None, "water_sewer", "U3_4", 2200.0, None, None, 2026),
        ("MN", "1", 2026, None, "impact", "SFD", 1500.0, None, None, 2026),
    )
    sfd = one(fl.coded_fees(f, "SFD"), "1")
    assert sfd["local_fee_per_unit"] == 3000 + 2800 + 1500
    plex = one(fl.coded_fees(f, "U3_4"), "1")
    # water_sewer: its own U3_4 row (2,200); permit: the OTHER row (3,000); impact: the house's (1,500).
    assert plex["local_fee_per_unit"] == 2200 + 3000 + 1500
    assert "impact:2026 (from SFD)" in plex["fee_years"]
    with pytest.raises(ValueError):
        fl.coded_fees(f, "MF5")


def five_places():
    """Five MN places with permit 1,000-5,000 and water/sewer 2,000-6,000; place 6 has only an impact fee."""
    out = []
    for i in range(1, 6):
        out.append(("MN", str(i), 2026, None, "permit", "SFD", 1000.0 * i, None, None, 2026))
        out.append(("MN", str(i), 2026, None, "water_sewer", "SFD", 1000.0 * (i + 1), None, None, 2026))
    out.append(("MN", "6", 2026, None, "impact", "SFD", 700.0, None, None, 2026))
    out.append(("MN", "7", 2026, None, "permit", "SFD", 2500.0, None, None, 2026))
    return rows(*out)


def test_fill_only_permit_and_water_sewer_from_the_state_median():
    places = pd.DataFrame({"geoid": ["6", "7", "1"], "state": "MN"})
    out = fl.place_fees(places, five_places()).set_index("geoid")
    # Permit over the six places with one: 1,000 2,000 2,500 3,000 4,000 5,000 -> median 2,750; linear P25 at
    # position 1.25 = 2,000 + 0.25 × 500 = 2,125; P75 at 3.75 = 3,000 + 0.75 × 1,000 = 3,750.
    # Water/sewer over places 1-5: 2,000..6,000 -> median 4,000, P25 3,000, P75 5,000.
    six = out.loc["6"]
    assert six["local_fee_per_unit"] == pytest.approx(700 + 2750 + 4000)
    assert six["local_fee_low"] == pytest.approx(700 + 2125 + 3000)
    assert six["local_fee_high"] == pytest.approx(700 + 3750 + 5000)
    assert six["fee_source"] == "local + filled: water_sewer, permit (state median)"
    seven = out.loc["7"]  # has a permit; only water/sewer filled; no impact fee invented
    assert seven["local_fee_per_unit"] == pytest.approx(2500 + 4000)
    assert out.loc["1", "fee_source"] == "local" and out.loc["1", "local_fee_per_unit"] == 3000


def test_uncoded_place_gets_the_state_median_total_else_pooled():
    places = pd.DataFrame({"geoid": ["99", "88"], "state": ["MN", "OH"]})
    out = fl.place_fees(places, five_places()).set_index("geoid")
    # MN totals: 3,000 5,000 7,000 9,000 11,000, 700, 2,500 -> median 5,000.
    assert out.loc["99", "local_fee_per_unit"] == 5000 and out.loc["99", "fee_source"] == "state median"
    # Ohio has no coded places: the pooled median (the same places here).
    assert out.loc["88", "local_fee_per_unit"] == 5000 and out.loc["88", "fee_source"] == "pooled median"


def test_too_few_places_for_a_prior():
    places = pd.DataFrame({"geoid": ["99"], "state": ["MN"]})
    f = rows(("MN", "1", 2026, None, "permit", "SFD", 1000.0, None, None, 2026))
    out = fl.place_fees(places, f)
    assert np.isnan(out.loc[0, "local_fee_per_unit"]) and out.loc[0, "fee_source"] == "no prior"


def test_plex_prior_falls_back_to_houses_when_too_few_plexes_are_coded():
    places = pd.DataFrame({"geoid": ["99"], "state": ["MN"]})
    out = fl.place_fees(places, five_places(), "U2")
    # No U2 rows anywhere; places 1-7 carry their SFD fees as "from SFD", so the U2 median is the SFD one.
    assert out.loc[0, "local_fee_per_unit"] == 5000
