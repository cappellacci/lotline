"""Polite, cached HTTP downloads that land in the manifest."""

from __future__ import annotations

import fcntl
import time
from pathlib import Path

import httpx

from lotline import __version__
from lotline.io.store import DataStore, ManifestEntry, sha256_file, utc_now

USER_AGENT = f"lotline/{__version__} (+https://github.com/cappellacci/lotline; open-source housing research)"
RETRY_STATUS = {429, 500, 502, 503, 504}
# Minimum seconds between requests to these hosts, across every process sharing LOTLINE_DATA_DIR (parallel
# workstreams). census.gov blocked this project's network on 2026-10-19 after parallel TIGERweb downloads.
MIN_INTERVAL = {"census.gov": 1.0}


class RawOverwriteError(RuntimeError):
    """A download would overwrite a raw file that was downloaded from a different URL."""


def client(timeout: float = 60.0) -> httpx.Client:
    return httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=timeout, follow_redirects=True)


def fetch(
    url: str,
    dest: Path,
    *,
    store: DataStore,
    source: str,
    license: str,
    adapter: str,
    adapter_version: str,
    http: httpx.Client | None = None,
    refresh: bool = False,
    retries: int = 4,
    backoff: float = 2.0,
    secret_params: dict[str, str] | None = None,
) -> Path:
    """Download `url` to `dest` (under the store's raw/ tree) unless a cached copy is still current.

    A cached file is reused without a request unless `refresh` is set; with `refresh`, a conditional
    request (ETag / Last-Modified) avoids re-downloading unchanged files. Every new download appends
    a manifest entry with its sha256.

    `secret_params` (e.g. an API key) are added to the request only: the manifest, cache key and any error
    message use `url` without them.

    Raw files are kept exactly as downloaded, so a file already on disk that was downloaded from a different
    URL is never overwritten (or returned as this URL's cached copy): `RawOverwriteError` asks the caller to
    write to another path. Refreshing the same URL may update its file (the manifest keeps each hash).
    """
    dest = Path(dest)
    rel = str(dest.resolve().relative_to(store.root))
    owner = store.latest_for_path(rel)
    if dest.exists() and owner and owner.url != url:
        raise RawOverwriteError(
            f"{rel} holds a download from a different URL ({owner.url}); write {url} to another path "
            "(a new vintage or name) so the earlier raw file is kept"
        )
    prior = store.latest(url)
    if dest.exists() and prior and not refresh:
        return dest

    headers = {}
    if dest.exists() and prior:
        if prior.etag:
            headers["If-None-Match"] = prior.etag
        if prior.last_modified:
            headers["If-Modified-Since"] = prior.last_modified

    own = http is None
    http = http or client()
    try:
        _wait_turn(store, url)
        resp = _get_with_retries(http, url, headers, retries, backoff, secret_params or {})
    finally:
        if own:
            http.close()

    if resp.status_code == 304:
        return dest
    if resp.is_error:
        raise httpx.HTTPStatusError(f"HTTP {resp.status_code} for {url}", request=resp.request, response=resp)

    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    tmp.write_bytes(resp.content)
    tmp.replace(dest)

    store.record(
        ManifestEntry(
            url=url,
            path=rel,
            accessed_at=utc_now(),
            sha256=sha256_file(dest),
            bytes=dest.stat().st_size,
            source=source,
            license=license,
            adapter=adapter,
            adapter_version=adapter_version,
            etag=resp.headers.get("ETag"),
            last_modified=resp.headers.get("Last-Modified"),
        )
    )
    return dest


def _wait_turn(store: DataStore, url: str) -> None:
    """Space requests to rate-limited hosts (MIN_INTERVAL) using a lock file in the data directory, so the
    limit holds across processes."""
    host = httpx.URL(url).host
    domain = next((d for d in MIN_INTERVAL if host == d or host.endswith("." + d)), None)
    if domain is None:
        return
    lock = store.root / ".ratelimit" / domain
    lock.parent.mkdir(parents=True, exist_ok=True)
    with lock.open("a+") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)  # one process at a time decides when to send
        fh.seek(0)
        last = float(fh.read().strip() or 0)
        wait = last + MIN_INTERVAL[domain] - time.time()
        if wait > 0:
            time.sleep(wait)
        fh.seek(0)
        fh.truncate()
        fh.write(f"{time.time():.3f}")
        fh.flush()
        fcntl.flock(fh, fcntl.LOCK_UN)


def _get_with_retries(
    http: httpx.Client, url: str, headers: dict, retries: int, backoff: float, secret_params: dict[str, str]
) -> httpx.Response:
    for attempt in range(retries + 1):
        try:
            resp = http.get(httpx.URL(url).copy_merge_params(secret_params), headers=headers)
        except httpx.TransportError as exc:
            if attempt == retries:
                raise httpx.TransportError(f"{type(exc).__name__} for {url}") from None
        else:
            if resp.status_code not in RETRY_STATUS or attempt == retries:
                return resp
        time.sleep(backoff * 2**attempt)
    raise AssertionError("unreachable")
