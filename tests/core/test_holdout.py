"""Holdouts never leak: the filter is on by default and unblinding needs a frozen prediction on main."""

import subprocess

import pandas as pd
import pytest

from lotline.config import Holdout
from lotline.validation import holdout

STPAUL = Holdout(
    test_id="V5-MN-STPAUL",
    place="St. Paul",
    geoid="2758000",
    outcome_from="2024-01-01",
    outcome_until="2026-12-31",
    reason="test",
)
CHARLOTTE = Holdout(
    test_id="V5-NC-CHARLOTTE",
    place="Charlotte",
    geoid="3712000",
    outcome_from="2023-06-01",
    outcome_until="2099-12-31",
    reason="test",
)


def _annual():
    return pd.DataFrame(
        {
            "geoid": ["2758000"] * 4 + ["2743000"] * 4,
            "year": [2022, 2023, 2024, 2025] * 2,
        }
    )


def test_annual_filter_drops_only_held_out_place_years():
    out = holdout.apply(_annual(), "MN", holdouts=[STPAUL], year_col="year")
    stpaul = out[out.geoid == "2758000"]
    assert stpaul.year.tolist() == [2022, 2023]
    assert len(out[out.geoid == "2743000"]) == 4  # other places untouched


def test_partial_year_is_held_out_whole():
    df = pd.DataFrame({"geoid": ["3712000"] * 3, "year": [2022, 2023, 2024]})
    assert holdout.apply(df, "NC", holdouts=[CHARLOTTE], year_col="year").year.tolist() == [2022]


def test_date_filter_uses_exact_window():
    df = pd.DataFrame({"geoid": ["3712000"] * 3, "issue_date": ["2023-05-31", "2023-06-01", "2024-02-01"]})
    out = holdout.apply(df, "NC", holdouts=[CHARLOTTE], date_col="issue_date")
    assert out.issue_date.tolist() == ["2023-05-31"]


def test_default_registry_comes_from_state_config():
    out = holdout.apply(_annual(), "MN", year_col="year")
    assert not ((out.geoid == "2758000") & (out.year >= 2024)).any()


def test_unblind_refused_without_frozen_prediction(tmp_path):
    _git_repo(tmp_path)
    with pytest.raises(holdout.UnblindError, match="no frozen prediction"):
        holdout.apply(
            _annual(), "MN", holdouts=[STPAUL], unblind=["V5-MN-STPAUL"], repo=tmp_path, year_col="year"
        )


def test_unblind_refused_when_frozen_file_uncommitted_or_off_main(tmp_path):
    _git_repo(tmp_path)
    frozen = holdout.frozen_path("V5-MN-STPAUL", tmp_path)
    frozen.parent.mkdir(parents=True)
    frozen.write_text("{}")
    with pytest.raises(holdout.UnblindError, match="not committed"):
        holdout.check_unblind("V5-MN-STPAUL", tmp_path)
    _run(tmp_path, "switch", "-q", "-c", "feature")
    _run(tmp_path, "add", ".")
    _run(tmp_path, "commit", "-q", "-m", "freeze")
    with pytest.raises(holdout.UnblindError, match="not on main"):
        holdout.check_unblind("V5-MN-STPAUL", tmp_path)


def test_unblind_allowed_once_frozen_prediction_is_on_main(tmp_path):
    _git_repo(tmp_path)
    frozen = holdout.frozen_path("V5-MN-STPAUL", tmp_path)
    frozen.parent.mkdir(parents=True)
    frozen.write_text("{}")
    _run(tmp_path, "add", ".")
    _run(tmp_path, "commit", "-q", "-m", "freeze")
    out = holdout.apply(
        _annual(), "MN", holdouts=[STPAUL], unblind=["V5-MN-STPAUL"], repo=tmp_path, year_col="year"
    )
    assert len(out) == 8


def test_unknown_test_id_rejected():
    with pytest.raises(holdout.UnblindError, match="unknown"):
        holdout.apply(_annual(), "MN", holdouts=[STPAUL], unblind=["V5-MN-NOPE"], year_col="year")


