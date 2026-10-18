"""Registering hand-downloaded files, and superseding the files of a replaced (abandoned) query."""

import os

import pytest

from lotline.adapters.national import fred
from lotline.cli import main
from lotline.io.store import DataStore, ManifestEntry, sha256_file

SRC = fred.SOURCE


def _write(store, rel, text, url, accessed_at):
    """Write a raw file and record its download, as fetch() would."""
    path = store.root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    fields = dict(sha256=sha256_file(path), bytes=path.stat().st_size, source=SRC, license="PD")
    store.record(
        ManifestEntry(url=url, path=rel, accessed_at=accessed_at, adapter="t", adapter_version="1", **fields)
    )


@pytest.fixture
def download(tmp_path):
    f = tmp_path / "Downloads" / "roll.zip"
    f.parent.mkdir()
    f.write_bytes(b"zipbytes")
    os.utime(f, (1760000000, 1760000000))  # 2025-10-09 UTC
    return f


def test_register_links_the_file_into_raw_and_logs_it(tmp_path, download):
    store = DataStore(tmp_path / "data")
    e = store.register(
        download, source="tcad", url="https://example.test/exports", license="Public", vintage="2026"
    )
    dest = store.root / "raw/tcad/2026/roll.zip"
    assert dest.read_bytes() == b"zipbytes" and download.exists()  # original left in place
    assert e.path == "raw/tcad/2026/roll.zip" and e.sha256 == sha256_file(download) and e.bytes == 8
    assert e.adapter == "manual_export" and e.accessed_at.startswith("2025-10-09")
    assert store.registered("tcad") == [e] and store.registered("other") == []


def test_register_twice_is_a_no_op_and_a_different_file_is_refused(tmp_path, download):
    store = DataStore(tmp_path / "data")
    kw = dict(source="tcad", url="https://example.test/x", license="Public", vintage="2026")
    first = store.register(download, **kw)
    assert store.register(download, **kw) == first and len(store.manifest()) == 1
    other = download.with_name("other") / "roll.zip"
    other.parent.mkdir()
    other.write_bytes(b"different")
    with pytest.raises(FileExistsError, match="different file"):
        store.register(other, **kw)
    assert (store.root / "raw/tcad/2026/roll.zip").read_bytes() == b"zipbytes"


def test_cli_register_uses_the_file_date_as_vintage(tmp_path, download, monkeypatch):
    monkeypatch.setenv("LOTLINE_DATA_DIR", str(tmp_path / "data"))
    args = ["manifest", "register", str(download), "--source", "tcad", "--url", "https://x", "--license", "P"]
    assert main(args) == 0
    (entry,) = DataStore(tmp_path / "data").manifest()
    assert entry.path.startswith("raw/tcad/2025-10-") and entry.path.endswith("/roll.zip")


def test_abandoned_query_files_can_be_superseded_only_by_path(tmp_path, monkeypatch, capsys):
    store = DataStore(tmp_path)
    _write(
        store,
        f"raw/{SRC}/v/layer/q-old/page_0001.json",
        "old",
        "https://x/q?fields=a",
        "2026-10-15T10:00:00+00:00",
    )
    _write(
        store,
        f"raw/{SRC}/v/layer/q-new/page_0001.json",
        "new",
        "https://x/q?fields=b",
        "2026-10-15T11:00:00+00:00",
    )
    monkeypatch.setenv("LOTLINE_DATA_DIR", str(tmp_path))
    base = ["manifest", "supersede", "--source", SRC, "--reason", "replaced by q-new", "--apply"]
    assert main([*base, "--abandoned"]) == 2  # never without --path
    assert main([*base, "--path", f"raw/{SRC}/v/layer/q-old/*"]) == 0
    assert (
        "1 kept" in capsys.readouterr().out and not store.supersessions()
    )  # intact: kept without --abandoned
    assert main([*base, "--path", f"raw/{SRC}/v/layer/q-old/*", "--abandoned"]) == 0
    assert [s.path for s in store.supersessions()] == [f"raw/{SRC}/v/layer/q-old/page_0001.json"]
