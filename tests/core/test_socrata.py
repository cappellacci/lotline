"""Socrata pager against a fake SODA server: paging, field selection, errors, overlap, token, snapshots."""

import json
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from lotline.io import socrata
from lotline.io.store import DataStore

DOMAIN, DATASET = "data.example.test", "abcd-1234"


def _server(n=25, calls=None, error=None, repeat_first=False):
    rows = [
        {":id": f"row-{i:03d}", "permit": f"P{i}", "units": str(i % 3), "name": "SECRET"} for i in range(n)
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        if calls is not None:
            calls.append(request.url)
        if request.url.path.startswith("/api/views/"):
            return httpx.Response(200, json={"id": DATASET, "name": "Permits", "rowsUpdatedAt": 1})
        q = {k: v[0] for k, v in parse_qs(urlparse(str(request.url)).query).items()}
        if error:
            return httpx.Response(400, json={"message": error, "errorCode": "query.soql.no-such-column"})
        fields = q["$select"].split(",")
        assert q["$order"] == ":id"
        off, lim = int(q["$offset"]), int(q["$limit"])
        page = rows[off : off + lim] if not (repeat_first and off) else rows[:lim]
        out = [{k: r[k] for k in fields if k in r and not (k == "units" and r[k] == "0")} for r in page]
        return httpx.Response(200, json=out)

    return httpx.Client(transport=httpx.MockTransport(handler))


def _download(tmp_path, http, **kw):
    kw = {"select": ["permit", "units"], "vintage": "v"} | kw
    return socrata.download_dataset(
        DOMAIN,
        DATASET,
        store=DataStore(tmp_path),
        source="test_soda",
        license="PD",
        adapter="test",
        adapter_version="1",
        http=http,
        pause=0,
        **kw,
    )


def _pages(tmp_path):
    return sorted((tmp_path / "raw/test_soda/v/dataset").glob("q-*/page_*.json"))


def test_pages_until_a_short_page_and_returns_only_selected_fields(tmp_path):
    df = _download(tmp_path, _server(n=25), page_size=10)
    assert df["permit"].tolist() == [f"P{i}" for i in range(25)]
    assert list(df.columns) == ["permit", "units"]  # no row id, and never a field that wasn't asked for
    assert df["units"].isna().sum() == 9  # SODA omits null keys: they come back as missing, not dropped
    assert [p.name for p in _pages(tmp_path)] == ["page_0001.json", "page_0002.json", "page_0003.json"]
    assert (tmp_path / "raw/test_soda/v/dataset/dataset.json").exists()
    assert len(DataStore(tmp_path).manifest()) == 4  # dataset.json + 3 pages


def test_exact_multiple_of_page_size_ends_on_an_empty_page(tmp_path):
    df = _download(tmp_path, _server(n=20), page_size=10)
    assert len(df) == 20 and len(_pages(tmp_path)) == 3


def test_select_is_required(tmp_path):
    with pytest.raises(socrata.SocrataError, match="select is required"):
        _download(tmp_path, _server(), select=[])


def test_query_errors_show_sodas_message(tmp_path):
    with pytest.raises(socrata.SocrataError, match="No such column: nope"):
        _download(tmp_path, _server(error="No such column: nope"))
    assert not _pages(tmp_path)  # an error is never cached as data


def test_overlapping_pages_are_an_error(tmp_path):
    with pytest.raises(socrata.SocrataError, match="duplicate or missing row ids"):
        _download(tmp_path, _server(n=25, repeat_first=True), page_size=10)


def test_app_token_is_sent_but_never_logged(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCRATA_APP_TOKEN", "tok-123")
    calls = []
    _download(tmp_path, _server(n=3, calls=calls))
    assert all(c.params.get("$$app_token") == "tok-123" for c in calls)
    manifest = (tmp_path / "manifest.jsonl").read_text()
    assert "tok-123" not in manifest
    assert all("tok-123" not in json.dumps(p.read_text()) for p in _pages(tmp_path))


def test_same_query_reuses_cache_and_another_query_is_a_new_snapshot(tmp_path):
    calls = []
    _download(tmp_path, _server(n=5, calls=calls))
    _download(tmp_path, _server(n=5, calls=calls))
    assert len(calls) == 2  # dataset.json + one page, then everything from cache
    _download(tmp_path, _server(n=5, calls=calls), where="units = '1'")
    pages = _pages(tmp_path)
    assert len(pages) == 2 and len({p.parent for p in pages}) == 2  # its own q- folder, nothing overwritten


def test_resource_url_is_deterministic():
    a = socrata.resource_url(DOMAIN, DATASET, **{"$select": "a,b", "$limit": 5})
    b = socrata.resource_url(DOMAIN, DATASET, **{"$limit": 5, "$select": "a,b"})
    assert a == b and a.startswith(f"https://{DOMAIN}/resource/{DATASET}.json?")
