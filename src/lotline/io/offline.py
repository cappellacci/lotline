"""Offline builds: rebuild processed tables from raw files already in LOTLINE_DATA_DIR, sending no request.

`lotline fetch --offline` runs every adapter inside `offline_build(store)`. While it is active:

- `fetch()` returns the cached copy of a URL (the file at `dest`, or else the newest current manifest entry
  for that URL whose file is still on disk) and never sends a request. No cached copy is an `OfflineError`.
- The ArcGIS and Socrata pagers read one whole cached snapshot instead of paging the server. With no vintage
  given (or today's date, the usual default), that is the **newest complete** snapshot of the same query
  (same `q-<hash>` folder) under `raw/<source>/<vintage>/<name>/`. A newer snapshot with missing pages
  (checked against its own `layer.json` / `object_ids.json`) is skipped with a note saying so. Pages are never
  mixed across snapshots. An explicit other vintage is read as is, or fails.
- `client()` returns an HTTP client whose transport refuses every request, so an adapter that calls the
  network directly fails loudly instead of going online.

What each build read is appended to `manifest.builds.jsonl` (one line per state and source: mode, the
snapshot folders or files used, and any incomplete snapshots skipped). Like the supersede file it sits next
to `manifest.jsonl` rather than inside it, so readers of the download manifest are unchanged.
"""

from __future__ import annotations

import datetime as dt
import json
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import asdict, dataclass, field
from pathlib import Path

from lotline import __version__
from lotline.io.store import DataStore, utc_now


class OfflineError(RuntimeError):
    """An offline build needed something that is not in the cache. Nothing was downloaded."""


class SnapshotIncomplete(OfflineError):
    """A cached snapshot is missing a page its own layer/ID record says it should have."""


@dataclass
class OfflineSession:
    """What one offline build read: snapshot folders / files, and notes about snapshots it skipped."""

    store: DataStore
    used: list[str] = field(default_factory=list)  # paths relative to the data dir
    notes: list[str] = field(default_factory=list)

    def used_path(self, path: Path) -> None:
        rel = _rel(self.store, path)
        if rel not in self.used:
            self.used.append(rel)

    def note(self, text: str) -> None:
        self.notes.append(text)

    def record(self, *, state: str, source: str) -> BuildRecord:
        """Append one build record for what was read since the last record, then start afresh."""
        rec = BuildRecord(
            built_at=utc_now(),
            mode="offline",
            state=state,
            source=source,
            snapshots=list(self.used),
            skipped=list(self.notes),
            lotline_version=__version__,
        )
        path = builds_path(self.store)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a") as fh:
            fh.write(json.dumps(asdict(rec), sort_keys=True) + "\n")
        self.used.clear()
        self.notes.clear()
        return rec


@dataclass(frozen=True)
class BuildRecord:
    built_at: str
    mode: str  # "offline"
    state: str
    source: str
    snapshots: list[str]  # raw snapshot folders (paged sources) or files (plain downloads) that were read
    skipped: list[str]  # incomplete or mismatched snapshots passed over, with the reason
    lotline_version: str


_SESSION: ContextVar[OfflineSession | None] = ContextVar("lotline_offline", default=None)


def session() -> OfflineSession | None:
    """The active offline build, or None when downloads are allowed."""
    return _SESSION.get()


def is_offline() -> bool:
    return _SESSION.get() is not None


@contextmanager
def offline_build(store: DataStore) -> Iterator[OfflineSession]:
    """Run the enclosed code with every download served from the cache and the network refused."""
    token = _SESSION.set(OfflineSession(store))
    try:
        yield _SESSION.get()  # type: ignore[misc]
    finally:
        _SESSION.reset(token)


def builds_path(store: DataStore) -> Path:
    return store.root / "manifest.builds.jsonl"


def read_builds(store: DataStore) -> list[BuildRecord]:
    path = builds_path(store)
    if not path.exists():
        return []
    return [BuildRecord(**json.loads(line)) for line in path.read_text().splitlines() if line.strip()]


def candidate_dirs(
    store: DataStore, source: str, name: str, vintage: str | None, marker: str, url: str
) -> Iterator[Path]:
    """`raw/<source>/<vintage>/<name>/` folders to try, newest vintage first.

    With no vintage, or today's (the usual default), every vintage folder holding `<name>/<marker>` is a
    candidate; otherwise only the vintage asked for. A folder whose marker file (`layer.json`,
    `dataset.json`) was downloaded from a different URL, or is not in the manifest, is skipped with a note,
    so a same-named query of another layer is never read by mistake.
    """
    sess = session()
    if vintage and vintage != dt.date.today().isoformat():
        vintages = [str(vintage)]
    else:
        base = store.root / "raw" / source
        vintages = (
            sorted((p.name for p in base.iterdir() if p.is_dir()), reverse=True) if base.is_dir() else []
        )
    for v in vintages:
        folder = store.raw(source, v) / name
        marker_path = folder / marker
        if not marker_path.is_file():
            continue
        owner = store.latest_for_path(_rel(store, marker_path))
        if owner is None or owner.url != url:
            if sess:
                why = "not in the manifest" if owner is None else f"downloaded from {owner.url}"
                sess.note(f"{_rel(store, marker_path)}: skipped, {why} (expected {url})")
            continue
        yield folder


def read_cached(path: Path) -> dict | list:
    """A cached raw JSON page, or `SnapshotIncomplete` if it is missing or not usable. Never deletes it."""
    if not path.is_file():
        raise SnapshotIncomplete(f"{path.parent.name}/{path.name} is missing")
    try:
        data = json.loads(path.read_text())
    except ValueError:
        raise SnapshotIncomplete(f"{path.parent.name}/{path.name} is not JSON") from None
    if isinstance(data, dict) and "error" in data:
        raise SnapshotIncomplete(f"{path.parent.name}/{path.name} holds an error body")
    return data


def _rel(store: DataStore, path: Path) -> str:
    return str(Path(path).resolve().relative_to(store.root))


def prune_candidates(store: DataStore) -> list[tuple[str, int, str]]:
    """Older snapshot folders a newer vintage repeats: (folder, bytes, newer folder). Deletes nothing.

    A `raw/<source>/<vintage>/<name>/q-<hash>/` folder is listed when a later vintage of the same source and
    name holds the same `q-<hash>` with at least as many pages. Whether to delete it (and supersede its
    manifest entries) is left to a person: an old snapshot may be the record behind a frozen result.
    """
    raw = store.root / "raw"
    groups: dict[tuple[str, str, str], list[Path]] = {}
    for q in raw.glob("*/*/*/q-*") if raw.is_dir() else []:
        if q.is_dir():
            source, _vintage, name = q.relative_to(raw).parts[:3]
            groups.setdefault((source, name, q.name), []).append(q)
    out = []
    for folders in groups.values():
        folders.sort(key=lambda p: p.parent.parent.name, reverse=True)
        newest, pages = folders[0], len(list(folders[0].glob("page_*.json")))
        for old in folders[1:]:
            if len(list(old.glob("page_*.json"))) <= pages:
                size = sum(f.stat().st_size for f in old.rglob("*") if f.is_file())
                out.append((_rel(store, old), size, _rel(store, newest)))
    return sorted(out)
