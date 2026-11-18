"""Tests for the rule swarms' shared core: document store, store-first fetch, passages, budget, evidence.

Synthetic fixtures only: tiny HTML pages and a hand-built two-page text PDF written into `tmp_path`, and an
httpx mock transport standing in for city web servers. No network, no downloaded data.
"""

from __future__ import annotations

import json
from datetime import date

import httpx
import pytest

from lotline.rule_agents import __main__ as cli
from lotline.rule_agents.common import budget, excerpts, fetch, handoff
from lotline.rule_agents.common import text as T
from lotline.rule_agents.common.docstore import Citation, DocStore
from lotline.rule_agents.common.evidence import Evidence, max_confidence

GEOID = "3755000"  # a synthetic NC place
COUNTY = "37183"


def _pdf(pages: list[str]) -> bytes:
    """A minimal valid PDF with one line of Helvetica text per page (offsets computed, so pypdf reads it)."""
    objs = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        None,
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    kids = []
    for txt in pages:
        stream = f"BT /F1 12 Tf 72 720 Td ({txt}) Tj ET"
        objs.append(f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream")
        content = len(objs)
        objs.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents {content} 0 R "
            "/Resources << /Font << /F1 3 0 R >> >> >>"
        )
        kids.append(f"{len(objs)} 0 R")
    objs[1] = f"<< /Type /Pages /Kids [{' '.join(kids)}] /Count {len(kids)} >>"
    out, offs = b"%PDF-1.4\n", []
    for i, o in enumerate(objs, start=1):
        offs.append(len(out))
        out += f"{i} 0 obj\n{o}\nendobj\n".encode()
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    out += b"".join(f"{o:010d} 00000 n \n".encode() for o in offs)
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return out


ADU_PAGE = (
    "<html><head><title>Sec. 5.2 Accessory dwelling units</title><script>track()</script></head><body>"
    "<p>Sec. 5.2.1 Signs. Signs shall not exceed 20 square feet.</p>"
    "<p>Sec. 5.2.4 Accessory dwelling units. One accessory dwelling unit is a permitted use on a lot in "
    "the R-1 district. Adopted June 4, 2019 by Ordinance No. 2019-12.</p>"
    "<p>Sec. 5.2.9 Fences. Fences may be 6 feet tall.</p></body></html>"
)


@pytest.fixture
def docs(tmp_path):
    return DocStore(tmp_path)


def _raw(docs, name, body: bytes | str):
    p = docs.data_root / "raw" / "rule_docs" / "2026-11-17" / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(body if isinstance(body, bytes) else body.encode())
    return p


# ---- document store ----------------------------------------------------------------------------------------
def test_same_bytes_from_two_urls_and_two_swarms_is_one_document(docs):
    a = docs.ingest(
        _raw(docs, "a.html", ADU_PAGE),
        url="https://city.gov/adu",
        added_by="run:adu:r1",
        category="adu",
        jurisdictions=[GEOID],
    )
    b = docs.ingest(
        _raw(docs, "b.html", ADU_PAGE),
        url="https://library.municode.com/x",
        added_by="run:mm:r2",
        category="mm",
    )
    assert a.doc_id == b.doc_id
    rec = docs.get(a.doc_id)
    assert [u["url"] for u in rec.urls] == ["https://city.gov/adu", "https://library.municode.com/x"]
    assert rec.categories == ["adu", "mm"]
    assert rec.added_by == "run:adu:r1"  # the first fetch keeps credit
    assert rec.title == "Sec. 5.2 Accessory dwelling units"
    assert len(list((docs.root / "blobs").rglob("*.html"))) == 1  # one blob
    assert "track()" not in docs.text(a.doc_id)  # sidecar holds what a reader sees


def test_new_bytes_from_a_known_url_supersede_and_history_walks_both_ways(docs):
    url = "https://city.gov/fees.html"
    v1 = docs.ingest(
        _raw(docs, "f1.html", "<p>Impact fee $1,000 per unit FY2025</p>"), url=url, added_by="r1"
    )
    v2 = docs.ingest(
        _raw(docs, "f2.html", "<p>Impact fee $1,200 per unit FY2026</p>"), url=url, added_by="r2"
    )
    assert v2.supersedes == v1.doc_id
    assert [r.doc_id for r in docs.history(v1.doc_id)] == [v1.doc_id, v2.doc_id]
    assert [r.doc_id for r in docs.history(v2.doc_id)] == [v1.doc_id, v2.doc_id]


