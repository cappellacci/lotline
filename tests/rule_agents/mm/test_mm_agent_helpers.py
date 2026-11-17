"""Tests for the MM rule agent swarm helpers (src/lotline/rule_agents/mm), on small synthetic fixtures.

Each test is a hand-worked example from the helper's docstring or docs/build/rule-agents/mm/DESIGN.md.
"""

from __future__ import annotations

import json
from datetime import date

import pandas as pd
import pytest
from pydantic import ValidationError

from lotline.model import rule_tags
from lotline.rule_agents.mm import __main__ as cli
from lotline.rule_agents.mm import access, compare, dates, handoff, reconcile, rows
from lotline.rule_agents.mm.fetch import allowed, snapshot_name
from lotline.rule_agents.mm.findings import (
    Blocker,
    Evidence,
    PlaceFinding,
    RuleFinding,
    check,
    draft_markers,
    verify_quote,
)
from lotline.rule_agents.mm.places import enumerate_places

TODAY = date(2026, 11, 17)
URL = "https://example.gov/ord-2019-048.pdf"


def ev(field, quote="Up to three dwelling units are permitted on a zoning lot.", url=URL):
    return Evidence(field=field, url=url, quote=quote, retrieved=TODAY, section="Ord. 2019-048 s.3")


def rule(**kw):
    base = dict(
        component="Ord. 2019-048: up to 3 units in R1-R2B",
        adoption_date=date(2019, 11, 8),
        effective_date=date(2020, 1, 1),
        date_basis="dated",
        unit_cap=3,
        by_right=True,
        coverage="Citywide R1, R1A, R2, R2B",
        coverage_zones=["R1", "R1A", "R2", "R2B"],
        prior_cap=1,
        evidence=[
            ev("effective_date"),
            ev("unit_cap"),
            ev("by_right"),
            ev("coverage_zones"),
            ev("prior_cap", "R1 One-family dwelling P; Two-family dwelling --", "https://web.archive.org/x"),
        ],
    )
    base.update(kw)
    return RuleFinding(**base)


def place(rules=None, blockers=None, coder="rules-mm-coder-a", geoid="2799999"):
    return PlaceFinding(
        state="MN",
        jurisdiction_geoid=geoid,
        place="Testville",
        coder=coder,
        coded_on=TODAY,
        rules=rules if rules is not None else [rule()],
        blockers=blockers or [],
    )


# ---- dates -----------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text, expect",
    [
        ("adopted November 8, 2019", date(2019, 11, 8)),
        ("Ord. 2019-048, eff. 1/1/20", date(2020, 1, 1)),
        ("passed 2019-11-08 and published", date(2019, 11, 8)),
        ("on 8 Nov 2019 the council", date(2019, 11, 8)),
        ("Sept. 3, 2019", date(2019, 9, 3)),
        ("6/3/98", date(1998, 6, 3)),
    ],
)
def test_parse_date_day(text, expect):
    assert dates.parse_date(text) == (expect, "day")


def test_parse_date_coarse_needs_permission():
    with pytest.raises(dates.DateParseError):
        dates.parse_date("in March 2021")
    assert dates.parse_date("in March 2021", precision="month") == (date(2021, 3, 1), "month")
    assert dates.parse_date("the 2021 code", precision="year") == (date(2021, 1, 1), "year")


def test_tags_match_engine_reader():
    """The tags we write are the ones rule_tags.flags reads."""
    notes = " ".join(dates.tags_for("predates") + dates.tags_for("earliest_known", standards_only=True))
    df = pd.DataFrame(
        {
            "theme": ["missing_middle"],
            "status": ["in_force"],
            "coding_notes": [notes],
            "adoption_date": [pd.Timestamp("2019-11-08")],
            "effective_date": [pd.Timestamp("2020-01-01")],
            "unit_cap": [3],
        }
    )
    f = rule_tags.flags(df).iloc[0]
    assert f["predates"] and f["earliest_known"] and f["standards"] and not f["event"]
    assert dates.tags_for("unconfirmed") == [rule_tags.UNCONFIRMED]


def test_basis_from_notes():
    assert dates.basis_from_notes("x [predates] y", "2019-01-01") == "predates"
    assert dates.basis_from_notes("", None) == "earliest_known"
    assert dates.basis_from_notes("DATE UNCONFIRMED", "2019-01-01") == "unconfirmed"
    assert dates.basis_from_notes("ok", "2019-01-01") == "dated"


