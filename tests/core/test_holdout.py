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
