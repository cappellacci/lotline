"""The page labels the five-year window from the bundle, so it shows 2027–2031 for a 2025 origin (D-061).

Promise tested here: D-061 puts a baseline-only lead year between the 2025 data origin and the window, so the
window is 2027-2031 (`baseline.window_label`). The page reads that label from the bundle's multi-year
`totals.period` (`windowLabel` in src/lotline/app/aggregate.js) instead of working it out as origin + 1, which
gave 2026-2030. With no multi-year row it prints no years rather than a guessed window.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from lotline.app import build
from lotline.model import baseline

REPO = Path(__file__).resolve().parents[2]
JS = REPO / "src" / "lotline" / "app" / "aggregate.js"
FIXTURE = REPO / "tests" / "fixtures" / "results" / "zz" / "bundle.json"
NODE = shutil.which("node")

LABEL = """
const agg = require(process.argv[1]);
let s = ""; process.stdin.on("data", (c) => (s += c)).on("end", () => {
  process.stdout.write(JSON.stringify(JSON.parse(s).map((b) => agg.windowLabel(b))));
});
"""


def _labels(bundles: list[dict]) -> list:
    out = subprocess.run(
        [NODE, "-e", LABEL, str(JS)], input=json.dumps(bundles), capture_output=True, text=True, check=True
    )
    return json.loads(out.stdout)


@pytest.mark.skipif(NODE is None, reason="node is needed to run the page's label helper")
def test_window_label_reads_the_bundle_period_not_origin_plus_one():
    bundle = json.loads(FIXTURE.read_text())
    assert bundle["meta"]["origin_year"] == 2025
    # by hand (D-061): origin 2025, lead 1, horizon 5 -> 2027-2031; the old origin + 1 rule gave 2026-2030
    assert baseline.window_label(bundle["meta"]["origin_year"]) == "2027-2031"
    no_totals = {**bundle, "totals": []}
    single_years = {**bundle, "totals": [r for r in bundle["totals"] if "-" not in r["period"]]}
    assert _labels([bundle, no_totals, single_years]) == ["2027–2031", None, None]


def test_page_does_not_work_out_the_window_from_meta():
    html = build.render(build.payload([json.loads(FIXTURE.read_text())], "t"))
    assert "origin_year + 1" not in html and "origin_year+1" not in html
    assert "AGG.windowLabel(b)" in html


def test_every_window_label_call_on_b_sits_in_a_function_that_takes_b():
    """The Model page's deep dives (`drawDeepDive`, `mmDeepDive`) hold only `bs`: a `windowLabel(b)` there
    threw "b is not defined" and left both sections on their placeholder (nightly review, 2026-11-25). Each
    top-level function that calls `windowLabel(b)` must take `b` as a parameter."""
    import re

    page = (REPO / "src" / "lotline" / "app" / "template.html").read_text(encoding="utf-8")
    starts = [
        (m.start(), m.group(1), m.group(2))
        for m in re.finditer(r"^(?:async )?function (\w+)\(([^)]*)\)", page, re.M)
    ]
    bad = []
    for i, (pos, name, params) in enumerate(starts):
        body = page[pos : starts[i + 1][0] if i + 1 < len(starts) else len(page)]
        if "windowLabel(b)" in body and "b" not in [p.split("=")[0].strip() for p in params.split(",")]:
            bad.append(name)
    assert not bad, f"windowLabel(b) used where no `b` parameter exists: {bad}"
