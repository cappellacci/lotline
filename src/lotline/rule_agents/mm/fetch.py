"""Polite fetching for the retrieval agent: robots first, one try, save a snapshot, classify the result.

`get(url, run_id)`:

1. Reads the host's robots.txt (cached per host per run) and refuses the URL if robots disallows it for any
   of our agent tokens (`AGENT_TOKENS`: the project's own user agent and Claude's fetch tokens, because the
   same swarm may also read pages with Claude Code's WebFetch). A refusal is a `robots_disallow` blocker.
2. Waits its turn: at most one request per `HOST_INTERVAL` seconds to any one host, across processes.
3. Downloads once through `lotline.io.http.fetch` (so the file lands under `LOTLINE_DATA_DIR/raw/rules_mm/
   <run_id>/` and in `manifest.jsonl`). The shared client retries only 429/5xx with backoff; a 403 is never
   retried, and **never retried with another user agent, curl or a browser-like header** (an Oct 2026
   incident: docs/build/rule-agents/mm/LESSONS.md, R-5).
4. Classifies the result with `access.classify` and returns a `FetchResult` (path to the snapshot or the
   blocker). The snapshot path is what evidence entries cite.
"""

from __future__ import annotations

import fcntl
import hashlib
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import httpx

from lotline.rule_agents.mm.access import classify, robots_allows, robots_url

AGENT_TOKENS = ("lotline", "Claude-User", "ClaudeBot", "anthropic-ai")
HOST_INTERVAL = 3.0  # seconds between requests to one host
ADAPTER = "rule_agents.mm"
ADAPTER_VERSION = "0.1"


@dataclass
class FetchResult:
    url: str
    path: Path | None  # the saved snapshot (None when blocked)
    status: int | None
    blocker: str | None = None  # access.BLOCKER kind
    detail: str = ""
    doc_id: str | None = None  # sha256 of the saved bytes: the document's stable ID (SHARED_CANDIDATES §10)


def allowed(robots_txt: str | None, url: str) -> bool:
    """robots.txt allows `url` for every token in AGENT_TOKENS (a block for any one is a block)."""
    return all(robots_allows(robots_txt, url, ua) for ua in AGENT_TOKENS)


def snapshot_name(url: str) -> str:
    """A stable file name for a URL: host, a 12-character hash, and the URL's extension (else .html)."""
    p = urlparse(url)
    ext = Path(p.path).suffix.lower()
    ext = ext if ext in (".pdf", ".htm", ".html", ".txt", ".json", ".xml") else ".html"
    h = hashlib.sha1(url.encode()).hexdigest()[:12]
    return f"{p.hostname}/{h}{ext}"


def _wait(root: Path, host: str) -> None:
    lock = root / ".ratelimit" / f"rules-mm-{host}"
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


def get(url: str, run_id: str, *, store=None, http: httpx.Client | None = None) -> FetchResult:
    """Fetch one URL politely (network; exercised in dry runs, not unit tests)."""
    from lotline.io import http as lhttp
    from lotline.io.store import DataStore, sha256_file

    store = store or DataStore()
    host = urlparse(url).hostname or ""
    rcache = store.raw("rules_mm", run_id) / "_robots" / f"{host}.txt"
    own = http is None
    http = http or lhttp.client(timeout=30)
    try:
        if rcache.exists():
            txt = rcache.read_text()
            robots = None if txt == "__none__" else txt
        else:
            _wait(store.root, host)
            r = http.get(robots_url(url))
            robots = r.text if r.status_code == 200 else None
            if r.status_code in (401, 403):
                # robots.txt itself refused: treat the host as closed to scripts
                return FetchResult(url, None, r.status_code, "http_403_waf", "robots.txt refused (HTTP 403)")
            rcache.parent.mkdir(parents=True, exist_ok=True)
            rcache.write_text(robots if robots is not None else "__none__")
        if not allowed(robots, url):
            return FetchResult(url, None, None, "robots_disallow", f"robots.txt at {robots_url(url)}")
        dest = store.raw("rules_mm", run_id) / snapshot_name(url)
        _wait(store.root, host)
        try:
            path = lhttp.fetch(
                url,
                dest,
                store=store,
                source=f"rules_mm:{host}",
                license="public record (local government publication)",
                adapter=ADAPTER,
                adapter_version=ADAPTER_VERSION,
                http=http,
                retries=2,
            )
        except httpx.HTTPStatusError as exc:
            st = exc.response.status_code
            kind, detail = classify(url, st, text=exc.response.text) or ("not_found", f"HTTP {st}")
            return FetchResult(url, None, st, kind, detail)
        except httpx.TransportError as exc:
            return FetchResult(url, None, None, "unreachable", f"transport error: {exc}")
        ctype = "application/pdf" if path.suffix == ".pdf" else "text/html"
        text = "" if path.suffix == ".pdf" else path.read_text(errors="replace")
        hit = classify(url, 200, content_type=ctype, text=text)
        doc = sha256_file(path)
        if hit:
            return FetchResult(url, path, 200, hit[0], hit[1], doc_id=doc)
        return FetchResult(url, path, 200, doc_id=doc)
    finally:
        if own:
            http.close()
