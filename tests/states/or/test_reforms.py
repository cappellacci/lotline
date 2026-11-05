"""config/reforms/or.csv and the generator of Oregon's state-law rows (scripts/dev/or_state_reform_rows.py).

The tier rules are checked on a synthetic set of places and counties built to sit on each statutory threshold
(SB 1051: > 2,500 / > 15,000; HB 2001: >= 25,000, Metro cities > 1,000, > 10,000 and < 25,000; 2023 c.223:
2,500 to 10,000; HB 2138: Metro cities >= 1,000). The committed CSV is then checked as a `reforms` table.
"""

import importlib.util
from pathlib import Path

import pandas as pd
import pytest

from lotline.config import CONFIG_DIR
from lotline.schemas import columns, validate

ROOT = Path(__file__).resolve().parents[3]
_spec = importlib.util.spec_from_file_location(
    "or_rows", ROOT / "scripts" / "dev" / "or_state_reform_rows.py"
)
gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen)

PATH = CONFIG_DIR / "reforms" / "or.csv"
BOOL_COLS = ["by_right", "owner_occ", "adu_detached_allowed", "lot_split"]

# geoid, name, 2020 population, in Metro?
PLACES = [
    ("4100001", "Big", 25000, False),  # large tier exactly at 25,000
    ("4100002", "Almost", 24999, False),  # medium
    ("4100003", "Tenk", 10000, False),  # not medium (needs > 10,000); small tier from 2025
    ("4100004", "Tenk1", 10001, False),  # medium
    ("4100005", "Small", 2500, False),  # small tier (>= 2,500) but no SB 1051 ADU duty (needs > 2,500)
    ("4100006", "Tiny", 2400, False),  # nothing
    ("4100007", "MetroMid", 5000, True),  # Metro city: large tier, not small
    ("4100008", "MetroK", 1000, True),  # Metro, 1,000: excluded in 2019 (1,000 or fewer), covered in 2027
    ("4100009", "MetroTiny", 600, True),  # Metro, under 1,000: never
]
COUNTIES = [("41005", "Clackamas", 400000), ("41001", "Baker", 16000), ("41069", "Wheeler", 1400)]


@pytest.fixture(scope="module")
def synthetic() -> pd.DataFrame:
    places = pd.DataFrame([p[:3] for p in PLACES], columns=["geoid", "name", "pop"])
    counties = pd.DataFrame(COUNTIES, columns=["geoid", "name", "pop"])
    metro = {p[0] for p in PLACES if p[3]}
    return gen.generate(places, counties, metro)


def _ids(df: pd.DataFrame, suffix: str) -> set[str]:
    return set(df.loc[df["reform_id"].str.endswith(suffix), "jurisdiction_geoid"])


def test_sb1051_adu_duty_is_strictly_over_2500_and_15000(synthetic):
    adu = _ids(synthetic, "-adu-2018")
    assert adu == {"4100001", "4100002", "4100003", "4100004", "4100007", "41005", "41001"}
    assert _ids(synthetic, "-adu-2020") == adu  # HB 2001 tightens the same set


def test_hb2001_large_tier_is_25000_plus_and_metro_cities_over_1000(synthetic):
    assert _ids(synthetic, "-missing_middle-2022") == {"4100001", "4100007", "41005"}


def test_hb2001_medium_tier_is_between_10000_and_25000_outside_metro(synthetic):
    assert _ids(synthetic, "-missing_middle-2021") == {"4100002", "4100004"}


def test_2023_small_tier_is_2500_to_10000_outside_metro(synthetic):
    assert _ids(synthetic, "-missing_middle-2025") == {"4100003", "4100005"}


def test_hb2138_counts_metro_cities_of_exactly_1000(synthetic):
    assert _ids(synthetic, "-missing_middle-2027") == {"4100001", "4100007", "4100008"}


def test_land_divisions_follow_each_middle_housing_row_and_never_start_before_july_2022(synthetic):
    s = synthetic.set_index("reform_id")
    for _rid, row in s[s.index.str.endswith("-landdiv")].iterrows():
        base = s.loc[row["supersedes"]]
        assert base["jurisdiction_geoid"] == row["jurisdiction_geoid"]
        assert row["effective_date"] == max(base["effective_date"], "2022-07-01")
        assert row["lot_split"] == "True"


