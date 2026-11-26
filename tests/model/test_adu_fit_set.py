"""The ADU anchor's fit-set builders (`lotline.model.adu_fit_set`) and calibration arithmetic
(`lotline.model.adu_refit`), on small made-up inputs. Each case is the docstring's hand-worked example."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from lotline.model import adu_fit_set as fs
from lotline.model import adu_refit as rf
from lotline.model import calibrate_adu as cal


def _pl(geoid="A", years=(2016, 2017, 2018), state="MN"):
    n = len(years)
    return cal.PlaceData(
        state, geoid, geoid, np.array(years), np.arange(n, dtype=float), np.full(n, 10.0),
        np.full((1, n, 1), 4), np.ones((n, 1)), np.array([1.0]), None, {},
    )  # fmt: skip


# ---- fit set -------------------------------------------------------------------------------------------


def test_big_sources_counts_rows_in_one_adu_flagging_source():
    rows = (
        [{"jurisdiction_geoid": "A", "source": "S", "building_type_std": "ADU", "adu_type": None}]
        + [{"jurisdiction_geoid": "A", "source": "S", "building_type_std": "SFD", "adu_type": None}] * 999
        + [{"jurisdiction_geoid": "B", "source": "S", "building_type_std": "SFD", "adu_type": None}] * 999
        + [{"jurisdiction_geoid": "C", "source": "T", "building_type_std": "SFD", "adu_type": None}] * 1500
    )
    assert fs.big_sources(pd.DataFrame(rows)) == {"A"}  # B has 999; T flags no ADUs, so C counts for nothing


def test_unknown_years_runs_to_the_day_before_the_end_date():
    rows = pd.DataFrame(
        {
            "theme": ["adu", "adu", "adu", "mm"],
            "jurisdiction_geoid": ["A", "B", "C", "D"],
            "coding_notes": [f"x {fs.PLACEHOLDER}", f"{fs.PLACEHOLDER}", "coded", fs.PLACEHOLDER],
            "effective_date": ["2016-01-01", "2024-03-01", "2016-01-01", "2016-01-01"],
            "end_date": ["2023-01-01", None, None, None],
        }
    )
    out = fs.unknown_years(states=("MN",), load=lambda st: rows)
    assert out["A"] == set(range(2016, 2023))  # end 2023-01-01: the day before is in 2022
    assert min(out["B"]) == 2024 and max(out["B"]) == 2099  # no end date: open to 2100
    assert "C" not in out and "D" not in out  # not a placeholder; not an ADU row


def test_limit_years_applies_the_year_limits_then_cuts_unknown_years():
    austin = _pl("4805000", years=tuple(range(2016, 2026)))
    assert list(fs.limit_years(austin).years) == list(range(2016, 2024))
    cut = fs.limit_years(_pl("A", years=(2017, 2018, 2019)), {"A": {2018, 2019}})
    assert list(cut.years) == [2017] and list(cut.y) == [0.0]
    assert fs.limit_years(_pl("A", years=(2018,)), {"A": {2018}}) is None
    assert fs.limit_years(None) is None


def test_d053_places_in_minnesota_leave_out_st_paul_and_rochester():
    r = pd.DataFrame(
        {"theme": ["adu"] * 3 + ["mm"], "jurisdiction_geoid": [fs.ST_PAUL, fs.ROCHESTER, "X", "Y"]}
    )
    assert fs.d053_places("MN", r) == {"X"}
    assert fs.d053_places("OH") == {"3915000"}
    assert fs.d053_places("ZZ") == set()


# ---- owner share and housing age ------------------------------------------------------------------------


def _acs(rows):
    return pd.DataFrame(rows, columns=["geo", "end_year", "table_id", "variable", "label", "estimate"])


def test_b25003_and_share_rows_by_source():
    acs = _acs(
        [
            ("place:A", 2015, "B25003", "B25003_001", "Total", 100),
            ("place:A", 2015, "B25003", "B25003_002", "Owner", 60),
            ("county:C", 2015, "B25003", "B25003_001", "Total", 300),
            ("county:C", 2015, "B25003", "B25003_002", "Owner", 240),
        ]
    )
    t = fs.b25003(acs)
    juris = pd.DataFrame(
        {"geoid": ["A", "R"], "county_geoid": ["C", "C"], "kind": ["place", "county_unincorporated"]}
    )
    assert fs.share_rows("A", "place", "C", t, juris) == ({2015: 0.6}, "place")
    # the county less its places: (240 - 60) / (300 - 100) = 0.9
    by, src = fs.share_rows("R", "county_unincorporated", "C", t, juris)
    assert src == "county less its places" and by[2015] == pytest.approx(0.9)
    assert fs.share_rows("Z", "place", "C", t, juris) == ({}, "none")


def test_b25034_counts_homes_built_before_1960():
    acs = _acs(
        [
            ("place:A", 2015, "B25034", "v1", "Total:", 100),
            ("place:A", 2015, "B25034", "v2", "Built 1950 to 1959", 10),
            ("place:A", 2015, "B25034", "v3", "Built 1939 or earlier", 15),
            ("place:A", 2015, "B25034", "v4", "Built 2000 to 2009", 30),
        ]
    )
    t = fs.b25034(acs)
    assert float(t.loc[("place:A", 2015), "owner"]) == 25 and float(t.loc[("place:A", 2015), "total"]) == 100


# ---- calibration arithmetic -----------------------------------------------------------------------------


def test_grid_weights_hand_worked():
    folds = pd.DataFrame(
        {
            "fold": ["a", "a", "b", "b"],
            "m_x": [0.1, 0.2, 0.1, 0.2],
            "loglik": [0.0, math.log(3), math.log(3), 0.0],
        }
    )
    w, wmax = rf.grid_weights(folds)
    assert list(w) == pytest.approx([0.5, 0.5])
    assert dict(wmax) == {0.1: 0.5, 0.2: 0.5}


def test_grid_table_keeps_the_all_states_rows_and_the_fold_weights():
    prof = pd.DataFrame(
        {
            "fold": ["all", "all", "without A", "without A"],
            "m_x": [0.1, 0.2, 0.1, 0.2],
            "theta": [1e-3, 2e-3, 9e-4, 1.9e-3],
            "alpha": [1.0, 2.0, 1.1, 2.1],
            "core": [1.0, 1.5, 1.1, 1.6],
            "loglik": [-10.0, -9.0, -5.0, -5.0 + math.log(3)],
        }
    )
    g = rf.grid_table(prof, 1.0, 3, 9)
    assert list(g["m_x"]) == [0.1, 0.2] and list(g["theta"]) == [1e-3, 2e-3]
    assert list(g["weight"]) == pytest.approx([0.25, 0.75]) and list(g["weight_fold_max"]) == [0.0, 1.0]
    assert "m_o 1.0, 3 places, 9 place-years" in g["source"].iloc[0]
    assert rf.grid_csv(g).splitlines()[0] == "m_x,theta,alpha,core,loglik,weight,weight_fold_max,source"


def test_folds_and_slope_arithmetic():
    places = [_pl("A", state="MN"), _pl("B", state="OR"), _pl("C", state="MN")]
    folds = rf.folds_of(places)
    assert [f for f, _ in folds] == ["all", "without MN", "without OR"]
    assert [p.geoid for p in folds[1][1]] == ["B"]
    assert rf.slope_bounds(0.5, 0.0, 1.0) == pytest.approx((0.4, 0.6))
    assert rf.slope_bounds(0.95, 0.0, 1.0) == pytest.approx((0.85, 1.0))
    assert rf.log_slope(1.0, math.e, 0.0, 2.0) == pytest.approx(0.5)
