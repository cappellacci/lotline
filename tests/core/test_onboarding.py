"""The onboarding steps file (WS-SCALE task 13): it loads, the guide matches it, and its checks and commands
do what the app will rely on. Synthetic data only."""

from __future__ import annotations

import json
import re

import pandas as pd
import pytest

from lotline import onboarding
from lotline.config import all_states
from lotline.io import DataStore


def test_steps_load_and_are_ordered_like_the_guide():
    steps = onboarding.steps()
    assert len(steps) == 14 and steps[0].id == "assess" and steps[-1].id == "pool"
    headings = re.findall(r"^### Step (\d+)\. (.+)$", onboarding.GUIDE.read_text(), re.M)
    assert [int(n) for n, _ in headings] == list(range(1, len(steps) + 1))
    for (n, heading), s in zip(headings, steps, strict=True):
        assert heading.startswith(s.title), f"guide step {n} is {heading!r}, steps.yaml says {s.title!r}"


def test_guide_blocks_are_generated_from_the_steps_file():
    text = onboarding.GUIDE.read_text()
    assert onboarding.sync_guide(text) == text, "run `uv run python -m lotline.onboarding`"


def test_short_path_is_level_zero_only():
    short = [s for s in onboarding.steps() if s.short_path]
    assert short and all(s.level in (0, None) for s in short)
    assert all("agent" not in s.modes for s in short)  # the short path needs no agent and no code


def test_commands_fill_in_the_state():
    cmds = onboarding.commands("first_run", "wi")
    assert cmds[0] == ["uv", "run", "lotline", "results", "--state", "WI"]
    assert "reports/wi/fees-statewide.csv" in cmds[1]
    assert onboarding.commands("rules", "WI") == []  # manual or agent only


def test_agent_steps_are_review_and_import():
    agent = [s for s in onboarding.steps() if "agent" in s.modes]
    assert {s.id for s in agent} == {"rules", "fees"}  # the rule agents propose reforms and fees tables only
    for s in agent:
        assert "manual" in s.modes and s.check  # same check as the manual path
        act = onboarding.import_action(s, "WI")
        assert act["import_to"] == f"config/{act['proposes']}/wi.csv"
    assert onboarding.import_action("national_data", "WI") is None


def test_imported_reforms_must_pass_the_schema(monkeypatch, tmp_path):
    (tmp_path / "reforms").mkdir()
    (tmp_path / "reforms" / "mn.csv").write_text("reform_id,state\nbad,MN\n")
    monkeypatch.setattr(onboarding, "CONFIG_DIR", tmp_path)
    from lotline.model.scenarios import adu

    real = adu.load_reforms
    monkeypatch.setattr(adu, "load_reforms", lambda st, config_dir=None: real(st, tmp_path))
    st = onboarding.check("rules", "MN")
    assert st.done is False and "reforms schema" in st.detail


@pytest.mark.parametrize("state", all_states())
def test_configured_states_have_no_config_problems(state):
    assert onboarding.config_problems(state) == []


def test_unknown_state_is_not_configured():
    st = onboarding.check("state_config", "QQ")
    assert st.done is False and "no config/states/qq.yaml" in st.detail


def test_national_tables_check_reads_only_which_tables_exist(tmp_path):
    store = DataStore(tmp_path)
    first = onboarding.check("national_data", "MN", store)
    assert first.done is False and "place_inputs" in first.detail
    for table in onboarding.NATIONAL_TABLES:
        folder = store.processed("MN", table)
        folder.mkdir(parents=True)
        pd.DataFrame({"x": [1]}).to_parquet(folder / "t.parquet")
    assert onboarding.check("national_data", "MN", store).done is True


def test_manual_steps_have_no_automatic_check():
    st = onboarding.check("read_results", "MN")
    assert st.done is None


def test_plan_is_json_for_the_app(tmp_path):
    plan = onboarding.plan("MN", DataStore(tmp_path))
    assert [p["n"] for p in plan] == list(range(1, 15))
    assert json.loads(json.dumps(plan))[1]["done"] is True  # MN's state file loads
    keys = {"id", "title", "modes", "commands", "agent", "import", "done", "detail", "done_when"}
    assert keys <= set(plan[0])


def test_bad_steps_are_rejected(tmp_path):
    good = onboarding.STEPS_FILE.read_text()
    bad = tmp_path / "steps.yaml"
    bad.write_text(good.replace("check: fees_coded", "check: fees_typed"))
    with pytest.raises(ValueError, match="unknown check"):
        onboarding.steps(bad)
    bad.write_text(
        good.replace(
            "modes: [manual, built_in]\n    commands:\n      - [uv, run, lotline, onboard",
            "modes: [manual]\n    commands:\n      - [uv, run, lotline, onboard",
        )
    )
    with pytest.raises(ValueError, match="built_in"):
        onboarding.steps(bad)
