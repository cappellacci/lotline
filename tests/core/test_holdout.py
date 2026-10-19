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