def test_find_by_place_county_and_text(docs):
    county_code = docs.ingest(
        _raw(docs, "c.html", ADU_PAGE),
        url="https://county.gov/udo",
        added_by="r",
        jurisdictions=[COUNTY],
        doc_type="code_section",
    )
    docs.ingest(
        _raw(docs, "o.html", "<p>Other town ordinance about fences.</p>"),
        url="https://o.gov/x",
        added_by="r",
        jurisdictions=["3799999"],
    )
    # a county code covers the place when the county is given (a place GEOID does not contain its county)
    assert [h.doc.doc_id for h in docs.find(geoid=GEOID, county=COUNTY)] == [county_code.doc_id]
    assert docs.find(geoid=GEOID) == []
    assert docs.find(state="NC", doc_type="code_section")[0].doc.doc_id == county_code.doc_id
    hits = docs.find(text="accessory dwelling R-1")
    assert [h.doc.doc_id for h in hits] == [county_code.doc_id] and hits[0].pages == [1]
    assert docs.find(text="duplex") == []


def test_pdf_sidecar_pages_and_quote_page(docs):
    pdf = _raw(
        docs,
        "o.pdf",
        _pdf(
            [
                "Section 1. Title and purpose of this ordinance " * 6,
                "Section 2. Up to three dwelling units are allowed per lot " * 5,
            ]
        ),
    )
    rec = docs.ingest(pdf, url="https://city.gov/o.pdf", added_by="r")
    assert (rec.pages, rec.text_status) == (2, "text")
    assert docs.quote(rec.doc_id, "Up to three dwelling units are allowed") == ("verbatim", 2)
    assert docs.quote(rec.doc_id, "four dwelling units") == ("not_found", None)
    assert "Section 2" in docs.text(rec.doc_id, page=2) and "Section 2" not in docs.text(rec.doc_id, page=1)


def test_scanned_pdf_quotes_are_image_read(docs):
    from pypdf import PdfWriter

    w = PdfWriter()
    w.add_blank_page(width=612, height=792)
    p = docs.data_root / "raw" / "rule_docs" / "scan.pdf"
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("wb") as fh:
        w.write(fh)
    rec = docs.ingest(p, url="https://city.gov/scan.pdf", added_by="r")
    assert rec.text_status == "scanned"
    assert docs.quote(rec.doc_id, "anything") == ("image_read", None)


def test_withdraw_hides_the_document_and_lists_its_citations(docs):
    rec = docs.ingest(_raw(docs, "w.html", ADU_PAGE), url="https://wrong-town.gov/adu", added_by="r")
    docs.cite(
        [
            Citation(
                rec.doc_id[:10],
                "adu",
                "NC-3755000-adu-2019",
                "effective_date",
                "Adopted June 4, 2019",
                page=1,
            )
        ]
    )
    back = docs.withdraw(rec.doc_id, "wrong town (same ordinance number, other state)")
    assert [c.row_key for c in back] == ["NC-3755000-adu-2019"]
    assert docs.find() == [] and docs.find(include_withdrawn=True)[0].doc.withdrawn.startswith("wrong town")
    with pytest.raises(ValueError):
        docs.withdraw(rec.doc_id, " ")


def test_a_person_adds_a_file_through_the_manifest(docs, tmp_path):
    saved = tmp_path / "saved" / "ord-2019-12.html"
    saved.parent.mkdir()
    saved.write_text(ADU_PAGE)
    rec = docs.add(
        saved, url="https://city.gov/adu", added_by="human:bc", retrieved="2026-11-17", jurisdictions=[GEOID]
    )
    assert rec.added_by == "human:bc"
    manifest = [json.loads(x) for x in (docs.data_root / "manifest.jsonl").read_text().splitlines()]
    assert manifest[-1]["source"] == "rule_docs_manual" and manifest[-1]["sha256"] == rec.doc_id
    with pytest.raises(ValueError):
        docs.add(saved, url="https://city.gov/adu", added_by="bc")  # must say it was a person


