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


def _state_file(out: Path, state: str) -> dict:
    """A state's bundle as the page loads it: states/<st>.js calling LotlineState(<json>)."""
    text = (out / "states" / f"{state.lower()}.js").read_text(encoding="utf-8")
    m = re.fullmatch(r"LotlineState\((.*)\);\n", text, re.S)
    assert m, "state file is not a single LotlineState(...) call"
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
    fixture = json.loads(FIXTURE.read_text())
    assert data["states"][0] == {"meta": fixture["meta"], "file": "states/zz.js"}  # the page embeds meta only
    assert _state_file(tmp_path, "ZZ") == fixture  # the full bundle, as-is, in its own file
    assert "uv run lotline results --all" in html


def test_page_needs_no_server_or_network_and_carries_its_fonts():
    # no external script or stylesheet; the brand fonts are inlined from docs/build/identity/fonts (OFL)
    html = build.render(build.payload([json.loads(FIXTURE.read_text())], "t"))
    assert not re.search(r'<(script|link)[^>]+(src|href)="https?://', html)
    assert "fonts.googleapis.com" not in html
    for family in build.APP_FONT_FAMILIES:
        assert f'font-family: "{family}"' in html
    assert html.count('url("data:font/woff2;base64,') == 6  # Public Sans 400-700, Plex Mono 400 and 500
    assert '"Source Serif 4"; font-style' not in html  # report-only face left out of the page


def test_every_font_file_is_listed_and_licensed():
    fonts = build.IDENTITY / "fonts"
    css = (fonts / "fonts.css").read_text()
    files = sorted(p.name for p in fonts.glob("*.woff2"))
    assert files == sorted(re.findall(r'url\("([^"]+)"\)', css))
    for family in ("PublicSans", "IBMPlexMono", "SourceSerif4"):
        lic = next(fonts.glob(f"{family}-OFL.*")).read_text()
        assert "SIL Open Font License, Version 1.1" in lic


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
    assert "<b>Provisional:</b> how the sliders move an assumption" in html  # Ben, 2026-11-06
    for part in ('id="headline"', 'id="ranges"', 'id="need"', 'id="funnel"', 'id="knobs"', "pencil out",
                 "How far the model is reaching", "LotlineAggregate"):  # fmt: skip
        assert part in html, part


def test_gross_and_net_are_explained_in_plain_words(tmp_path):
    """Ben, 2026-11-09: the toggle reads "All new homes" / "Net new housing", a "Why two numbers?" note uses
    the state's own figures, and the displacement slider says what it means. The old wording is gone."""
    html = build.build_app([FIXTURE], out_dir=tmp_path, data_summary=None).read_text()
    for part in ('"All new homes"', '"Net new housing"', "Why two numbers?", 'id="two-numbers"',
                 "Homes that would have been built elsewhere in the state anyway"):  # fmt: skip
        assert part in html, part
    for gone in ("In the places that build", "places that build", "Net statewide", "pulled in from nearby",
                 "Homes pulled from nearby places"):  # fmt: skip
        assert gone not in html, gone


def test_record_chart_reads_observed_permits_and_yearly_forecasts(tmp_path):
    """Schemas 1.12 (Ben, 2026-11-09): actual yearly permits as bars beside the reform's yearly additions."""
    html = build.build_app([FIXTURE], out_dir=tmp_path, data_summary=None).read_text()
    parts = ('id="record-card"', "function recordHtml", "What gets built now, and what the reform would add")
    for part in (*parts, "Actually permitted", "Added by the reform (P10–P90"):
        assert part in html, part
    state_file = (tmp_path / "states" / "zz.js").read_text()
    doc = json.loads(state_file[state_file.index("(") + 1 : state_file.rindex(")")])
    measures = {r["measure"] for r in doc["observed"]}
    assert measures == {"adu_permits", "homes_2_4"}
    yearly = [r for r in doc["totals"] if r["outcome"] == "permits_added" and len(r["period"]) == 4]
    assert len(yearly) == 5  # one per window year, the whiskers


