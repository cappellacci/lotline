"""The scenario contract (`lotline.model.scenarios`, #554): the registry, the one draws function, and a toy
scenario that reaches the bundle with nothing else edited. Synthetic inputs only (the `zz` store)."""

from __future__ import annotations

import importlib.util
import json
import types
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from lotline.model import aggregate, results, scenarios
from lotline.schemas import SCENARIOS

TOY = Path(__file__).resolve().parents[1] / "fixtures" / "scenarios" / "toy.py"


def _toy():
    spec = importlib.util.spec_from_file_location("lotline_test_toy_scenario", TOY)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_registry_is_the_built_in_scenarios_in_bundle_order():
    assert [s.name for s in scenarios.all()] == ["adu", "missing_middle", "fees"]
    assert list(scenarios.bundle_names()) == SCENARIOS  # schemas' list is the registry's, checked here
    assert results.ENGINE_SCENARIOS == tuple(SCENARIOS)
    assert results.FEE_SCENARIOS == {"fees": "handbook", "fees_local_half": "local_half"}  # D-065
    assert scenarios.get("fees_local_half").name == "fees"
    assert scenarios.get("fees").labels("fees_local_half")["title"] == "Fee reduction, real local fees"


def test_half_defined_scenarios_are_errors():
    bad = types.ModuleType("bad")
    bad.NAME = "bad"
    with pytest.raises(scenarios.ScenarioError, match="missing LABELS, VARIANTS, run"):
        scenarios.check_module(bad)
    bad.LABELS, bad.VARIANTS, bad.run = {"title": "Bad"}, {"bad": "x"}, lambda i, v: None
    with pytest.raises(scenarios.ScenarioError, match="title and a definition"):
        scenarios.check_module(bad)
    bad.LABELS["definition"] = "A bad one."
    bad.VARIANTS = {"fees": "x"}  # a bundle name another scenario already has
    with scenarios.registered(bad), pytest.raises(scenarios.ScenarioError, match="duplicate"):
        scenarios.all()
    assert "bad" not in [s.name for s in scenarios.all()]  # unregistered after the block


def test_one_draws_function_by_hand():
    """Two completion classes: 120 houses and 30 plex homes added, completion 0.95 and 0.85 -> 0.93; with
    one class the factor is used as drawn. Draw order: each class, then displacement."""
    run = scenarios.ScenarioRun(
        eligible=(0.0, 10_000.0, 0.0),
        theta=np.array([0.015]),
        pencil_out_share=1.0,
        net_new_share=1.0,
        completion={"single_family": np.array([120.0]), "multifamily": np.array([30.0])},
        year_shares=np.full((1, 5), 0.2),
        scenario="fees",
    )
    seen = []

    def fixed(name, n, rng, file="aggregate"):
        seen.append(name)
        return np.full(
            n, {"completion_factor_single_family": 0.95}.get(name, 0.85 if "multi" in name else 0.25)
        )

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(results, "triangular", fixed)
        r = results.scenario_draws(run, None).iloc[0]
    assert seen == ["completion_factor_single_family", "completion_factor_multifamily", "displacement_share"]
    assert r.completion_factor == pytest.approx(0.93)
    assert run.completion_draws["multifamily"][0] == 0.85
    h = aggregate.homes_from_draws(results.scenario_draws(run, np.random.default_rng(0)))
    assert h["permits_added"][0] == pytest.approx(150)


def test_a_toy_scenario_reaches_the_bundle_with_nothing_else_edited(zz, tmp_path):
    """The evidence for "add a scenario without touching the mechanics": the toy module, registered, appears
    in the draws, totals and `meta.scenarios`; the built-in scenarios' draws are unchanged by it."""
    plain = results.build_bundle("ZZ", zz, draws=20)
    with scenarios.registered(_toy()):
        b = results.build_bundle("ZZ", zz, draws=20)
        path = results.write_bundle(b, tmp_path / "bundle.json")
        back = results.read_bundle(path)
    d = b["draws"]
    assert list(dict.fromkeys(d["scenario"])) == [*SCENARIOS, "toy"]
    toy = d[d["scenario"] == "toy"]
    lots = toy[["eligible_tier1", "eligible_tier2", "eligible_tier3"]].sum(axis=1)
    assert lots.iloc[0] > 0
    five = b["totals"].query("scenario == 'toy' and outcome == 'permits_added' and period.str.contains('-')")
    assert five["p50"].iloc[0] == pytest.approx(0.01 * lots.iloc[0])
    pd.testing.assert_frame_equal(d[d["scenario"] != "toy"].reset_index(drop=True), plain["draws"])
    listed = json.loads(path.read_text())["meta"]["scenarios"]
    assert [s["scenario"] for s in listed] == [*SCENARIOS, "toy"]
    assert listed[-1]["title"] == "Toy reform" and listed[-1]["tables"] is None
    assert list(back["scenarios"]["scenario"]) == [*SCENARIOS, "toy"]
    assert b["scenarios"].query("scenario == 'fees_local_half'")["tables"].iloc[0] == "fee_types"
    assert b["meta"]["scenarios_pending"].iloc[0] is None