def test_inbox_and_saved_file_answer_become_a_cited_document(docs):
    docs.inbox.mkdir(parents=True)
    (docs.inbox / "minutes.html").write_text("<p>Council adopted Ordinance 2019-12 on June 4, 2019.</p>")
    assert [p.name for p in docs.pending_inbox()] == ["minutes.html"]
    row = {
        "result": "found",
        "saved_file": "minutes.html",
        "source_url": "https://city.gov/minutes",
        "checked_by": "BC",
        "checked_on": "2026-11-17",
        "quote": "adopted Ordinance 2019-12 on June 4, 2019",
    }
    did = handoff.take_saved_file(docs, row, geoid=GEOID, category="mm", state="NC")
    assert docs.pending_inbox() == []
    assert docs.get(did).added_by == "human:bc" and docs.quote(did, row["quote"])[0] == "verbatim"
    with pytest.raises(FileNotFoundError):
        handoff.take_saved_file(
            docs, {**row, "saved_file": "missing.pdf"}, geoid=GEOID, category="mm", state="NC"
        )


def test_doc_id_prefix_and_catalog_holds_no_document_text(docs):
    rec = docs.ingest(_raw(docs, "a.html", ADU_PAGE), url="https://city.gov/adu", added_by="human:bc")
    assert docs.resolve(rec.doc_id[:8]) == rec.doc_id
    with pytest.raises(KeyError):
        docs.resolve("abc")
    row = docs.catalog_rows()[0]
    assert row["doc_id"] == rec.doc_id and row["added_by"] == "human"  # initials stay out
    assert "permitted use" not in json.dumps(row)


def test_annotate_rejects_unknown_fields_and_types(docs):
    rec = docs.ingest(_raw(docs, "a.html", ADU_PAGE), url="https://city.gov/adu", added_by="r")
    docs.annotate(rec.doc_id, notes="county UDO adopted by the town", may_contain_outcomes=True)
    r = docs.get(rec.doc_id)
    assert r.notes == ["county UDO adopted by the town"] and r.may_contain_outcomes
    with pytest.raises(ValueError):
        docs.annotate(rec.doc_id, colour="red")
    with pytest.raises(ValueError):
        docs.annotate(rec.doc_id, doc_type="blog")


# ---- store-first fetch -------------------------------------------------------------------------------------
class _Server:
    """A fake web: robots.txt and pages per host; counts requests."""

    def __init__(self, routes):
        self.routes, self.calls = routes, []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(str(request.url))
        status, body, ctype = self.routes.get(str(request.url), (404, "", "text/html"))
        return httpx.Response(
            status,
            content=body if isinstance(body, bytes) else body.encode(),
            headers={"content-type": ctype},
        )


@pytest.fixture
def web(monkeypatch):
    monkeypatch.setattr(fetch, "HOST_INTERVAL", 0.0)

    def make(routes):
        srv = _Server(routes)
        return srv, httpx.Client(transport=httpx.MockTransport(srv), follow_redirects=True)

    return make


def test_fetch_stores_once_then_serves_from_the_store_without_a_request(docs, web):
    srv, http = web(
        {
            "https://city.gov/robots.txt": (200, "User-agent: *\nDisallow: /search", "text/plain"),
            "https://city.gov/udo/adu": (200, ADU_PAGE, "text/html"),
        }
    )
    r1 = fetch.get("https://city.gov/udo/adu", "adu", "r1", docs=docs, http=http, jurisdictions=[GEOID])
    assert r1.blocker is None and not r1.cached and r1.doc_id
    n = len(srv.calls)
    r2 = fetch.get("https://city.gov/udo/adu", "mm", "r2", docs=docs, http=http)  # another swarm
    assert r2.cached and r2.doc_id == r1.doc_id and len(srv.calls) == n  # no request at all
    assert docs.get(r1.doc_id).categories == ["adu", "mm"]


def test_robots_disallow_is_never_fetched_and_is_remembered(docs, web):
    srv, http = web(
        {"https://city.gov/robots.txt": (200, "User-agent: ClaudeBot\nDisallow: /", "text/plain")}
    )
    r = fetch.get("https://city.gov/code", "mm", "r1", docs=docs, http=http)
    assert r.blocker == "robots_disallow"
    assert srv.calls == ["https://city.gov/robots.txt"]  # a block for any of our tokens is a block
    assert docs.recent_block("https://city.gov/code")["kind"] == "robots_disallow"


def test_a_bot_wall_closes_the_host_for_every_swarm_with_no_retry(docs, web):
    srv, http = web(
        {
            "https://city.gov/robots.txt": (404, "", "text/plain"),
            "https://city.gov/a": (403, "<title>Just a moment...</title>", "text/html"),
        }
    )
    r = fetch.get("https://city.gov/a", "fees", "r1", docs=docs, http=http)
    assert r.blocker == "http_403_waf"
    assert srv.calls.count("https://city.gov/a") == 1  # one attempt, never retried
    n = len(srv.calls)
    r2 = fetch.get("https://city.gov/b", "adu", "r2", docs=docs, http=http)  # other page, same host
    assert r2.blocker == "http_403_waf" and len(srv.calls) == n


