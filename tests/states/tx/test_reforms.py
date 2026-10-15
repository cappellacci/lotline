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
