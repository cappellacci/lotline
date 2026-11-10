"""Fee scenario (model/scenarios/fees.py): hand-worked checks of each equation in the module docstring."""

import math

import numpy as np
import pandas as pd
import pytest

from lotline.model import proforma
from lotline.model.scenarios import fees

P = fees.central_params()
HAND = P | {
    "handbook_fee_per_unit_usd": 50000,
    "handbook_fee_cut_share": 0.5,
    "land_capture_share": 0.5,
    "fee_permit_elasticity": 0.3,
    "fee_ramp_half_years": 1.0,
    "fee_ramp_slope_years": 0.5,
    "fee_feasibility_min_lots": 20,
}


def fee_rows(rows):
    cols = ["jurisdiction_geoid", "year", "fee_component", "building_type_std", "amount_per_unit_usd"]
    return pd.DataFrame(rows, columns=cols)


def test_local_fees_newest_year_per_component():
    rows = fee_rows(
        [
            ("1", 2023, "permit", "OTHER", 3000.0),
            ("1", 2026, "permit", "OTHER", 2000.0),
            ("1", 2026, "permit", "SFD", 1500.0),
            ("1", 2025, "water_sewer", "SFD", 2000.0),
            ("1", 2026, "water_sewer", "SFD", None),  # no per-unit amount: 2025 stays the newest
            ("1", 2026, "impact", "U3_4", 900.0),  # not single-family
            ("2", 2024, "permit", "SFD", 700.0),
        ]
    )
    out = fees.local_fees(rows).set_index("geoid")
    # Place 1: permit 2026 (2,000 + 1,500) + water/sewer 2025 (2,000) = 5,500.
    assert out.at["1", "local_fee_per_unit"] == 5500
    assert out.at["1", "fee_components"] == "permit,water_sewer"
    assert out.at["1", "fee_years"] == "permit:2026,water_sewer:2025"
    assert out.at["2", "local_fee_per_unit"] == 700


def test_fee_levels_local_never_falls_back_to_the_handbook_fee():
    places = pd.DataFrame(
        {
            "local_fee_per_unit": [5500.0, 700.0],
            "fee_source": ["local", "local + filled: water_sewer (state median)"],
        }
    )
    level, source = fees.fee_levels(places, "local_half", HAND)
    assert list(level) == [5500, 700] and source[1].startswith("local + filled")
    assert list(fees.fee_levels(places, "local", HAND)[0]) == [5500, 700]  # old name of local_half
    level, source = fees.fee_levels(places, "handbook", HAND)
    assert list(level) == [50000] * 2 and set(source) == {"handbook"}
    with pytest.raises(ValueError):
        fees.fee_levels(places, "other", HAND)
    with pytest.raises(ValueError, match="not a fallback"):
        fees.fee_levels(places.assign(local_fee_per_unit=[5500.0, np.nan]), "local_25k", HAND)


def test_fee_cut_by_scenario_by_hand():
    fee = np.array([6000.0, 80000.0])
    # Half of the local fee: 3,000 and 40,000. Up to $25,000: all of 6,000; 25,000 of 80,000.
    assert list(fees.fee_cut(fee, HAND, "local_half")) == [3000, 40000]
    assert list(fees.fee_cut(fee, HAND, "local_25k")) == [6000, 25000]
    # Builders keep half: 3,000 and 12,500.
    assert list(fees.builder_saving(fee, HAND, "local_25k")) == [3000, 12500]


def test_fee_draws_stay_in_range_and_center_on_the_central_value():
    places = pd.DataFrame(
        {
            "local_fee_per_unit": [5000.0, 8000.0],
            "local_fee_low": [4000.0, np.nan],
            "local_fee_high": [7000.0, np.nan],
        }
    )
    d = fees.fee_draws(places, "local_half", HAND, 4000, 1)
    assert d[:, 0].min() >= 4000 and d[:, 0].max() <= 7000
    # triangular(4,000, 5,000, 7,000) has mean 16,000 / 3 = 5,333.
    assert d[:, 0].mean() == pytest.approx(16000 / 3, rel=0.02)
    assert np.all(d[:, 1] == 8000)  # no range: held at the central value
    assert np.all(fees.fee_draws(places, "handbook", HAND, 10, 1) == 50000)


