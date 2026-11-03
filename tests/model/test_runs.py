"""Run folders as data (`model/runs.py`) and the results dashboard (`model/dashboard.py`), on small synthetic
run folders shaped like a D-024 run (`estimate_mm.write`) and a D-025 run (`estimate_pooled_adu.stages`)."""

from __future__ import annotations

import json
import re

import pandas as pd
import pytest
import yaml

from lotline.model import dashboard, runs


def _write(folder, **tables):
    folder.mkdir(parents=True, exist_ok=True)
    for name, rows in tables.items():
        pd.DataFrame(rows).to_csv(folder / f"{name}.csv", index=False)
    return folder


@pytest.fixture
def mm_run(tmp_path):
    """A D-024-shaped run: terms beta_0 and att, robustness.csv, transport with a total row."""
    return _write(
        tmp_path / "mm-run",
        estimates=[
            {"term": "beta_0", "estimate": 0.5, "low": 0.1, "high": 0.9},
            {"term": "att", "estimate": 1.0, "low": 0.2, "high": 1.8},
            {"term": "intercept_like", "estimate": 9.0, "low": 8.0, "high": 10.0},
        ],
        checks=[
            {"check": "pre-trend leads", "statistic": 1.0, "p": 0.8, "pass": True},
            {"check": "placebo outcome", "estimate": 1.7, "low": 0.8, "high": 4.6, "pass": False},
            {"check": "excluding 2020-21", "estimate_att": 1.1, "pass": True},
            {"check": "local measurement (reported)", "note": "ratio 1.00"},
        ],
        robustness=[
            {"fit": "main (nb)", "term": "att", "estimate": 1.0, "low": 0.2, "high": 1.8},
            {"fit": "re", "term": "att", "estimate": 2.1, "low": 1.4, "high": 3.1},
            {"fit": "re", "term": "beta_0", "estimate": 9.0, "low": 9.0, "high": 9.0},
        ],
        randomization=[
            {"att_permuted": v, "att": 1.0, "p": 0.3, "failed": 0, "reliable": True} for v in (0.1, 1.2)
        ],
        bootstrap_draws=[{"beta_0": 0.4, "att": 0.9}, {"beta_0": 0.6, "att": 1.1}],
        leave_one_out=[
            {"left_out": "4824000", "att": 1.2},
            {"left_out": "Durham city and county", "att": 0.9},
        ],
        transport=[
            {
                "place": "3719000",
                "name": "Durham city",
                "year": "2024",
                "observed": 38,
                "mean": 50.8,
                "p10": 5,
                "p90": 119,
                "test": "A",
            },
            {
                "place": "3719000",
                "name": "Durham city",
                "year": "total",
                "observed": 279,
                "mean": 146,
                "p10": 40,
                "p90": 293,
                "test": "A",
            },
        ],
        transport_verdict=[
            {"test": "A", "totals_inside_80": True, "yearly_coverage_80": 0.69, "pass": False}
        ],
        added_homes=[
            {
                "place": "4824000",
                "name": "El Paso city",
                "years": 16,
                "added": 3006,
                "low": -2256,
                "high": 5122,
                "per_1000_parcels_year": 1.0,
            }
        ],
    )


@pytest.fixture
def adu_run(tmp_path):
    """A D-025-shaped run: `overall`, robust_*.csv files, sensitivity.csv, no `test` column in transport."""
    return _write(
        tmp_path / "adu-run",
        estimates=[
            {"term": "beta_0_1", "estimate": 2.4, "low": 0.6, "high": 4.0},
            {"term": "overall", "estimate": 2.37, "low": 0.12, "high": 4.51},
            {"term": "log_sigma", "estimate": 0.8, "low": 0.4, "high": 1.2},
        ],
        checks=[
            {
                "check": "placebo dates (−2 years)",
                "pass": None,
                "convergence": "0 of 1 refits converged",
                "note": "not computed",
            }
        ],
        randomization=[{"overall_permuted": 0.07, "overall": 2.37, "p": 0.11, "kept": 970}],
        robust_binary_dose=[{"term": "overall", "estimate": 1.57, "se": 0.7, "low": 0.41, "high": 2.71}],
        robust_fe_ppml=[{"estimated": True, "beta_0_1": -0.2}],
        sensitivity=[
            {"check": "T at the announcement year (C29)", "estimate": 2.99, "low": 1.13, "high": 4.98}
        ],
        leave_one_out=[{"place": "2701486", "overall_without": 2.46}],
        transport=[
            {
                "place": "4805000",
                "name": "Austin city",
                "year": "total",
                "observed": 2500,
                "mean": 60,
                "p10": 0,
                "p90": 200,
            }
        ],
        transport_verdict=[{"totals_inside_80": False, "yearly_coverage_80": 0.15, "pass": False}],
    )


