"""`lotline calibrate --check` (phase 1): every fitted value traces to one step, and config matches the lock.

The repository itself must pass; small synthetic config folders show each failure the check is there to catch.
"""

from __future__ import annotations

import pytest
import yaml

from lotline import calibrate
from lotline.calibrate.steps import Step


def test_the_repository_registry_config_and_lock_agree():
    assert calibrate.check() == []


def test_every_step_names_its_decision_script_and_how():
    for s in calibrate.STEPS:
        assert s.decision and s.script and s.how in {"code", "hand"}
        assert s.status in {"current", "stale", "frozen"}
        assert s.produces or s.tables


def _config(tmp_path, params: dict) -> object:
    (tmp_path / "params").mkdir()
    (tmp_path / "params" / "p.yaml").write_text(yaml.safe_dump(params))
    return tmp_path


EST = {"value": 1.0, "low": 0.0, "high": 2.0, "unit": "x", "source": "Estimated, D-1"}
JUDGE = {"value": 1.0, "low": 0.0, "high": 2.0, "unit": "x", "source": "Judgment"}


def test_a_value_changed_without_rewriting_the_lock_fails(tmp_path):
    cfg = _config(tmp_path, {"a": EST, "b": JUDGE})
    steps = (Step("fit_a", "D-1", {"p": ("a",)}, "script.py", "hand"),)
    calibrate.write_lock(cfg, steps)
    assert calibrate.check(cfg, steps) == []
    (cfg / "params" / "p.yaml").write_text(yaml.safe_dump({"a": {**EST, "value": 1.5}, "b": JUDGE}))
    (problem,) = calibrate.check(cfg, steps)
    assert "p:a changed in config (1.0 -> 1.5)" in problem and "fit_a" in problem


def test_an_estimated_value_no_step_produces_fails(tmp_path):
    cfg = _config(tmp_path, {"a": EST, "c": {**EST, "source": "Estimated, D-2"}})
    steps = (Step("fit_a", "D-1", {"p": ("a",)}, "script.py", "hand"),)
    calibrate.write_lock(cfg, steps)
    assert calibrate.check(cfg, steps) == ["p:c is estimated but no calibration step produces it"]


def test_a_step_naming_a_missing_key_fails(tmp_path):
    cfg = _config(tmp_path, {"a": EST})
    steps = (Step("fit_a", "D-1", {"p": ("a", "zz")}, "script.py", "hand"),)
    assert any("p.yaml has no zz" in p for p in calibrate.check(cfg, steps))


def test_star_produces_every_entry_of_a_generated_file(tmp_path):
    cfg = _config(tmp_path, {"a": EST, "b": JUDGE})
    steps = (Step("gen", "D-1", {"p": ("*",)}, "script.py", "code"),)
    assert set(calibrate.produced(steps, cfg)) == {"p:a", "p:b"}


def test_order_unknown_steps_cycles_and_double_producers_are_refused(tmp_path):
    a = Step("a", "D", {"p": ("x",)}, "s", "hand", after=("b",))
    b = Step("b", "D", {"p": ("y",)}, "s", "hand")
    assert [s.name for s in calibrate.order((a, b))] == ["b", "a"]
    with pytest.raises(ValueError, match="unknown step"):
        calibrate.order((a,))
    with pytest.raises(ValueError, match="cycle"):
        calibrate.order((a, Step("b", "D", {"p": ("y",)}, "s", "hand", after=("a",))))
    cfg = _config(tmp_path, {"x": EST})
    with pytest.raises(ValueError, match="produced by both"):
        calibrate.produced(
            (Step("a", "D", {"p": ("x",)}, "s", "hand"), Step("b", "D", {"p": ("x",)}, "s", "hand")), cfg
        )


def double_a(ctx):
    return {"p": {"a": {"value": 2.0, "low": 1.5, "high": 2.5} if not ctx.quick else 1.9}}


def test_run_compares_and_writes_only_the_value_line(tmp_path):
    cfg = _config(tmp_path, {"a": EST, "b": JUDGE})
    text = (cfg / "params" / "p.yaml").read_text()
    (cfg / "params" / "p.yaml").write_text("# a comment that must survive\n" + text)
    steps = (
        Step("fit_a", "D-1", {"p": ("a",)}, "s", "hand", runner="tests.calibrate.test_registry:double_a"),
        Step("fit_b", "D-1", {"p": ("b",)}, "s", "hand"),
    )
    calibrate.write_lock(cfg, steps)
    rows = calibrate.run(quick=False, store=object(), config_dir=cfg, steps=steps)
    assert {"step": "fit_b", "name": None, "status": "not ported yet"} in rows
    (row,) = [r for r in rows if r["name"]]
    assert (row["config"], row["new"], row["rel_diff"]) == (1.0, 2.0, 1.0)
    with pytest.raises(ValueError, match="quick run"):
        calibrate.run(quick=True, write=True, store=object(), config_dir=cfg, steps=steps)
    calibrate.run(write=True, store=object(), config_dir=cfg, steps=steps)
    after = (cfg / "params" / "p.yaml").read_text()
    assert after.startswith("# a comment that must survive")
    assert {k: yaml.safe_load(after)["a"][k] for k in ("value", "low", "high")} == {
        "value": 2.0,
        "low": 1.5,
        "high": 2.5,
    }
    assert yaml.safe_load(after)["a"]["source"] == "Estimated, D-1"
    assert calibrate.check(cfg, steps) == []  # config and lock were written together
