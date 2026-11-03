"""St. Paul V5 helper on synthetic rows: the snapshot-date guard, district assignment and H1/H2 lot counts."""

import pandas as pd
import pytest

from lotline.adapters.states.mn import stpaul_v5

OPENS = pd.Timestamp("2024-01-01")


def square(x0, y0, size=1.0):
    return [[[x0, y0], [x0 + size, y0], [x0 + size, y0 + size], [x0, y0 + size], [x0, y0]]]


def test_snapshot_date_from_layer_name():
    assert stpaul_v5.snapshot_date("Principal Zoning - November 26th, 2023") == pd.Timestamp("2023-11-26")
    assert stpaul_v5.snapshot_date("Principal Zoning - April 3rd, 2023 ") == pd.Timestamp("2023-04-03")
    assert stpaul_v5.snapshot_date("Principal Zoning - June 1st, 2024") == pd.Timestamp("2024-06-01")
    with pytest.raises(ValueError, match="no day-month-year"):
        stpaul_v5.snapshot_date("Principal Zoning - December 2018")  # month-only names are refused


def test_window_guard_refuses_snapshots_from_the_window():
    assert stpaul_v5.check_window("Principal Zoning - November 26th, 2023", OPENS) == pd.Timestamp(
        "2023-11-26"
    )
    with pytest.raises(ValueError, match="holdout window"):
        stpaul_v5.check_window("Principal Zoning - January 1st, 2024", OPENS)
    with pytest.raises(ValueError, match="holdout window"):
        stpaul_v5.check_window("Principal Zoning - June 25th, 2024", OPENS)


def test_window_opens_from_state_config():
    assert stpaul_v5.window_opens() == OPENS


def test_districts_cleans_codes_and_drops_empty_rows():
    raw = pd.DataFrame(
        {"Zoning": [" h1 ", "", None, "RM2"], "rings": [square(0, 0), square(1, 0), square(2, 0), []]}
    )
    out = stpaul_v5.districts(raw)
    assert out["district"].tolist() == ["H1"]


def test_roll_2023_keeps_st_paul_rolls_dated_before_the_window():
    p = pd.DataFrame(
        {
            "jurisdiction_geoid": ["2758000", "2758000", "2758000", "2743000"],
            "vintage": [2023, 2023, 2024, 2023],
            "vintage_date": pd.to_datetime(["2023-12-26", "2024-01-08", "2024-12-30", "2023-12-28"]),
            "parcel_id": ["a", "b", "c", "d"],
        }
    )
    # "b" is a 2023-vintage roll exported in January 2024: the snapshot rule hides it.
    assert stpaul_v5.roll_2023(p)["parcel_id"].tolist() == ["a"]


def test_h_lots_hand_worked():
    # H1 square at x 0-1, H2 at x 1-2, RM2 at x 2-3; every lot is above the eligibility floor.
    polygons = pd.DataFrame(
        {"district": ["H1", "H2", "RM2"], "rings": [square(0, 0), square(1, 0), square(2, 0)]}
    )
    p = pd.DataFrame(
        {
            "parcel_id": list("abcdefg"),
            "lon": [0.2, 0.5, 0.8, 1.5, 1.6, 2.5, 5.0],
            "lat": [0.5] * 7,
            "land_use_std": [
                "SF_DETACHED",
                "SF_DETACHED",
                "VACANT_RESIDENTIAL",
                "DUPLEX",
                "SF_DETACHED",
                "SF_DETACHED",
                "SF_DETACHED",
            ],
            "units": [1, 1, 0, 2, 1, 1, 1],
            "lot_sqft": [6000.0, 8000.0, 5000.0, 7000.0, 9000.0, 6000.0, 6000.0],
        }
    )
    out = stpaul_v5.h_lots(p, polygons).set_index(["district", "land_use_std"])
    # H1: two houses and a vacant lot, all eligible; H2: a duplex (not eligible) and a house (eligible).
    assert out.loc[("H1", "SF_DETACHED"), "parcels"] == 2 and out.loc[("H1", "SF_DETACHED"), "eligible"] == 2
    assert out.loc[("H1", "VACANT_RESIDENTIAL"), "eligible"] == 1
    assert out.loc[("H2", "DUPLEX"), "eligible"] == 0 and out.loc[("H2", "SF_DETACHED"), "eligible"] == 1
    assert out.loc[("H1", "SF_DETACHED"), "median_lot_sqft"] == 7000.0
    assert out["parcels"].sum() == 5  # the RM2 house and the point outside every polygon are left out


def test_former_district_check_cross_tab():
    before = pd.DataFrame(
        {"district": ["R4", "RT1", "B2"], "rings": [square(0, 0), square(1, 0), square(2, 0)]}
    )
    after = pd.DataFrame(
        {"district": ["H1", "H2", "B2"], "rings": [square(0, 0), square(1, 0), square(2, 0)]}
    )
    p = pd.DataFrame({"parcel_id": list("abc"), "lon": [0.5, 1.5, 2.5], "lat": [0.5, 0.5, 0.5]})
    out = stpaul_v5.former_district_check(p, before, after)
    assert sorted(zip(out["before"], out["after"], out["parcels"], strict=True)) == [
        ("R4", "H1", 1),
        ("RT1", "H2", 1),
    ]
