"""Parity: the page's JavaScript aggregation (src/lotline/app/aggregate.js) equals `model/aggregate.py`.

The contract in the WS-APP brief: the browser's only model arithmetic is the re-multiplication of the
engine's draws, and it must give the same P10/P50/P90 as `aggregate.homes_from_draws` on the same fixture.
The JS runs under node. A slider shifts one factor to a point q in its own range (every draw times
P_q / P50 of that factor, kept within [0, 1]); the Python side of that is three lines here (np.percentile,
numpy's default linear method, then homes_from_draws), so both the shift and the product are checked.
"""

import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from lotline.model import aggregate

REPO = Path(__file__).resolve().parents[2]
JS = REPO / "src" / "lotline" / "app" / "aggregate.js"
FIXTURE = REPO / "tests" / "fixtures" / "results" / "zz" / "bundle.json"
NODE = shutil.which("node")
OUTCOMES = ("legal", "pencils", "permits_added", "homes_in_place", "homes_net_statewide")
FACTORS = ("theta", "pencil_out_share", "completion_factor", "net_new_share", "displacement_share")

pytestmark = pytest.mark.skipif(NODE is None, reason="node is needed to run the page's aggregation")


def _node(script: str, payload: dict):
    out = subprocess.run(
        [NODE, "-e", script, str(JS)], input=json.dumps(payload), capture_output=True, text=True, check=True
    )
    return json.loads(out.stdout)


RUN = """
const agg = require(process.argv[1]);
let s = ""; process.stdin.on("data", (c) => (s += c)).on("end", () => {
  const {draws, cases} = JSON.parse(s);
  process.stdout.write(JSON.stringify(cases.map((pins) => agg.summarize(draws, pins))));
});
"""


def _python(draws: pd.DataFrame, pins: dict) -> dict:
    d = draws.sort_values("draw").copy()
    for col, q in pins.items():
        x = d[col].to_numpy(dtype=float)
        mid = np.percentile(x, 50)
        d[col] = np.clip(x * (np.percentile(x, q) / mid if mid > 0 else 1.0), 0.0, 1.0)
    h = aggregate.homes_from_draws(d)
    pct = {k: np.percentile(h[k], [10, 50, 90]) for k in OUTCOMES}
    return {k: dict(zip(("p10", "p50", "p90"), v, strict=True)) for k, v in pct.items()}


def _records(df: pd.DataFrame) -> list[dict]:
    # full precision (pandas' to_json rounds to 10 digits by default); NaN -> null as in the bundle
    return [{k: (None if isinstance(v, float) and np.isnan(v) else v) for k, v in r.items()}
            for r in df.to_dict(orient="records")]  # fmt: skip


def _draws() -> pd.DataFrame:
    return pd.DataFrame(json.loads(FIXTURE.read_text())["draws"])


CASES = (
    [{}]
    + [{f: q} for f in FACTORS for q in (0, 10, 50, 90, 100)]
    + [{"theta": 90, "pencil_out_share": 10}, {f: 50 for f in FACTORS}]
)


@pytest.mark.parametrize("scenario", sorted(set(_draws()["scenario"])))
def test_js_matches_python_for_every_shift(scenario):
    draws = _draws()
    draws = draws[draws["scenario"] == scenario]
    js = _node(RUN, {"draws": _records(draws), "cases": CASES})
    for pins, got in zip(CASES, js, strict=True):
        want = _python(draws, pins)
        for k in OUTCOMES:
            for p in ("p10", "p50", "p90"):
                assert got[k][p] == pytest.approx(want[k][p], rel=1e-12, abs=1e-9), (pins, k, p)


def test_unpinned_js_equals_the_bundles_own_totals():
    # the bundle's `totals` were written by the engine from these draws: the page's default view must match
    doc = json.loads(FIXTURE.read_text())
    draws = pd.DataFrame(doc["draws"])
    for scenario, g in draws.groupby("scenario"):
        (got,) = _node(RUN, {"draws": _records(g), "cases": [{}]})
        for t in doc["totals"]:
            if t["scenario"] == scenario and "-" in t["period"]:
                for p in ("p10", "p50", "p90"):
                    # to rounding: the fixture stores draws at 15 significant digits
                    assert got[t["outcome"]][p] == pytest.approx(t[p], rel=1e-8)


