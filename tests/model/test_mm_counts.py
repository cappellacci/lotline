"""D-082 (proposed) §2–§3 counting rules (`model/mm_counts.py`), each against a hand-worked synthetic example.

No real data: every table here is built in the test.
"""

from __future__ import annotations

import math

import pandas as pd
import pytest

from lotline.model import mm_counts as mc

NA = pd.NA


def permits(rows: list[dict], *, address: bool = True) -> pd.DataFrame:
    """Processed-permits-like rows. Defaults: one source, place G1, not a conversion or demolition."""
    base = {
        "state": "NC",
        "parcel_id": NA,
        "jurisdiction_geoid": "3700001",
        "issue_date": pd.NaT,
        "building_type_std": "U2",
        "units_new": NA,
        "is_conversion": False,
        "is_demolition": False,
        "n_buildings": NA,
        "source": "test_permits",
        "address": "",
    }
    out = pd.DataFrame([{**base, "permit_id": f"P{i + 1}", **r} for i, r in enumerate(rows)])
    out["units_new"] = out["units_new"].astype("Int64")
    out["n_buildings"] = out["n_buildings"].astype("Int64")
    out["issue_year"] = out["issue_year"].astype("Int64")
    out["is_conversion"] = out["is_conversion"].astype("boolean")
    out["is_demolition"] = out["is_demolition"].astype("boolean")
    if not address:
        out = out.drop(columns="address")
    return out


# --------------------------------------------------------------------------------------------- parameters


def test_params_are_the_d082_values():
    p = mc.params()
    assert p["mm_coverage_k_low"] == 0.8
    assert p["mm_coverage_k_high"] == 1.25
    assert p["mm_ratio_min_buildings"] == 50
    assert p["mm_teardown_demolition_window"] == 2
    assert p["mm_roll_merge_growth"] == 0.20
    assert p["mm_strong_parcel_fill"] == 0.85
    assert p["mm_strong_min_pre_years"] == 3
    assert (p["mm_collapse_min_units"], p["mm_collapse_max_units"]) == (2, 4)


# -------------------------------------------------------------------------------------- building collapse

COLLAPSE_ROWS = [
    # parcel A, 2020: two half-permits at one address (case and punctuation differ) → one duplex
    {"parcel_id": "A", "issue_year": 2020, "address": "12 Main St", "units_new": 1},
    {"parcel_id": "A", "issue_year": 2020, "address": "12 main st.", "units_new": 1},
    # parcel A, 2020, another address → its own triplex
    {
        "parcel_id": "A",
        "issue_year": 2020,
        "address": "14 Main St",
        "building_type_std": "U3_4",
        "units_new": 3,
    },
    # parcel B, 2021: 4 + 2 at one address → 6 units, out of range
    {"parcel_id": "B", "issue_year": 2021, "address": "9 Oak", "building_type_std": "U3_4", "units_new": 4},
    {"parcel_id": "B", "issue_year": 2021, "address": "9 Oak", "units_new": 2},
    # parcel C: no unit count → units_missing
    {"parcel_id": "C", "issue_year": 2021, "address": "1 Elm"},
    # two permits with no parcel ID at the same address → two buildings, each kept
    {"issue_year": 2022, "address": "5 Pine", "units_new": 2},
    {"issue_year": 2022, "address": "5 Pine", "units_new": 2},
    # a house: not a 2–4 type, ignored
    {"parcel_id": "D", "issue_year": 2022, "building_type_std": "SFD", "units_new": 1},
    # an aggregate row (type × year total): dropped
    {"issue_year": 2022, "units_new": 10, "n_buildings": 5},
]


