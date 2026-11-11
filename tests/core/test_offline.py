"""Offline builds (`lotline fetch --offline`): snapshot choice, incomplete snapshots, no network, records.

Snapshots are first written by the real pagers against fake servers (httpx.MockTransport); the offline reads
then run with `httpx.Client.send` patched to fail the test, so any request at all is caught.
"""

import datetime as dt
import json
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from lotline import cli, registry
from lotline.io import arcgis, fetch, socrata
from lotline.io.http import client
from lotline.io.offline import OfflineError, offline_build, read_builds
from lotline.io.store import DataStore

URL = "https://gis.example.test/arcgis/rest/services/Permits/FeatureServer/0"
OTHER_URL = "https://gis.example.test/arcgis/rest/services/Other/FeatureServer/0"
DOMAIN, DATASET = "data.example.test", "abcd-1234"


def _arcgis_server(n, max_records=10, pagination=True):
    feats = [{"attributes": {"OBJECTID": i, "UNITS": i % 3}} for i in range(1, n + 1)]

    def handler(request: httpx.Request) -> httpx.Response:
        q = {k: v[0] for k, v in parse_qs(urlparse(str(request.url)).query).items()}
        if not request.url.path.endswith("/query"):
            caps = {"supportsPagination": pagination, "supportsOrderBy": True}
            return httpx.Response(
                200,
                json={
                    "maxRecordCount": max_records,
                    "objectIdField": "OBJECTID",
                    "advancedQueryCapabilities": caps,
                },
            )
        if q.get("returnIdsOnly") == "true":
            return httpx.Response(200, json={"objectIds": [f["attributes"]["OBJECTID"] for f in feats]})
        if "objectIds" in q:
            ids = {int(i) for i in q["objectIds"].split(",")}
            return httpx.Response(
                200, json={"features": [f for f in feats if f["attributes"]["OBJECTID"] in ids]}
            )
        off, size = int(q["resultOffset"]), int(q["resultRecordCount"])
        return httpx.Response(200, json={"features": feats[off : off + size]})

    return httpx.Client(transport=httpx.MockTransport(handler))


def _layer(store, vintage=None, http=None, url=URL, **kw):
    return arcgis.download_layer(
        url,
        store=store,
        source="test_permits",
        license="CC0",
        adapter="test",
        adapter_version="1",
        vintage=vintage,
        http=http,
        pause=0,
        retry_backoff=0,
        **kw,
    )


@pytest.fixture
def block(monkeypatch):
    """Call `block()` once the cached snapshots are written: from then on any HTTP request, through a real
    or a mocked transport, fails the test."""

    def send(self, request, *a, **kw):
        pytest.fail(f"offline build sent a request: {request.url}")

    return lambda: monkeypatch.setattr(httpx.Client, "send", send)


def _snapshots(tmp_path):
    """Two cached snapshots of the same query: 25 features on 11-01, 30 on 11-05."""
    store = DataStore(tmp_path)
    _layer(store, "2026-11-01", _arcgis_server(25))
    _layer(store, "2026-11-05", _arcgis_server(30))
    return store


# ArcGIS ----------------------------------------------------------------------------------------------------


def test_offline_reads_the_newest_complete_snapshot(tmp_path, block):
    store = _snapshots(tmp_path)
    block()
    with offline_build(store) as sess:
        df = _layer(store)  # default vintage: latest cached, not today's (absent) folder
    assert len(df) == 30
    (used,) = sess.used
    assert used.startswith("raw/test_permits/2026-11-05/layer/q-")
    assert not (tmp_path / f"raw/test_permits/{dt.date.today().isoformat()}").exists()


def test_todays_date_as_vintage_also_means_latest_cached(tmp_path, block):
    store = _snapshots(tmp_path)
    block()
    with offline_build(store):
        assert len(_layer(store, dt.date.today().isoformat())) == 30


