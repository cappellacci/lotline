"""Data directory layout and the append-only download manifest.

$LOTLINE_DATA_DIR/
  raw/{source}/{vintage}/...          exactly as downloaded, never edited
  interim/{state}/...                 parsed, typed
  processed/{state}/{table}.parquet   canonical tables
  manifest.jsonl                      one line per download
  manifest.superseded.jsonl           one line per download entry marked as no longer current
  manual/...                          (optional) files saved by hand before `lotline manifest register`

Both files are append-only: nothing is ever deleted from them. An entry that no longer describes the file
on disk (the same path was downloaded again under a different URL, or an exploratory pull was redone) is
marked superseded in the second file, with a reason, instead of being removed from the first. Supersede
records live in their own file so that older code reading `manifest.jsonl` keeps working.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

DEFAULT_DATA_DIR = "~/lotline-data"


def data_dir() -> Path:
    """Resolve LOTLINE_DATA_DIR (env var, then .env in the working directory, then ~/lotline-data)."""
    value = os.environ.get("LOTLINE_DATA_DIR") or _dotenv_value("LOTLINE_DATA_DIR") or DEFAULT_DATA_DIR
    return Path(value).expanduser().resolve()


def _dotenv_value(key: str, path: Path = Path(".env")) -> str | None:
    if not path.is_file():
        return None
    for line in path.read_text().splitlines():
        name, sep, value = line.partition("=")
        if sep and name.strip() == key and value.strip():
            return value.strip().strip("'\"")
    return None


@dataclass(frozen=True)
class ManifestEntry:
    url: str
    path: str  # relative to the data dir
    accessed_at: str  # ISO 8601, UTC
    sha256: str
    bytes: int
    source: str
    license: str
    adapter: str
    adapter_version: str
    etag: str | None = None
    last_modified: str | None = None


def entry_key(entry: ManifestEntry) -> tuple[str, str, str]:
    """What identifies one download: the file it wrote, its hash and when it happened."""
    return (entry.path, entry.sha256, entry.accessed_at)


@dataclass(frozen=True)
class Supersession:
    """A record that one manifest entry is no longer current. The entry itself stays in the manifest."""

    path: str
    sha256: str
    accessed_at: str
    source: str
    reason: str
    superseded_at: str  # ISO 8601, UTC

    @property
    def key(self) -> tuple[str, str, str]:
        return (self.path, self.sha256, self.accessed_at)


class DataStore:
    """Paths and manifest for one data directory."""

    def __init__(self, root: Path | None = None):
        self.root = (root or data_dir()).expanduser().resolve()

    def raw(self, source: str, vintage: str | int) -> Path:
        return self.root / "raw" / source / str(vintage)

    def interim(self, state: str) -> Path:
        return self.root / "interim" / state.lower()

    def processed(self, state: str, table: str, source: str | None = None) -> Path:
        """Folder holding a canonical table (read it whole with pandas.read_parquet), or one source's file."""
        folder = self.root / "processed" / state.lower() / table
        return folder / f"{source}.parquet" if source else folder

    def read(self, state: str, table: str) -> pd.DataFrame | None:
        """A processed table, combining every source's file (`processed/<st>/<table>/*.parquet`).

        Use this instead of `pandas.read_parquet(folder)`: reading the folder as one dataset keeps only the
        first file's columns, so e.g. FRED's `cpi_u` vanishes from `market_geo_year`. Here each file is read
        on its own and rows are stacked with the union of columns. Returns None if the table isn't built.
        """
        files = sorted(self.processed(state, table).glob("*.parquet"))
        if not files:
            return None
        return pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)

    @property
    def manifest_path(self) -> Path:
        return self.root / "manifest.jsonl"

    def record(self, entry: ManifestEntry) -> None:
        """Append one line to the manifest. Never rewrites earlier lines."""
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        with self.manifest_path.open("a") as fh:
            fh.write(json.dumps(asdict(entry), sort_keys=True) + "\n")

    def manifest(self, *, include_superseded: bool = True) -> list[ManifestEntry]:
        """Every download entry, in the order recorded; `include_superseded=False` drops superseded ones."""
        if not self.manifest_path.exists():
            return []
        lines = self.manifest_path.read_text().splitlines()
        entries = [ManifestEntry(**json.loads(line)) for line in lines if line.strip()]
        if include_superseded:
            return entries
        gone = {s.key for s in self.supersessions()}
        return [e for e in entries if entry_key(e) not in gone]

    @property
    def superseded_path(self) -> Path:
        return self.root / "manifest.superseded.jsonl"

    def supersessions(self) -> list[Supersession]:
        if not self.superseded_path.exists():
            return []
        lines = self.superseded_path.read_text().splitlines()
        return [Supersession(**json.loads(line)) for line in lines if line.strip()]

    def supersede(self, entries: list[ManifestEntry], reason: str) -> list[Supersession]:
        """Mark manifest entries as no longer current (append-only). Returns the records written.

        Entries already superseded are skipped; an entry that isn't in the manifest raises ValueError.
        """
        if not reason.strip():
            raise ValueError("a reason is required to supersede manifest entries")
        known = {entry_key(e) for e in self.manifest()}
        done = {s.key for s in self.supersessions()}
        stamp = utc_now()
        written = []
        for e in entries:
            if entry_key(e) not in known:
                raise ValueError(f"not in the manifest: {e.path} ({e.accessed_at})")
            if entry_key(e) in done:
                continue
            done.add(entry_key(e))
            written.append(Supersession(e.path, e.sha256, e.accessed_at, e.source, reason.strip(), stamp))
        if written:
            with self.superseded_path.open("a") as fh:
                for s in written:
                    fh.write(json.dumps(asdict(s), sort_keys=True) + "\n")
        return written

    def register(
        self,
        file: Path,
        *,
        source: str,
        url: str,
        license: str,
        vintage: str,
        adapter: str = "manual_export",
        adapter_version: str = "1",
    ) -> ManifestEntry:
        """Record a file downloaded by hand (e.g. in a browser) as a raw download, append-only.

        The file is linked (or copied, across file systems) to `raw/<source>/<vintage>/<file name>` so manual
        downloads sit where every other raw file does; the original stays where it was. `url` is the page or
        link it came from; `accessed_at` is the file's modification time (when it was saved). Registering the
        same file again is a no-op; a different file under the same name is refused.
        """
        file = Path(file).expanduser().resolve()
        if not file.is_file():
            raise FileNotFoundError(file)
        dest = self.raw(source, vintage) / file.name
        rel = str(dest.relative_to(self.root))
        digest = sha256_file(file)
        known = self.latest_for_path(rel)
        if dest.exists():
            if sha256_file(dest) != digest:
                raise FileExistsError(f"{rel} already holds a different file; use another vintage or name")
            if known and known.sha256 == digest:
                return known  # already registered
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            try:
                os.link(file, dest)  # no second copy of a large download
            except OSError:
                shutil.copy2(file, dest)
        stamp = datetime.fromtimestamp(file.stat().st_mtime, UTC).replace(microsecond=0).isoformat()
        entry = ManifestEntry(
            url=url,
            path=rel,
            accessed_at=stamp,
            sha256=digest,
            bytes=dest.stat().st_size,
            source=source,
            license=license,
            adapter=adapter,
            adapter_version=adapter_version,
        )
        self.record(entry)
        return entry

    def registered(self, source: str) -> list[ManifestEntry]:
        """Current manifest entries of hand-downloaded files for `source` (see `register`), in order."""
        return [
            e
            for e in self.manifest(include_superseded=False)
            if e.source == source and e.adapter == "manual_export"
        ]

    def is_stale(self, entry: ManifestEntry) -> bool:
        """True when the entry's file is missing or no longer has the recorded sha256."""
        path = self.root / entry.path
        return not path.is_file() or sha256_file(path) != entry.sha256

    def latest_for_path(self, path: str) -> ManifestEntry | None:
        """Most recent current (not superseded) manifest entry for the file at `path` (relative), if any."""
        hits = [e for e in self.manifest(include_superseded=False) if e.path == path]
        return hits[-1] if hits else None

    def latest(self, url: str) -> ManifestEntry | None:
        """Most recent manifest entry for `url`, if any."""
        hits = [e for e in self.manifest() if e.url == url]
        return hits[-1] if hits else None


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()