# ---- findings ----------------------------------------------------------------------------------------------


def test_clean_finding_passes():
    assert check(place(), today=TODAY) == []


def test_missing_evidence_flagged():
    r = rule(evidence=[ev("effective_date")])
    msgs = check(place([r]), today=TODAY)
    assert "rule 0 (2020-01-01): unit_cap has no evidence" in msgs
    assert any("by_right has no evidence" in m for m in msgs)


def test_date_rules():
    coarse = rule(date_precision="month")
    assert any("must be earliest_known" in m for m in check(place([coarse]), today=TODAY))
    no_adopt = rule(adoption_date=None)
    assert any("needs an adoption_date" in m for m in check(place([no_adopt]), today=TODAY))
    backwards = rule(adoption_date=date(2020, 2, 1))
    assert any("before adoption_date" in m for m in check(place([backwards]), today=TODAY))
    future = rule(adoption_date=date(2026, 10, 1), effective_date=date(2027, 1, 1))
    assert any("status should be 'pending'" in m for m in check(place([future]), today=TODAY))


def test_none_row_and_standards_rules():
    none_ok = rule(
        unit_cap=1,
        by_right=None,
        prior_cap=None,
        evidence=[ev("effective_date"), ev("unit_cap"), ev("coverage_zones")],
    )
    assert check(place([none_ok]), today=TODAY) == []
    bad = rule(unit_cap=1, standards_only=True)
    assert any("cannot be standards_only" in m for m in check(place([bad]), today=TODAY))
    std = rule(unit_cap=None, standards_only=True)  # Houston-style MUR route: no cap change
    assert not any("unit_cap blank" in m for m in check(place([std]), today=TODAY))
    assert any("unit_cap blank" in m for m in check(place([rule(unit_cap=None)]), today=TODAY))


def test_prior_cap_check():
    """An event must show what the code allowed just before; an equal cap is a recodification."""
    nopr = rule(
        prior_cap=None, evidence=[ev("effective_date"), ev("unit_cap"), ev("by_right"), ev("coverage_zones")]
    )
    assert any("no prior_cap" in m for m in check(place([nopr]), today=TODAY))
    blocked = Blocker(url="https://web.archive.org/x", kind="not_found", fields=["prior_cap"])
    assert check(place([nopr], [blocked]), today=TODAY) == []  # handed off: allowed (St. Louis Park)
    recod = rule(prior_cap=3)
    assert any("no cap rise" in m for m in check(place([recod]), today=TODAY))
    pre = rule(
        prior_cap=None,
        date_basis="predates",
        evidence=[ev("effective_date"), ev("unit_cap"), ev("by_right"), ev("coverage_zones")],
    )
    assert check(place([pre]), today=TODAY) == []


def test_lead_only_and_mirror_sources():
    news = ev("unit_cap")
    news = news.model_copy(update={"source_kind": "news"})
    r = rule(evidence=[e for e in rule().evidence if e.field != "unit_cap"] + [news])
    assert any("a lead, not evidence" in m for m in check(place([r]), today=TODAY))
    mir = ev("unit_cap").model_copy(update={"source_kind": "mirror"})
    r2 = rule(confidence="high", evidence=[e for e in rule().evidence if e.field != "unit_cap"] + [mir])
    assert any("mirror only" in m for m in check(place([r2]), today=TODAY))
    df = rows.table(rows.place_rows(place([r2]), coder_2=None, agreement="single_coder"))
    assert "FLAG for second coder: unit_cap read on a mirror only." in df.loc[0, "coding_notes"]
    assert "Prior cap (code just before): 1." in df.loc[0, "coding_notes"]


def test_tags_in_notes_rejected():
    r = rule(notes="second coder says tag [predates]")
    assert any("engine tag" in m for m in check(place([r]), today=TODAY))


def test_verify_quote_across_markup():
    html = "<html><body><p>Effective <b>January&nbsp;1, 2020</b>, up to three units</p></body></html>"
    assert verify_quote("Effective January 1, 2020, up to three units", html)


def test_draft_markers():
    assert draft_markers("ORDINANCE NO. XXX-XX ... effective on [insert effective date]")
    assert draft_markers("Ordinance No. 2690-25, adopted March 3, 2025. Signed: Mayor") == []