def test_an_incomplete_newer_snapshot_is_skipped_with_a_note(tmp_path, block):
    store = _snapshots(tmp_path)
    block()
    (page,) = (tmp_path / "raw/test_permits/2026-11-05/layer").glob("q-*/page_0002.json")
    page.unlink()  # 30 features at 10 a page: page 1 is full, so page 2 must exist
    with offline_build(store) as sess:
        df = _layer(store)
    assert len(df) == 25  # the complete 11-01 snapshot, never a mix of the two
    assert sess.used[0].startswith("raw/test_permits/2026-11-01/")
    (note,) = sess.notes
    assert "2026-11-05" in note and "incomplete" in note and "page_0002.json is missing" in note


def test_object_id_snapshot_missing_a_chunk_is_incomplete(tmp_path, block):
    store = DataStore(tmp_path)
    _layer(store, "2026-11-05", _arcgis_server(1203, max_records=1000, pagination=False))
    (page,) = (tmp_path / "raw/test_permits/2026-11-05/layer").glob("q-*/page_0003.json")
    page.unlink()  # object_ids.json lists 1,203 IDs: three chunks of 500
    block()
    with offline_build(store), pytest.raises(OfflineError, match="page_0003.json is missing"):
        _layer(store)


def test_no_snapshot_fails_clearly(tmp_path, block):
    store = DataStore(tmp_path)
    block()
    with offline_build(store), pytest.raises(OfflineError, match="no cached snapshot of this layer"):
        _layer(store)


def test_a_different_query_has_no_snapshot(tmp_path, block):
    store = _snapshots(tmp_path)
    block()
    with offline_build(store), pytest.raises(OfflineError, match="no pages for this query"):
        _layer(store, out_fields="OBJECTID")  # another field list: another q-<hash>, never cached


def test_an_explicit_vintage_is_read_as_is(tmp_path, block):
    store = _snapshots(tmp_path)
    block()
    with offline_build(store):
        assert len(_layer(store, "2026-11-01")) == 25
        with pytest.raises(OfflineError):
            _layer(store, "2026-10-01")


def test_a_snapshot_of_another_layer_under_the_same_name_is_not_read(tmp_path, block):
    store = DataStore(tmp_path)
    _layer(store, "2026-11-05", _arcgis_server(30), url=OTHER_URL)
    block()
    with offline_build(store) as sess, pytest.raises(OfflineError):
        _layer(store)
    assert "downloaded from" in sess.notes[0]


# Plain HTTP ------------------------------------------------------------------------------------------------


def _plain(store, vintage, http=None):
    return fetch(
        "https://example.test/a.csv",
        store.raw("src", vintage) / "a.csv",
        store=store,
        source="src",
        license="PD",
        adapter="test",
        adapter_version="1",
        http=http,
    )


def test_plain_fetch_offline_reuses_the_newest_copy_of_the_url(tmp_path, block):
    store = DataStore(tmp_path)
    path = _plain(
        store,
        "2026-11-01",
        httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, content=b"a,b\n"))),
    )
    block()
    with offline_build(store) as sess:
        assert _plain(store, "2026-11-11") == path  # today's folder is empty: the newest cached copy is used
        assert _plain(store, "2026-11-01") == path
    assert sess.used == ["raw/src/2026-11-01/a.csv"]
    assert len(store.manifest()) == 1  # nothing new downloaded


def test_plain_fetch_offline_without_a_cached_copy_fails(tmp_path, block):
    store = DataStore(tmp_path)
    block()
    with (
        offline_build(store),
        pytest.raises(OfflineError, match="no cached copy of https://example.test/a.csv"),
    ):
        _plain(store, "2026-11-11")


def test_client_refuses_requests_during_an_offline_build(tmp_path):
    with offline_build(DataStore(tmp_path)), client() as http, pytest.raises(OfflineError, match="refused"):
        http.get("https://example.test/")


