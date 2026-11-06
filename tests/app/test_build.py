"""The app page builds from the committed fixture bundle, contains every section, and stays state-agnostic.

Promise tested here (WS-APP brief, acceptance): the page builds from a clean clone with the fixture bundle;
every state with a bundle appears without code changes; the footer carries the bundle's provenance (D1).
"""

import json
import re
from pathlib import Path

import pandera.errors
import pytest

from lotline.app import build

REPO = Path(__file__).resolve().parents[2]
FIXTURE = REPO / "tests" / "fixtures" / "results" / "zz" / "bundle.json"


def _embedded(html: str) -> dict:
    m = re.search(r'<script id="lotline-data" type="application/json">(.*?)</script>', html, re.S)
    assert m, "data script missing"
    return json.loads(m.group(1))


def test_page_builds_from_fixture_and_has_every_section(tmp_path):
    page = build.build_app([FIXTURE], out_dir=tmp_path, generated="2026-11-06T00:00:00Z")
    html = page.read_text(encoding="utf-8")
    for section in ("results", "data", "trust"):
        assert f'data-section="{section}"' in html
    for heading in ("Results", "The data", "How well does it hold up?"):
        assert heading in html
    # identity inlined from the one source, no placeholder left behind
    assert "--scenario-adu" in html and "/*__" not in html and "<!--__" not in html
    assert "data:image/svg+xml;base64," in html  # wordmark inlined, page stays self-contained
    data = _embedded(html)
    assert [b["meta"]["state"] for b in data["states"]] == ["ZZ"]
    assert data["generated"] == "2026-11-06T00:00:00Z"
    assert data["states"][0] == json.loads(FIXTURE.read_text())  # embedded as-is
    assert "uv run lotline results --all" in html


def test_page_needs_no_server_or_network():
    # the shell loads nothing from the network: no external script, stylesheet or font yet
    html = build.render(build.payload([json.loads(FIXTURE.read_text())], "t"))
    assert not re.search(r'<(script|link)[^>]+(src|href)="https?://', html)


def test_every_bundle_under_results_dir_appears_in_role_order(tmp_path):
    doc = json.loads(FIXTURE.read_text())
    for st, role in (("ZZ", "development"), ("ZY", "transfer"), ("ZX", "benchmark")):
        b = json.loads(json.dumps(doc))
        b["meta"]["state"], b["meta"]["state_role"] = st, role
        for part in ("draws", "funnel", "totals", "need", "scorecard"):
            for row in b[part]:
                row["state"] = st
        d = tmp_path / "results" / st.lower()
        d.mkdir(parents=True)
        (d / "bundle.json").write_text(json.dumps(b))
    page = build.build_app(results_dir=tmp_path / "results", out_dir=tmp_path / "app")
    states = [b["meta"]["state"] for b in _embedded(page.read_text())["states"]]
    assert states == ["ZX", "ZZ", "ZY"]  # benchmark, development, transfer


def test_invalid_bundle_is_refused(tmp_path):
    doc = json.loads(FIXTURE.read_text())
    doc["meta"]["overlap_flag"] = "excellent"  # not in the enum
    bad = tmp_path / "bundle.json"
    bad.write_text(json.dumps(doc))
    with pytest.raises(pandera.errors.SchemaErrors):
        build.build_app([bad], out_dir=tmp_path)


def test_no_bundles_and_duplicate_states_are_refused(tmp_path):
    with pytest.raises(ValueError, match="no results bundles"):
        build.build_app(results_dir=tmp_path, out_dir=tmp_path)
    doc = json.loads(FIXTURE.read_text())
    with pytest.raises(ValueError, match="more than one bundle"):
        build.payload([doc, doc])


def test_json_cannot_close_its_script_tag():
    doc = json.loads(FIXTURE.read_text())
    doc["meta"]["overlap_note"] = "</script><script>alert(1)</script>"
    html = build.render(build.payload([doc], "t"))
    assert _embedded(html)["states"][0]["meta"]["overlap_note"] == doc["meta"]["overlap_note"]


def test_script_builds_the_page(tmp_path):
    from importlib.util import module_from_spec, spec_from_file_location

    spec = spec_from_file_location("build_app", REPO / "scripts" / "build_app.py")
    mod = module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.main(["--bundle", str(FIXTURE), "--out", str(tmp_path)]) == 0
    assert (tmp_path / "index.html").exists()


def test_no_state_names_in_app_code():
    # WS-APP brief: no state-specific branches; state codes come only from bundles
    configured = [p.stem.upper() for p in (REPO / "config" / "states").glob("*.yaml")]
    for f in (build.TEMPLATE, Path(build.__file__)):
        text = f.read_text(encoding="utf-8")
        for st in configured:
            assert not re.search(rf'["\']{st}["\']', text), f"{st} hard-coded in {f.name}"