def test_place_with_nothing_is_flagged_but_blocker_suffices():
    assert any("no rules and no blockers" in m for m in check(place([]), today=TODAY))
    b = Blocker(url="https://library.municode.com/x", kind="code_host_wall", fields=["unit_cap"])
    assert check(place([], [b]), today=TODAY) == []
    b2 = Blocker(url="https://x.gov/y", kind="http_403_waf")
    assert any("name the field" in m for m in check(place([], [b2]), today=TODAY))


def test_evidence_validation():
    with pytest.raises(ValidationError):
        Evidence(field="unit_cap", url="ftp://x", quote="q", retrieved=TODAY)
    with pytest.raises(ValidationError):
        Evidence(field="unit_cap", url=URL, quote="x" * 301, retrieved=TODAY)


def test_verify_quote():
    text = "Sec. 3.  Up to  three\ndwelling units are permitted on a zoning lot in the R1 district."
    assert verify_quote("up to three dwelling units are permitted", text)
    assert verify_quote("Up to three ... in the R1 district", text)
    assert not verify_quote("up to four dwelling units", text)
    assert not verify_quote("in the R1 district ... Up to three", text)  # order matters
    assert verify_quote("“Up to three”", 'the text says "up to three" units')


# ---- access ------------------------------------------------------------------------------------------------


def test_robots():
    txt = "User-agent: *\nDisallow: /search\n\nUser-agent: ClaudeBot\nDisallow: /\n"
    assert access.robots_allows(txt, "https://x.gov/code", "lotline")
    assert not access.robots_allows(txt, "https://x.gov/search/q", "lotline")
    assert not allowed(txt, "https://x.gov/code")  # ClaudeBot is blocked: a block for one is a block
    assert allowed(None, "https://x.gov/anything")


def test_classify():
    assert (
        access.classify("https://x.gov/a", 403, text="<title>Just a moment...</title>")[0] == "http_403_waf"
    )
    assert access.classify("https://library.municode.com/nc/x", 403)[0] == "code_host_wall"
    shell = "<html><noscript>Please enable JavaScript</noscript><div id=app></div></html>"
    assert access.classify("https://library.municode.com/nc/x", 200, text=shell)[0] == "code_host_wall"
    assert access.classify("https://x.gov/a", 200, text=shell)[0] == "js_only"
    assert (
        access.classify(URL, 200, content_type="application/pdf", pdf_text_chars=300, pdf_pages=12)[0]
        == "scanned_pdf"
    )
    assert (
        access.classify(URL, 200, content_type="application/pdf", pdf_text_chars=30000, pdf_pages=12) is None
    )
    assert access.classify("https://x.gov/a", 404)[0] == "not_found"
    body = "<p>" + "Sec. 20.3 Two-family dwellings are permitted. " * 100 + "</p>"
    assert access.classify("https://x.gov/a", 200, text=body) is None
    login = '<form><input type="password" name="pw"></form>'
    assert access.classify("https://x.gov/a", 200, text=login)[0] == "login_required"


def test_classify_ignores_challenge_words_in_scripts():
    """St. Louis Park dry run: a long <head> with an Akamai script, then a real page -> usable."""
    page = (
        "<html><head><title>Zoning Code Update</title>"
        + "<script>/* akamai bot manager */ var x = 1;</script>" * 600
        + "</head><body>"
        + "<p>The city council adopted the zoning code update on March 3, 2025.</p>" * 60
        + "</body></html>"
    )
    assert len(page) > 20000
    assert access.classify("https://www.stlouisparkmn.gov/zoning", 200, text=page) is None
    wall = "<html><head><title>Just a moment...</title></head><body>Checking your browser</body></html>"
    assert access.classify("https://x.gov/a", 200, text=wall)[0] == "http_403_waf"


def test_snapshot_name_is_stable():
    assert snapshot_name(URL) == snapshot_name(URL)
    assert snapshot_name(URL).startswith("example.gov/") and snapshot_name(URL).endswith(".pdf")
    assert snapshot_name("https://x.gov/code?id=1").endswith(".html")


# ---- handoff -----------------------------------------------------------------------------------------------


