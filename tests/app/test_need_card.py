"""The share-of-housing-need card (WS-NEED-AMI part A; office hours 2026-11-17, B1 and B2).

The page's own script runs under node, against a page built from a synthetic bundle: the fixture's ADU draws,
plus missing-middle and fee runs made by scaling its uptake, so every number is known by hand. Checks: the
card's numbers trace to bundle fields (the need rows; each reform's draws, summed run by run for the three
together); every midpoint comes with its range (S6); the fee view defaults to real local fees and falls back
to the Handbook benchmark; one bar against the headline kind of need, the other kind as one line; a bundle
with no need rows renders the pending note.
"""

from __future__ import annotations

import copy
import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest

from lotline.app import build

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "results" / "zz" / "bundle.json"
NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None, reason="node is needed to run the page's script")

HARNESS = Path(__file__).with_name("need_card_harness.js")  # the page's script under node, stub DOM

SCALE = {"missing_middle": 3.0, "fees": 2.0, "fees_local_half": 0.5}  # uptake multiples of the ADU draws


def _bundle(*, fees_local_half: bool = True, need: bool = True, shortfall: bool = False) -> dict:
    doc = json.loads(FIXTURE.read_text())
    adu = [d for d in doc["draws"] if d["scenario"] == "adu"]
    for s, k in SCALE.items():
        if s == "fees_local_half" and not fees_local_half:
            continue
        doc["draws"] += [{**copy.deepcopy(d), "scenario": s, "theta": d["theta"] * k} for d in adu]
        doc["need"] += [{**n, "scenario": s} for n in doc["need"] if n["scenario"] == "adu"]
    if not need:
        doc["need"] = []
    if not shortfall:  # the share-of-need view (the fallback when a bundle has no shortfall row)
        doc["shortfall"] = []
    return doc


def _render(tmp_path: Path, doc: dict) -> dict:
    tmp_path.mkdir(parents=True, exist_ok=True)
    src = tmp_path / "zz.json"
    src.write_text(json.dumps(doc))
    build.build_app([src], out_dir=tmp_path / "app", data_summary=None)
    cmd = [NODE, str(HARNESS), str(tmp_path / "app"), "ZZ"]
    out = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def _net(draws: list[dict]) -> np.ndarray:
    """aggregate.homesFromDraws by hand:
    eligible × pencil × θ × (1 − overlap) × completion × net-new × (1 − displaced)."""
    d = sorted(draws, key=lambda r: r["draw"])
    return np.array(
        [
            (r["eligible_tier1"] + r["eligible_tier2"] + r["eligible_tier3"])
            * r["pencil_out_share"]
            * r["theta"]
            * (1 - (r["overlap_share"] or 0))
            * r["completion_factor"]
            * r["net_new_share"]
            * (1 - r["displacement_share"])
            for r in d
        ]
    )


def _fmt(x: float) -> str:
    """The page's fmtN."""
    a = abs(x)
    r = round(x / 100) * 100 if a >= 10000 else round(x / 10) * 10 if a >= 1000 else round(x)
    return f"{int(r):,}"


def test_fee_view_defaults_to_real_local_fees_and_falls_back(tmp_path):
    assert _render(tmp_path / "a", _bundle())["fee"] == "fees_local_half"
    assert _render(tmp_path / "b", _bundle(fees_local_half=False))["fee"] == "fees"


def test_card_numbers_trace_to_the_bundle(tmp_path):
    doc = _bundle()
    html = _render(tmp_path, doc)["html"]
    shown = ("adu", "missing_middle", "fees_local_half")  # the default fee view
    net = {s: _net([d for d in doc["draws"] if d["scenario"] == s]) for s in shown}
    together = sum(net.values())
    lo, hi = np.percentile(together, [10, 90])
    assert 'data-need-kind="household_growth_5y"' in html  # one bar, against the headline kind
    assert "Need: 2,000" in html and "Need: 5,000" not in html
    assert "needs about 2,000 homes by 2031" in html  # household growth over the window ends in 2031
    assert "mid-2026 to mid-2031" in html  # where the number comes from, in one plain sentence
    assert "is also short about 5,000 homes today" in html  # the shortage: one line, not a second bar
    assert f"({_fmt(lo)} to {_fmt(hi)} net new homes)" in html
    # each reform's row: its own draws' P10 to P90, never a bare midpoint
    for s in shown:
        p10, p90 = np.percentile(net[s], [10, 90])
        assert f"{_fmt(p10)} to {_fmt(p90)}" in html, s
    # one sentence: what the three cover and which adds the most (missing middle, 3x ADU uptake), with range
    rank = html[html.index('id="need-rank"') :].split("</p>")[0]
    assert "The three reforms together would cover" in rank and "missing middle would add the most" in rank
    p10, p90 = np.percentile(net["missing_middle"], [10, 90])
    assert f"({_fmt(p10)} to {_fmt(p90)})" in rank


def test_one_bar_with_the_other_kind_as_a_line(tmp_path):
    """Ben, 2026-11-19: one bar against the headline kind; the other kind is a sentence, not a second bar."""
    html = _render(tmp_path, _bundle())["html"]
    assert html.count('<svg class="needbar"') == 1
    assert 'data-need-also="shortage_stock"' in html
    assert html.index('class="needbar"') < html.index("data-need-also")


def test_a_bundle_without_need_rows_says_so(tmp_path):
    html = _render(tmp_path, _bundle(need=False))["html"]
    assert "No housing-need estimate is coded for this state." in html
    assert "needbar" not in html


def test_shortfall_view_stacks_the_reforms_on_what_gets_built_anyway(tmp_path):
    """Ben, 2026-11-19: need left after homes built anyway; numbers trace to results_shortfall and draws."""
    doc = _bundle(shortfall=True)
    sf = doc["shortfall"][0]
    html = _render(tmp_path, doc)["html"]
    assert 'data-need-kind="shortfall"' in html and html.count('<svg class="needbar"') == 1
    assert f"needs about {_fmt(sf['need'])} more homes by 2031" in html
    assert f"{_fmt(sf['shortage'])} the state is already short" in html
    assert f"{_fmt(sf['lost'])} to replace homes lost" in html
    shown = ("adu", "missing_middle", "fees_local_half")
    together = sum(_net([d for d in doc["draws"] if d["scenario"] == s]) for s in shown)
    lo, hi = np.percentile(together, [10, 90])
    assert f"{_fmt(lo)} to {_fmt(hi)} net new homes" in html
    if sf["gap"] > 0:
        assert f"leaving a gap of about {_fmt(sf['gap'])} homes" in html
    else:
        assert "would cover the need" in html
    assert f"could run from {_fmt(sf['gap_low'])} to {_fmt(sf['gap_high'])}" in html  # the gap's full range


def test_shortfall_view_says_when_building_anyway_covers_the_need(tmp_path):
    doc = _bundle(shortfall=True)
    sf = doc["shortfall"][0]
    sf.update(built=sf["need"] + 1000, gap=-1000.0)
    html = _render(tmp_path, doc)["html"]
    assert "homes the market builds anyway" in html and "would cover the need" in html