def test_baseline_card_reads_the_bundle_baseline(tmp_path):
    """Schemas 1.11: the page shows the no-change forecast from the bundle's `baseline` part."""
    html = build.build_app([FIXTURE], out_dir=tmp_path, data_summary=None).read_text()
    parts = ("function baselineHtml", "With no policy change", "${baselineHtml(b)}", "0 added, by definition")
    for part in (*parts, "The baseline forecast is not in this state's results yet."):
        assert part in html, part
    state_file = (tmp_path / "states" / "zz.js").read_text()
    doc = json.loads(state_file[state_file.index("(") + 1 : state_file.rindex(")")])
    window = [r for r in doc["baseline"] if r["size_class"] == "all" and r["period"] == "2027-2031"]
    assert len(window) == 1 and window[0]["p10"] <= window[0]["p50"] <= window[0]["p90"]


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
    assert 'id="lotline-fold"' in dash and "--paper:" in dash  # restyled with the tokens, header hidden
    for part in ("Data available and data used", 'id="dash-host"', 'id="dash-frame"', 'id="dash-state"'):
        assert part in html
    # The tier card was dropped (Ben, 2026-11-09): the dashboard carries coverage.
    assert '<p class="eyebrow">Data tier</p>' not in html
    assert 'scope: "ALL"' in html  # the dashboard opens on every state, with its own dropdown
    # Ben, 2026-11-09: the data page opens with what the model needs and from which years, then the
    # dashboard, and lists every source last.
    slots = ('id="data-method"', 'id="data-body"', 'id="dash-host"', 'id="data-sources"')
    order = [html.index(p) for p in slots]
    assert order == sorted(order)
    method = html[html.index('id="data-method"') : html.index('id="data-body"')]
    kinds = ("Parcels", "Zoning", "Building permits", "Prices and rents", "Development fees", "2027–2031")
    for kind in kinds:
        assert kind in method, kind
    without = build.build_app([FIXTURE], out_dir=tmp_path / "b", data_summary=None).read_text()
    m = re.search(r'<script id="lotline-dashboard" type="application/json">(.*?)</script>', without, re.S)
    assert json.loads(m.group(1)) is None


# ---------------------------------------------------------------------- section 3: how well it holds up
def test_trust_section_parts_and_overlap_thresholds_from_config(tmp_path):
    from lotline.config import load_params

    html = build.build_app([FIXTURE], out_dir=tmp_path, data_summary=None).read_text()
    parts = (
        "Overlap check",
        'id="tornado"',
        "Technical detail",
        'id="dag"',
        'id="conf-table"',
        'id="checks"',
    )
    for part in parts:
        assert part in html, part
    # Ben, 2026-11-09: the model page runs in order: goal, data, model and range, other states, then limits.
    steps = ["step-goal", "step-data", "step-model", "step-states", "step-limits"]
    assert [html.index(f'id="{s}"') for s in steps] == sorted(html.index(f'id="{s}"') for s in steps)
    register = (REPO / "docs/research/lotline-confounder-register.csv").read_text().splitlines()[1:]
    ids = [line.split(",", 1)[0] for line in register if line.strip()]
    for cid in ids:  # every factor in the register is on the page with what was done about it
        assert f'["{cid}", ' in html, cid
    agg = load_params("aggregate")
    assert _embedded(html)["overlap_thresholds"] == {
        "medium": agg["overlap_flag_medium_distance"].value,
        "low": agg["overlap_flag_low_distance"].value,
    }
    # the fixture's scorecard row reaches the page as-is
    assert _state_file(tmp_path, "ZZ")["scorecard"][0]["check_id"] == "V1"


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
    assert '<link rel="icon" type="image/svg+xml" href="data:image/svg+xml;base64,' in html  # favicon cut
    assert 'id="state"' not in re.search(r'<header class="mast">.*?</header>', html, re.S).group(0)


def test_overall_sums_every_state_in_the_summary():
    two = json.loads(json.dumps(SUMMARY))
    second = json.loads(json.dumps(SUMMARY["states"][0]))
    second["state"] = "ZY"
    second["totals"] = dict(second["totals"], parcels=700, reforms=4, permit_years=[1995, 2025])
    two["states"].append(second)
    o = build.overall(two)
    assert o["states"] == ["ZZ", "ZY"] and o["parcels"] == 1000 and o["reforms"] == 5
    assert (o["permit_first"], o["permit_last"]) == (1995, 2025)
    assert build.overall(None) is None
    html = build.render(build.payload([json.loads(FIXTURE.read_text())], "t", two))
    assert _embedded(html)["data"]["overall"]["parcels"] == 1000 and 'id="data-lead"' in html


def test_state_map_has_every_state_once_and_every_configured_state():
    m = build.tile_map()
    codes = [t["code"] for t in m["tiles"]]
    assert len(codes) == len(set(codes)) == 51  # 50 states and DC
    assert len({(t["row"], t["col"]) for t in m["tiles"]}) == 51
    configured = {p.stem.upper() for p in (REPO / "config" / "states").glob("*.yaml")}
    assert configured <= set(codes)


def test_state_map_refuses_a_repeated_tile(tmp_path):
    bad = tmp_path / "tiles.yaml"
    bad.write_text("tiles:\n  - [AA, A, 0, 0]\n  - [BB, B, 0, 0]\n")
    with pytest.raises(ValueError, match="twice"):
        build.tile_map(bad)


def test_state_map_colours_every_tier_and_links_grey_states_to_the_readme():
    import tomllib

    from lotline.schemas import DATA_TIERS

    m = build.tile_map()
    tokens = (build.IDENTITY / "tokens.css").read_text(encoding="utf-8")
    assert sorted(int(k) for k in m["tier_tokens"]) == DATA_TIERS
    for tok in m["tier_tokens"].values():
        assert f"{tok}:" in tokens  # a real identity token, light and dark
    # richer data is the stronger step of the ramp
    steps = [int(m["tier_tokens"][str(t)].rsplit("-", 1)[1]) for t in DATA_TIERS]
    assert steps == sorted(steps, reverse=True)
    repo = tomllib.loads((REPO / "challenge.toml").read_text(encoding="utf-8"))["links"]["repo_url"]
    assert m["byos_url"] == repo.rstrip("/") + build.BYOS_ANCHOR
    assert "\n## Bring your own state\n" in (REPO / "README.md").read_text(encoding="utf-8")