def test_tasks_dedupe_priority_and_records_requests():
    b1 = Blocker(url="https://library.municode.com/mn/t", kind="code_host_wall", fields=["effective_date"])
    b2 = Blocker(url="https://library.municode.com/mn/t", kind="code_host_wall", fields=["coverage_zones"])
    b3 = Blocker(url="https://x.gov/zoning", kind="http_403_waf", fields=["by_right"])
    b4 = Blocker(url="https://x.gov/records", kind="records_request_only")
    fa = place([], [b1, b3, b4])
    fb = place([], [b2], coder="rules-mm-coder-b")
    ts = handoff.tasks([fa, fb], {"2799999": 5000})
    assert len(ts) == 2  # municode deduped across coders; the records request is not a task
    first = ts[0]
    assert first["priority"] == 1 and "municode" in first["start_url"]
    assert set(first["fields_to_fill"].split(";")) >= {"effective_date", "districts", "result", "quote"}
    assert "Versions" in first["browser_tip"]
    assert ts[1]["priority"] == 2
    md = handoff.to_markdown(ts, "MN lookups")
    assert md.count("- [ ]") == 2


def test_answers_roundtrip(tmp_path):
    t = handoff.task_for(
        place(), Blocker(url="https://x.gov/z", kind="http_403_waf", fields=["unit_cap", "effective_date"]), 1
    )
    ok = {
        **t,
        "result": "found",
        "max_homes_per_single_family_lot": "4",
        "by_right": "yes",
        "adopted_date": "2021-07-06",
        "effective_date": "2021-08-05",
        "districts": "R-2; R-4",
        "quote": "attached houses are permitted in R-2 and R-4",
        "source_url": "https://x.gov/ord.pdf",
        "checked_on": "2026-11-17",
    }
    bad = {**t, "result": "found", "max_homes_per_single_family_lot": "6", "adopted_date": "7/6/21"}
    blank = dict(t)
    nousable = {**t, "result": "no_usable_source"}
    p = tmp_path / "a.csv"
    handoff.write_csv([ok, bad, blank, nousable], p)
    got = handoff.read_answers(p)
    assert handoff.answer_problems(got[0]) == []
    probs = handoff.answer_problems(got[1])
    assert "found needs a quote" in probs and any("must be 1-4" in x for x in probs)
    assert any("YYYY-MM-DD" in x for x in probs)
    assert handoff.answer_problems(got[2]) == [] and handoff.answer_problems(got[3]) == []
    vals, evs = handoff.answer_to_evidence(got[0])
    assert vals == {
        "unit_cap": 4,
        "by_right": True,
        "adoption_date": date(2021, 7, 6),
        "effective_date": date(2021, 8, 5),
        "coverage_zones": ["R-2", "R-4"],
    }
    assert {e.field for e in evs} == set(vals) and evs[0].source_kind == "human_lookup"
    assert handoff.answer_to_evidence(got[3]) == ({}, [])


# ---- reconcile ---------------------------------------------------------------------------------------------


def test_reconcile_minor_and_unpaired():
    a = place([rule(adoption_date=date(2019, 11, 12))])
    later = rule(
        component="2023 rewrite", adoption_date=date(2023, 5, 1), effective_date=date(2023, 6, 1), unit_cap=4
    )
    b = place([rule(coverage_zones=["R-1", "R-1A", "R-2", "R-2B"]), later], coder="rules-mm-coder-b")
    d = reconcile.compare(a, b)
    assert [(x.field, x.severity) for x in d] == [("adoption_date", "minor"), ("rule", "major")]
    assert reconcile.agreement(d) == "adjudicated"
    assert reconcile.agreement(reconcile.compare(a, a)) == "agree"


def test_reconcile_cap_and_date_major():
    a = place([rule()])
    b = place([rule(unit_cap=2, effective_date=date(2020, 1, 15))], coder="b")
    fields = {(x.field, x.severity) for x in reconcile.compare(a, b)}
    assert fields == {("unit_cap", "major"), ("effective_date", "major")}


def test_reconcile_none_rows_dates_minor():
    """Rochester dry run: both coders coded a none row; date basis and adoption differ -> minor only."""
    ev3 = [ev("effective_date"), ev("unit_cap"), ev("coverage_zones")]
    a = place(
        [
            rule(
                unit_cap=1,
                by_right=None,
                prior_cap=None,
                adoption_date=None,
                date_basis="earliest_known",
                evidence=ev3,
            )
        ]
    )
    b = place([rule(unit_cap=1, by_right=None, prior_cap=None, evidence=ev3)], coder="b")
    d = reconcile.compare(a, b)
    assert {x.field for x in d} == {"adoption_date", "date_basis"} and {x.severity for x in d} == {"minor"}


# ---- rows --------------------------------------------------------------------------------------------------


