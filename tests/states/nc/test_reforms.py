"""config/reforms/nc.csv: every row is a valid `reforms` record coded with the protocol §5.4 rubric.

The CSV is read as text (empty cell = unknown) and the rubric's true/false columns are parsed explicitly, so a
typo like "Ture" fails instead of becoming null. No reforms loader exists in `lotline.config` yet.
"""

import pandas as pd
import pytest

from lotline.config import CONFIG_DIR
from lotline.schemas import columns, validate

PATH = CONFIG_DIR / "reforms" / "nc.csv"
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
    assert len(reforms) >= 12
    assert (reforms["state"] == "NC").all()


def test_every_row_has_an_opened_source(reforms):
    for urls in reforms["source_url"]:
        assert all(u.strip().startswith("https://") for u in urls.split(";")), urls


def test_geoids_are_nc_state_county_or_place(reforms):
    geoids = reforms["jurisdiction_geoid"]
    assert geoids.str.startswith("37").all()
    assert geoids.str.len().isin([2, 5, 7]).all()


def test_supersedes_points_to_an_earlier_row(reforms):
    by_id = reforms.set_index("reform_id")
    for rid, old in by_id["supersedes"].dropna().items():
        assert old in by_id.index, f"{rid} supersedes unknown {old}"
        assert by_id.at[old, "effective_date"] < by_id.at[rid, "effective_date"]


def test_single_coder_rows_have_no_second_coder(reforms):
    single = reforms["coder_agreement"] == "single_coder"
    assert reforms.loc[single, "coder_2"].isna().all()


def test_hand_checked_values(reforms):
    r = reforms.set_index("reform_id")
    # Raleigh TC-5-20: "Adopted: July 6, 2021", "Effective: August 5, 2021" (30 days after adoption)
    assert r.at["NC-3755000-missing_middle-2021", "effective_date"] == pd.Timestamp("2021-08-05")
    # Raleigh TC-20-21: adopted 2022-05-10, effective 90 days later on 2022-08-08, amends TC-5-20
    assert r.at["NC-3755000-missing_middle-2022", "effective_date"] == pd.Timestamp("2022-08-08")
    assert r.at["NC-3755000-missing_middle-2022", "supersedes"] == "NC-3755000-missing_middle-2021"
    # Charlotte UDO: adopted 2022-08-22, effective 2023-06-01 (the V5 holdout date), up to a triplex on N1
    clt = r.loc["NC-3712000-missing_middle-2023"]
    assert clt["effective_date"] == pd.Timestamp("2023-06-01")
    assert clt["unit_cap"] == 3
    assert "N1-A" in clt["coverage_zones"].split(";")
    # S.L. 2026-59 Sec. 44: one row per covered city, effective 2027-01-15, no parking minimum, cap floor 800
    sl = r.loc["NC-SL2026-59-3712000"]
    assert sl["jurisdiction_geoid"] == "3712000"
    assert sl["effective_date"] == pd.Timestamp("2027-01-15")
    assert sl["parking_min_per_unit"] == 0
    assert sl["adu_max_sqft"] == 800
    # Durham EHC: 800 sq ft ADUs, voted 2019-09-03 (city) and 2019-10-28 (county)
    assert r.at["NC-3719000-adu-2019", "adu_max_sqft"] == 800
    assert r.at["NC-37063-adu-2019", "adoption_date"] == pd.Timestamp("2019-10-28")


def test_state_adu_law_is_coded_per_covered_city(reforms):
    sl = reforms[reforms["reform_id"].str.startswith("NC-SL2026-59-")].set_index("jurisdiction_geoid")
    assert not (reforms["jurisdiction_geoid"] == "37").any()  # a 2-digit row would cover every NC place
    assert (sl["status"] == "in_force").sum() == 19
    assert set(sl.index[sl["status"] == "pending"]) == {"3770540", "3732260"}  # sensitivity only
    assert sl.loc["3770540", "coding_notes"].startswith("SENSITIVITY ONLY")
    assert "3774440" not in sl.index  # Wilmington: coastal, excluded
    assert (sl["effective_date"] == pd.Timestamp("2027-01-15")).all()


def test_carthage_list_stays_in_its_own_file(reforms):
    assert not reforms["reform_id"].str.contains("arthage").any()
    assert (CONFIG_DIR / "reforms" / "nc_carthage_towns.csv").exists()


def test_bad_boolean_is_rejected(tmp_path):
    df = pd.read_csv(PATH, dtype=str, keep_default_na=False)
    df.loc[0, "by_right"] = "Ture"
    bad = tmp_path / "nc.csv"
    df.to_csv(bad, index=False)
    with pytest.raises(AssertionError, match="by_right"):
        _read(bad)


def test_adu_rules_round_4(reforms):
    r = reforms.set_index("reform_id")
    # Raleigh's 2019 overlay: not by right; TC-16-19 supersedes it
    assert r.at["NC-3755000-adu-2019", "by_right"] == False  # noqa: E712
    assert r.at["NC-3755000-adu-2020", "supersedes"] == "NC-3755000-adu-2019"
    # Wilmington LDC-7-424: adopted and effective 2024-05-21; owner occupancy unknown
    w = r.loc["NC-3774440-adu-2024"]
    assert w["effective_date"] == pd.Timestamp("2024-05-21") and w["adu_max_sqft"] == 1200
    assert pd.isna(w["owner_occ"])
    # Charlotte 2012-067A ends when the UDO replaces the ordinance (no inheritance into the UDO row)
    c = r.loc["NC-3712000-adu-2012"]
    assert c["end_date"] == pd.Timestamp("2023-06-01") and c["parking_min_per_unit"] == 1
    assert pd.isna(r.at["NC-3712000-adu-2023", "supersedes"])
