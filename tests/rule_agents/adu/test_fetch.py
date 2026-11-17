"""Polite retrieval: robots.txt first, no retry on a block, cache + manifest in the data dir, text."""

import json
import zlib

import httpx
import pytest

from lotline.io.store import DataStore
from lotline.rule_agents.adu import fetch as F

PAGE = (
    "<html><head><title>x</title><script>var a=1</script></head><body><h1>Sec. 5.3</h1>"
    + ("<p>An accessory dwelling unit shall not exceed 800 square feet.</p>" * 20)
    + "</body></html>"
)


def make(store, routes, calls):
    def handler(req: httpx.Request) -> httpx.Response:
        calls.append(str(req.url))
        for prefix, resp in routes.items():
            if str(req.url).startswith(prefix):
                return resp() if callable(resp) else resp
        return httpx.Response(404)

    http = httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=True)
    return F.Fetcher(store, "NC", http=http, interval=0)


@pytest.fixture
def store(tmp_path):
    return DataStore(tmp_path)


def html(body=PAGE, status=200, **h):
    return httpx.Response(status, text=body, headers={"content-type": "text/html", **h})


def test_robots_disallow_for_ai_agents_stops_before_the_page(store):
    calls = []
    robots = httpx.Response(200, text="User-agent: ClaudeBot\nDisallow: /\n")
    f = make(store, {"https://a.gov/robots.txt": robots, "https://a.gov/": html()}, calls)
    r = f.get("https://a.gov/code")
    assert (r.ok, r.reason) == (False, "robots_disallow")
    assert calls == ["https://a.gov/robots.txt"]


def test_missing_robots_allows_and_page_is_cached_with_manifest_and_text(store):
    calls = []
    f = make(store, {"https://a.gov/code": html()}, calls)
    r = f.get("https://a.gov/code")
    assert (
        r.ok and r.path.exists() and r.path.is_relative_to(store.root / "raw" / "rule_agents" / "adu" / "NC")
    )
    text = r.text_path.read_text()
    assert "shall not exceed 800 square feet" in text and "var a=1" not in text
    entry = json.loads(store.manifest_path.read_text().splitlines()[-1])
    assert entry["url"] == "https://a.gov/code" and entry["adapter"] == "lotline.rule_agents.adu.fetch"
    assert r.doc_id == entry["sha256"]  # the stable document id evidence cites


def test_wayback_redirect_reports_the_capture_actually_served(store):
    def to_capture():
        return httpx.Response(
            302, headers={"location": "https://web.archive.org/web/20250614000000/https://a.gov/x"}
        )

    routes = {
        "https://web.archive.org/web/2023/": to_capture,
        "https://web.archive.org/web/20250614000000/": html(),
    }
    r = make(store, routes, []).get("https://web.archive.org/web/2023/https://a.gov/x")
    assert (
        r.ok and r.wayback_ts == "20250614000000" and r.final_url.endswith("20250614000000/https://a.gov/x")
    )


def test_robots_server_error_means_assume_disallowed(store):
    f = make(store, {"https://a.gov/robots.txt": httpx.Response(503)}, [])
    assert f.get("https://a.gov/code").reason == "robots_unavailable"


def test_403_blocks_the_host_for_the_rest_of_the_run(store):
    calls = []
    f = make(store, {"https://b.gov/x": html("Forbidden", 403), "https://b.gov/y": html()}, calls)
    assert f.get("https://b.gov/x").reason == "http_403"
    r = f.get("https://b.gov/y")
    assert r.reason == "http_403" and "blocked earlier" in r.detail
    assert "https://b.gov/y" not in calls


def test_cloudflare_challenge_and_js_only_viewer_and_login(store):
    challenge = html("<html><title>Just a moment...</title></html>", 403, **{"cf-mitigated": "challenge"})
    js = html("<html><body><noscript>Please enable JavaScript</noscript><div id=app></div></body></html>")
    login = httpx.Response(
        200, text="<form><input type=password></form>", headers={"content-type": "text/html"}
    )
    f = make(store, {"https://c.gov/": challenge, "https://d.gov/": js, "https://e.gov/": login}, [])
    assert f.get("https://c.gov/code").reason == "waf_challenge"
    assert f.get("https://d.gov/code").reason == "js_only_viewer"
    assert f.get("https://e.gov/code").reason == "login_required"


def test_scanned_pdf_is_flagged_but_text_pdf_is_not(store):
    scanned = httpx.Response(
        200, content=b"%PDF-1.4 /XObject /Image stream", headers={"content-type": "application/pdf"}
    )
    texty = httpx.Response(
        200, content=b"%PDF-1.4 /Font /F1 BT (ADU) Tj", headers={"content-type": "application/pdf"}
    )
    f = make(store, {"https://f.gov/scan.pdf": scanned, "https://f.gov/text.pdf": texty}, [])
    s, t = f.get("https://f.gov/scan.pdf"), f.get("https://f.gov/text.pdf")
    assert (s.ok, s.reason, s.path.suffix) == (True, "scanned_pdf", ".pdf")
    assert (t.ok, t.reason) == (True, None)


def test_http_only_urls_are_refused_without_a_request(store):
    calls = []
    f = make(store, {}, calls)
    assert f.get("http://old.gov/code").reason == "not_https" and calls == []


def test_classify_status_codes():
    assert F.classify(429, {}, "", "https://x") == "rate_limited"
    assert (
        F.classify(200, {"content-type": "text/html"}, "x", "https://x/account/login?next=1")
        == "login_required"
    )
    assert F.classify(404, {}, "", "https://x") == "not_found"
    assert F.classify(200, {"content-type": "text/html"}, PAGE, "https://x") is None


def test_text_layer_found_inside_compressed_object_streams():
    hidden = zlib.compress(b"<< /Type /Page /Resources << /Font << /F1 5 0 R >> >> >>")
    pdf = b"%PDF-1.5\n1 0 obj << /Type /ObjStm /Filter /FlateDecode >>\nstream\n" + hidden + b"\nendstream"
    assert F.pdf_has_text(pdf)
    ops = zlib.compress(b"BT /F1 12 Tf (Accessory dwelling) Tj ET")
    assert F.pdf_has_text(b"%PDF-1.7\n2 0 obj\nstream\n" + ops + b"\nendstream")
    image = zlib.compress(b"\x00\xff" * 500)
    assert not F.pdf_has_text(b"%PDF-1.7\n3 0 obj << /Subtype /Image >>\nstream\n" + image + b"\nendstream")


def test_quote_check_normalises_quotes_dashes_case_and_ellipsis():
    text = "Sec. 5.3 — An “accessory dwelling unit” shall not\n exceed 800 square feet. Parking: none."
    assert F.quote_in_text('an "accessory dwelling unit" shall not exceed 800 square feet', text)
    assert F.quote_in_text("Sec. 5.3 - An ... exceed 800 square feet", text)
    assert not F.quote_in_text("shall not exceed 1,000 square feet", text)
    assert not F.quote_in_text("Parking: none ... Sec. 5.3", text)  # parts must appear in order
