"""Polite, robots-respecting retrieval for the rule agents, with a block classifier.

Agents never fetch a code or city page any other way (no WebFetch on official hosts, no curl, no changed
user agent): two process incidents in WS-ADU-RULES came from agents retrying a refused PDF with curl and a
browser user agent (lessons L-R6). Here:

- **robots.txt first** (RFC 9309): a disallow for our user agent stops the request. A robots.txt that answers
  4xx means no rules; 5xx or no answer means "assume disallowed" for this run.
- **One request per host every `MIN_INTERVAL` seconds**, across processes (lock file in the data directory).
- **No retry on a block.** 401/403/429, a bot challenge page, a login wall or a script-only code viewer is
  classified (`REASONS` in handoff.py) and returned as a block; the orchestrator turns it into a human task.
- **Every copy lands in LOTLINE_DATA_DIR** (`raw/rule_agents/adu/<ST>/<host>/<sha1(url)>.<ext>`) and in
  `manifest.jsonl`; nothing is written to the repo.
- **Text** for the coders: HTML is reduced to text with the standard-library parser; a PDF with no text layer
  is a `scanned_pdf` block (the coder may still read it with the Read tool and must say so); a text PDF is
  returned as a path for the Read tool (no PDF dependency added).
"""

from __future__ import annotations

import datetime as dt
import fcntl
import hashlib
import re
import time
import zlib
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from urllib.robotparser import RobotFileParser

import httpx

from lotline.io import http as lhttp
from lotline.io.store import DataStore, ManifestEntry, sha256_file, utc_now
from lotline.rule_agents.adu import HELPERS_VERSION

USER_AGENT = lhttp.USER_AGENT
# Checked together: the request carries lotline's user agent, but an AI agent chose the URL, so a site that
# disallows AI crawlers (ecode360 disallows ClaudeBot) is respected too.
ROBOTS_AGENTS = ("lotline", "ClaudeBot", "Claude-User", "anthropic-ai")
MIN_INTERVAL = 3.0  # seconds between requests to one host
MAX_BYTES = 15_000_000

# Hosts whose live pages are known not to serve scripts (lessons L-R1): asked once, then routed to a human
# task or an allowed alternative. The value is the plain-language alternative for the task.
KNOWN_BLOCKERS = {
    "library.municode.com": "Municode library (Cloudflare challenge, script-only viewer): open in a browser",
    "codelibrary.amlegal.com": "American Legal code library (403 to scripts): open in a browser",
    "ecode360.com": "eCode360 (robots.txt disallows AI agents): open in a browser",
}
# Hosts known to serve scripts in earlier runs (useful alternatives, still robots-checked every time).
KNOWN_ALTERNATIVES = {
    "mcclibrary.blob.core.usgovcloudapi.net": "Municode's PDF supplements (served NC Wilmington's LDC)",
    "files.amlegal.com": "American Legal PDF files (served Cary's LDO chapters)",
    "webapi.legistar.com": "Legistar API: matters and attachments (St. Paul, Columbus, Winston-Salem)",
    "web.archive.org": "Wayback copies of past code versions and of pages that refuse scripts",
    "www.zoneomics.com": "third-party code mirror: secondary only, caps confidence at medium",
}
_CHALLENGE = re.compile(
    r"just a moment\.\.\.|attention required! \| cloudflare|cf-chl|cf_chl_opt|"
    r"request unsuccessful\. incapsula|"
    r"access denied|are you a robot|captcha|ddos protection by|akamai reference #",
    re.I,
)
_JS_ONLY = re.compile(r"(enable|requires) javascript|<noscript>|ng-app|data-reactroot", re.I)
_LOGIN = re.compile(r"/(login|signin|sign-in|account/logon)\b|<input[^>]+type=[\"']?password", re.I)


@dataclass
class FetchResult:
    url: str
    ok: bool
    reason: str | None = None  # a handoff.REASONS key when not ok
    status: int | None = None
    path: Path | None = None  # cached copy under LOTLINE_DATA_DIR
    text_path: Path | None = None  # extracted text (HTML) next to it
    content_type: str | None = None
    retrieved: dt.date | None = None
    detail: str = ""
    doc_id: str | None = None  # sha256 of the bytes: cite it in Evidence.doc_id


# ---- robots ----------------------------------------------------------------------------------------------


