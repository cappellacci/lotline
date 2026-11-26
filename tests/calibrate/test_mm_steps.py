"""Missing-middle calibration runners (phase 3): registered, resolvable, and the cheap one end to end."""

import pandas as pd
import pytest

from lotline.calibrate import RunContext, _resolve, run
from lotline.calibrate import mm_steps as ms
from lotline.calibrate.steps import STEPS

MM = ("mm_year_spread", "mm_c4", "mm_fast_ramp", "mm_units_per_project")


def test_every_mm_step_has_a_runner():
    by = {s.name: s for s in STEPS}
    for name in MM:
        assert by[name].runner and callable(_resolve(by[name].runner)), name


class _Store:
    """Two states of jurisdictions and BPS rows, enough for `mm_units_per_project`."""

    def __init__(self, tables):
        self.tables = tables

    def read(self, state, table):
        return self.tables[(state.upper(), table)]


def _units_store(monkeypatch):
    monkeypatch.setattr(ms.fs, "D038_PLACES", {"NC": ("Wilson",), "MN": ("Richfield",)})
    t = {}
    for st, g, name, homes, bldgs in (("NC", "01", "Wilson", 10, 5), ("MN", "02", "Richfield", 8, 2)):
        t[(st, "jurisdictions")] = pd.DataFrame({"geoid": [g], "name": [f"{name} city"], "kind": ["place"]})
        t[(st, "bps_place_year")] = pd.DataFrame(
            {"geoid": [g], "year": [2020], "units_2": [homes], "units_3_4": [0], "bldgs_2": [bldgs],
             "bldgs_3_4": [0]}
        )  # fmt: skip
    return _Store(t)


def test_units_runner_by_hand(monkeypatch):
    out = ms.mm_units_per_project(RunContext(_units_store(monkeypatch), False, None, None))
    u = out["mm_hazard"]["mm_units_per_project"]
    assert u["value"] == 2.57  # pooled 18 homes / 7 buildings = 2.5714, rounded as config writes it
    assert u["low"] == u["high"] == pytest.approx(2.0)  # NC only: MN is left out of the range


def test_run_compares_with_config(monkeypatch):
    rows = run(["mm_units_per_project"], store=_units_store(monkeypatch))
    (row,) = rows
    assert row["name"] == "mm_hazard:mm_units_per_project" and row["config"] == 2.08
    assert row["new"] == 2.57


def test_sig_rounds_half_up_to_config_precision():
    """C4's full-run numbers round to config's: 0.00103869627 -> 0.0010387 (5 figures), 6.1445e-6 -> 6.1e-6
    (2), 1.92437 -> 1.92 (3); half up, so 0.000012345 -> 0.00001235 at 4 (Python's round gives 1.234e-05)."""
    assert ms._sig(0.0010386962707638191, 5) == 0.0010387
    assert ms._sig(0.01938852911, 4) == 0.01939
    assert ms._sig(6.144505358680093e-06, 2) == 0.0000061
    assert ms._sig(1.9243714315647968, 3) == 1.92
    assert ms._sig(0.000012345, 4) == 0.00001235
    assert ms._sig(0.0, 3) == 0.0