def test_collapse_by_parcel_year_address():
    b = mc.collapse_buildings(permits(COLLAPSE_ROWS))
    rep = mc.collapse_report(b)
    # Hand count: A/12 Main (2 units), A/14 Main (3), B (6), C (?), P7 (2), P8 (2)
    # → 6 buildings from 8 permits
    assert rep == {
        "permits": 8,
        "buildings": 6,
        "buildings_ok": 4,
        "buildings_units_missing": 1,
        "buildings_units_out_of_range": 1,
        "buildings_parcel_missing": 2,
        "buildings_split": 0,
        "address_used": True,
        "aggregate_rows_dropped": 1,
    }
    a12 = b[(b["parcel_id"] == "A") & (b["address_key"] == "12 MAIN ST")].iloc[0]
    assert (a12["units"], a12["n_permits"], a12["status"]) == (2, 2, "ok")
    assert b.loc[b["parcel_id"] == "B", "units"].iloc[0] == 6
    assert sorted(mc.ok(b)["units"].tolist()) == [2, 2, 2, 3]


def test_collapse_without_address_merges_a_parcel_year():
    # Processed tables carry no address: parcel A's two 2020 buildings become one of 1 + 1 + 3 = 5 units.
    b = mc.collapse_buildings(permits(COLLAPSE_ROWS, address=False))
    a = b[b["parcel_id"] == "A"]
    assert len(a) == 1 and a["units"].iloc[0] == 5 and a["status"].iloc[0] == "units_out_of_range"
    assert not b["address_used"].any()
    assert len(b) == 5  # A, B, C and the two parcel-less permits


def test_per_permit_split_separates_merged_buildings():
    # No address. Parcel B 2021: 4 + 2 = 6 > 4 and both permits are 2-4 on their own -> two buildings (4, 2).
    # Parcel A 2020: 1 + 1 + 3 = 5 but the 1-unit half-permits are below 2 -> stays merged, out of range.
    b = mc.collapse_buildings(permits(COLLAPSE_ROWS, address=False), split_merged=True)
    bb = b[b["parcel_id"] == "B"]
    assert sorted(bb["units"].tolist()) == [2, 4] and bb["split"].all() and (bb["status"] == "ok").all()
    a = b[b["parcel_id"] == "A"]
    assert len(a) == 1 and a["units"].iloc[0] == 5 and not a["split"].iloc[0]
    assert a["status"].iloc[0] == "units_out_of_range"
    rep = mc.collapse_report(b)
    assert rep["buildings_split"] == 2 and rep["buildings"] == 6
    # Without the flag the pre-registered rule is unchanged: B is one 6-unit building.
    old = mc.collapse_buildings(permits(COLLAPSE_ROWS, address=False))
    assert old.loc[old["parcel_id"] == "B", "units"].tolist() == [6] and not old["split"].any()


def test_collapse_refuses_st_paul():
    df = permits([{"parcel_id": "X", "issue_year": 2020, "units_new": 2, "jurisdiction_geoid": "2758000"}])
    with pytest.raises(mc.NeverReadError):
        mc.collapse_buildings(df)


# ------------------------------------------------------------------------------------------ coverage and k


def test_coverage_k_point_interval_and_rule():
    # 45 permit buildings vs 50 BPS buildings: k = 0.9. Conditional binomial: n = 95, p = 45/95 = 0.47368.
    # Wilson, z = 1.6449: centre = (0.47368 + 0.014241) / 1.028481 = 0.47441; half = 0.083093
    # p in [0.39132, 0.55750] → k = p/(1-p) in [0.6429, 1.2599].
    r = mc.coverage_k(45, 50)
    assert r["k"] == pytest.approx(0.9)
    assert r["k_lo"] == pytest.approx(0.6429, abs=5e-4)
    assert r["k_hi"] == pytest.approx(1.2599, abs=5e-4)
    assert r["enters"]


@pytest.mark.parametrize(
    "a,b,enters",
    [(40, 50, True), (50, 40, True), (39, 50, False), (63, 50, False), (0, 0, False), (3, 0, False)],
)
def test_coverage_entry_bounds(a, b, enters):
    # 40/50 = 0.8 and 50/40 = 1.25 are on the bounds (inclusive); 0.78 and 1.26 are outside; 0/0 and 3/0 never
    assert mc.coverage_k(a, b)["enters"] is enters


