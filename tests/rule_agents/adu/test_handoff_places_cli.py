"""Human lookup tasks, the worklist, and the CLI end to end on a temporary data directory."""

import json

import pandas as pd
import pytest

from lotline.rule_agents.adu import cli
from lotline.rule_agents.adu import coding as C
from lotline.rule_agents.adu import handoff as H
from lotline.rule_agents.adu import places as P

from .fixtures import coding, era_2020, none_era


def task(**kw):
    base = dict(
        state="NC",
        geoid="3799999",
        place="Testville",
        question="When were ADUs first allowed?",
        reason="http_403",
        url="https://example.gov/code",
        what_to_look_for="Ordinance adopting Sec. 5.3",
        fields_to_fill=["adoption_date", "effective_date"],
        pop_2020=1000,
    )
    return H.HumanTask(**(base | kw))


def test_task_id_is_stable_and_reason_and_fields_are_checked():
    assert task().task_id == task().task_id and task().task_id.startswith("ADU-NC-3799999-")
    with pytest.raises(ValueError):
        task(reason="because")
    with pytest.raises(ValueError):
        task(fields_to_fill=["colour"])


def test_triage_ranks_by_population_dedupes_and_closes_records_request_only():
    big = task(geoid="3700001", place="Bigtown", pop_2020=50000)
    rr = task(geoid="3700002", place="Recordsville", notes="records_request_only: ordinance not online")
    queue, closed = H.triage([task(), big, task(), rr])
    assert [t.place for t in queue] == ["Bigtown", "Testville"] and [t.priority for t in queue] == [1, 2]
    assert [t.status for t in closed] == ["no_usable_source"]


def test_written_tasks_have_plain_instructions(tmp_path):
    queue, _ = H.triage([task()])
    H.write_csv(queue, tmp_path / "t.csv")
    H.write_markdown(queue, tmp_path / "t.md", "Lookups")
    row = H.read_csv(tmp_path / "t.csv")[0]
    assert list(row) == H.COLUMNS
    assert "HTTP 403" in row["why_agent_stopped"] and "YYYY-MM-DD" in row["allowed_values"]
    md = (tmp_path / "t.md").read_text()
    assert "- [ ] **Open:** https://example.gov/code" in md and "Done when" in md


def test_answers_need_url_and_quote_to_be_accepted():
    row = task().row() | {"status": "done", "answers": "adoption_date=2020-07-07; effective_date=2020-07-22"}
    _, ev, probs = H.answered(row)
    assert ev is None and any("answer_url" in p for p in probs) and any("answer_quote" in p for p in probs)
    row |= {
        "answer_url": "https://example.gov/ord.pdf",
        "answer_quote": "This ordinance takes effect July 22, 2020.",
    }
    ans, ev, probs = H.answered(row)
    assert probs == [] and ans["effective_date"] == "2020-07-22" and ev.kind == "human_primary"
    _, _, probs = H.answered(row | {"answers": "effective_date=2020-07-22"})
    assert any("not answered" in p for p in probs)


def test_worklist_is_largest_first_with_existing_rows():
    j = pd.DataFrame(
        {
            "geoid": ["3700001", "3700002", "37001", "3700003"],
            "name": ["A", "B", "Co", "C"],
            "kind": ["place", "place", "county", "place"],
            "county_geoid": None,
            "pop_2020": [3000, 90000, 500000, 1000],
        }
    )
    existing = pd.DataFrame(
        {"reform_id": ["NC-3700002-adu-2019"], "jurisdiction_geoid": ["3700002"], "theme": ["adu"]}
    )
    wl = P.worklist(j, existing, min_pop=2500)
    assert list(wl["name"]) == ["B", "A"] and list(wl["existing_adu_rows"]) == ["NC-3700002-adu-2019", ""]


def test_state_law_threshold_is_strict_and_flags_near_threshold():
    p = pd.DataFrame({"geoid": ["1", "2", "3"], "kind": "place", "pop_2020": [2500, 2501, 10000]})
    cov = P.covered_by_state_law(p, 2500)
    assert list(cov["covered"]) == [False, True, True] and list(cov["near_threshold"]) == [True, True, False]


def test_cli_end_to_end(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LOTLINE_DATA_DIR", str(tmp_path))
    d = cli.run_dir("NC", "t1")
    a = coding()
    a.blocked = [
        C.BlockedSource(
            url="https://library.municode.com/nc/testville",
            reason="js_only_viewer",
            era_id="none",
            fields=["adoption_date"],
            what_to_look_for="Ordinance that first listed ADUs. Check history notes.",
        )
    ]
    b = coding(coder="blind", eras=[none_era(), era_2020(sqft=1000)])
    C.dump(a, d / "coding_a" / "3799999.json")
    C.dump(b, d / "coding_b" / "3799999.json")
    assert (
        cli.main(["check", str(d / "coding_a" / "3799999.json"), str(d / "coding_b" / "3799999.json")]) == 0
    )
    cli.main(
        [
            "merge",
            str(d / "coding_a/3799999.json"),
            str(d / "coding_b/3799999.json"),
            "--out",
            str(d / "final/3799999.json"),
        ]
    )
    meta = json.loads((d / "final" / "3799999.meta").read_text())
    assert meta["agreement"] == "single_coder" and meta["unresolved"][0]["field"] == "adu_max_sqft"
    assert cli.main(["rows", str(d / "final" / "3799999.json"), "--out", str(d / "rows.csv")]) == 0
    rows = pd.read_csv(d / "rows.csv")
    assert len(rows) == 2 and rows["adu_max_sqft"].isna().all()
    assert cli.main(["tasks", str(d)]) == 0
    tasks = pd.read_csv(d / "tasks.csv")
    assert set(tasks["why_agent_stopped"].str[:20]) == {
        H.REASONS["js_only_viewer"][0][:20],
        H.REASONS["conflicting_sources"][0][:20],
    }
    assert "Testville" in (d / "tasks.md").read_text()
    capsys.readouterr()
