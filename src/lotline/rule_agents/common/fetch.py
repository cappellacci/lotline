"""Polite, store-first fetching for every rule swarm.

`get(url, category, run_id)`:

0. **Store first.** If the document store already holds this URL (any swarm, any run), return that document
   with no network request (`cached=True`). Pass `refresh=True` only to look for a newer version.
1. **Known refusal.** If this URL, or its host for a host-wide refusal, refused any swarm in the last 30 days
   (`DocStore.recent_block`), return the same blocker with no request.
2. **robots.txt** is read once per host per day (cached under `rule_docs/_robots/`) and the URL is refused
   if robots disallows it for any of our agent tokens (`AGENT_TOKENS`: the project's user agent and Claude's
   fetch tokens, since agents may also read pages with WebFetch). A 5xx or no answer for robots.txt counts as
   disallowed (RFC 9309); a 401/403 closes the host.
3. **One request**, spaced `HOST_INTERVAL` seconds per host across processes, through `lotline.io.http.fetch`
   (so it is in `manifest.jsonl`). A 403 is never retried, and **never retried with another user agent, curl
   or browser-like headers** (Oct 2026 incident: docs/build/rule-agents/mm/LESSONS.md, R-5).
   Redirects are followed; the URL that actually answered is kept (`final_url`), and for the Wayback Machine
   its 14-digit capture time (`wayback_ts`): `/web/2023/<url>` redirects to the nearest capture, which can
   be from another year, so a coder dates the text by `wayback_ts`, never by the year in the link.
4. **Ingest**: the file goes into the document store (blob, text sidecar, index event) and the result is
   classified (`access.classify`). Any blocker is recorded in `blocks.jsonl` for every swarm to see.

Moved from the MM swarm's `mm/fetch.py` (master) when the shared core was built, 2026-11-17.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import re
import time
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

import httpx

from lotline.rule_agents.common.access import classify, robots_allows, robots_url
from lotline.rule_agents.common.docstore import DocStore, sniff_ext

AGENT_TOKENS = ("lotline", "Claude-User", "ClaudeBot", "anthropic-ai")
HOST_INTERVAL = 3.0  # seconds between requests to one host, across processes
SOURCE = "rule_docs"
ADAPTER = "rule_agents.common.fetch"
ADAPTER_VERSION = "1.0"
_WAYBACK = re.compile(r"^https?://web\.archive\.org/web/(\d{14})")
_EXTS = (".pdf", ".htm", ".html", ".txt", ".json", ".xml", ".csv", ".xlsx", ".docx")


@dataclass
class FetchResult:
    url: str
    path: Path | None  # the stored blob (None when blocked before any download)
    status: int | None
    blocker: str | None = None  # evidence.BLOCKER_KINDS
    detail: str = ""
    doc_id: str | None = None
    cached: bool = False  # served from the document store, no request made
    pages: int | None = None
    text_status: str = ""
    final_url: str | None = None  # the URL that answered, when a redirect took the request elsewhere
    wayback_ts: str | None = None  # 14-digit Wayback capture actually served

    def to_json(self) -> str:
        d = asdict(self)
        d["path"] = str(self.path) if self.path else None
        return json.dumps(d)


def allowed(robots_txt: str | None, url: str) -> bool:
    """robots.txt allows `url` for every token in AGENT_TOKENS (a block for any one is a block)."""
    return all(robots_allows(robots_txt, url, ua) for ua in AGENT_TOKENS)


def snapshot_name(url: str) -> str:
    """A stable file name for a URL: host, a 12-character hash, and the URL's extension (else .html)."""
    p = urlparse(url)
    ext = Path(p.path).suffix.lower()
    ext = ext if ext in _EXTS else ".html"
    h = hashlib.sha1(url.encode()).hexdigest()[:12]
    return f"{p.hostname}/{h}{ext}"


def wayback_ts(url: str | None) -> str | None:
    """The 14-digit capture time in a Wayback URL: '.../web/20230115083000/https://x' -> '20230115083000';
    a year-only '.../web/2023/https://x' -> None (it is not a capture, only a request for the nearest one)."""
    m = _WAYBACK.match(url or "")
    return m.group(1) if m else None


def wayback_url(url: str, when: str = "2") -> str:
    """The Wayback address for `url`; `when` is a year or a 14-digit capture ('2' = latest capture)."""
    return f"https://web.archive.org/web/{when}/{url}"


def _wait(root: Path, host: str) -> None:
    lock = root / ".ratelimit" / f"rule-agents-{host}"
    lock.parent.mkdir(parents=True, exist_ok=True)
    with lock.open("a+") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        fh.seek(0)
        last = float(fh.read().strip() or 0)
        wait = last + HOST_INTERVAL - time.time()
        if wait > 0:
            time.sleep(wait)
        fh.seek(0)
        fh.truncate()
        fh.write(f"{time.time():.3f}")
        fcntl.flock(fh, fcntl.LOCK_UN)