def robots_parser(status: int | None, body: str) -> RobotFileParser | None:
    """A parser for a robots.txt response; None means 'assume disallowed' (5xx or no answer, RFC 9309)."""
    rp = RobotFileParser()
    if status is None or status >= 500:
        return None
    if status >= 400:
        rp.parse([])  # no robots.txt: no rules
        return rp
    rp.parse(body.splitlines())
    return rp


def robots_allows(rp: RobotFileParser | None, url: str, agents=ROBOTS_AGENTS) -> bool:
    return rp is not None and all(rp.can_fetch(a, url) for a in agents)


# ---- classification --------------------------------------------------------------------------------------


def classify(status: int, headers: dict[str, str], body_head: str, final_url: str) -> str | None:
    """A block reason for a response, or None when it is a real page."""
    h = {k.lower(): v for k, v in headers.items()}
    if status == 429:
        return "rate_limited"
    if status in (401, 407) or _LOGIN.search(final_url):
        return "login_required"
    if "cf-mitigated" in h or (status in (403, 503) and _CHALLENGE.search(body_head)):
        return "waf_challenge"
    if status == 403:
        return "http_403"
    if status == 404 or status == 410:
        return "not_found"
    if status >= 400:
        return "http_error"
    ctype = h.get("content-type", "")
    if "html" in ctype:
        if _CHALLENGE.search(body_head[:5000]) and len(body_head) < 20000:
            return "waf_challenge"
        if _LOGIN.search(body_head[:20000]) and "password" in body_head.lower():
            return "login_required"
        if _JS_ONLY.search(body_head[:5000]) and len(html_to_text(body_head)) < 400:
            return "js_only_viewer"
    return None


def pdf_has_text(data: bytes, max_streams: int = 400) -> bool:
    """True when a PDF carries a text layer (a font resource or text-showing operators).

    PDF 1.5+ files often hide `/Font` inside compressed object streams, so Flate streams are inflated
    (standard library zlib) and searched too. Scanned PDFs carry images only.
    (Dry run 2026-11-17: Raleigh and Wilmington text PDFs were wrongly flagged before this.)"""
    if b"/Font" in data:
        return True
    for i, m in enumerate(re.finditer(rb"stream\r?\n", data)):
        if i >= max_streams:
            break
        end = data.find(b"endstream", m.end())
        if end < 0:
            break
        try:
            raw = zlib.decompressobj().decompress(data[m.end() : end], 2_000_000)
        except zlib.error:
            continue
        if b"/Font" in raw or re.search(rb"\)\s*Tj|\]\s*TJ", raw):
            return True
    return False