def _run(repo, *args):
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def _git_repo(path):
    _run(path, "init", "-q", "-b", "main")
    _run(path, "config", "user.email", "t@example.com")
    _run(path, "config", "user.name", "t")
    (path / "README").write_text("x")
    _run(path, "add", ".")
    _run(path, "commit", "-q", "-m", "init")


def test_year_only_permits_cannot_leak():
    # permits from a year-only source carry issue_year but no issue_date
    df = pd.DataFrame(
        {
            "jurisdiction_geoid": ["3712000"] * 5,
            "issue_date": ["2023-05-31", None, None, "2023-06-01", None],
            "issue_year": [2023, 2022, 2023, 2023, None],
        }
    )
    out = holdout.apply(
        df,
        "NC",
        holdouts=[CHARLOTTE],
        geoid_col="jurisdiction_geoid",
        date_col="issue_date",
        year_col="issue_year",
    )
    # kept: dated before the window, and a 2022 year-only row; dropped: a 2023 year-only row (overlaps the
    # window), a dated row inside it, and a row with neither date nor year (when unsure, hide it)
    assert out.index.tolist() == [0, 1]


def test_mask_needs_a_time_column():
    with pytest.raises(ValueError):
        holdout.held_out_mask(_annual(), [STPAUL])


def test_parcel_rolls_after_the_window_opens_stay_hidden():
    # a roll is a snapshot: one taken in or after the window shows what was built there, so no end date
    rolls = pd.DataFrame(
        {
            "jurisdiction_geoid": ["2758000"] * 5 + ["2743000"],
            "vintage": pd.array([2023, 2024, 2026, 2027, 2030, 2030], dtype="Int64"),
        }
    )
    hidden = holdout.held_out_mask(
        rolls, [STPAUL], geoid_col="jurisdiction_geoid", year_col="vintage", snapshot=True
    )
    assert hidden.tolist() == [False, True, True, True, True, False]  # Minneapolis (2743000) is not held out
    as_events = holdout.held_out_mask(rolls, [STPAUL], geoid_col="jurisdiction_geoid", year_col="vintage")
    assert not as_events.iloc[3]  # without snapshot, 2027 would wrongly pass


def test_parcel_roll_dates_beat_years_and_undated_years_are_strict():
    rolls = pd.DataFrame(
        {
            "jurisdiction_geoid": ["3712000"] * 3,
            "vintage": pd.array([2023, 2023, 2022], dtype="Int64"),
            "vintage_date": pd.to_datetime(["2023-05-31", None, None]),
        }
    )
    cols = dict(geoid_col="jurisdiction_geoid", date_col="vintage_date", year_col="vintage", snapshot=True)
    # dated before the UDO: usable; 2023 with no date: hidden (could be after June 1); 2022: usable
    assert holdout.held_out_mask(rolls, [CHARLOTTE], **cols).tolist() == [False, True, False]


def test_central_guard_checks_parcels_with_or_without_vintage_date(monkeypatch):
    monkeypatch.setattr(holdout, "holdouts_for", lambda state: [STPAUL])
    ok = pd.DataFrame({"jurisdiction_geoid": ["2758000"], "vintage": pd.array([2023], dtype="Int64")})
    holdout.assert_no_leak(ok, "parcels", "MN")
    late = ok.assign(vintage=pd.array([2025], dtype="Int64"))
    with pytest.raises(holdout.HoldoutLeak):
        holdout.assert_no_leak(late, "parcels", "MN")
    dated = ok.assign(vintage_date=pd.to_datetime(["2024-03-01"]))
    with pytest.raises(holdout.HoldoutLeak):
        holdout.assert_no_leak(dated, "parcels", "MN")


def test_reporting_geoids_are_held_out_like_the_place():
    # BPS files Charlotte's permits under Mecklenburg County: its rows carry Charlotte's outcomes
    clt = Holdout(
        test_id="V5-NC-CHARLOTTE",
        place="Charlotte",
        geoid="3712000",
        outcome_from="2023-06-01",
        outcome_until="2099-12-31",
        reason="test",
        reporting_geoids=["37119"],
        reporting_reason="BPS reports Charlotte under the county",
    )
    bps = pd.DataFrame({"geoid": ["37119", "37119", "37119", "37183"], "year": [2022, 2023, 2025, 2025]})
    hidden = holdout.held_out_mask(bps, [clt], geoid_col="geoid", year_col="year")
    assert hidden.tolist() == [False, True, True, False]  # Wake (37183) is untouched


