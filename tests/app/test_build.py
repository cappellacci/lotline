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
    page = build.build_app([FIXTURE], out_dir=tmp_path, generated="2026-11-06T00:00:00Z", data_summary=None)
    html = page.read_text(encoding="utf-8")
    for section in ("results", "data", "trust"):
        assert f'data-section="{section}"' in html
    for heading in ("Results", "The data", "The model"):
        assert heading in html
    # identity inlined from the one source, no placeholder left behind
    assert "--scenario-adu" in html and "/*__" not in html and "<!--__" not in html
    assert "data:image/svg+xml;base64," in html  # wordmark inlined, page stays self-contained
    data = _embedded(html)
    assert [b["meta"]["state"] for b in data["states"]] == ["ZZ"]
    assert data["generated"] == "2026-11-06T00:00:00Z"
    assert data["states"][0] == json.loads(FIXTURE.read_text())  # embedded as-is
    assert "uv run lotline results --all" in html


def test_page_needs_no_server_and_loads_only_the_brand_fonts():
    # no external script; the only external stylesheet is the brand fonts (OFL, docs/disclosures.md),
    # and the page reads fine without it (tokens.css names system fallbacks)
    html = build.render(build.payload([json.loads(FIXTURE.read_text())], "t"))
    assert not re.search(r'<script[^>]+src="https?://', html)
    links = re.findall(r'<link[^>]+href="(https?://[^"]+)"', html)
    assert all(u.startswith(("https://fonts.googleapis.com", "https://fonts.gstatic.com")) for u in links)
    assert any("Public+Sans" in u and "IBM+Plex+Mono" in u for u in links)
    assert '"Public Sans", "Helvetica Neue", Arial, sans-serif' in html  # fallback stack inlined


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
    page = build.build_app(results_dir=tmp_path / "results", out_dir=tmp_path / "app", data_summary=None)
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
    assert mod.main(["--bundle", str(FIXTURE), "--out", str(tmp_path), "--no-data-summary"]) == 0
    assert (tmp_path / "index.html").exists()


def test_no_state_names_in_app_code():
    # WS-APP brief: no state-specific branches; state codes come only from bundles
    configured = [p.stem.upper() for p in (REPO / "config" / "states").glob("*.yaml")]
    for f in (build.TEMPLATE, Path(build.__file__)):
        text = f.read_text(encoding="utf-8")
        for st in configured:
            assert not re.search(rf'["\']{st}["\']', text), f"{st} hard-coded in {f.name}"


def test_scenario_labels_cover_the_schema_in_order():
    from lotline.schemas import SCENARIOS

    assert list(build.SCENARIOS) == list(SCENARIOS)
    assert build.SCENARIOS["adu"][0] == "ADUs" and build.SCENARIOS["fees"][0] == "Fee reduction"  # Handbook


def test_every_slider_is_a_draws_factor_with_its_citation_from_config():
    from lotline.config import load_params
    from lotline.schemas import columns

    ks = build.knobs()
    assert {k["column"] for k in ks} <= set(columns("results_draws"))
    for k in ks:
        assert k["label"] and k["why"] and k["low_word"] and k["high_word"]
        for rows in k["params"].values():
            for r in rows:
                p = load_params(r["file"])[r["key"]]
                assert (r["value"], r["low"], r["high"], r["source"]) == (p.value, p.low, p.high, p.source)


def test_a_slider_citing_an_unknown_parameter_is_refused(tmp_path):
    bad = tmp_path / "knobs.yaml"
    bad.write_text(
        "theta:\n  label: x\n  why: y\n  low_word: a\n  high_word: b\n  params:\n    adu: [hazard:nope]\n"
    )
    with pytest.raises(KeyError):
        build.knobs(bad)


def test_results_section_parts_are_on_the_page(tmp_path):
    html = build.build_app([FIXTURE], out_dir=tmp_path, data_summary=None).read_text()
    for part in ('id="headline"', 'id="ranges"', 'id="need"', 'id="funnel"', 'id="knobs"', "pencil out",
                 "How far the model is reaching", "LotlineAggregate"):  # fmt: skip
        assert part in html, part


