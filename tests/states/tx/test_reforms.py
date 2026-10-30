"""config/reforms/tx.csv: every row is a valid `reforms` record coded with the protocol §5.4 rubric.

The CSV is read as text (empty cell = unknown) and the rubric's true/false columns are parsed explicitly, so a
typo like "Ture" fails instead of becoming null. No reforms loader exists in `lotline.config` yet.
"""

import pandas as pd
import pytest

from lotline.config import CONFIG_DIR
from lotline.schemas import columns, validate

PATH = CONFIG_DIR / "reforms" / "tx.csv"
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
    assert len(reforms) >= 10
    assert (reforms["state"] == "TX").all()


def test_every_row_has_an_opened_source(reforms):
    for urls in reforms["source_url"]:
        assert all(u.strip().startswith("https://") for u in urls.split(";")), urls


def test_geoids_are_texas_state_or_place(reforms):
    geoids = reforms["jurisdiction_geoid"]
    assert geoids.str.startswith("48").all()
    assert geoids.str.len().isin([2, 7]).all()


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
    # Austin HOME phase 1: up to three units on SF-1/2/3 lots, applications from 2024-02-05
    assert r.at["TX-4805000-missing_middle-2024", "unit_cap"] == 3
    assert r.at["TX-4805000-missing_middle-2024", "effective_date"] == pd.Timestamp("2024-02-05")
    # Austin HOME phase 2: 1,800 sq ft minimum lot
    assert r.at["TX-4805000-lot_size-2024a", "min_lot_sqft"] == 1800
    # Houston: 3,500 sq ft by right, citywide from 2013-05-24
    assert r.at["TX-4835000-lot_size-2013", "effective_date"] == pd.Timestamp("2013-05-24")
    # SB 15: lots can't be required to exceed 3,000 sq ft, from 2025-09-01
    assert r.at["TX-48-lot_size-2025", "min_lot_sqft"] == 3000
    assert r.at["TX-48-lot_size-2025", "effective_date"] == pd.Timestamp("2025-09-01")


def test_bad_boolean_is_rejected(tmp_path):
    df = pd.read_csv(PATH, dtype=str, keep_default_na=False)
    df.loc[0, "by_right"] = "Ture"
    bad = tmp_path / "tx.csv"
    df.to_csv(bad, index=False)
    with pytest.raises(AssertionError, match="by_right"):
        _read(bad)


# The 20 largest Texas places by 2020 population (Census PL 94-171, `jurisdictions.pop_2020`)
TOP_20 = {
    "4835000": "Houston",
    "4865000": "San Antonio",
    "4819000": "Dallas",
    "4805000": "Austin",
    "4827000": "Fort Worth",
    "4824000": "El Paso",
    "4804000": "Arlington",
    "4817000": "Corpus Christi",
    "4858016": "Plano",
    "4845000": "Lubbock",
    "4837000": "Irving",
    "4841464": "Laredo",
    "4829000": "Garland",
    "4827684": "Frisco",
    "4803000": "Amarillo",
    "4830464": "Grand Prairie",
    "4845744": "McKinney",
    "4810768": "Brownsville",
    "4839148": "Killeen",
    "4856000": "Pasadena",
}


# Not coded yet: no ADU source could be opened (official code hosts block automated access); second coder
PENDING = {"4856000": "Pasadena"}  # Corpus Christi coded 2026-10-27 from Ben's research workbook


def test_every_top_20_place_has_an_adu_rule(reforms):
    adu = reforms[reforms["theme"] == "adu"]
    coded = set(adu["jurisdiction_geoid"])
    missing = {g: n for g, n in TOP_20.items() if g not in coded and g not in PENDING}
    assert not missing, f"no ADU row (coded rule or explicit 'none'): {missing}"
    assert not set(PENDING) & coded, "a pending place is now coded: drop it from PENDING"


def test_no_adu_rows_are_explicit(reforms):
    # A place whose code allows no ADU in single-family zones is coded adus_per_lot = 0, not left blank
    none = reforms[(reforms["theme"] == "adu") & (reforms["adus_per_lot"] == 0)]
    assert (none["by_right"] == False).all()  # noqa: E712
    assert none["coding_notes"].str.startswith("NO ADU RULE").all()
    assert none["source_url"].notna().all()


def test_austin_adu_history(reforms):
    r = reforms.set_index("reform_id")
    # Ord. 20151119-080: 15% of a 5,750 sq ft lot, one parking space
    assert r.at["TX-4805000-adu-2015", "adu_max_sqft"] == 862
    assert r.at["TX-4805000-adu-2015", "parking_min_per_unit"] == 1
    # parking minimums gone 2023-11-02; HOME phase 1 from 2024-02-05
    assert r.at["TX-4805000-adu-2023", "supersedes"] == "TX-4805000-adu-2015"
    assert r.at["TX-4805000-adu-2024", "effective_date"] == pd.Timestamp("2024-02-05")
    assert r.at["TX-4805000-adu-2024", "supersedes"] == "TX-4805000-adu-2023"


def test_corrections_2026_10_30(reforms):
    # Ben's decisions on tx-corrections-2026-10-29.csv, checked against the local PDFs where noted
    r = reforms.set_index("reform_id")
    # Ord. 20151119-080 Part 9
    assert r.at["TX-4805000-adu-2015", "effective_date"] == pd.Timestamp("2015-11-30")
    assert r.at["TX-4819000-adu-2018", "effective_date"] == pd.Timestamp("2018-06-30")  # published 2018-06-30
    assert r.at["TX-4819000-adu-2018", "adoption_date"] == pd.Timestamp("2018-06-27")
    assert pd.isna(r.at["TX-4824000-adu-2011", "parking_min_per_unit"])  # Ord. 17532 sets no ADU minimum
    assert r.at["TX-4845744-adu-2022", "adus_per_lot"] == 1  # McKinney: rentable ADU, not "none"
    assert r.at["TX-4827684-adu-2019", "supersedes"] == "TX-4827684-adu-2011"
    assert r.at["TX-4865000-adu-2023", "supersedes"] == "TX-4865000-adu-2010"
    assert r.at["TX-4815976-adu-2018", "effective_date"] == pd.Timestamp("2018-11-29")  # Ord. 2018-4059
    assert r.at["TX-4801000-missing_middle-2010", "unit_cap"] == 1  # Ben: district text governs
    renamed = {"TX-4865000-adu-2001", "TX-4827684-adu-2021", "TX-4841464-adu-1992", "TX-4815976-adu-2023"}
    assert not renamed & set(r.index)
