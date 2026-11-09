"""WS-NC-GUTCHECK: the trailing observed-ADU window (`adu.observed_per_year`) and the `historical_floor` check.

Synthetic fixtures only; each expected value is worked by hand in the docstrings of the functions tested.
"""

from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd
import pytest

from lotline.config import Holdout
from lotline.model import gutcheck
from lotline.model.scenarios import adu


def _counts(rows):
    return pd.DataFrame(rows, columns=["geoid", "year", "adu_permits"])


# ---- the observed window ---------------------------------------------------------------------------------


def test_observed_window_trails_the_origin():
    # place A: 2019-21 = 9 each (outside the window), 2022-25 = 1, 2, 3, 6 -> 12 / 4 = 3.0
    rows = [("A", y, 9) for y in (2019, 2020, 2021)] + [("A", 2022, 1), ("A", 2023, 2), ("A", 2024, 3)]
    rows += [("A", 2025, 6)]
    out = adu.observed_per_year(_counts(rows), origin=2025, n_years=4, stops={})
    assert out["A"] == pytest.approx(3.0)


def test_observed_window_for_a_backtest_origin_is_d019s():
    # origin 2022 -> 2019-2022, D-019's fixed window: 9, 9, 9, 1 -> 7.0; later years are not read
    rows = [("A", y, 9) for y in (2019, 2020, 2021)] + [("A", 2022, 1), ("A", 2025, 100)]
    out = adu.observed_per_year(_counts(rows), origin=2022, n_years=4, stops={})
    assert out["A"] == pytest.approx(7.0)


def test_held_out_place_window_ends_before_its_holdout():
    # B held out from 2023: window 2019-2022 = 2, 2, 4, 0 (missing year counts 0) -> 2.0, never the
    # partly held-out 2023 (which the store would show as a low count)
    rows = [("B", 2019, 2), ("B", 2020, 2), ("B", 2021, 4), ("B", 2023, 1)]
    out = adu.observed_per_year(_counts(rows), origin=2025, n_years=4, stops={"B": 2023})
    assert out["B"] == pytest.approx(2.0)


def _holdout(geoid, start, released=None, reporting=()):
    return Holdout(
        test_id="V5-NC-TEST",
        place="x",
        geoid=geoid,
        outcome_from=start,
        outcome_until=dt.date(2099, 12, 31),
        reason="test",
        reporting_geoids=list(reporting),
        reporting_reason="test" if reporting else None,
        released_on=released,
        released_note="test" if released else None,
    )


def test_holdout_stops_cover_reporting_geoids_and_skip_released():
    hs = [
        _holdout("3712000", dt.date(2023, 6, 1), reporting=["37119"]),
        _holdout("41", dt.date(2018, 1, 1), released=dt.date(2026, 11, 5)),
    ]
    assert adu.holdout_stops(hs) == {"3712000": 2023, "37119": 2023}
    assert adu.holdout_stops([_holdout("41", dt.date(2018, 1, 1))]) == {"*": 2018}


# ---- historical_floor -----------------------------------------------------------------------------------


OBS = {2021: 61, 2022: 100, 2023: 146, 2024: 109, 2025: 123}  # floor 2023-25 = 378 / 3 = 126


def test_floor_is_the_trailing_mean():
    assert gutcheck.floor(OBS, 2025, 3) == pytest.approx(126.0)
    assert gutcheck.floor(OBS, 2025, 6) is None  # 2020 missing


def test_below_history_is_flagged_not_failed():
    draws = np.array([[80.0] * 5, [90.0] * 5, [100.0] * 5])  # median 90 a year -> 90 / 126 = 0.714
    row = gutcheck.historical_floor("adu", draws, OBS, 2025, scope="test", years=3)
    assert row["verdict"] == "partial"
    assert row["value"] == pytest.approx(90 / 126)
    assert "FLAG" in row["label"]


def test_at_or_above_history_passes():
    draws = np.array([[130.0] * 5, [140.0] * 5, [150.0] * 5])  # median 140 -> 1.111
    row = gutcheck.historical_floor("adu", draws, OBS, 2025, scope="test", years=3)
    assert row["verdict"] == "pass"
    assert row["value"] == pytest.approx(140 / 126)


def test_a_stated_reason_passes_and_is_shown():
    draws = np.array([[80.0] * 5, [90.0] * 5, [100.0] * 5])
    row = gutcheck.historical_floor("adu", draws, OBS, 2025, scope="test", years=3, reason="R")
    assert row["verdict"] == "pass"
    assert "reason: R" in row["label"]


def test_one_dimensional_draws_are_window_totals():
    # five-year totals 450 / 5 = 90 a year, as above
    row = gutcheck.historical_floor("adu", np.array([400.0, 450.0, 500.0]), OBS, 2025, scope="t", years=3)
    assert row["value"] == pytest.approx(90 / 126)


def test_no_history_is_not_run():
    row = gutcheck.historical_floor("adu", np.ones((3, 5)), {2025: 0}, 2025, scope="t", years=1)
    assert row["verdict"] == "not_run"
    assert row["value"] is None


def test_reasons_file_parses(tmp_path):
    f = tmp_path / "r.yaml"
    f.write_text("nc:\n  adu: because\n")
    assert gutcheck.reasons(f) == {"NC": {"adu": "because"}}
    assert gutcheck.reasons(tmp_path / "missing.yaml") == {}
    assert isinstance(gutcheck.reasons(), dict)  # the committed file parses
