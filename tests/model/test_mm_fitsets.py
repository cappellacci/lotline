"""`mm_fitsets`: the missing-middle fit sets moved from scripts/dev (calibration phase 3); small fixtures."""

import numpy as np
import pandas as pd
import pytest

from lotline.model import calibrate_mm as cal
from lotline.model import mm_fitsets as fs


def test_short_names():
    assert fs.short("Wake Forest town") == "Wake Forest"
    assert fs.short("St. Louis Park city") == "St. Louis Park"
    assert fs.short("Euclid") == "Euclid"


def test_named_geoids_matches_places_only():
    j = pd.DataFrame(
        {
            "geoid": ["01", "02", "03"],
            "name": ["Wilson city", "Wilson township", "Garner town"],
            "kind": ["place", "township", "place"],
        }
    )
    assert fs.named_geoids(j, ["Wilson", "Garner"]) == {"Wilson": "01", "Garner": "03"}
    with pytest.raises(ValueError, match="Sanford: 0 places"):
        fs.named_geoids(j, ["Sanford"])


def test_units_ratio_counts_2_to_4_units_in_window():
    bps = pd.DataFrame(
        {
            "geoid": ["01", "01", "01", "02"],
            "year": [2015, 2016, 2025, 2020],
            "units_2": [100, 4, 2, 6],
            "units_3_4": [100, 3, 0, 0],
            "bldgs_2": [50, 2, 1, 3],
            "bldgs_3_4": [30, 1, 0, 0],
        }
    )
    # 2015 is outside 2016-2025; 02 is not asked for: homes 4 + 3 + 2 = 9 in 2 + 1 + 1 = 4 buildings
    assert fs.units_ratio(bps, ["01"]) == (9.0, 4.0)


def test_units_per_building_by_hand():
    u = fs.units_per_building({"NC": (216, 106), "OH": (162, 59), "MN": (40, 10)})
    assert u["value"] == pytest.approx(418 / 175)  # 2.389
    assert u["low"] == pytest.approx(216 / 106)  # NC 2.038
    assert u["high"] == pytest.approx(162 / 59)  # OH 2.746; MN's 4.0 is left out


def test_units_per_building_reproduces_config_totals():
    """D-038's record: 10,210 homes in 4,912 buildings -> 2.08; NC 2.04 and OH 2.75 the range."""
    by_state = {"NC": (216, 106), "OH": (162, 59), "MN": (40, 10), "TX": (9792, 4737)}
    u = fs.units_per_building(by_state)
    assert round(u["value"], 2) == 2.08 and round(u["low"], 2) == 2.04 and round(u["high"], 2) == 2.75


def _event(year=2020, cls="cap", prior=1, new=4):
    return cal.Event(year, prior, new, cls)


def test_split_events_keeps_usable_and_separates_tests():
    lubbock, minneapolis, wilson = "4845000", "2743000", "3774540"
    events = {lubbock: _event(), minneapolis: _event(), wilson: _event(), "x": _event(prior=4, new=4)}
    fit, test = fs.split_events(events)
    assert set(fit) == {wilson}  # Lubbock excluded; "x" already allowed 4, so no outcome class
    assert set(test) == {minneapolis}


def test_horizon_cuts_to_five_years():
    n = np.ones(10)  # post-reform years 2020-2029 (a Place holds only years from T)
    p = cal.Place("a", "A", 2020, 1.0, np.arange(2020, 2030), 0 * n, n, n, np.arange(0.5, 10.0), n)
    assert list(fs.horizon([p])[0].years) == [2020, 2021, 2022, 2023, 2024]


def test_spread_ids_drops_every_reason(monkeypatch):
    rows = []
    for g, status, state, dose in [
        ("keep", "uncoded", "MN", 0.0),
        ("dosed", "uncoded", "MN", 0.5),
        ("coded", "coded_not_treated", "NC", 0.0),
        ("oregon", "uncoded", "OR", 0.0),
        ("evented", "uncoded", "TX", 0.0),
        ("frank", "uncoded", "OH", 0.0),
        ("2743000", "uncoded", "MN", 0.0),  # Minneapolis, a test place
    ]:
        rows.append({"place": g, "status": status, "state": state, "dose": dose, "year": 2020})
    panel = pd.DataFrame(rows)
    monkeypatch.setattr(fs, "events_d092", lambda panel, rules: ({"evented": _event()}, {}))
    empty = pd.DataFrame(columns=["theme", "status", "unit_cap", "jurisdiction_geoid"])
    rules = {"MN": {"raw": empty}}
    keep, removed = fs.spread_ids(panel, rules, {"frank"})
    assert keep == ["keep"]
    assert removed["dose"] == 1 and removed["event"] == 1 and removed["test_c"] == 1 and removed["tests"] == 1