def _robots(docs: DocStore, url: str, http: httpx.Client) -> tuple[str | None, str | None]:
    """(robots text or None, blocker kind or None), cached per host per day."""
    host = urlparse(url).hostname or ""
    cache = docs.root / "_robots" / date.today().isoformat() / f"{host}.json"
    if cache.exists():
        c = json.loads(cache.read_text())
        return c["text"], c["blocker"]
    _wait(docs.data_root, host)
    text, blocker = None, None
    try:
        r = http.get(robots_url(url))
        if r.status_code == 200:
            text = r.text
        elif r.status_code in (401, 403):
            blocker = "http_403_waf"
        elif r.status_code >= 500:
            blocker = "robots_unavailable"
    except httpx.TransportError:
        blocker = "robots_unavailable"
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps({"text": text, "blocker": blocker}))
    return text, blocker


def _result(docs: DocStore, url: str, rec, status, cached) -> FetchResult:
    return FetchResult(
        url,
        docs.root / rec.path,
        status,
        doc_id=rec.doc_id,
        cached=cached,
        pages=rec.pages,
        text_status=rec.text_status,
        final_url=rec.served_url or None,
        wayback_ts=rec.wayback_ts or wayback_ts(url),
    )


def get(
    url: str,
    category: str,
    run_id: str,
    *,
    refresh: bool = False,
    docs: DocStore | None = None,
    http: httpx.Client | None = None,
    **facts,
) -> FetchResult:
    """Fetch one URL politely into the document store. `facts` (jurisdictions, doc_type, title...) are
    recorded on the document."""
    from lotline.io import http as lhttp
    from lotline.io.store import DataStore

    docs = docs or DocStore()
    if not url.startswith("https://") and not url.startswith("http://"):
        return FetchResult(url, None, None, "not_found", "not an http(s) URL")
    if not refresh:
        held = docs.by_url(url)
        if held is not None:
            docs.annotate(held.doc_id, categories=[category], **{k: v for k, v in facts.items() if v})
            return _result(docs, url, held, 200, True)
    prior = docs.recent_block(url)
    if prior is not None:
        return FetchResult(
            url, None, None, prior["kind"], f"refused on {prior['at'][:10]}: {prior['detail']}"
        )

    host = urlparse(url).hostname or ""
    own = http is None
    http = http or lhttp.client(timeout=30)
    try:
        robots, rblock = _robots(docs, url, http)
        if rblock:
            detail = f"robots.txt at {robots_url(url)}: " + (
                "refused" if rblock == "http_403_waf" else "no answer"
            )
            docs.record_block(url, rblock, detail, category)
            return FetchResult(url, None, None, rblock, detail)
        if not allowed(robots, url):
            detail = f"robots.txt at {robots_url(url)}"
            docs.record_block(url, "robots_disallow", detail, category)
            return FetchResult(url, None, None, "robots_disallow", detail)
        store = DataStore(docs.data_root)
        dest = store.raw(SOURCE, date.today().isoformat()) / snapshot_name(url)
        _wait(docs.data_root, host)
        served: list[str] = []  # every response's URL; the last is the one that answered

        def _note(resp: httpx.Response) -> None:
            served.append(str(resp.url))

        http.event_hooks["response"].append(_note)
        try:
            path = lhttp.fetch(
                url,
                dest,
                store=store,
                source=SOURCE,
                license="public record (local government publication)",
                adapter=ADAPTER,
                adapter_version=ADAPTER_VERSION,
                http=http,
                retries=0,
                refresh=refresh,
            )
        except httpx.HTTPStatusError as exc:
            st = exc.response.status_code
            kind, detail = classify(url, st, text=exc.response.text) or ("not_found", f"HTTP {st}")
            docs.record_block(url, kind, detail, category)
            if st in (404, 410) and not wayback_ts(url) and "web.archive.org" not in url:
                # Sites are redesigned and old file links die; the archived copy is often still there.
                detail += f"; try the archived copy {wayback_url(url)} (ask for an exact 14-digit capture)"
            return FetchResult(url, None, st, kind, detail)
        except httpx.TransportError as exc:
            docs.record_block(url, "unreachable", str(exc)[:200], category)
            return FetchResult(url, None, None, "unreachable", f"transport error: {exc}")
        finally:
            http.event_hooks["response"].remove(_note)
        final = served[-1] if served else url
        if final != url:
            facts = {**facts, "served_url": final}
        if wayback_ts(final):
            facts = {**facts, "wayback_ts": wayback_ts(final)}
        if sniff_ext(path) != ".pdf":
            # A wall (login form, bot challenge, code-host shell) is a result, not a document: record it and
            # keep it out of the store, so it is never offered as "already held" (a news site's login page
            # was stored as a fee schedule in the Burlington VT proof of concept, 2026-11-19).
            wall = classify(url, 200, content_type="text/html", text=path.read_text(errors="replace"))
            if wall:
                docs.record_block(url, wall[0], wall[1], category)
                return FetchResult(url, None, 200, wall[0], wall[1])
        rec = docs.ingest(path, url=url, added_by=f"run:{category}:{run_id}", category=category, **facts)
        if rec.ext == ".pdf":
            hit = (
                ("scanned_pdf", f"no text layer on {rec.pages} page(s)")
                if rec.text_status == "scanned"
                else None
            )
        else:
            hit = None  # walls were caught before ingest
        res = _result(docs, url, rec, 200, False)
        if hit:
            res.blocker, res.detail = hit
            if hit[0] != "scanned_pdf":  # a scan is held and readable by eye; walls are recorded
                docs.record_block(url, hit[0], hit[1], category)
        return res
    finally:
        if own:
            http.close()