def test_builder_saving_and_elasticity_by_hand():
    # (1 − 0.5) × 0.5 × 50,000 = 12,500 reaches builders; 0.3 × 12,500 / 250,000 = 0.015.
    saving = fees.builder_saving(np.array([50000.0]), HAND)
    assert saving[0] == 12500
    assert fees.elasticity_change(saving, [250000.0], HAND)[0] == pytest.approx(0.015)


def test_ramp_by_hand():
    # half 1, slope 0.5: t = 1 -> 0.5; t = 2 -> 1 / (1 + e^-2) = 0.8808.
    r = fees.ramp(5, HAND)
    assert r[0] == pytest.approx(0.5) and r[1] == pytest.approx(1 / (1 + math.exp(-2)))


def test_added_units_by_hand():
    # 100 units a year × 1.5% × ramp: year 1 0.75, year 2 1.5 × 0.8808 = 1.3212.
    a = fees.added_units(np.full((1, 5), 100.0), np.array([0.015]), HAND)
    assert a[0, 0] == pytest.approx(0.75) and a[0, 1] == pytest.approx(1.5 / (1 + math.exp(-2)))


def lots_around(value, fee, saving, params, n_both=25, n_new=5, n_never=10):
    """Lots feasible before and after the cut, only after it, and never."""
    market = proforma.Market(value / params["single_family_sqft"], 0.0)
    rlv_b = proforma.residual_land_value("single_family", "for_sale", market, fee, params)
    rlv_a = proforma.residual_land_value("single_family", "for_sale", market, fee - saving, params)
    m = 1 + params["existing_use_margin"]
    assert rlv_a > rlv_b > 0
    return np.concatenate(
        [
            np.full(n_both, 0.9 * rlv_b / m),
            np.full(n_new, (rlv_b + rlv_a) / 2 / m),
            np.full(n_never, 2 * rlv_a / m),
        ]
    )


def test_feasibility_change_by_hand():
    value, fee, saving = 900_000.0, 20_000.0, 5_000.0
    lots = lots_around(value, fee, saving, HAND)
    # 25 feasible before, 30 after: 30 / 25 − 1 = +20%.
    change, before, after = fees.feasibility_change(value, fee, saving, lots, HAND)
    assert (before, after) == (25, 30) and change == pytest.approx(0.2)
    # Fewer than the minimum feasible before: no ratio (the place uses the elasticity route).
    change, before, _ = fees.feasibility_change(value, fee, saving, lots[5:], HAND)
    assert before == 20 and not math.isnan(change)
    change, before, _ = fees.feasibility_change(value, fee, saving, lots[6:], HAND)
    assert before == 19 and math.isnan(change)


def places_frame(with_parcels: bool):
    df = pd.DataFrame(
        {
            "geoid": ["a", "b"],
            "state": ["MN", "MN"],
            "baseline_units": [100.0, 40.0],
            "home_value": [300000.0, 250000.0],
            "local_fee_per_unit": [8000.0, 6000.0],
            "local_fee_low": [8000.0, 4500.0],
            "local_fee_high": [8000.0, 9000.0],
            "fee_source": ["local", "state median"],
        }
    )
    if with_parcels:
        df["new_home_value"] = [900_000.0, np.nan]
        df["lot_values"] = [lots_around(900_000.0, 8000.0, 2000.0, P), None]
    return df


@pytest.mark.parametrize("with_parcels", [False, True])
def test_zero_cut_equals_baseline(with_parcels):
    places = places_frame(with_parcels)
    c = fees.central_path(places, params={"handbook_fee_cut_share": 0.0})
    assert np.all(c["added"] == 0)


CUTS = [m for m in fees.MODES if m != "local_rise"]


