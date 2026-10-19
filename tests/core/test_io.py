import httpx
import pytest

from lotline.io import DataStore, fetch
from lotline.io.http import RawOverwriteError
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


def test_read_keeps_every_sources_columns(tmp_path):
    # pandas.read_parquet(folder) keeps only the first file's schema; DataStore.read must not
    import pandas as pd

    store = DataStore(tmp_path)
    folder = store.processed("MN", "market_geo_year")
    folder.mkdir(parents=True)
    pd.DataFrame({"geo": ["county:27053"], "year": [2024], "hpi": [500.0]}).to_parquet(
        folder / "fhfa.parquet"
    )
    pd.DataFrame({"geo": ["national:US"], "year": [2024], "cpi_u": [313.7]}).to_parquet(
        folder / "fred.parquet"
    )
    df = store.read("MN", "market_geo_year")
    assert {"hpi", "cpi_u"} <= set(df.columns) and len(df) == 2
    assert df.set_index("geo").loc["national:US", "cpi_u"] == 313.7
    assert store.read("MN", "parcels") is None  # not built


def test_fetch_never_overwrites_a_raw_file_from_another_url(tmp_path):
    store = DataStore(tmp_path)
    dest = store.raw("src", 2024) / "a.txt"
    ok = httpx.MockTransport(lambda r: httpx.Response(200, content=r.url.query or b"plain"))

    def get(url, **kw):
        return fetch(url, dest, store=store, source="src", license="PD", adapter="t", adapter_version="1",
                     http=httpx.Client(transport=ok), **kw)  # fmt: skip

    get("https://example.test/a.txt?fields=a")
    for kw in ({}, {"refresh": True}):  # neither a cached read nor a refresh may touch another URL's file
        with pytest.raises(RawOverwriteError, match="different URL"):
            get("https://example.test/a.txt?fields=b", **kw)
    assert dest.read_bytes() == b"fields=a" and len(store.manifest()) == 1
    dest.unlink()  # no file on disk: nothing to protect, so the new URL may write it
    get("https://example.test/a.txt?fields=b")
    assert dest.read_bytes() == b"fields=b"


def test_census_requests_are_spaced_across_processes(tmp_path, monkeypatch):
    from lotline.io import http as h

    clock = {"now": 1000.0}
    slept = []
    monkeypatch.setattr(h.time, "time", lambda: clock["now"])
    monkeypatch.setattr(
        h.time, "sleep", lambda s: (slept.append(round(s, 3)), clock.update(now=clock["now"] + s))
    )
    store = DataStore(tmp_path)
    h._wait_turn(store, "https://tigerweb.geo.census.gov/arcgis/rest/services/x?f=json")  # first: no wait
    clock["now"] += 0.25
    h._wait_turn(store, "https://api.census.gov/data/2024/acs/acs5")  # same domain, 0.25 s later
    h._wait_turn(store, "https://example.test/a.txt")  # other hosts: never limited
    assert slept == [0.75]
    assert (tmp_path / ".ratelimit" / "census.gov").read_text() == "1001.000"