def test_reporting_geoids_need_a_reason():
    with pytest.raises(ValueError, match="reporting_reason"):
        Holdout(
            test_id="V5-NC-CHARLOTTE",
            place="Charlotte",
            geoid="3712000",
            outcome_from="2023-06-01",
            outcome_until="2099-12-31",
            reason="test",
            reporting_geoids=["37119"],
        )


def test_the_real_nc_config_holds_out_mecklenburg_county():
    (clt,) = holdout.holdouts_for("NC")
    assert "37119" in clt.geoids and clt.reporting_reason


def test_holdout_window_edges_are_inclusive_and_exact():
    # St. Paul's window ends 2026-12-31: the last day is hidden, the next day is not (dates win over years)
    permits = pd.DataFrame(
        {
            "jurisdiction_geoid": ["2758000"] * 4,
            "issue_date": pd.to_datetime(["2023-12-31", "2024-01-01", "2026-12-31", "2027-01-01"]),
        }
    )
    hidden = holdout.held_out_mask(permits, [STPAUL], geoid_col="jurisdiction_geoid", date_col="issue_date")
    assert hidden.tolist() == [False, True, True, False]


OREGON = Holdout(
    test_id="V9-OR-TRANSFER",
    place="Oregon (statewide)",
    geoid="41",
    outcome_from="2018-01-01",
    outcome_until="2099-12-31",
    reason="test",
)


def test_statewide_holdout_hides_every_jurisdiction_in_the_state_only():
    # place (7), township-style (10), county remainder (5) and state total (2) in Oregon; Ohio rows untouched
    bps = pd.DataFrame(
        {
            "geoid": [
                *["4159000", "4105800", "4100000001", "41051", "41"],
                *["41051", "3918000", "39049", "4159000"],
            ],
            "year": [2018, 2025, 2019, 2020, 2021, 2017, 2020, 2020, 2017],
        }
    )
    hidden = holdout.held_out_mask(bps, [OREGON], geoid_col="geoid", year_col="year")
    assert hidden.tolist() == [True, True, True, True, True, False, False, False, False]


def test_statewide_holdout_hides_every_oregon_roll_from_the_window_on():
    rolls = pd.DataFrame(
        {"jurisdiction_geoid": ["4159000", "4159000", "4105800"], "vintage": [2017, 2018, 2026]}
    )
    hidden = holdout.held_out_mask(
        rolls, [OREGON], geoid_col="jurisdiction_geoid", year_col="vintage", snapshot=True
    )
    assert hidden.tolist() == [False, True, True]


def test_holdout_geoid_must_be_a_state_place_or_township():
    for bad in ["4", "411", "41051", "41590000"]:
        with pytest.raises(ValueError):
            Holdout(
                test_id="V9-OR-TRANSFER",
                place="x",
                geoid=bad,
                outcome_from="2018-01-01",
                outcome_until="2099-12-31",
                reason="test",
            )
    assert OREGON.statewide and not STPAUL.statewide


def test_the_real_or_config_holds_out_all_of_oregon_from_2018():
    (v9,) = holdout.holdouts_for("OR")
    assert v9.test_id == "V9-OR-TRANSFER" and v9.statewide and v9.geoid == "41"
    assert str(v9.outcome_from) == "2018-01-01"


# Issue #283: gaps for a statewide holdout whose window is in the past (V9, Oregon)


def _acs(rows):
    return pd.DataFrame(rows, columns=["geo", "end_year", "table_id"])


def test_acs_stock_vintages_overlapping_the_window_are_hidden_for_every_oregon_level():
    df = _acs(
        [
            ("state:41", 2017, "B25024"),  # 2013-2017: before the window, kept
            ("state:41", 2018, "B25024"),  # 2014-2018 overlaps 2018: hidden
            ("county:41051", 2024, "B25034"),
            ("place:4159000", 2020, "B25003"),
            ("tract:41051000100", 2022, "B25024"),
            ("place:4159000", 2022, "B25064"),  # rent: a market input, kept (Ben, 2026-11-04)
            ("place:4159000", 2022, "B25077"),  # value: kept
            ("place:3918000", 2022, "B25024"),  # Ohio: untouched
        ]
    )
    hidden = holdout.acs_held_out_mask(df, [OREGON])
    assert hidden.tolist() == [False, True, True, True, True, False, False, False]