class _Text(HTMLParser):
    SKIP = {"script", "style", "noscript", "svg", "head"}
    BLOCK = {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "section", "table", "dd", "dt"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.skip += 1
        elif tag in self.BLOCK:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self.SKIP and self.skip:
            self.skip -= 1
        elif tag in self.BLOCK:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def html_to_text(html: str) -> str:
    p = _Text()
    p.feed(html)
    text = "".join(p.parts)
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    return re.sub(r"\n\s*\n+", "\n\n", text).strip()


def normalize(s: str) -> str:
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    s = s.replace("–", "-").replace("—", "-").replace(" ", " ")
    return re.sub(r"\s+", " ", s).strip().lower()


def quote_in_text(quote: str, text: str) -> bool:
    """The verifier's check that a quote is verbatim in the cached source (whitespace, quotes, dashes and
    case normalised; an ellipsis splits the quote into parts that must all appear in order)."""
    hay = normalize(text)
    pos = 0
    for part in re.split(r"\s*(?:\.\.\.|…)\s*", quote):
        part = normalize(part)
        if not part:
            continue
        i = hay.find(part, pos)
        if i < 0:
            return False
        pos = i + len(part)
    return True


# ---- fetching --------------------------------------------------------------------------------------------


def _wait_turn(store: DataStore, host: str, interval: float = MIN_INTERVAL) -> None:
    lock = store.root / ".ratelimit" / f"rule-agents-{host}"
    lock.parent.mkdir(parents=True, exist_ok=True)
    with lock.open("a+") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        fh.seek(0)
        last = float(fh.read().strip() or 0)
        wait = last + interval - time.time()
        if wait > 0:
            time.sleep(wait)
        fh.seek(0)
        fh.truncate()
        fh.write(f"{time.time():.3f}")
        fh.flush()
        fcntl.flock(fh, fcntl.LOCK_UN)


def cache_dir(store: DataStore, state: str, url: str) -> Path:
    host = httpx.URL(url).host or "unknown"
    return store.root / "raw" / "rule_agents" / "adu" / state.upper() / host


def _ext(ctype: str, url: str) -> str:
    if "pdf" in ctype or url.lower().endswith(".pdf"):
        return ".pdf"
    if "html" in ctype:
        return ".html"
    if "json" in ctype:
        return ".json"
    return ".bin"


class Fetcher:
    """One run's fetcher: caches robots.txt per host and refuses hosts that blocked earlier in the run."""

    def __init__(self, store: DataStore, state: str, http: httpx.Client | None = None, interval=MIN_INTERVAL):
        self.store, self.state, self.interval = store, state.upper(), interval
        self.http = http or httpx.Client(
            headers={"User-Agent": USER_AGENT}, timeout=60.0, follow_redirects=True
        )
        self._robots: dict[str, RobotFileParser | None] = {}
        self.blocked_hosts: dict[str, str] = {}

    def _robots_for(self, url: str) -> RobotFileParser | None:
        u = httpx.URL(url)
        key = f"{u.scheme}://{u.host}"
        if key not in self._robots:
            try:
                _wait_turn(self.store, u.host, self.interval)
                r = self.http.get(f"{key}/robots.txt")
                self._robots[key] = robots_parser(r.status_code, r.text)
            except httpx.HTTPError:
                self._robots[key] = robots_parser(None, "")
        return self._robots[key]

    def get(self, url: str) -> FetchResult:
        today = dt.date.today()
        host = httpx.URL(url).host
        if not url.startswith("https://"):
            return FetchResult(url, False, "not_https", detail="use the https page or a Wayback https copy")
        if host in self.blocked_hosts:
            return FetchResult(url, False, self.blocked_hosts[host], detail="host blocked earlier this run")
        rp = self._robots_for(url)
        if not robots_allows(rp, url):
            reason = "robots_disallow" if rp is not None else "robots_unavailable"
            return FetchResult(url, False, reason, detail=KNOWN_BLOCKERS.get(host, ""))
        _wait_turn(self.store, host, self.interval)
        try:
            resp = self.http.get(url)
        except httpx.HTTPError as exc:
            return FetchResult(url, False, "no_answer", detail=type(exc).__name__)
        ctype = resp.headers.get("content-type", "")
        head = resp.text[:200_000] if ("html" in ctype or resp.status_code >= 400) else ""
        reason = classify(resp.status_code, dict(resp.headers), head, str(resp.url))
        if reason:
            if reason in {"waf_challenge", "http_403", "rate_limited", "login_required"}:
                self.blocked_hosts[host] = reason  # never hammer a host that refused us
            return FetchResult(url, False, reason, resp.status_code, detail=KNOWN_BLOCKERS.get(host, ""))
        if len(resp.content) > MAX_BYTES:
            return FetchResult(url, False, "too_large", resp.status_code, detail=f"{len(resp.content)} bytes")
        folder = cache_dir(self.store, self.state, url)
        folder.mkdir(parents=True, exist_ok=True)
        stem = hashlib.sha1(url.encode()).hexdigest()[:16]
        dest = folder / (stem + _ext(ctype, url))
        dest.write_bytes(resp.content)
        self.store.record(
            ManifestEntry(
                url=url,
                path=str(dest.relative_to(self.store.root)),
                accessed_at=utc_now(),
                sha256=sha256_file(dest),
                bytes=dest.stat().st_size,
                source=f"rule_agents_adu_{self.state.lower()}",
                license="public record (local law); quoted for research",
                adapter="lotline.rule_agents.adu.fetch",
                adapter_version=HELPERS_VERSION,
                etag=resp.headers.get("ETag"),
                last_modified=resp.headers.get("Last-Modified"),
            )
        )
        result = FetchResult(url, True, None, resp.status_code, dest, None, ctype, today)
        result.doc_id = sha256_file(dest)
        if dest.suffix == ".pdf":
            if not pdf_has_text(resp.content):
                result.reason = "scanned_pdf"
                result.detail = "no text layer: read page images with the Read tool and say so, or hand off"
        elif dest.suffix == ".html":
            text = html_to_text(resp.text)
            result.text_path = dest.with_suffix(".txt")
            result.text_path.write_text(text)
        return result