def test_coverage_screen_uses_years_before_the_event_and_the_area():
    b = pd.DataFrame(
        {
            "jurisdiction_geoid": ["G1", "G1", "G1", "G1", "G2"],
            "issue_year": pd.array([2016, 2017, 2018, 2019, 2017], dtype="Int64"),
            "status": ["ok", "ok", "units_out_of_range", "ok", "ok"],
        }
    )
    bps = pd.DataFrame(
        {
            "geoid": ["G1", "G1", "G1", "G1", "G2"],
            "year": [2016, 2017, 2018, 2019, 2017],
            "bldgs_2": [1, 0, 1, 9, 9],
            "bldgs_3_4": [0, 1, 0, 9, 9],
        }
    )
    # Event 2019, from 2016: G1 permit buildings 2016–2018 that are ok = 2; BPS G1 2016–2018 = 1 + 1 + 1 = 3
    r = mc.coverage_screen(b, bps, geoids=["G1"], first_event_year=2019, first_year=2016)
    assert (r["permit_buildings"], r["bps_buildings"]) == (2, 3)
    assert r["k"] == pytest.approx(2 / 3) and not r["enters"]
    assert r["years"] == "2016-2018"


def test_area_coverage_sums_each_place_over_its_own_years():
    b = pd.DataFrame(
        {
            "jurisdiction_geoid": ["G1", "G1", "G1", "G2", "G2", "G2"],
            "issue_year": pd.array([2016, 2017, 2018, 2017, 2018, 2018], dtype="Int64"),
            "status": ["ok", "ok", "ok", "ok", "ok", "units_missing"],
        }
    )
    bps = pd.DataFrame(
        {
            "geoid": ["G1", "G1", "G1", "G2", "G2"],
            "year": [2016, 2017, 2018, 2017, 2018],
            "bldgs_2": [1, 1, 5, 7, 2],
            "bldgs_3_4": [0, 1, 5, 7, 0],
        }
    )
    # G1 2016-2017: permits 2, BPS 1 + 2 = 3. G2 2018 only: permits 1 (the units_missing one is out), BPS 2.
    # Totals 3 / 5 = 0.6 -> below 0.8, does not enter.
    r = mc.area_coverage(b, bps, {"G1": (2016, 2017), "G2": (2018, 2018)})
    assert (r["permit_buildings"], r["bps_buildings"]) == (3, 5)
    assert r["k"] == pytest.approx(0.6) and not r["enters"]
    assert r["years"] == "G1 2016-2017; G2 2018-2018"


def test_strong_source_four_tests():
    rows = [{"parcel_id": f"p{i}", "issue_year": 2014 + i % 4, "units_new": 2} for i in range(17)]
    rows += [{"issue_year": 2020, "units_new": 2} for _ in range(3)]  # 3 of 20 rows without a parcel ID
    df = permits(rows)
    r = mc.strong_source(df, {"enters": True}, first_event_year=2019)
    # fill = 17/20 = 0.85 (passes, inclusive); years before 2019: 2014–2017 = 4
    assert r["parcel_fill"] == pytest.approx(0.85) and r["parcel_fill_ok"]
    assert r["pre_years"] == 4 and r["has_units"] and r["strong"]
    assert not mc.strong_source(df, {"enters": False}, first_event_year=2019)["strong"]
    assert mc.strong_source(df, {"enters": True}, first_event_year=2017)["strong"]  # 2014–2016: 3, inclusive
    assert not mc.strong_source(df, {"enters": True}, first_event_year=2016)["strong"]  # 2014–2015: 2


# ------------------------------------------------------------------------------------------- uplift ratios