def test_mm_run_terms_and_overall(mm_run):
    r = runs.load_run(mm_run)
    assert r["status"] == "completed" and r["id"] == "mm-run"  # no manifest: estimates mean it finished
    assert r["overall"] == {
        "term": "att",
        "label": "Overall effect",
        "estimate": 1.0,
        "low": 0.2,
        "high": 1.8,
    }
    assert [t["label"] for t in r["terms"]] == ["Years 0-1", "Overall effect"]  # unknown terms left out


def test_mm_run_checks_read_estimates_tests_and_notes(mm_run):
    c = {x["name"]: x for x in runs.load_run(mm_run)["checks"]}
    assert c["pre-trend leads"]["pass"] is True and c["pre-trend leads"]["p"] == 0.8
    assert c["pre-trend leads"]["estimate"] is None
    assert c["placebo outcome"]["pass"] is False and c["placebo outcome"]["low"] == 0.8
    assert c["excluding 2020-21"]["estimate"] == 1.1  # estimate_att when there is no `estimate`
    local = c["local measurement (reported)"]
    assert local["pass"] is None and local["note"] == "ratio 1.00"


def test_mm_run_robustness_overall_only_with_common_labels(mm_run):
    rob = runs.load_run(mm_run)["robustness"]
    assert [(x["fit"], x["estimate"]) for x in rob] == [
        ("Main: negative binomial", 1.0),
        ("Poisson-gamma", 2.1),
    ]


def test_mm_run_draws_names_and_transport(mm_run):
    r = runs.load_run(mm_run)
    assert r["randomization"] == {"observed": 1.0, "p": 0.3, "draws": [0.1, 1.2], "failed": 0}
    assert r["bootstrap"] == [0.9, 1.1]  # the overall effect's draws
    # place codes become names where the run names them; other labels pass through
    assert [x["left_out"] for x in r["leave_one_out"]] == ["El Paso city", "Durham city and county"]
    assert [t["year"] for t in r["transport"]] == ["2024", "total"]  # "total" survives as text
    assert r["transport"][1]["p90"] == 293
    assert r["transport_verdict"] == [{"test": "A", "pass": False, "coverage": 0.69}]
    assert r["added_homes"][0]["name"] == "El Paso city" and r["added_homes"][0]["added"] == 3006


def test_adu_run_reads_the_other_layout(adu_run):
    r = runs.load_run(adu_run)
    assert r["overall"]["term"] == "overall" and r["overall"]["estimate"] == 2.37
    assert "log_sigma" not in [t["term"] for t in r["terms"]]
    assert r["randomization"]["p"] == 0.11 and r["randomization"]["failed"] is None
    rob = {x["fit"]: x["estimate"] for x in r["robustness"]}
    # robust_fe_ppml has no overall term, so it is not a robustness line
    assert rob == {"Binary by-right dose": 1.57, "T at the announcement year (C29)": 2.99}
    assert r["checks"][0]["pass"] is None and "0 of 1 refits" in r["checks"][0]["note"]
    assert r["leave_one_out"] == [{"left_out": "2701486", "estimate": 2.46}]
    assert r["transport"][0]["test"] == r["transport_verdict"][0]["test"] == "Transport test"
    assert r["added_homes"] == [] and r["bootstrap"] == []


