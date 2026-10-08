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
        **kw,
    )


def test_offset_paging_gets_every_feature_once(tmp_path):
    df = _download(tmp_path, _server(n=25, max_records=10), vintage="2026-10-14")
    assert sorted(df.OBJECTID) == list(range(1, 26))
    pages = sorted(p.name for p in (tmp_path / "raw/test_permits/2026-10-14/layer").glob("page_*.json"))
    assert pages == ["page_0001.json", "page_0002.json", "page_0003.json"]
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
    assert (tmp_path / "raw/test_permits/v/layer/object_ids.json").exists()
    assert len(list((tmp_path / "raw/test_permits/v/layer").glob("page_*.json"))) == 3  # chunks of 500


def test_error_body_raises_and_is_not_cached(tmp_path):
    with pytest.raises(arcgis.ArcGISError, match="Invalid query"):
        _download(tmp_path, _server(error=True), vintage="v")
    assert not list((tmp_path / "raw/test_permits/v/layer").glob("page_*.json"))


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
    assert (tmp_path / "raw/test_permits/2026-10-21/layer/page_0001.json").exists()


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
    page = tmp_path / "raw/test_permits/v/layer/page_0001.json"
    assert len(json.loads(page.read_text())["features"]) == 3


def test_polygon_layers_return_centroids(tmp_path):
    calls = []
    df = _download(tmp_path, _server(n=3, calls=calls, polygon=True), geometry=True, vintage="v")
    assert any("returnCentroid=true" in c for c in calls) and set(df.lat) == {44.0}