def ratio_fixture() -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = [
        # new 2–4 buildings, 2016–2025
        {"parcel_id": "A", "issue_year": 2017, "units_new": 2},  # b1: house on 2015 roll → teardown
        {"parcel_id": "B", "issue_year": 2017, "units_new": 3, "building_type_std": "U3_4"},  # b2: vacant lot
        {"parcel_id": "C", "issue_year": 2020, "units_new": 2},  # b3: vacant on 2019 roll, demolition 2018
        {
            "parcel_id": "E",
            "issue_year": 2018,
            "units_new": 2,
        },  # b4: no prior roll row; demolition 2021 (3 y)
        {"issue_year": 2019, "units_new": 2},  # b5: no parcel ID
        {"parcel_id": "G", "issue_year": 2015, "units_new": 2},  # outside 2016–2025
        # a conversion to a duplex
        {"parcel_id": "H", "issue_year": 2021, "units_new": 2, "is_conversion": True},
        # townhouses
        {"parcel_id": "T1", "issue_year": 2018, "building_type_std": "TH", "units_new": 1},  # SF-zoned 2015
        {"parcel_id": "T2", "issue_year": 2018, "building_type_std": "TH", "units_new": 1},  # not SF-zoned
        {"issue_year": 2018, "building_type_std": "TH", "units_new": 1},  # no parcel → unmatched
        # 5–6 unit buildings
        {"parcel_id": "F1", "issue_year": 2022, "building_type_std": "U5_6", "units_new": 5},  # SF-zoned 2019
        {"parcel_id": "A", "issue_year": 2022, "building_type_std": "U5_6", "units_new": 7},  # 7 units: out
        # demolitions
        {"parcel_id": "C", "issue_year": 2018, "building_type_std": "OTHER", "is_demolition": True},
        {"parcel_id": "E", "issue_year": 2021, "building_type_std": "OTHER", "is_demolition": True},
    ]
    roll = [
        ("A", 2015, "SF_DETACHED", True),
        ("B", 2015, "VACANT_RESIDENTIAL", True),
        ("C", 2015, "SF_DETACHED", False),
        ("T1", 2015, "SF_DETACHED", True),
        ("T2", 2015, "SF_DETACHED", False),
        ("C", 2019, "VACANT_RESIDENTIAL", False),
        ("F1", 2019, "SF_DETACHED", True),
    ]
    rolls = pd.DataFrame(roll, columns=["parcel_id", "vintage", "land_use_std", "sf_only_zoned"])
    return permits(rows), rolls


def test_source_ratios_hand_worked():
    p, rolls = ratio_fixture()
    r = mc.source_ratios(p, rolls, r56_measured=True).set_index("ratio")
    # New 2–4 buildings in 2016–2025: b1..b5 = 5 (H is a conversion, G is 2015)
    assert (r["denominator"] == pd.Series({"r56": 5, "rTH": 5, "rCV": 5, "s_td": 4})).all()
    assert r.loc["rCV", "value"] == pytest.approx(1 / 5)  # H
    assert r.loc["rTH", "value"] == pytest.approx(1 / 5)  # T1 only
    assert r.loc["rTH", "unmatched"] == 1  # the parcel-less townhouse
    assert r.loc["r56", "value"] == pytest.approx(1 / 5)  # F1; parcel A's 7-unit building is out of range
    # s_td: parcel-joined b1..b4 = 4; b1 (house in 2015), b3 (demolition 2018, within 2 of 2020) → 2/4
    assert r.loc["s_td", "value"] == pytest.approx(0.5)
    assert (r.loc["s_td", "no_parcel"], r.loc["s_td", "no_prior_roll"]) == (1, 1)


def test_source_ratios_without_roll_or_56():
    p, _ = ratio_fixture()
    r = mc.source_ratios(p, None).set_index("ratio")
    assert not r.loc["r56", "measured"] and math.isnan(r.loc["r56", "value"])
    assert not r.loc["rTH", "measured"] and math.isnan(r.loc["rTH", "value"])
    # demolitions alone: only b3 → 1/4
    assert r.loc["s_td", "value"] == pytest.approx(0.25)


