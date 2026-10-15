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
PLACES = {"3915000": "Cincinnati", "3916000": "Cleveland", "3918000": "Columbus"}


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
    assert set(reforms["jurisdiction_geoid"]) <= set(PLACES) | {"39"}


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
    assert adu.effective_date == pd.Timestamp("2025-12-25")


def test_single_coder_rows_have_no_second_coder(reforms):
    single = reforms["coder_agreement"] == "single_coder"
    assert reforms.loc[single, "coder_2"].isna().all()