def test_amendments_supersede_rows_that_exist(synthetic):
    ids = set(synthetic["reform_id"])
    sup = synthetic["supersedes"].replace("", pd.NA).dropna()
    assert set(sup) <= ids


def test_local_rows_survive_regeneration(tmp_path, synthetic):
    local = {c: "" for c in gen.COLUMNS} | {"reform_id": "OR-4159000-adu-2010", "coding_notes": "local row"}
    path = tmp_path / "or.csv"
    pd.concat([pd.DataFrame([local]), synthetic]).to_csv(path, index=False)
    out = gen.merged(synthetic, path)
    assert "OR-4159000-adu-2010" in set(out["reform_id"])
    assert len(out) == len(synthetic) + 1  # old generated rows replaced, not duplicated


# --- the committed file -------------------------------------------------------------------------------------


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
    assert len(reforms) > 0


def test_every_row_has_an_https_source_and_a_quote(reforms):
    assert reforms["source_url"].str.startswith("https://").all()
    assert reforms["source_quote"].notna().all()


def test_adoption_never_after_effect(reforms):
    both = reforms.dropna(subset=["adoption_date"])
    assert (both["adoption_date"] <= both["effective_date"]).all()


def test_no_statewide_row_stands_in_for_the_tiers(reforms):
    """Coverage depends on city size, so state law is coded per place, never as jurisdiction '41'."""
    assert not (reforms["jurisdiction_geoid"] == "41").any()


def test_known_places_land_in_the_right_tier(reforms):
    tier = {
        g: set(reforms.loc[reforms["jurisdiction_geoid"] == g, "reform_id"]) for g in ("4159000", "4105800")
    }
    assert "OR-4159000-missing_middle-2022" in tier["4159000"]  # Portland: large (and Metro)
    assert "OR-4105800-missing_middle-2022" in tier["4105800"]  # Bend: 99,178 in 2020
    metro = set(pd.read_csv(gen.METRO, dtype=str)["geoid"])
    assert len(metro) == 24
    generated = reforms["coding_notes"].str.startswith(gen.GENERATED)
    medium = generated & reforms["reform_id"].str.endswith("-missing_middle-2021")
    mm = set(reforms.loc[medium, "jurisdiction_geoid"])
    assert not mm & metro  # the duplex-only tier is for cities outside Metro


def test_local_rows_for_portland_bend_and_metro_adopters(reforms):
    r = reforms.set_index("reform_id")
    local = r[~r["coding_notes"].fillna("").str.startswith(gen.GENERATED)]
    assert {
        "OR-4159000-missing_middle-2021",
        "OR-4159000-fees-2018",
        "OR-4105800-missing_middle-2021",
    } <= set(local.index)
    # Portland's Residential Infill Project took effect before HB 2001's deadline for large cities
    assert r.loc["OR-4159000-missing_middle-2021", "effective_date"] < pd.Timestamp("2022-06-30")
    # Late Metro adopters replace the state row rather than standing beside it
    for rid in ("OR-4173650-missing_middle-2022-local", "OR-4140550-missing_middle-2022-local"):
        assert r.loc[rid, "supersedes"] == rid.removesuffix("-local")


@pytest.mark.parametrize("geoid", ["4173650", "4140550"])  # Tigard, Lake Oswego: local code a week late
def test_late_adopters_keep_state_coverage_until_their_own_code_takes_over(reforms, geoid):
    """The supersede rule of `model/scenarios/adu._live`: a row drops out only when a row superseding it is
    itself in force. The state chain (HB 2001 row, then its SB 458 land-division row from 07-01) covers the
    place from 2022-06-30 with no gap; the local row adds itself from 07-07 and never before."""

    def live(day):
        r = reforms[(reforms["jurisdiction_geoid"] == geoid) & (reforms["theme"] == "missing_middle")]
        r = r[(r["effective_date"] <= pd.Timestamp(day)) & (r["end_date"].isna() | (r["end_date"] > day))]
        return set(r["reform_id"]) - set(r["supersedes"].dropna())

    state = {f"OR-{geoid}-missing_middle-2022", f"OR-{geoid}-missing_middle-2022-landdiv"}
    local = f"OR-{geoid}-missing_middle-2022-local"
    assert live("2022-06-29") == set()
    for day in ("2022-06-30", "2022-07-01", "2022-07-06"):
        assert live(day) & state and local not in live(day), day
    assert local in live("2022-07-07") and live("2022-07-07") & state