def test_share_of_need_matches_the_bundle():
    # aggregate.share_of_need wrote these rows from the net statewide draws; the page recomputes them
    doc = json.loads(FIXTURE.read_text())
    script = """
const agg = require(process.argv[1]);
let s = ""; process.stdin.on("data", (c) => (s += c)).on("end", () => {
  const {draws, need} = JSON.parse(s);
  const net = agg.summarize(draws).homes_net_statewide;
  process.stdout.write(JSON.stringify(need.map((n) => agg.shareOfNeed(net, n))));
});
"""
    draws = pd.DataFrame(doc["draws"])
    for scenario, g in draws.groupby("scenario"):
        need = [n for n in doc["need"] if n["scenario"] == scenario]
        assert need, "fixture has need rows"
        got = _node(script, {"draws": _records(g), "need": need})
        for row, js in zip(need, got, strict=True):
            for k, v in js.items():
                assert v == pytest.approx(row[k], rel=1e-8), k


def test_centre_of_every_slider_is_the_engine():
    (got, centred) = _node(RUN, {"draws": _records(_draws()), "cases": [{}, {f: 50 for f in FACTORS}]})
    assert got == centred


def test_hand_worked_shift():
    # the docstring example in aggregate.js: theta 0.02 / 0.04, shifted to q=100 -> x 4/3
    base = dict(
        eligible_tier1=1000.0, eligible_tier2=0.0, eligible_tier3=0.0, pencil_out_share=0.5,
        completion_factor=1.0, net_new_share=0.6, displacement_share=0.25, overlap_share=None,
    )  # fmt: skip
    draws = [dict(base, draw=0, theta=0.02), dict(base, draw=1, theta=0.04)]
    (got,) = _node(RUN, {"draws": draws, "cases": [{"theta": 100}]})
    # permits 13.33 and 26.67: P10 = 13.33 + 0.1 x 13.33, P90 = 13.33 + 0.9 x 13.33 (numpy linear)
    assert got["permits_added"]["p10"] == pytest.approx(40 / 3 * 1.1)
    assert got["permits_added"]["p90"] == pytest.approx(40 / 3 * 1.9)
    assert got["homes_in_place"]["p50"] == pytest.approx(12.0)  # (8 + 16) / 2


def test_shift_keeps_shares_within_one():
    base = dict(
        eligible_tier1=100.0, eligible_tier2=0.0, eligible_tier3=0.0, theta=0.1, completion_factor=0.99,
        net_new_share=1.0, displacement_share=0.0, overlap_share=None,
    )  # fmt: skip
    draws = [dict(base, draw=0, pencil_out_share=0.5), dict(base, draw=1, pencil_out_share=0.9)]
    (got,) = _node(RUN, {"draws": draws, "cases": [{"pencil_out_share": 100}]})
    # scale 0.9 / 0.7: 0.643 and 1.157 -> capped at 1.0; legal x share = 64.3 and 100 pencils
    assert got["pencils"]["p90"] == pytest.approx(0.5 * 0.9 / 0.7 * 100 + 0.9 * (100 - 0.5 * 0.9 / 0.7 * 100))


def test_percentile_matches_numpy_linear():
    a = [5.0, 1.0, 4.0, 2.0, 3.0, 10.0]
    script = """
const agg = require(process.argv[1]);
let s = ""; process.stdin.on("data", (c) => (s += c)).on("end", () => {
  const {a, qs} = JSON.parse(s); process.stdout.write(JSON.stringify(qs.map((q) => agg.percentile(a, q))));
});
"""
    qs = [0, 7, 10, 33.3, 50, 90, 100]
    assert _node(script, {"a": a, "qs": qs}) == pytest.approx(list(np.percentile(a, qs)))


def test_shifting_an_unknown_column_is_refused():
    script = """
const agg = require(process.argv[1]);
try { agg.homesFromDraws([], {eligible_tier1: 50}); console.log("null"); }
catch (e) { console.log('"refused"'); }
"""
    assert _node(script, {}) == "refused"
