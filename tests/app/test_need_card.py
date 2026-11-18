"""The share-of-housing-need card (WS-NEED-AMI part A; office hours 2026-11-17, B1 and B2).

The page's own script runs under node, against a page built from a synthetic bundle: the fixture's ADU draws,
plus missing-middle and fee runs made by scaling its uptake, so every number is known by hand. Checks: the
card's numbers trace to bundle fields (the need rows; each reform's draws, summed run by run for the three
together); every midpoint comes with its range (S6); the fee view defaults to real local fees and falls back
to the Handbook benchmark; one bar per kind of need, never mixed; a bundle with no need rows renders
the pending note.
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


def _bundle(*, fees_local_half: bool = True, need: bool = True) -> dict:
    doc = json.loads(FIXTURE.read_text())
    adu = [d for d in doc["draws"] if d["scenario"] == "adu"]
    for s, k in SCALE.items():
        if s == "fees_local_half" and not fees_local_half:
            continue
        doc["draws"] += [{**copy.deepcopy(d), "scenario": s, "theta": d["theta"] * k} for d in adu]
        doc["need"] += [{**n, "scenario": s} for n in doc["need"] if n["scenario"] == "adu"]
    if not need:
        doc["need"] = []
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
    for n in (r for r in doc["need"] if r["scenario"] == "adu"):
        assert f'data-need-kind="{n["denominator_kind"]}"' in html  # one bar per kind
        assert f"Need: {_fmt(n['denominator'])}" in html
    assert "needs about 2,000 homes by 2031" in html  # household growth over the window ends in 2031
    assert "is short about 5,000 homes today" in html  # the shortage is a stock, not a five-year flow
    assert f"together add {_fmt(lo)} to {_fmt(hi)} of them" in html
    # each reform's row: its own draws' P10 to P90, never a bare midpoint
    for s in shown:
        p10, p90 = np.percentile(net[s], [10, 90])
        assert f"{_fmt(p10)} to {_fmt(p90)}" in html, s
    # the ranking: missing middle (3× the ADU uptake) first, then ADUs, then the halved real fees
    rank = html[html.index('id="need-rank"') :].split("</p>")[0]
    order = [rank.index(w) for w in ("Missing middle adds the most", "then ADUs", "real local fees")]
    assert order == sorted(order)
    for s in shown:  # every midpoint in the sentence carries its range
        p10, p50, p90 = np.percentile(net[s], [10, 50, 90])
        assert f"about {_fmt(p50)}" in rank and f"({_fmt(p10)} to {_fmt(p90)})" in rank, s


def test_the_two_kinds_of_need_are_separate_bars(tmp_path):
    html = _render(tmp_path, _bundle())["html"]
    assert html.count('<svg class="needbar"') == 2
    # the headline kind comes first
    assert html.index('data-need-kind="household_growth_5y"') < html.index('data-need-kind="shortage_stock"')


def test_a_bundle_without_need_rows_says_so(tmp_path):
    html = _render(tmp_path, _bundle(need=False))["html"]
    assert "No housing-need estimate is coded for this state." in html
    assert "needbar" not in html