@pytest.mark.parametrize("with_parcels", [False, True])
@pytest.mark.parametrize("mode", CUTS)
def test_bigger_cut_never_lowers_output(with_parcels, mode):
    places = places_frame(with_parcels)
    totals = [
        fees.central_path(places, mode, {"handbook_fee_cut_share": s})["added"].sum(axis=1)
        for s in (0.0, 0.25, 0.5, 0.75, 1.0)
    ]
    assert all(np.all(b >= a - 1e-9) for a, b in zip(totals, totals[1:], strict=False))


def test_channel_choice():
    c = fees.central_path(places_frame(True))
    assert list(c["channel"]) == ["feasibility", "elasticity"]
    assert list(c["fee_source"]) == ["local", "state median"]
    assert list(fees.central_path(places_frame(False))["channel"]) == ["elasticity", "elasticity"]


@pytest.mark.parametrize("mode", fees.MODES)
def test_run_ranges_and_state_sum(mode):
    places = places_frame(True)
    yearly, totals, summary = fees.run(places, 2025, mode=mode, draws=200, summary_by="state")
    assert set(totals["scenario_label"]) == {fees.LABELS[mode]}
    assert len(yearly) == 2 * 5 and list(yearly["year"].unique()) == [2027, 2028, 2029, 2030, 2031]
    for t in (yearly, totals):
        assert (t["units_added_p10"] <= t["units_added_p50"]).all()
        assert (t["units_added_p50"] <= t["units_added_p90"]).all()
        if mode == "local_rise":  # a fee rise never adds homes
            assert (t["units_added_p90"] <= 0).all()
        else:
            assert (t["units_added_p10"] >= 0).all()  # ε low is 0, never negative
    five = summary[summary["period"] == "2027-2031"].iloc[0]
    # Means add up across non-overlapping places; percentiles are of each draw's sum.
    assert five["mean"] == pytest.approx(totals["units_added_mean"].sum())
    assert "lot_values" not in totals


def test_parcel_inputs():
    parcels = pd.DataFrame(
        {
            "jurisdiction_geoid": ["a"] * 5,
            "vintage": [2026] * 5,
            "land_use_std": [
                "SF_DETACHED",
                "SF_DETACHED",
                "SF_DETACHED",
                "VACANT_RESIDENTIAL",
                "VACANT_RESIDENTIAL",
            ],
            "year_built": [2020, 2022, 1950, None, None],
            "bldg_sqft": [2000.0, 2500.0, 1500.0, None, None],
            "land_value": [100000.0, 150000.0, 80000.0, 60000.0, 70000.0],
            "bldg_value": [400000.0, 450000.0, 120000.0, 0.0, 0.0],
        }
    )
    out = fees.parcel_inputs(parcels, 2025, P).set_index("geoid")
    # Built 2018-2025: $500k / 2,000 = $250/sq ft and $600k / 2,500 = $240/sq ft; median $245 × 2,150 sq ft.
    assert out.at["a", "new_home_value"] == pytest.approx(245 * P["single_family_sqft"])
    assert list(out.at["a", "lot_values"]) == [60000.0, 70000.0]
    assert out.at["a", "new_homes_seen"] == 2


# ---------------------------------------------------------------------------------------------------------
# D-073: fee rise and a dose per building size
# ---------------------------------------------------------------------------------------------------------


def test_fee_rise_is_a_negative_cut_by_hand():
    # Half of 6,000 added: −3,000; builders bear (1 − 0.5) of it: −1,500.
    fee = np.array([6000.0])
    assert fees.fee_cut(fee, HAND | {"fee_rise_share": 0.5}, "local_rise")[0] == -3000
    assert fees.builder_saving(fee, HAND | {"fee_rise_share": 0.5}, "local_rise")[0] == -1500


@pytest.mark.parametrize("with_parcels", [False, True])
def test_bigger_rise_never_adds_and_mirrors_the_cut(with_parcels):
    places = places_frame(with_parcels)
    totals = [
        fees.central_path(places, "local_rise", {"fee_rise_share": s})["added"].sum()
        for s in (0.0, 0.25, 0.5, 1.0)
    ]
    assert totals[0] == 0 and all(b <= a + 1e-9 for a, b in zip(totals, totals[1:], strict=False))
    if not with_parcels:  # elasticity is linear in the fee change: the rise is the cut's mirror image
        cut = fees.central_path(places, "local_half")["added"].sum()
        assert totals[2] == pytest.approx(-cut)


