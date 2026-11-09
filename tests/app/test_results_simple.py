"""Section 1 of the app, the "two worlds" results story (WS-RESULTS-SIMPLE; copy in src/lotline/app/copy/results.md).

Promises tested here (brief, "Design rules" and "Tasks"):
- one tab per single policy, never a stacked pair or "combined" (Ben, 2026-11-09);
- every number in the story comes from the bundle: no number is written into the copy or the sentence templates;
- a midpoint is never shown without its likely range (S6);
- the "reason to believe it" line reads a scorecard row and falls back to words, never a hand-written number;
- the story renders from the fixture bundle with the headline added homes equal to the bundle's own totals.
"""

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from lotline.app import build

REPO = Path(__file__).resolve().parents[2]
FIXTURE = REPO / "tests" / "fixtures" / "results" / "zz" / "bundle.json"
TEMPLATE = build.TEMPLATE.read_text(encoding="utf-8")
NODE = shutil.which("node")
needs_node = pytest.mark.skipif(NODE is None, reason="node is needed to run the page's JavaScript")


def _block(start: str, end: str) -> str:
    a = TEMPLATE.index(start)
    return TEMPLATE[a : TEMPLATE.index(end, a)]


def _strip_expressions(js: str) -> str:
    """Template-literal text with every ${...} expression (nested braces included) removed."""
    out, i = [], 0
    while i < len(js):
        if js.startswith("${", i):
            depth, i = 1, i + 2
            while depth and i < len(js):
                depth += {"{": 1, "}": -1}.get(js[i], 0)
                i += 1
        else:
            out.append(js[i])
            i += 1
    return "".join(out)


def _visible_literal_text(js: str) -> str:
    """The words a reader can see from a block's template literals: expressions, tags and entities removed."""
    # Expressions first: they can hold nested template literals of their own.
    literals = re.findall(r"`([^`]*)`", _strip_expressions(js), re.S)
    text = " ".join(literals)
    text = re.sub(r"<[^>]*>", " ", text)
    return re.sub(r"&\w+;", " ", text)


# ------------------------------------------------------------------------------------------------ the policy copy
def test_one_tab_per_single_policy_never_combined():
    pol = build.policy_copy()
    assert list(pol) == ["adu", "missing_middle", "fees"]
    assert all(len(p["limits"]) == 3 and "{legal}" in p["legal"] for p in pol.values())


@pytest.mark.parametrize(
    "bad, match",
    [
        ("combined:\n  legal: 'x {legal}'\n  limits: [[a, b], [c, d], [e, f]]\n", "not a single-policy"),
        ("adu+fees:\n  legal: 'x {legal}'\n  limits: [[a, b], [c, d], [e, f]]\n", "not a single-policy"),
        ("adu:\n  legal: 'on 300 lots {legal}'\n  limits: [[a, b], [c, d], [e, f]]\n", "number written"),
        ("adu:\n  legal: 'no slot'\n  limits: [[a, b], [c, d], [e, f]]\n", "slot"),
        ("adu:\n  legal: 'x {legal}'\n  limits: [[a, b]]\n", "three limits"),
    ],
)
def test_policy_copy_is_refused_when_it_breaks_a_rule(tmp_path, bad, match):
    f = tmp_path / "scenarios.yaml"
    f.write_text(bad)
    with pytest.raises(ValueError, match=match):
        build.policy_copy(f)


def test_page_embeds_the_policy_tabs(tmp_path):
    html = build.build_app([FIXTURE], out_dir=tmp_path, data_summary=None).read_text()
    m = re.search(r'<script id="lotline-data" type="application/json">(.*?)</script>', html, re.S)
    assert list(json.loads(m.group(1))["policies"]) == ["adu", "missing_middle", "fees"]
    for part in ('role="tablist"', 'id="worlds"', 'id="diff"', 'id="headline-sentence"', 'id="trust-line"',
                 'id="funnel-words"', "What this can't tell you", "Change the assumptions", "Full methodology"):  # fmt: skip
        assert part in html, part


# ------------------------------------------------------------------------------- numbers come from the bundle
def test_story_sentences_have_no_number_written_in():
    story = (
        _block("  results(b) {", "  data(b) {")
        + _block("const policiesIn", "function drawWorlds")
        + _block("function updateResults", "function drawTornado")
    )
    text = _visible_literal_text(story)
    # The one allowed literal: the definition of "likely range" in the More detail fold.
    text = text.replace("middle 80% of those runs (P10 to P90)", "")
    assert not re.search(r"\d", text), re.findall(r".{30}\d.{30}", text)


def test_the_map_is_below_the_story():
    page = _block('<section class="part" id="page-results"', "</section>")
    assert page.index('id="results-body"') < page.index('id="map-card"')


# --------------------------------------------------------------------------------- run the story's own JS
HELPERS = ("const fmtN", "const fmtInt")  # fmtN ends where fmtInt starts


def _run(script: str):
    fmt = _block(*HELPERS)
    story = _block("const policiesIn", "function drawWorlds")
    prelude = (
        "const esc = (s) => String(s);\n"
        "const DATA = { policies: {}, scenarios: {}, map: { tiles: [{ code: 'ZZ', name: 'Zedland' }] } };\n"
        + fmt + story
    )
    out = subprocess.run([NODE, "-e", prelude + script], capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


@needs_node
def test_a_midpoint_always_carries_its_range():
    got = _run(
        "console.log(JSON.stringify([withRange({p10: 103, p50: 259, p90: 791}),"
        " withRange({p10: 1700, p50: 1700, p90: 1700})]))"
    )
    assert got == ["259 (likely range 103–791)", "1,700"]  # a count every run agrees on has no range to show


@needs_node
def test_trust_line_reads_the_scorecard_or_says_it_has_not_been_checked():
    meta = "{meta: {state: 'ZZ'}}"
    row = "{metric: 'abs_pct_error_5y', value: 0.12, label: '2019–2023'}"
    got = _run(
        f"console.log(JSON.stringify([trustLine({{...{meta}, scorecard: []}}),"
        f" trustLine({{...{meta}, scorecard: [{row}]}})]))"
    )
    assert got[0] == "We have not yet checked this model against past years in Zedland."
    assert got[1] == (
        "When we ran this model on 2019–2023 without seeing the answer, it landed within 12% of what was actually built."
    )


@needs_node
def test_headline_added_homes_match_the_bundle_totals():
    """At default sliders the story's +N is the bundle's `permits_added` midpoint (same draws, same arithmetic)."""
    agg = build.AGGREGATE_JS.read_text(encoding="utf-8")
    b = json.loads(FIXTURE.read_text())
    want = next(t for t in b["totals"] if t["outcome"] == "permits_added" and "-" in t["period"])
    draws = [d for d in b["draws"] if d["scenario"] == want["scenario"]]
    script = agg + f"\nconsole.log(JSON.stringify(module.exports.summarize({json.dumps(draws)}).permits_added))"
    out = subprocess.run([NODE, "-e", script], capture_output=True, text=True, check=True)
    got = json.loads(out.stdout)
    for q in ("p10", "p50", "p90"):
        assert got[q] == pytest.approx(want[q], rel=1e-9)