def test_acs_filter_ignores_place_holdouts():
    # V5 places keep their ACS inputs as before; only statewide holdouts filter ACS
    df = _acs([("place:2758000", 2024, "B25024")])
    assert not holdout.acs_held_out_mask(df, [STPAUL]).any()


def test_acs_apply_and_central_guard(monkeypatch):
    df = _acs([("place:4159000", 2017, "B25024"), ("place:4159000", 2019, "B25024")])
    out = holdout.apply_acs(df, "OR", holdouts=[OREGON])
    assert out.end_year.tolist() == [2017]
    monkeypatch.setattr(holdout, "holdouts_for", lambda state: [OREGON])
    with pytest.raises(holdout.HoldoutLeak, match="acs_geo_year"):
        holdout.assert_no_leak(df, "acs_geo_year", "OR")
    holdout.assert_no_leak(out, "acs_geo_year", "OR")


def test_state_bps_totals_drop_statewide_held_out_years(monkeypatch):
    monkeypatch.setattr(holdout, "holdouts_for", lambda state: [OREGON] if state == "OR" else [STPAUL])
    totals = pd.DataFrame({"state_fips": ["41", "41", "27", "27"], "year": [2017, 2018, 2018, 2025]})
    out = holdout.drop_statewide(totals, geoid_col="state_fips", year_col="year")
    # Oregon from 2018 goes; Minnesota's state total stays (place holdouts are skipped in V0 instead)
    assert list(zip(out.state_fips, out.year, strict=True)) == [("41", 2017), ("27", 2018), ("27", 2025)]


def test_bps_state_load_filters_oregon(monkeypatch, tmp_path):
    from lotline.adapters.national import bps_state

    def fake_fetch(url, dest, **kw):
        dest.write_text("")
        return dest

    monkeypatch.setattr(bps_state, "fetch", fake_fetch)
    monkeypatch.setattr(
        bps_state,
        "parse",
        lambda text, year: pd.DataFrame({"state_fips": ["41", "39"], "year": [year, year]}),
    )

    class Store:
        def raw(self, source, year):
            return tmp_path

    out = bps_state.load(Store(), range(2017, 2019))
    assert list(zip(out.state_fips, out.year, strict=True)) == [("41", 2017), ("39", 2017), ("39", 2018)]


def test_bps_reads_region_and_fips_from_the_state_config():
    from lotline.adapters.national import bps
    from lotline.config import load_state

    assert load_state("OR").bps_region == "West Region"
    assert bps.file_url("West Region", 2020).endswith("/West%20Region/we2020a.txt")
    raw = pd.DataFrame(
        {
            "state_fips": ["41", "39"],
            "id6": ["000001", "000002"],
            "county": ["051", "049"],
            "fips_place": ["59000", "18000"],
            "fips_mcd": ["00000", "00000"],
            "name": ["Portland", "Columbus"],
            "months_reported": [12, 12],
        }
        | {f"units_{s}{r}": [1, 1] for s in ["1", "2", "3_4", "5p"] for r in ["", "_rep"]}
    )
    out = bps.to_canonical(raw, "OR")
    assert out.geoid.tolist() == ["4159000"]


def test_statewide_holdout_hides_rows_with_no_geoid():
    # Found by WS-OR after #287: BPS rows Census filed without FIPS codes have a null GEOID and escaped the
    # prefix match. In the state's own table they belong to the state, so they are hidden in the window.
    bps = pd.DataFrame(
        {"geoid": pd.array([None, None, "4159000"], dtype="string"), "year": [2017, 2018, 2019]}
    )
    hidden = holdout.held_out_mask(bps, [OREGON], geoid_col="geoid", year_col="year")
    assert hidden.tolist() == [False, True, True]
    out = holdout.apply(bps, "OR", holdouts=[OREGON], year_col="year")
    assert out.year.tolist() == [2017]
    # a place holdout still never hides a null-GEOID row
    assert not holdout.held_out_mask(bps, [STPAUL], geoid_col="geoid", year_col="year").any()