def test_type_pct_change_by_hand():
    # Duplex fee 10,000 cut in half, builders keep half: 2,500. Home value 430,000 over 2,150 sq ft is $200 a
    # sq ft, so a 1,000 sq ft unit costs 200,000: 0.3 × 2,500 / 200,000 = 0.00375.
    places = pd.DataFrame({"home_value": [430_000.0]})
    p = HAND | {"single_family_sqft": 2150.0, "plex_unit_sqft": 1000.0}
    pct = fees.type_pct_change(places, np.array([10_000.0]), p, "local_half", "U2")
    assert pct[0] == pytest.approx(0.00375)


def by_size_frame(**fees_by_type):
    """One place, baseline by size class: 1-unit 10 a year, 2-unit 4, 3-4 unit 8, 5+ 50."""
    df = pd.DataFrame(
        {"geoid": ["a"], "state": ["MN"], "home_value": [430_000.0], "local_fee_per_unit": [10_000.0]}
    )
    for cls, n in (("1", 10.0), ("2", 4.0), ("3_4", 8.0), ("5p", 50.0)):
        for h in range(1, 6):
            df[f"baseline_y{h}_{cls}"] = n
    for t, v in fees_by_type.items():
        df[f"local_fee_per_unit_{t}"] = v
    return df


def test_each_size_class_takes_its_own_dose_and_5plus_none():
    p = HAND | {"single_family_sqft": 2150.0, "plex_unit_sqft": 1000.0}
    c = fees.central_path(by_size_frame(U2=10_000.0, U3_4=6_000.0), "local_half", p)
    r = fees.ramp(5, p)
    # Houses: 0.3 × 2,500 / 430,000; duplex 0.3 × 2,500 / 200,000; fourplex unit 0.3 × 1,500 / 200,000.
    pct = {"1": 0.3 * 2500 / 430_000, "2": 0.3 * 2500 / 200_000, "3_4": 0.3 * 1500 / 200_000}
    assert c["pct_by_size"]["2"][0] == pytest.approx(pct["2"])
    assert c["pct_by_size"]["3_4"][0] == pytest.approx(pct["3_4"])
    expected = (10 * pct["1"] + 4 * pct["2"] + 8 * pct["3_4"]) * r  # 5+ (50 a year) adds nothing
    assert c["added"][0] == pytest.approx(expected)
    assert set(c["added_by_size"]) == {"1", "2", "3_4"}


def test_same_fee_per_unit_moves_plexes_more_than_houses():
    # The Handbook's $50,000 on every unit: a plex unit costs less than a house, so the same cut is a bigger
    # share of its cost (the density point of office hours A5).
    c = fees.central_path(by_size_frame(), "handbook")
    assert c["pct_by_size"]["2"][0] > c["pct_by_size"]["1"][0]
    assert c["pct_by_size"]["3_4"][0] == pytest.approx(c["pct_by_size"]["2"][0])


def test_missing_type_fee_uses_the_house_fee_and_says_so():
    level, source = fees.fee_levels(by_size_frame(), "local_half", HAND, "U2")
    assert level[0] == 10_000 and source[0] == "local (house fee: no U2 level given)"


def test_run_by_size_reports_each_class_and_adds_up():
    _, totals = fees.run(by_size_frame(U2=10_000.0, U3_4=6_000.0), 2025, mode="local_half", draws=100)
    r = totals.iloc[0]
    assert r["baseline_five_year"] == 5 * (10 + 4 + 8 + 50)
    parts = sum(r[f"units_added_mean_{c}"] for c in ("1", "2", "3_4"))
    assert parts == pytest.approx(r["units_added_mean"])
    assert "units_added_mean_5p" not in totals
