"""The ADU calibration runners' own arithmetic and the framework's table comparison (no data needed)."""

from __future__ import annotations

from types import SimpleNamespace

import pandas as pd
import pytest

from lotline import calibrate
from lotline.calibrate import adu_steps as st
from lotline.calibrate.steps import STEPS
from lotline.config import load_params


def test_every_ported_adu_step_names_a_runner_that_exists():
    want = {"adu_joint", "adu_partial_share_grid", "adu_anchor_slopes", "adu_calibration_range",
            "adu_town_prior_sd", "adu_new_rule", "adu_state_effect", "adu_drift",
            "adu_ramp_share"}  # fmt: skip
    by = {s.name: s for s in STEPS}
    for name in want:
        assert by[name].runner and callable(calibrate._resolve(by[name].runner)), name
    for stale in ("adu_state_effect", "adu_drift", "adu_ramp_share"):  # refit in phase 5, not yet written
        assert by[stale].status == "stale"


def test_sig_rounds_to_significant_figures():
    assert st.sig(0.00022411868) == 0.000224 and st.sig(1.50502, 4) == 1.505


def test_town_prior_sd_reproduces_config():
    out = st.town_prior_sd(SimpleNamespace(store=None, quick=False))["adu_place_types"][
        "adu_types_town_prior_sd"
    ]
    assert out["value"] == load_params("adu_place_types")["adu_types_town_prior_sd"].value  # 1.740 / 1.645


def test_nu_interval_hand_worked():
    prof = pd.DataFrame({"nu": [0.5, 0.75, 1.0], "loglik": [-3.0, 0.0, -1.2]})
    assert st.nu_interval(prof) == {"nu": 0.75, "low": 0.75, "high": 1.0}


def test_compare_table_matches_rows_on_the_first_column(tmp_path):
    p = tmp_path / "g.csv"
    p.write_text("m_x,theta,source\n0.1,1.0,a\n0.2,2.0,a\n")
    r = calibrate.compare_table(p, "m_x,theta\n0.2,2.2\n")
    assert r["rel_diff"] == pytest.approx(0.1) and not r["same"]
    assert calibrate.compare_table(p, p.read_text())["same"]