def test_state_map_is_on_the_results_page(tmp_path):
    page = build.build_app([FIXTURE], out_dir=tmp_path, generated="t", data_summary=None)
    html = page.read_text(encoding="utf-8")
    assert 'id="state-map"' in html and 'id="map-legend"' in html and "Choose a state" in html
    assert html.index('id="map-card"') < html.index('id="page-data"')  # on page 1
    assert _embedded(html)["map"] == build.tile_map()


def test_each_state_gets_its_own_file_and_stale_files_are_removed(tmp_path):
    # The page stays small with every state run: it carries meta only; each bundle loads when picked.
    stale = tmp_path / "states" / "qq.js"
    stale.parent.mkdir(parents=True)
    stale.write_text("old")
    page = build.build_app([FIXTURE], out_dir=tmp_path, data_summary=None)
    assert sorted(p.name for p in (tmp_path / "states").iterdir()) == ["zz.js"]
    assert '"draws"' not in page.read_text(encoding="utf-8")


def test_state_file_names_only_take_two_letter_codes():
    assert build.state_file("ZZ") == "states/zz.js"
    # the page rebuilds the same path from the checked code rather than reading it from the data
    assert "`states/${state.toLowerCase()}.js`" in build.TEMPLATE.read_text(encoding="utf-8")
    for bad in ("../x", "Z", "zz", "Z/"):
        with pytest.raises(ValueError):
            build.state_file(bad)


def test_state_script_cannot_close_a_script_tag():
    doc = json.loads(FIXTURE.read_text())
    doc["meta"]["overlap_note"] = "</script><script>alert(1)</script>"
    assert "</script>" not in build.state_script(doc)


# --- Publishing: scripts/publish_app.py -> GitHub release -> .github/workflows/pages.yml


def _results_dir(tmp_path: Path) -> Path:
    """A results folder holding the fixture under a folder name that is not its state code."""
    d = tmp_path / "results" / "somewhere"
    d.mkdir(parents=True)
    (d / "bundle.json").write_bytes(FIXTURE.read_bytes())
    return tmp_path / "results"


def test_staged_release_holds_each_bundle_unchanged_under_its_own_state_code(tmp_path):
    summary = tmp_path / "summary.json"
    summary.write_text("{}", encoding="utf-8")
    stage = tmp_path / "stage"
    stage.mkdir()
    (stage / "old.bundle.json").write_text("stale", encoding="utf-8")
    files = build.stage_release(stage, results_dir=_results_dir(tmp_path), data_summary=summary)
    assert [f.name for f in files] == ["zz.bundle.json", "data-summary.json"]
    assert (stage / "zz.bundle.json").read_bytes() == FIXTURE.read_bytes()
    assert not (stage / "old.bundle.json").exists(), "a stale asset would be uploaded"
    bundles, found = build.release_inputs(stage)
    assert bundles == [stage / "zz.bundle.json"] and found == stage / "data-summary.json"


def test_the_page_builds_from_a_staged_release(tmp_path):
    stage = tmp_path / "stage"
    build.stage_release(stage, results_dir=_results_dir(tmp_path), data_summary=None)
    bundles, summary = build.release_inputs(stage)
    assert summary is None
    page = build.build_app(bundles, out_dir=tmp_path / "site", data_summary=summary)
    assert [s["meta"]["state"] for s in _embedded(page.read_text(encoding="utf-8"))["states"]] == ["ZZ"]
    assert _state_file(tmp_path / "site", "ZZ") == json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_nothing_is_staged_without_a_bundle(tmp_path):
    with pytest.raises(FileNotFoundError):
        build.stage_release(tmp_path / "stage", results_dir=tmp_path, data_summary=None)
    with pytest.raises(FileNotFoundError):
        build.release_inputs(tmp_path)


def test_pages_workflow_builds_from_what_publish_app_uploads():
    from fnmatch import fnmatch

    wf = (REPO / ".github" / "workflows" / "pages.yml").read_text(encoding="utf-8")
    pattern = re.search(r"--pattern '([^']+)'", wf).group(1)
    for name in (build.BUNDLE_ASSET.format(state="mn"), build.SUMMARY_ASSET):
        assert fnmatch(name, pattern), f"the workflow would not download {name}"
    assert "--dir release" in wf and "build_app.py --from-release release --out site" in wf
    assert "path: site" in wf and "actions/deploy-pages@" in wf
    # the page must be built with the code that made the results
    assert "ref: refs/tags/${{ inputs.tag }}" in wf
    assert 'WORKFLOW = "pages.yml"' in (REPO / "scripts" / "publish_app.py").read_text(encoding="utf-8")
