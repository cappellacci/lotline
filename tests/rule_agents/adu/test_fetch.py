"""ADU fetching goes through the shared core: store first into the document store, PDFs page-marked, and
the shared quote checks. (Robots, refusals and the no-retry rule are tested in tests/rule_agents/common.)"""

import httpx
import pytest

from lotline.rule_agents.adu import fetch as F
from lotline.rule_agents.common import fetch as common_fetch
from lotline.rule_agents.common.docstore import DocStore

PAGE = (
    "<html><head><title>Sec. 5.3</title><script>var a=1</script></head><body><h1>Sec. 5.3</h1>"
    + ("<p>An accessory dwelling unit shall not exceed 800 square feet.</p>" * 20)
    + "</body></html>"
)


@pytest.fixture
def web(monkeypatch):
    monkeypatch.setattr(common_fetch, "HOST_INTERVAL", 0.0)
    calls: list[str] = []

    def make(routes):
        def handler(req: httpx.Request) -> httpx.Response:
            calls.append(str(req.url))
            status, body, ctype = routes.get(str(req.url), (404, "", "text/html"))
            content = body if isinstance(body, bytes) else body.encode()
            return httpx.Response(status, content=content, headers={"content-type": ctype})

        return httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=True)

    return make, calls


def test_adu_fetch_is_store_first_under_the_adu_category(tmp_path, web):
    make, calls = web
    docs = DocStore(tmp_path)
    http = make({"https://a.gov/code": (200, PAGE, "text/html")})
    r = F.get("https://a.gov/code", "r1", docs=docs, http=http, jurisdictions=["3799999"])
    assert r.blocker is None and r.doc_id and not r.cached
    assert docs.get(r.doc_id).categories == ["adu"] and docs.get(r.doc_id).jurisdictions == ["3799999"]
    text = docs.text(r.doc_id)
    assert "shall not exceed 800 square feet" in text and "var a=1" not in text
    n = len(calls)
    again = F.get("https://a.gov/code", "r2", docs=docs, http=http)
    assert again.cached and again.doc_id == r.doc_id and len(calls) == n  # no second request


def test_stored_text_pdf_is_page_marked_and_scan_is_a_blocker(tmp_path, web):
    make, _ = web
    docs = DocStore(tmp_path)
    pad = " Text continues." * 14  # a text page has at least SCAN_CHARS_PER_PAGE characters
    pdf = tiny_pdf(
        ["Section 5.3 Accessory dwelling units are permitted by right." + pad, "One ADU per lot." + pad]
    )
    http = make(
        {
            "https://g.gov/ord.pdf": (200, pdf, "application/pdf"),
            "https://g.gov/scan.pdf": (200, tiny_pdf(["", ""]), "application/pdf"),
        }
    )
    r = F.get("https://g.gov/ord.pdf", "r1", docs=docs, http=http)
    assert r.blocker is None and r.pages == 2
    assert docs.quote(r.doc_id, "accessory dwelling units are permitted by right") == ("verbatim", 1)
    assert docs.quote(r.doc_id, "One ADU per lot") == ("verbatim", 2)
    assert docs.quote(r.doc_id, "three ADUs per lot") == ("not_found", None)
    s = F.get("https://g.gov/scan.pdf", "r1", docs=docs, http=http)
    assert s.blocker == "scanned_pdf" and s.doc_id  # held, readable by eye (image_read)


def test_quote_check_normalises_quotes_dashes_case_and_ellipsis():
    text = "Sec. 5.3 — An “accessory dwelling unit” shall not\n exceed 800 square feet. Parking: none."
    assert F.quote_in_text('an "accessory dwelling unit" shall not exceed 800 square feet', text)
    assert F.quote_in_text("Sec. 5.3 - An ... exceed 800 square feet", text)
    assert not F.quote_in_text("shall not exceed 1,000 square feet", text)
    assert not F.quote_in_text("Parking: none ... Sec. 5.3", text)  # parts must appear in order


def tiny_pdf(pages: list[str]) -> bytes:
    """A minimal, valid PDF with one line of Helvetica text per page (hand-built; no PDF writer needed)."""
    n = len(pages)
    objs = ["<< /Type /Catalog /Pages 2 0 R >>"]
    kids = " ".join(f"{4 + 2 * i} 0 R" for i in range(n))
    objs.append(f"<< /Type /Pages /Kids [{kids}] /Count {n} >>")
    objs.append("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    for i, line in enumerate(pages):
        stream = f"BT /F1 10 Tf 20 700 Td ({line}) Tj ET"
        objs.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 3 0 R >> >> "
            f"/Contents {5 + 2 * i} 0 R >>"
        )
        objs.append(f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream")
    out, offsets = b"%PDF-1.4\n", []
    for k, body in enumerate(objs, 1):
        offsets.append(len(out))
        out += f"{k} 0 obj\n{body}\nendobj\n".encode()
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    out += b"".join(f"{o:010d} 00000 n \n".encode() for o in offsets)
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return out


def test_quote_across_a_page_break_counts_on_the_first_page():
    text = "=== page 1 ===\npermitted by right.\n=== page 2 ===\nOne ADU per lot"
    assert F.quote_page("by right. One ADU", text) == 1


def test_quote_check_tolerates_pdf_word_breaks_but_not_different_words():
    text = "accessory dwelling un its shall not be subject to Article 6.7 and the requirem ents"
    assert F.quote_in_text("accessory dwelling units shall not be subject to Article 6.7", text)
    assert not F.quote_in_text("accessory dwelling units shall be subject to Article 6.7", text)
