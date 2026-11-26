"""A new scenario reaches the app with nothing else edited (modularity plan step 1.4, #554).

The toy scenario (`tests/fixtures/scenarios/toy.py`, one home per 100 eligible lots) is registered for one
build of the synthetic `zz` state. The page built from that bundle draws its result box, lane, evidence card
and every-state bar from `meta.scenarios`; no line of the app names it. The page's own script runs under node
against a stub DOM (`scenario_harness.js`). Synthetic data only.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from lotline.app import build
from lotline.model import results, scenarios

NODE = shutil.which("node")
TOY = Path(__file__).resolve().parents[1] / "fixtures" / "scenarios" / "toy.py"
HARNESS = Path(__file__).with_name("scenario_harness.js")
APP = [Path(build.__file__), build.TEMPLATE]


def _toy():
    spec = importlib.util.spec_from_file_location("lotline_test_toy_scenario_app", TOY)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_app_names_no_toy():
    for f in APP:
        assert "toy" not in f.read_text(encoding="utf-8").lower()


def test_the_toy_reaches_the_page(zz, tmp_path):
    """In the page data, then (under node) a result box, a lane, an evidence card and an every-state bar."""
    with scenarios.registered(_toy()):
        bundle = results.build_bundle("ZZ", zz, draws=20)
        path = results.write_bundle(bundle, tmp_path / "zz" / "bundle.json")
        build.build_app([path], out_dir=tmp_path / "app", data_summary=None)
    s = build.payload([json.loads(path.read_text())], "t")["scenarios"]
    assert list(s) == ["adu", "missing_middle", "fees", "fees_local_half", "toy"]
    assert s["toy"]["label"] == "Toy reform" and s["toy"]["model"] == "toy" and s["toy"]["color"] == "--ink"
    local = s["fees_local_half"]
    assert local["short"] == "Fee reduction" and local["tables"] == ["fee_types"]
    if NODE is None:
        pytest.skip("node is needed to run the page's script")
    cmd = [NODE, str(HARNESS), str(tmp_path / "app"), "ZZ", "toy"]
    page = json.loads(subprocess.run(cmd, capture_output=True, text=True, check=True).stdout)
    assert page["hero"] == ["adu", "missing_middle", "fees", "toy"]
    html = page["results"]
    assert 'data-box="toy"' in html and 'data-lane="toy"' in html and 'data-model="toy"' in html
    assert "Toy reform" in html and "one home for every 100 eligible lots" in html
    ev = page["evidence"]
    assert "Toy reform" in ev and "Where the reform applies" in ev and "Homes built" in ev
    assert "still being designed" not in ev
    assert "Toy reform" in page["allstates"]
