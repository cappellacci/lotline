"""The 'who the new homes serve' strip (WS-NEED-AMI part B) under the need chart.

The page's own script runs under node (`need_card_harness.js`) against a page built from the synthetic fixture
bundle, whose `affordability` rows come from `model.affordability.table`. Checks: every number on the strip is
a bundle field (statewide rows only, nothing below place type, S10); every midpoint has its range (S6); the
fee line follows the fee switch; the band edges match config/params/affordability.yaml; a bundle without the
table shows the pending note.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from lotline.app import build
from lotline.config import load_params

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "fixtures" / "results" / "zz" / "bundle.json"
TEMPLATE = ROOT / "src" / "lotline" / "app" / "template.html"
HARNESS = Path(__file__).with_name("need_card_harness.js")
NODE = shutil.which("node")
needs_node = pytest.mark.skipif(NODE is None, reason="node is needed to run the page's script")


def _render(tmp_path: Path, doc: dict, fee: str = "") -> dict:
    tmp_path.mkdir(parents=True, exist_ok=True)
    src = tmp_path / "zz.json"
    src.write_text(json.dumps(doc))
    build.build_app([src], out_dir=tmp_path / "app", data_summary=None)
    cmd = [NODE, str(HARNESS), str(tmp_path / "app"), "ZZ", "amiHtml", fee]
    return json.loads(subprocess.run(cmd, capture_output=True, text=True, check=True).stdout)


def _fmt_n(x: float) -> str:
    a = abs(x)
    r = round(x / 100) * 100 if a >= 10000 else round(x / 10) * 10 if a >= 1000 else round(x)
    return f"{int(r):,}"


def _pct(x: float) -> str:
    """The strip's pct0: whole percents."""
    return f"{int(x * 100 + 0.5)}%"  # Math.round, not Python's round-half-even


def _row(doc, home_type, rent_kind, fee_case, place_type="state"):
    return next(
        r
        for r in doc["affordability"]
        if (r["home_type"], r["rent_kind"], r["fee_case"], r["place_type"])
        == (home_type, rent_kind, fee_case, place_type)
    )


@needs_node
def test_strip_numbers_trace_to_the_bundle(tmp_path):
    doc = json.loads(FIXTURE.read_text())
    html = _render(tmp_path, doc)["html"]
    for h in ("adu", "plex_unit", "house"):
        m = _row(doc, h, "market", "current")
        # midpoint with its range, and the dollar income beside it (S6)
        assert f"{_fmt_n(m['income'])} income" in html
        assert f"<b>{_pct(m['ami_share'])} of area median income</b>" in html
        assert f"({_pct(m['ami_share_p10'])}–{_pct(m['ami_share_p90'])})" in html
        be = _row(doc, h, "break_even", "current")
        assert (
            f"needs {_pct(be['ami_share'])} of AMI ({_pct(be['ami_share_p10'])}–{_pct(be['ami_share_p90'])})"
            in html
        )
    method, chart = html.index("How we worked this out"), html.index("ami-grid")
    assert method < chart < html.index("How to read this chart")
    assert "What this is not" in html and "not what they rent for" in html


@needs_node
def test_strip_shows_no_place_below_the_state(tmp_path):
    doc = json.loads(FIXTURE.read_text())
    html = _render(tmp_path, doc)["html"]
    core = _row(doc, "adu", "market", "current", "core")
    state = _row(doc, "adu", "market", "current")
    if round(core["income"], -1) != round(state["income"], -1):
        assert f"${_fmt_n(core['income'])} income" not in html


@needs_node
def test_fee_line_follows_the_switch(tmp_path):
    doc = json.loads(FIXTURE.read_text())
    local = _render(tmp_path / "a", doc, fee="fees_local_half")["html"]
    bench = _render(tmp_path / "b", doc, fee="fees")["html"]
    half = _row(doc, "plex_unit", "break_even", "fees_local_half")
    hb = _row(doc, "plex_unit", "break_even", "fees")
    assert f"With real local fees cut in half: ${_fmt_n(half['value'])} a month" in local
    assert f"($50,000 fee cut in half): ${_fmt_n(hb['value'])} a month" in bench
    assert "The model charges ADUs no fee" in local


@needs_node
def test_no_affordability_rows_shows_the_pending_note(tmp_path):
    doc = json.loads(FIXTURE.read_text())
    doc["affordability"] = []
    assert "needs HUD's income limits file" in _render(tmp_path, doc)["html"]


def test_band_edges_match_the_parameters():
    p = load_params("affordability")
    m = re.search(
        r"const AMI_BANDS = \{ subsidy: ([\d.]+), zoning: ([\d.]+), max: ([\d.]+) \};", TEMPLATE.read_text()
    )
    assert m, "AMI_BANDS not found in template.html"
    assert [float(v) for v in m.groups()] == [
        p["band_subsidy_below"].value,
        p["band_zoning_above"].value,
        p["axis_max"].value,
    ]


@needs_node
def test_takeaway_names_only_the_homes_cheaper_than_a_new_house(tmp_path):
    doc = json.loads(FIXTURE.read_text())
    house = _row(doc, "house", "market", "current")["ami_share"]
    html = _render(tmp_path / "a", doc)["html"]
    lead = html[html.index('id="ami-lead"') :].split("</p>")[0]
    assert (
        "ADUs and missing-middle homes add an important layer of affordability" in lead
    )  # both below the house
    assert f"against {_pct(house)} for a new single-family house" in lead
    # make the house cheaper than an ADU: the lead names missing middle only
    for r in doc["affordability"]:
        if r["home_type"] == "adu" and r["rent_kind"] == "market":
            r["ami_share"] = house + 0.1
    lead = _render(tmp_path / "b", doc)["html"]
    lead = lead[lead.index('id="ami-lead"') :].split("</p>")[0]
    assert "Missing-middle homes add an important layer" in lead and "ADUs and" not in lead
