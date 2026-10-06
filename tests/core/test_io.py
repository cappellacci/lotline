import httpx

from lotline.io import DataStore, fetch
from lotline.io.store import data_dir


def _fetch(store, transport, **kw):
    return fetch(
        "https://example.test/a.txt",
        store.raw("src", 2024) / "a.txt",
        store=store,
        source="src",
        license="PD",
        adapter="test",
        adapter_version="1",
        http=httpx.Client(transport=transport),
        **kw,
    )


def test_fetch_downloads_once_and_records_manifest(tmp_path):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, content=b"hello", headers={"ETag": '"v1"'})

    store = DataStore(tmp_path)
    path = _fetch(store, httpx.MockTransport(handler))
    assert path.read_bytes() == b"hello"
    _fetch(store, httpx.MockTransport(handler))  # cached: no second request
    assert len(calls) == 1
    (entry,) = store.manifest()
    assert entry.path == "raw/src/2024/a.txt" and entry.bytes == 5 and entry.etag == '"v1"'
    assert entry.sha256 == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"


def test_refresh_sends_conditional_request_and_keeps_file_on_304(tmp_path):
    seen = []

    def handler(request):
        seen.append(request.headers.get("If-None-Match"))
        if seen[-1]:
            return httpx.Response(304)
        return httpx.Response(200, content=b"v1", headers={"ETag": '"v1"'})

    store = DataStore(tmp_path)
    _fetch(store, httpx.MockTransport(handler))
    path = _fetch(store, httpx.MockTransport(handler), refresh=True)
    assert seen == [None, '"v1"'] and path.read_bytes() == b"v1"
    assert len(store.manifest()) == 1  # unchanged file: no new manifest line


def test_retries_transient_errors(tmp_path):
    statuses = iter([503, 200])

    def handler(request):
        code = next(statuses)
        return httpx.Response(code, content=b"ok" if code == 200 else b"")

    path = _fetch(DataStore(tmp_path), httpx.MockTransport(handler), backoff=0)
    assert path.read_bytes() == b"ok"


def test_data_dir_from_env(monkeypatch, tmp_path):
    monkeypatch.setenv("LOTLINE_DATA_DIR", str(tmp_path))
    assert data_dir() == tmp_path.resolve()