def test_demolition_window_is_two_years_either_side():
    p = permits(
        [
            {"parcel_id": "A", "issue_year": 2020, "units_new": 2},
            {"parcel_id": "A", "issue_year": 2022, "building_type_std": "OTHER", "is_demolition": True},
            {"parcel_id": "B", "issue_year": 2020, "units_new": 2},
            {"parcel_id": "B", "issue_year": 2017, "building_type_std": "OTHER", "is_demolition": True},
        ]
    )
    r = mc.source_ratios(p, None).set_index("ratio")
    assert r.loc["s_td", "value"] == pytest.approx(0.5)  # A (+2) counts, B (−3) does not


def test_pool_ratios_weighted_mean_and_range():
    rows = [
        {
            "source": "S1",
            "ratio": "rCV",
            "measured": True,
            "numerator": 10,
            "denominator": 100,
            "value": 0.10,
        },
        {"source": "S2", "ratio": "rCV", "measured": True, "numerator": 3, "denominator": 20, "value": 0.15},
        {"source": "S3", "ratio": "rCV", "measured": True, "numerator": 30, "denominator": 60, "value": 0.50},
        {"source": "S1", "ratio": "r56", "measured": True, "numerator": 2, "denominator": 100, "value": 0.02},
        {
            "source": "S2",
            "ratio": "r56",
            "measured": False,
            "numerator": NA,
            "denominator": 20,
            "value": math.nan,
        },
        {
            "source": "S1",
            "ratio": "rTH",
            "measured": False,
            "numerator": NA,
            "denominator": 100,
            "value": math.nan,
        },
    ]
    out = mc.pool_ratios(pd.DataFrame(rows)).set_index("ratio")
    # rCV pooled = (10 + 3 + 30) / (100 + 20 + 60) = 43/180; range over sources with ≥ 50: 0.10 and 0.50
    assert out.loc["rCV", "pooled"] == pytest.approx(43 / 180)
    assert (out.loc["rCV", "low"], out.loc["rCV", "high"]) == (0.10, 0.50)
    assert out.loc["rCV", "sources_in_range"] == 2
    assert out.loc["r56", "pooled"] == pytest.approx(0.02) and out.loc["r56", "sources"] == 1
    assert math.isnan(out.loc["rTH", "pooled"]) and math.isnan(out.loc["s_td", "low"])


# ------------------------------------------------------------------------------------- roll diff (test B)


def roll(rows: list[tuple]) -> pd.DataFrame:
    df = pd.DataFrame(rows, columns=["parcel_id", "buildings", "units", "lot_sqft"]).set_index("parcel_id")
    df["jurisdiction_geoid"] = "G"
    return df


def test_diff_rolls_24_hand_worked():
    before = roll(
        [
            ("L1", 1, 1, 5000),  # → duplex: gained
            ("L2", 1, 1, 5000),  # → still a house
            ("L3", 0, 0, 4000),  # vacant → fourplex: gained
            ("L4", 1, 1, 5000),  # → triplex on a lot 30% bigger: merge (looked gained)
            ("L5", 1, 1, 5000),  # parcel retired: split
            ("L6", 1, 1, 5000),  # → house + ADU (two buildings): none
            ("L7", 1, 2, 5000),  # a duplex already: not in the base
            ("L8", 1, 1, 5000),  # → 5 units: none
            ("L9", 1, 1, 5000),  # → duplex, lot exactly +20% (not more): gained
        ]
    )
    after = roll(
        [
            ("L1", 1, 2, 5000),
            ("L2", 1, 1, 5000),
            ("L3", 1, 4, 4000),
            ("L4", 1, 3, 6500),
            ("L6", 2, 2, 5000),
            ("L7", 1, 3, 5000),
            ("L8", 1, 5, 5000),
            ("L9", 1, 2, 6000),
            ("NEW", 1, 2, 2500),  # a new parcel: not in the base
        ]
    )
    d = mc.diff_rolls_24(before, after)
    assert d["group"].to_dict() == {
        "L1": "gained_24",
        "L2": "none",
        "L3": "gained_24",
        "L4": "merge",
        "L5": "split",
        "L6": "none",
        "L8": "none",
        "L9": "gained_24",
    }
    s = mc.roll_diff_summary(d).iloc[0]
    assert (s["lots"], s["single"], s["vacant"]) == (8, 7, 1)
    assert (s["gained_24"], s["merge"], s["split"], s["none"]) == (3, 1, 1, 3)
    assert s["merge_looked_gained"] == 1
    assert s["counted"] == 6 and s["share"] == pytest.approx(0.5)