def test_rows_validate_against_schema():
    later = rule(
        component="2023: fourplexes",
        adoption_date=date(2023, 5, 1),
        effective_date=date(2023, 6, 1),
        unit_cap=4,
        supersedes_effective=date(2020, 1, 1),
    )
    same_year = rule(
        component="2023: cottage courts",
        adoption_date=date(2023, 8, 1),
        effective_date=date(2023, 9, 1),
        unit_cap=4,
        date_basis="earliest_known",
    )
    f = place([later, rule(), same_year])
    rs = rows.place_rows(
        f,
        coder_2="rules-mm-coder-b",
        agreement="adjudicated",
        verified_by="rules-mm-verifier",
        verified_date=TODAY,
        adjudication="cap per s.3",
    )
    df = rows.table(rs)
    assert list(df["reform_id"]) == [
        "MN-2799999-missing_middle-2020",
        "MN-2799999-missing_middle-2023",
        "MN-2799999-missing_middle-2023-b",
    ]
    assert df.loc[1, "supersedes"] == "MN-2799999-missing_middle-2020"
    assert df.loc[0, "coverage_zones"] == "R1;R1A;R2;R2B"
    assert df.loc[0, "source_quote"].startswith("Up to three")
    assert df.loc[2, "coding_notes"].startswith("[earliest-known]")
    notes = df.loc[0, "coding_notes"]
    assert "Reconciled: cap per s.3" in notes
    assert 'Sources: effective_date, unit_cap, by_right, coverage_zones: "Up to three' in notes
    # the engine's reader sees what we meant
    fl = rule_tags.flags(df)
    assert list(fl["event"]) == [True, True, True] and list(fl["earliest_known"]) == [False, False, True]


def test_rows_none_and_predates():
    none_row = rule(unit_cap=1, by_right=None, date_basis="earliest_known", adoption_date=None)
    old = rule(
        date_basis="predates", unit_cap=2, effective_date=date(1985, 1, 1), adoption_date=date(1985, 1, 1)
    )
    df = rows.table(
        rows.place_rows(place([none_row]), coder_2=None, agreement="single_coder")
        + rows.place_rows(place([old], geoid="2788888"), coder_2=None, agreement="single_coder")
    )
    fl = rule_tags.flags(df)
    assert fl["none_row"].iloc[0] and not fl["event"].iloc[0]
    assert fl["predates"].iloc[1] and not fl["event"].iloc[1]
    assert rule_tags.always_allowed_places(df) == {"2788888"}  # kept in the fit as an always-allowed place


# ---- compare / CLI -----------------------------------------------------------------------------------------


def test_compare_against_coded():
    coded = rows.table(rows.place_rows(place(), coder_2=None, agreement="single_coder"))
    same = coded.copy()
    lower = rows.table(rows.place_rows(place([rule(unit_cap=2)]), coder_2=None, agreement="single_coder"))
    assert bool(compare.compare(same, coded)["match"].iloc[0])
    res = compare.compare(lower, coded)
    assert not bool(res["match"].iloc[0]) and res["final_cap_agent"].iloc[0] == 2.0
    assert res["event_year_coded"].iloc[0] == 2020


def test_compare_two_none_places_match():
    """Dry-run bug: a place with no event on both sides compared None with NaN and failed."""
    none = rule(unit_cap=1, by_right=None, prior_cap=None, date_basis="earliest_known", adoption_date=None)
    a = rows.table(rows.place_rows(place([none]), coder_2=None, agreement="single_coder"))
    old = rule(
        unit_cap=1,
        by_right=None,
        prior_cap=None,
        effective_date=date(2010, 1, 1),
        adoption_date=None,
        date_basis="earliest_known",
    )
    c = rows.table(rows.place_rows(place([old]), coder_2=None, agreement="single_coder"))
    assert bool(compare.compare(a, c)["match"].iloc[0])


