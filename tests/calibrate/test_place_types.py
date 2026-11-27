"""Place types (D-088's rule, missing middle D-092 deviation 2026-11-15 (c)): hand-worked examples."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from lotline.calibrate import place_types as pt


def _juris():
    return pd.DataFrame(
        {
            "geoid": ["A", "B", "C", "D", "E"],
            "cbsa_code": ["M", "M", "M", "m", None],
            "cbsa_type": ["metro", "metro", "metro", "micro", None],
            "units": [300, 120, 90, 50, 10],
        }
    )


def test_assign_types_by_hand():
    t = pt.assign_types(_juris())
    assert t.to_dict() == {"A": "core", "B": "core", "C": "suburb", "D": "town", "E": "town"}


def test_core_share_edge_is_inclusive():
    j = _juris().assign(units=[300, 100, 99.9, 50, 10])
    t = pt.assign_types(j)
    assert t["B"] == "core" and t["C"] == "suburb"


def test_missing_units_rank_as_zero():
    j = _juris().assign(units=[None, 120, 90, 50, 10])
    t = pt.assign_types(j)
    # B is now the largest (120); C (90) >= 40 is a core too; A (0) is a suburb
    assert (t["A"], t["B"], t["C"]) == ("suburb", "core", "core")


def test_two_metros_are_ranked_separately():
    j = pd.DataFrame({"geoid": ["A", "B"], "cbsa_code": ["M1", "M2"], "cbsa_type": ["metro", "metro"],
                      "units": [1000, 10]})  # fmt: skip
    assert pt.assign_types(j).to_dict() == {"A": "core", "B": "core"}


def test_merge_small_by_hand():
    ft = pd.DataFrame(
        {"type": ["core"] * 10 + ["suburb"] * 30 + ["town"] * 5,
         "state": ["MN", "NC", "OH"] * 3 + ["TX"]
         + ["MN", "NC", "OH", "TX", "OR"] * 6
         + ["MN", "NC"] * 2 + ["MN"]}
    )  # fmt: skip
    mapping, notes = pt.merge_small(ft)
    assert mapping == {"core": "core", "suburb": "suburb", "town": "suburb"}
    assert len(notes) == 1 and notes[0].startswith("town")


def test_merge_small_states_rule_merges_core_too():
    ft = pd.DataFrame({"type": ["core"] * 9 + ["suburb"] * 20 + ["town"] * 9,
                       "state": ["MN", "NC"] * 4 + ["MN"]
                       + ["MN", "NC", "OH", "TX"] * 5
                       + ["MN", "NC", "OH"] * 3})  # fmt: skip
    mapping, notes = pt.merge_small(ft)
    # core: 9 places but only 2 states -> merged; town: 9 in 3 states -> kept
    assert mapping == {"core": "suburb", "suburb": "suburb", "town": "town"}
    assert [n.split()[0] for n in notes] == ["core"]


def test_indicators():
    assert pt.indicators("core").tolist() == [1.0, 0.0]
    assert pt.indicators("suburb").tolist() == [0.0, 0.0]
    assert pt.indicators("town").tolist() == [0.0, 1.0]


@pytest.mark.parametrize(
    "vals,expect",
    [
        ({2013: 90, 2015: 100, 2017: 120}, (100.0, 2015, "acs 2011-15")),
        ({2014: 80}, (80.0, 2014, "acs early")),
        ({2018: 70}, (70.0, 2018, "acs latest let through")),
    ],
)
def test_pick_units(vals, expect):
    assert pt.pick_units(pd.Series(vals)) == expect


def test_pick_units_none():
    u, v, s = pt.pick_units(None)
    assert math.isnan(u) and v is None and s == "none"


def test_raw_types_non_places_never_core():
    u = pd.DataFrame(
        {"geoid": ["A", "T", "U"], "kind": ["place", "township", "county_unincorporated"],
         "cbsa_code": ["M", "M", None], "cbsa_type": ["metro", "metro", None], "units": [300, 900, 50]}
    )  # fmt: skip
    t = pt.raw_types(u)
    assert t.to_dict() == {"A": "core", "T": "suburb", "U": "town"}
    assert np.all(t.notna())