def test_roll_from_parcels_reads_land_use():
    p = pd.DataFrame(
        {
            "parcel_id": ["a", "b", "c", "d", "e"],
            "jurisdiction_geoid": "G",
            "land_use_std": ["SF_DETACHED", "DUPLEX", "VACANT_RESIDENTIAL", "MULTIFAMILY_5P", "SF_DETACHED"],
            "units": pd.array([1, 2, NA, 12, 0], dtype="Int64"),
            "lot_sqft": [5000.0, 5000.0, 4000.0, 20000.0, 5000.0],
        }
    )
    r = mc.roll_from_parcels(p)
    assert r["buildings"].tolist() == [1, 1, 0, NA, NA]
    assert r["units"].tolist() == [1, 2, 0, 12, 0]


def test_diff_refuses_ramsey_parcel():
    before = roll([("27123000000001", 1, 1, 5000)])
    with pytest.raises(mc.NeverReadError):
        mc.diff_rolls_24(before, before)


# ------------------------------------------------------------------------------------------------ holdouts


def test_blind_drops_st_paul_and_ramsey_before_holdout_apply(monkeypatch):
    calls = []

    def fake_apply(df, state, **kw):
        calls.append((state, kw))
        return df

    monkeypatch.setattr(mc.holdout, "apply", fake_apply)
    df = pd.DataFrame(
        {
            "jurisdiction_geoid": ["2743000", "2758000", "2712345678", "2743000"],
            "parcel_id": ["27053001", "27123001", "x", "27123002"],
            "issue_year": [2020, 2020, 2020, 2020],
            "issue_date": pd.NaT,
        }
    )
    out = mc.blind(df, "MN", date_col="issue_date", year_col="issue_year")
    # St. Paul (any year, even before its 2024 window), a Ramsey-coded GEOID and a Ramsey parcel are dropped
    assert out["parcel_id"].tolist() == ["27053001"]
    assert calls == [
        ("MN", {"holdouts": None, "geoid_col": "jurisdiction_geoid", "date_col": "issue_date",
                "year_col": "issue_year", "snapshot": False})
    ]  # fmt: skip


def test_blind_uses_the_real_registry_for_st_paul():
    # The real MN registry (config, not data) also hides St. Paul 2024+; blind refuses earlier years too.
    df = pd.DataFrame(
        {
            "jurisdiction_geoid": ["2758000", "2758000", "2743000"],
            "issue_year": pd.array([2019, 2024, 2024], dtype="Int64"),
            "issue_date": pd.NaT,
        }
    )
    out = mc.blind(df, "MN", date_col="issue_date", year_col="issue_year")
    assert out["jurisdiction_geoid"].tolist() == ["2743000"]