def test_robots_server_error_means_disallowed(docs, web):
    _, http = web({"https://city.gov/robots.txt": (503, "", "text/plain")})
    assert fetch.get("https://city.gov/a", "mm", "r1", docs=docs, http=http).blocker == "robots_unavailable"


# ---- passages for coders -----------------------------------------------------------------------------------
def test_excerpts_keep_the_relevant_block_within_budget(docs):
    pages = [
        "Section 3.1 Signs. Signs in residential districts shall not exceed 20 square feet in area. " * 3,
        "Section 3.2 Accessory dwelling units. One accessory dwelling unit is a permitted use in R-1. "
        "Adopted June 4, 2019 by Ordinance No. 2019-12.",
        "Section 3.3 Fences. Fences shall not exceed six feet. " * 3,
    ]
    rec = docs.ingest(_raw(docs, "o.pdf", _pdf(pages)), url="https://city.gov/o.pdf", added_by="r")
    ps = excerpts.excerpts(docs, rec.doc_id, "adu", max_chars=500)
    assert [p.page for p in ps] == [2]
    assert "Adopted June 4, 2019" in ps[0].text and ps[0].render().startswith(f"[{rec.doc_id[:12]} p.2]")
    assert excerpts.excerpts(docs, rec.doc_id, "fees", max_chars=500) == []  # nothing on fees
    assert excerpts.score("Adopted June 4, 2019.", "adu") == 0  # date words alone are not relevant
    assert 3 in [p.page for p in excerpts.excerpts(docs, rec.doc_id, "mm", extra=["fences"], max_chars=500)]


def test_outline_lists_section_headings_with_pages(docs):
    rec = docs.ingest(
        _raw(docs, "c.txt", "Sec. 5.2.4 Accessory dwelling units\ntext\nTable 2-1 Uses\n"),
        url="https://city.gov/c.txt",
        added_by="r",
    )
    assert excerpts.outline(docs, rec.doc_id) == [
        (1, "Sec. 5.2.4 Accessory dwelling units"),
        (1, "Table 2-1 Uses"),
    ]


# ---- budget ------------------------------------------------------------------------------------------------
def test_budget_stops_a_place_at_its_limit(tmp_path):
    budget.add(tmp_path, GEOID, "scout", tokens=60, searches=3)
    budget.add(tmp_path, GEOID, "coder-a", tokens=50, fetches=2)
    st = budget.status(tmp_path, GEOID, {"tokens": 100})
    assert st["left"]["tokens"] == -10 and st["stop"] and st["reason"] == ["tokens"]
    assert not budget.status(tmp_path, "other", {"tokens": 100})["stop"]
    rows = budget.summary(tmp_path)
    assert rows[-1] == {"place": "TOTAL", "tokens": 110, "fetches": 2, "searches": 3}
    with pytest.raises(ValueError):
        budget.add(tmp_path, GEOID, "x", tokens=-1)


def test_ledger_cli_status_exit_code_says_stop(tmp_path, capsys):
    run = str(tmp_path)
    assert cli.main(["ledger", "add", run, GEOID, "coder-a", "--tokens", "130000"]) == 0
    assert cli.main(["ledger", "status", run, GEOID]) == 3  # over the default 120k
    assert json.loads(capsys.readouterr().out.strip().splitlines()[-1])["reason"] == ["tokens"]


# ---- evidence, text, hand-off ------------------------------------------------------------------------------
def _ev(kind, status):
    return Evidence(
        field="x",
        url="https://a.gov",
        quote="q",
        retrieved=date(2026, 11, 17),
        source_kind=kind,
        quote_status=status,
    )


def test_confidence_ceiling_from_evidence():
    assert max_confidence([_ev("code", "verbatim")]) == "high"
    assert max_confidence([_ev("mirror", "verbatim")]) == "medium"
    assert max_confidence([_ev("code", "image_read")]) == "medium"
    assert max_confidence([_ev("news", "verbatim")]) == "low"
    assert max_confidence([]) == "low"


