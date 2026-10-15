"""Superseding manifest entries (append-only) and counting each downloaded file once in provenance."""

import json

import pytest

from lotline import provenance
from lotline.adapters.national import fred
from lotline.cli import main
from lotline.io.store import DataStore, ManifestEntry, sha256_file

SRC = fred.SOURCE


def _write(store, rel, text, url, accessed_at, license="Public domain"):
    """Write a raw file and record its download, as fetch() would."""
    path = store.root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    entry = ManifestEntry(
        url=url,
        path=rel,
        accessed_at=accessed_at,
        sha256=sha256_file(path),
        bytes=path.stat().st_size,
        source=SRC,
        license=license,
        adapter="national.fred",
        adapter_version="1.0",
    )
    store.record(entry)
    return entry


@pytest.fixture
def store(tmp_path):
    """Same file downloaded twice under different URLs (an exploratory pull, then the adapter's own), plus a
    second file downloaded once. The first pull's license text differs, as in the Durham case."""
    s = DataStore(tmp_path)
    _write(s, f"raw/{SRC}/2026-10/a.json", "old", "https://x/a?fields=*", "2026-10-14T22:25:00+00:00", "Old")
    _write(s, f"raw/{SRC}/2026-10/a.json", "new", "https://x/a?fields=id", "2026-10-14T23:00:00+00:00")
    _write(s, f"raw/{SRC}/2026-10/b.json", "bee", "https://x/b", "2026-10-14T23:00:01+00:00")
    return s


def test_provenance_counts_each_file_once(store):
    files = provenance.current_files(store.manifest())
    assert [(e.path, e.url) for e in files] == [
        (f"raw/{SRC}/2026-10/a.json", "https://x/a?fields=id"),
        (f"raw/{SRC}/2026-10/b.json", "https://x/b"),
    ]
    doc = provenance.render(store.manifest())
    assert "**Files:** 2 (0.0 MB)" in doc
    assert "Old" not in doc  # the overwritten download's license text no longer shows


def test_is_stale_when_file_changed_or_missing(store):
    first, second, third = store.manifest()
    assert store.is_stale(first) and not store.is_stale(second)
    (store.root / third.path).unlink()
    assert store.is_stale(third)


def test_supersede_appends_and_never_touches_the_manifest(store):
    before = store.manifest_path.read_bytes()
    first = store.manifest()[0]
    written = store.supersede([first], "re-downloaded with the adapter's field list")
    assert len(written) == 1 and written[0].key == (first.path, first.sha256, first.accessed_at)
    assert store.manifest_path.read_bytes() == before  # manifest.jsonl unchanged
    assert len(store.manifest()) == 3
    assert first not in store.manifest(include_superseded=False)
    assert store.supersede([first], "again") == []  # already superseded: nothing new written
    lines = store.superseded_path.read_text().splitlines()
    assert len(lines) == 1 and json.loads(lines[0])["reason"].startswith("re-downloaded")


def test_supersede_needs_a_reason_and_a_known_entry(store):
    first = store.manifest()[0]
    with pytest.raises(ValueError, match="reason"):
        store.supersede([first], "  ")
    stranger = ManifestEntry(**{**first.__dict__, "accessed_at": "1999-01-01T00:00:00+00:00"})
    with pytest.raises(ValueError, match="not in the manifest"):
        store.supersede([stranger], "x")


def test_provenance_leaves_superseded_entries_out(store, tmp_path):
    doc = tmp_path / "prov.md"
    b = store.manifest()[2]
    (store.root / b.path).write_text("changed")  # b's only entry is now stale
    store.supersede([b], "file replaced by hand")
    provenance.write(store, doc)
    assert "**Files:** 1 (0.0 MB)" in doc.read_text()
    assert provenance.check(store, doc) == []


def test_cli_dry_run_then_apply(store, monkeypatch, capsys):
    monkeypatch.setenv("LOTLINE_DATA_DIR", str(store.root))
    args = ["manifest", "supersede", "--source", SRC, "--stale", "--reason", "overwritten by a later pull"]
    assert main(args) == 0
    assert "1 entry selected" in capsys.readouterr().out and not store.superseded_path.exists()
    assert main([*args, "--apply"]) == 0
    assert [s.path for s in store.supersessions()] == [f"raw/{SRC}/2026-10/a.json"]


def test_cli_never_supersedes_the_intact_record_of_a_file(store, monkeypatch, capsys):
    monkeypatch.setenv("LOTLINE_DATA_DIR", str(store.root))
    args = ["manifest", "supersede", "--source", SRC, "--before", "2027", "--reason", "x", "--apply"]
    assert main(args) == 0
    assert "2 kept because they are the current, intact record" in capsys.readouterr().out
    assert [s.path for s in store.supersessions()] == [f"raw/{SRC}/2026-10/a.json"]


def test_cli_refuses_a_whole_source(store, monkeypatch):
    monkeypatch.setenv("LOTLINE_DATA_DIR", str(store.root))
    assert main(["manifest", "supersede", "--source", SRC, "--reason", "x", "--apply"]) == 2
    assert not store.superseded_path.exists()
