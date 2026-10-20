"""config/reforms/mn.csv: every row is a valid `reforms` record coded with the protocol §5.4 rubric.

Read as text (empty cell = unknown); true/false columns are parsed explicitly so a typo fails loudly.
"""

import pandas as pd
import pytest

from lotline.config import CONFIG_DIR
from lotline.schemas import columns, validate

PATH = CONFIG_DIR / "reforms" / "mn.csv"
BOOL_COLS = ["by_right", "owner_occ", "adu_detached_allowed", "lot_split"]


def _read(path=PATH) -> pd.DataFrame:
    raw = pd.read_csv(path, dtype=str, keep_default_na=False)
    df = raw.replace("", pd.NA)
    for col in BOOL_COLS:
        bad = set(df[col].dropna()) - {"True", "False"}
        assert not bad, f"{col}: not True/False: {bad}"
        df[col] = df[col].map({"True": True, "False": False}).astype("boolean")
    return df


@pytest.fixture(scope="module")
def reforms() -> pd.DataFrame:
    return validate(_read(), "reforms")


def test_header_is_the_canonical_column_list():
    assert list(pd.read_csv(PATH, nrows=0).columns) == columns("reforms")


def test_rows_validate(reforms):
    assert len(reforms) >= 11
    assert (reforms["state"] == "MN").all()


def test_every_row_has_an_opened_source(reforms):
    for urls in reforms["source_url"]:
        assert all(u.strip().startswith("https://") for u in urls.split(";")), urls


def test_geoids_are_mn_places(reforms):
    assert reforms["jurisdiction_geoid"].str.fullmatch(r"27\d{5}").all()


def test_supersedes_points_to_an_earlier_row(reforms):
    by_id = reforms.set_index("reform_id")
    for rid, old in by_id["supersedes"].dropna().items():
        assert old in by_id.index, f"{rid} supersedes unknown {old}"
        assert by_id.at[old, "effective_date"] < by_id.at[rid, "effective_date"]


def test_windows_end_after_they_start(reforms):
    w = reforms[reforms["end_date"].notna()]
    assert (w["end_date"] > w["effective_date"]).all()
    assert set(w["status"]) == {"suspended"}


def test_single_coder_rows_have_no_second_coder(reforms):
    single = reforms["coder_agreement"] == "single_coder"
    assert reforms.loc[single, "coder_2"].isna().all()


def test_hand_checked_values(reforms):
    r = reforms.set_index("reform_id")
    # Minneapolis three-unit amendment: adopted 2019-11-08, "scheduled to take effect Jan. 1, 2020"
    tri = r.loc["MN-2743000-missing_middle-2020"]
    assert tri["effective_date"] == pd.Timestamp("2020-01-01") and tri["unit_cap"] == 3
    # Minneapolis ADUs: 2014 owner-occupied only; 2021 amendment drops it for attached/detached ADUs
    assert bool(r.at["MN-2743000-adu-2014", "owner_occ"])
    assert not bool(r.at["MN-2743000-adu-2021", "owner_occ"])
    assert r.at["MN-2743000-adu-2021", "supersedes"] == "MN-2743000-adu-2016"
    assert r.at["MN-2743000-adu-2016", "supersedes"] == "MN-2743000-adu-2014"
    # since 2014: 800 sq ft attached/internal, no ADU parking; owner occupancy ends 2021-03-06
    assert r.at["MN-2743000-adu-2014", "adu_max_sqft"] == 800
    assert r.at["MN-2743000-adu-2014", "parking_min_per_unit"] == 0
    assert r.at["MN-2743000-adu-2021", "effective_date"] == pd.Timestamp("2021-03-06")
    assert r.at["MN-2743000-adu-2023", "effective_date"] == pd.Timestamp("2023-07-01")
    # 2040 injunction windows end when stayed / lifted
    assert r.at["MN-2743000-moratorium-2022", "end_date"] == pd.Timestamp("2022-07-26")
    assert r.at["MN-2743000-moratorium-2023", "end_date"] == pd.Timestamp("2024-05-13")
    # St. Paul Ord. 23-43: adopted 2023-10-18, effective 2023-11-26, H1/H2, 4 units base, 2 ADUs per lot
    h = r.loc["MN-2758000-missing_middle-2023"]
    assert h["effective_date"] == pd.Timestamp("2023-11-26") and h["unit_cap"] == 4
    assert set(h["coverage_zones"].split(";")) == {"H1", "H2"}
    assert r.at["MN-2758000-adu-2023", "adus_per_lot"] == 2
    # St. Paul ADUs: citywide 2018-10-17; owner occupancy dropped by Ord. 22-1 (effective 2022-03-05)
    assert r.at["MN-2758000-adu-2018", "adoption_date"] == pd.Timestamp("2018-10-17")
    assert r.at["MN-2758000-adu-2022", "effective_date"] == pd.Timestamp("2022-03-05")


def test_no_adu_rows_follow_the_convention(reforms):
    none = reforms[reforms["adus_per_lot"] == 0]
    assert len(none) == 6
    assert (none["by_right"] == False).all()  # noqa: E712
    assert none["coding_notes"].str.startswith("NO ADU RULE").all()
    assert set(none["jurisdiction_geoid"]) == {
        "2707966",
        "2771428",
        "2740166",
        "2718116",
        "2713114",
        "2759350",
    }


def test_bad_boolean_is_rejected(tmp_path):
    df = pd.read_csv(PATH, dtype=str, keep_default_na=False)
    df.loc[0, "by_right"] = "Ture"
    bad = tmp_path / "mn.csv"
    df.to_csv(bad, index=False)
    with pytest.raises(AssertionError, match="by_right"):
        _read(bad)