def test_quote_checks_survive_pdf_word_splits_and_find_pages():
    assert T.verify_quote("accessory dwelling units", "an accessory dwel ling units rule")
    assert not T.verify_quote("four units", "three units")
    txt = "=== page 1 ===\nintro\n=== page 2 ===\nUp to three\n=== page 3 ===\ndwelling units per lot"
    assert T.quote_page("Up to three dwelling units", txt) == 2  # spans pages 2-3: starts on 2


def test_base_answer_checks():
    ok = {"result": "found", "quote": "q", "source_url": "https://a.gov", "checked_on": "2026-11-17"}
    assert handoff.base_problems(ok) == []
    assert handoff.base_problems({}) == []  # not answered yet
    assert "found needs a quote" in handoff.base_problems({**ok, "quote": ""})
    assert any("not one of" in p for p in handoff.base_problems({**ok, "result": "maybe"}))
    assert any("YYYY-MM-DD" in p for p in handoff.base_problems({**ok, "checked_on": "11/17/26"}))
    assert any("longer" in p for p in handoff.base_problems({**ok, "quote": "x" * 301}))


def test_a_heading_brings_its_lettered_standards(docs):
    """The Sunfish Lake pattern: the heading names ADUs, the size cap sits in clause D with no ADU word."""
    page = (
        "1207.11 ANTENNAS: Antennas shall be attached to buildings.\n \n"
        "1207.12 ACCESSORY DWELLING UNITS (ADUs): Standards for attached ADUs are as follows:\n \n"
        "A. Allowed as a permitted use in the R-1 district.\n \n"
        "B. Must meet living space setbacks.\n \n"
        "D. Maximum size of fifty percent (50%) of the finished square footage or 1,200 square feet.\n \n"
    )
    rec = docs.ingest(_raw(docs, "p.txt", page), url="https://city.gov/p.txt", added_by="r")
    text = " ".join(p.text for p in excerpts.excerpts(docs, rec.doc_id, "adu", max_chars=2000))
    assert "1,200 square feet" in text and "Antennas" not in text


# ---- import and setup check --------------------------------------------------------------------------------
def _reform_file(tmp_path, rows):
    """A tiny config/reforms/mn.csv using the real header, filled from an existing schema-valid row shape."""
    from lotline.schemas import columns

    header = list(columns("reforms"))
    cfg = tmp_path / "config" / "reforms"
    cfg.mkdir(parents=True)
    import csv as _csv

    with open(cfg / "mn.csv", "w", newline="") as fh:
        w = _csv.DictWriter(fh, fieldnames=header)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in header})
    return tmp_path / "config", header


def _reform(rid, cap, **kw):
    """A schema-valid row: the first missing-middle row of the repo's MN reforms file, re-keyed."""
    import csv as _csv
    from pathlib import Path

    src = Path(__file__).resolve().parents[3] / "config" / "reforms" / "mn.csv"
    with open(src, newline="") as fh:
        base = next(r for r in _csv.DictReader(fh) if r["theme"] == "missing_middle")
    geoid = rid.split("-")[1]
    return {
        **base,
        "reform_id": rid,
        "jurisdiction_geoid": geoid,
        "unit_cap": str(cap),
        "supersedes": "",
        **kw,
    }


def test_import_previews_adds_and_only_replaces_changes_when_asked(tmp_path):
    from lotline.rule_agents.common import importer
    from lotline.schemas import columns

    a, b = _reform("MN-2700001-missing_middle-2020", 3), _reform("MN-2700002-missing_middle-2021", 2)
    config, header = _reform_file(tmp_path, [a, b])
    before = (config / "reforms" / "mn.csv").read_text()
    prop = tmp_path / "proposal.csv"
    import csv as _csv

    with open(prop, "w", newline="") as fh:
        w = _csv.DictWriter(fh, fieldnames=list(columns("reforms")))
        w.writeheader()
        w.writerow({**a, "unit_cap": "4"})
        w.writerow(_reform("MN-2700003-missing_middle-2022", 2))
    try:
        p = importer.plan(prop, "reforms", "MN", config)
    except importer.ImportError_ as exc:  # pragma: no cover - shows the schema problem if the fixture drifts
        raise AssertionError(exc) from None
    assert [r["reform_id"] for r in p.added] == ["MN-2700003-missing_middle-2022"]
    assert [(n["reform_id"], cols) for _, n, cols in p.changed] == [
        ("MN-2700001-missing_middle-2020", ["unit_cap"])
    ]
    # preview writes nothing
    assert (config / "reforms" / "mn.csv").read_text() == before
    assert "MN-2700003" in importer.merged_text(p)
    importer.apply(p)
    rows = (config / "reforms" / "mn.csv").read_text().splitlines()
    assert len(rows) == 4 and rows[1] == before.splitlines()[1]  # existing row untouched, byte for byte
    importer.apply(importer.plan(prop, "reforms", "MN", config), replace_changed=True)
    assert "MN-2700001" in (config / "reforms" / "mn.csv").read_text().splitlines()[1]