def test_apply_themes_recodes_non_mm_rows_and_keeps_demolitions():
    df = permits(
        [
            {"parcel_id": "A", "issue_year": 2020, "units_new": 1},  # U2 themed adu
            {"parcel_id": "B", "issue_year": 2020, "units_new": 2},  # U2 themed mm_2_4
            {
                "parcel_id": "C",
                "issue_year": 2020,
                "building_type_std": "U3_4",
                "units_new": 0,
                "is_demolition": True,
            },  # fmt: skip
            {"parcel_id": "D", "issue_year": 2020, "building_type_std": "SFD", "units_new": 1},
        ]
    )
    themes = pd.Series(["adu", "mm_2_4", "other", "other"], index=df.index)
    out = mc.apply_themes(df, themes)
    assert out["building_type_std"].tolist() == ["OTHER", "U2", "OTHER", "SFD"]
    assert out["theme_recoded"].tolist() == [True, False, True, False]
    assert bool(out["is_demolition"].iloc[2])
    # Only parcel B is left as a 2-4 building after the collapse.
    assert mc.ok(mc.collapse_buildings(out))["parcel_id"].tolist() == ["B"]


def test_two_unit_adu_share_hand_worked():
    df = permits(
        [
            {"parcel_id": "A", "issue_year": 2020, "units_new": 1},
            {"parcel_id": "B", "issue_year": 2020, "units_new": 2},
            {"parcel_id": "C", "issue_year": 2021, "units_new": 2},
            {"parcel_id": "D", "issue_year": 2021, "units_new": 0},
            {"parcel_id": "E", "issue_year": 2010, "units_new": 1},  # outside the years
        ]
    )
    themes = pd.Series(["adu", "mm_2_4", "mm_2_4", "other", "adu"], index=df.index)
    r = mc.two_unit_adu_share(df, themes, 2016, 2025)
    # adding U2 rows in 2016-2025: A (adu), B, C (mm_2_4) = 3; ADUs 1 -> 1/3
    assert (r["u2_adding_rows"], r["u2_adu_rows"]) == (3, 1)
    assert r["adu_share"] == pytest.approx(1 / 3)


def test_source_ratios_split_passthrough():
    # Parcel P 2020: two 2-unit permits, no address -> one 4-unit building either way (sum 4 is in range).
    # Parcel Q 2020: 4 + 3 = 7 -> dropped by the pre-registered collapse, two buildings with the split.
    df = permits(
        [
            {"parcel_id": "P", "issue_year": 2020, "units_new": 2},
            {"parcel_id": "P", "issue_year": 2020, "units_new": 2},
            {"parcel_id": "Q", "issue_year": 2020, "building_type_std": "U3_4", "units_new": 4},
            {"parcel_id": "Q", "issue_year": 2020, "building_type_std": "U3_4", "units_new": 3},
        ],
        address=False,
    )
    den = lambda r: int(r.loc[r["ratio"] == "rCV", "denominator"].iloc[0])  # noqa: E731
    assert den(mc.source_ratios(df, None)) == 1
    assert den(mc.source_ratios(df, None, split_merged=True)) == 3


def test_ratios_without_zoning_on_the_roll_leave_r56_and_rth_unmeasured():
    # The roll has land use (for s_td) but no sf_only_zoned: r56 and rTH are "not measured", s_td still reads
    # the house. Parcel H held a house on the 2019 roll; its 2021 duplex counts as a teardown -> s_td 1/1.
    df = permits(
        [
            {"parcel_id": "H", "issue_year": 2021, "units_new": 2},
            {"parcel_id": "T", "issue_year": 2021, "building_type_std": "TH", "units_new": 1},
        ]
    )
    roll = pd.DataFrame({"parcel_id": ["H"], "vintage": [2019], "land_use_std": ["SF_DETACHED"]})
    r = mc.source_ratios(df, roll, r56_measured=True).set_index("ratio")
    assert not r.at["r56", "measured"] and not r.at["rTH", "measured"]
    assert math.isnan(r.at["rTH", "value"])
    assert r.at["s_td", "value"] == 1.0