def test_cli_end_to_end(tmp_path, capsys):
    run = tmp_path / "MN" / "2026-11-17"
    for d in ("findings", "reconcile", "final", "answers", "out"):
        (run / d).mkdir(parents=True)
    a = place([rule()])
    b = place([rule()], coder="rules-mm-coder-b")
    (run / "findings" / "2799999.coder-a.json").write_text(a.model_dump_json())
    (run / "findings" / "2799999.coder-b.json").write_text(b.model_dump_json())
    assert cli.main(["check", str(run)]) == 0
    assert cli.main(["reconcile", str(run)]) == 0
    assert json.loads((run / "reconcile" / "2799999.json").read_text())["agreement"] == "agree"
    final = {
        "finding": json.loads(a.model_dump_json()),
        "coder_2": "rules-mm-coder-b",
        "agreement": "agree",
        "verified_by": "rules-mm-verifier",
        "verified_date": "2026-11-17",
    }
    (run / "final" / "2799999.json").write_text(json.dumps(final))
    assert cli.main(["build", str(run)]) == 0
    out = pd.read_csv(run / "out" / "reforms_mm_mn.csv", dtype={"jurisdiction_geoid": str})
    assert out["reform_id"].tolist() == ["MN-2799999-missing_middle-2020"]
    assert cli.main(["compare", str(run), "--coded", str(run / "out" / "reforms_mm_mn.csv")]) == 0
    assert cli.main(["handoff", str(run)]) == 0
    snap = tmp_path / "s.html"
    snap.write_text("<p>Up to three dwelling units are permitted on a zoning lot.</p>")
    assert cli.main(["quote", str(snap), "up to three dwelling units"]) == 0
    assert cli.main(["quote", str(snap), "up to four"]) == 1


def test_enumerate_places():
    j = pd.DataFrame(
        {
            "geoid": ["2700001", "2700002", "27R1"],
            "name": ["A", "B", "Region"],
            "kind": ["place", "place", "region"],
            "pop_2020": [900, 5000, 99999],
        }
    )
    coded = pd.DataFrame(
        {
            "theme": ["missing_middle", "adu"],
            "jurisdiction_geoid": ["2700002", "2700001"],
            "reform_id": ["MN-2700002-missing_middle-2020", "MN-2700001-adu-2019"],
        }
    )
    out = enumerate_places(j, coded)
    assert out["geoid"].tolist() == ["2700002", "2700001"] and out["priority"].tolist() == [1, 2]
    assert out.loc[0, "coded_mm_ids"] == "MN-2700002-missing_middle-2020" and out.loc[1, "coded_mm_ids"] == ""
    assert enumerate_places(j, coded, skip_coded=True)["geoid"].tolist() == ["2700001"]
    assert enumerate_places(j, coded, min_pop=1000)["geoid"].tolist() == ["2700002"]
    assert enumerate_places(j, coded, only=["2700001"])["geoid"].tolist() == ["2700001"]


def test_brief_lists_holdouts_and_state_law(tmp_path):
    from lotline.rule_agents.mm import brief

    (tmp_path / "states").mkdir()
    (tmp_path / "states" / "mn.yaml").write_text(
        "holdouts:\n  - test_id: V5-X\n    place: St. Paul\n    geoid: '2758000'\n"
    )
    places = pd.DataFrame(
        {
            "geoid": ["2700001"],
            "place": ["A"],
            "kind": ["place"],
            "pop": [1000],
            "coded_mm_ids": [""],
            "priority": [1],
        }
    )
    coded = pd.DataFrame(
        {
            "theme": ["missing_middle"],
            "jurisdiction_geoid": ["27"],
            "reform_id": ["MN-27-missing_middle-2026"],
            "component": ["State law"],
        }
    )
    md = brief.render("MN", "r1", places, coded, tmp_path)
    assert "St. Paul (2758000)" in md and "MN-27-missing_middle-2026" in md and "Minn. Stat." in md
    assert "No default recorded" in brief.render("TX", "r1", places, None, tmp_path)
    coded_place = places.assign(coded_mm_ids="MN-2700001-missing_middle-2020")
    assert "missing_middle-2020" not in brief.render("MN", "r1", coded_place, None, tmp_path)  # blind


def test_pdftext_blank_pages_read_as_scan(tmp_path):
    """A PDF whose pages have no text layer extracts 0 characters, which `classify` calls a scan."""
    from pypdf import PdfWriter

    from lotline.rule_agents.mm import access, pdftext

    w = PdfWriter()
    w.add_blank_page(width=612, height=792)
    w.add_blank_page(width=612, height=792)
    pdf = tmp_path / "scan.pdf"
    with pdf.open("wb") as fh:
        w.write(fh)
    text, pages, chars = pdftext.extract(pdf)
    assert (pages, chars) == (2, 0)
    assert "=== page 2 ===" in text
    kind = access.classify(
        "https://x.gov/o.pdf", 200, content_type="application/pdf", pdf_text_chars=chars, pdf_pages=pages
    )
    assert kind[0] == "scanned_pdf"
    pages, chars = pdftext.write_sidecar(pdf, tmp_path / "text" / "scan.pdf.txt")
    assert (tmp_path / "text" / "scan.pdf.txt").exists()
