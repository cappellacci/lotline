"""Human lookup tasks, the worklist, and the CLI end to end on a temporary data directory."""

import json

import pandas as pd
import pytest

from lotline.rule_agents.adu import cli
from lotline.rule_agents.adu import coding as C
from lotline.rule_agents.adu import handoff as H
from lotline.rule_agents.adu import places as P
from lotline.rule_agents.common.docstore import DocStore

from .fixtures import coding, era_2020, none_era


def task(**kw):
    base = dict(
        state="NC",
        geoid="3799999",
        place="Testville",
        question="When were ADUs first allowed?",
        blocker="http_403_waf",
        url="https://example.gov/code",
        what_to_look_for="Ordinance adopting Sec. 5.3",
        fields_to_fill=["adoption_date", "effective_date"],
        pop_2020=1000,
    )
    return H.HumanTask(**(base | kw))


def test_task_id_is_stable_and_reason_and_fields_are_checked():
    assert task().task_id == task().task_id and task().task_id.startswith("ADU-NC-3799999-")
    with pytest.raises(ValueError):
        task(blocker="because")
    with pytest.raises(ValueError):
        task(fields_to_fill=["colour"])


def test_all_is_shorthand_for_every_field():
    assert task(fields_to_fill=["all"]).fields_to_fill == list(H.ALLOWED)


def test_triage_ranks_by_priority_then_population_and_keeps_records_requests_as_optional():
    big = task(geoid="3700001", place="Bigtown", pop_2020=50000)
    rr = task(geoid="3700002", place="Recordsville", notes="records_request_only: ordinance not online")
    same_page = task(fields_to_fill=["adu_max_sqft"], era_id="2020")
    sizes = task(geoid="3700003", place="Sizeton", pop_2020=90000, fields_to_fill=["adu_max_sqft"])
    rr2 = task(geoid="3700004", place="Clerkburg", blocker="records_request_only", pop_2020=99000)
    queue, closed = H.triage([task(), big, task(), rr, same_page, sizes, rr2])
    merged = next(t for t in queue if t.place == "Testville")
    assert merged.fields_to_fill == ["adoption_date", "effective_date", "adu_max_sqft"]
    assert [t.place for t in queue] == ["Bigtown", "Testville", "Sizeton", "Clerkburg", "Recordsville"]
    assert [t.priority for t in queue] == [1, 1, 2, 3, 3]
    assert [t.optional for t in queue] == [False, False, False, True, True]
    assert closed == []


def test_written_tasks_have_plain_instructions(tmp_path):
    queue, _ = H.triage([task()])
    H.write_csv(queue, tmp_path / "t.csv")
    H.write_markdown(queue, tmp_path / "t.md", "Lookups")
    row = H.read_csv(tmp_path / "t.csv")[0]
    assert list(row) == H.COLUMNS
    assert "HTTP 403" in row["why_agent_stopped"] and "YYYY-MM-DD" in row["allowed_values"]
    md = (tmp_path / "t.md").read_text()
    assert "- [ ] **Open:** https://example.gov/code" in md and "Done when" in md


def test_answers_need_url_and_quote_to_be_accepted(tmp_path):
    row = task().row() | {"result": "found", "answers": "adoption_date=2020-07-07; effective_date=2020-07-22"}
    _, ev, probs = H.answered(row)
    assert ev is None and any("quote" in p for p in probs) and any("source_url" in p for p in probs)
    row |= {
        "source_url": "https://example.gov/ord.pdf",
        "quote": "This ordinance takes effect July 22, 2020.",
        "checked_on": "2026-11-18",
    }
    ans, ev, probs = H.answered(row)
    assert probs == [] and ans["effective_date"] == "2020-07-22"
    assert (ev.source_kind, ev.quote_status, ev.doc_id) == ("human_lookup", "human", None)
    _, _, probs = H.answered(row | {"answers": "effective_date=2020-07-22"})
    assert any("not answered" in p for p in probs)
    assert H.answered(row | {"result": "maybe"})[2]  # not one of the shared results
    assert H.answered(task().row())[1:] == (None, [])  # not answered yet


def test_saved_file_is_registered_in_the_store_and_cited(tmp_path):
    docs = DocStore(tmp_path)
    docs.inbox.mkdir(parents=True, exist_ok=True)
    (docs.inbox / "ord.txt").write_text("This ordinance takes effect July 22, 2020.")
    row = task().row() | {
        "result": "found",
        "answers": "adoption_date=2020-07-07; effective_date=2020-07-22",
        "source_url": "https://example.gov/ord.pdf",
        "quote": "This ordinance takes effect July 22, 2020.",
        "saved_file": "ord.txt",
        "checked_by": "Tester",
        "checked_on": "2026-11-18",
    }
    _, ev, probs = H.answered(row, docs)
    assert probs == [] and ev.doc_id and docs.get(ev.doc_id) is not None


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


def test_tasks_skip_fields_the_final_coding_settled_on_primary_evidence():
    final = coding()  # every era has adus_per_lot on official code
    assert cli.settled_fields_dropped(["adus_per_lot", "adu_max_sqft"], final) == ["adu_max_sqft"]
    assert cli.settled_fields_dropped(["adus_per_lot"], None) == ["adus_per_lot"]


def test_cli_end_to_end(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LOTLINE_DATA_DIR", str(tmp_path))
    d = cli.run_dir("NC", "t1")
    a = coding()
    a.blocked = [
        C.Blocker(
            url="https://library.municode.com/nc/testville",
            kind="code_host_wall",
            era_id="none",
            fields=["adoption_date"],
            look_for="Ordinance that first listed ADUs. Check history notes.",
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
        H.WHY["code_host_wall"][:20],
        H.WHY["conflicting_sources"][:20],
    }
    assert "Testville" in (d / "tasks.md").read_text()
    capsys.readouterr()


def test_optional_task_is_marked_in_sheet_and_checklist(tmp_path):
    queue, _ = H.triage([task(blocker="records_request_only")])
    H.write_csv(queue, tmp_path / "t.csv")
    H.write_markdown(queue, tmp_path / "t.md", "Lookups")
    row = H.read_csv(tmp_path / "t.csv")[0]
    assert (row["optional"], row["priority"]) == ("yes", "3")
    assert row["what_to_do"].startswith("Optional: this record is only available by public-records request.")
    assert "· priority 3 · optional" in (tmp_path / "t.md").read_text()


def test_a_blocker_for_an_uncoded_period_keeps_every_field():
    """South Burlington VT: only the 2022 era was coded. A blocker for the rule before 2022 must keep all its
    fields (the 2022 values say nothing about earlier years); one for the 2022 era drops what 2022 settled."""
    final = coding()  # every era has adus_per_lot on official code
    first = final.eras[0].era_id
    asked = ["adus_per_lot", "by_right", "adu_max_sqft"]
    assert cli.settled_fields_dropped(asked, final, "before-2016") == asked
    assert "adus_per_lot" not in cli.settled_fields_dropped(asked, final, first)
    assert "adus_per_lot" not in cli.settled_fields_dropped(asked, final)  # no era: about every coded era
