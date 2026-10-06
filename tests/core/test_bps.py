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
    assert df.loc[(2024, "Anoka County Unincorporated Area"), "geoid"] == "27003"  # county issues permits
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


def _rows(**cols):
    base = {
        "state_fips": "39",
        "id6": "000001",
        "county": "041",
        "fips_place": "",
        "fips_mcd": "",
        "months_reported": 12,
        "year": 2020,
    }
    nums = {c: 0 for c in bps.NUMERIC}
    return pd.DataFrame([base | nums | cols])


def test_ohio_county_part_rows_belong_to_the_county():
    df = bps.to_canonical(_rows(name="Delaware County Part", fips_place="00000", fips_mcd="00000"), "OH")
    assert df.geoid.tolist() == ["39041"]


def test_name_fallback_handles_multi_county_suffix_and_county_changes():
    later = _rows(id6="111111", name="Andover village", county="007", fips_place="01848", year=2015)
    early = _rows(id6="999999", name="Andover village@4", county="055", year=2000)  # other county, old ID
    df = bps.backfill_geoids(
        pd.concat([bps.to_canonical(f, "OH") for f in (later, early)], ignore_index=True)
    )
    assert df.geoid.tolist() == ["3901848", "3901848"]


def test_ambiguous_names_are_not_guessed():
    a = _rows(id6="111111", name="Union township", county="001", fips_mcd="11111", year=2015)
    b = _rows(id6="222222", name="Union township", county="003", fips_mcd="22222", year=2015)
    old = _rows(id6="999999", name="Union township", county="005", year=2000)  # matches neither county
    df = bps.backfill_geoids(pd.concat([bps.to_canonical(f, "OH") for f in (a, b, old)], ignore_index=True))
    assert pd.isna(df.geoid.iloc[2])
