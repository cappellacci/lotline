"""ArcGIS pager against a fake server: offset paging, server caps, object-ID fallback, errors, snapshots."""

import json
from urllib.parse import parse_qs, urlparse

import httpx
import pandas as pd
import pytest

from lotline.io import arcgis
from lotline.io.store import DataStore

URL = "https://gis.example.test/arcgis/rest/services/Permits/FeatureServer/0"


def _server(n=25, max_records=10, cap=None, pagination=True, error=False, calls=None, polygon=False):
    """A fake layer of `n` features; `cap` makes the server return fewer than asked."""
    feats = [
        {"attributes": {"OBJECTID": i, "UNITS": i % 3}, "geometry": {"x": -93.0 - i / 100, "y": 45.0}}
        for i in range(1, n + 1)
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        if calls is not None:
            calls.append(str(request.url))
        q = {k: v[0] for k, v in parse_qs(urlparse(str(request.url)).query).items()}
        if not request.url.path.endswith("/query"):
            return httpx.Response(
                200,
                json={
                    "maxRecordCount": max_records,
                    "geometryType": "esriGeometryPolygon" if polygon else "esriGeometryPoint",
                    "objectIdField": "OBJECTID",
                    "advancedQueryCapabilities": {"supportsPagination": pagination, "supportsOrderBy": True},
                },
            )
        if q.get("returnCentroid") and not polygon:
            return httpx.Response(
                200, json={"error": {"code": 400, "message": "returnCentroid not supported"}}
            )
        if polygon and q.get("returnGeometry") == "true":
            feats_out = [f | {"centroid": {"x": f["geometry"]["x"], "y": 44.0}} for f in feats]
        else:
            feats_out = feats
        if error:
            return httpx.Response(200, json={"error": {"code": 400, "message": "Invalid query"}})
        if q.get("returnIdsOnly") == "true":
            return httpx.Response(200, json={"objectIds": [f["attributes"]["OBJECTID"] for f in feats][::-1]})
        if "objectIds" in q:
            ids = {int(i) for i in q["objectIds"].split(",")}
            return httpx.Response(
                200, json={"features": [f for f in feats_out if f["attributes"]["OBJECTID"] in ids]}
            )
        assert pagination, "offset query sent to a layer without pagination"
        off, size = int(q["resultOffset"]), int(q["resultRecordCount"])
        limit = min(size, cap or size, max_records)
        page = feats_out[off : off + limit]
        return httpx.Response(200, json={"features": page, "exceededTransferLimit": off + limit < len(feats)})

    return httpx.Client(transport=httpx.MockTransport(handler))


def _download(tmp_path, http, **kw):
    return arcgis.download_layer(
        URL,
        store=DataStore(tmp_path),
        source="test_permits",
        license="CC0",
        adapter="test",
        adapter_version="1",
        http=http,
        pause=0,
        **({"retry_backoff": 0} | kw),
    )


def _pages(tmp_path, vintage):
    """Raw page files of every query folder under raw/test_permits/<vintage>/layer/."""
    return sorted((tmp_path / f"raw/test_permits/{vintage}/layer").glob("q-*/page_*.json"))


def test_offset_paging_gets_every_feature_once(tmp_path):
    df = _download(tmp_path, _server(n=25, max_records=10), vintage="2026-10-14")
    assert sorted(df.OBJECTID) == list(range(1, 26))
    pages = _pages(tmp_path, "2026-10-14")
    assert [p.name for p in pages] == ["page_0001.json", "page_0002.json", "page_0003.json"]
    assert len({p.parent for p in pages}) == 1  # one query folder
    entries = DataStore(tmp_path).manifest()
    assert len(entries) == 4 and all(e.source == "test_permits" for e in entries)  # layer.json + 3 pages


def test_server_cap_below_page_size_keeps_paging(tmp_path):
    # asks for 10, server returns 4 with exceededTransferLimit: must continue from offset 4, not 10
    df = _download(tmp_path, _server(n=13, max_records=10, cap=4), vintage="v")
    assert sorted(df.OBJECTID) == list(range(1, 14))


def test_exact_multiple_of_page_size_terminates(tmp_path):
    df = _download(tmp_path, _server(n=20, max_records=10), vintage="v")
    assert len(df) == 20


def test_object_id_fallback_without_pagination(tmp_path):
    df = _download(tmp_path, _server(n=1203, max_records=1000, pagination=False), vintage="v")
    assert sorted(df.OBJECTID) == list(range(1, 1204))
    assert len(list((tmp_path / "raw/test_permits/v/layer").glob("q-*/object_ids.json"))) == 1
    assert len(_pages(tmp_path, "v")) == 3  # chunks of 500


def test_error_body_raises_and_is_not_cached(tmp_path):
    with pytest.raises(arcgis.ArcGISError, match="Invalid query"):
        _download(tmp_path, _server(error=True), vintage="v")
    assert not _pages(tmp_path, "v")


def test_geometry_returns_wgs84_points(tmp_path):
    calls = []
    df = _download(tmp_path, _server(n=3, calls=calls), geometry=True, vintage="v")
    assert df.lon.tolist() == pytest.approx([-93.01, -93.02, -93.03]) and set(df.lat) == {45.0}
    assert any("outSR=4326" in c for c in calls)


def test_same_day_reuses_cache_and_new_day_is_a_new_snapshot(tmp_path):
    calls = []
    _download(tmp_path, _server(n=5, calls=calls), vintage="2026-10-14")
    _download(tmp_path, _server(n=5, calls=calls), vintage="2026-10-14")
    assert len(calls) == 2  # metadata + one page, second run served from cache
    _download(tmp_path, _server(n=5, calls=calls), vintage="2026-10-21")
    assert len(calls) == 4
    assert [p.name for p in _pages(tmp_path, "2026-10-21")] == ["page_0001.json"]


def test_query_url_is_deterministic():
    a = arcgis.query_url(URL, where="1=1", f="json", resultOffset=0)
    b = arcgis.query_url(URL, resultOffset=0, f="json", where="1=1")
    assert a == b and a.startswith(URL + "/query?")


def test_epoch_ms_dates():
    out = arcgis.epoch_ms_to_timestamp(pd.Series([1704067200000, None]))
    assert out.iloc[0] == pd.Timestamp("2024-01-01") and pd.isna(out.iloc[1])


def test_layer_without_object_id_field_is_an_error():
    with pytest.raises(arcgis.ArcGISError):
        arcgis.layer_info({"fields": [{"name": "X", "type": "esriFieldTypeString"}]})


def test_raw_pages_are_valid_json(tmp_path):
    _download(tmp_path, _server(n=3), vintage="v")
    (page,) = _pages(tmp_path, "v")
    assert len(json.loads(page.read_text())["features"]) == 3


def test_polygon_layers_return_centroids(tmp_path):
    calls = []
    df = _download(tmp_path, _server(n=3, calls=calls, polygon=True), geometry=True, vintage="v")
    assert any("returnCentroid=true" in c for c in calls) and set(df.lat) == {44.0}


def test_a_different_query_the_same_day_is_a_new_snapshot_not_an_overwrite(tmp_path):
    calls = []
    _download(tmp_path, _server(n=5, calls=calls), vintage="v", out_fields="OBJECTID,UNITS")
    first = {p: p.read_bytes() for p in _pages(tmp_path, "v")}
    _download(tmp_path, _server(n=5, calls=calls), vintage="v", out_fields="OBJECTID")
    pages = _pages(tmp_path, "v")
    assert len(pages) == 2 and len({p.parent for p in pages}) == 2  # two query folders
    assert all(p.read_bytes() == b for p, b in first.items())  # the first query's pages are untouched
    assert len(calls) == 3  # layer.json is shared and cached; one page per query


def test_query_folder_depends_on_what_defines_the_query():
    base = {"where": "1=1", "outFields": "*", "f": "json"}
    same = arcgis.query_folder(dict(reversed(base.items())), 10, "offset")
    assert arcgis.query_folder(base, 10, "offset") == same and same.startswith("q-") and len(same) == 10
    assert arcgis.query_folder(base | {"outFields": "A"}, 10, "offset") != same
    assert arcgis.query_folder(base, 20, "offset") != same
    assert arcgis.query_folder(base, 10, "object_ids") != same


def _polygon_server(n=3, fail_first=0, calls=None, centroids=True):
    """A polygon layer: features carry rings; the server computes label points (centroids) on request.
    `fail_first` query requests get an ArcGIS error body (HTTP 200), as flaky servers do on deep pages."""
    left = [fail_first]
    square = [[[-83.0, 40.0], [-82.9, 40.0], [-82.9, 40.1], [-83.0, 40.1], [-83.0, 40.0]]]

    def handler(request: httpx.Request) -> httpx.Response:
        q = {k: v[0] for k, v in parse_qs(urlparse(str(request.url)).query).items()}
        if not request.url.path.endswith("/query"):
            return httpx.Response(
                200,
                json={
                    "maxRecordCount": 10,
                    "geometryType": "esriGeometryPolygon",
                    "objectIdField": "OBJECTID",
                    "advancedQueryCapabilities": {
                        "supportsPagination": True,
                        "supportsOrderBy": True,
                        "supportsReturningGeometryCentroid": centroids,
                    },
                },
            )
        if calls is not None:
            calls.append(q)
        if left[0]:
            left[0] -= 1
            return httpx.Response(200, json={"error": {"code": 400, "message": "Invalid query parameters"}})
        feats = []
        for i in range(1, n + 1):
            f = {"attributes": {"OBJECTID": i}}
            if q.get("returnGeometry") == "true":
                f["geometry"] = {"rings": square}
            if q.get("returnCentroid") == "true":
                f["centroid"] = {"x": -82.95, "y": 40.05}
            feats.append(f)
        off = int(q["resultOffset"])
        return httpx.Response(200, json={"features": feats[off : off + 10]})

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_centroid_mode_gets_label_points_without_polygons(tmp_path):
    calls = []
    df = _download(tmp_path, _polygon_server(calls=calls), geometry="centroid", vintage="v")
    assert set(df.lon) == {-82.95} and set(df.lat) == {40.05} and "rings" not in df
    assert calls[0]["returnGeometry"] == "false" and calls[0]["returnCentroid"] == "true"


def test_polygon_mode_returns_rings(tmp_path):
    df = _download(tmp_path, _polygon_server(), geometry="polygon", vintage="v")
    assert len(df) == 3 and df.rings.iloc[0][0][1] == [-82.9, 40.0] and "lon" not in df


def test_centroid_and_polygon_modes_need_a_polygon_layer(tmp_path):
    for mode in ("centroid", "polygon"):
        with pytest.raises(arcgis.ArcGISError, match="needs a polygon layer"):
            _download(tmp_path, _server(n=3), geometry=mode, vintage="v")
    with pytest.raises(ValueError, match="geometry must be"):
        _download(tmp_path, _server(n=3), geometry="lines", vintage="v")


def test_flaky_error_pages_are_retried(tmp_path):
    calls = []
    df = _download(tmp_path, _polygon_server(fail_first=2, calls=calls), vintage="v", retries=3)
    assert len(df) == 3 and len(calls) == 3  # two error bodies, then the page
    (page,) = _pages(tmp_path, "v")
    assert "error" not in json.loads(page.read_text())  # error bodies are never kept as data


def test_persistent_errors_raise_after_the_retries(tmp_path):
    calls = []
    with pytest.raises(arcgis.ArcGISError, match="Invalid query parameters"):
        _download(tmp_path, _polygon_server(fail_first=99, calls=calls), vintage="v", retries=2)
    assert len(calls) == 3


def test_object_id_field_is_always_requested(tmp_path):
    calls = []
    df = _download(tmp_path, _polygon_server(calls=calls), out_fields="NAME", vintage="v")
    assert calls[0]["outFields"] == "OBJECTID,NAME" and len(df) == 3


def test_centroid_mode_refuses_servers_that_cannot_compute_centroids(tmp_path):
    with pytest.raises(arcgis.ArcGISError, match="can't compute centroids"):
        _download(tmp_path, _polygon_server(centroids=False), geometry="centroid", vintage="v")