def test_run_without_estimates_loads_its_manifest_only(tmp_path):
    folder = tmp_path / "failed"
    folder.mkdir()
    (folder / "run.yaml").write_text(yaml.safe_dump({"model": "D-025", "status": "no_estimate"}))
    (folder / "transport.csv").write_text("")  # an empty file a stage left behind is not an error
    r = runs.load_run(folder)
    assert r["status"] == "no_estimate" and r["overall"] is None and r["randomization"] is None
    assert r["terms"] == r["checks"] == r["robustness"] == r["transport"] == []
    json.dumps(r, allow_nan=False)


def test_manifest_start_and_finish(tmp_path):
    folder = tmp_path / "run-a"
    runs.start_manifest(
        folder, model="D-024", title="t", plan_entry="D-024 x", scope={"places": 2}, config={"seed": 1}
    )
    m = runs.read_manifest(folder)
    assert m["id"] == "run-a" and m["status"] == "started" and m["method"] == runs.METHODS["D-024"]
    assert m["scope"] == {"places": 2} and m["config"] == {"seed": 1} and "finished" not in m
    assert runs.load_run(folder)["status"] == "started"  # stopped before writing any estimate
    runs.finish_manifest(folder, "no_estimate", "BFGS did not converge")
    m = runs.read_manifest(folder)
    assert m["status"] == "no_estimate" and m["status_note"] == "BFGS did not converge" and m["finished"]
    with pytest.raises(ValueError):
        runs.finish_manifest(folder, "done")
    with pytest.raises(ValueError):
        runs.start_manifest(folder, model="D-099", title="", plan_entry="", scope={}, config={})


def test_started_run_with_estimates_counts_as_completed(mm_run):
    runs.start_manifest(mm_run, model="D-024", title="t", plan_entry="", scope={}, config={})
    assert runs.load_run(mm_run)["status"] == "completed"


def test_panel_scope_hand_example():
    panel = pd.DataFrame(
        {
            "place": ["1"] * 3 + ["2"] * 3,
            "state": ["MN"] * 3 + ["TX"] * 3,
            "year": [2016, 2017, 2018] * 2,
            "T": [2018.0] * 3 + [float("nan")] * 3,
            "y": [0, 1, None, 2, 0, 0],
        }
    )
    s = runs.panel_scope(panel, "ADUs", holdouts="none")
    assert s == {
        "states": ["MN", "TX"],
        "years": "2016-2018",
        "outcome": "ADUs",
        "places": 2,
        "place_years": 5,
        "treated": 1,
        "adopting_in_window": 1,
        "places_by_state": {"MN": 1, "TX": 1},
        "holdouts": "none",
    }


def test_find_runs_orders_by_start(tmp_path):
    for name, started in (("b", "2026-11-02T19:00"), ("a", "2026-10-20T20:00"), ("c", "2026-11-03T01:00")):
        (tmp_path / "reports" / name).mkdir(parents=True)
        (tmp_path / "reports" / name / "run.yaml").write_text(yaml.safe_dump({"started": started}))
    (tmp_path / "reports" / "no-manifest").mkdir()
    assert [f.name for f in runs.find_runs(tmp_path / "reports")] == ["a", "b", "c"]


def _embedded(page: str) -> list:
    m = re.search(r'<script id="runs-data" type="application/json">(.*?)</script>', page, re.S)
    return json.loads(m.group(1))


def test_render_embeds_the_runs(mm_run, adu_run):
    loaded = [runs.load_run(mm_run), runs.load_run(adu_run)]
    page = dashboard.render(loaded, generated="2026-11-03")
    assert _embedded(page) == loaded
    assert "Generated 2026-11-03" in page and "__RUNS_JSON__" not in page


def test_render_escapes_script_end_in_text(mm_run):
    run = runs.load_run(mm_run)
    run["manifest"]["reading"] = "x</script><script>alert(1)</script>"
    page = dashboard.render([run], generated="now")
    assert page.count("</script>") == 2  # the data block's and the code block's own
    assert _embedded(page)[0]["manifest"]["reading"] == run["manifest"]["reading"]


def test_render_refuses_bad_input(mm_run):
    run = runs.load_run(mm_run)
    with pytest.raises(ValueError):
        dashboard.render([])
    with pytest.raises(ValueError):
        dashboard.render([run, run])
    with pytest.raises(ValueError):
        dashboard.render([{**run, "id": "x", "overall": {"estimate": float("nan")}}])
