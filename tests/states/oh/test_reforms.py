"""config/reforms/oh.csv: every row is a valid `reforms` record coded with the protocol §5.4 rubric.

The CSV is read as text (empty cell = unknown) and the rubric's true/false columns are parsed explicitly, so a
typo like "Ture" fails instead of becoming null.
"""

import pandas as pd
import pytest

from lotline.config import CONFIG_DIR
from lotline.schemas import columns, validate

PATH = CONFIG_DIR / "reforms" / "oh.csv"
BOOL_COLS = ["by_right", "owner_occ", "adu_detached_allowed", "lot_split"]
PLACES = {  # Ohio's 20 largest places (2020 census), the ADU rule round of 2026-10-20
    "3918000": "Columbus",
    "3916000": "Cleveland",
    "3915000": "Cincinnati",
    "3977000": "Toledo",
    "3901000": "Akron",
    "3921000": "Dayton",
    "3961000": "Parma",
    "3912000": "Canton",
    "3944856": "Lorain",
    "3933012": "Hamilton",
    "3988000": "Youngstown",
    "3974118": "Springfield",
    "3940040": "Kettering",
    "3925256": "Elyria",
    "3919778": "Cuyahoga Falls",
    "3949840": "Middletown",
    "3941664": "Lakewood",
    "3954040": "Newark",
    "3925704": "Euclid",
    "3922694": "Dublin",
}
ROUND_2 = {  # the 2026-10-26 round: places 21-40 and the Franklin County places in franklin_permits
    "3929106": "Gahanna",
}


def _read() -> pd.DataFrame:
    df = pd.read_csv(PATH, dtype=str, keep_default_na=False).replace("", pd.NA)
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
    assert len(reforms) >= 4
    assert (reforms["state"] == "OH").all()
    assert set(reforms["jurisdiction_geoid"]) <= set(PLACES) | set(ROUND_2) | {"39"}


def test_every_row_has_an_https_source(reforms):
    for urls in reforms["source_url"]:
        assert all(u.strip().startswith("https://") for u in urls.split(";")), urls


def test_ids_name_place_theme_and_year(reforms):
    for _, r in reforms.iterrows():
        prefix = f"OH-{r.jurisdiction_geoid}-{r.theme}-{r.effective_date.year}"
        assert r.reform_id.startswith(prefix), r.reform_id


def test_adoption_never_after_effect(reforms):
    dated = reforms.dropna(subset=["adoption_date"])
    assert (dated["adoption_date"] <= dated["effective_date"]).all()


def test_each_named_reform_is_coded(reforms):
    ids = set(reforms["reform_id"])
    assert "OH-3915000-missing_middle-2024" in ids  # Cincinnati Connected Communities
    assert "OH-3918000-other-2024" in ids  # Columbus Zone In phase 1
    assert "OH-3918000-adu-2025" in ids  # Columbus ADU ordinance
    assert "OH-3916000-other-2024" in ids  # Cleveland form-based code pilot


def test_columbus_adu_rubric(reforms):
    adu = reforms.set_index("reform_id").loc["OH-3918000-adu-2025"]
    assert adu.by_right and not adu.owner_occ and adu.adu_detached_allowed
    assert adu.adus_per_lot == 1 and adu.parking_min_per_unit == 0
    assert adu.effective_date == pd.Timestamp("2025-12-24")  # the city's BZS notice


def test_euclid_missing_middle_rubric(reforms):
    mm = reforms.set_index("reform_id").loc["OH-3925704-missing_middle-2024"]
    assert mm.by_right and mm.unit_cap == 2 and mm.min_lot_sqft == 5000
    assert mm.effective_date == pd.Timestamp("2024-11-06") and mm.coverage_zones == "U1"


def test_single_coder_rows_have_no_second_coder(reforms):
    single = reforms["coder_agreement"] == "single_coder"
    assert reforms.loc[single, "coder_2"].isna().all()


def test_no_adu_rows_follow_the_convention(reforms):
    none = reforms[(reforms["theme"] == "adu") & (reforms["adus_per_lot"] == 0)]
    assert len(none) >= 8
    assert (~none["by_right"].astype(bool)).all()
    assert none["coding_notes"].str.startswith("NO ADU RULE").all()


def test_ended_rules_hand_over_to_their_successor(reforms):
    by_id = reforms.set_index("reform_id")
    for rid, old in by_id["supersedes"].dropna().items():
        if pd.notna(by_id.at[old, "end_date"]):
            assert by_id.at[old, "end_date"] <= by_id.at[rid, "effective_date"], rid


@pytest.mark.parametrize(
    "geoid, as_of, expected",
    [
        ("3918000", "2024-12-31", "none"),  # Columbus before Ord. 2526-2025
        ("3918000", "2026-01-31", "handbook"),
        ("3915000", "2022-12-31", "none"),
        ("3915000", "2024-12-31", "partial"),  # owner occupancy
        ("3916000", "2025-12-31", "none"),
        ("3921000", "2024-12-31", "partial"),  # conditional use
        ("3954040", "2025-12-31", "none"),
        ("3974118", "2025-12-31", "partial"),
    ],
)
def test_scenario_reads_the_rule_class(geoid, as_of, expected):
    from lotline.model.scenarios import adu

    rules = adu.current_rules(adu.load_reforms("OH"), [geoid], "39", pd.Timestamp(as_of))
    assert rules.loc[0, "rule_class"] == expected