def test_import_refuses_unknown_columns_other_states_and_repeated_keys(tmp_path):
    from lotline.rule_agents.common import importer

    config, header = _reform_file(tmp_path, [])
    bad = tmp_path / "bad.csv"
    bad.write_text("reform_id,state,colour\nMN-2700001-missing_middle-2020,MN,red\n")
    with pytest.raises(importer.ImportError_, match="colour"):
        importer.plan(bad, "reforms", "MN", config)
    bad.write_text("reform_id,state\nWI-5500001-missing_middle-2020,WI\n")
    with pytest.raises(importer.ImportError_, match="other than MN"):
        importer.plan(bad, "reforms", "MN", config)
    bad.write_text("reform_id,state\nMN-1,MN\nMN-1,MN\n")
    with pytest.raises(importer.ImportError_, match="repeats"):
        importer.plan(bad, "reforms", "MN", config)


def test_import_will_not_write_a_table_that_fails_the_schema(tmp_path):
    from lotline.rule_agents.common import importer

    config, header = _reform_file(tmp_path, [])
    prop = tmp_path / "p.csv"
    prop.write_text("reform_id,state,jurisdiction_geoid,theme\nMN-2700001-x-2020,MN,2700001,not_a_theme\n")
    p = importer.plan(prop, "reforms", "MN", config)
    with pytest.raises(importer.ImportError_, match="schema"):
        importer.apply(p)
    assert len((config / "reforms" / "mn.csv").read_text().splitlines()) == 1  # unchanged


def test_doctor_flags_only_what_a_run_needs(tmp_path):
    from lotline.rule_agents.common import doctor

    repo = tmp_path / "repo"
    (repo / ".claude" / "commands").mkdir(parents=True)
    (repo / ".claude" / "commands" / "rules-mm.md").write_text("x")
    res = doctor.checks("MN", repo, category="mm", data_root=tmp_path / "data")
    bad = {label for ok, label, _ in res if not ok}
    assert any("data folder" in b for b in bad)  # missing data folder is flagged
    assert any("jurisdictions" in b for b in bad)
    assert not any("rules-adu" in b for b in bad)  # other categories are information only
    assert any(
        "rules-fees" in b
        for b in {
            label for ok, label, _ in doctor.checks("MN", repo, category="fees", data_root=tmp_path) if not ok
        }
    )
    assert "thing(s) to fix" in doctor.render(res)


def test_a_year_only_wayback_link_records_the_capture_actually_served(docs, monkeypatch):
    """By hand: /web/2023/<url> redirects to the nearest capture, /web/20220301120000/<url> (a 2022 copy);
    the result and the stored document carry that capture, and a later store hit reports it too."""
    monkeypatch.setattr(fetch, "HOST_INTERVAL", 0.0)
    asked = "https://web.archive.org/web/2023/https://city.gov/udo/adu"
    served = "https://web.archive.org/web/20220301120000/https://city.gov/udo/adu"

    def srv(request: httpx.Request) -> httpx.Response:
        u = str(request.url)
        if u.endswith("/robots.txt"):
            return httpx.Response(200, text="User-agent: *\nAllow: /")
        if u == asked:
            return httpx.Response(302, headers={"location": served})
        if u == served:
            return httpx.Response(200, text=ADU_PAGE, headers={"content-type": "text/html"})
        return httpx.Response(404)

    http = httpx.Client(transport=httpx.MockTransport(srv), follow_redirects=True)
    r = fetch.get(asked, "adu", "r1", docs=docs, http=http)
    assert r.blocker is None
    assert r.final_url == served and r.wayback_ts == "20220301120000"
    assert docs.get(r.doc_id).wayback_ts == "20220301120000"
    again = fetch.get(asked, "mm", "r2", docs=docs, http=http)
    assert again.cached and again.wayback_ts == "20220301120000" and again.final_url == served
    assert not http.event_hooks["response"]  # the caller's client is left as it was
    assert fetch.wayback_ts(asked) is None
