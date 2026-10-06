"""Data directory layout and the append-only download manifest.

$LOTLINE_DATA_DIR/
  raw/{source}/{vintage}/...          exactly as downloaded, never edited
  interim/{state}/...                 parsed, typed
  processed/{state}/{table}.parquet   canonical tables
  manifest.jsonl                      one line per download
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

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

    @property
    def manifest_path(self) -> Path:
        return self.root / "manifest.jsonl"

    def record(self, entry: ManifestEntry) -> None:
        """Append one line to the manifest. Never rewrites earlier lines."""
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        with self.manifest_path.open("a") as fh:
            fh.write(json.dumps(asdict(entry), sort_keys=True) + "\n")

    def manifest(self) -> list[ManifestEntry]:
        if not self.manifest_path.exists():
            return []
        lines = self.manifest_path.read_text().splitlines()
        return [ManifestEntry(**json.loads(line)) for line in lines if line.strip()]

    def latest(self, url: str) -> ManifestEntry | None:
        """Most recent manifest entry for `url`, if any."""
        hits = [e for e in self.manifest() if e.url == url]
        return hits[-1] if hits else None


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()