# ------------------------------------------------------------------------------- section 2: the data
SUMMARY = {
    "generated": "2026-11-05T00:00:00Z",
    "population_source": None,
    "states": [
        {
            "state": "ZZ",
            "name": "Zedland",
            "totals": {
                "population_covered_share": 0.5,
                "jurisdictions": 4,
                "jurisdictions_covered": 2,
                "parcels": 300,
                "reforms": 1,
                "permit_years": [2000, 2024],
                "tiers": {"1": 2, "3": 2},
            },
            "parcel_sources": [
                {"source": "bps", "parcels_latest": 300, "parcels_used": 250, "vintages": [2026]}
            ],
        }  # fmt: skip
    ],
}


def test_available_vs_used_lists_every_registry_source_and_parcels_used():
    from lotline.registry import sources_for

    d = build.data_section(["ZZ"], SUMMARY)
    rows = d["by_state"]["ZZ"]["sources"]
    assert [r["source"] for r in rows] == list(sources_for("ZZ"))  # available = the registry, nothing else
    by = {r["source"]: r for r in rows}
    assert (by["bps"]["parcels_on_file"], by["bps"]["parcels_used"]) == (300, 250)  # used, from the summary
    assert all(r["parcels_used"] is None for r in rows if r["source"] != "bps")
    assert d["by_state"]["ZZ"]["totals"]["parcels"] == 300 and d["summary_generated"] == SUMMARY["generated"]


def test_without_a_data_summary_sources_are_still_listed():
    d = build.data_section(["ZZ"], None)
    assert d["by_state"]["ZZ"]["totals"] is None and d["by_state"]["ZZ"]["sources"]


def test_data_dashboard_is_embedded_when_its_summary_exists(tmp_path):
    summary = tmp_path / "summary.json"
    summary.write_text(json.dumps(SUMMARY))
    html = build.build_app([FIXTURE], out_dir=tmp_path, data_summary=summary).read_text()
    m = re.search(r'<script id="lotline-dashboard" type="application/json">(.*?)</script>', html, re.S)
    dash = json.loads(m.group(1))
    assert dash.startswith("<!doctype html>") and "Zedland" in dash  # the dashboard's own page, our summary
    assert _embedded(html)["data"]["by_state"]["ZZ"]["name"] == "Zedland"
    for part in ("Data available and data used", "Data tier", 'id="open-dash"'):
        assert part in html
    without = build.build_app([FIXTURE], out_dir=tmp_path / "b", data_summary=None).read_text()
    m = re.search(r'<script id="lotline-dashboard" type="application/json">(.*?)</script>', without, re.S)
    assert json.loads(m.group(1)) is None


# ---------------------------------------------------------------------- section 3: how well it holds up
def test_trust_section_parts_and_overlap_thresholds_from_config(tmp_path):
    from lotline.config import load_params

    html = build.build_app([FIXTURE], out_dir=tmp_path, data_summary=None).read_text()
    for part in ("Validation scorecard", "Blind tests", "Overlap check", 'id="tornado"', "Technical detail"):
        assert part in html, part
    agg = load_params("aggregate")
    assert _embedded(html)["overlap_thresholds"] == {
        "medium": agg["overlap_flag_medium_distance"].value,
        "low": agg["overlap_flag_low_distance"].value,
    }
    # the fixture's scorecard row reaches the page as-is
    assert _embedded(html)["states"][0]["scorecard"][0]["check_id"] == "V1"


def test_sections_are_separate_pages_with_the_intro_above_them(tmp_path):
    html = build.build_app([FIXTURE], out_dir=tmp_path, data_summary=None).read_text()
    assert "Housing Reform Model" in html and "Lotline is a tool to help understand" in html
    # one page shown at a time: results first, the other two hidden until their tab is chosen
    assert '<section class="part" id="page-results" data-section="results">' in html
    for page in ("data", "trust"):
        assert f'id="page-{page}" data-section="{page}" hidden>' in html
        assert f'href="#{page}" data-page="{page}"' in html


def test_state_picker_and_mark_sit_in_the_menu_bar(tmp_path):
    html = build.build_app([FIXTURE], out_dir=tmp_path, data_summary=None).read_text()
    nav = re.search(r'<nav class="sections".*?</nav>', html, re.S).group(0)
    assert 'id="state"' in nav and 'class="mark"' in nav and nav.count("data:image/svg+xml;base64,") == 2
    assert 'id="state"' not in re.search(r'<header class="mast">.*?</header>', html, re.S).group(0)
