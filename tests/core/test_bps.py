from pathlib import Path

import pandas as pd

from lotline.adapters.national import bps
from lotline.schemas import assert_conforms

FIX = Path(__file__).parent / "fixtures"


def _table(state="MN"):
    frames = [
        bps.to_canonical(bps.parse((FIX / f"bps_{y}_style.txt").read_text(), y), state) for y in (1990, 2024)
    ]
    return bps.backfill_geoids(pd.concat(frames, ignore_index=True))


def test_parses_both_layouts_and_filters_state():
    df = _table()
    assert_conforms(df, "bps_place_year")
    assert set(df.state) == {"MN"} and len(df) == 2 + 5


def test_geoid_rules_place_township_unincorporated():
    df = _table().set_index(["year", "name"])
    assert df.loc[(2024, "Minneapolis"), "geoid"] == "2743000"  # place: SS + FIPS place
    assert df.loc[(2024, "Arna township"), "geoid"] == "2700102224"  # township: SS + county + MCD
    assert pd.isna(df.loc[(2024, "Anoka County Unincorporated Area"), "geoid"])  # neither
    assert df.loc[(2024, "Anoka County Unincorporated Area"), "county_geoid"] == "27003"


def test_place_names_with_commas_survive():
    assert "Lake Elmo, Village of" in set(_table().name)


def test_pre_1992_rows_link_by_name_not_reused_id():
    df = _table().set_index(["year", "name"])
    # 1990 Minneapolis had ID 140500, which 2024 reuses for Arna township: must not inherit Arna's GEOID
    assert df.loc[(1990, "Minneapolis"), "geoid"] == "2743000"
    # "St. Paul" (1990) matches "Saint Paul city" (2024) in the same county
    assert df.loc[(1990, "St. Paul"), "geoid"] == "2758000"


def test_imputed_flag_and_reported_columns():
    df = _table().set_index(["year", "name"])
    stp = df.loc[(1990, "St. Paul")]
    assert stp.months_reported == 9 and stp.units_1 == 8 and stp.units_1_rep == 6 and stp.imputed
    assert not df.loc[(2024, "Minneapolis"), "imputed"]
    assert df.loc[(2024, "Minneapolis"), "units_5p"] == 351