def test_roll_from_cards_hand_worked_and_diff():
    before = pd.DataFrame(
        {
            "dwelling_cards": [1, 0, 0, 1],
            "dwelling_units": [1, 0, 0, 1],
            "acres": [0.5, 0.25, 1.0, 0.2],
            "luc": ["510", "500", "400", "510"],
            "jurisdiction_geoid": ["3918000"] * 4,
        },
        index=pd.Index(["S", "V", "C", "K"]),
    )
    after = before.copy()
    after.loc["S", ["dwelling_units"]] = 2  # the house lot now holds one 2-unit building: a gain
    after.loc["V", ["dwelling_cards", "dwelling_units"]] = [1, 3]  # vacant lot -> one triplex: a gain
    after.loc["K", ["dwelling_cards", "dwelling_units"]] = [2, 2]  # two cards: not one 2-4 building
    r1 = mc.roll_from_cards(before, vacant_uses=["500"])
    assert r1.at["S", "lot_sqft"] == pytest.approx(21_780)
    assert (r1.at["V", "buildings"], r1.at["V", "units"]) == (0, 0)
    assert pd.isna(r1.at["C", "buildings"])  # no dwelling, not residential vacant land
    d = mc.diff_rolls_24(r1, mc.roll_from_cards(after, vacant_uses=["500"]))
    # Denominator: S, V, K (C is NA). Gains: S, V. K has two cards -> none.
    assert sorted(d.index) == ["K", "S", "V"]
    assert d["gained"].to_dict() == {"S": True, "V": True, "K": False}


def test_roll_from_parcels_house_with_two_units_is_ambiguous():
    # SF_DETACHED with 2 units (house + ADU, or a miscoded duplex) is neither single nor one 2-4 building.
    parcels = pd.DataFrame(
        {
            "parcel_id": ["A", "B", "C"],
            "jurisdiction_geoid": ["G"] * 3,
            "land_use_std": ["SF_DETACHED", "SF_DETACHED", "DUPLEX"],
            "units": [1, 2, 2],
            "lot_sqft": [5000.0] * 3,
        }
    )
    r = mc.roll_from_parcels(parcels)
    assert r.at["A", "buildings"] == 1 and pd.isna(r.at["B", "buildings"]) and r.at["C", "buildings"] == 1


def _script():
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parents[2] / "scripts" / "dev" / "mm_counts_d082.py"
    spec = importlib.util.spec_from_file_location("mm_counts_d082", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_franklin_key_maps_columbus_permit_parcels_to_the_ohio_roll():
    f = _script().franklin_key
    ids = pd.Series(["010052628", "010-052628", "010-052628-00", "5453005", None])
    # 9 digits -> 39049 + DDD-DDDDDD; anything else -> missing
    assert f(ids).tolist()[:3] == ["39049010-052628"] * 3
    assert f(ids).isna().tolist()[3:] == [True, True]


def test_wake_crosswalk_maps_pin10_to_the_reid_parcel_id():
    cards = pd.DataFrame(
        {
            "REAL_ESTATE_ID": ["0046821", "0046821", "0001234"],
            "Parcel_Identification": ["1714.09 05 9993 000", "1714.09 05 9993 000", "0778.11 88 4160 000"],
        }
    )
    xw = _script().wake_crosswalk([cards])
    assert xw.to_dict() == {"371830046821": "1714059993", "371830001234": "0778884160"}


def test_conversion_buildings_counts_any_type_adding_one_to_three_homes():
    df = permits(
        [
            {"parcel_id": "A", "issue_year": 2020, "building_type_std": "OTHER", "units_new": 1},
            {"parcel_id": "A", "issue_year": 2020, "building_type_std": "OTHER", "units_new": 1},
            {"parcel_id": "B", "issue_year": 2021, "units_new": 2},
            {"parcel_id": "C", "issue_year": 2021, "building_type_std": "OTHER", "units_new": 5},
            {"parcel_id": "D", "issue_year": 2021, "units_new": 1},
        ]
    )
    themes = pd.Series(["conversion", "conversion", "conversion", "conversion", "mm_2_4"], index=df.index)
    assert mc.conversion_buildings(df, themes, 2016, 2025) == 2