# Socrata ---------------------------------------------------------------------------------------------------


def _soda_server(n):
    rows = [{":id": f"row-{i:03d}", "permit": f"P{i}"} for i in range(n)]

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.startswith("/api/views/"):
            return httpx.Response(200, json={"id": DATASET})
        q = {k: v[0] for k, v in parse_qs(urlparse(str(request.url)).query).items()}
        off, lim = int(q["$offset"]), int(q["$limit"])
        return httpx.Response(200, json=rows[off : off + lim])

    return httpx.Client(transport=httpx.MockTransport(handler))


def _soda(store, vintage=None, http=None):
    return socrata.download_dataset(
        DOMAIN,
        DATASET,
        select=["permit"],
        store=store,
        source="test_soda",
        license="PD",
        adapter="test",
        adapter_version="1",
        vintage=vintage,
        page_size=10,
        http=http,
        pause=0,
    )


def test_socrata_offline_skips_an_incomplete_snapshot(tmp_path, block):
    store = DataStore(tmp_path)
    _soda(store, "2026-11-01", _soda_server(15))
    _soda(store, "2026-11-05", _soda_server(25))
    (page,) = (tmp_path / "raw/test_soda/2026-11-05/dataset").glob("q-*/page_0003.json")
    page.unlink()  # pages 1-2 are full (10 rows), so page 3 must exist
    block()
    with offline_build(store) as sess:
        df = _soda(store)
    assert len(df) == 15
    assert "incomplete" in sess.notes[0] and sess.used[0].startswith("raw/test_soda/2026-11-01/")


# CLI and build record --------------------------------------------------------------------------------------


def test_cli_offline_build_is_recorded(tmp_path, monkeypatch, block, capsys):
    store = _snapshots(tmp_path)
    block()
    monkeypatch.setenv("LOTLINE_DATA_DIR", str(tmp_path))
    module = SimpleNamespace(load=lambda state, store, refresh=False: _layer(store))
    src = registry.Source("test_permits", module, "test_table", None)
    monkeypatch.setattr(registry, "sources_for", lambda state: {"test_permits": src})
    assert cli.main(["fetch", "--offline", "--state", "MN", "--source", "test_permits"]) == 0
    (rec,) = read_builds(store)
    assert rec.mode == "offline" and rec.state == "MN" and rec.source == "test_permits"
    assert rec.snapshots[0].startswith("raw/test_permits/2026-11-05/layer/q-")
    assert (tmp_path / "processed/mn/test_table/test_permits.parquet").exists()
    line = json.loads((tmp_path / "manifest.builds.jsonl").read_text())
    assert line["snapshots"] == rec.snapshots


def test_cli_offline_reports_a_missing_snapshot_and_fails(tmp_path, monkeypatch, block, capsys):
    block()
    monkeypatch.setenv("LOTLINE_DATA_DIR", str(tmp_path))
    module = SimpleNamespace(load=lambda state, store, refresh=False: _layer(store))
    src = registry.Source("test_permits", module, "test_table", None)
    monkeypatch.setattr(registry, "sources_for", lambda state: {"test_permits": src})
    assert cli.main(["fetch", "--offline", "--state", "MN", "--source", "test_permits"]) == 1
    assert "FAILED offline" in capsys.readouterr().out
    assert read_builds(DataStore(tmp_path)) == []


def test_cli_offline_and_refresh_conflict():
    assert cli.main(["fetch", "--offline", "--refresh"]) == 2


def test_prune_candidates_lists_older_repeats_and_deletes_nothing(tmp_path):
    from lotline.io.offline import prune_candidates

    store = _snapshots(tmp_path)
    (row,) = prune_candidates(store)
    folder, size, newer = row
    assert folder.startswith("raw/test_permits/2026-11-01/layer/q-") and size > 0
    assert newer.startswith("raw/test_permits/2026-11-05/layer/q-")
    assert (tmp_path / folder).is_dir()
